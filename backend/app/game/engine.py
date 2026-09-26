"""Игровой движок: один объект Game — одна партия от первого уровня до GAME OVER.

Сервер 30 раз в секунду вызывает update(dt), а между вызовами передаёт нажатия клавиш
(set_direction, place_bomb, toggle_pause). После каждого update браузер получает
snapshot() — «фотографию» игры, по которой он всё рисует.

Этапы партии (phase):
    ready       «ПРИГОТОВЬТЕСЬ» — все стоят
    playing     идёт игра
    paused      пауза (клавиша P)
    level_done  все игроки либо ушли в дверь, либо погибли — короткая пауза
    game_over   жизни кончились у всех
"""

from __future__ import annotations

import itertools
import math
import random

from . import ai
from .board import EMPTY, PILLAR, WALL, Board, Cell
from .config import (
    BLAST_RADIUS,
    BOMB_BONUS_OVERFLOW_SCORE,
    BOMB_FUSE,
    CHAIN_DELAY,
    DEATH_TIME,
    ENEMY_SCORES,
    ENEMY_TOUCH_DISTANCE,
    EXTRA_LIFE_EVERY,
    FLAME_TIME,
    HITBOX,
    ITEM_SCORES,
    LEVEL_END_TIME,
    MAX_BOMBS,
    NAMES,
    PICKUP_DISTANCE,
    PLAYER_SPEED,
    READY_TIME,
    SPAWNS,
    START_BOMBS,
    START_FACING,
)
from .difficulty import enemy_stats, for_level
from .entities import Bomb, Enemy, Flame, Item, Player
from .movement import DIRECTIONS, move_on_grid, touched_cells

COINS = ("bag", "bigbag", "gems")
DOOR_MIN_DISTANCE = 6       # дверь прячем подальше от стартовых углов
ENEMY_SPAWN_DISTANCE = 6    # и врагов тоже ставим подальше
ENEMY_REST = 0.25           # сколько враг стоит, если идти некуда


def blast_cells(board: Board, origin: Cell, radius: int = BLAST_RADIUS) -> list[tuple[Cell, str]]:
    """Клетки, которые накроет взрыв: крест на radius клеток.

    Колонна останавливает огонь, стена — сгорает и тоже останавливает.
    """
    cells = [(origin, "near")]
    for dx, dy in DIRECTIONS.values():
        for step in range(1, radius + 1):
            cell = (origin[0] + dx * step, origin[1] + dy * step)
            if not board.inside(cell) or board.get(cell) == PILLAR:
                break
            cells.append((cell, "near" if step == 1 else "far"))
            if board.get(cell) == WALL:
                break
    return cells


def _manhattan(a: Cell, b: Cell) -> int:
    return abs(a[0] - b[0]) + abs(a[1] - b[1])


class Game:
    def __init__(self, players: int = 1, rng: random.Random | None = None, level: int = 1):
        if players not in (1, 2):
            raise ValueError("Игроков может быть 1 или 2")
        self.rng = rng or random.Random()
        self._ids = itertools.count(1)
        self.players = [Player(i, NAMES[i], facing=START_FACING[i]) for i in range(players)]
        self.level = level
        self.events: list[dict] = []
        self.result: str | None = None   # next — идём дальше, retry — переигрываем уровень
        self._start_level()

    # ------------------------------------------------------------------ уровень

    def _start_level(self) -> None:
        self.settings = for_level(self.level, len(self.players))
        keep_free: set[Cell] = set()
        for sx, sy in SPAWNS:  # угол и две соседние клетки — чтобы было куда отойти от первой бомбы
            keep_free |= {(sx, sy), (sx + (1 if sx == 0 else -1), sy), (sx, sy + (1 if sy == 0 else -1))}
        self.board = Board.generate(self.rng, self.settings.walls, keep_free)
        self.hidden = self._hide_items()
        self.items: dict[int, Item] = {}
        self.bombs: dict[int, Bomb] = {}
        self.flames: list[Flame] = []
        self.legacy_dropped = False
        self.at_locked_door: set[int] = set()
        self.result = None
        for player in self.players:
            if player.lives > 0:
                sx, sy = SPAWNS[player.index]
                player.x, player.y = float(sx), float(sy)
                player.state, player.state_time = "alive", 0.0
                player.facing = START_FACING[player.index]
                player.wanted, player.moving, player.death_kind = None, False, None
                player.ghost_bombs.clear()
            else:
                player.state = "out"
        self.enemies = self._spawn_enemies()
        self._set_phase("ready")
        self._emit("level_start", level=self.level)

    def _hide_items(self) -> dict[Cell, str]:
        """Прячет под стенами дверь и бонусы — как в оригинале: 9 штук."""
        walls = self.board.cells_of(WALL)
        self.rng.shuffle(walls)
        starts = [SPAWNS[p.index] for p in self.players]
        far = [c for c in walls if min(_manhattan(c, s) for s in starts) >= DOOR_MIN_DISTANCE]
        door = far[0] if far else walls[0]
        kinds = ["chest", "bomb", "life" if self.rng.random() < self.settings.life_chance else "death"]
        kinds += [self.rng.choice(COINS) for _ in range(5)]
        hidden = {door: "door"}
        hidden.update(zip([c for c in walls if c != door], kinds))
        return hidden

    def _spawn_enemies(self) -> dict[int, Enemy]:
        free = self.board.cells_of(EMPTY)
        for min_distance in (ENEMY_SPAWN_DISTANCE, 4, 2):
            candidates = [c for c in free if all(_manhattan(c, s) >= min_distance for s in SPAWNS)]
            if len(candidates) >= self.settings.enemies:
                break
        enemies = {}
        cells = self.rng.sample(candidates, min(len(candidates), self.settings.enemies))
        for number, (x, y) in enumerate(cells):
            stats = enemy_stats(self.settings, strong=number < self.settings.strong_enemies)
            enemy = Enemy(next(self._ids), float(x), float(y), stats.tier, stats.speed, sight=stats.sight,
                          smart=stats.smart, memory=stats.memory, avoid_danger=stats.avoid_danger)
            enemies[enemy.id] = enemy
        return enemies

    def _set_phase(self, phase: str) -> None:
        self.phase = phase
        self.phase_time = 0.0

    def _emit(self, event: str, /, **data) -> None:
        self.events.append({"type": event, **data})

    # ------------------------------------------------------------------ команды игроков

    def set_direction(self, index: int, direction: str | None, alt: str | None = None) -> None:
        """direction — последняя нажатая стрелка, alt — предыдущая, если она ещё зажата."""
        if 0 <= index < len(self.players) and (direction is None or direction in DIRECTIONS):
            self.players[index].wanted = direction
            self.players[index].wanted_alt = alt if alt in DIRECTIONS and alt != direction else None

    def place_bomb(self, index: int) -> None:
        if self.phase != "playing" or not 0 <= index < len(self.players):
            return
        player = self.players[index]
        if not player.active:
            return
        cell = player.cell
        if any(b.cell == cell for b in self.bombs.values()) or self._bombs_of(index) >= player.capacity:
            return
        bomb = Bomb(next(self._ids), cell, index, BOMB_FUSE, BOMB_FUSE)
        self.bombs[bomb.id] = bomb
        for other in self.players:  # кто стоит на бомбе, может с неё сойти
            if other.active and self._overlaps(other, cell):
                other.ghost_bombs.add(bomb.id)
        self._emit("bomb_placed", player=index, x=cell[0], y=cell[1])

    def toggle_pause(self) -> None:
        if self.phase == "playing":
            self._set_phase("paused")
        elif self.phase == "paused":
            self._set_phase("playing")

    # ------------------------------------------------------------------ ход времени

    def update(self, dt: float) -> None:
        self.phase_time += dt
        if self.phase == "ready" and self.phase_time >= READY_TIME:
            self._set_phase("playing")
        elif self.phase == "playing":
            self._step(dt)
        elif self.phase == "level_done" and self.phase_time >= LEVEL_END_TIME:
            self._finish_level()

    def _step(self, dt: float) -> None:
        for player in self.players:
            if player.active:
                self._move_player(player, dt)
            elif player.state == "dying":
                player.state_time += dt
                if player.state_time >= DEATH_TIME:
                    player.state = "dead"
                    self._drop_legacy(player)
        self._pick_items()
        self._tick_bombs(dt)
        self._tick_flames(dt)
        self._tick_enemies(dt)
        self._check_hits()
        self._check_level_end()

    # ------------------------------------------------------------------ игроки

    @staticmethod
    def _overlaps(player: Player, cell: Cell) -> bool:
        return abs(player.x - cell[0]) < 1 - 1e-6 and abs(player.y - cell[1]) < 1 - 1e-6

    def _bombs_of(self, index: int) -> int:
        return sum(1 for b in self.bombs.values() if b.owner == index)

    def _move_player(self, player: Player, dt: float) -> None:
        player.moving = False
        player.ghost_bombs = {
            bid for bid in player.ghost_bombs if bid in self.bombs and self._overlaps(player, self.bombs[bid].cell)
        }
        if player.wanted is None:
            return
        blocked = {b.cell for b in self.bombs.values() if b.id not in player.ghost_bombs}

        def passable(cell: Cell) -> bool:
            return self.board.is_floor(cell) and cell not in blocked

        # Повернул раньше, чем дошёл до прохода, — продолжаем идти по прежней клавише,
        # а как только проход появится, свернём в него сами.
        for direction in (player.wanted, player.wanted_alt):
            if direction is None:
                continue
            x, y = move_on_grid(player.x, player.y, direction, PLAYER_SPEED * dt, passable)
            if (x, y) != (player.x, player.y):
                player.x, player.y, player.facing, player.moving = x, y, direction, True
                return
        player.facing = player.wanted

    def _door_locked(self, item: Item) -> bool:
        """Взорванная дверь пускает, только когда убиты все враги."""
        return item.kind == "door" and item.burned and bool(self.enemies)

    def _pick_items(self) -> None:
        for player in self.players:
            at_locked = False
            for item in list(self.items.values()):
                if not player.active:
                    break
                if math.hypot(player.x - item.cell[0], player.y - item.cell[1]) < PICKUP_DISTANCE:
                    if self._door_locked(item):
                        at_locked = True
                        if player.index not in self.at_locked_door:
                            self._emit("door_closed", player=player.index, x=item.cell[0], y=item.cell[1])
                    else:
                        self._apply_item(player, item)
            if at_locked:
                self.at_locked_door.add(player.index)
            else:
                self.at_locked_door.discard(player.index)

    def _apply_item(self, player: Player, item: Item) -> None:
        kind = item.kind
        if kind != "door":
            del self.items[item.id]
        self._emit("item_taken", player=player.index, kind=kind, x=item.cell[0], y=item.cell[1])
        if kind == "door":
            player.state, player.state_time = "exited", 0.0
            player.wanted, player.moving = None, False
            self._emit("player_exited", player=player.index)
        elif kind == "bomb":
            if player.capacity < MAX_BOMBS:
                player.capacity += 1
            else:
                self._add_score(player, BOMB_BONUS_OVERFLOW_SCORE)
        elif kind == "life":
            player.lives += 1
        elif kind == "death":
            self._kill(player, epic=False, cause="trap")
        else:
            self._add_score(player, ITEM_SCORES[kind])

    def _add_score(self, player: Player, points: int) -> None:
        before = player.score // EXTRA_LIFE_EVERY
        player.score += points
        gained = player.score // EXTRA_LIFE_EVERY - before
        if gained:
            player.lives += gained
            self._emit("extra_life", player=player.index)

    def _kill(self, player: Player, epic: bool, cause: str, killer: int | None = None) -> None:
        """epic — погиб вплотную к бомбе: «суперсмерть», героя отбрасывает взрывом.
        cause — от чего: "bomb", "enemy" или "trap"; killer — чья бомба убила (None — враг или ловушка)."""
        player.state, player.state_time = "dying", 0.0
        player.wanted, player.moving = None, False
        player.lives = max(0, player.lives - 1)
        player.capacity = START_BOMBS
        player.death_kind = "super" if epic else "normal"
        self._emit("player_died", player=player.index, kind=player.death_kind, cause=cause, killer=killer)

    def _drop_legacy(self, player: Player) -> None:
        """«Наследство» — один раз за уровень остаётся на месте погибшего."""
        if not self.legacy_dropped:
            self.legacy_dropped = True
            item = Item(next(self._ids), player.cell, "legacy")
            self.items[item.id] = item

    # ------------------------------------------------------------------ бомбы и огонь

    def _tick_bombs(self, dt: float) -> None:
        for bomb in self.bombs.values():
            bomb.fuse -= dt
        # взрываем по порядку установки: сначала самые ранние
        for bomb in sorted((b for b in self.bombs.values() if b.fuse <= 0), key=lambda b: b.id):
            self._explode(bomb)

    def _explode(self, bomb: Bomb) -> None:
        del self.bombs[bomb.id]
        self._emit("explosion", id=bomb.id, x=bomb.cell[0], y=bomb.cell[1])
        caught: list[Bomb] = []
        for cell, kind in blast_cells(self.board, bomb.cell):
            self.flames.append(Flame(cell, kind, FLAME_TIME, bomb.owner, bomb.id))
            if self.board.get(cell) == WALL:
                self.board.set(cell, EMPTY)
                self._emit("wall_destroyed", x=cell[0], y=cell[1])
                hidden = self.hidden.pop(cell, None)
                if hidden:
                    item = Item(next(self._ids), cell, hidden, revealed_by=bomb.id)
                    self.items[item.id] = item
            caught.extend(b for b in self.bombs.values() if b.cell == cell)
        # Цепная реакция идёт волной: задетые бомбы рвутся по очереди — от поставленной раньше к поздним.
        for rank, other in enumerate(sorted(caught, key=lambda b: b.id), start=1):
            other.fuse = min(other.fuse, CHAIN_DELAY * rank)

    def _tick_flames(self, dt: float) -> None:
        for flame in self.flames:
            flame.time_left -= dt
        self.flames = [f for f in self.flames if f.time_left > 0]
        self._burn_items()

    def _burn_items(self) -> None:
        """Огонь уничтожает открытые бонусы. Дверь не сгорает, но запирается до гибели всех врагов."""
        for item in list(self.items.values()):
            if not any(f.cell == item.cell and f.bomb != item.revealed_by for f in self.flames):
                continue
            x, y = item.cell
            if item.kind != "door":
                del self.items[item.id]
                self._emit("item_destroyed", kind=item.kind, x=x, y=y)
            elif not item.burned:
                item.burned = True
                if self.enemies:
                    self._emit("door_locked", x=x, y=y)

    def _danger_cells(self) -> set[Cell]:
        cells = {f.cell for f in self.flames}
        for bomb in self.bombs.values():
            cells.update(c for c, _ in blast_cells(self.board, bomb.cell))
        return cells

    # ------------------------------------------------------------------ враги

    def _tick_enemies(self, dt: float) -> None:
        blocked = {b.cell for b in self.bombs.values()}
        danger = self._danger_cells() if (self.bombs or self.flames) else set()
        for enemy in self.enemies.values():
            ai.perceive(enemy, self.players, dt)
            self._move_enemy(enemy, dt, blocked, danger)

    def _move_enemy(self, enemy: Enemy, dt: float, blocked: set[Cell], danger: set[Cell]) -> None:
        if enemy.wait > 0:
            enemy.wait -= dt
            return
        # впереди внезапно появилась бомба — разворачиваемся
        if enemy.target is not None and enemy.target in blocked and enemy.target != enemy.cell:
            back = enemy.came_from
            enemy.came_from = enemy.target
            enemy.target = back if back is not None and back not in blocked else None
        if enemy.target is None:
            here = enemy.cell
            if (enemy.x, enemy.y) != here:
                enemy.target = here      # сначала встать ровно в центр клетки
            else:
                step = ai.choose_step(enemy, self.board, blocked, danger, self.rng)
                if step is None:
                    enemy.wait = ENEMY_REST
                    return
                enemy.came_from, enemy.target = here, step
                enemy.heading = (step[0] - here[0], step[1] - here[1])
        tx, ty = enemy.target
        dx, dy = tx - enemy.x, ty - enemy.y
        length = math.hypot(dx, dy)
        distance = enemy.speed * dt
        if length <= distance:
            enemy.x, enemy.y, enemy.target = float(tx), float(ty), None
        else:
            enemy.x += dx / length * distance
            enemy.y += dy / length * distance

    # ------------------------------------------------------------------ столкновения и конец уровня

    def _check_hits(self) -> None:
        fire: dict[Cell, int] = {}      # клетка в огне → чья бомба
        close: set[Cell] = set()        # клетки вплотную к бомбе (сама бомба и соседние)
        for flame in self.flames:
            fire.setdefault(flame.cell, flame.owner)
            if flame.kind == "near":
                close.add(flame.cell)
        if fire:
            for player in self.players:
                hit = touched_cells(player.x, player.y, HITBOX) & fire.keys()
                if player.active and hit:
                    killer = fire.get(player.cell, fire[min(hit)])
                    self._kill(player, epic=player.cell in close, cause="bomb", killer=killer)
            for enemy in list(self.enemies.values()):
                hit = touched_cells(enemy.x, enemy.y, HITBOX) & fire.keys()
                if hit:
                    owner = self.players[fire[min(hit)]]
                    points = ENEMY_SCORES[enemy.tier]
                    del self.enemies[enemy.id]
                    self._add_score(owner, points)
                    self._emit("enemy_killed", id=enemy.id, x=round(enemy.x, 3), y=round(enemy.y, 3),
                               tier=enemy.tier, player=owner.index, score=points)
                    if not self.enemies:
                        doors = [i for i in self.items.values() if i.kind == "door" and i.burned]
                        self._emit("all_enemies_killed", door_unlocked=bool(doors),
                                   x=doors[0].cell[0] if doors else None, y=doors[0].cell[1] if doors else None)
        for player in self.players:
            if player.active and any(
                math.hypot(player.x - e.x, player.y - e.y) < ENEMY_TOUCH_DISTANCE for e in self.enemies.values()
            ):
                self._kill(player, epic=False, cause="enemy")

    def _check_level_end(self) -> None:
        if any(p.state in ("alive", "dying") for p in self.players):
            return
        self.result = "next" if any(p.state == "exited" for p in self.players) else "retry"
        self._set_phase("level_done")
        self._emit("level_done", result=self.result)

    def _finish_level(self) -> None:
        if all(p.lives == 0 for p in self.players):
            self._set_phase("game_over")
            self._emit("game_over", level=self.level, score=self.total_score)
            return
        if self.result == "next":
            self.level += 1
        self._start_level()

    # ------------------------------------------------------------------ для браузера

    @staticmethod
    def _look(enemy: Enemy) -> list[float]:
        """Куда смотрят глаза врага: на игрока, если гонится, иначе — куда идёт."""
        if enemy.chasing and enemy.last_seen is not None:
            dx, dy = enemy.last_seen[0] - enemy.x, enemy.last_seen[1] - enemy.y
        else:
            dx, dy = enemy.heading
        length = math.hypot(dx, dy)
        return [round(dx / length, 2), round(dy / length, 2)] if length > 1e-6 else [0.0, 0.0]

    @property
    def total_score(self) -> int:
        return sum(p.score for p in self.players)

    def snapshot(self) -> dict:
        """Всё, что нужно браузеру, чтобы нарисовать текущий кадр. События отдаются один раз."""
        events, self.events = self.events, []
        r = lambda v: round(v, 3)  # noqa: E731 — хватит тысячных долей клетки
        return {
            "type": "state",
            "phase": self.phase,
            "level": self.level,
            "result": self.result,
            "grid": self.board.encode(),
            "players": [
                {
                    "index": p.index,
                    "name": p.name,
                    "x": r(p.x),
                    "y": r(p.y),
                    "facing": p.facing,
                    "moving": p.moving,
                    "state": p.state,
                    "death": p.death_kind,
                    "lives": p.lives,
                    "score": p.score,
                    "bombs": max(0, p.capacity - self._bombs_of(p.index)),
                }
                for p in self.players
            ],
            "enemies": [
                {"id": e.id, "x": r(e.x), "y": r(e.y), "tier": e.tier, "chasing": e.chasing, "look": self._look(e)}
                for e in self.enemies.values()
            ],
            "bombs": [
                {"id": b.id, "x": b.cell[0], "y": b.cell[1], "owner": b.owner, "progress": r(1 - b.fuse / b.total)}
                for b in self.bombs.values()
            ],
            "flames": [{"x": f.cell[0], "y": f.cell[1], "kind": f.kind} for f in self.flames],
            "items": [
                {"id": i.id, "x": i.cell[0], "y": i.cell[1], "kind": i.kind, "locked": self._door_locked(i)}
                for i in self.items.values()
            ],
            "events": events,
        }
