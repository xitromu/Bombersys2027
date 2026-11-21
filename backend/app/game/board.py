"""Игровое поле: пол, разрушаемые стены и несгораемые колонны.

В оригинале это была матрица char Matrix[15][15] с кодами 10/80/90/99.
Здесь — сетка символов: "." пол, "w" стена, "#" колонна.

Планировка: с 5-го уровня (не босс) поле собирается по одной из схем — «сквозной коридор»,
«арена с островом», «лабиринт-улитка» или наугад, как раньше. У каждой схены свой характер:
где убегать воришке, что кроту рыть, где игроку закрываться.
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
    def with_layout(cls, rng: random.Random, walls: int, keep_free: set[Cell], layout: str) -> Board:
        """Поле по имени планировки; 'random' и неизвестные имена — старый наугад."""
        makers = {"corridor": cls._layout_corridor, "island": cls._layout_island, "spiral": cls._layout_spiral}
        maker = makers.get(layout)
        return maker(rng, walls, keep_free) if maker else cls.generate(rng, walls, keep_free)

    @classmethod
    def _layout_corridor(cls, rng: random.Random, walls: int, keep_free: set[Cell]) -> Board:
        """«Сквозной коридор»: широкая кишка через всё поле — длинная погоня без тупиков,
        а по бокам — глухие комнаты: воришке есть где прятать добычу, кроту — что вскрывать."""
        board = cls.empty()
        y0 = rng.choice((5, 6, 7, 8))
        band = {(x, y) for x in range(GRID) for y in (y0, y0 + 1)}
        pool = [c for c in cls.empty().cells_of(EMPTY) if c not in keep_free and c not in band]
        for cell in rng.sample(pool, min(walls, len(pool))):
            board.set(cell, WALL)
        return board

    @classmethod
    def _layout_island(cls, rng: random.Random, walls: int, keep_free: set[Cell]) -> Board:
        """«Арена с островом»: в центре — квадрат из стен с четырьмя входами,
        дверь и бонусы чаще всего прячутся именно там. Крот отрезает остров от мостиков."""
        board = cls.empty()
        island = [(x, y) for y in range(5, 10) for x in range(5, 10) if not cls.is_pillar_cell(x, y)]
        for cell in island:
            board.set(cell, WALL)
        gates = [(6, 5), (8, 5), (6, 9), (8, 9)]          # проходы внутрь острова
        for cell in gates:
            board.set(cell, EMPTY)
        made = len(island) - len(gates)
        pool = [c for c in cls.empty().cells_of(EMPTY) if c not in keep_free and board.get(c) == EMPTY]
        for cell in rng.sample(pool, min(max(walls - made, 0), len(pool))):
            board.set(cell, WALL)
        return board

    @classmethod
    def _layout_spiral(cls, rng: random.Random, walls: int, keep_free: set[Cell]) -> Board:
        """«Лабиринт-улитка»: спираль валов от краёв к центру, между валами — по проходу.
        Кемпиться негде: коридоры длинные, а крот прорубает прямые ходы через валы."""
        board = cls.empty()
        forbidden = keep_free | {(7, 7)}
        ring_walls: list[Cell] = []
        ring = 0
        while GRID - 2 * ring > 3:
            x0, x1 = ring, GRID - 1 - ring
            y0, y1 = ring, GRID - 1 - ring
            wall_cells = ([(x, y0) for x in range(x0, x1 + 1)] + [(x1, y) for y in range(y0, y1 + 1)]
                          + [(x, y1) for x in range(x0, x1 + 1)] + [(x0, y) for y in range(y0, y1 + 1)])
            wall_cells = [c for c in dict.fromkeys(wall_cells) if c not in forbidden and not cls.is_pillar_cell(*c)]
            ring_walls.extend(rng.sample(wall_cells, min(len(wall_cells), max(walls // 3, 6))))
            ring += 2                   # следующий вал — через ряд, чтобы остались проходы
        # остальные стены — наугад, но не там, где уже вал
        pool = [c for c in cls.empty().cells_of(EMPTY) if c not in keep_free and c not in ring_walls]
        for cell in ring_walls + rng.sample(pool, min(max(walls - len(ring_walls), 0), len(pool))):
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
