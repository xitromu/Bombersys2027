"""Как растёт сложность от уровня к уровню.

Это главный файл для настройки баланса. Всё растёт плавно и упирается в потолок,
чтобы до 10-го уровня мог дойти любой игрок. Посмотреть таблицу по уровням:
    uv run python -m app.game.difficulty
"""

from __future__ import annotations

from dataclasses import asdict, dataclass

from .config import PLAYER_SPEED

# Насколько «сильный» враг лучше обычного врага своего уровня — за каждую ступень вида.
TIER_BONUS = {"speed": 0.2, "sight": 1.5, "smart": 0.15, "memory": 1.0, "avoid_danger": 0.15}


@dataclass(frozen=True)
class LevelSettings:
    level: int
    walls: int            # разрушаемых стен на поле
    enemies: int          # сколько врагов
    enemy_tier: int       # вид обычных врагов 0..3 (зелёный → оранжевый → красный → фиолетовый)
    strong_enemies: int   # сколько из них на ступень сильнее (и дороже по очкам)
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
        strong_enemies=enemies // 3 if level >= 2 and n // 3 < 3 else 0,
        enemy_speed=round(min(1.5 + 0.07 * n, PLAYER_SPEED * 0.8), 2),
        sight=min(2.5 + 0.5 * n, 9.0),
        smart=round(_clamp(0.1 * (level - 2), 0.0, 0.85), 2),
        memory=round(min(0.4 * n, 4.0), 1),
        avoid_danger=round(_clamp(0.12 * (level - 3), 0.0, 0.9), 2),
        life_chance=1.0 if level <= 3 else 0.5,
    )


@dataclass(frozen=True)
class EnemyStats:
    tier: int
    speed: float
    sight: float
    smart: float
    memory: float
    avoid_danger: float


def enemy_stats(settings: LevelSettings, strong: bool = False) -> EnemyStats:
    """Параметры конкретного врага: обычного для уровня или «сильного» (на ступень выше)."""
    tier = min(settings.enemy_tier + (1 if strong else 0), 3)
    k = tier - settings.enemy_tier
    return EnemyStats(
        tier=tier,
        speed=round(min(settings.enemy_speed + TIER_BONUS["speed"] * k, PLAYER_SPEED * 0.85), 2),
        sight=settings.sight + TIER_BONUS["sight"] * k,
        smart=round(min(settings.smart + TIER_BONUS["smart"] * k, 0.95), 2),
        memory=settings.memory + TIER_BONUS["memory"] * k,
        avoid_danger=round(min(settings.avoid_danger + TIER_BONUS["avoid_danger"] * k, 0.95), 2),
    )


def table(levels: int = 15, players: int = 1) -> list[dict]:
    return [asdict(for_level(level, players)) for level in range(1, levels + 1)]


if __name__ == "__main__":
    rows = table()
    print("  ".join(f"{key:>12}" for key in rows[0]))
    for row in rows:
        print("  ".join(f"{value:>12}" for value in row.values()))
