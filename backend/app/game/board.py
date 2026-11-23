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

SHELTER_BLOCKS = (
    ((3, 3), (4, 3), (3, 4), (4, 4)),
    ((10, 3), (11, 3), (10, 4), (11, 4), (10, 5), (11, 5)),
    ((3, 9), (4, 9), (3, 10), (4, 10), (3, 11), (4, 11)),
    ((10, 10), (11, 10), (10, 11), (11, 11)),
)
# Блоки добавляют 14 новых колонн — столько же убираем, чтобы плотность поля не менялась.
SHELTER_CLEARINGS = {
    (1, 3), (3, 1), (5, 3), (3, 5),
    (9, 3), (9, 5), (13, 5),
    (5, 9), (1, 9), (5, 11),
    (9, 11), (13, 11), (11, 9), (11, 13),
}


def _mirror4(cells: set[Cell]) -> set[Cell]:
    out: set[Cell] = set()
    for x, y in cells:
        out.update(((x, y), (GRID - 1 - x, y), (x, GRID - 1 - y), (GRID - 1 - x, GRID - 1 - y)))
    return out


_CLASSIC_PILLARS = {(x, y) for y in range(GRID) for x in range(GRID) if x % 2 == 1 and y % 2 == 1}
_BLOCK_PILLARS = (_CLASSIC_PILLARS - SHELTER_CLEARINGS) | {c for block in SHELTER_BLOCKS for c in block}
_BASTION_PILLARS = {c for c in _mirror4({
    (3, 3), (4, 3), (3, 4), (4, 4), (1, 5), (5, 1), (5, 5), (2, 6), (6, 2),
}) if c[0] != GRID // 2 and c[1] != GRID // 2}
_RING_PILLARS = {(x, 3) for x in range(3, 12) if x != 7} | {(x, 11) for x in range(3, 12) if x != 7}
_RING_PILLARS |= {(3, y) for y in range(4, 11) if y != 7} | {(11, y) for y in range(4, 11) if y != 7}
_RING_PILLARS |= _mirror4({(1, 1), (2, 1), (1, 2), (6, 6), (7, 6), (6, 7), (7, 7)})
_CROSS_PILLARS = _mirror4({(7, 2), (7, 4), (2, 7), (4, 7), (3, 3), (4, 3), (3, 4), (4, 4), (5, 5)})
_COLONNADE_PILLARS = _mirror4({
    (2, 2), (3, 2), (2, 3), (3, 3), (6, 2), (6, 3),
    (2, 6), (3, 6), (6, 6), (6, 7), (7, 6), (7, 7),
})

PILLAR_PATTERNS = {
    "classic": _CLASSIC_PILLARS,
    "blocks": _BLOCK_PILLARS,
    "bastions": _BASTION_PILLARS,
    "ring": _RING_PILLARS,
    "cross": _CROSS_PILLARS,
    "colonnade": _COLONNADE_PILLARS,
}
PILLAR_PATTERN_ORDER = ("classic", "blocks", "bastions", "ring", "cross", "colonnade")
NEW_PILLAR_PATTERNS = PILLAR_PATTERN_ORDER[1:]
PILLAR_PATTERN_SEQUENCE = list(PILLAR_PATTERN_ORDER)
random.Random(2027).shuffle(PILLAR_PATTERN_SEQUENCE)
PILLAR_PATTERN_SEQUENCE = tuple(PILLAR_PATTERN_SEQUENCE)


class Board:
    def __init__(self, cells: list[list[str]]):
        self.cells = cells  # cells[y][x]

    @staticmethod
    def is_pillar_cell(x: int, y: int) -> bool:
        """Базовая шахматная сетка; блочные укрытия добавляются отдельно."""
        return x % 2 == 1 and y % 2 == 1

    @classmethod
    def empty(cls, pattern: str = "classic") -> Board:
        """Голое поле с выбранной симметричной расстановкой невзрываемых колонн."""
        pillars = PILLAR_PATTERNS.get(pattern, _CLASSIC_PILLARS)
        return cls([[PILLAR if (x, y) in pillars else EMPTY for x in range(GRID)] for y in range(GRID)])

    @classmethod
    def generate(cls, rng: random.Random, walls: int, keep_free: set[Cell], pattern: str = "classic") -> Board:
        """Случайно расставляет стены, не трогая клетки из keep_free (углы игроков)."""
        board = cls.empty(pattern)
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
    def with_layout(cls, rng: random.Random, walls: int, keep_free: set[Cell], layout: str, pattern: str = "classic") -> Board:
        """Поле по имени планировки; 'random' и неизвестные имена — старый наугад."""
        makers = {"corridor": cls._layout_corridor, "island": cls._layout_island, "spiral": cls._layout_spiral}
        maker = makers.get(layout)
        return maker(rng, walls, keep_free, pattern) if maker else cls.generate(rng, walls, keep_free, pattern)

    @classmethod
    def _layout_corridor(cls, rng: random.Random, walls: int, keep_free: set[Cell], pattern: str = "classic") -> Board:
        """«Сквозной коридор»: две свободные строки через всё поле, а сверху и снизу — частокол
        из одинаковых блоков с проходами между ними. Длинная погоня без тупиков;
        воришке есть где прятать добычу, кроту — что вскрывать."""
        board = cls.empty(pattern)
        y0 = rng.choice((6, 7))
        band = {y0, y0 + 1}
        blocks = [(x, y) for y in range(GRID) if y not in band
                  for x in range(GRID) if x % 2 == 0 and y % 2 == 0
                  and board.get((x, y)) == EMPTY and (x, y) not in keep_free]
        for cell in rng.sample(blocks, min(walls, len(blocks))):
            board.set(cell, WALL)
        rest = [c for c in board.cells_of(EMPTY) if c not in keep_free and c[1] not in band]
        over = walls - min(walls, len(blocks))
        if over > 0:
            for cell in rng.sample(rest, min(over, len(rest))):
                board.set(cell, WALL)
        return board

    @classmethod
    def _layout_island(cls, rng: random.Random, walls: int, keep_free: set[Cell], pattern: str = "classic") -> Board:
        """«Арена с островом»: в центре — квадрат из стен с четырьмя входами, вокруг него чистая
        арена. Дверь и бонусы чаще всего прячутся в острове. Крот отрезает остров от мостиков."""
        board = cls.empty(pattern)
        island = [(x, y) for y in range(5, 10) for x in range(5, 10) if board.get((x, y)) != PILLAR]
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
    def _layout_spiral(cls, rng: random.Random, walls: int, keep_free: set[Cell], pattern: str = "classic") -> Board:
        """«Лабиринт-улитка»: два вала — кольцо посреди поля и квадрат у центра, каждый с одним
        проходом с противоположных сторон: внутрь попадаешь, обойдя вал кругом. Снаружи — редкие
        стены. Кемпиться негде, а крот прорубает прямые ходы через валы."""
        board = cls.empty(pattern)
        forbidden = keep_free | {(7, 7)}

        def ring(offset: int, gap: Cell) -> list[Cell]:
            lo, hi = offset, GRID - 1 - offset
            cells = ([(x, lo) for x in range(lo, hi + 1)] + [(x, hi) for x in range(lo, hi + 1)]
                     + [(lo, y) for y in range(lo + 1, hi)] + [(hi, y) for y in range(lo + 1, hi)])
            return [c for c in cells if c != gap and c not in forbidden and board.get(c) == EMPTY]

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
