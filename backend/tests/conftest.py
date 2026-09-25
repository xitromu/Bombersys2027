import random

import pytest

from app import records
from app.game.engine import Game
from app.game.board import Board


@pytest.fixture(autouse=True)
def records_in_tmp(tmp_path, monkeypatch):
    """Тесты не должны портить настоящую таблицу рекордов."""
    monkeypatch.setattr(records, "RECORDS_FILE", tmp_path / "records.json")


def open_field() -> Board:
    """Поле только с колоннами — без стен."""
    return Board.empty()


def make_game(players: int = 1, seed: int = 1, level: int = 1, board: Board | None = None) -> Game:
    """Партия в фазе playing, при желании — на заданном поле и без врагов."""
    game = Game(players=players, rng=random.Random(seed), level=level)
    if board is not None:
        game.board = board
        game.hidden = {}
        game.enemies = {}
    game.phase = "playing"
    return game


def run(game: Game, seconds: float, dt: float = 1 / 30) -> None:
    for _ in range(round(seconds / dt)):
        game.update(dt)
