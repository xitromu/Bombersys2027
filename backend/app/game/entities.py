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
    index: int                      # 0 — Иван, 1 — Игорь
    name: str
    x: float = 0.0
    y: float = 0.0
    facing: str = "right"
    wanted: str | None = None       # куда игрок сейчас жмёт
    wanted_alt: str | None = None   # предыдущая зажатая клавиша: если повернуть рано, идём по ней
    moving: bool = False
    lives: int = START_LIVES
    score: int = 0
    capacity: int = START_BOMBS     # сколько бомб может стоять одновременно
    # alive — в игре; dying — анимация смерти; dead — ждёт конца уровня (или пока воскресит напарник);
    # exited — ушёл в дверь; out — жизни кончились (напарник может воскресить, отдав свою)
    state: str = "alive"
    state_time: float = 0.0
    shield: float = 0.0             # сколько секунд ещё неуязвим: только что воскрешён напарником
    death_kind: str | None = None   # normal / super
    death_anim: str | None = None   # как именно падает: knees / thrown / flip / rocket (см. config.py)
    death_cause: str | None = None  # от чего погиб: bomb / enemy / snake / trap
    remains: str | None = None      # что осталось от съеденного змеёй: skeleton / pile (см. config.py)

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
    tier: int                       # 0..3 — чем больше, тем враг сильнее и дороже
    speed: float
    sight: float = 3.0              # остальные параметры — см. difficulty.enemy_stats
    smart: float = 0.0
    memory: float = 0.0
    avoid_danger: float = 0.0
    target: Cell | None = None      # клетка, в которую сейчас идёт
    came_from: Cell | None = None
    heading: tuple[int, int] = (0, 0)
    chasing: bool = False
    last_seen: Cell | None = None   # где последний раз видел игрока
    memory_left: float = 0.0
    wait: float = 0.0               # стоит на месте (некуда идти)
    kind: str = "ghost"             # ghost — обычный враг, snake — змея длиной в три клетки (см. snake.py)
    trail: list[tuple[float, float]] = field(default_factory=list)   # змея: путь головы, свежие точки первыми

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
    bomb: int = 0                   # какая бомба зажгла
    wall: bool = False              # горит на месте сгоревшей стены: пока не погаснет, враги туда не идут


@dataclass
class Nest:
    """Место взорванного бонуса «жизнь»: когда огонь погаснет, отсюда по одному выходят враги."""
    cell: Cell
    left: int                       # сколько врагов ещё выйдет
    wait: float = 0.0               # пауза до следующего


@dataclass
class Item:
    id: int
    cell: Cell
    kind: str   # door, chest, bomb, life, death, bag, bigbag, gems
    revealed_by: int | None = None  # бомба, открывшая бонус, — её огонь бонус не трогает
    burned: bool = False            # для двери: в неё попал огонь
