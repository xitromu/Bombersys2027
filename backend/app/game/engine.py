"""Игровой движок: один объект Game — одна партия от первого уровня до GAME OVER.

Сервер 30 раз в секунду вызывает update(dt), а между вызовами передаёт нажатия клавиш
(set_direction, place_bomb, revive, toggle_pause). После каждого update браузер получает
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

from . import ai, snake
from .board import EMPTY, PILLAR, WALL, Board, Cell
from .config import (
    BLAST_RADIUS,
    BOMB_BONUS_OVERFLOW_SCORE,
    BOMB_FUSE,
    BURNED_LIFE_ENEMIES,
    BURNED_LIFE_PAUSE,
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
    NORMAL_DEATH,
    PICKUP_DISTANCE,
    PLAYER_SPEED,
    READY_TIME,
    REVIVE_COST,
    REVIVE_SHIELD,
    SNAKE_LENGTH,
    SNAKE_REMAINS,
    SNAKE_SCORE_FACTOR,
    SPAWNS,
    START_BOMBS,
    START_FACING,
    SUPER_DEATH_IN_PLACE,
    SUPER_DEATHS,
)
from .difficulty import enemy_stats, for_level
from .entities import Bomb, Enemy, Flame, Item, Nest, Player
from .movement import DIRECTIONS, move_on_grid, touched_cells

COINS = ("bag", "bigbag", "gems")
DOOR_MIN_DISTANCE = 6       # дверь прячем подальше от стартовых углов
ENEMY_SPAWN_DISTANCE = 6    # и врагов тоже ставим подальше
SNAKE_TAIL_DISTANCE = 3     # тело змеи при появлении лежит не ближе к стартовым углам
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
        self.nests: list[Nest] = []
        self.at_locked_door: set[int] = set()
        self.result = None
        for player in self.players:
            if player.lives > 0:
                self._stand_up(player)
            else:
                player.state = "out"
        self.enemies = self._spawn_enemies()
        self._set_phase("ready")
        self._emit("level_start", level=self.level)

    @staticmethod
    def _stand_up(player: Player) -> None:
        """Герой встаёт в своём углу: в начале уровня и когда его воскресил напарник."""
        sx, sy = SPAWNS[player.index]
        player.x, player.y = float(sx), float(sy)
        player.state, player.state_time, player.shield = "alive", 0.0, 0.0
        player.facing = START_FACING[player.index]
        player.wanted, player.moving = None, False
        player.death_kind, player.death_anim, player.death_cause, player.remains = None, None, None, None

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
        spare = [c for c in candidates if c not in cells]
        for number, cell in enumerate(cells):
            enemy = self._new_enemy(cell, strong=number < self.settings.strong_enemies)
            if number >= len(cells) - self.settings.snakes:
                enemy.kind = "snake"
                self._lay_snake(enemy, spare)
            enemies[enemy.id] = enemy
        return enemies

    def _lay_snake(self, enemy: Enemy, spare: list[Cell]) -> None:
        """Змея появляется сразу во всю длину: тело лежит в свободных клетках позади головы.

        Если у её клетки места для тела нет, перебирается на запасную клетку, где оно есть."""
        self.rng.shuffle(spare)
        for head in [enemy.cell, *spare]:
            tail = self._room_behind([head])
            if tail:
                if head in spare:
                    spare.remove(head)
                enemy.x, enemy.y = float(head[0]), float(head[1])
                enemy.trail = [(float(x), float(y)) for x, y in tail]
                enemy.came_from = tail[0]
                enemy.heading = (head[0] - tail[0][0], head[1] - tail[0][1])
                return

    def _room_behind(self, chain: list[Cell]) -> list[Cell] | None:
        """Цепочка соседних свободных клеток, на которую ляжет тело змеи, — от шеи к хвосту (chain[0] — голова)."""
        if len(chain) > math.ceil(SNAKE_LENGTH):
            return chain[1:]
        ways = [c for c in self.board.neighbors(chain[-1]) if self.board.is_floor(c) and c not in chain
                and all(_manhattan(c, s) >= SNAKE_TAIL_DISTANCE for s in SPAWNS)]
        self.rng.shuffle(ways)
        for cell in ways:
            found = self._room_behind([*chain, cell])
            if found:
                return found
        return None

    def _new_enemy(self, cell: Cell, strong: bool = False) -> Enemy:
        stats = enemy_stats(self.settings, strong=strong)
        return Enemy(next(self._ids), float(cell[0]), float(cell[1]), stats.tier, stats.speed, sight=stats.sight,
                     smart=stats.smart, memory=stats.memory, avoid_danger=stats.avoid_danger)

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
        self._emit("bomb_placed", player=index, x=cell[0], y=cell[1])

    def revive(self, index: int) -> None:
        """Герой index воскрешает погибшего напарника: тратит свою жизнь, и напарник тут же встаёт в своём углу.

        Работает в любом раунде, пока своих жизней хватает (последнюю отдать нельзя). У напарника, оставшегося
        без жизней, отданная жизнь становится единственной. Первые секунды воскрешённого ничто не берёт:
        в углу его может ждать враг или огонь."""
        if not 0 <= index < len(self.players):
            return
        player = self.players[index]
        partner = self._revivable(player)
        if partner is None:
            return
        player.lives -= REVIVE_COST
        partner.lives = max(partner.lives, 1)
        self._stand_up(partner)
        partner.shield = REVIVE_SHIELD
        self._emit("player_revived", player=partner.index, by=index, x=round(partner.x), y=round(partner.y))

    def _revivable(self, player: Player) -> Player | None:
        """Кого player может воскресить прямо сейчас: погибшего напарника — или никого."""
        if self.phase != "playing" or len(self.players) < 2 or not player.active or player.lives <= REVIVE_COST:
            return None
        partner = self.players[1 - player.index]
        return partner if partner.state in ("dead", "out") else None

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
                player.shield = max(0.0, player.shield - dt)
                self._move_player(player, dt)
            elif player.state == "dying":
                player.state_time += dt
                if player.state_time >= DEATH_TIME:
                    player.state = "dead"
        self._pick_items()
        self._tick_bombs(dt)
        self._tick_flames(dt)
        self._tick_enemies(dt)
        self._check_hits()
        self._check_level_end()

    # ------------------------------------------------------------------ игроки

    def _bombs_of(self, index: int) -> int:
        return sum(1 for b in self.bombs.values() if b.owner == index)

    def _move_player(self, player: Player, dt: float) -> None:
        player.moving = False
        if player.wanted is None:
            return
        # Повернул раньше, чем дошёл до прохода, — продолжаем идти по прежней клавише,
        # а как только проход появится, свернём в него сами.
        for direction in (player.wanted, player.wanted_alt):
            if direction is None:
                continue
            # бомбы героям не преграда: мимо невзорвавшейся можно пробежать (врагов бомба останавливает)
            x, y = move_on_grid(player.x, player.y, direction, PLAYER_SPEED * dt, self.board.is_floor)
            if (x, y) != (player.x, player.y):
                player.x, player.y, player.facing, player.moving = x, y, direction, True
                return
        player.facing = player.wanted

    def _door_locked(self, item: Item) -> bool:
        """Взорванная дверь пускает, только когда убиты все враги."""
        return item.kind == "door" and item.burned and self._enemies_remain()

    def _enemies_remain(self) -> bool:
        """Враги ещё есть: на поле или те, что вот-вот выйдут из взорванной «жизни»."""
        return bool(self.enemies) or bool(self.nests)

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
        cause — от чего: "bomb", "enemy", "snake" или "trap"; killer — чья бомба убила (None — враг или ловушка)."""
        if player.shield > 0:           # только что воскрешён — пока неуязвим
            return
        player.state, player.state_time = "dying", 0.0
        player.death_cause = cause
        player.wanted, player.moving = None, False
        player.lives = max(0, player.lives - 1)
        player.capacity = START_BOMBS
        player.death_kind = "super" if epic else "normal"
        player.death_anim = self._fall(player) if epic else NORMAL_DEATH
        # что останется от съеденного змеёй, тоже решает сервер: оба игрока должны увидеть одно и то же
        player.remains = self.rng.choice(SNAKE_REMAINS) if cause == "snake" else None
        self._emit("player_died", player=player.index, kind=player.death_kind, cause=cause, killer=killer)

    def _fall(self, player: Player) -> str:
        """Как героя швыряет взрыв. Решает сервер: в игре по сети оба игрока должны увидеть одно и то же.

        Отбросить назад можно только на свободную клетку: на стене, колонне и за краем поля телу лежать негде,
        а на бонус или дверь тело не кладём — тогда героя подбрасывает на месте."""
        dx, dy = DIRECTIONS[player.facing]
        x, y = player.cell
        back = (x - dx, y - dy)
        free = self.board.is_floor(back) and all(item.cell != back for item in self.items.values())
        return self.rng.choice(SUPER_DEATHS) if free else SUPER_DEATH_IN_PLACE

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
            was_wall = self.board.get(cell) == WALL
            self.flames.append(Flame(cell, kind, FLAME_TIME, bomb.owner, bomb.id, wall=was_wall))
            if was_wall:
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
                if item.kind == "life":      # взорвали «жизнь» — из этого места выйдут новые враги
                    self.nests.append(Nest(item.cell, BURNED_LIFE_ENEMIES))
                    self._emit("life_burned", x=x, y=y, enemies=BURNED_LIFE_ENEMIES)
            elif not item.burned:
                item.burned = True
                if self._enemies_remain():
                    self._emit("door_locked", x=x, y=y)

    def _danger_cells(self) -> set[Cell]:
        cells = {f.cell for f in self.flames}
        for bomb in self.bombs.values():
            cells.update(c for c, _ in blast_cells(self.board, bomb.cell))
        return cells

    # ------------------------------------------------------------------ враги

    def _release_enemies(self, dt: float) -> None:
        """Из мест взорванной «жизни» по одному выходят новые враги — как только там погас огонь."""
        burning = {f.cell for f in self.flames}
        for nest in self.nests:
            if nest.cell in burning:
                continue
            nest.wait -= dt
            if nest.wait <= 0:
                enemy = self._new_enemy(nest.cell)
                ways = [c for c in self.board.neighbors(nest.cell) if self.board.is_floor(c)]
                if ways:   # каждый следующий смотрит в свою сторону — расходятся веером
                    way = ways[nest.left % len(ways)]
                    enemy.heading = (way[0] - nest.cell[0], way[1] - nest.cell[1])
                self.enemies[enemy.id] = enemy
                nest.left -= 1
                nest.wait = BURNED_LIFE_PAUSE
                self._emit("enemy_released", id=enemy.id, x=nest.cell[0], y=nest.cell[1], tier=enemy.tier)
        self.nests = [n for n in self.nests if n.left > 0]

    def _tick_enemies(self, dt: float) -> None:
        self._release_enemies(dt)
        # Стена сгорела, но на её месте ещё горит огонь: для врагов проход закрыт, пока не погаснет.
        # Иначе тот, кто стоял за стеной, сразу шагал в пламя и гиб, хотя взрыв до него не достал.
        blocked = {b.cell for b in self.bombs.values()} | {f.cell for f in self.flames if f.wall}
        danger = self._danger_cells() if (self.bombs or self.flames) else set()
        for enemy in self.enemies.values():
            ai.perceive(enemy, self.players, dt)
            self._move_enemy(enemy, dt, blocked, danger)

    def _move_enemy(self, enemy: Enemy, dt: float, blocked: set[Cell], danger: set[Cell]) -> None:
        if enemy.wait > 0:
            enemy.wait -= dt
            return
        is_snake = enemy.kind == "snake"
        # впереди внезапно появилась бомба — разворачиваемся
        if enemy.target is not None and enemy.target in blocked and enemy.target != enemy.cell:
            if is_snake:   # голова поворачивает назад и ползёт вдоль своего тела — разворот петлёй
                snake.fold(enemy)
            back = enemy.came_from
            enemy.came_from = enemy.target
            enemy.target = back if back is not None and back not in blocked else None
        if enemy.target is None:
            here = enemy.cell
            if (enemy.x, enemy.y) != here:
                enemy.target = here      # сначала встать ровно в центр клетки
            else:
                closed = blocked
                if is_snake and snake.behind(enemy) is not None:
                    closed = blocked | {snake.behind(enemy)}      # за головой лежит её собственное тело
                step = ai.choose_step(enemy, self.board, closed, danger, self.rng)
                if step is None and is_snake:
                    # тупик: голова поворачивает в клетку за собой и ползёт вдоль своего тела — разворот петлёй
                    back = snake.behind(enemy)
                    dead_end = not any(self.board.is_floor(c) and c not in closed for c in self.board.neighbors(here))
                    if dead_end and back is not None and self.board.is_floor(back) and back not in blocked:
                        step = back
                if step is None:
                    enemy.wait = ENEMY_REST
                    return
                enemy.came_from, enemy.target = here, step
                enemy.heading = (step[0] - here[0], step[1] - here[1])
                if is_snake:
                    snake.leave_cell(enemy, here)
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
                hit = self._enemy_cells(enemy) & fire.keys()
                if hit:
                    owner = self.players[fire[min(hit)]]
                    is_snake = enemy.kind == "snake"
                    points = ENEMY_SCORES[enemy.tier] * (SNAKE_SCORE_FACTOR if is_snake else 1)
                    del self.enemies[enemy.id]
                    self._add_score(owner, points)
                    self._emit("enemy_killed", id=enemy.id, x=round(enemy.x, 3), y=round(enemy.y, 3),
                               tier=enemy.tier, player=owner.index, score=points, kind=enemy.kind,
                               body=self._body_for_browser(enemy) if is_snake else [])
                    if not self._enemies_remain():
                        doors = [i for i in self.items.values() if i.kind == "door" and i.burned]
                        self._emit("all_enemies_killed", door_unlocked=bool(doors),
                                   x=doors[0].cell[0] if doors else None, y=doors[0].cell[1] if doors else None)
        for player in self.players:
            for enemy in self.enemies.values():
                if player.active and any(
                    math.hypot(player.x - x, player.y - y) < ENEMY_TOUCH_DISTANCE for x, y in self._enemy_points(enemy)
                ):
                    self._kill(player, epic=False, cause="snake" if enemy.kind == "snake" else "enemy")

    @staticmethod
    def _enemy_points(enemy: Enemy) -> list[tuple[float, float]]:
        """Точки, касание которых губит героя: у змеи — вдоль всего тела."""
        return snake.body(enemy, 0.25) if enemy.kind == "snake" else [(enemy.x, enemy.y)]

    @staticmethod
    def _enemy_cells(enemy: Enemy) -> set[Cell]:
        """Клетки, которые задевает враг. Змею огонь достаёт в любой части тела."""
        if enemy.kind != "snake":
            return touched_cells(enemy.x, enemy.y, HITBOX)
        cells: set[Cell] = set()
        for x, y in snake.body(enemy, 0.5):
            cells |= touched_cells(x, y, HITBOX)
        return cells

    @staticmethod
    def _body_for_browser(enemy: Enemy) -> list[list[float]]:
        """Тело змеи без головы: точки через четверть клетки, от шеи к кончику хвоста."""
        return [[round(x, 3), round(y, 3)] for x, y in snake.body(enemy, 0.25)[1:]]

    @staticmethod
    def _path_for_browser(enemy: Enemy) -> list[list[float]]:
        """Ломаная вдоль змеи от головы к кончику хвоста: по ней браузер рисует тело лентой."""
        return [[round(x, 3), round(y, 3)] for x, y in snake.path(enemy)]

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
                    "death_anim": p.death_anim,
                    "cause": p.death_cause,
                    "remains": p.remains,
                    "lives": p.lives,
                    "score": p.score,
                    "bombs": max(0, p.capacity - self._bombs_of(p.index)),
                    "can_revive": self._revivable(p) is not None,   # может воскресить напарника прямо сейчас
                    "shield": p.shield > 0,                         # неуязвим после воскрешения: на экране мигает
                }
                for p in self.players
            ],
            "enemies": [
                {"id": e.id, "x": r(e.x), "y": r(e.y), "tier": e.tier, "chasing": e.chasing, "look": self._look(e),
                 "kind": e.kind, "path": self._path_for_browser(e) if e.kind == "snake" else []}
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
