"""Снимает настоящую игру для промо-ролика: Edge без окна, бот на странице жмёт те же сообщения, что и клавиши.

Запуск из backend/.venv:  python promo/capture.py [название дубля ...]
Кадры: promo/work/takes/<дубль>/f_00000.jpg, frames.json (время кадров), events.json (события игры и положение
героев и врагов) — по ним make_video.py выбирает моменты и ставит звуки.
"""

from __future__ import annotations

import asyncio
import base64
import json
import shutil
import subprocess
import sys
import time
import urllib.request
from pathlib import Path

import websockets

HERE = Path(__file__).resolve().parent
ROOT = HERE.parent
WORK = HERE / "work"
TAKES = WORK / "takes"
EDGE = r"C:\Program Files (x86)\Microsoft\Edge\Application\msedge.exe"
PYTHON = ROOT / "backend" / ".venv" / "Scripts" / "python.exe"
PORT, DEBUG_PORT = 8011, 9333
SCENE = "window.__game.scene.getScene('game')"

HOOK = """(() => { let P; Object.defineProperty(window, 'Phaser', { configurable: true, get() { return P; },
  set(v) { P = v; const Game = v.Game; v.Game = class extends Game { constructor(c) { super(c); window.__game = this; } }; } }); })()"""

# Бот живёт на странице: читает то же состояние, что рисует игра, и шлёт те же сообщения, что клавиатура.
# Режимы героя: play — играет сам; seek — идёт прямо на врага; bomb_self — ставит бомбу и стоит; idle — стоит;
# goto — идёт к клетке bot.goal[i].
BOT = r"""
window.__bot = (() => {
  const N = 15, DIRS = { left: [-1, 0], right: [1, 0], up: [0, -1], down: [0, 1] };
  const bot = { mode: ['play', 'play'], goal: [null, null], revive: true, door: false, log: [], lastDir: [undefined, undefined],
                lastBomb: [0, 0], send: null, bombGap: 900 };
  const net = window.__game.registry.get('net');
  bot.send = (m) => net.send(m);
  const key = (x, y) => y * N + x;
  const inside = (x, y) => x >= 0 && y >= 0 && x < N && y < N;

  net.onState((st) => {
    const t = Date.now() / 1000;
    for (const e of st.events) bot.log.push({ t, ...e });
    if (!bot.lastTrack || t - bot.lastTrack >= 0.1) {
      bot.lastTrack = t;
      bot.log.push({ t, type: 'track', phase: st.phase, level: st.level,
        p: st.players.map((p) => [p.x, p.y, p.state, p.score, p.lives]),
        e: st.enemies.map((e) => [e.x, e.y, e.kind, e.tier]), b: st.bombs.length, f: st.flames.length });
    }
  });

  function blast(grid, x, y) {
    const cells = [key(x, y)];
    for (const [dx, dy] of Object.values(DIRS)) for (let s = 1; s <= 2; s++) {
      const cx = x + dx * s, cy = y + dy * s;
      if (!inside(cx, cy) || grid[key(cx, cy)] === '#') break;
      cells.push(key(cx, cy));
      if (grid[key(cx, cy)] === 'w') break;
    }
    return cells;
  }

  function bfs(grid, sx, sy, blocked, goal) {
    const seen = new Map([[key(sx, sy), null]]), queue = [[sx, sy]];
    while (queue.length) {
      const [x, y] = queue.shift();
      if (goal(x, y)) {
        const path = [[x, y]];
        let k = seen.get(key(x, y));
        while (k !== null) { path.unshift([k % N, Math.floor(k / N)]); k = seen.get(k); }
        return path;
      }
      for (const [dx, dy] of Object.values(DIRS)) {
        const nx = x + dx, ny = y + dy, k = key(nx, ny);
        if (!inside(nx, ny) || seen.has(k) || grid[k] !== '.' || blocked.has(k)) continue;
        seen.set(k, key(x, y));
        queue.push([nx, ny]);
      }
    }
    return null;
  }

  function steer(i, p, path) {
    let dir = null;
    if (path && path.length > 1) {
      const [nx, ny] = path[1], cx = Math.round(p.x), cy = Math.round(p.y);
      dir = Object.keys(DIRS).find((d) => DIRS[d][0] === nx - cx && DIRS[d][1] === ny - cy) ?? null;
    }
    if (dir !== bot.lastDir[i]) {
      bot.lastDir[i] = dir;
      bot.send({ type: 'dir', player: i, dir, alt: null });
    }
  }

  function think(st, i) {
    const p = st.players[i], grid = st.grid;
    if (p.state !== 'alive') {
      bot.lastDir[i] = undefined;
      return;
    }
    if (bot.revive && p.can_revive && !bot.reviveHold) bot.send({ type: 'revive', player: i });
    const cx = Math.round(p.x), cy = Math.round(p.y), mode = bot.mode[i];
    if (mode === 'idle') return steer(i, p, null);

    const danger = new Set(), monsters = new Set(), traps = new Set();
    for (const b of st.bombs) for (const c of blast(grid, b.x, b.y)) danger.add(c);
    for (const f of st.flames) danger.add(key(f.x, f.y));
    for (const e of st.enemies) {
      const points = e.kind === 'snake' ? [[e.x, e.y], ...(e.path || [])] : [[e.x, e.y]];
      for (const [ex, ey] of points) {
        const rx = Math.round(ex), ry = Math.round(ey);
        monsters.add(key(rx, ry));
        for (const [dx, dy] of Object.values(DIRS)) if (inside(rx + dx, ry + dy)) monsters.add(key(rx + dx, ry + dy));
      }
    }
    for (const it of st.items) if (it.kind === 'death' || (it.kind === 'door' && !bot.door)) traps.add(key(it.x, it.y));

    if (mode === 'goto') {
      const [gx, gy] = bot.goal[i];
      return steer(i, p, bfs(grid, cx, cy, new Set(), (x, y) => x === gx && y === gy));
    }
    if (mode === 'seek') {
      const fire = new Set(st.flames.map((f) => key(f.x, f.y)));
      return steer(i, p, bfs(grid, cx, cy, fire, (x, y) => st.enemies.some(
        (e) => Math.round(e.x) === x && Math.round(e.y) === y)));
    }
    if (mode === 'seek_snake') {
      const fire = new Set(st.flames.map((f) => key(f.x, f.y)));
      return steer(i, p, bfs(grid, cx, cy, fire, (x, y) => st.enemies.some(
        (e) => e.kind === 'snake' && Math.round(e.x) === x && Math.round(e.y) === y)));
    }
    if (mode === 'bomb_self') {
      bot.send({ type: 'bomb', player: i });
      return steer(i, p, null);
    }

    const avoid = new Set([...danger, ...monsters, ...traps]);
    const isSafe = (x, y) => !avoid.has(key(x, y));
    if (!isSafe(cx, cy)) {
      const fire = new Set(st.flames.map((f) => key(f.x, f.y)));
      return steer(i, p, bfs(grid, cx, cy, new Set([...fire, ...traps]), isSafe));
    }
    const canBomb = p.bombs > 0 && performance.now() - bot.lastBomb[i] > bot.bombGap;
    const worth = (x, y) => blast(grid, x, y).some((k) => grid[k] === 'w'
      || st.enemies.some((e) => key(Math.round(e.x), Math.round(e.y)) === k));
    const escape = (x, y) => {
      const hot = new Set([...avoid, ...blast(grid, x, y)]);
      return bfs(grid, x, y, new Set([...st.flames.map((f) => key(f.x, f.y)), ...traps]), (a, b) => !hot.has(key(a, b)));
    };
    if (canBomb && worth(cx, cy) && escape(cx, cy)) {
      bot.lastBomb[i] = performance.now();
      bot.send({ type: 'bomb', player: i });
      return steer(i, p, escape(cx, cy));
    }
    const prizes = new Set(st.items.filter((it) => it.kind !== 'death' && (it.kind !== 'door' || bot.door))
      .map((it) => key(it.x, it.y)));
    const path = bfs(grid, cx, cy, avoid, (x, y) => prizes.has(key(x, y)))
      ?? bfs(grid, cx, cy, avoid, (x, y) => worth(x, y) && (x !== cx || y !== cy) && !!escape(x, y));
    if (path) return steer(i, p, path);
    bot.door = true;
    return steer(i, p, null);
  }

  setInterval(() => {
    const scene = window.__game.scene.getScene('game');
    const st = scene && scene.curr;
    if (!st || st.phase !== 'playing') return;
    st.players.forEach((_, i) => think(st, i));
  }, 60);
  return bot;
})();
"""


class Browser:
    """Связь с Edge по протоколу отладки; кадры записывает прямо в потоке чтения, чтобы не копить очередь."""

    def __init__(self, ws):
        self.ws = ws
        self.n = 0
        self.waiting: dict[int, asyncio.Future] = {}
        self.folder: Path | None = None
        self.frames: list[float] = []
        self.problems: list[str] = []

    async def read(self):
        async for raw in self.ws:
            msg = json.loads(raw)
            if "id" in msg:
                self.waiting.pop(msg["id"]).set_result(msg)
            elif msg.get("method") == "Page.screencastFrame":
                self.on_frame(msg["params"])
            elif msg.get("method") == "Runtime.exceptionThrown":
                d = msg["params"]["exceptionDetails"]
                self.problems.append(d.get("text", "") + " " + str(d.get("exception", {}).get("description", ""))[:300])

    def on_frame(self, params):
        if self.folder is not None:
            (self.folder / f"f_{len(self.frames):05d}.jpg").write_bytes(base64.b64decode(params["data"]))
            self.frames.append(params["metadata"]["timestamp"])
        asyncio.ensure_future(self.ws.send(json.dumps({"id": self.next_id(), "method": "Page.screencastFrameAck",
                                                       "params": {"sessionId": params["sessionId"]}})))

    def next_id(self):
        self.n += 1
        future = asyncio.get_running_loop().create_future()
        self.waiting[self.n] = future
        return self.n

    async def call(self, method, **params):
        mine = self.next_id()
        future = self.waiting[mine]
        await self.ws.send(json.dumps({"id": mine, "method": method, "params": params}))
        msg = await future
        if "error" in msg:
            raise RuntimeError(f"{method}: {msg['error']}")
        return msg.get("result", {})

    async def js(self, expression):
        r = await self.call("Runtime.evaluate", expression=expression, returnByValue=True, awaitPromise=True)
        if "exceptionDetails" in r:
            raise RuntimeError("JS: " + json.dumps(r["exceptionDetails"])[:600])
        return r.get("result", {}).get("value")

    async def promo(self, cmd, **args):
        await self.js(f"window.__bot.send({json.dumps({'type': 'promo', 'cmd': cmd, **args})})")

    async def start_recording(self, name):
        self.folder = TAKES / name
        shutil.rmtree(self.folder, ignore_errors=True)
        self.folder.mkdir(parents=True)
        self.frames = []
        await self.js("window.__bot && (window.__bot.log = [])")
        await self.call("Page.startScreencast", format="jpeg", quality=93, maxWidth=1018, maxHeight=742, everyNthFrame=2)

    async def stop_recording(self):
        await self.call("Page.stopScreencast")
        log = await self.js("JSON.stringify(window.__bot ? window.__bot.log : [])")
        (self.folder / "events.json").write_text(log, encoding="utf-8")
        (self.folder / "frames.json").write_text(json.dumps(self.frames), encoding="utf-8")
        spent = self.frames[-1] - self.frames[0] if len(self.frames) > 1 else 0
        print(f"TAKE {self.folder.name}: {len(self.frames)} frames, {spent:.1f} s, "
              f"{len(self.frames) / max(spent, 0.01):.1f} fps", flush=True)
        self.folder = None


async def open_game(page, players):
    await page.call("Page.navigate", url=f"http://127.0.0.1:{PORT}/")
    for _ in range(80):
        await asyncio.sleep(0.25)
        if await page.js("!!(window.__game && window.__game.scene.isActive('menu') "
                         "&& window.__game.registry.get('net').connected)"):
            break
    await asyncio.sleep(0.4)
    await page.js(f"window.__game.scene.getScene('menu').scene.start('game', {{ players: {players} }}); 0")
    await asyncio.sleep(0.8)
    await page.js(BOT + "; 0")


# ------------------------------------------------------------------ дубли

async def take_play(page, name="play", level=2, seed=11, seconds=45, players=2):
    """Обычная партия: оба бота играют сами."""
    await open_game(page, players)
    await page.promo("level", level=level, seed=seed)
    await page.start_recording(name)
    await asyncio.sleep(seconds)
    await page.stop_recording()


async def take_chain(page):
    """Цепная реакция: семь бомб в ряд, вокруг стены, в ряду враги. Рвутся по настоящим правилам."""
    await open_game(page, 2)
    await page.js("window.__bot.mode = ['idle', 'idle']; window.__bot.revive = false")
    await page.promo("level", level=3, seed=5)
    await asyncio.sleep(2.0)
    y, xs = 8, [1, 3, 5, 7, 9, 11, 13]
    await page.promo("hero", index=0, x=0, y=0)
    await page.promo("hero", index=1, x=14, y=14)
    await page.promo("walls_around", y=y, xs=xs)
    await page.start_recording("chain")
    await asyncio.sleep(0.4)
    await page.promo("chain", y=y, xs=xs, fuse=2.4, owner=0)
    await page.promo("enemy", x=6, y=8, strong=False)
    await page.promo("enemy", x=10, y=8, strong=True)
    await page.promo("enemy", x=2, y=8, strong=True)
    await asyncio.sleep(0.1)
    await page.js("window.__bot.mode = ['play', 'play']")
    await asyncio.sleep(9)
    await page.stop_recording()


async def take_eaten(page):
    """Герой сам идёт на зубастика: голову откусывают по настоящим правилам."""
    await open_game(page, 2)
    await page.js("window.__bot.revive = false; window.__bot.mode = ['idle', 'play']")
    await page.promo("level", level=6, seed=21)
    await asyncio.sleep(1.8)
    await page.start_recording("eaten")
    await asyncio.sleep(1.0)
    await page.js("window.__bot.mode = ['seek', 'play']")
    await asyncio.sleep(15)
    await page.stop_recording()


async def take_snake(page):
    """Змея: уровень 10 (красная), герой идёт прямо на неё, вторая половина дубля — обгладывает."""
    await open_game(page, 2)
    await page.js("window.__bot.revive = false; window.__bot.mode = ['play', 'play']")
    await page.promo("level", level=7, seed=33)
    await asyncio.sleep(1.8)
    await page.start_recording("snake")
    await asyncio.sleep(5.0)
    await page.js("window.__bot.mode = ['seek', 'play']")
    await asyncio.sleep(16)
    await page.stop_recording()


async def take_revive(page):
    """Игорь подрывает себя, Иван тратит жизнь и поднимает его."""
    await open_game(page, 2)
    await page.js("window.__bot.revive = false; window.__bot.mode = ['play', 'idle']")
    await page.promo("level", level=2, seed=8)
    await asyncio.sleep(1.8)
    await page.start_recording("revive")
    await asyncio.sleep(3.0)
    await page.js("window.__bot.mode = ['play', 'bomb_self']")
    await asyncio.sleep(0.2)
    await page.js("window.__bot.mode = ['play', 'idle']")
    await asyncio.sleep(5.5)
    await page.js("window.__bot.revive = true; window.__bot.mode = ['play', 'play']")
    await asyncio.sleep(6)
    await page.stop_recording()


async def take_bite(page):
    """Крупно «Хрум!»: второй герой стоит в углу и не мешает, первый идёт прямо на зубастика."""
    await open_game(page, 2)
    await page.js("window.__bot.revive = false; window.__bot.mode = ['idle', 'idle']")
    await page.promo("level", level=6, seed=21)
    await asyncio.sleep(1.8)
    await page.start_recording("bite")
    await asyncio.sleep(0.5)
    await page.js("window.__bot.mode = ['seek', 'idle']")
    await asyncio.sleep(10)
    await page.stop_recording()


async def take_bones(page):
    """Змея обгладывает героя до костей: уровень 10, красная змея, зубастиков на поле нет."""
    await open_game(page, 2)
    await page.js("window.__bot.revive = false; window.__bot.mode = ['idle', 'idle']")
    await page.promo("level", level=10, seed=52)
    await asyncio.sleep(1.8)
    await page.promo("only_snakes")
    await page.start_recording("bones")
    await asyncio.sleep(0.5)
    await page.js("window.__bot.mode = ['seek_snake', 'idle']")
    await asyncio.sleep(14)
    await page.stop_recording()


async def take_zoo(page):
    """Зубастики крупно: настоящие картинки врагов всех четырёх ступеней на чёрном поле."""
    await page.call("Page.navigate", url=f"http://127.0.0.1:{PORT}/")
    for _ in range(80):
        await asyncio.sleep(0.25)
        if await page.js("!!(window.__game && window.__game.scene.isActive('menu'))"):
            break
    await asyncio.sleep(0.5)
    await page.js("""(async () => {
      const { EnemyView } = await import('/js/enemyView.js');
      const s = window.__game.scene.getScene('menu');
      s.decor.forEach(({ view }) => view.image.setVisible(false));
      s.add.rectangle(509, 371, 1018, 742, 0x000000).setDepth(100);
      const views = [0, 1, 2, 3].map((tier) => {
        const view = new EnemyView(s, { tier });
        const col = tier % 2, row = tier >> 1;
        view.image.setPosition(255 + col * 508, 186 + row * 370).setDepth(101).setScale(view.image.scale * 6);
        return view;
      });
      s.events.on('update', (time) => {
        const clock = time / 1000, a = time / 700;
        views.forEach((view, i) => view.paint(clock + i * 1.3, [Math.cos(a + i), Math.sin(a * 0.7 + i) * 0.6], i >= 2));
      });
    })()""")
    await asyncio.sleep(0.5)
    await page.start_recording("zoo")
    await asyncio.sleep(5)
    await page.stop_recording()


async def take_records(page):
    """GAME OVER с таблицей рекордов: героям оставлена одна жизнь, оба идут на врагов."""
    await open_game(page, 2)
    await page.js("window.__bot.revive = false")
    await page.promo("level", level=10, seed=44, lives=1)
    await asyncio.sleep(1.8)
    await page.promo("score", index=0, value=18300)
    await page.promo("score", index=1, value=15250)
    await page.start_recording("records")
    await asyncio.sleep(0.5)
    await page.js("window.__bot.mode = ['seek', 'seek']")
    await asyncio.sleep(24)
    await page.stop_recording()


TAKES_LIST = {
    "play": take_play,
    "chain": take_chain,
    "eaten": take_eaten,
    "snake": take_snake,
    "revive": take_revive,
    "zoo": take_zoo,
    "records": take_records,
    "bite": take_bite,
    "bones": take_bones,
    "level10": lambda page: take_play(page, name="level10", level=10, seed=77, seconds=25),
}

FAKE_RECORDS = [
    {"names": "Иван и Игорь", "level": 15, "score": 48200, "date": "31.12.1991"},
    {"names": "Иван и Игорь", "level": 12, "score": 36750, "date": "09.05.1990"},
    {"names": "Иван", "level": 11, "score": 29100, "date": "01.06.1989"},
    {"names": "Игорь", "level": 9, "score": 21400, "date": "12.04.1988"},
]


async def main(names):
    TAKES.mkdir(parents=True, exist_ok=True)
    records_file = WORK / "records.json"
    records_file.write_text(json.dumps(FAKE_RECORDS, ensure_ascii=False), encoding="utf-8")
    server = subprocess.Popen([str(PYTHON), str(HERE / "capture_server.py"), str(PORT), str(records_file)], cwd=ROOT)
    profile = Path(r"C:\Temp\bombersys_promo_edge")
    edge = subprocess.Popen([EDGE, "--headless=new", f"--remote-debugging-port={DEBUG_PORT}", "--remote-allow-origins=*",
                             f"--user-data-dir={profile}", "--mute-audio", "--no-first-run", "--window-size=1018,742",
                             "--disable-background-timer-throttling", "--disable-renderer-backgrounding",
                             "--disable-backgrounding-occluded-windows", "--use-angle=d3d11", "--ignore-gpu-blocklist",
                             "--enable-gpu-rasterization", "about:blank"])
    try:
        for _ in range(60):
            try:
                urllib.request.urlopen(f"http://127.0.0.1:{PORT}/api/version", timeout=1)
                targets = json.load(urllib.request.urlopen(f"http://127.0.0.1:{DEBUG_PORT}/json", timeout=1))
                break
            except OSError:
                time.sleep(0.5)
        target = next(t for t in targets if t["type"] == "page")
        async with websockets.connect(target["webSocketDebuggerUrl"], max_size=None) as ws:
            page = Browser(ws)
            reader = asyncio.ensure_future(page.read())
            await page.call("Runtime.enable")
            await page.call("Page.enable")
            await page.call("Emulation.setDeviceMetricsOverride", width=1018, height=742, deviceScaleFactor=1, mobile=False)
            await page.call("Page.addScriptToEvaluateOnNewDocument", source=HOOK)
            for name in names:
                print(f"--- {name}  {time.strftime('%H:%M:%S')}", flush=True)
                await TAKES_LIST[name](page)
            for problem in page.problems:
                print("PROBLEM", problem, flush=True)
            reader.cancel()
    finally:
        edge.terminate()
        server.terminate()


if __name__ == "__main__":
    sys.stdout.reconfigure(encoding="utf-8")
    asyncio.run(main(sys.argv[1:] or list(TAKES_LIST)))
