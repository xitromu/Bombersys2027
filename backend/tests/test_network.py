"""Игра по сети: хозяин создаёт партию, гость присоединяется, каждый управляет своим героем."""

from fastapi.testclient import TestClient

from app.game.engine import Game
from app.main import Member, Room, app


def receive_until(ws, kind: str, limit: int = 200) -> dict:
    """Пропускает состояния игры, пока не придёт сообщение нужного типа."""
    for _ in range(limit):
        message = ws.receive_json()
        if message["type"] == kind:
            return message
    raise AssertionError(f"не дождались {kind}")


def test_network_game_starts_when_second_player_joins():
    # один TestClient на обе вкладки — как один сервер на хозяйском ноутбуке
    with TestClient(app) as client, client.websocket_connect("/ws") as host:
        host.send_json({"type": "host"})
        assert isinstance(host.receive_json()["urls"], list)
        with client.websocket_connect("/ws") as guest:
            guest.send_json({"type": "join"})
            assert guest.receive_json() == {"type": "joined", "seat": 1}
            assert host.receive_json() == {"type": "joined", "seat": 0}
            for ws in (host, guest):
                state = receive_until(ws, "state")
                assert [p["name"] for p in state["players"]] == ["Иван", "Колян"]


def test_guest_controls_only_kolyan():
    room = Room(network=True)
    host, guest = Member(None), Member(None)
    room.add(host, seat=0)
    room.add(guest, seat=1)
    room.game = Game(players=2)
    room.handle(guest, {"type": "dir", "player": 0, "dir": "left"})   # прикидывается Иваном
    assert room.game.players[1].wanted == "left"
    assert room.game.players[0].wanted is None


def test_join_without_host_reports_error():
    with TestClient(app) as client, client.websocket_connect("/ws") as ws:
        ws.send_json({"type": "join"})
        assert ws.receive_json()["type"] == "error"


def test_partner_leaving_ends_network_game():
    with TestClient(app) as client, client.websocket_connect("/ws") as host:
        host.send_json({"type": "host"})
        host.receive_json()
        with client.websocket_connect("/ws") as guest:
            guest.send_json({"type": "join"})
            receive_until(guest, "joined")
            guest.send_json({"type": "quit"})
            assert receive_until(host, "left") == {"type": "left", "name": "Колян"}
