"""Веб-сервер: отдаёт браузеру страницу игры и держит с ним связь по WebSocket.

Запуск:  uv run bombersys   (из папки backend) — откроется браузер на http://127.0.0.1:8000

Каждая вкладка браузера — своя отдельная партия. Браузер присылает нажатия клавиш,
сервер 30 раз в секунду пересчитывает игру и отправляет обратно её состояние.

Сообщения от браузера (JSON):
    {"type": "start", "players": 1}           новая игра на 1 или 2 игроков
    {"type": "dir", "player": 0, "dir": "up", "alt": "left"}
                                              куда жмёт игрок (null — отпустил);
                                              alt — предыдущая ещё зажатая клавиша
    {"type": "bomb", "player": 0}             поставить бомбу
    {"type": "pause"}                         пауза / продолжить
    {"type": "quit"}                          выйти в меню
"""

from __future__ import annotations

import asyncio
import contextlib
import mimetypes
import os
import socket
import sys
import threading
import webbrowser
from pathlib import Path

from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.staticfiles import StaticFiles

from . import records
from .game.engine import Game
from .game.config import TICK_RATE
from .game.difficulty import table

# В собранном BOMBERSYS.exe файлы лежат во временной папке распаковки (sys._MEIPASS).
FROZEN = getattr(sys, "frozen", False)
FRONTEND = (Path(sys._MEIPASS) if FROZEN else Path(__file__).resolve().parents[2]) / "frontend"
HOST, PORT = "127.0.0.1", 8000

app = FastAPI(title="BOMBERSYS")


@app.get("/api/records")
def get_records() -> list[dict]:
    return records.load()


@app.get("/api/difficulty")
def get_difficulty(players: int = 1) -> list[dict]:
    """Таблица сложности по уровням — удобно смотреть при настройке баланса."""
    return table(15, players)


class Session:
    """Одна вкладка браузера: принимает команды и ведёт партию."""

    def __init__(self) -> None:
        self.game: Game | None = None

    def handle(self, message: dict) -> None:
        kind = message.get("type")
        if kind == "start":
            self.game = Game(players=2 if message.get("players") == 2 else 1)
        elif self.game is None:
            return
        elif kind == "dir":
            self.game.set_direction(int(message.get("player", 0)), message.get("dir"), message.get("alt"))
        elif kind == "bomb":
            self.game.place_bomb(int(message.get("player", 0)))
        elif kind == "pause":
            self.game.toggle_pause()
        elif kind == "quit":
            self.game = None

    def tick(self, dt: float) -> dict | None:
        """Сдвигает игру на dt секунд и возвращает то, что надо отправить в браузер."""
        if self.game is None:
            return None
        self.game.update(dt)
        state = self.game.snapshot()
        if self.game.phase == "game_over":
            names = [p.name for p in self.game.players]
            state["records"] = records.add(names, self.game.level, self.game.total_score)
            self.game = None  # партия окончена, ждём новый «start»
        return state


@app.websocket("/ws")
async def play(websocket: WebSocket) -> None:
    await websocket.accept()
    session = Session()

    async def receive() -> None:
        while True:
            session.handle(await websocket.receive_json())

    reader = asyncio.create_task(receive())
    loop = asyncio.get_running_loop()
    dt = 1 / TICK_RATE
    next_tick = loop.time()
    try:
        while not reader.done():
            state = session.tick(dt)
            if state is not None:
                await websocket.send_json(state)
            next_tick += dt
            await asyncio.sleep(max(0.0, next_tick - loop.time()))
    except (WebSocketDisconnect, RuntimeError):
        pass  # вкладку закрыли — просто заканчиваем партию
    finally:
        reader.cancel()
        with contextlib.suppress(asyncio.CancelledError, Exception):
            await reader


# Всё остальное — файлы фронтенда (index.html, скрипты, картинки).
# В реестре Windows у .js иногда записан тип text/plain — тогда браузер не запустит скрипты.
mimetypes.add_type("text/javascript", ".js")
app.mount("/", StaticFiles(directory=FRONTEND, html=True), name="frontend")


def free_port(preferred: int) -> int:
    """8000, если свободен, иначе любой свободный порт."""
    with socket.socket() as probe:
        try:
            probe.bind((HOST, preferred))
        except OSError:
            probe.bind((HOST, 0))
        return probe.getsockname()[1]


def run() -> None:
    import uvicorn

    port = free_port(PORT)
    url = f"http://{HOST}:{port}"
    print(f"BOMBERSYS запущен: {url}", flush=True)
    print("Играйте в открывшемся браузере. Чтобы выйти — закройте это окно (или Ctrl+C).", flush=True)
    if not os.environ.get("BOMBERSYS_NO_BROWSER"):  # для автопроверок — без браузера
        threading.Timer(1.0, webbrowser.open, args=[url]).start()
    uvicorn.run(app, host=HOST, port=port, log_level="warning")
