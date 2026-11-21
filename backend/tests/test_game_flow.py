import random

from fastapi.testclient import TestClient

from app.game.engine import Game
from app.game.board import Board
from app.game.config import BOMB_FUSE, REVIVE_SHIELD
from app.game.entities import Enemy, Flame, Item
from app.main import app

from .conftest import make_game, run


def test_each_next_extra_life_costs_more_points():
    from app.game.config import extra_life_threshold
    assert [extra_life_threshold(n) for n in (1, 2, 3)] == [5000, 10500, 16500]
    game = make_game(board=Board.empty())
    ivan = game.players[0]
    start = ivan.lives
    game._add_score(ivan, 4999)
    assert ivan.lives == start                                 # до первой жизни не дотянул
    game._add_score(ivan, 1)
    assert ivan.lives == start + 1                             # ровно 5000 — жизнь
    game._add_score(ivan, 5499)
    assert ivan.lives == start + 1                             # вторая дороже первой на 500
    game._add_score(ivan, 1)
    assert ivan.lives == start + 2                             # 10 500 — вторая жизнь
    game._add_score(ivan, 5999)
    assert ivan.lives == start + 2                             # третья дороже второй ещё на 500
    game._add_score(ivan, 1)
    assert ivan.lives == start + 3                             # 16 500 — третья жизнь


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
    assert died == [{"type": "player_died", "player": 1, "kind": "normal", "cause": "bomb", "killer": 0}]


def test_death_cause_tells_enemy_from_trap():
    """По причине смерти игра выбирает звук: над жертвой призрака призраки злорадствуют."""
    game = make_game(board=Board.empty())
    game.enemies = {1: Enemy(1, 0.0, 0.0, tier=0, speed=0, sight=9)}   # стоит прямо на герое
    run(game, 0.1)
    died = [e for e in game.snapshot()["events"] if e["type"] == "player_died"]
    assert died[0]["cause"] == "enemy" and died[0]["killer"] is None

    game = make_game(board=Board.empty())
    game.items = {1: Item(1, (1, 0), "death")}
    game.set_direction(0, "right")
    run(game, 1.0)
    died = [e for e in game.snapshot()["events"] if e["type"] == "player_died"]
    assert died[0]["cause"] == "trap"


def test_enemy_eyes_look_at_chased_player():
    game = make_game(level=10, board=Board.empty())
    game.enemies = {1: Enemy(1, 4.0, 0.0, tier=0, speed=0, sight=9)}
    run(game, 0.1)
    enemy = game.snapshot()["enemies"][0]
    assert enemy["chasing"] and enemy["look"] == [-1.0, 0.0]   # игрок слева, в (0,0)


def test_two_players_level_continues_while_one_alive():
    game = make_game(players=2, board=Board.empty())
    game._kill(game.players[0], epic=False, cause="enemy")
    run(game, 3.0)
    assert game.phase == "playing"          # Игорь ещё в игре


def test_game_over_when_lives_run_out():
    game = make_game(board=Board.empty())
    game.players[0].lives = 1
    game._kill(game.players[0], epic=False, cause="enemy")
    run(game, 4.0)
    assert game.phase == "game_over"


def test_revive_costs_a_life_and_partner_stands_up_in_his_corner():
    game = make_game(players=2, board=Board.empty())
    ivan, igor = game.players
    igor.x, igor.y = 6.0, 8.0
    game._kill(igor, epic=False, cause="enemy")
    run(game, 2.0)                                              # упал и лежит
    assert igor.state == "dead" and igor.lives == 4
    assert [p["can_revive"] for p in game.snapshot()["players"]] == [True, False]   # панель зовёт Ивана воскресить
    game.revive(0)
    assert igor.state == "alive" and (igor.x, igor.y) == (14.0, 14.0)
    assert (ivan.lives, igor.lives) == (4, 4)                   # Иван заплатил жизнью, у Игоря — сколько было
    state = game.snapshot()
    assert {"type": "player_revived", "player": 1, "by": 0, "x": 14, "y": 14} in state["events"]
    assert [p["can_revive"] for p in state["players"]] == [False, False]

    ivan.lives = 1
    run(game, REVIVE_SHIELD + 0.1)                              # воскрешённый первые секунды неуязвим — ждём
    game._kill(igor, epic=False, cause="enemy")
    run(game, 2.0)
    game.revive(0)                                              # последнюю жизнь отдать нельзя
    assert igor.state == "dead" and ivan.lives == 1


def test_partner_without_lives_can_be_revived_in_a_later_round():
    """Воскресить можно в любом раунде: и того, у кого жизни кончились ещё на прошлом уровне."""
    game = make_game(players=2, board=Board.empty())
    ivan, igor = game.players
    igor.lives = 1
    game._kill(igor, epic=False, cause="enemy")                 # последняя жизнь Игоря
    game.items = {1: Item(1, (2, 0), "door")}
    game.set_direction(0, "right")
    run(game, 5.0)                                              # Иван ушёл в дверь, начался второй уровень
    assert game.level == 2 and game.phase == "playing" and igor.state == "out" and igor.lives == 0
    game.enemies = {}
    game.revive(0)
    assert igor.state == "alive" and (igor.x, igor.y) == (14.0, 14.0)
    assert (ivan.lives, igor.lives) == (4, 1)                   # отданная жизнь стала у Игоря единственной


def test_revived_hero_is_safe_for_two_seconds():
    """Воскрешённого первые секунды не берут ни огонь, ни тварь: в углу они могут его ждать."""
    game = make_game(players=2, board=Board.empty())
    igor = game.players[1]
    game._kill(igor, epic=False, cause="enemy")
    run(game, 2.0)
    game.flames = [Flame((14, 14), "near", 1.0, owner=0)]       # угол Игоря в огне
    game.revive(0)
    run(game, 1.2)                                              # огонь отгорел
    assert igor.state == "alive" and game.snapshot()["players"][1]["shield"]
    game.enemies = {1: Enemy(1, 14.0, 14.0, tier=0, speed=0, sight=9)}   # теперь в углу стоит тварь
    run(game, REVIVE_SHIELD - 1.2 - 0.2)
    assert igor.state == "alive"
    run(game, 0.4)                                              # защита кончилась — тварь берёт своё
    assert igor.state == "dying" and not game.snapshot()["players"][1]["shield"]


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
                    if rng.random() < 0.01:
                        game.revive(index)
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
        assert [p["name"] for p in state["players"]] == ["Иван", "Игорь"]
        assert len(state["grid"]) == 225


def test_frontend_is_served():
    client = TestClient(app)
    assert client.get("/").status_code == 200
    assert client.get("/api/difficulty").json()[0]["level"] == 1
    assert client.get("/sounds/voice/fighter_ready.ogg").status_code == 200   # голоса попадают в игру
    assert client.get("/api/version").json()["version"] != "?"              # номер версии для меню
