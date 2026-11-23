import math
import random

from app.game import snake
from app.game.board import EMPTY, WALL, Board
from app.game.config import BOMB_FUSE, ENEMY_SCORES, SNAKE_LENGTH, SNAKE_REMAINS, SNAKE_SCORE_FACTOR, snake_rank
from app.game.difficulty import for_level
from app.game.engine import Game
from app.game.entities import Bomb, Enemy

from .conftest import make_game, run


def corridor_game(seed=1):
    """Открыт только верхний ряд поля: развилок нет, змея ползёт по нему как по трубе."""
    board = Board.empty()
    for x in range(0, 15, 2):
        board.set((x, 1), WALL)
    game = make_game(seed=seed, board=board)
    game.players[0].x, game.players[0].y = 14.0, 14.0
    return game


def add_snake(game, x, y, trail=()):
    enemy = Enemy(999, float(x), float(y), tier=0, speed=2.0, kind="snake",
                  trail=[(float(px), float(py)) for px, py in trail])
    game.enemies[enemy.id] = enemy
    return enemy


def length(points):
    return sum(math.hypot(b[0] - a[0], b[1] - a[1]) for a, b in zip(points, points[1:]))


def test_snake_body_follows_the_head_around_a_corner():
    game = corridor_game()
    game.board.set((2, 1), EMPTY)           # проход вниз
    game.board.set((3, 0), WALL)            # а дальше вправо — стена
    s = add_snake(game, 0, 0)
    while s.y < 1.5:
        game.update(1 / 30)
    head, middle, tail = snake.body(s, 1.0)
    assert head[0] == 2.0                                   # голова уже в проходе вниз
    assert middle == (2.0, head[1] - 1.0)                   # середина идёт за ней тем же проходом
    assert tail[1] == 0.0 and abs(tail[0] - head[1]) < 1e-6   # хвост ещё в верхнем ряду, до угла не дополз
    assert abs(length(snake.path(s)) - SNAKE_LENGTH) < 1e-6


def test_fire_on_the_tail_kills_the_whole_snake_for_triple_score():
    game = corridor_game()
    s = add_snake(game, 6, 0, trail=[(5, 0), (4, 0), (3, 0)])   # голова в (6,0), хвост в (4,0)
    s.wait = 100                                                # стоит на месте
    game.bombs[998] = Bomb(998, (2, 0), 0, 0.1, BOMB_FUSE)      # огонь достанет до (4,0), но не до головы
    run(game, 0.3)
    assert not game.enemies
    assert game.players[0].score == ENEMY_SCORES[0] * SNAKE_SCORE_FACTOR


def test_touching_the_tail_kills_the_player():
    game = corridor_game()
    s = add_snake(game, 6, 0, trail=[(5, 0), (4, 0), (3, 0)])
    s.wait = 100
    game.players[0].x, game.players[0].y = 4.0, 0.0             # герой на хвосте, до головы две клетки
    run(game, 0.1)
    assert game.players[0].state == "dying"
    died = [e for e in game.events if e["type"] == "player_died"]
    assert died[0]["cause"] == "snake"                          # браузеру видно, что героя съела змея…
    assert game.snapshot()["players"][0]["cause"] == "snake"    # …и пока он лежит — тоже (от него останется скелет)


def test_server_picks_what_is_left_of_a_hero_eaten_by_a_snake():
    """От съеденного змеёй остаётся скелет в сапогах или кучка костей. Выбирает сервер и сообщает браузеру:
    в игре по сети оба игрока должны увидеть одно и то же. После другой гибели костей нет."""
    seen = set()
    for seed in range(20):
        game = corridor_game(seed)
        add_snake(game, 6, 0, trail=[(5, 0), (4, 0), (3, 0)]).wait = 100
        game.players[0].x, game.players[0].y = 4.0, 0.0             # герой на хвосте
        run(game, 0.1)
        seen.add(game.snapshot()["players"][0]["remains"])
    assert seen == set(SNAKE_REMAINS)

    game = corridor_game()
    game.enemies[1] = Enemy(1, 14.0, 14.0, tier=0, speed=0, sight=9)   # обычный враг стоит прямо на герое
    run(game, 0.1)
    player = game.snapshot()["players"][0]
    assert player["cause"] == "enemy" and player["remains"] is None


def test_snake_in_a_dead_end_turns_its_head_back_and_crawls_along_itself():
    game = corridor_game()
    s = add_snake(game, 13, 0, trail=[(12, 0), (11, 0)])        # ползёт вправо, впереди тупик (14,0)
    run(game, 0.8)
    line = snake.path(s)
    assert 13 < s.x < 14 and line[1] == (14.0, 0.0)             # голова уже ползёт обратно, тело ещё идёт в тупик
    assert abs(length(line) - SNAKE_LENGTH) < 1e-6              # петля: тело сложилось, но не «порвалось»
    run(game, 3.2)
    assert 999 in game.enemies
    assert s.x < 11                                             # развернулась целиком и уползла обратно
    assert abs(length(snake.path(s)) - SNAKE_LENGTH) < 1e-6


def test_snake_retreats_from_a_bomb_that_appears_ahead():
    game = corridor_game()
    s = add_snake(game, 10, 0, trail=[(9, 0), (8, 0)])
    run(game, 0.2)                                              # ползёт к (11,0)
    game.bombs[998] = Bomb(998, (11, 0), 0, BOMB_FUSE, BOMB_FUSE)
    run(game, BOMB_FUSE + 0.3)
    assert 999 in game.enemies                                  # повернула голову назад и уползла — взрыв не достал
    assert abs(length(snake.path(s)) - SNAKE_LENGTH) < 1e-6


def test_snakes_appear_from_level_four_and_replace_ordinary_enemies():
    assert [for_level(n).snakes for n in (1, 3, 4, 8, 9)] == [0, 0, 1, 1, 2]
    game = Game(players=1, rng=random.Random(2), level=4)
    kinds = [e.kind for e in game.enemies.values()]
    assert kinds.count("snake") == 1 and len(kinds) == for_level(4).enemies
    seen = next(e for e in game.snapshot()["enemies"] if e["kind"] == "snake")
    assert seen["path"][0] == [seen["x"], seen["y"]]            # ломаная тела для браузера начинается с головы…
    assert abs(length(seen["path"]) - SNAKE_LENGTH) < 1e-6      # …и змея сразу во всю длину


def test_snake_colors_keep_the_old_ladder_and_add_purple_from_level_thirteen():
    assert [snake_rank(n) for n in (4, 6, 7, 9, 10, 12, 13, 20)] == [0, 0, 1, 1, 2, 2, 3, 3]
    for level, rank in ((4, 0), (7, 1), (11, 2), (13, 3)):
        game = Game(players=1, rng=random.Random(2), level=level)
        snakes = [enemy for enemy in game.snapshot()["enemies"] if enemy["kind"] == "snake"]
        assert snakes and all(enemy["rank"] == rank for enemy in snakes)


def test_snake_appears_at_full_length_on_free_cells():
    """Змея не вырастает из головы: с первого мгновения лежит во всю длину — на свободных клетках,
    не у стартовых углов героев, и головой от собственного тела."""
    for level in (4, 9, 15):
        for seed in range(30):
            game = Game(players=2, rng=random.Random(seed), level=level)
            snakes = [e for e in game.enemies.values() if e.kind == "snake"]
            assert len(snakes) == for_level(level, 2).snakes
            for s in snakes:
                cells = [(round(x), round(y)) for x, y in snake.path(s)]
                assert abs(length(snake.path(s)) - SNAKE_LENGTH) < 1e-6
                assert len(set(cells)) == 3 and all(game.board.is_floor(c) for c in cells)
                assert all(abs(x - sx) + abs(y - sy) >= 3 for x, y in cells for sx, sy in ((0, 0), (14, 14)))
                assert snake.behind(s) == cells[1]              # за головой — её тело, туда она не повернёт
