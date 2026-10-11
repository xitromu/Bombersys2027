"""Змея — враг длиной в три клетки: голова и тело, которое повторяет её путь.

Голову ведёт тот же «мозг», что и обычных врагов (ai.py). За собой голова оставляет след (trail) —
точки пути от самой свежей к старым; тело лежит на этом следе. Здесь только геометрия: где находятся
части тела и как змея разворачивается, когда ползти вперёд некуда (хвост становится головой).
"""

from __future__ import annotations

import math

from .board import Cell
from .config import SNAKE_LENGTH
from .entities import Enemy
from .movement import cell_of

Point = tuple[float, float]
EPS = 1e-6


def _sign(value: float) -> int:
    return (value > EPS) - (value < -EPS)


def path(snake: Enemy, length: float = SNAKE_LENGTH) -> list[Point]:
    """Ломаная от головы к кончику хвоста. Короче length, пока змея не выползла во всю длину."""
    points: list[Point] = [(snake.x, snake.y)]
    left = length
    for nxt in snake.trail:
        px, py = points[-1]
        segment = math.hypot(nxt[0] - px, nxt[1] - py)
        if segment <= EPS:
            continue
        if segment >= left:
            k = left / segment
            points.append((px + (nxt[0] - px) * k, py + (nxt[1] - py) * k))
            break
        points.append(nxt)
        left -= segment
    return points


def body(snake: Enemy, step: float) -> list[Point]:
    """Точки вдоль тела через каждые step клетки — от головы до кончика хвоста.

    Пока змея не выползла во всю длину, хвост лежит там, где она появилась.
    """
    line = path(snake)
    result: list[Point] = []
    index, start = 0, 0.0   # start — расстояние от головы до line[index]
    for i in range(round(SNAKE_LENGTH / step) + 1):
        s = i * step
        while index < len(line) - 1:
            (ax, ay), (bx, by) = line[index], line[index + 1]
            segment = math.hypot(bx - ax, by - ay)
            if s <= start + segment:
                k = (s - start) / segment
                result.append((ax + (bx - ax) * k, ay + (by - ay) * k))
                break
            start += segment
            index += 1
        else:
            result.append(line[-1])
    return result


def behind(snake: Enemy) -> Cell | None:
    """Клетка сразу за головой: там лежит собственное тело, туда голова не поворачивает."""
    for px, py in snake.trail:
        dx, dy = px - snake.x, py - snake.y
        if abs(dx) > EPS or abs(dy) > EPS:
            here = snake.cell
            return here[0] + _sign(dx), here[1] + _sign(dy)
    return None


def leave_cell(snake: Enemy, cell: Cell) -> None:
    """Голова уходит из центра клетки: запоминаем его в следе, а слишком старый след отбрасываем."""
    snake.trail.insert(0, (float(cell[0]), float(cell[1])))
    total, prev = 0.0, (snake.x, snake.y)
    for i, point in enumerate(snake.trail):
        total += math.hypot(point[0] - prev[0], point[1] - prev[1])
        prev = point
        if total > SNAKE_LENGTH + 1.0:
            del snake.trail[i + 1:]
            break


def reverse(snake: Enemy) -> bool:
    """Хвост становится головой: змея ползёт обратно по своему же следу.

    Возвращает False, если разворачиваться нечем (змея ещё не сдвинулась с места).
    """
    line = path(snake)
    if len(line) < 2:
        return False
    line.reverse()
    (snake.x, snake.y), snake.trail = line[0], line[1:]
    bx, by = snake.trail[0]                       # с этой стороны теперь тело
    hx, hy = _sign(snake.x - bx), _sign(snake.y - by)
    snake.heading = (hx, hy)
    snake.came_from = cell_of(bx, by)
    snake.target = None
    here = snake.cell
    if abs(snake.x - here[0]) > EPS or abs(snake.y - here[1]) > EPS:
        # новая голова оказалась между клетками — доползает до ближайшего центра по ходу движения
        tx = here[0] if hx == 0 else (math.floor(snake.x) + 1 if hx > 0 else math.ceil(snake.x) - 1)
        ty = here[1] if hy == 0 else (math.floor(snake.y) + 1 if hy > 0 else math.ceil(snake.y) - 1)
        snake.target = (tx, ty)
    return True
