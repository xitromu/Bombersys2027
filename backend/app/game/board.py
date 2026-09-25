"""Игровое поле: пол, разрушаемые стены и несгораемые колонны.

В оригинале это была матрица char Matrix[15][15] с кодами 10/80/90/99.
Здесь — сетка символов: "." пол, "w" стена, "#" колонна.
"""

from __future__ import annotations

import random

from .config import GRID

EMPTY, WALL, PILLAR = ".", "w", "#"
Cell = tuple[int, int]  # (x, y) — столбец и строка

NEIGHBOR_STEPS = ((-1, 0), (1, 0), (0, -1), (0, 1))


class Board:
    def __init__(self, cells: list[list[str]]):
        self.cells = cells  # cells[y][x]

    @staticmethod
    def is_pillar_cell(x: int, y: int) -> bool:
        """Колонны стоят в шахматном порядке: на нечётных строках и столбцах."""
        return x % 2 == 1 and y % 2 == 1

    @classmethod
    def empty(cls) -> Board:
        return cls([[PILLAR if cls.is_pillar_cell(x, y) else EMPTY for x in range(GRID)] for y in range(GRID)])

    @classmethod
    def generate(cls, rng: random.Random, walls: int, keep_free: set[Cell]) -> Board:
        """Случайно расставляет стены, не трогая клетки из keep_free (углы игроков)."""
        board = cls.empty()
        candidates = [
            (x, y)
            for y in range(GRID)
            for x in range(GRID)
            if board.get((x, y)) == EMPTY and (x, y) not in keep_free
        ]
        for cell in rng.sample(candidates, min(walls, len(candidates))):
            board.set(cell, WALL)
        return board

    @classmethod
    def from_rows(cls, rows: list[str]) -> Board:
        """Для тестов: поле из строк вида "..w#."."""
        return cls([list(row) for row in rows])

    @staticmethod
    def inside(cell: Cell) -> bool:
        x, y = cell
        return 0 <= x < GRID and 0 <= y < GRID

    def get(self, cell: Cell) -> str:
        x, y = cell
        return self.cells[y][x]

    def set(self, cell: Cell, value: str) -> None:
        x, y = cell
        self.cells[y][x] = value

    def is_floor(self, cell: Cell) -> bool:
        return self.inside(cell) and self.get(cell) == EMPTY

    def cells_of(self, kind: str) -> list[Cell]:
        return [(x, y) for y in range(GRID) for x in range(GRID) if self.cells[y][x] == kind]

    def neighbors(self, cell: Cell) -> list[Cell]:
        x, y = cell
        return [(x + dx, y + dy) for dx, dy in NEIGHBOR_STEPS if self.inside((x + dx, y + dy))]

    def encode(self) -> str:
        """Всё поле одной строкой из 225 символов — так его удобно отправлять в браузер."""
        return "".join("".join(row) for row in self.cells)
