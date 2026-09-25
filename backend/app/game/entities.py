"""Участники игры: игроки, враги, бомбы, огонь, бонусы.

Это просто «карточки с данными» (dataclass). Правила, которые ими двигают, — в engine.py и ai.py.
"""

from __future__ import annotations

from dataclasses import dataclass, field

from .board import Cell
from .config import START_BOMBS, START_LIVES
from .movement import cell_of


@dataclass
class Player:
    index: int                      # 0 — Иван, 1 — Колян
    name: str
    x: float = 0.0
    y: float = 0.0
    facing: str = "right"
    wanted: str | None = None       # куда игрок сейчас жмёт
    moving: bool = False
    lives: int = START_LIVES
    score: int = 0
    capacity: int = START_BOMBS     # сколько бомб может стоять одновременно
    # alive — в игре; dying — анимация смерти; dead — ждёт конца уровня;
    # exited — ушёл в дверь; out — жизни кончились
    state: str = "alive"
    state_time: float = 0.0
    death_kind: str | None = None   # normal / super
    # бомбы, с которых игрок ещё не сошёл (по ним можно ходить, пока не отойдёшь)
    ghost_bombs: set[int] = field(default_factory=set)

    @property
    def cell(self) -> Cell:
        return cell_of(self.x, self.y)

    @property
    def active(self) -> bool:
        return self.state == "alive"


@dataclass
class Enemy:
    id: int
    x: float
    y: float
    tier: int
    speed: float
    target: Cell | None = None      # клетка, в которую сейчас идёт
    came_from: Cell | None = None
    heading: tuple[int, int] = (0, 0)
    chasing: bool = False
    last_seen: Cell | None = None   # где последний раз видел игрока
    memory_left: float = 0.0
    wait: float = 0.0               # стоит на месте (некуда идти)

    @property
    def cell(self) -> Cell:
        return cell_of(self.x, self.y)


@dataclass
class Bomb:
    id: int
    cell: Cell
    owner: int
    fuse: float                     # секунд до взрыва
    total: float


@dataclass
class Flame:
    cell: Cell
    kind: str                       # near — рядом с бомбой, far — дальний язык
    time_left: float
    owner: int


@dataclass
class Item:
    id: int
    cell: Cell
    kind: str   # door, chest, bomb, life, death, bag, bigbag, gems, legacy
