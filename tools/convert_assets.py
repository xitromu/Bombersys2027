"""Перегоняет старую графику (legacy/*.bmp) в PNG для браузера.

Запуск из корня проекта:  python tools/convert_assets.py

Что делает:
  * читает BMP (24 и 8 бит) без сторонних библиотек;
  * у спрайтов белый цвет RGB(255,255,255) превращает в прозрачный —
    в 2005 году так работал TransparentBlt, теперь это альфа-канал PNG;
  * вырезает из фоновых текстур кусок под игровое поле;
  * рисует спрайты врагов (в оригинале их не было).
"""

from __future__ import annotations

import math
import struct
import zlib
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
SRC = ROOT / "legacy"
DST = ROOT / "frontend" / "assets"

FIELD = 15 * 49  # поле 15×15 клеток по 49 пикселей


# ---------------------------------------------------------------- BMP / PNG

def load_bmp(name: str) -> tuple[int, int, list[list[tuple[int, int, int]]]]:
    data = (SRC / name).read_bytes()
    offset = struct.unpack("<I", data[10:14])[0]
    width, height = struct.unpack("<ii", data[18:26])
    bpp = struct.unpack("<H", data[28:30])[0]
    rows = []
    if bpp == 8:
        colors = struct.unpack("<I", data[46:50])[0] or 256
        palette = [tuple(data[54 + 4 * i: 57 + 4 * i][::-1]) for i in range(colors)]
        stride = (width + 3) & ~3
        for y in range(abs(height)):
            line = data[offset + y * stride: offset + y * stride + width]
            rows.append([palette[c] for c in line])
    elif bpp == 24:
        stride = (width * 3 + 3) & ~3
        for y in range(abs(height)):
            line = data[offset + y * stride: offset + y * stride + width * 3]
            rows.append([(line[i + 2], line[i + 1], line[i]) for i in range(0, len(line), 3)])
    else:
        raise ValueError(f"{name}: {bpp}-битные BMP не поддерживаются")
    if height > 0:  # BMP хранится снизу вверх
        rows.reverse()
    return width, abs(height), rows


def save_png(name: str, rows: list[list[tuple[int, ...]]]) -> None:
    height, width = len(rows), len(rows[0])
    raw = b"".join(b"\0" + bytes(c for px in row for c in px) for row in rows)

    def chunk(tag: bytes, body: bytes) -> bytes:
        return struct.pack(">I", len(body)) + tag + body + struct.pack(">I", zlib.crc32(tag + body))

    header = struct.pack(">IIBBBBB", width, height, 8, 6, 0, 0, 0)  # RGBA
    png = b"\x89PNG\r\n\x1a\n" + chunk(b"IHDR", header) + chunk(b"IDAT", zlib.compress(raw, 9)) + chunk(b"IEND", b"")
    (DST / name).write_bytes(png)


def convert(src: str, dst: str, transparent: bool = False, crop: tuple[int, int, int, int] | None = None) -> None:
    _, _, rows = load_bmp(src)
    if crop:
        x, y, w, h = crop
        rows = [row[x:x + w] for row in rows[y:y + h]]
    out = [[(r, g, b, 0 if transparent and (r, g, b) == (255, 255, 255) else 255) for r, g, b in row] for row in rows]
    save_png(dst, out)
    print(f"  {src:16} -> {dst}")


# ---------------------------------------------------------------- враги

ENEMY_TIERS = [  # (цвет тела, брови, рот, рога) — от добродушного к злобному
    ((96, 196, 88), False, False, False),
    ((238, 150, 42), True, False, False),
    ((214, 52, 52), True, True, False),
    ((148, 72, 214), True, True, True),
]


def _over(dst: list[float], color: tuple[float, float, float], alpha: float) -> None:
    """Накладывает цвет поверх пикселя (обычное альфа-смешивание)."""
    if alpha <= 0:
        return
    out_a = alpha + dst[3] * (1 - alpha)
    for i in range(3):
        dst[i] = (color[i] * alpha + dst[i] * dst[3] * (1 - alpha)) / out_a
    dst[3] = out_a


def _enemy_sample(x: float, y: float, tier: int, frame: int) -> list[float]:
    body, brows, mouth, horns = ENEMY_TIERS[tier]
    phase = 2 * math.pi * frame / 4
    bob = 1.5 * math.sin(phase)       # подпрыгивание
    squash = math.sin(phase)          # сплющивание
    cx, cy = 24.5, 25.5 - bob
    rx, ry = 16 + 1.2 * squash, 14.5 - 1.2 * squash
    bottom = 40.5 + 1.4 * math.sin(x * 0.75 + phase)  # волнистый «подол»

    def inside(px: float, py: float) -> bool:
        if py <= cy:
            return ((px - cx) / rx) ** 2 + ((py - cy) / ry) ** 2 <= 1
        return abs(px - cx) <= rx and py <= bottom

    pix = [0.0, 0.0, 0.0, 0.0]
    # тень
    if ((x - 24.5) / 15) ** 2 + ((y - 44) / 3.6) ** 2 <= 1:
        _over(pix, (0, 0, 0), 0.35)
    # рога
    if horns:
        for hx in (15.5, 33.5):
            top = cy - ry - 5
            if top <= y <= cy - ry + 5 and abs(x - hx) <= (y - top) * 0.45:
                _over(pix, (235, 225, 200), 1)
    if inside(x, y):
        edge = not all(inside(x + dx, y + dy) for dx, dy in ((1.6, 0), (-1.6, 0), (0, 1.6), (0, -1.6)))
        shade = 1.15 - 0.45 * max(0.0, min(1.0, (y - (cy - ry)) / (bottom - cy + ry)))
        color = tuple(min(255, c * shade) for c in body)
        _over(pix, tuple(c * 0.45 for c in body) if edge else color, 1)
        # блик
        if ((x - 17) / 5) ** 2 + ((y - (cy - 8)) / 3) ** 2 <= 1:
            _over(pix, (255, 255, 255), 0.45)
        # Глаз здесь нет: их рисует браузер поверх (frontend/js/enemyEyes.js),
        # чтобы они краснели и следили за игроком. Центры глаз: x = 18.5 и 30.5, y = cy - 1.
        # сердитые брови
        if brows:
            for ex, sign in ((18.5, 1), (30.5, -1)):
                bx0, by0, bx1, by1 = ex - 5 * sign, cy - 9, ex + 4 * sign, cy - 5.5
                t = max(0.0, min(1.0, ((x - bx0) * (bx1 - bx0) + (y - by0) * (by1 - by0)) / ((bx1 - bx0) ** 2 + (by1 - by0) ** 2)))
                if math.hypot(x - bx0 - t * (bx1 - bx0), y - by0 - t * (by1 - by0)) <= 1.3:
                    _over(pix, (25, 15, 15), 1)
        # оскал
        if mouth and ((x - 24.5) / 6.5) ** 2 + ((y - (cy + 8)) / 2.6) ** 2 <= 1:
            teeth = y < cy + 8 and int(x) % 3 != 0
            _over(pix, (250, 250, 240) if teeth else (60, 10, 10), 1)
    return pix


def draw_enemies() -> None:
    """Лист 196×196: строка = тип врага (0..3), столбец = кадр анимации (0..3)."""
    size, ss = 49, 3  # ss×ss подвыборок на пиксель — сглаживание краёв
    sheet = [[(0, 0, 0, 0)] * (size * 4) for _ in range(size * 4)]
    for tier in range(4):
        for frame in range(4):
            for py in range(size):
                for px in range(size):
                    acc = [0.0, 0.0, 0.0, 0.0]
                    for sy in range(ss):
                        for sx in range(ss):
                            r, g, b, a = _enemy_sample(px + (sx + 0.5) / ss, py + (sy + 0.5) / ss, tier, frame)
                            acc[0] += r * a
                            acc[1] += g * a
                            acc[2] += b * a
                            acc[3] += a
                    n = ss * ss
                    alpha = acc[3] / n
                    color = tuple(int(acc[i] / acc[3]) if acc[3] else 0 for i in range(3))
                    sheet[tier * size + py][frame * size + px] = (*color, int(alpha * 255))
    save_png("enemies.png", sheet)
    print("  (нарисованы)      -> enemies.png")


# ---------------------------------------------------------------- список

SPRITES = {  # с прозрачным белым фоном
    "PLAYER1.bmp": "player1.png",
    "PLAYER2.bmp": "player2.png",
    "TRUP1.bmp": "death1.png",
    "TRUP2.bmp": "death2.png",
    "SUPERTRUP1.bmp": "superdeath1.png",
    "SUPERTRUP2.bmp": "superdeath2.png",
    "Bomb1.bmp": "bomb1.png",
    "Bomb2.bmp": "bomb2.png",
    "Bumbomb.bmp": "explosion.png",
    "bum1.bmp": "flame_near.png",
    "bum2.bmp": "flame_far.png",
    "door.bmp": "item_door.png",
    "sunduk.bmp": "item_chest.png",
    "bomba.bmp": "item_bomb.png",
    "live.bmp": "item_life.png",
    "smert.bmp": "item_death.png",
    "meshok.bmp": "item_bag.png",
    "bigmeshok.bmp": "item_bigbag.png",
    "bruliki.bmp": "item_gems.png",
    "nasledstvo.bmp": "item_legacy.png",
}

PICTURES = {  # непрозрачные картинки целиком (заставка start.bmp — кадр из «Мумии» — не переносится)
    "gameover.bmp": "gameover.png",
    "3.bmp": "panel.png",
    "plus.bmp": "level_box.png",
    "plus1.bmp": "stats1.png",
    "plus2.bmp": "stats2.png",
    "FACE.bmp": "face1.png",
    "FACE1.bmp": "face2.png",
    "Pause.bmp": "pause.png",
    "Pause1.bmp": "ready.png",
}

TEXTURES = {  # вырезаем кусок размером с поле
    "POL.bmp": "floor.png",
    "2.bmp": "walls.png",
    "22.bmp": "pillars.png",
}


def main() -> None:
    DST.mkdir(parents=True, exist_ok=True)
    print(f"Из {SRC} в {DST}:")
    for src, dst in SPRITES.items():
        convert(src, dst, transparent=True)
    for src, dst in PICTURES.items():
        convert(src, dst)
    for src, dst in TEXTURES.items():
        convert(src, dst, crop=(4, 4, FIELD, FIELD))
    draw_enemies()


if __name__ == "__main__":
    main()
