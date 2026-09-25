"""Рисует иконку игры — бомбу с горящим фитилём — без сторонних библиотек.

Запуск из корня проекта:  python tools/make_icon.py

Результат:
  backend/packaging/bombersys.ico  — иконка BOMBERSYS.exe (размеры 16…256)
  frontend/assets/icon.png         — значок вкладки браузера
"""

from __future__ import annotations

import math
import struct
import zlib
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
ICO = ROOT / "backend" / "packaging" / "bombersys.ico"
PNG = ROOT / "frontend" / "assets" / "icon.png"
SIZES = [16, 24, 32, 48, 64, 128, 256]

BODY = (0.44, 0.60, 0.35)     # центр и радиус бомбы (в долях размера иконки)
SPARK = (0.84, 0.15)          # где горит искра


def _over(dst: list[float], color: tuple[float, float, float], alpha: float) -> None:
    if alpha <= 0:
        return
    alpha = min(alpha, 1.0)
    out = alpha + dst[3] * (1 - alpha)
    for i in range(3):
        dst[i] = (color[i] * alpha + dst[i] * dst[3] * (1 - alpha)) / out
    dst[3] = out


def _segment_distance(px, py, ax, ay, bx, by) -> float:
    t = max(0.0, min(1.0, ((px - ax) * (bx - ax) + (py - ay) * (by - ay)) / ((bx - ax) ** 2 + (by - ay) ** 2)))
    return math.hypot(px - ax - t * (bx - ax), py - ay - t * (by - ay))


def _fuse_distance(u: float, v: float) -> float:
    """Фитиль — плавная кривая из горлышка бомбы к искре (ломаная из 12 отрезков)."""
    points = []
    for i in range(13):
        t = i / 12
        # квадратичная кривая Безье: горлышко → изгиб → искра
        x = (1 - t) ** 2 * 0.68 + 2 * (1 - t) * t * 0.80 + t * t * SPARK[0]
        y = (1 - t) ** 2 * 0.32 + 2 * (1 - t) * t * 0.30 + t * t * SPARK[1]
        points.append((x, y))
    return min(_segment_distance(u, v, *a, *b) for a, b in zip(points, points[1:]))


def sample(u: float, v: float) -> list[float]:
    """Цвет точки (u, v) иконки, координаты от 0 до 1."""
    pix = [0.0, 0.0, 0.0, 0.0]
    cx, cy, r = BODY

    # тёплое свечение вокруг искры
    d_spark = math.hypot(u - SPARK[0], v - SPARK[1])
    if d_spark < 0.2:
        _over(pix, (255, 170, 40), 0.45 * (1 - d_spark / 0.2) ** 2)

    # горлышко бомбы — квадрат, повёрнутый по направлению к фитилю
    nx, ny = u - 0.66, v - 0.34
    a = math.radians(45)
    lx, ly = nx * math.cos(a) - ny * math.sin(a), nx * math.sin(a) + ny * math.cos(a)
    if abs(lx) < 0.085 and abs(ly) < 0.07:
        edge = abs(lx) > 0.07 or abs(ly) > 0.055
        _over(pix, (40, 42, 50) if edge else (120, 126, 140), 1)

    # тело бомбы: тёмный шар с объёмом, светлым ободком и бликом
    d = math.hypot(u - cx, v - cy)
    if d < r:
        light = max(0.0, 1 - math.hypot(u - (cx - r * 0.4), v - (cy - r * 0.4)) / (r * 1.6))
        base = 28 + 70 * light ** 1.5
        _over(pix, (base, base + 3, base + 12), 1)
        if d > r - 0.022:
            _over(pix, (190, 195, 210), 0.9)          # ободок — чтобы бомба была видна на тёмном фоне
        if ((u - (cx - r * 0.42)) / (r * 0.28)) ** 2 + ((v - (cy - r * 0.45)) / (r * 0.16)) ** 2 < 1:
            _over(pix, (255, 255, 255), 0.75)         # блик

    # фитиль
    fd = _fuse_distance(u, v)
    if fd < 0.03:
        _over(pix, (70, 45, 25) if fd > 0.018 else (200, 160, 100), 1)

    # искра — звёздочка из восьми лучей
    ang = math.atan2(v - SPARK[1], u - SPARK[0])
    reach = 0.045 + 0.075 * abs(math.cos(4 * ang)) ** 6
    if d_spark < reach:
        _over(pix, (255, 200, 40), 1)
        if d_spark < 0.04:
            _over(pix, (255, 250, 210), 1)
    return pix


def render(size: int) -> list[list[tuple[int, int, int, int]]]:
    ss = 4 if size <= 64 else 3  # сглаживание: несколько проб на пиксель
    rows = []
    for py in range(size):
        row = []
        for px in range(size):
            acc = [0.0, 0.0, 0.0, 0.0]
            for sy in range(ss):
                for sx in range(ss):
                    r, g, b, a = sample((px + (sx + 0.5) / ss) / size, (py + (sy + 0.5) / ss) / size)
                    acc[0] += r * a
                    acc[1] += g * a
                    acc[2] += b * a
                    acc[3] += a
            alpha = acc[3] / (ss * ss)
            color = [int(acc[i] / acc[3]) if acc[3] else 0 for i in range(3)]
            row.append((*color, int(alpha * 255)))
        rows.append(row)
    return rows


def png_bytes(rows: list[list[tuple[int, int, int, int]]]) -> bytes:
    height, width = len(rows), len(rows[0])
    raw = b"".join(b"\0" + bytes(c for px in row for c in px) for row in rows)

    def chunk(tag: bytes, body: bytes) -> bytes:
        return struct.pack(">I", len(body)) + tag + body + struct.pack(">I", zlib.crc32(tag + body))

    header = struct.pack(">IIBBBBB", width, height, 8, 6, 0, 0, 0)
    return b"\x89PNG\r\n\x1a\n" + chunk(b"IHDR", header) + chunk(b"IDAT", zlib.compress(raw, 9)) + chunk(b"IEND", b"")


def ico_bytes(images: list[tuple[int, bytes]]) -> bytes:
    """ICO-файл с PNG внутри (так умеет Windows начиная с Vista)."""
    header = struct.pack("<HHH", 0, 1, len(images))
    offset = 6 + 16 * len(images)
    entries, data = b"", b""
    for size, png in images:
        dim = 0 if size >= 256 else size
        entries += struct.pack("<BBBBHHII", dim, dim, 0, 0, 1, 32, len(png), offset + len(data))
        data += png
    return header + entries + data


def main() -> None:
    images = [(size, png_bytes(render(size))) for size in SIZES]
    ICO.parent.mkdir(parents=True, exist_ok=True)
    ICO.write_bytes(ico_bytes(images))
    PNG.write_bytes(dict(images)[64])
    print(f"  {ICO}\n  {PNG}")


if __name__ == "__main__":
    main()
