"""Воришка, крот, планировки поля и «пультовые» бомбы после смерти хозяина."""

import random

from app.game.board import EMPTY, WALL, Board
from app.game.config import (
    BOMB_FUSE,
    ENEMY_SCORES,
    FLAME_TIME,
    KIND_SCORE_FACTOR,
    MOLE_BURROW_TIME,
    REMOTE_DEATH_FUSE,
    THIEF_PANIC_RADIUS,
    GRID,
)
from app.game.difficulty import for_level
from app.game.engine import Game
from app.game.entities import Bomb, Enemy, Flame, Item

from .conftest import make_game, run


# ------------------------------------------------------------------ воришка

def test_thief_grabs_item_and_hides_it_under_a_wall():
    board = Board.empty()
    board.set((2, 0), WALL)                 # стена без клада — под неё и заныкает
    game = make_game(board=board)
    game.players[0].x, game.players[0].y = 14.0, 14.0
    thief = game._new_enemy((0, 0), kind="thief")
    game.enemies = {thief.id: thief}
    game.items = {1: Item(1, (0, 0), "chest")}

    run(game, 0.2)
    assert thief.loot == 1                  # схватил бонус
    assert any(e["type"] == "loot_grabbed" for e in game.events)
    assert not any(i["id"] == 1 for i in game.snapshot()["items"])   # с поля пропал

    run(game, 4.0)
    assert thief.loot is None               # заныкал
    assert game.hidden.get((2, 0)) == "chest"
    assert any(e["type"] == "loot_hidden" for e in game.events)
    run(game, 2.0)                          # спрятанный бонус достаётся только взрывом стены
    assert game.board.get((2, 0)) == WALL


def test_thief_does_not_overwrite_hidden_door():
    board = Board.empty()
    board.set((2, 0), WALL)
    game = make_game(board=board)
    game.players[0].x, game.players[0].y = 14.0, 14.0
    game.hidden = {(2, 0): "door"}          # под этой стеной дверь — её трогать нельзя
    thief = game._new_enemy((0, 0), kind="thief")
    game.enemies = {thief.id: thief}
    game.items = {1: Item(1, (0, 0), "chest")}
    run(game, 6.0)
    assert game.hidden.get((2, 0)) == "door"   # дверь цела
    assert thief.loot == 1                     # …а воришка так и несёт добычу дальше


def test_thief_panics_near_player_and_drops_the_loot():
    game = make_game(board=Board.empty())
    thief = game._new_enemy((7, 7), kind="thief")
    game.enemies = {thief.id: thief}
    game.items = {1: Item(1, (7, 7), "gems")}
    game.players[0].x, game.players[0].y = 10.0, 7.0   # далеко: паники нет
    run(game, 0.2)
    assert thief.loot == 1                               # взял
    game.players[0].x, game.players[0].y = 8.6, 7.0    # вплотную
    run(game, 0.2)
    assert thief.loot is None                            # бросил
    assert game.items[1].carried is None
    assert any(e["type"] == "loot_dropped" for e in game.events)
    assert thief.flee > 0                                # удирает


def test_thief_is_harmless_and_drops_loot_when_killed():
    game = make_game(board=Board.empty())
    thief = game._new_enemy((0, 0), kind="thief")
    game.enemies = {thief.id: thief}
    game.items = {1: Item(1, (0, 0), "bag")}
    game.players[0].x, game.players[0].y = 0.0, 1.0   # рядом: паника, но мешок ещё не подобрал
    run(game, 0.5)
    assert game.players[0].state == "alive"     # под ногами — а героя не трогает
    assert 1 in game.items                       # мешок на месте
    game.players[0].x, game.players[0].y = 14.0, 14.0
    run(game, 6.5)                               # перестал удирать, вернулся и схватил добычу
    assert thief.loot == 1                       # схватил
    thief.wait = 5                               # держим на месте: добьём огнём
    game.flames = [Flame(thief.cell, "near", FLAME_TIME, owner=0)]
    run(game, 0.3)
    assert thief.id not in game.enemies
    dropped = game.items.get(1)
    assert dropped is None or dropped.carried is None   # добыча на поле (или сгорела), а не пропала
    assert game.players[0].score == ENEMY_SCORES[thief.tier] * KIND_SCORE_FACTOR["thief"]


# ------------------------------------------------------------------ крот

def test_mole_burrows_digs_and_eats():
    board = Board.empty()
    board.set((3, 0), WALL)                 # крот выроет эту стену
    game = make_game(board=board)
    game.players[0].x, game.players[0].y = 14.0, 14.0
    mole = game._new_enemy((2, 0), kind="mole")
    mole.cooldown = 0.05                    # ныряет почти сразу
    game.enemies = {mole.id: mole}
    game.hidden = {(3, 0): "gems"}

    run(game, 0.2)
    assert mole.burrowed > 0
    assert any(e["type"] == "mole_burrowed" for e in game.events)

    run(game, MOLE_BURROW_TIME + 0.3)
    assert board.get((3, 0)) == EMPTY                  # прорыл ход
    assert any(e["type"] == "wall_destroyed" for e in game.events)
    assert any(e["type"] == "mole_ate" for e in game.events)   # и тут же сожрал вскрытый бонус
    assert not game.items                                # бонусов не осталось


def test_mole_underground_is_harmless_and_fireproof():
    board = Board.empty()
    game = make_game(board=board)
    mole = game._new_enemy((0, 0), kind="mole")
    mole.burrowed = 5.0                     # сразу под землёй
    game.enemies = {mole.id: mole}
    game.players[0].x, game.players[0].y = 0.0, 0.0
    run(game, 0.2)
    assert game.players[0].state == "alive"            # героя под землёй не трогает

    game.players[0].x, game.players[0].y = 14.0, 14.0
    game.bombs[900] = Bomb(900, (0, 0), 0, 0.05, BOMB_FUSE)
    run(game, 0.3)
    assert mole.id in game.enemies                     # и огонь его не берёт

    mole.burrowed = 0.0                                # вынырнул — огонь того же пожара берёт
    run(game, 0.3)
    assert mole.id not in game.enemies


# ------------------------------------------------------------------ планировки

def test_layouts_generate_distinct_boards_respecting_free_corners():
    keep = {(0, 0), (1, 0), (0, 1), (14, 14), (13, 14), (14, 13)}
    boards = {name: Board.with_layout(random.Random(7), 40, keep, name)
              for name in ("random", "corridor", "island", "spiral")}
    for name, board in boards.items():
        assert all(board.get(c) == EMPTY for c in keep), name
        assert 30 <= len(board.cells_of(WALL)) <= 55, name
    # «сквозной коридор»: есть две соседние строки без единой стены
    free_rows = [y for y in range(GRID) if all(boards["corridor"].get((x, y)) != WALL for x in range(GRID))]
    assert any(b - a == 1 for a, b in zip(free_rows, free_rows[1:]))
    # «остров» — сплошные стены в центре
    assert boards["island"].get((6, 6)) == WALL and boards["island"].get((8, 8)) == WALL
    # все четыре разные
    assert len({b.encode() for b in boards.values()}) == 4


def test_layout_comes_from_level_settings():
    assert for_level(4).layout == "random"
    assert for_level(5).layout == "random"          # у босса арена
    assert for_level(6).layout == "island"
    assert for_level(7).layout == "spiral"
    game = Game(players=1, rng=random.Random(11), level=6)
    assert len(game.board.cells_of(WALL)) >= 30


# ------------------------------------------------------------------ бомбы после смерти хозяина

def test_remote_bombs_blow_two_seconds_after_owner_death():
    game = make_game(board=Board.empty())
    player = game.players[0]
    player.remote = True
    game.place_bomb(0)
    mine = next(iter(game.bombs.values()))
    assert mine.remote
    run(game, 1.0)                                     # жива — бомба молчит
    assert game.bombs

    game._kill(player, epic=False, cause="enemy")
    run(game, 1.0)                                     # прошла секунда — ещё цела
    assert game.bombs
    run(game, REMOTE_DEATH_FUSE + 0.3)                 # две секунды после смерти — взорвалась
    assert not game.bombs
    assert any(e["type"] == "explosion" and e["id"] == mine.id for e in game.events)
