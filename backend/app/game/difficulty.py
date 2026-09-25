"""Как растёт сложность от уровня к уровню.

Это главный файл для настройки баланса. Всё растёт плавно и упирается в потолок,
чтобы до 10-го уровня мог дойти любой игрок. Посмотреть таблицу по уровням:
    uv run python -m app.game.difficulty
"""

from __future__ import annotations

from dataclasses import asdict, dataclass

from .config import PLAYER_SPEED


@dataclass(frozen=True)
class LevelSettings:
    level: int
    walls: int            # разрушаемых стен на поле
    enemies: int          # сколько врагов
    enemy_tier: int       # внешний вид врагов 0..3 (зелёный → фиолетовый)
    enemy_speed: float    # клеток в секунду (всегда медленнее игрока)
    sight: float          # с какого расстояния враг замечает игрока, клеток
    smart: float          # 0..1 — как часто враг ищет путь в обход стен, а не прёт напрямик
    memory: float         # сколько секунд враг помнит, где видел игрока
    avoid_danger: float   # 0..1 — как часто враг обходит бомбы и огонь
    life_chance: float    # шанс, что под стеной «жизнь», а не ловушка «смерть»


def _clamp(value: float, low: float, high: float) -> float:
    return max(low, min(high, value))


def for_level(level: int, players: int = 1) -> LevelSettings:
    n = level - 1  # сколько уровней уже пройдено
    enemies = min(2 + int(0.6 * n + 0.5), 10)
    if players == 2:
        enemies += 1  # вдвоём чуть веселее
    return LevelSettings(
        level=level,
        walls=min(40 + 2 * n, 70),
        enemies=enemies,
        enemy_tier=min(n // 3, 3),
        enemy_speed=round(min(1.5 + 0.07 * n, PLAYER_SPEED * 0.8), 2),
        sight=min(2.5 + 0.5 * n, 9.0),
        smart=round(_clamp(0.1 * (level - 2), 0.0, 0.85), 2),
        memory=round(min(0.4 * n, 4.0), 1),
        avoid_danger=round(_clamp(0.12 * (level - 3), 0.0, 0.9), 2),
        life_chance=1.0 if level <= 3 else 0.5,
    )


def table(levels: int = 15, players: int = 1) -> list[dict]:
    return [asdict(for_level(level, players)) for level in range(1, levels + 1)]


if __name__ == "__main__":
    rows = table()
    print("  ".join(f"{key:>12}" for key in rows[0]))
    for row in rows:
        print("  ".join(f"{value:>12}" for value in row.values()))
