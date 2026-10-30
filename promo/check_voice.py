"""Проверка без колонок: что слышно в итоговой дорожке promo/work/mix.wav — по кускам, где говорит диктор
(Whisper на видеокарте, окружение CHESS). Запуск: C:\\projects\\CHESS\\voicekit\\.venv\\Scripts\\python.exe promo\\check_voice.py
"""

import sys
import wave
from pathlib import Path

import numpy as np
import torch
from transformers import pipeline

PIECES = [(4.2, 6.1), (6.4, 9.0), (9.2, 12.5), (14.4, 17.2), (18.0, 19.3), (19.5, 20.9), (21.0, 23.1), (24.0, 26.8), (27.1, 28.9), (30.0, 33.6),
          (36.0, 38.7), (39.0, 42.0), (42.0, 45.0), (45.0, 46.4), (49.4, 51.7)]
path = Path(__file__).resolve().parent / "work" / "mix.wav"
with wave.open(str(path), "rb") as w:
    rate = w.getframerate()
    channels = w.getnchannels()
    data = np.frombuffer(w.readframes(w.getnframes()), dtype=np.int16).astype(np.float32) / 32768
mono = data.reshape(-1, channels).mean(axis=1)
target = 16000
asr = pipeline("automatic-speech-recognition", model="openai/whisper-large-v3-turbo", device=0 if torch.cuda.is_available() else -1,
               dtype=torch.float16 if torch.cuda.is_available() else torch.float32)
sys.stdout.reconfigure(encoding="utf-8")
for a, b in PIECES:
    piece = mono[int(a * rate):int(b * rate)]
    x = np.arange(0, len(piece), rate / target)
    sample = np.interp(x, np.arange(len(piece)), piece).astype(np.float32)
    print(f"{a:5.1f}-{b:5.1f}:", asr({"array": sample, "sampling_rate": target}, generate_kwargs={"language": "russian"})["text"])
