"""Герои крупным планом для ролика: те же модели, что в игре (mockups/realhero/real_render.py), но камера почти на
уровне груди и герой развёрнут вполоборота. Сцена и бег берутся из игрового сценария без копирования.

  set BLENDER_USER_RESOURCES=C:\\Blender\\user
  blender -b --python-exit-code 1 -P promo/render_heroes.py -- --tag P --look I1 --size 720 --dirs down --turn 32 --out promo/work/heroes
"""
from pathlib import Path

SOURCE = Path(__file__).resolve().parents[1] / "mockups" / "realhero" / "real_render.py"
code = SOURCE.read_text(encoding="utf-8")
for old, new in [('float(OPTS["ortho"]), 0.60, 30.0, 6.0', 'float(OPTS["ortho"]), 0.60, 9.0, 6.0'),
                 ('TURN = {"down": 0,', 'TURN = {"down": float(OPTS["turn"]),')]:
    if old not in code:
        raise SystemExit(f"real_render.py изменился, не нашёл: {old}")
    code = code.replace(old, new)
exec(compile(code, str(SOURCE), "exec"), {"__name__": "__main__", "__file__": str(SOURCE)})
