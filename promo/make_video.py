"""Собирает промо-ролик BOMBERSYS в духе рекламы игровых автоматов 80–90-х: 1280×720, 30 кадров в секунду, H.264 + AAC.

  python -I -u promo/make_video.py                   весь ролик → promo/out/BOMBERSYS-promo.mp4
  python -I -u promo/make_video.py --still 7.5,20.5  только отдельные кадры → promo/work/stills/

Материалы (promo/work, в git не входят) готовят: capture.py — настоящая игра, render_logo.py и render_heroes.py — Blender,
render_audio.py — музыка и звуки на синтезаторе игры, voice.py — голос диктора. Монтаж идёт по тактам мелодии: такт 1,5 с.
Пиксельный шрифт — 8×8, строки экрана — 240, как у настоящего автомата: при высоте 720 одна строка занимает три точки.
"""

import bisect
import json
import math
import random
import sys
import time
import wave
from fractions import Fraction
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))

import av  # noqa: E402
import numpy as np  # noqa: E402
from PIL import Image, ImageChops, ImageDraw, ImageFilter  # noqa: E402

from pixfont import PixFont  # noqa: E402

ROOT = HERE.parent
WORK = HERE / "work"
OUT = HERE / "out"
W, H, FPS, RATE = 1280, 720, 30, 48000
BAR = 1.5
NET_AT = 21 * BAR + 0.75   # реплика «или по сети»: отсюда на экране два ноутбука
TOTAL = 54.9
VERSION = "0.5.0"
URL = "github.com/xitromu/Bombersys2027"
SPEAKER = "eugene"

F8 = PixFont(r"C:\Windows\Fonts\cga80866.fon")

FIRE = ["#fff7b0", "#ffe45c", "#ffc21a", "#ff9a0a", "#ff6a00", "#f03a00", "#c81e10", "#8a0f20"]
ICE = ["#ffffff", "#d8f6ff", "#9fe8ff", "#5cc8ff", "#2a96ff", "#1a62e6", "#1a3ab8", "#20208a"]
PINK = ["#ffffff", "#ffd0f0", "#ff9ae0", "#ff5ac8", "#ff2aa8", "#e0108c", "#a00a78", "#600860"]
LIME = ["#f0ffe0", "#c8ffa0", "#99ff66", "#66e640", "#3cc828", "#20a018", "#107810", "#0a500a"]
GOLD = ["#ffffff", "#fff8c0", "#ffe870", "#ffd030", "#ffb000", "#e08800", "#b06000", "#804000"]
BLOOD = ["#ffd0c0", "#ff9080", "#ff5040", "#ff2010", "#e00808", "#b00000", "#800000", "#500000"]
WHITE = ["#ffffff"] * 8
GREY = ["#c8c8d8"] * 8
IVAN, IGOR = "#66ccff", "#99ff66"
DARKRED = ["#e01000"] * 4 + ["#a80000"] * 4


def rgb(color):
    return tuple(int(color[i:i + 2], 16) for i in (1, 3, 5))


# ------------------------------------------------------------------ текст

_sprites = {}


def sprite(text, scale, pal=WHITE, outline=True):
    key = (text, scale, tuple(pal), outline)
    if key in _sprites:
        return _sprites[key]
    mask = F8.mask(text)
    big = np.kron(mask, np.ones((scale, scale), dtype=bool))
    pad = max(2, scale // 2) + scale if outline else 0
    h, w = big.shape
    out = np.zeros((h + pad * 2, w + pad * 2, 4), dtype=np.uint8)
    if outline:
        edge = np.zeros(out.shape[:2], dtype=bool)
        d = max(2, scale // 2)
        for dx in (-d, 0, d):
            for dy in (-d, 0, d):
                edge[pad + dy:pad + dy + h, pad + dx:pad + dx + w] |= big
        out[edge] = (10, 0, 30, 255)
        out[pad + scale:pad + scale + h, pad + scale:pad + scale + w][big] = (40, 0, 70, 255)
    colors = np.array([rgb(c) for c in pal], dtype=np.uint8)
    rows = colors[np.minimum(np.arange(h) * len(pal) // h, len(pal) - 1)]
    area = out[pad:pad + h, pad:pad + w]
    area[big, :3] = np.repeat(rows[:, None, :], w, axis=1)[big]
    area[big, 3] = 255
    im = Image.fromarray(out, "RGBA")
    _sprites[key] = im
    return im


def put(img, spr, cx, cy):
    img.paste(spr, (int(cx - spr.width / 2), int(cy - spr.height / 2)), spr)


def slam(img, spr, cx, cy, age, length=0.13):
    """Надпись влетает из экрана и бьёт по стеклу."""
    if age < length:
        k = 1 + 0.8 * (1 - age / length) ** 2
        spr = spr.resize((int(spr.width * k), int(spr.height * k)), Image.NEAREST)
    put(img, spr, cx, cy)


def blink(t, rate=3.0):
    return (t * rate) % 1 < 0.6


# ------------------------------------------------------------------ фоны

rng = random.Random(1987)
HORIZON = 400


def make_sky():
    a = np.zeros((H, W, 3), dtype=np.float32)
    top, mid, low = np.array(rgb("#05021c")), np.array(rgb("#2a0a5e")), np.array(rgb("#c81a7a"))
    for y in range(HORIZON):
        u = y / HORIZON
        a[y] = top + (mid - top) * (u / 0.6) if u < 0.6 else mid + (low - mid) * ((u - 0.6) / 0.4) ** 1.5
    a[HORIZON:] = np.array(rgb("#0a0220"))
    for _ in range(170):
        x, y = rng.randrange(W), rng.randrange(HORIZON - 80)
        a[y:y + 3, x:x + 3] = rng.choice([(255, 255, 255), (180, 220, 255), (255, 200, 240)])
    yy, xx = np.mgrid[0:H, 0:W]
    r = np.hypot(xx - W / 2, yy - HORIZON + 30)
    band = ((HORIZON - yy) / 14 + 0.5 * ((HORIZON - yy) / 210) ** 2) % 1 > ((HORIZON - 40 - yy) / 330).clip(0, 1) * 0.42 + 0.0
    sun = (r < 225) & (yy < HORIZON) & ((yy < HORIZON - 150) | band)
    grad = ((yy - (HORIZON - 255)) / 255).clip(0, 1)[..., None]
    color = np.array(rgb("#ffa630"), dtype=np.float32) * (1 - grad) + np.array(rgb("#ff2a8c"), dtype=np.float32) * grad
    a[sun] = color[sun]
    return Image.fromarray(a.clip(0, 255).astype(np.uint8))


SKY = make_sky()


def neon_bg(t, speed=1.0):
    img = SKY.copy()
    d = ImageDraw.Draw(img)
    color = rgb("#ff2ad0")
    for k in range(-14, 15):
        d.line([(W / 2 + k * 26, HORIZON), (W / 2 + k * 210, H)], fill=color, width=2)
    phase = (t * speed * 1.6) % 1
    for i in range(9):
        z = ((i + phase) / 9) ** 2.4
        y = HORIZON + (H - HORIZON) * z
        d.line([(0, y), (W, y)], fill=color, width=2 if z < 0.4 else 3)
    d.line([(0, HORIZON), (W, HORIZON)], fill=rgb("#7ff0ff"), width=3)
    return img


_yy, _xx = np.mgrid[0:H, 0:W]
_angle = np.arctan2(_yy - H / 2, _xx - W / 2).astype(np.float32)


def rays_bg(t, c1, c2, n=14):
    a = ((_angle / (2 * math.pi) * n + t * 1.3) % 1) < 0.5
    out = np.empty((H, W, 3), dtype=np.uint8)
    out[a], out[~a] = rgb(c1), rgb(c2)
    return Image.fromarray(out)


def checker_bg(t):
    cell = 48
    a = (((_xx + int(t * 72)) // cell) + ((_yy + int(t * 36)) // cell)) % 2 == 0
    out = np.empty((H, W, 3), dtype=np.uint8)
    out[a], out[~a] = (20, 8, 58), (30, 14, 82)
    return Image.fromarray(out)


def stars_bg(t):
    img = Image.new("RGB", (W, H), (0, 0, 8))
    d = ImageDraw.Draw(img)
    r = random.Random(7)
    for _ in range(90):
        x, y, s = r.randrange(W), r.randrange(H), r.choice((1, 2, 3))
        d.rectangle([(x - t * s * 45) % W, y, (x - t * s * 45) % W + s * 2, y + s * 2 - 1],
                    fill=r.choice([(255, 255, 255), (130, 170, 255), (255, 150, 220)]))
    return img


# ------------------------------------------------------------------ дубли настоящей игры


class Take:
    def __init__(self, name):
        self.dir = WORK / "takes" / name
        frames = json.loads((self.dir / "frames.json").read_text())
        self.t0 = frames[0]
        self.times = [f - self.t0 for f in frames]
        events = json.loads((self.dir / "events.json").read_text(encoding="utf-8"))
        for e in events:
            e["t"] -= self.t0
        self.events = [e for e in events if e["type"] != "track"]
        self.track = [e for e in events if e["type"] == "track"]
        self.track_t = [e["t"] for e in self.track]
        self.index, self.image = -1, None

    def frame(self, t):
        i = min(max(bisect.bisect_left(self.times, t), 0), len(self.times) - 1)
        if i != self.index:
            self.index = i
            self.image = Image.open(self.dir / f"f_{i:05d}.jpg").convert("RGB")
        return self.image

    def state(self, t):
        i = min(bisect.bisect_left(self.track_t, t), len(self.track) - 1)
        return self.track[i]

    def hero(self, t, i):
        total = [0.0, 0.0]
        for dt in (-0.5, -0.25, 0, 0.25, 0.5):
            p = self.state(t + dt)["p"][i]
            total[0] += p[0] / 5
            total[1] += p[1] / 5
        return total

    def first(self, kind, **match):
        return next(e for e in self.events if e["type"] == kind and all(e.get(k) == v for k, v in match.items()))


takes = {}


def take(name):
    if name not in takes:
        takes[name] = Take(name)
    return takes[name]


def px(cell):
    return 4 + 49 * cell + 24.5


def zoom_view(image, cx, cy, z):
    w, h = W / z, H / z
    x0 = min(max(cx - w / 2, 0), 739 - w)
    y0 = min(max(cy - h / 2, 0), 742 - h)
    return image.resize((W, H), Image.BICUBIC, box=(x0, y0, x0 + w, y0 + h))


MARQUEE = "BOMBERSYS"


def full_view(image, t):
    """Вся игра с её панелью; по бокам — бегущие огни, как на корпусе автомата."""
    img = Image.new("RGB", (W, H), (12, 2, 34))
    d = ImageDraw.Draw(img)
    for i in range(-1, 14):
        y = i * 60 + (t * 90) % 60
        d.polygon([(0, y), (146, y + 40), (146, y + 62), (0, y + 22)], fill=(24, 6, 62))
        d.polygon([(1134, y + 40), (W, y), (W, y + 22), (1134, y + 62)], fill=(24, 6, 62))
    img.paste(image.resize((988, 720), Image.LANCZOS), (146, 0))
    lit = int(t * 10) % len(MARQUEE)
    for i, ch in enumerate(MARQUEE):
        pal = FIRE if i == lit or (i + 3) % len(MARQUEE) == lit else PINK
        y = 44 + i * 79
        put(img, sprite(ch, 6, pal), 73, y)
        put(img, sprite(ch, 6, pal), W - 73, y)
    return img


def hud(img, take_obj, t):
    p = take_obj.state(t)["p"]
    score = [q[3] for q in p] + [0, 0]
    d = ImageDraw.Draw(img)
    d.rectangle([0, 0, W, 36], fill=(4, 0, 20))
    put(img, sprite(f"1UP {score[0]:06d}", 3, ICE, outline=False), 190, 19)
    put(img, sprite("РЕКОРД 048200", 3, FIRE, outline=False), W / 2, 19)
    put(img, sprite(f"2UP {score[1]:06d}", 3, LIME, outline=False), W - 190, 19)


# ------------------------------------------------------------------ картинки


def digitize(im, step=3, levels=20):
    """«Оцифрованный актёр» 90-х: крупная точка и мало оттенков."""
    small = im.resize((im.width // step, im.height // step), Image.BOX)
    a = np.asarray(small, dtype=np.float32).copy()
    a[..., :3] = np.round(a[..., :3] / 255 * levels) / levels * 255
    a[..., 3] = (a[..., 3] > 120) * 255
    return Image.fromarray(a.astype(np.uint8), "RGBA").resize((small.width * step, small.height * step), Image.NEAREST)


_heroes = {}


def hero_big(player, k):
    key = (player, k)
    if key not in _heroes:
        im = Image.open(WORK / "heroes" / f"P_p{player}_down_run_{k:02d}.png").convert("RGBA").resize((600, 600), Image.LANCZOS)
        _heroes[key] = digitize(im, 3)
    return _heroes[key]


_runners = {}


def runner(player, k):
    key = (player, k)
    if key not in _runners:
        path = ROOT / "mockups" / "realhero" / "out" / f"R_p{player}_right_run_{k:02d}.png"
        im = Image.open(path).convert("RGBA").resize((180, 180), Image.LANCZOS)
        a = np.asarray(im, dtype=np.float32).copy()
        a[..., :3] = np.minimum(a[..., :3] * 1.6 + 14, 255)   # в маленьком размере тёмная одежда сливается с фоном
        _runners[key] = digitize(Image.fromarray(a.astype(np.uint8), "RGBA"), 2)
    return _runners[key]


_portraits = {}


def portrait(player):
    if player not in _portraits:
        im = Image.open(ROOT / "frontend" / "assets" / f"photo{player}.png").convert("RGBA")
        small = im.resize((64, 76), Image.BOX)
        a = np.asarray(small, dtype=np.float32).copy()
        a[..., :3] = np.round(a[..., :3] / 255 * 12) / 12 * 255
        _portraits[player] = Image.fromarray(a.astype(np.uint8), "RGBA").resize((192, 228), Image.NEAREST).convert("RGB")
    return _portraits[player]


ZOO_AT = [(255, 186), (763, 186), (255, 556), (763, 556)]


def monster(tier, t, size=270, key_black=False):
    image = take("zoo").frame((t * 1.0) % 4.5)
    x, y = ZOO_AT[tier]
    crop = image.crop((x - 125, y - 125, x + 125, y + 125)).resize((size, size), Image.BICUBIC)
    if key_black:
        rgba = crop.convert("RGBA")
        a = np.asarray(rgba).copy()
        a[..., 3] = (a[..., :3].max(axis=2) > 26) * 255
        return Image.fromarray(a, "RGBA")
    return crop


def make_coin():
    im = Image.new("RGBA", (40, 40), (0, 0, 0, 0))
    d = ImageDraw.Draw(im)
    d.ellipse([0, 0, 39, 39], fill=(120, 120, 136, 255))
    d.ellipse([2, 2, 37, 37], fill=(226, 226, 240, 255))
    d.ellipse([5, 5, 34, 34], fill=(180, 182, 200, 255))
    d.arc([5, 5, 34, 34], 200, 340, fill=(250, 250, 255, 255))
    big = sprite("15", 2, ["#3a3a52"] * 8, outline=False)
    im.paste(big, (20 - big.width // 2, 12), big)
    return im.resize((160, 160), Image.NEAREST)


COIN = make_coin()


def coin(angle, size=1.0):
    w = max(6, int(COIN.width * abs(math.cos(angle)) * size))
    return COIN.resize((w, int(COIN.height * size)), Image.NEAREST)


_bursts = {}


def burst(lines, radius, fill="#ffe000", edge="#e01010", pal=DARKRED, scale=6, spikes=16):
    key = (tuple(lines), radius, fill, scale)
    if key not in _bursts:
        s = radius * 2 + 20
        im = Image.new("RGBA", (s * 2, s * 2), (0, 0, 0, 0))
        d = ImageDraw.Draw(im)
        points = []
        for i in range(spikes * 2):
            r = radius * 2 if i % 2 == 0 else radius * 2 * 0.72
            a = math.pi * i / spikes
            points.append((s + math.cos(a) * r, s + math.sin(a) * r * 0.74))
        d.polygon(points, fill=rgb(edge))
        inner = [(s + (x - s) * 0.9, s + (y - s) * 0.9) for x, y in points]
        d.polygon(inner, fill=rgb(fill))
        im = im.resize((s, s), Image.LANCZOS)
        total = len(lines) * (scale * 8 + 12)
        for i, line in enumerate(lines):
            spr = sprite(line, scale, pal, outline=False)
            y = s // 2 - total // 2 + i * (scale * 8 + 12)
            im.paste(spr, (s // 2 - spr.width // 2, y), spr)
        _bursts[key] = im
    return _bursts[key]


def put_burst(img, spr, cx, cy, t, age):
    angle = -7 + 3 * math.sin(t * 7)
    k = 1 + 1.0 * (1 - age / 0.12) ** 2 if age < 0.12 else 1 + 0.03 * math.sin(t * 14)
    b = spr.resize((int(spr.width * k), int(spr.height * k)), Image.BILINEAR).rotate(angle, Image.BICUBIC, expand=True)
    put(img, b, cx, cy)


def logo_frame(frame):
    """Кадры 1–90 — полёт, дальше логотип покачивается туда-обратно."""
    if frame > 150:
        frame = 90 + abs((frame - 150) % 120 - 60) * 1
    return Image.open(WORK / "logo" / f"logo_{int(frame):04d}.png")


def put_logo(img, frame, scale=1.0, cy=None):
    logo = logo_frame(frame)
    if scale != 1.0:
        logo = logo.resize((int(W * scale), int(H * scale)), Image.LANCZOS)
    y = (cy if cy is not None else H // 2 - 90) - logo.height // 2
    x = (W - logo.width) // 2
    # тёмный ореол отделяет хром от солнца
    halo = logo.getchannel("A").filter(ImageFilter.GaussianBlur(7)).point(lambda v: min(255, v * 2))
    img.paste((16, 0, 44), (x + 3, y + 5), halo)
    img.paste(logo, (x, y), logo)


_sparks = [(random.Random(i).uniform(0, 6.283), random.Random(i * 7 + 1).uniform(180, 900),
            random.Random(i * 3 + 2).choice(["#ffffff", "#ffe45c", "#ff9a0a", "#ff2aa8", "#7ff0ff"]),
            random.Random(i * 5 + 3).choice((4, 6, 9))) for i in range(150)]


def shock(img, age, cx=W / 2, cy=H / 2 - 90):
    """Взрыв при ударе логотипа: кольцо и искры."""
    if age > 1.3:
        return
    d = ImageDraw.Draw(img)
    r = age * 1500
    width = max(1, int(26 * (1 - age / 1.3)))
    d.ellipse([cx - r, cy - r * 0.62, cx + r, cy + r * 0.62], outline=rgb("#fff7b0"), width=width)
    for angle, speed, color, size in _sparks:
        x = cx + math.cos(angle) * speed * age
        y = cy + math.sin(angle) * speed * age * 0.7 + 420 * age * age
        d.rectangle([x, y, x + size, y + size], fill=rgb(color))


# ------------------------------------------------------------------ сцены


def g(bar):
    return bar * BAR


def scene_attract(t):
    img = stars_bg(t)
    put(img, sprite("1UP 000000", 3, ICE, outline=False), 190, 22)
    put(img, sprite("РЕКОРД 048200", 3, FIRE, outline=False), W / 2, 22)
    put(img, sprite("2UP 000000", 3, LIME, outline=False), W - 190, 22)
    put(img, sprite("BOMBERSYS", 10, FIRE), W / 2, 190)
    put(img, sprite("(C) 2005-2026", 3, GREY, outline=False), W / 2, 290)
    if t < 1.75:
        if blink(t, 2.5):
            put(img, sprite("ОПУСТИТЕ МОНЕТУ", 6, ICE), W / 2, 385)
    elif blink(t, 6):
        put(img, sprite("ИГРА НАЧИНАЕТСЯ!", 6, LIME), W / 2, 385)
    d = ImageDraw.Draw(img)
    d.rectangle([520, 560, 760, 680], fill=(50, 50, 66), outline=(150, 150, 170), width=6)
    if t < 1.5:
        if t > 0.75:
            u = (t - 0.75) / 0.75
            spin = coin(t * 16)
            y = -100 + 700 * u * u
            img.paste(spin, (int(W / 2 - spin.width / 2), int(y - spin.height / 2)), spin)
    d.rectangle([634, 576, 646, 636], fill=(0, 0, 0))
    d.rectangle([520, 560, 760, 680], outline=(150, 150, 170), width=6)
    put(img, sprite("15 КОП", 2, GOLD, outline=False), 640, 656)
    credit = 1 if t >= 1.5 else 0
    put(img, sprite(f"КРЕДИТ {credit:02d}", 4, GOLD if credit else WHITE), W - 200, 640)
    if t < 2.8:
        put(img, sprite("> ВОСПР.", 3, LIME, outline=False), 120, 70)
    return img


def scene_flyin(t):
    img = neon_bg(t, 1 + t * 0.9)
    put_logo(img, 1 + int(t * 30))
    return img


def scene_logo(t):
    img = neon_bg(t, 0.8)
    put_logo(img, 90 + t * 30)
    shock(img, t)
    if t >= 0.65:
        slam(img, sprite("ИГРОВОЙ АВТОМАТ", 6, ICE), W / 2, 530, t - 0.65)
    if t >= 1.6:
        slam(img, sprite("У ВАС ДОМА!", 8, FIRE), W / 2, 625, t - 1.6)
    return img


CALLOUTS = [(g(6) + 0.35, "СТАВЬ БОМБЫ!", FIRE), (g(6) + 1.35, "КРУШИ СТЕНЫ!", ICE), (g(6) + 2.35, "БЕГИ ОТ ОГНЯ!", PINK)]


def callouts(img, now):
    current = None
    for at, text, pal in CALLOUTS:
        if now >= at:
            current = (at, text, pal)
    if current:
        slam(img, sprite(current[1], 8, current[2]), W / 2, H - 76, now - current[0])


def shot_view(s, now):
    """Кадр настоящей игры: вся игра с панелью (z=None) или камера над полем с экранным счётом."""
    tk = take(s["take"])
    t = s["at"] + now - s["start"]
    image = tk.frame(t)
    z = s.get("z")
    if z is None:
        return full_view(image, now)
    focus = s["focus"]
    if focus == "both":
        a, b = tk.hero(t, 0), tk.hero(t, 1)
        cx, cy = px((a[0] + b[0]) / 2), px((a[1] + b[1]) / 2)
    elif isinstance(focus, int):
        p = tk.hero(t, focus)
        cx, cy = px(p[0]), px(p[1]) - 18
    else:
        cx, cy = px(focus[0]), px(focus[1])
    img = zoom_view(image, cx, cy, z)
    hud(img, tk, t)
    return img


def key_cap(d, img, x, y, text, size=46):
    d.rectangle([x, y, x + size, y + size], fill=(230, 230, 240), outline=(90, 90, 110), width=3)
    d.rectangle([x + 3, y + size - 8, x + size - 3, y + size - 3], fill=(170, 170, 186))
    if isinstance(text, int):
        glyph = np.kron(F8.glyphs[text], np.ones((3, 3), dtype=bool))
        a = np.zeros((*glyph.shape, 4), dtype=np.uint8)
        a[glyph] = (20, 20, 40, 255)
        spr = Image.fromarray(a, "RGBA")
    else:
        spr = sprite(text, 3 if len(text) == 1 else 2, ["#141428"] * 8, outline=False)
    img.paste(spr, (x + (size - spr.width) // 2, y + (size - 8 - spr.height) // 2 + 1), spr)


def overlay_keyboard(img, age):
    d = ImageDraw.Draw(img)
    y0 = H - 168
    d.rectangle([146, y0, W - 146, H - 6], fill=(8, 2, 28), outline=rgb(IVAN), width=4)
    slam(img, sprite("ОДНА КЛАВИАТУРА", 4, FIRE), W / 2, y0 + 28, age)
    top = y0 + 56
    put(img, sprite("ИВАН", 3, ICE, outline=False), 230, top + 44)
    key_cap(d, img, 346, top, "W")
    for i, ch in enumerate("ASD"):
        key_cap(d, img, 296 + i * 50, top + 50, ch)
    key_cap(d, img, 456, top + 50, "БОМБА", 46)
    d.rectangle([456, top + 50, 566, top + 96], fill=(230, 230, 240), outline=(90, 90, 110), width=3)
    put(img, sprite("ПРОБЕЛ", 2, ["#141428"] * 8, outline=False), 511, top + 71)
    put(img, sprite("ИГОРЬ", 3, LIME, outline=False), 1050, top + 44)
    key_cap(d, img, 806, top, 24)
    for i, code in enumerate((27, 25, 26)):
        key_cap(d, img, 756 + i * 50, top + 50, code)
    d.rectangle([626, top + 50, 730, top + 96], fill=(230, 230, 240), outline=(90, 90, 110), width=3)
    put(img, sprite("ENTER", 2, ["#141428"] * 8, outline=False), 678, top + 71)


def laptop(d, x, y, color):
    d.rectangle([x, y, x + 120, y + 78], fill=(26, 26, 40), outline=(190, 190, 205), width=4)
    d.rectangle([x + 9, y + 9, x + 111, y + 69], fill=rgb(color))
    d.polygon([(x - 16, y + 100), (x + 136, y + 100), (x + 122, y + 80), (x - 2, y + 80)], fill=(190, 190, 205))


def overlay_laptops(img, t, age):
    d = ImageDraw.Draw(img)
    y0 = H - 176
    d.rectangle([146, y0, W - 146, H - 6], fill=(8, 2, 28), outline=rgb(IGOR), width=4)
    laptop(d, 220, y0 + 36, IVAN)
    laptop(d, W - 340, y0 + 36, IGOR)
    for i in range(12):
        x = 372 + i * 45
        lit = (i - int(t * 16)) % 12 < 4
        d.rectangle([x, y0 + 80, x + 16, y0 + 96], fill=rgb("#fff27a") if lit else (52, 42, 80))
    slam(img, sprite("ДВА НОУТБУКА", 5, FIRE), W / 2, y0 + 38, age)
    put(img, sprite("ПО СЕТИ - В ОДНОЙ WI-FI", 2, ICE, outline=False), W / 2, y0 + 134)


STATS = {1: [("ВАТНИК", 9), ("БОРОДА", 10), ("ДИНАМИТ", 8)], 2: [("КОМБИНЕЗОН", 9), ("ВЗГЛЯД", 10), ("ДИНАМИТ", 8)]}


def fighter_card(img, player, x0, t, active, since):
    color = IVAN if player == 1 else IGOR
    y0, w, h = 112, 600, 596
    d = ImageDraw.Draw(img)
    d.rectangle([x0, y0, x0 + w, y0 + h], fill=(6, 4, 26))
    frame_on = active and (blink(t, 5) or t - since > 1.0)
    d.rectangle([x0, y0, x0 + w, y0 + h], outline=rgb(color) if frame_on else (60, 60, 90), width=7)
    hero = hero_big(player, int(t * 26) % 20)
    if player == 1:
        hx, col = x0 - 110, x0 + 244
    else:
        hx, col = x0 + 110, x0 + 18
    img.paste(hero, (hx, y0 - 8), hero)
    img.paste(portrait(player), (col + 74, y0 + 18))
    d.rectangle([col + 70, y0 + 14, col + 270, y0 + 250], outline=rgb(color), width=4)
    name = "ИВАН" if player == 1 else "ИГОРЬ"
    pal = ICE if player == 1 else LIME
    age = t - since
    if active and age >= 0:
        slam(img, sprite(name, 6, pal), col + 170, y0 + 298, age)
    else:
        put(img, sprite(name, 6, pal), col + 170, y0 + 298)
    for i, (label, value) in enumerate(STATS[player]):
        y = y0 + 356 + i * 72
        put(img, sprite(label, 2, WHITE, outline=False), col + 170, y)
        fill = value if not active else min(value, int(max(0, age) * 18))
        fill = value if age > 1 else fill
        for k in range(10):
            xk = col + 40 + k * 26
            on = k < fill
            shade = rgb(color) if on else (44, 44, 70)
            d.rectangle([xk, y + 16, xk + 21, y + 40], fill=shade)
    put(img, sprite(f"ИГРОК {player}", 2, GOLD, outline=False), col + 170, y0 + h - 22)
    if not active:
        veil = Image.new("RGBA", (w, h), (0, 0, 10, 140))
        img.paste(veil, (x0, y0), veil)


def scene_select(t):
    img = checker_bg(t)
    slam(img, sprite("ВЫБЕРИ БОЙЦА", 8, FIRE), W / 2, 58, t)
    both = t >= 4.5
    fighter_card(img, 1, 28, t, t >= 1.5 and (t < 3.0 or both), 1.5 if not both else 4.5)
    fighter_card(img, 2, 652, t, t >= 3.0, 3.0 if not both else 4.5)
    if both:
        slam(img, sprite("ГОТОВЫ?", 12, PINK), W / 2, H / 2 + 40, t - 4.5)
    return img


TIERS = [("ЗЕЛЁНЫЙ", 100, LIME, "#3fae45"), ("ОРАНЖЕВЫЙ", 250, FIRE, "#f08a1c"),
         ("КРАСНЫЙ", 500, BLOOD, "#d92c22"), ("ФИОЛЕТОВЫЙ", 1000, PINK, "#8a4fe0")]


def scene_monsters(t):
    img = stars_bg(t)
    d = ImageDraw.Draw(img)
    slam(img, sprite("ЗУБАСТИКИ", 9, BLOOD), W / 2, 62, t)
    for i, (name, points, pal, color) in enumerate(TIERS):
        at = 0.08 + i * 0.26
        if t < at:
            continue
        x = 18 + i * 314
        d.rectangle([x, 128, x + 302, 430], outline=rgb(color), width=6)
        tile = monster(i, t + i * 0.7, 290)
        img.paste(tile, (x + 6, 134))
        put(img, sprite(name, 3, pal, outline=False), x + 151, 466)
        slam(img, sprite(str(points), 7, pal), x + 151, 536, t - at)
        put(img, sprite("ОЧКОВ", 2, WHITE, outline=False), x + 151, 590)
    if t > 0.9 and blink(t, 4):
        put(img, sprite("БЕРЕГИСЬ!", 6, FIRE), W / 2, 660)
    return img


RECORDS = [("1", "ИВАН И ИГОРЬ", 15, 48200), ("2", "ИВАН И ИГОРЬ", 12, 36750), ("3", "ИВАН", 11, 29100), ("4", "ИГОРЬ", 9, 21400)]


def scene_records(t):
    img = stars_bg(t)
    slam(img, sprite("ТАБЛИЦА РЕКОРДОВ", 6, FIRE), W / 2, 80, t)
    put(img, sprite("  ИМЯ          УР.  ОЧКИ", 3, GREY, outline=False), W / 2, 158)
    pals = [GOLD, ICE, PINK, LIME]
    for i, (rank, name, level, score) in enumerate(RECORDS):
        if t < 0.1 + i * 0.1:
            continue
        pal = pals[(i + int(t * 10)) % 4]
        line = f"{rank}. {name:<12} {level:>2}  {score:>6}"
        put(img, sprite(line, 4, pal, outline=False), W / 2, 216 + i * 76)
    if t > 0.6 and blink(t, 5):
        put(img, sprite("5. ТВОЁ ИМЯ ?", 5, FIRE), W / 2, 216 + 4 * 76)
    return img


def level_card(img, level, age):
    slam(img, sprite(f"УРОВЕНЬ {level}", 7, GOLD), W / 2, 110, age)


def parade(img, t):
    """Как в заставках автоматов: герои бегут через экран, за ними гонятся твари."""
    if t < 0:
        return
    base = H - 136
    x = -200 + t * 330
    frame = int(t * 26) % 20
    for offset, tier in ((-620, 3), (-470, 2), (-320, 0)):
        mx = int(x + offset)
        bob = abs(math.sin(t * 9 + offset)) * 12
        mon = monster(tier, t, 118, key_black=True)
        img.paste(mon, (mx, int(base + 18 - bob)), mon)
    for offset, player in ((0, 1), (-150, 2)):
        run = runner(player, frame)
        img.paste(run, (int(x + offset), base - 44), run)


def scene_offer(t):
    img = neon_bg(t, 0.55)
    put_logo(img, 150 + t * 30, 0.62, 118)
    d = ImageDraw.Draw(img)
    now = t + g(28)
    if t < 1.5:
        c = coin(t * 8, 1.5)
        put(img, c, W / 2, 400)
        size = 130
        d.line([(W / 2 - size, 400 - size), (W / 2 + size, 400 + size)], fill=rgb("#ff1010"), width=22)
        d.line([(W / 2 + size, 400 - size), (W / 2 - size, 400 + size)], fill=rgb("#ff1010"), width=22)
        slam(img, sprite("МОНЕТА НЕ НУЖНА!", 7, ICE), W / 2, 625, t)
    elif t < 3.0:
        put_burst(img, burst(["БЕСПЛАТНО!"], 430, scale=7), W / 2, 430, now, t - 1.5)
    elif t < 10.5:
        d.rectangle([66, 220, W - 66, 540], fill=(6, 2, 26), outline=rgb("#7ff0ff"), width=5)
        slam(img, sprite("СКАЧАЙ НА GITHUB", 7, FIRE), W / 2, 288, t - 3.0)
        if t > 3.3:
            put(img, sprite(URL, 4, ICE, outline=False), W / 2, 380)
        if t > 3.7:
            put(img, sprite(f"ВЕРСИЯ {VERSION}  ДЛЯ WINDOWS", 3, WHITE, outline=False), W / 2, 442)
            put(img, sprite("1-2 ИГРОКА  БЕЗ УСТАНОВКИ", 3, LIME, outline=False), W / 2, 492)
        if 7.4 < t < 10.5:
            put(img, sprite("ПЕРЕД ИГРОЙ ПРОКОНСУЛЬТИРУЙТЕСЬ С НАПАРНИКОМ", 2, WHITE), W / 2, 566)
        parade(img, t - 5.2)
    else:
        return None
    return img


def scene_final(t):
    img = neon_bg(t, 0.3)
    put_logo(img, 130 + t * 30, 1.0, 280)
    shock(img, t, W / 2, 280)
    slam(img, sprite("БЕСПЛАТНО!", 8, FIRE), W / 2, 490, t)
    band = Image.new("RGBA", (W - 120, 136), (6, 2, 26, 220))
    img.paste(band, (60, 556), band)
    put(img, sprite(URL, 4, ICE), W / 2, 600)
    put(img, sprite("АВТОРЫ ОДЕЖДЫ ГЕРОЕВ И ЛИЦЕНЗИИ - В README РЕПОЗИТОРИЯ", 2, WHITE, outline=False), W / 2, 670)
    return img


SHOTS = [
    {"start": g(6), "end": g(7), "take": "play", "at": 3.0},
    {"start": g(7), "end": g(8), "take": "play", "at": 4.8, "z": 2.0, "focus": 1},
    {"start": g(8), "end": g(9), "take": "play", "at": 10.8, "z": 1.9, "focus": 0},
    {"start": g(9), "end": g(12), "take": "chain", "at": 2.78 - 1.5, "z": 1.74, "focus": (7, 8)},
    {"start": g(20), "end": NET_AT, "take": "level10", "at": 7.0},
    {"start": NET_AT, "end": g(24), "take": "level10", "at": 13.45, "z": 1.74, "focus": 1},
    {"start": g(24), "end": g(26), "take": "revive", "at": 8.8 - 1.5},
    {"start": g(26), "end": g(26) + 0.5, "take": "play", "at": 18.2, "z": 1.74, "focus": 0, "level": 2},
    {"start": g(26) + 0.5, "end": g(26) + 1.0, "take": "snake", "at": 3.2, "z": 1.74, "focus": 1, "level": 7},
    {"start": g(26) + 1.0, "end": g(26) + 1.5, "take": "level10", "at": 9.1, "z": 1.74, "focus": 0, "level": 10},
]


def add_bite_shots():
    bite = take("bite").first("player_died", player=0)
    SHOTS.append({"start": g(17), "end": g(18), "take": "bite", "at": bite["t"] - 0.75, "z": 2.7, "focus": 0, "bite": True})
    bones = take("bones").first("player_died", player=0)
    SHOTS.append({"start": g(18), "end": g(20), "take": "bones", "at": bones["t"] - 0.9, "z": 2.5, "focus": 0, "bones": True})


add_bite_shots()
SHOTS.sort(key=lambda s: s["start"])
CHAIN_BOOMS = [e["t"] - (2.78 - g(10)) for e in take("chain").events if e["type"] == "explosion" and 2.7 < e["t"] < 3.7]
BITE_AT = g(17) + 0.75
BONES_AT = g(18) + 0.9


def compose(now):
    if now < 3.0:
        return scene_attract(now)
    if now < g(4):
        return scene_flyin(now - 3.0)
    if now < g(6):
        return scene_logo(now - g(4))
    if g(12) <= now < g(16):
        return scene_select(now - g(12))
    if g(16) <= now < g(17):
        return scene_monsters(now - g(16))
    if g(26) + 1.5 <= now < g(28):
        return scene_records(now - g(26) - 1.5)
    if now >= g(35):
        return scene_final(now - g(35))
    if now >= g(28):
        return scene_offer(now - g(28))
    shot = next(s for s in SHOTS if s["start"] <= now < s["end"])
    img = shot_view(shot, now)
    if g(6) <= now < g(9):
        callouts(img, now)
    if g(9) <= now < g(12):
        if now >= g(10):
            slam(img, sprite("ЦЕПНАЯ", 9, FIRE), W / 2, 120, now - g(10))
        if now >= g(10) + 0.3:
            slam(img, sprite("РЕАКЦИЯ!", 9, FIRE), W / 2, 216, now - g(10) - 0.3)
        count = sum(1 for at in CHAIN_BOOMS if at <= now)
        if count >= 2:
            last = max(at for at in CHAIN_BOOMS if at <= now)
            slam(img, sprite(f"X{count}", 14, GOLD), W - 220, H - 130, now - last)
    if shot.get("bite") and now >= BITE_AT:
        put_burst(img, burst(["ХРУМ!"], 250, fill="#ffffff", edge="#e01010", scale=8), W - 300, 200, now, now - BITE_AT)
    if shot.get("bones"):
        slam(img, sprite("ЗМЕЯ!", 9, LIME), W / 2, 112, now - g(18))
        if now >= g(19):
            slam(img, sprite("ДО КОСТЕЙ!", 10, BLOOD), W / 2, H - 92, now - g(19))
    if g(20) <= now < NET_AT:
        put_burst(img, burst(["2", "ИГРОКА!"], 250, scale=6), 990, 190, now, now - g(20))
        if now >= g(20) + 0.85:
            overlay_keyboard(img, now - g(20) - 0.85)
    if NET_AT <= now < g(24):
        overlay_laptops(img, now, now - NET_AT)
    if g(24) <= now < g(26):
        if now < g(25):
            slam(img, sprite("ПОГИБ НАПАРНИК?", 6, ICE), 640, 620, now - g(24))
        else:
            slam(img, sprite("ОТДАЙ ЕМУ ЖИЗНЬ!", 6, LIME), 640, 620, now - g(25))
    if shot.get("level"):
        level_card(img, shot["level"], now - shot["start"])
        put_burst(img, burst(["10+", "УРОВНЕЙ"], 215, scale=5), 1030, 560, now, now - g(26))
    return img


# ------------------------------------------------------------------ телевизор

_map_y, _map_x = np.mgrid[0:H, 0:W].astype(np.float32)
_u, _v = (_map_x - W / 2) / (W / 2), (_map_y - H / 2) / (H / 2)
_bend = 1 + 0.028 * (_u * _u + _v * _v)
_sx = (_u * _bend * 0.982 + 1) * W / 2
_sy = (_v * _bend * 0.982 + 1) * H / 2
_x0 = np.clip(np.floor(_sx).astype(np.int32), 0, W - 2)
_y0 = np.clip(np.floor(_sy).astype(np.int32), 0, H - 2)
_fx = np.clip(_sx - _x0, 0, 1)[..., None]
_fy = np.clip(_sy - _y0, 0, 1)[..., None]
_outside = (_sx < 0) | (_sx > W - 1) | (_sy < 0) | (_sy > H - 1)
_scan = np.array([1.04, 1.0, 0.8], dtype=np.float32)[(np.arange(H) % 3)][:, None, None]
_edge = (np.abs(_u) ** 6 + np.abs(_v) ** 6)
_vign = (1 - 0.42 * _edge).clip(0, 1)[..., None]
_noise = [np.random.default_rng(i).normal(0, 2.4, (H, W, 1)).astype(np.float32) for i in range(6)]
GLITCH = [(2.85, 3.05), (g(12) - 0.05, g(12) + 0.08), (g(16) - 0.05, g(16) + 0.07), (g(24) - 0.05, g(24) + 0.07),
          (g(28) - 0.05, g(28) + 0.08), (g(33) + 0.5, g(33) + 0.62)]
FLASH = [(3.0, 0.5), (g(4), 1.0), (g(10), 0.8), (g(12), 0.5), (g(16), 0.5), (g(20), 0.9), (g(25), 0.6), (g(28), 0.8), (g(35), 1.0)]
HITS = [(g(4), 26), (g(10), 18), (g(10) + 0.2, 14), (g(10) + 0.4, 12), (g(10) + 0.6, 10), (g(20), 16), (g(28), 14),
        (BITE_AT, 18), (BONES_AT, 12), (g(35), 22)]


def tv(img, now, index):
    # тряска от ударов
    dx = dy = 0
    for at, amp in HITS:
        age = now - at
        if 0 <= age < 0.5:
            fade = amp * (1 - age / 0.5)
            dx += int(fade * math.sin(age * 71))
            dy += int(fade * math.cos(age * 53))
    if dx or dy:
        img = ImageChops.offset(img, dx, dy)
    small = img.resize((320, 180), Image.BILINEAR).filter(ImageFilter.GaussianBlur(3.2)).resize((W, H), Image.BILINEAR)
    f = np.asarray(img, dtype=np.float32).copy()
    bloom = np.asarray(small, dtype=np.float32)
    f += np.clip(bloom - 90, 0, None) * 0.55
    # цвет чуть расходится по горизонтали, как на бытовом телевизоре
    f[..., 0] = np.roll(f[..., 0], 1, axis=1)
    f[..., 2] = np.roll(f[..., 2], -1, axis=1)
    for at, strength in FLASH:
        age = now - at
        if 0 <= age < 0.45:
            a = strength * math.exp(-age * 9)
            f = f * (1 - a) + 255 * a
    glitch = any(a <= now < b for a, b in GLITCH)
    r = random.Random(index)
    if glitch:
        for _ in range(9):
            y, h, shift = r.randrange(H), r.randrange(8, 70), r.randrange(-90, 90)
            f[y:y + h] = np.roll(f[y:y + h], shift, axis=1)
        f = f * 0.55 + r.uniform(40, 120) * _noise[index % 6] * 0.4 + 60
    elif index % 211 < 5:
        # редкая полоска «трекинга» плёнки
        y = (index * 37) % (H - 40)
        f[y:y + 26] = np.roll(f[y:y + 26], r.randrange(-24, 24), axis=1) * 0.8 + 34
    a, b = f[_y0, _x0], f[_y0, _x0 + 1]
    c, e = f[_y0 + 1, _x0], f[_y0 + 1, _x0 + 1]
    f = (a * (1 - _fx) + b * _fx) * (1 - _fy) + (c * (1 - _fx) + e * _fx) * _fy
    f *= _scan * _vign * (1.0 + 0.012 * math.sin(now * 37))
    f += _noise[index % 6]
    f[_outside] = 0
    return np.clip(f, 0, 255).astype(np.uint8)


def power(arr, now):
    """Включение и выключение кинескопа: картинка схлопывается в светящуюся полоску, а потом гаснет."""
    if now < 0.35:
        u = now / 0.35
    elif now > 54.0:
        u = max(0.0, 1 - (now - 54.0) / 0.4)
    else:
        return arr
    if u <= 0.0:
        return np.zeros_like(arr)
    h = max(2, int(H * u ** 2.6))
    w = W if u > 0.2 else max(6, int(W * (u / 0.2) ** 2))
    im = Image.fromarray(arr).resize((w, h), Image.BILINEAR)
    out = Image.new("RGB", (W, H), (0, 0, 0))
    out.paste(im, ((W - w) // 2, (H - h) // 2))
    a = np.asarray(out, dtype=np.float32) * (1 + 2.0 * (1 - u)) + (1 - u) * 80 * (np.asarray(out).max(axis=2, keepdims=True) > 0)
    return np.clip(a, 0, 255).astype(np.uint8)


# ------------------------------------------------------------------ звук

AUDIO = WORK / "audio"


def read_wav(path):
    with wave.open(str(path), "rb") as w:
        data = np.frombuffer(w.readframes(w.getnframes()), dtype=np.int16).astype(np.float32) / 32768
        channels = w.getnchannels()
    data = data.reshape(-1, channels).T
    return np.vstack([data, data]) if channels == 1 else data


_sfx = {}


def sfx(name):
    if name not in _sfx:
        data = read_wav(AUDIO / f"sfx_{name}.wav")
        # тишину на конце отрезаем, громкость приводим к одному потолку
        loud = np.nonzero(np.abs(data).max(axis=0) > 1e-3)[0]
        data = data[:, :(loud[-1] + 1 if len(loud) else 1)]
        _sfx[name] = data / max(np.abs(data).max(), 1e-6)
    return _sfx[name]


def decode_ogg(path):
    pieces = []
    resampler = av.AudioResampler(format="fltp", layout="mono", rate=RATE)
    with av.open(str(path)) as box:
        for frame in box.decode(audio=0):
            for out in resampler.resample(frame):
                pieces.append(out.to_ndarray()[0])
    data = np.concatenate(pieces)
    return data / max(np.abs(data).max(), 1e-6)


def voice_fx(mono, slow=0.965):
    """Диктор из телевизора: чуть ниже и плотнее, с коротким эхом студии."""
    x = np.arange(0, len(mono) - 1, slow)
    v = np.interp(x, np.arange(len(mono)), mono).astype(np.float32)
    v = v / max(np.abs(v).max(), 1e-6)
    low = np.zeros_like(v)
    state = 0.0
    k = 1 - math.exp(-2 * math.pi * 110 / RATE)
    for i in range(0, len(v)):   # срез низа, чтобы голос не гудел
        state += k * (v[i] - state)
        low[i] = state
    v = v - low
    state = 0.0
    k = 1 - math.exp(-2 * math.pi * 2600 / RATE)
    smooth = np.zeros_like(v)
    for i in range(0, len(v)):
        state += k * (v[i] - state)
        smooth[i] = state
    v = smooth + 1.5 * (v - smooth)  # разборчивость
    v = np.tanh(v / max(np.abs(v).max(), 1e-6) * 2.0) / math.tanh(2.0)
    tail = int(RATE * 0.45)
    out = np.zeros(len(v) + tail, dtype=np.float32)
    out[:len(v)] += v
    delay = int(RATE * 0.095)
    out[delay:delay + len(v)] += 0.2 * v
    delay2 = int(RATE * 0.19)
    out[delay2:delay2 + len(v)] += 0.08 * v
    return out


VO = [("title", g(4) - 1.68), ("home", g(4) + 0.55), ("bombs", g(6) + 0.35), ("chain", g(10) - 0.5), ("choose", g(12) + 0.1),
      ("ivan", g(13) + 0.1), ("igor", g(14) + 0.1), ("toothy", g(16) + 0.1), ("snake", g(18) + 0.15), ("two", g(20) + 0.1),
      ("revive", g(24) + 0.1), ("levels", g(26) + 0.1), ("free", g(28) + 0.1), ("github", g(30) + 0.25), ("legal", g(33) + 0.0)]
ENGLISH = [("fighter_ready", 2.25, 0.85), ("fighter_multi_kill", g(11) + 0.2, 0.9),
           ("fighter_ready", g(15) + 0.1, 0.9), ("fighter_fight", g(15) + 1.0, 1.0), ("female_new_highscore", g(26) + 2.75, 0.8)]
SOUNDS = [("crtOn", 0.0, 0.5), ("clink", 1.5, 0.9), ("credit", 1.72, 0.6), ("static", 2.85, 0.5), ("whoosh", 3.1, 0.25),
          ("bigboom", g(4), 0.6), ("slam", g(4) + 0.65, 0.4), ("slam", g(4) + 1.6, 0.5), ("slam", g(6) + 0.35, 0.4),
          ("slam", g(6) + 1.35, 0.4), ("slam", g(6) + 2.35, 0.4), ("bigboom", g(10), 0.9), ("slam", g(10) + 0.3, 0.6),
          ("slam", g(12), 0.6), ("slam", g(13), 0.5), ("slam", g(14), 0.5), ("slam", g(15), 0.7), ("slam", g(16), 0.7),
          ("crunch", BITE_AT, 1.0), ("slam", BITE_AT, 0.7), ("slam", g(19), 0.7), ("slam", g(20), 0.9), ("slam", g(20) + 0.85, 0.45),
          ("slam", NET_AT, 0.5), ("revive", g(25), 0.9), ("slam", g(26), 0.6), ("tick", g(26) + 0.5, 0.8),
          ("tick", g(26) + 1.0, 0.8), ("slam", g(26) + 1.5, 0.6), ("slam", g(28), 0.7), ("slam", g(29), 0.6),
          ("fanfare", g(29), 0.55), ("slam", g(30), 0.6), ("bigboom", g(35), 0.8), ("crtOff", 54.0, 0.6)]
for tier in range(4):
    SOUNDS.append(("tick", g(16) + 0.08 + tier * 0.26, 0.9))
EVENT_SOUND = {"explosion": ("explosion", 0.5), "wall_destroyed": ("wall", 0.3), "bomb_placed": ("bomb", 0.25),
               "enemy_killed": ("ghostKilled", 0.4), "player_revived": ("revive", 0.5), "item_destroyed": ("giftBurn", 0.3)}


def mix():
    length = int((TOTAL + 1) * RATE)
    fx = np.zeros((2, length), dtype=np.float32)
    vo = np.zeros((2, length), dtype=np.float32)

    def add(buffer, data, at, gain=1.0):
        start = int(at * RATE)
        n = min(data.shape[1], length - start)
        if n > 0 and start >= 0:
            buffer[:, start:start + n] += data[:, :n] * gain

    for name, at, gain in SOUNDS:
        add(fx, sfx(name), at, gain)
    # звуки самой игры — по её настоящим событиям в показанных отрезках
    for s in SHOTS:
        tk = take(s["take"])
        last = -9.0
        for e in tk.events:
            if not s["at"] <= e["t"] < s["at"] + s["end"] - s["start"]:
                continue
            at = s["start"] + e["t"] - s["at"]
            kind = e["type"]
            if kind == "explosion":
                if at - last < 0.06:
                    continue
                last = at
            if kind == "player_died" and e.get("cause") == "snake":
                add(fx, sfx("ghostLaugh"), at, 0.5)
                add(fx, sfx("gnaw"), at + 1.5, 1.0)
            elif kind == "player_died" and e.get("cause") == "enemy":
                if not s.get("bite"):
                    add(fx, sfx("crunch"), at, 0.6)
                add(fx, sfx("ghostLaugh"), at + 0.2, 0.45)
            elif kind == "item_taken":
                add(fx, sfx({"bomb": "powerUp", "chest": "chest"}.get(e.get("kind"), "coin")), at, 0.45)
            elif kind in EVENT_SOUND:
                name, gain = EVENT_SOUND[kind]
                add(fx, sfx(name), at, gain)
    for name, at in VO:
        data = voice_fx(read_wav(WORK / "voice" / SPEAKER / f"{name}.wav")[0])
        add(vo, np.vstack([data, data]), at, 0.95)
        print(f"VO {name}: {at:.2f} .. {at + len(data) / RATE - 0.45:.2f}", flush=True)
    for name, at, gain in ENGLISH:
        data = decode_ogg(ROOT / "frontend" / "sounds" / "voice" / f"{name}.ogg")
        add(vo, np.vstack([data, data]), at, gain)

    song = read_wav(AUDIO / "song.wav")
    song = song / max(np.abs(song).max(), 1e-6) * 0.62
    music = np.zeros((2, length), dtype=np.float32)
    add(music, song, 3.0)
    # музыка уступает голосу: огибающая голоса с быстрым приходом и плавным уходом
    level = np.abs(vo).max(axis=0)
    env = np.zeros(length, dtype=np.float32)
    current = 0.0
    release = math.exp(-1 / (0.22 * RATE))
    attack = math.exp(-1 / (0.012 * RATE))
    for i in range(0, length, 16):
        peak = float(level[i:i + 16].max())
        current = attack * current + (1 - attack) * peak if peak > current else release * current
        env[i:i + 16] = current
    duck = 1 - 0.5 * np.minimum(env * 3, 1)
    total = music * duck + fx * 0.62 + vo * 0.95
    total = np.tanh(total * 1.1) / math.tanh(1.3)
    end = int(TOTAL * RATE)
    total[:, end - int(0.2 * RATE):end] *= np.linspace(1, 0, int(0.2 * RATE))
    total = total[:, :end] / max(np.abs(total).max() / 0.97, 1.0)
    print(f"AUDIO peak {np.abs(total).max():.3f} rms {np.sqrt((total ** 2).mean()):.3f}", flush=True)
    return total.astype(np.float32)


# ------------------------------------------------------------------ сборка


def stills(times):
    folder = WORK / "stills"
    folder.mkdir(exist_ok=True)
    for t in times:
        arr = power(tv(compose(t), t, int(t * FPS)), t)
        Image.fromarray(arr).save(folder / f"s_{t:06.2f}.png")
        print("still", t, flush=True)


def main():
    if "--still" in sys.argv:
        stills([float(x) for x in sys.argv[sys.argv.index("--still") + 1].split(",")])
        return
    OUT.mkdir(exist_ok=True)
    audio = mix()
    with wave.open(str(WORK / "mix.wav"), "wb") as w:
        w.setnchannels(2)
        w.setsampwidth(2)
        w.setframerate(RATE)
        w.writeframes((np.clip(audio.T, -1, 1) * 32767).astype(np.int16).tobytes())
    if "--audio" in sys.argv:
        return
    path = OUT / "BOMBERSYS-promo.mp4"
    total = int(TOTAL * FPS)
    started = time.time()
    with av.open(str(path), "w", options={"movflags": "+faststart"}) as box:
        v = box.add_stream("libx264", rate=FPS)
        v.width, v.height, v.pix_fmt = W, H, "yuv420p"
        v.options = {"crf": "22", "preset": "medium"}
        a = box.add_stream("aac", rate=RATE)
        a.layout = "stereo"
        a.bit_rate = 192000
        position = 0

        def write_audio(until):
            nonlocal position
            until = min(until, audio.shape[1])
            while position < until:
                chunk = min(1024, audio.shape[1] - position)
                part = audio[:, position:position + chunk]
                if part.shape[1] < 1024:
                    part = np.pad(part, ((0, 0), (0, 1024 - part.shape[1])))
                frame = av.AudioFrame.from_ndarray(np.ascontiguousarray(part), format="fltp", layout="stereo")
                frame.sample_rate, frame.pts, frame.time_base = RATE, position, Fraction(1, RATE)
                for packet in a.encode(frame):
                    box.mux(packet)
                position += chunk

        for i in range(total):
            now = i / FPS
            arr = power(tv(compose(now), now, i), now)
            frame = av.VideoFrame.from_ndarray(arr, format="rgb24")
            frame.pts, frame.time_base = i, Fraction(1, FPS)
            for packet in v.encode(frame):
                box.mux(packet)
            write_audio(int((i + 1) / FPS * RATE))
            if i % 60 == 0:
                spent = time.time() - started
                left = spent / (i + 1) * (total - i)
                print(f"PROGRESS {i}/{total} ({100 * i // total}%)  spent {spent:.0f} s, left about {left:.0f} s", flush=True)
        write_audio(audio.shape[1])
        for packet in v.encode():
            box.mux(packet)
        for packet in a.encode():
            box.mux(packet)
    print(f"DONE {path}  {path.stat().st_size / 1e6:.1f} MB, {time.time() - started:.0f} s", flush=True)


if __name__ == "__main__":
    sys.stdout.reconfigure(encoding="utf-8")
    main()
