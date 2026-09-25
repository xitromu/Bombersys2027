"""Движение по сетке с «мягкими» поворотами.

Координаты — дробные, в клетках: (3.0, 5.0) — центр клетки (3, 5), (3.4, 5.0) — чуть правее.
Идти вдоль коридора можно, только стоя ровно по его оси. Если игрок повернул чуть
раньше или позже прохода, его плавно подтягивает к оси — как «сглаженный поворот»
в Player::NextStep оригинала.
"""

from __future__ import annotations

import math
from collections.abc import Callable

from .board import Cell
from .config import CORNER_ASSIST

DIRECTIONS: dict[str, tuple[int, int]] = {
    "left": (-1, 0),
    "right": (1, 0),
    "up": (0, -1),
    "down": (0, 1),
}
EPS = 1e-6


def cell_of(x: float, y: float) -> Cell:
    """В какой клетке находится центр тела."""
    return math.floor(x + 0.5), math.floor(y + 0.5)


def touched_cells(x: float, y: float, half: float) -> set[Cell]:
    """Все клетки, которые задевает квадратное тело полуразмером half."""
    xs = {math.floor(x - half + 0.5), math.floor(x + half + 0.5)}
    ys = {math.floor(y - half + 0.5), math.floor(y + half + 0.5)}
    return {(cx, cy) for cx in xs for cy in ys}


def move_on_grid(
    x: float, y: float, direction: str, distance: float, passable: Callable[[Cell], bool]
) -> tuple[float, float]:
    """Сдвигает тело на distance в направлении direction. Возвращает новые (x, y)."""
    dx, dy = DIRECTIONS[direction]
    horizontal = dx != 0
    sign = dx if horizontal else dy
    along, across = (x, y) if horizontal else (y, x)

    def cell(a: int, c: int) -> Cell:
        return (a, c) if horizontal else (c, a)

    def result(a: float, c: float) -> tuple[float, float]:
        return (a, c) if horizontal else (c, a)

    lane = math.floor(across + 0.5)
    offset = across - lane
    here = math.floor(along + 0.5)

    # 1) Стоим не по оси коридора — сначала подтягиваемся к ней.
    if abs(offset) > EPS:
        other_lane = lane + (1 if offset > 0 else -1)
        if passable(cell(here + sign, lane)):
            goal = lane
        elif 1 - abs(offset) <= CORNER_ASSIST and passable(cell(here + sign, other_lane)):
            goal = other_lane
        else:
            return x, y
        step = min(distance, abs(goal - across))
        across += step if goal > across else -step
        if abs(across - goal) < EPS:
            across = goal
        return result(along, across)

    # 2) Стоим ровно — идём вперёд, пока следующая клетка свободна.
    target = along + sign * distance
    if (target - here) * sign <= 0 or passable(cell(here + sign, lane)):
        along = target
    elif (along - here) * sign < 0:
        along = here  # дошли до центра клетки и упёрлись
    return result(along, float(lane))
