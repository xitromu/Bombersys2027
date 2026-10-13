"""Собирает картинки героев для игры из кадров Blender.

Запуск из корня проекта (питоном, встроенным в Blender, — в нём есть numpy):
    C:\\Blender\\blender.exe -b --factory-startup --python-exit-code 1 -P tools/build_hero.py

Откуда берёт: mockups/hero/out — кадры бега (набор P) и гибели (набор D), их рисует
mockups/hero/hero_render.py. Папка mockups в репозиторий не входит.

Что делает с каждым кадром — то же, что страницы-макеты mockups/hero/index.html и death.html:
  * накладывает линии между частями тела;
  * при «суперсмерти» затемняет героя копотью — чем дальше, тем сильнее;
  * уменьшает до размера игры;
  * обводит тёмным контуром.

Что получается:
  frontend/assets/hero<N>.png        бег: строка — направление, 20 кадров и в конце «стоит»
  frontend/assets/hero<N>_death.png  гибель: строка — вид гибели и направление
  frontend/js/heroMeta.js            размеры кадров, точки привязки и таблицы гибели для экрана игры
"""

from __future__ import annotations

import json
import math
import re
import struct
import sys
import zlib
from pathlib import Path

import bpy
import numpy as np

ROOT = Path(__file__).resolve().parent.parent
SRC = ROOT / "mockups" / "hero" / "out"
ASSETS = ROOT / "frontend" / "assets"
META_JS = ROOT / "frontend" / "js" / "heroMeta.js"

UNIT = 46.0                      # точек экрана в «единице роста» героя
FEET = 18                        # ступни стоящего героя ниже центра клетки на столько точек
OUTLINE = 0.75                   # толщина контура, точек экрана
MARGIN = math.ceil(OUTLINE) + 1  # поля кадра под контур
DARK = (0x12, 0x0D, 0x0A)        # цвет контура
SOOT = (0x17, 0x11, 0x0D)        # цвет копоти
DIRS = ["right", "left", "up", "down"]
# Виды гибели: название, в какую сторону от середины тела лежит голова (туда сдвинута лужа крови), с копотью ли.
DEATHS = [("knees", 1, False), ("thrown", -1, True), ("flip", -1, True), ("rocket", 1, True)]


# ---------------------------------------------------------------- чтение и запись картинок

def load(name: str) -> np.ndarray:
    """Картинка как массив высота × ширина × 4 (RGBA, 0..1, верхняя строка первой)."""
    image = bpy.data.images.load(str(SRC / name))
    width, height = image.size
    pixels = np.empty(width * height * 4, dtype=np.float32)
    image.pixels.foreach_get(pixels)
    bpy.data.images.remove(image)
    return pixels.reshape(height, width, 4)[::-1].astype(np.float64)


def save_png(path: Path, rgba: np.ndarray) -> None:
    height, width, _ = rgba.shape
    data = np.clip(np.rint(rgba * 255), 0, 255).astype(np.uint8)
    rows = np.concatenate([np.zeros((height, 1), np.uint8), data.reshape(height, width * 4)], axis=1)

    def chunk(kind: bytes, body: bytes) -> bytes:
        return struct.pack(">I", len(body)) + kind + body + struct.pack(">I", zlib.crc32(kind + body))

    header = struct.pack(">IIBBBBB", width, height, 8, 6, 0, 0, 0)
    path.write_bytes(b"\x89PNG\r\n\x1a\n" + chunk(b"IHDR", header)
                     + chunk(b"IDAT", zlib.compress(rows.tobytes(), 9)) + chunk(b"IEND", b""))


# ---------------------------------------------------------------- обработка кадра

def over(top: np.ndarray, bottom: np.ndarray) -> np.ndarray:
    """Кладёт одну картинку поверх другой с учётом прозрачности."""
    ta, ba = top[..., 3:], bottom[..., 3:]
    alpha = ta + ba * (1 - ta)
    color = (top[..., :3] * ta + bottom[..., :3] * ba * (1 - ta)) / np.maximum(alpha, 1e-9)
    return np.concatenate([color, alpha], axis=2)


_weights: dict[tuple[int, int], np.ndarray] = {}


def weights(source: int, target: int) -> np.ndarray:
    """Таблица уменьшения по одной оси (фильтр Ланцоша): строка — точка результата, столбец — точка исходника."""
    key = (source, target)
    if key not in _weights:
        scale = source / target
        centers = (np.arange(target) + 0.5) * scale
        x = (np.arange(source) + 0.5 - centers[:, None]) / scale
        table = np.where(np.abs(x) < 3, np.sinc(x) * np.sinc(x / 3), 0.0)
        _weights[key] = table / table.sum(axis=1, keepdims=True)
    return _weights[key]


def shrink(image: np.ndarray, size: int) -> np.ndarray:
    table = weights(image.shape[0], size)
    alpha = image[..., 3]
    small_alpha = np.clip(table @ alpha @ table.T, 0, 1)
    out = np.zeros((size, size, 4))
    for c in range(3):   # цвет усредняем с весом прозрачности, иначе по краям фигуры будет тёмная кайма
        out[..., c] = np.clip(table @ (image[..., c] * alpha) @ table.T, 0, 1) / np.maximum(small_alpha, 1e-6)
    out[..., :3] = np.clip(out[..., :3], 0, 1)
    out[..., 3] = small_alpha
    return out


def shifted(alpha: np.ndarray, dx: float, dy: float) -> np.ndarray:
    """Сдвиг на дробное число точек (поля кадра шире сдвига, так что за край ничего не уходит)."""
    def along(a: np.ndarray, d: float, axis: int) -> np.ndarray:
        whole = math.floor(d)
        part = d - whole
        return (1 - part) * np.roll(a, whole, axis) + part * np.roll(a, whole + 1, axis)
    return along(along(alpha, dx, 1), dy, 0)


def outlined(figure: np.ndarray) -> np.ndarray:
    """Кадр с полями и тёмным контуром: силуэт, сдвинутый по кругу, а поверх него сама фигура."""
    size = figure.shape[0]
    frame = np.zeros((size + 2 * MARGIN, size + 2 * MARGIN, 4))
    frame[MARGIN:-MARGIN, MARGIN:-MARGIN] = figure
    clear = np.ones(frame.shape[:2])
    for k in range(12):
        angle = k / 12 * 2 * math.pi
        clear *= 1 - shifted(frame[..., 3], math.cos(angle) * OUTLINE, math.sin(angle) * OUTLINE)
    edge = np.empty_like(frame)
    edge[..., :3] = np.array(DARK) / 255
    edge[..., 3] = 1 - clear
    return over(frame, edge)


def game_frame(name: str, lines: str, size: int, soot: float = 0.0) -> np.ndarray:
    figure = over(load(lines), load(name))
    if soot > 0:
        figure[..., :3] = figure[..., :3] * (1 - soot) + np.array(SOOT) / 255 * soot
    return outlined(shrink(figure, size))


def sheet(rows: list[list[np.ndarray]]) -> np.ndarray:
    """Лист кадров: строки — как в списке, недостающие кадры в конце строки пустые."""
    side = rows[0][0].shape[0]
    columns = max(len(row) for row in rows)
    out = np.zeros((side * len(rows), side * columns, 4))
    for r, row in enumerate(rows):
        for c, frame in enumerate(row):
            out[r * side:(r + 1) * side, c * side:(c + 1) * side] = frame
    return out


# ---------------------------------------------------------------- сборка

def rest_shift(frame: np.ndarray, origin: list[float]) -> list[float]:
    """На сколько точек сдвинуть лежащее тело, чтобы оно оказалось посередине клетки.

    Blender держит картинку за точку на полу под бёдрами, а тело с руками и шапкой лежит от неё не поровну
    в разные стороны — без поправки голова или руки заходили бы на соседнюю клетку."""
    rows, columns = np.nonzero(frame[..., 3] > 0.4)
    side = frame.shape[0]
    return [round(origin[0] * side - (columns.min() + columns.max() + 1) / 2, 1),
            round(origin[1] * side - (rows.min() + rows.max() + 1) / 2, 1)]


def smooth(u: float) -> float:
    return u * u * (3 - 2 * u)


def death_table(meta: dict, name: str) -> dict:
    """Что экрану игры надо знать про каждый кадр гибели (расчёты — как в макете death.html)."""
    frames = meta["deaths"][name]
    landed = next(i for i, f in enumerate(frames) if f["z"] <= meta["z_lie"] + 0.06)
    table = []
    for i, f in enumerate(frames):
        ground = meta["z_stand"] * (1 - f["flat"]) + meta["z_lie"] * f["flat"]
        air = max(0.0, f["z"] - ground)
        table.append([
            round(f["shift"] * UNIT, 1),                                  # сдвиг вдоль взгляда, точек
            round(smooth(min(1.0, i / landed)), 3),                       # насколько лёг: 0 — стоит, 1 — лежит
            round(0.30 * max(1 - f["flat"], min(1.0, air / 0.15)), 3),    # прозрачность тени
            round(1 / (1 + air * 0.9), 3),                                # размер тени: в воздухе — мельче
        ])
    return {"landed": round(landed / meta["fps"], 3), "frames": table}


def main() -> None:
    run_meta = json.loads((SRC / "meta_P.json").read_text(encoding="utf-8"))
    text = (SRC / "death_meta.js").read_text(encoding="utf-8")
    death_meta = json.loads(text[text.index("{"):].rstrip().rstrip(";"))

    run_size = round(run_meta["size"] * UNIT / run_meta["unit_px"])
    death_size = round(death_meta["size"] * UNIT / death_meta["unit_px"])
    count = run_meta["frames"]

    def origin(anchor: list[float], size: int) -> list[float]:
        return [round((a * size + MARGIN) / (size + 2 * MARGIN), 4) for a in anchor]

    death_origin = origin(death_meta["anchor"], death_size)
    rest: dict[str, list] = {name: [] for name, _, _ in DEATHS}   # поправка лежащему: по видам гибели и направлениям

    for n in (1, 2):
        rows = []
        for facing in DIRS:
            labels = [f"run_{i:02d}" for i in range(count)] + ["idle"]
            rows.append([game_frame(f"P_p{n}_{facing}_{label}.png", f"PL_p{n}_{facing}_{label}.png", run_size)
                         for label in labels])
            print(f"PROGRESS hero {n}: run {facing}", flush=True)
        save_png(ASSETS / f"hero{n}.png", sheet(rows))

        rows = []
        for name, _, sooty in DEATHS:
            for facing in DIRS:
                rows.append([
                    game_frame(f"D_p{n}_{facing}_{name}_{i:02d}.png", f"DL_p{n}_{facing}_{name}_{i:02d}.png",
                               death_size, min(0.55, 0.28 * i) if sooty else 0.0)
                    for i in range(len(death_meta["deaths"][name]))
                ])
                if n == 1:   # герои одного сложения — поправку меряем по Ивану
                    rest[name].append(rest_shift(rows[-1][-1], death_origin))
                print(f"PROGRESS hero {n}: death {name} {facing}", flush=True)
        save_png(ASSETS / f"hero{n}_death.png", sheet(rows))

    meta = {
        "feet": FEET,
        "dirs": DIRS,
        "run": {
            "frame": run_size + 2 * MARGIN,
            "origin": origin(run_meta["anchor"]["right"], run_size),
            "frames": count,                                              # кадров бега; следующий за ними — «стоит»
            "cycle": round(run_meta["cycle_units"] * UNIT, 2),            # точек пути на один круг бега
        },
        "death": {
            "frame": death_size + 2 * MARGIN,
            "origin": death_origin,
            "columns": max(len(death_meta["deaths"][name]) for name, _, _ in DEATHS),
            "fps": death_meta["fps"],
            "pool": round(0.28 * UNIT, 1),                                # лужа крови сдвинута к голове на столько точек
            "kinds": {name: {"row": 4 * k, "head": head, "rest": rest[name], **death_table(death_meta, name)}
                      for k, (name, head, _) in enumerate(DEATHS)},
        },
    }
    # списки чисел — в одну строку, иначе таблицы гибели растягиваются на сотни строк
    body = re.sub(r"\[[^\[\]{}]*\]", lambda m: " ".join(m.group().split()).replace("[ ", "[").replace(" ]", "]"),
                  json.dumps(meta, ensure_ascii=False, indent=2))
    lines = [
        "// Размеры и таблицы картинок героя. Файл пишет tools/build_hero.py — руками не править.",
        "// Гибель, кадр за кадром: [сдвиг вдоль взгляда, насколько лёг (0..1), прозрачность тени, размер тени].",
        "// rest — на сколько точек [x, y] сдвинуть лежащее тело, чтобы оно было посередине клетки; по направлениям dirs.",
        "",
        f"export const HERO = {body};",
        "",
    ]
    META_JS.write_text("\n".join(lines), encoding="utf-8", newline="\r\n")
    print("DONE", flush=True)


if __name__ == "__main__":   # Blender запускает файл именно так; при import (из макетов) сборка не начинается
    try:
        main()
    except Exception:
        import traceback
        traceback.print_exc()
        sys.exit(1)
