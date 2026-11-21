"""Участники игры: игроки, враги, бомбы, огонь, бонусы.

Это просто «карточки с данными» (dataclass). Правила, которые ими двигают, — в engine.py и ai.py.
"""

from __future__ import annotations

from dataclasses import dataclass, field

from .board import Cell
from .config import BLAST_RADIUS, START_BOMBS, START_LIVES
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
    lives_bought: int = 0           # сколько дополнительных жизней уже куплено очками: порог следующей растёт
    capacity: int = START_BOMBS     # сколько бомб может стоять одновременно
    radius: int = BLAST_RADIUS      # крест огня его бомб (бонус «огонь +1»)
    remote: bool = False            # пульт: бомбы рвутся по клавише, а не по фитилю
    armor: bool = False             # щит: гасит один любой удар
    boots: bool = False             # сапоги: герой быстрее
    # alive — в игре; dying — анимация смерти; dead — ждёт конца уровня (или пока воскресит напарник);
    # exited — ушёл в дверь; out — жизни кончились (напарник может воскресить, отдав свою)
    state: str = "alive"
    state_time: float = 0.0
    shield: float = 0.0             # сколько секунд ещё неуязвим: только что воскрешён напарником
    death_kind: str | None = None   # normal / super
    death_anim: str | None = None   # как именно падает: knees / thrown / flip / rocket (см. config.py)
    death_cause: str | None = None  # от чего погиб: bomb / enemy / snake / trap
    death_half: bool = False        # съеден крупным (босс, матка): откушена половина туловища, а не голова
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
    # ghost — обычный зубастик, snake — змея (snake.py), armored — броненосец, phantom — призрак,
    # queen — матка, bomber — подрывник, thief — воришка, mole — крот, boss — гигантский зубастик
    kind: str = "ghost"
    trail: list[tuple[float, float]] = field(default_factory=list)   # змея: путь головы, свежие точки первыми
    armor: int = 0                  # сколько взрывов переживёт (панцири броненосца и босса)
    invuln: float = 0.0             # после треснувшего панциря огонь 잠시 не берёт
    mother: int | None = None       # ребёнок матки: id матки (чтобы считать живых детей)
    cooldown: float = 0.0           # матка: до следующего ребёнка; подрывник: до следующей бомбы;
                                    # крот: до следующего нырка
    flee: float = 0.0               # подрывник удирает от игрока ещё столько секунд
    enraged: bool = False           # ярость последнего: остался один и озверел
    loot: int | None = None         # воришка: id бонуса, который тащит в лапах
    burrowed: float = 0.0           # крот: столько секунд ещё под землёй (0 — на поверхности)

    @property
    def cell(self) -> Cell:
        return cell_of(self.x, self.y)


@dataclass
class Bomb:
    id: int
    cell: Cell
    owner: int                      # индекс игрока или ENEMY_BOMB_OWNER — бомба подрывника
    fuse: float                     # секунд до взрыва
    total: float
    radius: int = BLAST_RADIUS      # крест огня этой бомбы
    remote: bool = False            # пульт: фитиль не тикает, ждёт клавиши (цепная реакция поджигает и её)


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
    kind: str   # door, chest, bomb, life, death, bag, bigbag, gems, remote, fire, shield, boots
    revealed_by: int | None = None  # бомба, открывшая бонус, — её огонь бонус не трогает
    burned: bool = False            # для двери: в неё попал огонь
    carried: int | None = None      # воришка тащит: id врага (с поля бонус убран, но живёт у него в лапах)
