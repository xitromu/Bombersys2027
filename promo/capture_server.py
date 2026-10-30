"""Сервер игры для съёмки промо-ролика: настоящий движок и настоящая страница, но партию ведёт сценарий.

Отличия от обычного сервера: свой порт, только 127.0.0.1, рекорды — в отдельном файле (таблицу игрока не трогаем)
и сообщение {"type": "promo", "cmd": ...}, которым capture.py ставит нужную сцену. Дальше всё считают обычные
правила из backend/app/game.

Запуск: backend/.venv/Scripts/python.exe promo/capture_server.py 8011 <файл рекордов>
"""

from __future__ import annotations

import random
import sys
from pathlib import Path

import uvicorn

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "backend"))

import app.main as server  # noqa: E402
from app import records  # noqa: E402
from app.game.board import EMPTY, WALL  # noqa: E402
from app.game.config import BOMB_FUSE  # noqa: E402
from app.game.entities import Bomb  # noqa: E402


def set_level(game, level: int, seed: int, lives: int = 9, capacity: int = 3) -> None:
    game.rng = random.Random(seed)
    game.level = level
    for player in game.players:
        player.lives, player.capacity = lives, capacity
    game._start_level()


def clean_row(game, y: int) -> None:
    """Убирает стены с ряда: иначе огонь упрётся в первую же и цепочка оборвётся."""
    for x in range(15):
        if game.board.get((x, y)) == WALL:
            game.board.set((x, y), EMPTY)
            game.hidden.pop((x, y), None)


def chain(game, y: int, xs: list[int], fuse: float, owner: int) -> None:
    """Ряд бомб через клетку: поджигается первая, остальные рвутся от неё по правилам игры."""
    clean_row(game, y)
    for i, x in enumerate(xs):
        left = fuse if i == 0 else BOMB_FUSE * 9
        bomb = Bomb(next(game._ids), (x, y), owner, left, left)
        game.bombs[bomb.id] = bomb


def walls_around(game, y: int, xs: list[int]) -> None:
    """Стены вокруг ряда бомб: красиво рушатся, а без колонн огонь до них достаёт."""
    for x in xs:
        for dy in (-2, 2):
            cell = (x, y + dy)
            if game.board.inside(cell) and game.board.get(cell) == EMPTY:
                game.board.set(cell, WALL)


def enemy_at(game, x: int, y: int, strong: bool) -> None:
    enemy = game._new_enemy((x, y), strong)
    game.enemies[enemy.id] = enemy


def place_hero(game, index: int, x: int, y: int) -> None:
    player = game.players[index]
    player.x, player.y = float(x), float(y)
    if game.board.get((x, y)) == WALL:
        game.board.set((x, y), EMPTY)
    # чтобы герою было куда уйти
    for cell in game.board.neighbors((x, y)):
        if game.board.get(cell) == WALL:
            game.board.set(cell, EMPTY)


def score(game, index: int, value: int) -> None:
    game.players[index].score = value


def only_snakes(game) -> None:
    """На поле остаются одни змеи: герой должен дойти именно до змеи, а не до зубастика."""
    game.enemies = {i: e for i, e in game.enemies.items() if e.kind == "snake"}
    for y in range(15):
        clean_row(game, y)      # и стены не мешают ему дойти


COMMANDS = {
    "level": set_level, "chain": chain, "walls_around": walls_around, "enemy": enemy_at, "hero": place_hero,
    "score": score, "only_snakes": only_snakes,
}
original_handle = server.Room.handle


def handle(self, member, message: dict) -> None:
    if message.get("type") == "promo":
        args = {k: v for k, v in message.items() if k not in ("type", "cmd")}
        if self.game is not None:
            COMMANDS[message["cmd"]](self.game, **args)
    else:
        original_handle(self, member, message)


if __name__ == "__main__":
    port, records_file = int(sys.argv[1]), Path(sys.argv[2])
    records.RECORDS_FILE = records_file
    add, load = records.add, records.load
    records.add = lambda names, level, total, path=None: add(names, level, total, records_file)
    records.load = lambda path=None: load(records_file)
    server.Room.handle = handle
    uvicorn.run(server.app, host="127.0.0.1", port=port, log_level="warning")
