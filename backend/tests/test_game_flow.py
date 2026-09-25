import random

from fastapi.testclient import TestClient

from app.game.engine import Game
from app.game.board import Board
from app.game.config import BOMB_FUSE
from app.game.entities import Enemy, Item
from app.main import app

from .conftest import make_game, run


def test_door_takes_player_to_next_level():
    game = make_game(board=Board.empty())
    game.items = {1: Item(1, (2, 0), "door")}
    game.set_direction(0, "right")
    run(game, 1.0)
    assert game.players[0].state == "exited"
    run(game, 2.0)
    assert game.level == 2 and game.phase == "ready"


def test_early_turn_keeps_walking_until_passage():
    game = make_game(board=Board.empty())
    game.players[0].x, game.players[0].y = 1.0, 0.0
    # жмём «вниз», ещё держа «вправо»: под (1,0) колонна — идём вправо до прохода (2,0) и сворачиваем
    game.set_direction(0, "down", alt="right")
    run(game, 1.2)
    player = game.players[0]
    assert player.x == 2.0 and player.y > 0.5


def test_killer_is_reported_when_one_player_blows_up_another():
    game = make_game(players=2, board=Board.empty())
    ivan, kolya = game.players
    kolya.x, kolya.y = 2.0, 0.0
    game.place_bomb(0)
    ivan.x, ivan.y = 0.0, 4.0
    run(game, BOMB_FUSE + 0.1)
    died = [e for e in game.snapshot()["events"] if e["type"] == "player_died"]
    assert died == [{"type": "player_died", "player": 1, "kind": "normal", "killer": 0}]


def test_enemy_eyes_look_at_chased_player():
    game = make_game(level=10, board=Board.empty())
    game.enemies = {1: Enemy(1, 4.0, 0.0, tier=0, speed=0, sight=9)}
    run(game, 0.1)
    enemy = game.snapshot()["enemies"][0]
    assert enemy["chasing"] and enemy["look"] == [-1.0, 0.0]   # игрок слева, в (0,0)


def test_two_players_level_continues_while_one_alive():
    game = make_game(players=2, board=Board.empty())
    game._kill(game.players[0], epic=False)
    run(game, 3.0)
    assert game.phase == "playing"          # Колян ещё в игре


def test_game_over_when_lives_run_out():
    game = make_game(board=Board.empty())
    game.players[0].lives = 1
    game._kill(game.players[0], epic=False)
    run(game, 4.0)
    assert game.phase == "game_over"


def test_random_play_does_not_crash():
    """«Обезьяний тест»: тысячи случайных нажатий на разных уровнях."""
    for players in (1, 2):
        for level in (1, 5, 10, 15):
            rng = random.Random(level * 10 + players)
            game = Game(players=players, rng=random.Random(level), level=level)
            for _ in range(3000):
                for index in range(players):
                    if rng.random() < 0.1:
                        game.set_direction(index, rng.choice(["left", "right", "up", "down", None]))
                    if rng.random() < 0.02:
                        game.place_bomb(index)
                game.update(1 / 30)
                state = game.snapshot()
                if state["phase"] == "game_over":
                    break


def test_websocket_game_starts_and_sends_state():
    client = TestClient(app)
    with client.websocket_connect("/ws") as ws:
        ws.send_json({"type": "start", "players": 2})
        state = ws.receive_json()
        assert state["type"] == "state"
        assert state["level"] == 1
        assert [p["name"] for p in state["players"]] == ["Иван", "Колян"]
        assert len(state["grid"]) == 225


def test_frontend_is_served():
    client = TestClient(app)
    assert client.get("/").status_code == 200
    assert client.get("/api/difficulty").json()[0]["level"] == 1
