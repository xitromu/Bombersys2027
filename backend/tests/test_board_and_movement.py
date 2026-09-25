import random

from app.game.board import EMPTY, PILLAR, WALL, Board
from app.game.config import GRID
from app.game.movement import move_on_grid


def test_pillars_in_checkerboard_and_corners_free():
    keep = {(0, 0), (1, 0), (0, 1)}
    board = Board.generate(random.Random(5), walls=40, keep_free=keep)
    assert len(board.cells_of(PILLAR)) == 49
    assert len(board.cells_of(WALL)) == 40
    assert all(board.get(c) == EMPTY for c in keep)
    assert len(board.encode()) == GRID * GRID


def test_walk_along_corridor_and_stop_at_pillar():
    board = Board.empty()
    x, y = 0.0, 0.0
    for _ in range(200):
        x, y = move_on_grid(x, y, "down", 0.1, board.is_floor)
    assert (x, y) == (0.0, 14.0)
    # из (0,1) вправо — колонна (1,1): не проходим
    x, y = move_on_grid(0.0, 1.0, "right", 0.1, board.is_floor)
    assert (x, y) == (0.0, 1.0)


def test_soft_corner_forgives_big_miss():
    board = Board.empty()
    # игрок в (2.8, 0): под ним колонна (3,1), проход вниз — в столбце 2; промах 0.8 клетки прощается
    x, y = 2.8, 0.0
    for _ in range(20):
        x, y = move_on_grid(x, y, "down", 0.1, board.is_floor)
    assert x == 2.0 and y > 0.5


def test_soft_corner_pulls_player_into_passage():
    board = Board.empty()
    # игрок чуть ниже строки 2 и жмёт «вправо» — его подтягивает к оси прохода
    x, y = move_on_grid(0.0, 2.2, "right", 0.1, board.is_floor)
    assert x == 0.0 and abs(y - 2.1) < 1e-9
    x, y = move_on_grid(x, y, "right", 0.2, board.is_floor)
    assert y == 2.0
