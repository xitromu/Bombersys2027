"""Таблица рекордов: 10 лучших результатов в файле backend/data/records.json."""

from __future__ import annotations

import json
import sys
from datetime import datetime
from pathlib import Path

# У собранного BOMBERSYS.exe рекорды лежат рядом с ним, в папке bombersys_data.
if getattr(sys, "frozen", False):
    RECORDS_FILE = Path(sys.executable).resolve().parent / "bombersys_data" / "records.json"
else:
    RECORDS_FILE = Path(__file__).resolve().parent.parent / "data" / "records.json"
TOP = 10


def load(path: Path | None = None) -> list[dict]:
    try:
        return json.loads((path or RECORDS_FILE).read_text(encoding="utf-8"))
    except (FileNotFoundError, json.JSONDecodeError):
        return []


def add(names: list[str], level: int, score: int, path: Path | None = None) -> list[dict]:
    """Добавляет результат и возвращает обновлённую таблицу."""
    path = path or RECORDS_FILE
    entry = {
        "names": " и ".join(names),
        "level": level,
        "score": score,
        "date": datetime.now().strftime("%d.%m.%Y"),
    }
    records = sorted([*load(path), entry], key=lambda r: (r["score"], r["level"]), reverse=True)[:TOP]
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(records, ensure_ascii=False, indent=2), encoding="utf-8")
    return records
