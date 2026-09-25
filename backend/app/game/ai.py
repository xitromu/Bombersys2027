"""Мозги врагов.

Каждый раз, дойдя до центра клетки, враг решает, в какую соседнюю клетку идти дальше.
Насколько он хорош, задают настройки уровня (difficulty.py):
  * sight — с какого расстояния он «чует» игрока;
  * memory — сколько секунд идёт туда, где видел игрока последний раз;
  * smart — как часто ищет настоящий путь в обход стен (поиск в ширину, BFS),
    а не просто шагает «в сторону игрока» (так легко застрять за стеной);
  * avoid_danger — как часто обходит бомбы и огонь.
"""

from __future__ import annotations

import math
import random
from collections import deque
from collections.abc import Callable, Iterable

from .board import Board, Cell
from .difficulty import LevelSettings
from .entities import Enemy, Player

GREEDY_SHARE = 0.7        # если не ищет путь — с такой долей всё же идёт «в сторону игрока»
KEEP_STRAIGHT = 0.75      # в свободном блуждании чаще идёт прямо, чем сворачивает


def perceive(enemy: Enemy, players: Iterable[Player], settings: LevelSettings, dt: float) -> None:
    """Замечает ближайшего живого игрока в радиусе sight или постепенно «забывает» его."""
    nearest, best = None, math.inf
    for player in players:
        if player.active:
            distance = math.hypot(player.x - enemy.x, player.y - enemy.y)
            if distance < best:
                nearest, best = player, distance
    if nearest is not None and best <= settings.sight:
        enemy.chasing = True
        enemy.last_seen = nearest.cell
        enemy.memory_left = settings.memory
        return
    enemy.memory_left -= dt
    if enemy.memory_left <= 0:
        enemy.chasing = False
        enemy.last_seen = None


def bfs_next_step(start: Cell, goal: Cell, walkable: Callable[[Cell], bool], board: Board) -> Cell | None:
    """Первый шаг кратчайшего пути от start до goal (или None, если пути нет)."""
    came: dict[Cell, Cell | None] = {start: None}
    queue = deque([start])
    while queue:
        cell = queue.popleft()
        if cell == goal:
            while came[cell] != start:
                cell = came[cell]
            return cell
        for nxt in board.neighbors(cell):
            if nxt not in came and (nxt == goal or walkable(nxt)):
                came[nxt] = cell
                queue.append(nxt)
    return None


def _greedy(here: Cell, goal: Cell, options: list[Cell], rng: random.Random) -> Cell:
    """Шаг, который сильнее всего сокращает расстояние «по прямой» — без учёта стен."""
    def distance(c: Cell) -> int:
        return abs(c[0] - goal[0]) + abs(c[1] - goal[1])

    best = min(distance(c) for c in options)
    return rng.choice([c for c in options if distance(c) == best])


def _wander(enemy: Enemy, here: Cell, options: list[Cell], rng: random.Random) -> Cell:
    straight = (here[0] + enemy.heading[0], here[1] + enemy.heading[1])
    if straight in options and rng.random() < KEEP_STRAIGHT:
        return straight
    forward = [c for c in options if c != enemy.came_from]
    return rng.choice(forward or options)


def choose_step(
    enemy: Enemy,
    board: Board,
    blocked: set[Cell],
    danger: set[Cell],
    settings: LevelSettings,
    rng: random.Random,
) -> Cell | None:
    """Решает, в какую соседнюю клетку идти. None — постоять на месте."""
    here = enemy.cell

    def walkable(cell: Cell) -> bool:
        return board.is_floor(cell) and cell not in blocked

    options = [c for c in board.neighbors(here) if walkable(c)]
    if not options:
        return None

    if danger and rng.random() < settings.avoid_danger:
        safe = [c for c in options if c not in danger]
        if here in danger:
            options = safe or options   # убегаем из-под взрыва куда угодно
        elif safe:
            options = safe
        else:
            return None                 # вокруг опасно — лучше переждать

    goal = enemy.last_seen if enemy.chasing else None
    if goal is None or goal == here:
        return _wander(enemy, here, options, rng)

    roll = rng.random()
    if roll < settings.smart:
        step = bfs_next_step(here, goal, walkable, board)
        if step in options:
            return step
    if roll < settings.smart + (1 - settings.smart) * GREEDY_SHARE:
        return _greedy(here, goal, options, rng)
    return rng.choice(options)
