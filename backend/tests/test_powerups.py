"""Бонусы-механики: пульт, огонь +1, щит, сапоги. Действуют до гибели, между уровнями сохраняются."""

import random

from app.game.board import Board
from app.game.config import (
    BLAST_RADIUS,
    BOMB_BONUS_OVERFLOW_SCORE,
    BOMB_FUSE,
    BOOTS_FACTOR,
    LEVEL_END_TIME,
    MAX_RADIUS,
    MECHANIC_ITEMS,
    PLAYER_SPEED,
    START_BOMBS,
)
from app.game.engine import Game
from app.game.entities import Bomb, Item

from .conftest import make_game, run


def give(game, kind):
    game._apply_item(game.players[0], Item(777, (0, 0), kind))


def test_two_mechanic_bonuses_hide_under_walls_each_level():
    for seed in range(10):
        game = Game(players=1, rng=random.Random(seed), level=2)
        kinds = list(game.hidden.values())
        assert sum(k in MECHANIC_ITEMS for k in kinds) == 2
        assert sum(k in ("bag", "bigbag", "gems") for k in kinds) == 3
        assert kinds.count("door") == 1


# ------------------------------------------------------------------ пульт

def test_remote_bomb_waits_for_the_key():
    game = make_game(board=Board.empty())
    player = game.players[0]
    give(game, "remote")
    game.place_bomb(0)
    player.x, player.y = 6.0, 0.0
    run(game, BOMB_FUSE + 0.5)
    assert len(game.bombs) == 1                     # фитиль не тикает
    assert game.snapshot()["bombs"][0]["remote"]
    game.detonate(0)
    assert not game.bombs
    assert any(e["type"] == "explosion" for e in game.events)
    assert player.state == "alive"


def test_detonate_without_the_bonus_does_nothing():
    game = make_game(board=Board.empty())
    game.place_bomb(0)
    game.players[0].x = 6.0
    game.detonate(0)
    assert len(game.bombs) == 1
    run(game, BOMB_FUSE + 0.2)
    assert not game.bombs                           # обычная бомба рвётся по фитилю


def test_detonate_pops_the_earliest_bomb_first():
    game = make_game(board=Board.empty())
    player = game.players[0]
    give(game, "remote")
    game.place_bomb(0)                              # бомба в (0,0)
    player.x = 6.0                                  # подальше: чтобы взрыв первой не поджёг вторую
    game.place_bomb(0)                              # бомба в (6,0)
    player.x = 12.0
    game.detonate(0)
    assert [b.cell for b in game.bombs.values()] == [(6, 0)]
    game.detonate(0)
    assert not game.bombs


def test_chain_reaction_ignites_remote_bombs():
    game = make_game(board=Board.empty())
    player = game.players[0]
    give(game, "remote")
    game.place_bomb(0)
    player.x = 2.0
    game.place_bomb(0)
    player.x = 8.0
    game.detonate(0)                                # первая рвётся, вторая подожжена
    run(game, 0.5)
    assert not game.bombs                           # вторая не стала ждать клавишу


# ------------------------------------------------------------------ огонь +1

def test_fire_bonus_grows_the_cross_up_to_four():
    game = make_game(board=Board.empty())
    player = game.players[0]
    assert player.radius == BLAST_RADIUS
    give(game, "fire")
    assert player.radius == BLAST_RADIUS + 1
    give(game, "fire")
    assert player.radius == MAX_RADIUS
    score = player.score
    give(game, "fire")                              # уже предел — деньгами
    assert player.radius == MAX_RADIUS and player.score == score + BOMB_BONUS_OVERFLOW_SCORE


def test_bigger_cross_really_burns_farther():
    game = make_game(board=Board.empty())
    player = game.players[0]
    player.radius = MAX_RADIUS
    game.place_bomb(0)
    player.x = 8.0
    run(game, BOMB_FUSE + 0.1)
    burning = {f.cell for f in game.flames}
    assert (4, 0) in burning                        # крест в 4 клетки достаёт до (4,0)


# ------------------------------------------------------------------ щит

def test_shield_absorbs_one_hit_then_breaks():
    game = make_game(board=Board.empty())
    player = game.players[0]
    give(game, "shield")
    game.bombs[900] = Bomb(900, (2, 0), 0, 0.05, BOMB_FUSE)
    run(game, 0.3)
    assert player.state == "alive" and not player.armor
    assert any(e["type"] == "shield_saved" for e in game.events)
    run(game, 1.0)
    game.bombs[901] = Bomb(901, (2, 0), 0, 0.05, BOMB_FUSE)
    run(game, 0.3)
    assert player.state == "dying"


def test_shield_absorbs_a_trap_too():
    game = make_game(board=Board.empty())
    give(game, "shield")
    give(game, "death")
    assert game.players[0].state == "alive" and not game.players[0].armor


# ------------------------------------------------------------------ сапоги

def test_boots_make_the_hero_faster():
    game = make_game(board=Board.empty())
    player = game.players[0]
    give(game, "boots")
    game.set_direction(0, "right")
    run(game, 0.5)
    assert abs(player.x - PLAYER_SPEED * BOOTS_FACTOR * 0.5) < 0.05


# ------------------------------------------------------------------ срок действия

def test_death_takes_all_mechanic_bonuses():
    game = make_game(board=Board.empty())
    player = game.players[0]
    for kind in MECHANIC_ITEMS:
        give(game, kind)
    player.armor = False                            # щит уже потратили — ловушка убьёт
    give(game, "death")
    assert player.state == "dying"
    assert player.capacity == START_BOMBS
    assert player.radius == BLAST_RADIUS
    assert not player.remote and not player.armor and not player.boots


def test_bonuses_survive_the_level_change():
    game = make_game(board=Board.empty())
    player = game.players[0]
    give(game, "remote")
    give(game, "fire")
    give(game, "boots")
    player.state = "exited"                         # герой ушёл в дверь — уровень пройден
    run(game, LEVEL_END_TIME + 0.2)
    assert game.level == 2
    assert player.remote and player.boots and player.radius == BLAST_RADIUS + 1


def test_duplicate_bonus_pays_coins():
    game = make_game(board=Board.empty())
    player = game.players[0]
    give(game, "remote")
    score = player.score
    give(game, "remote")
    assert player.score == score + BOMB_BONUS_OVERFLOW_SCORE