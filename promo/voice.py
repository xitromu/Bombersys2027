"""Голос диктора: Silero на видеокарте (окружение и модель — из C:\\projects\\CHESS\\voicekit).

  C:\\projects\\CHESS\\voicekit\\.venv\\Scripts\\python.exe promo\\voice.py [--speaker eugene]

Пишет promo/work/voice/<speaker>/<номер>.wav (48 кГц, моно, без обработки: эхо и «телевизор» добавляет make_video.py).
Плюс перед гласной — ударение. Лицензия моделей Silero — некоммерческая: игра бесплатная, ролик тоже.
"""

from __future__ import annotations

import argparse
import os
import sys
import wave
from pathlib import Path

VOICEKIT = Path(r"C:\projects\CHESS\voicekit")
os.environ.setdefault("TORCH_HOME", str(VOICEKIT / ".cache" / "torch"))

import numpy as np  # noqa: E402
import torch  # noqa: E402

OUT = Path(__file__).resolve().parent / "work" / "voice"

# Имя -> текст. Время каждой реплики в ролике — в make_video.py (SCRIPT).
LINES = {
    "title": "Б+омберсис или Бомбич+ел!",
    "home": "Игров+ой автом+ат — пр+ямо у вас д+ома!",
    "bombs": "Ст+авь б+омбы! Круш+и ст+ены! Бег+и от огн+я!",
    "chain": "Цепн+ая ре+акция! Всё взлет+ает на в+оздух!",
    "choose": "В+ыбери бойц+а!",
    "ivan": "Ив+ан! В в+атнике!",
    "igor": "+Игорь — в комбинез+оне танк+иста.",
    "toothy": "Берег+ись зуб+астиков: отк+усят г+олову!",
    "snake": "А зме+я обгл+одает — до кост+ей!",
    "two": "Игр+ай вдво+ём! За одн+ой клавиат+урой, +или по сет+и!",
    "revive": "Пог+иб нап+арник? Отд+ай ем+у сво+ю жизнь!",
    "levels": "Б+ольше десят+и +уровней! Табл+ица рек+ордов!",
    "free": "Мон+ета не нужн+а! Б+омбичел — беспл+атно!",
    "github": "Скач+ай на гитх+абе!",
    "legal": "Перед игр+ой проконсульт+ируйтесь с нап+арником.",
}
RATE = 48000


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--speaker", default="eugene")
    ap.add_argument("--model", default="v5_ru")
    args = ap.parse_args()
    hub = Path(os.environ["TORCH_HOME"]) / "hub" / "snakers4_silero-models_master"
    model, _ = torch.hub.load(repo_or_dir=str(hub), source="local", model="silero_tts", language="ru", speaker=args.model,
                              trust_repo=True)
    device = "cuda" if torch.cuda.is_available() else "cpu"
    model.to(device)
    print("speakers", getattr(model, "speakers", None), "device", device, flush=True)
    out = OUT / args.speaker
    out.mkdir(parents=True, exist_ok=True)
    for name, text in LINES.items():
        audio = model.apply_tts(text=text, speaker=args.speaker, sample_rate=RATE, put_accent=True, put_yo=True)
        data = audio.detach().cpu().numpy().astype(np.float32)
        with wave.open(str(out / f"{name}.wav"), "wb") as w:
            w.setnchannels(1)
            w.setsampwidth(2)
            w.setframerate(RATE)
            w.writeframes((np.clip(data, -1, 1) * 32767).astype(np.int16).tobytes())
        print(f"{name}: {len(data) / RATE:.2f} s", flush=True)


if __name__ == "__main__":
    sys.stdout.reconfigure(encoding="utf-8")
    main()
