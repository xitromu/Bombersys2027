import random

from app.game.board import EMPTY, PILLAR, PILLAR_PATTERNS, PILLAR_PATTERN_SEQUENCE, WALL, Board
from app.game.config import GRID, SPAWNS
from app.game.difficulty import for_level
from app.game.engine import Game
from app.game.movement import move_on_grid


def assert_connected_ignoring_walls(board):
    """Разрушаемые стены рано или поздно откроются, поэтому здесь препятствуют только колонны."""
    pillars = set(board.cells_of(PILLAR))
    seen = set()
    stack = [(0, 0)]
    while stack:
        cell = stack.pop()
        if cell in seen or cell in pillars:
            continue
        seen.add(cell)
        stack.extend(board.neighbors(cell))
    assert seen == {(x, y) for y in range(GRID) for x in range(GRID)} - pillars


def test_generated_board_has_free_corners_and_connected_field():
    keep = {(0, 0), (1, 0), (0, 1), (14, 14), (13, 14), (14, 13)}
    board = Board.generate(random.Random(5), walls=40, keep_free=keep)
    assert len(board.cells_of(PILLAR)) == 49
    assert len(board.cells_of(WALL)) == 40
    assert all(board.get(c) == EMPTY for c in keep)
    assert len(board.encode()) == GRID * GRID
    assert_connected_ignoring_walls(board)


def test_pillar_patterns_are_symmetric_and_connected():
    for name, pillars in PILLAR_PATTERNS.items():
        board = Board.empty(name)
        assert set(board.cells_of(PILLAR)) == pillars, name
        for y in range(GRID):
            for x in range(GRID):
                assert (board.get((x, y)) == PILLAR) == (board.get((GRID - 1 - x, GRID - 1 - y)) == PILLAR), name
        assert_connected_ignoring_walls(board)


def test_bastions_have_central_five_cell_cross():
    board = Board.empty("bastions")
    center = GRID // 2
    assert all(board.get((center, y)) == PILLAR for y in range(5, 10))
    assert all(board.get((x, center)) == PILLAR for x in range(5, 10))
    assert all(board.get((center, y)) == EMPTY for y in [*range(5), *range(10, GRID)])
    assert all(board.get((x, center)) == EMPTY for x in [*range(5), *range(10, GRID)])


def test_odd_levels_cycle_through_six_symmetric_patterns():
    for level in range(1, 25, 2):
        game = Game(players=1, rng=random.Random(level), level=level)
        expected = PILLAR_PATTERN_SEQUENCE[((level - 1) // 2) % len(PILLAR_PATTERN_SEQUENCE)]
        assert set(game.board.cells_of(PILLAR)) == PILLAR_PATTERNS[expected], (level, expected)
    assert set(PILLAR_PATTERN_SEQUENCE) == set(PILLAR_PATTERNS)
    assert len(PILLAR_PATTERN_SEQUENCE) == 6


def test_even_levels_have_walls_like_in_060():
    """Каждый второй уровень — поле как в 0.6.0: шахматные колонны и столько же стен наугад."""
    keep = set()
    for sx, sy in SPAWNS:
        keep |= {(sx, sy), (sx + (1 if sx == 0 else -1), sy), (sx, sy + (1 if sy == 0 else -1))}
    for level in range(2, 13, 2):
        game = Game(players=1, rng=random.Random(100 + level), level=level)
        old = Board.generate(random.Random(100 + level), for_level(level, 1).walls, keep)
        assert game.board.encode() == old.encode(), level
        assert len(game.board.cells_of(WALL)) == for_level(level, 1).walls


def test_layouts_preserve_selected_pattern_and_connected_core():
    keep = {(0, 0), (1, 0), (0, 1), (14, 14), (13, 14), (14, 13)}
    for layout in ("random", "corridor", "island", "spiral"):
        for name, pillars in PILLAR_PATTERNS.items():
            for seed in range(4):
                board = Board.with_layout(random.Random(seed), walls=70, keep_free=keep, layout=layout, pattern=name)
                assert set(board.cells_of(PILLAR)) == pillars, (layout, name)
                assert all(board.get(cell) == EMPTY for cell in keep), (layout, name)
                assert_connected_ignoring_walls(board)


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
