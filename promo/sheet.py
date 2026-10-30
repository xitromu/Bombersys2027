"""Обзорный лист дубля и список его событий: python -I promo/sheet.py <дубль> [с какой секунды] [по какую] [шаг]."""
import json
import sys
from pathlib import Path

from PIL import Image, ImageDraw

WORK = Path(__file__).resolve().parent / "work"
name = sys.argv[1]
start = float(sys.argv[2]) if len(sys.argv) > 2 else 0
folder = WORK / "takes" / name
frames = json.loads((folder / "frames.json").read_text())
events = json.loads((folder / "events.json").read_text())
end = float(sys.argv[3]) if len(sys.argv) > 3 else frames[-1] - frames[0]
step = float(sys.argv[4]) if len(sys.argv) > 4 else max(0.5, (end - start) / 24)
print(name, len(frames), f"{frames[-1] - frames[0]:.1f}s")
print(" ".join(f"{e['t'] - frames[0]:.1f}:{e['type']}" + (f"({e.get('cause')})" if e["type"] == "player_died" else "")
               for e in events if e["type"] not in ("track", "bomb_placed", "wall_destroyed")))
cols, w, h = 6, 340, 248
times = [start + i * step for i in range(int((end - start) / step) + 1)]
rows = (len(times) + cols - 1) // cols
sheet = Image.new("RGB", (cols * w, rows * h))
for i, t in enumerate(times):
    k = min(range(len(frames)), key=lambda j: abs(frames[j] - frames[0] - t))
    im = Image.open(folder / f"f_{k:05d}.jpg").resize((w, h))
    ImageDraw.Draw(im).text((4, 4), f"{t:.1f}", fill="yellow")
    sheet.paste(im, (i % cols * w, i // cols * h))
sheet.save(WORK / f"sheet_{name}.png")
