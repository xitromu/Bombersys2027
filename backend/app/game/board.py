"""Игровое поле: пол, разрушаемые стены и несгораемые колонны.

В оригинале это была матрица char Matrix[15][15] с кодами 10/80/90/99.
Здесь — сетка символов: "." пол, "w" стена, "#" колонна.

Планировка: со 2-го уровня (не босс) поле собирается по одной из схем — «сквозной коридор»,
«арена с островом» или «лабиринт-улитка» (боссы — наугад, у них своя арена). У каждой схемы свой
характер: где убегать воришке, что кроту рыть, где игроку закрываться.
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
        """«Сквозной коридор»: две свободные строки через всё поле, а сверху и снизу — частокол
        из одинаковых блоков с проходами между ними. Длинная погоня без тупиков;
        воришке есть где прятать добычу, кроту — что вскрывать."""
        board = cls.empty()
        y0 = rng.choice((6, 7))
        band = {y0, y0 + 1}
        blocks = [(x, y) for y in range(GRID) if y not in band
                  for x in range(GRID) if x % 2 == 0 and y % 2 == 0 and (x, y) not in keep_free]
        for cell in rng.sample(blocks, min(walls, len(blocks))):
            board.set(cell, WALL)
        rest = [c for c in board.cells_of(EMPTY) if c not in keep_free and c[1] not in band]
        over = walls - min(walls, len(blocks))
        if over > 0:
            for cell in rng.sample(rest, min(over, len(rest))):
                board.set(cell, WALL)
        return board

    @classmethod
    def _layout_island(cls, rng: random.Random, walls: int, keep_free: set[Cell]) -> Board:
        """«Арена с островом»: в центре — квадрат из стен с четырьмя входами, вокруг него чистая
        арена. Дверь и бонусы чаще всего прячутся в острове. Крот отрезает остров от мостиков."""
        board = cls.empty()
        island = [(x, y) for y in range(5, 10) for x in range(5, 10) if not cls.is_pillar_cell(x, y)]
        for cell in island:
            board.set(cell, WALL)
        gates = [(6, 5), (8, 5), (6, 9), (8, 9)]          # проходы внутрь острова
        for cell in gates:
            board.set(cell, EMPTY)
        made = len(island) - len(gates)
        arena = {(x, y) for y in range(4, 11) for x in range(4, 11)}   # вокруг острова — не заваливать
        pool = [c for c in board.cells_of(EMPTY) if c not in keep_free and c not in arena]
        for cell in rng.sample(pool, min(max(walls - made, 0), len(pool))):
            board.set(cell, WALL)
        return board

    @classmethod
    def _layout_spiral(cls, rng: random.Random, walls: int, keep_free: set[Cell]) -> Board:
        """«Лабиринт-улитка»: два вала — кольцо посреди поля и квадрат у центра, каждый с одним
        проходом с противоположных сторон: внутрь попадаешь, обойдя вал кругом. Снаружи — редкие
        стены. Кемпиться негде, а крот прорубает прямые ходы через валы."""
        board = cls.empty()
        forbidden = keep_free | {(7, 7)}

        def ring(offset: int, gap: Cell) -> list[Cell]:
            lo, hi = offset, GRID - 1 - offset
            cells = ([(x, lo) for x in range(lo, hi + 1)] + [(x, hi) for x in range(lo, hi + 1)]
                     + [(lo, y) for y in range(lo + 1, hi)] + [(hi, y) for y in range(lo + 1, hi)])
            return [c for c in cells if c != gap and c not in forbidden and not cls.is_pillar_cell(*c)]

        pattern = ring(2, (7, 2)) + ring(6, (7, 8))
        if walls < len(pattern):                         # бюджет мал — вал с прорехами, но проходы целы
            pattern = rng.sample(pattern, walls)
        for cell in pattern:
            board.set(cell, WALL)
        rest = [c for c in board.cells_of(EMPTY) if c not in keep_free
                and (c[0] < 2 or c[1] < 2 or c[0] > 12 or c[1] > 12)]   # только внешний край
        for cell in rng.sample(rest, min(max(walls - len(pattern), 0), len(rest))):
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
