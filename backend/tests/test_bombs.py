from app.game.board import EMPTY, WALL, Board
from app.game.config import BOMB_FUSE, CHAIN_DELAY, FLAME_TIME, NORMAL_DEATH, SUPER_DEATH_IN_PLACE, SUPER_DEATHS
from app.game.engine import blast_cells
from app.game.entities import Bomb, Enemy, Item

from .conftest import make_game, run


def test_blast_is_a_cross_of_two_cells_stopped_by_pillars():
    board = Board.empty()
    cells = {c for c, _ in blast_cells(board, (2, 2))}
    assert cells == {(2, 2), (1, 2), (0, 2), (3, 2), (4, 2), (2, 1), (2, 0), (2, 3), (2, 4)}
    # из (2,1): влево и вправо колонны (1,1) и (3,1)
    assert {c for c, _ in blast_cells(board, (2, 1))} == {(2, 1), (2, 0), (2, 2), (2, 3)}


def test_wall_burns_and_stops_the_fire():
    board = Board.empty()
    board.set((0, 1), WALL)
    cells = {c for c, _ in blast_cells(board, (0, 0))}
    assert (0, 1) in cells and (0, 2) not in cells


def test_bomb_explodes_destroys_wall_and_reveals_item():
    board = Board.empty()
    board.set((2, 0), WALL)
    game = make_game(board=board)
    game.hidden = {(2, 0): "chest"}
    game.place_bomb(0)                      # игрок стоит в (0,0)
    game.set_direction(0, "down")
    run(game, 1.0)                          # отходим за угол
    game.set_direction(0, "right")
    run(game, 0.4)
    run(game, BOMB_FUSE)
    assert game.board.get((2, 0)) == EMPTY
    assert [i.kind for i in game.items.values()] == ["chest"]
    assert game.players[0].state == "alive"


def test_chain_reaction():
    game = make_game(board=Board.empty())
    game.players[0].x, game.players[0].y = 4.0, 0.0
    game.place_bomb(0)
    game.players[0].capacity = 5
    game.players[0].x = 6.0
    game.place_bomb(0)
    game.players[0].x, game.players[0].y = 14.0, 14.0
    first, second = game.bombs.values()
    second.fuse = 100                       # сама бы не взорвалась
    run(game, BOMB_FUSE + 0.05)
    assert list(game.bombs) == [second.id]  # вторая ещё ждёт — волна идёт с задержкой
    run(game, CHAIN_DELAY + 0.05)
    assert not game.bombs


def test_chain_wave_goes_from_earliest_to_latest():
    game = make_game(board=Board.empty())
    player = game.players[0]
    player.capacity = 5
    for x in (4, 2, 6):                     # ставим: средняя, левая, правая
        player.x, player.y = float(x), 0.0
        game.place_bomb(0)
    player.x, player.y = 14.0, 14.0
    middle, left, right = game.bombs.values()
    left.fuse = right.fuse = 100
    order = []
    for _ in range(200):
        game.update(1 / 30)
        order += [e["x"] for e in game.snapshot()["events"] if e["type"] == "explosion"]
    assert order == [4, 2, 6]               # левая поставлена раньше правой — и рвётся раньше


def test_fire_kills_player_and_enemy_and_gives_score():
    game = make_game(board=Board.empty())
    game.enemies = {99: Enemy(99, 2.0, 0.0, tier=0, speed=0)}
    game.place_bomb(0)
    run(game, BOMB_FUSE + 0.1)
    assert game.players[0].state == "dying"
    assert game.players[0].death_kind == "super"   # стоял на бомбе — эпичная смерть
    died = [e for e in game.snapshot()["events"] if e["type"] == "player_died"]
    assert died[0]["killer"] == 0                   # сам себя
    assert game.players[0].lives == 4
    assert not game.enemies
    assert game.players[0].score == 100     # зелёный враг


def test_fire_destroys_revealed_items_but_not_by_revealing_bomb():
    board = Board.empty()
    board.set((2, 0), WALL)
    game = make_game(board=board)
    game.hidden = {(2, 0): "gems"}
    game.players[0].x = 4.0
    game.place_bomb(0)                      # эта бомба откроет бонус
    game.players[0].x, game.players[0].y = 14.0, 14.0
    run(game, BOMB_FUSE + FLAME_TIME)
    assert [i.kind for i in game.items.values()] == ["gems"]
    game.players[0].x, game.players[0].y = 0.0, 0.0
    game.place_bomb(0)                      # а эта — сожжёт
    game.players[0].x, game.players[0].y = 14.0, 14.0
    run(game, BOMB_FUSE + 0.1)
    assert not game.items


def test_burned_door_opens_only_when_all_enemies_dead():
    game = make_game(board=Board.empty())
    game.items = {1: Item(1, (2, 0), "door")}
    game.enemies = {9: Enemy(9, 14.0, 14.0, tier=0, speed=0)}
    game.place_bomb(0)
    game.set_direction(0, "down")
    run(game, 1.0)
    game.set_direction(0, None)
    run(game, BOMB_FUSE)
    assert game.items[1].burned and game.snapshot()["items"][0]["locked"]
    game.players[0].x, game.players[0].y = 2.0, 0.0
    run(game, 0.5)                          # стоим на двери — но она заперта
    assert game.players[0].state == "alive"
    game.enemies = {}
    run(game, 0.1)
    assert game.players[0].state == "exited"


def test_stronger_enemy_gives_more_points():
    game = make_game(board=Board.empty())
    game.enemies = {1: Enemy(1, 2.0, 0.0, tier=0, speed=0), 2: Enemy(2, 0.0, 2.0, tier=3, speed=0)}
    game.players[0].x, game.players[0].y = 0.0, 0.0
    game.place_bomb(0)
    game.players[0].x, game.players[0].y = 14.0, 14.0
    run(game, BOMB_FUSE + 0.1)
    assert game.players[0].score == 100 + 1000


def test_level_ends_after_death_and_is_replayed():
    game = make_game(board=Board.empty())
    game.place_bomb(0)
    run(game, BOMB_FUSE + FLAME_TIME + 2.0)
    assert game.phase == "level_done" and game.result == "retry"
    run(game, 1.0)
    assert game.phase == "ready" and game.level == 1 and game.players[0].state == "alive"


def test_far_flame_gives_ordinary_death():
    game = make_game(board=Board.empty())
    game.players[0].x = 2.0
    game.place_bomb(0)
    game.players[0].x = 0.0                 # в двух клетках от бомбы — дальний язык пламени
    run(game, BOMB_FUSE + 0.1)
    assert game.players[0].state == "dying"
    assert game.players[0].death_kind == "normal"


def test_server_picks_how_the_hero_falls():
    """Обычная гибель — всегда «на колени». При «суперсмерти» сервер сам выбирает один из трёх вариантов
    и сообщает его браузеру: в игре по сети оба игрока должны увидеть одно и то же."""
    seen = set()
    for seed in range(30):
        game = make_game(seed=seed, board=Board.empty())
        game.players[0].x = 2.0             # смотрит вправо, позади свободная клетка
        game.place_bomb(0)                  # стоит на собственной бомбе
        run(game, BOMB_FUSE + 0.1)
        player = game.snapshot()["players"][0]
        assert player["death"] == "super" and player["death_anim"] in SUPER_DEATHS
        seen.add(player["death_anim"])
    assert seen == set(SUPER_DEATHS)

    # позади край поля, колонна или уцелевшая стена — отбрасывать некуда, героя подбрасывает на месте.
    # Стену вплотную за спиной тот же взрыв сжигает раньше, чем герой падает, — она не помеха.
    for seed in range(10):
        for bomb, hero, facing, wall in (
            ((0, 0), (0, 0), "right", None),        # в углу: позади край поля
            ((2, 1), (2, 1), "right", None),        # между колоннами: позади колонна (1,1)
            ((2, 1), (2, 2), "left", (3, 2)),       # рядом с бомбой, спиной к стене, до которой огонь не достаёт
        ):
            game = make_game(seed=seed, board=Board.empty())
            player = game.players[0]
            if wall:
                game.board.set(wall, WALL)
            player.x, player.y = float(bomb[0]), float(bomb[1])
            game.place_bomb(0)
            player.x, player.y, player.facing = float(hero[0]), float(hero[1]), facing
            run(game, BOMB_FUSE + 0.1)
            assert game.snapshot()["players"][0]["death_anim"] == SUPER_DEATH_IN_PLACE

    game = make_game(board=Board.empty())
    game.players[0].x = 2.0
    game.place_bomb(0)
    game.players[0].x = 0.0                 # дальний язык пламени
    run(game, BOMB_FUSE + 0.1)
    assert game.snapshot()["players"][0]["death_anim"] == NORMAL_DEATH


def test_heroes_run_past_bombs_but_enemies_do_not():
    game = make_game(players=2, board=Board.empty())
    game.players[1].x, game.players[1].y = 4.0, 0.0
    game.place_bomb(1)                      # бомба Игоря в (4,0) — на пути у Ивана
    game.set_direction(0, "right")
    run(game, 2.0)
    assert game.players[0].x > 5.0          # Иван пробежал мимо

    game = make_game(board=Board.empty())
    game.players[0].x, game.players[0].y = 14.0, 14.0
    game.bombs[998] = Bomb(998, (2, 0), 0, BOMB_FUSE, BOMB_FUSE)
    game.enemies = {1: Enemy(1, 0.0, 0.0, tier=0, speed=2.0, sight=0)}
    run(game, 2.0)
    assert game.enemies[1].x < 1.5          # враг в бомбу не идёт


def _bomb_at_corner(game, fuse=0.1):
    """Бомба в углу (0,0), игрок — в дальнем углу: взрыв его не касается."""
    game.players[0].x, game.players[0].y = 14.0, 14.0
    game.bombs[998] = Bomb(998, (0, 0), 0, fuse, BOMB_FUSE)


def test_enemy_behind_a_burning_wall_waits_for_the_fire_to_go_out():
    board = Board.empty()
    board.set((2, 0), WALL)                 # эта стена сгорит
    board.set((4, 0), WALL)                 # а эта запирает врага в клетке (3,0)
    game = make_game(board=board)
    game.enemies[999] = Enemy(999, 3.0, 0.0, tier=0, speed=1.5)
    _bomb_at_corner(game)
    run(game, 0.1 + FLAME_TIME - 0.1)       # стена сгорела, огонь на её месте ещё горит
    assert game.board.get((2, 0)) == EMPTY
    assert game.enemies[999].cell == (3, 0)             # ждёт, а не идёт в пламя
    run(game, 2.0)
    assert 999 in game.enemies                          # жив
    assert game.enemies[999].cell != (3, 0)             # и пошёл в открывшийся проход


def test_burned_life_releases_three_enemies():
    game = make_game(board=Board.empty())
    game.items[900] = Item(900, (2, 0), "life")
    _bomb_at_corner(game)
    run(game, 0.3)                          # взрыв: «жизнь» сгорела, но пока там огонь — никого
    assert not game.items and not game.enemies
    run(game, FLAME_TIME + 0.1)
    assert len(game.enemies) == 1           # огонь погас — вышел первый
    run(game, 2.0)
    assert len(game.enemies) == 3 and not game.nests


def test_door_stays_locked_until_enemies_from_burned_life_are_dead():
    game = make_game(board=Board.empty())
    game.items[900] = Item(900, (2, 0), "life")
    door = Item(901, (1, 0), "door")
    game.items[901] = door
    _bomb_at_corner(game)
    run(game, 0.3)                          # огонь задел и дверь, и «жизнь»; врагов на поле ещё нет
    assert door.burned and not game.enemies
    assert game._door_locked(door)          # но трое уже на подходе — дверь заперта
