"""Веб-сервер: отдаёт браузеру страницу игры и держит с ним связь по WebSocket.

Запуск:  uv run bombersys   (из папки backend) — откроется браузер на http://127.0.0.1:8000

Партия живёт в «комнате». Своя игра — комната на одну вкладку, она управляет всеми героями.
Игра по сети — комната на две вкладки (обычно на двух ноутбуках в одной Wi-Fi):
хозяин — Иван, гость — Колян, каждый управляет только своим героем.
Браузер присылает нажатия клавиш, сервер 30 раз в секунду пересчитывает игру
и рассылает её состояние всем в комнате.

Сообщения от браузера (JSON):
    {"type": "start", "players": 1}           своя игра на 1 или 2 игроков (за одной клавиатурой)
    {"type": "host"}                          создать игру по сети и ждать второго
    {"type": "join"}                          присоединиться к созданной игре по сети
    {"type": "dir", "player": 0, "dir": "up", "alt": "left"}
                                              куда жмёт игрок (null — отпустил);
                                              alt — предыдущая ещё зажатая клавиша
    {"type": "bomb", "player": 0}             поставить бомбу
    {"type": "pause"}                         пауза / продолжить
    {"type": "quit"}                          выйти в меню (в игре по сети — закончить её для обоих)

Ответы сервера, кроме состояния игры ("state"):
    {"type": "hosting", "urls": [...]}        игра по сети создана; urls — что ввести второму игроку
    {"type": "joined", "seat": 0}             второй пришёл, партия началась; seat — ваш герой
    {"type": "left", "name": "Колян"}         второй игрок вышел — партия окончена
    {"type": "error", "text": "..."}          не получилось (например, игру по сети никто не создал)
"""

from __future__ import annotations

import asyncio
import contextlib
import ipaddress
import mimetypes
import os
import socket
import sys
import threading
import webbrowser
from importlib.metadata import PackageNotFoundError, version
from pathlib import Path

from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.staticfiles import StaticFiles

from . import records
from .game.engine import Game
from .game.config import NAMES, TICK_RATE
from .game.difficulty import table

# В собранном BOMBERSYS.exe файлы лежат во временной папке распаковки (sys._MEIPASS).
FROZEN = getattr(sys, "frozen", False)
FRONTEND = (Path(sys._MEIPASS) if FROZEN else Path(__file__).resolve().parents[2]) / "frontend"
# Слушаем всю домашнюю сеть, чтобы второй ноутбук мог подключиться; свой браузер открываем по 127.0.0.1.
HOST, PORT = "0.0.0.0", 8000

try:
    VERSION = version("bombersys")   # номер версии — из pyproject.toml, одно место на всю игру
except PackageNotFoundError:
    VERSION = "?"

app = FastAPI(title="BOMBERSYS")


@app.middleware("http")
async def always_fresh_files(request, call_next):
    """Браузер сверяет каждый файл игры с сервером перед использованием: после обновления
    игры он не станет запускать старые скрипты из своего кэша вперемешку с новыми."""
    response = await call_next(request)
    response.headers["Cache-Control"] = "no-cache"
    return response


@app.get("/api/version")
def get_version() -> dict:
    return {"version": VERSION}


@app.get("/api/records")
def get_records() -> list[dict]:
    return records.load()


@app.get("/api/difficulty")
def get_difficulty(players: int = 1) -> list[dict]:
    """Таблица сложности по уровням — удобно смотреть при настройке баланса."""
    return table(15, players)


class Member:
    """Одна вкладка браузера. seat — каким героем управляет (None — всеми: своя игра за одной клавиатурой)."""

    def __init__(self, websocket: WebSocket) -> None:
        self.websocket = websocket
        self.seat: int | None = None
        self.room: Room | None = None

    async def send(self, message: dict) -> None:
        with contextlib.suppress(Exception):  # вкладку уже закрыли — её обработчик сам всё уберёт
            await self.websocket.send_json(message)


class Room:
    """Партия и те, кто в неё играет. Сама двигает игру 30 раз в секунду и рассылает состояние."""

    def __init__(self, network: bool) -> None:
        self.network = network
        self.members: list[Member] = []
        self.game: Game | None = None
        self.task: asyncio.Task | None = None

    def add(self, member: Member, seat: int | None) -> None:
        member.room, member.seat = self, seat
        self.members.append(member)

    def start(self, players: int) -> None:
        self.game = Game(players=players)
        if self.task is None:
            self.task = asyncio.create_task(self.run())

    def handle(self, member: Member, message: dict) -> None:
        if self.game is None:
            return
        kind = message.get("type")
        # в игре по сети каждый управляет только своим героем, что бы ни прислал браузер
        player = member.seat if member.seat is not None else int(message.get("player", 0))
        if kind == "dir":
            self.game.set_direction(player, message.get("dir"), message.get("alt"))
        elif kind == "bomb":
            self.game.place_bomb(player)
        elif kind == "pause":
            self.game.toggle_pause()

    def tick(self, dt: float) -> dict | None:
        """Сдвигает игру на dt секунд и возвращает то, что надо разослать."""
        if self.game is None:
            return None
        self.game.update(dt)
        state = self.game.snapshot()
        if self.game.phase == "game_over":
            names = [p.name for p in self.game.players]
            state["records"] = records.add(names, self.game.level, self.game.total_score)
            self.game = None  # партия окончена: своя игра ждёт новый «start», сетевая закрывается
        return state

    async def run(self) -> None:
        loop = asyncio.get_running_loop()
        dt = 1 / TICK_RATE
        next_tick = loop.time()
        while self.members:
            state = self.tick(dt)
            if state is not None:
                for member in list(self.members):
                    await member.send(state)
                if self.network and self.game is None:
                    self.close()
                    return
            next_tick += dt
            await asyncio.sleep(max(0.0, next_tick - loop.time()))

    def close(self) -> None:
        for member in self.members:
            member.room, member.seat = None, None
        self.members.clear()
        self.game = None


class Lobby:
    """Раздаёт вкладки по комнатам. Ждущая игра по сети — одна: второй присоединяется к ней."""

    def __init__(self) -> None:
        self.waiting: Room | None = None

    async def handle(self, member: Member, message: dict) -> None:
        kind = message.get("type")
        if kind == "start":
            await self.leave(member)
            room = Room(network=False)
            room.add(member, seat=None)
            room.start(players=2 if message.get("players") == 2 else 1)
        elif kind == "host":
            await self.leave(member)
            room = Room(network=True)
            room.add(member, seat=0)
            self.waiting = room
            port = member.websocket.scope.get("server", (None, PORT))[1]
            await member.send({"type": "hosting", "urls": [f"http://{ip}:{port}" for ip in lan_addresses()]})
        elif kind == "join":
            room = self.waiting
            if room is None or not room.members or member.room is room:
                await member.send({"type": "error", "text": "Игру по сети пока никто не создал"})
                return
            await self.leave(member)
            self.waiting = None
            room.add(member, seat=1)
            for m in room.members:
                await m.send({"type": "joined", "seat": m.seat})
            room.start(players=2)
        elif kind == "quit":
            await self.leave(member)
        elif member.room is not None:
            member.room.handle(member, message)

    async def leave(self, member: Member) -> None:
        """Вкладка вышла из комнаты (в меню или закрылась). Сетевая партия без одного — закончена."""
        room = member.room
        if room is None:
            return
        if room is self.waiting:
            self.waiting = None
        if room.network:
            others = [m for m in room.members if m is not member]
            name = NAMES[member.seat or 0]
            room.close()
            for other in others:
                await other.send({"type": "left", "name": name})
        else:
            room.close()


lobby = Lobby()


def lan_addresses() -> list[str]:
    """Адреса этого компьютера в домашней сети (192.168.x.x и т. п.) — их вводит второй игрок.
    Первым — тот, через который компьютер выходит в сеть."""
    found = []
    with contextlib.suppress(OSError), socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as probe:
        probe.connect(("192.168.0.1", 9))   # пакет не уходит: так лишь узнаём, какой адрес «главный»
        found.append(probe.getsockname()[0])
    with contextlib.suppress(OSError):
        found += [info[4][0] for info in socket.getaddrinfo(socket.gethostname(), None, socket.AF_INET)]
    usable = []
    for ip in dict.fromkeys(found):
        address = ipaddress.ip_address(ip)
        if address.is_private and not address.is_loopback and not address.is_link_local:
            usable.append(ip)
    return usable


@app.websocket("/ws")
async def play(websocket: WebSocket) -> None:
    await websocket.accept()
    member = Member(websocket)
    try:
        while True:
            await lobby.handle(member, await websocket.receive_json())
    except (WebSocketDisconnect, RuntimeError):
        pass  # вкладку закрыли
    finally:
        await lobby.leave(member)


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
    url = f"http://127.0.0.1:{port}"
    print(f"BOMBERSYS {VERSION} запущен: {url}", flush=True)
    for lan in lan_addresses():
        print(f"Для игры по сети второй игрок открывает: http://{lan}:{port}", flush=True)
    print("Играйте в открывшемся браузере. Чтобы выйти — закройте это окно (или Ctrl+C).", flush=True)
    if not os.environ.get("BOMBERSYS_NO_BROWSER"):  # для автопроверок — без браузера
        threading.Timer(1.0, webbrowser.open, args=[url]).start()
    uvicorn.run(app, host=HOST, port=port, log_level="warning")
