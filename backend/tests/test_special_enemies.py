"""Особые враги: броненосец, призрак, матка, подрывник, ярость последнего и босс."""

import random

from app.game import ai
from app.game.board import WALL, Board
from app.game.config import (
    BOMB_FUSE,
    BOSS_ARMOR,
    BOSS_MINIONS,
    BOSS_SCORE,
    BOSS_WALLS,
    ENEMY_BOMB_OWNER,
    ENEMY_SCORES,
    FLAME_TIME,
    KIND_SCORE_FACTOR,
    QUEEN_MAX_CHILDREN,
    QUEEN_PERIOD,
)
from app.game.difficulty import for_level
from app.game.engine import Game
from app.game.entities import Bomb, Enemy

from .conftest import make_game, run


def far_player(game):
    game.players[0].x, game.players[0].y = 14.0, 14.0


def dummy(game):
    """Второй враг подальше: чтобы «ярость последнего» не мешала проверять одного."""
    game.enemies[9999] = Enemy(9999, 14.0, 12.0, tier=0, speed=0)


def blow(game, cell, fuse=0.05):
    game.bombs[9000 + len(game.bombs)] = Bomb(9000 + len(game.bombs), cell, 0, fuse, BOMB_FUSE)


# ------------------------------------------------------------------ броненосец

def test_armored_survives_first_blast_then_dies_from_second():
    game = make_game(board=Board.empty())
    far_player(game)
    enemy = game._new_enemy((6, 0), kind="armored")
    enemy.wait = 100
    game.enemies[enemy.id] = enemy
    dummy(game)
    base_speed = enemy.speed

    blow(game, (4, 0))
    run(game, 0.3)
    assert enemy.id in game.enemies and enemy.armor == 0
    assert enemy.speed > base_speed
    assert any(e["type"] == "armor_cracked" for e in game.events)

    run(game, FLAME_TIME + 1.0)      # огонь погас, неуязвимость после панциря прошла
    blow(game, (4, 0))
    run(game, 0.3)
    assert enemy.id not in game.enemies
    assert game.players[0].score == ENEMY_SCORES[enemy.tier] * KIND_SCORE_FACTOR["armored"]


def test_one_blast_cannot_strip_two_armors():
    game = make_game(board=Board.empty())
    far_player(game)
    enemy = game._new_enemy((6, 0), kind="boss")
    enemy.wait = 100
    game.enemies[enemy.id] = enemy
    blow(game, (4, 0))
    run(game, FLAME_TIME)            # огонь горит всё время — но панцирь снимается только один
    assert enemy.armor == BOSS_ARMOR - 1


# ------------------------------------------------------------------ призрак

def test_phantom_paths_through_broken_walls_but_not_pillars():
    board = Board.empty()
    board.set((1, 0), WALL)
    game = make_game(board=board)
    phantom = game._new_enemy((0, 0), kind="phantom")
    phantom.chasing, phantom.last_seen, phantom.smart = True, (2, 0), 1.0
    step = ai.choose_step(phantom, board, set(), set(), game.rng)
    assert step == (1, 0)            # кратчайший путь — прямо сквозь стену
    board.set((1, 0), "#")           # а колонна для него всё равно преграда
    step = ai.choose_step(phantom, board, set(), set(), game.rng)
    assert step != (1, 0)


def test_phantom_half_inside_a_wall_is_harmless_and_fireproof():
    board = Board.empty()
    board.set((1, 0), WALL)
    game = make_game(board=board)
    phantom = game._new_enemy((1, 0), kind="phantom")
    phantom.x, phantom.wait = 1.4, 100      # центр ещё в стене, тело уже выглядывает наружу
    game.enemies[phantom.id] = phantom
    game.players[0].x, game.players[0].y = 1.0, 0.0   # герой вплотную к выглядывающему телу, но не в огне
    blow(game, (4, 0))                       # огонь накрывает (2,0), но не стену (1,0)
    run(game, 0.3)
    assert game.players[0].state == "alive"  # призрак в стене не трогает…
    assert phantom.id in game.enemies        # …и огонь его не берёт
    assert game.snapshot()["enemies"][0]["in_wall"]

    phantom.x = 2.0                          # выполз целиком — теперь уязвим и опасен
    run(game, 0.1)
    assert phantom.id not in game.enemies or game.players[0].state != "alive"


def test_phantom_fully_outside_dies_from_fire():
    game = make_game(board=Board.empty())
    far_player(game)
    phantom = game._new_enemy((6, 0), kind="phantom")
    phantom.wait = 100
    game.enemies[phantom.id] = phantom
    dummy(game)
    blow(game, (4, 0))
    run(game, 0.3)
    assert phantom.id not in game.enemies


# ------------------------------------------------------------------ матка

def test_queen_releases_green_children_up_to_the_limit():
    game = make_game(board=Board.empty())
    far_player(game)
    queen = game._new_enemy((6, 6), kind="queen")
    queen.wait = 1000
    game.enemies[queen.id] = queen

    run(game, QUEEN_PERIOD + 0.2)
    children = [e for e in game.enemies.values() if e.mother == queen.id]
    assert len(children) == 1 and children[0].tier == 0 and children[0].kind == "ghost"

    for _ in range(QUEEN_MAX_CHILDREN + 2):
        queen.cooldown = 0.05
        run(game, 0.1)
    children = [e for e in game.enemies.values() if e.mother == queen.id]
    assert len(children) == QUEEN_MAX_CHILDREN


def test_killing_the_queen_stops_the_stream_but_children_stay():
    game = make_game(board=Board.empty())
    far_player(game)
    queen = game._new_enemy((6, 6), kind="queen")
    queen.wait = 1000
    game.enemies[queen.id] = queen
    queen.cooldown = 0.05
    run(game, 0.1)
    child = next(e for e in game.enemies.values() if e.mother == queen.id)
    child.x, child.y, child.wait = 12.0, 12.0, 100   # уводим ребёнка подальше от взрыва

    blow(game, (4, 6))
    run(game, 0.3)
    assert queen.id not in game.enemies
    assert game.players[0].score == ENEMY_SCORES[queen.tier] * KIND_SCORE_FACTOR["queen"]
    assert child.id in game.enemies
    run(game, QUEEN_PERIOD + 0.5)
    assert len([e for e in game.enemies.values() if e.mother == queen.id]) == 1


# ------------------------------------------------------------------ подрывник

def test_bomber_places_his_own_small_bomb_and_flees():
    game = make_game(board=Board.empty())
    bomber = game._new_enemy((4, 0), kind="bomber")
    bomber.cooldown = 0.05
    game.enemies[bomber.id] = bomber
    run(game, 0.2)
    mines = [b for b in game.bombs.values() if b.owner == ENEMY_BOMB_OWNER]
    assert len(mines) == 1 and mines[0].radius == 1
    assert bomber.flee > 0
    assert any(e["type"] == "bomb_placed" and e["player"] == ENEMY_BOMB_OWNER for e in game.events)


def test_bomber_waits_while_his_two_bombs_are_out():
    game = make_game(board=Board.empty())
    bomber = game._new_enemy((4, 0), kind="bomber")
    bomber.chasing, bomber.last_seen, bomber.memory_left = True, (0, 0), 10.0
    bomber.cooldown = 0.01
    game.enemies[bomber.id] = bomber
    for cell in ((8, 0), (10, 0)):
        game.bombs[900 + cell[0]] = Bomb(900 + cell[0], cell, ENEMY_BOMB_OWNER, BOMB_FUSE, BOMB_FUSE, radius=1)
    run(game, 0.1)
    assert sum(b.owner == ENEMY_BOMB_OWNER for b in game.bombs.values()) == 2


def test_bomber_bomb_kills_enemies_without_score_and_players_without_killer():
    game = make_game(board=Board.empty())
    far_player(game)
    victim = Enemy(1, 5.0, 0.0, tier=0, speed=0)
    victim.wait = 100
    game.enemies[1] = victim
    game.bombs[900] = Bomb(900, (4, 0), ENEMY_BOMB_OWNER, 0.05, BOMB_FUSE, radius=1)
    run(game, 0.3)
    assert 1 not in game.enemies
    assert game.players[0].score == 0
    killed = next(e for e in game.events if e["type"] == "enemy_killed")
    assert killed["player"] is None and killed["score"] == 0

    game.players[0].x, game.players[0].y = 5.0, 0.0
    game.bombs[901] = Bomb(901, (4, 0), ENEMY_BOMB_OWNER, 0.05, BOMB_FUSE, radius=1)
    run(game, 0.3)
    died = next(e for e in game.events if e["type"] == "player_died")
    assert died["killer"] is None and died["cause"] == "bomb"


# ------------------------------------------------------------------ ярость последнего

def test_last_enemy_enrages():
    game = make_game(board=Board.empty())
    far_player(game)
    enemy = Enemy(1, 8.0, 8.0, tier=0, speed=1.5, sight=3)
    game.enemies = {1: enemy}
    run(game, 0.1)
    assert enemy.enraged and enemy.speed == 2.1 and enemy.sight >= 12
    assert any(e["type"] == "enemy_enraged" for e in game.events)


def test_no_frenzy_while_two_enemies_or_a_queen_remain():
    game = make_game(board=Board.empty())
    far_player(game)
    game.enemies = {1: Enemy(1, 8.0, 8.0, tier=0, speed=1.5), 2: Enemy(2, 10.0, 8.0, tier=0, speed=1.5)}
    run(game, 0.1)
    assert not any(e.enraged for e in game.enemies.values())

    game = make_game(board=Board.empty())
    far_player(game)
    queen = game._new_enemy((6, 6), kind="queen")
    game.enemies = {queen.id: queen}
    run(game, 0.1)
    assert not queen.enraged


# ------------------------------------------------------------------ босс

def test_boss_levels_are_arenas_with_a_boss_and_no_hidden_door():
    settings = for_level(5)
    assert settings.boss and settings.walls == BOSS_WALLS and settings.snakes == 0
    game = Game(players=1, rng=random.Random(3), level=5)
    kinds = [e.kind for e in game.enemies.values()]
    assert kinds.count("boss") == 1 and len(kinds) == settings.enemies + 1
    assert "door" not in game.hidden.values()
    boss = next(e for e in game.enemies.values() if e.kind == "boss")
    assert boss.armor == BOSS_ARMOR


def test_boss_takes_three_blasts_spawns_minions_and_opens_the_door():
    game = make_game(level=5, board=Board.empty())
    boss = game._new_enemy((8, 0), kind="boss")
    boss.wait = 1000
    game.enemies[boss.id] = boss

    for phase in range(BOSS_ARMOR):
        blow(game, (6, 0))
        run(game, 0.1)
        assert boss.id in game.enemies and boss.armor == BOSS_ARMOR - phase - 1
        assert any(e["type"] == "boss_phase" for e in game.events)
        for minion in game.enemies.values():        # выпущенные зубастики стоят смирно вдали — не лезут под следующий взрыв
            minion.wait = 1000
            if minion.id != boss.id:
                minion.x, minion.y = 12.0, 12.0
        run(game, FLAME_TIME + 1.0)
    minions = len(game.enemies) - 1
    assert minions == BOSS_ARMOR * BOSS_MINIONS

    blow(game, (6, 0))
    run(game, 0.3)
    assert boss.id not in game.enemies
    assert game.players[0].score == BOSS_SCORE
    assert any(e["type"] == "extra_life" for e in game.events)   # 5000 очков — сразу жизнь
    assert any(e["type"] == "door_appeared" for e in game.events)
    doors = [i for i in game.items.values() if i.kind == "door"]
    assert len(doors) == 1 and game.board.is_floor(doors[0].cell)


# ------------------------------------------------------------------ расписание

def test_special_enemies_appear_on_schedule_and_replace_ordinary_ones():
    assert for_level(5).armored == 0 and for_level(6).armored == 1
    assert for_level(6).phantoms == 0 and for_level(7).phantoms == 1
    assert for_level(7).queens == 0 and for_level(8).queens == 1
    assert for_level(8).bombers == 0 and for_level(9).bombers == 1
    assert (for_level(12).armored, for_level(13).bombers, for_level(14).phantoms) == (2, 2, 2)
    for level in range(1, 21):
        s = for_level(level)
        if not s.boss:
            assert s.snakes + s.armored + s.phantoms + s.queens + s.bombers <= s.enemies
    game = Game(players=1, rng=random.Random(5), level=9)
    kinds = [e.kind for e in game.enemies.values()]
    s = for_level(9)
    assert len(kinds) == s.enemies
    for kind, count in (("armored", s.armored), ("phantom", s.phantoms), ("queen", s.queens),
                        ("bomber", s.bombers), ("snake", s.snakes)):
        assert kinds.count(kind) == count


# ------------------------------------------------------------------ укус крупного

def test_big_eater_bites_half_torso_and_small_one_bites_head():
    for kind, half in (("boss", True), ("queen", True), ("ghost", False), ("armored", False)):
        game = make_game(board=Board.empty())
        player = game.players[0]
        player.x, player.y = 5.0, 5.0
        enemy = game._new_enemy((5, 5), kind=kind)
        enemy.wait = 100
        game.enemies[enemy.id] = enemy
        dummy(game)
        run(game, 0.1)
        assert player.state == "dying", kind
        assert player.death_half is half, kind
        assert game.snapshot()["players"][0]["half"] is half, kind