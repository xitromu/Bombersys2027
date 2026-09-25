import random

from app.game import ai
from app.game.board import WALL, Board
from app.game.config import PLAYER_SPEED
from app.game.difficulty import enemy_stats, for_level
from app.game.entities import Enemy

from .conftest import make_game, run


def test_difficulty_grows_smoothly_and_never_falls():
    levels = [for_level(n) for n in range(1, 21)]
    for field in ("enemies", "enemy_speed", "sight", "smart", "memory", "avoid_danger", "walls"):
        values = [getattr(s, field) for s in levels]
        assert values == sorted(values), field
    # от уровня к уровню врагов прибавляется не больше одного
    assert all(b.enemies - a.enemies <= 1 for a, b in zip(levels, levels[1:]))


def test_enemies_always_slower_than_player():
    for n in range(1, 100):
        for strong in (False, True):
            assert enemy_stats(for_level(n), strong).speed < PLAYER_SPEED


def test_strong_enemies_are_better_and_appear_from_level_two():
    assert for_level(1).strong_enemies == 0
    assert for_level(2).strong_enemies == 1
    settings = for_level(5)
    normal, strong = enemy_stats(settings), enemy_stats(settings, strong=True)
    assert strong.tier == normal.tier + 1
    assert strong.speed > normal.speed and strong.sight > normal.sight and strong.smart > normal.smart


def test_first_levels_are_gentle():
    first = for_level(1)
    assert first.enemies == 2 and first.smart == 0 and first.sight <= 3
    assert for_level(1, players=2).enemies == 3


def test_bfs_finds_way_around_wall():
    board = Board.empty()
    board.set((0, 1), WALL)                 # прямой путь вниз закрыт
    step = ai.bfs_next_step((0, 0), (0, 2), board.is_floor, board)
    assert step == (1, 0)


def test_smart_enemy_catches_standing_player():
    game = make_game(level=12, board=Board.empty())
    game.players[0].x, game.players[0].y = 0.0, 0.0
    game.enemies = {1: Enemy(1, 8.0, 6.0, tier=3, speed=2.5, sight=9, smart=0.85, memory=4)}
    run(game, 15.0)
    assert game.players[0].state != "alive"


def test_level_one_enemy_does_not_notice_far_player():
    game = make_game(level=1, board=Board.empty())
    enemy = Enemy(1, 10.0, 10.0, tier=0, speed=1.5, sight=game.settings.sight)
    ai.perceive(enemy, game.players, 1 / 30)
    assert not enemy.chasing


def test_smart_enemy_avoids_bomb_zone():
    game = make_game(level=15, board=Board.empty())
    game.rng = random.Random(3)
    game.players[0].x, game.players[0].y = 14.0, 14.0
    enemy = Enemy(1, 0.0, 4.0, tier=3, speed=0, avoid_danger=0.9)
    danger = {(0, 3), (0, 5)}
    steps = [ai.choose_step(enemy, game.board, set(), danger, game.rng) for _ in range(200)]
    assert sum(step in danger for step in steps) < 40   # в опасную клетку идёт редко
