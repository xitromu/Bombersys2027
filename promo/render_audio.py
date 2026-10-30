"""Музыка и звуки ролика: тот же синтезатор, что и в игре, только «играет» в память (OfflineAudioContext) в Edge.

Запуск из backend/.venv:  python promo/render_audio.py
Пишет promo/work/audio/song.wav и sfx_<имя>.wav (48 кГц, стерео).

Мелодия «Пятнадцать копеек» написана для ролика — своя, в звучании эталона игры («Холмы за околицей»: джига на 6/8,
дудочка высоко, под ней тянутся тоника и квинта, прыгающий бас, барабан-бойран). 6 знаков в такте — шесть восьмых.
Такт длится ровно 1,5 с (160 ударов в минуту), поэтому монтаж ролика идёт по тактам.
"""

from __future__ import annotations

import asyncio
import base64
import json
import subprocess
import sys
import time
import urllib.request
import wave
from pathlib import Path

import websockets

from capture import DEBUG_PORT, EDGE, PORT, PYTHON, WORK, Browser, HERE

OUT = WORK / "audio"
BPM = 160
RATE = 48000

LEAD = {"wave": "square25", "vol": 0.42, "vibrato": {"rate": 6, "cents": 18, "delay": 0.15}}
ARP = {"play": "arp", "wave": "square12", "vol": 0.1, "octave": 4}
BASS = {"wave": "triangle", "vol": 0.85, "gate": 0.8, "decay": 0, "sustain": 1}
DRONE = {"wave": "square50", "gate": 0.98, "attack": 0.08, "decay": 0, "sustain": 1, "release": 0.1}

INTRO, A, B, A2, END = 2, 8, 8, 8, 8   # такты: заход, запев, минорная часть, запев на тон выше, финал
REST = " | ".join(["."] * (INTRO + A + B))
LEAD_TEXT = """
  D4 G4 B4 D5 G5 B5 | D6 B5 G5 D6 E6 F#6 |
  G5 - B5 D6 - B5 | C6 - A5 F#5 - A5 | G5 - B5 D6 - G6 | F#6 E6 D6 C6 B5 A5 |
  G5 - B5 D6 - B5 | E6 - C6 A5 - C6 | B5 G5 B5 A5 F#5 A5 | G5 - - G5 D5 G5 |
  E5 - G5 B5 - E6 | D6 - B5 G5 - B5 | C6 - E6 G6 - E6 | D6 C6 B5 A5 G5 F#5 |
  E5 - G5 B5 - E6 | F#6 - D6 A5 - D6 | C6 - E6 G6 - E6 | G#5 B5 E6 G#6 - E6 |
  A5 - C#6 E6 - C#6 | D6 - B5 G#5 - B5 | A5 - C#6 E6 - A6 | G#6 F#6 E6 D6 C#6 B5 |
  A5 - C#6 E6 - C#6 | F#6 - D6 B5 - D6 | C#6 A5 C#6 B5 G#5 B5 | A5 - - A5 E5 A5 |
  A5 - E6 E6 - C#6 | D6 - F#6 F#6 - D6 | C#6 - E6 A6 - E6 | F#6 E6 D6 C#6 B5 A5 |
  F#5 - A5 D6 - F#6 | E6 - C#6 A5 - C#6 | B5 - D6 G#6 - E6 | A6 - - - - -"""
HARM_TEXT = REST + """ |
  E5 - A5 C#6 - A5 | B5 - G#5 E5 - G#5 | E5 - A5 C#6 - E6 | E6 D6 C#6 B5 A5 G#5 |
  E5 - A5 C#6 - A5 | D6 - A5 F#5 - A5 | A5 E5 A5 G#5 E5 G#5 | E5 - - E5 C#5 E5 |
  E5 - C#6 C#6 - A5 | A5 - D6 D6 - A5 | A5 - C#6 E6 - C#6 | D6 C#6 B5 A5 G#5 F#5 |
  D5 - F#5 A5 - D6 | C#6 - A5 E5 - A5 | G#5 - B5 E6 - B5 | E6 - - - - -"""
CHORDS = ("G D | G D | "
          "G | D7 | G | D | G | C | D | G | "
          "Em | G | C | D | Em | D | C | E7 | "
          "A | E7 | A | E | A | D | E | A | "
          "A | D | A | D E | D | A | E7 | A")
ROOTS = {"G": "G2 - D3 G3 - D3", "D": "D2 - A2 D3 - A2", "C": "C3 - G2 C3 - G2", "Em": "E2 - B2 E3 - B2",
         "E": "E2 - B2 E3 - B2", "A": "A2 - E3 A3 - E3"}
BASS_ORDER = ("G G  G D G D G C D G  Em G C D Em D C E  A E A E A D E A  A D A D D A E A").split()
BASS_TEXT = " | ".join(ROOTS[c] for c in BASS_ORDER)
# Держим тонику и квинту, как волынка: в запеве соль и ре, потом ми и си, потом ля и ми.
DRONE_LOW = " | ".join(["G3 - - - - -"] * (INTRO + A) + ["E3 - - - - -"] * B + ["A3 - - - - -"] * (A2 + END))
DRONE_HIGH = " | ".join(["D4 - - - - -"] * (INTRO + A) + ["B3 - - - - -"] * B + ["E4 - - - - -"] * (A2 + END))
GROOVE = ["k h h s h h", "k h h s h s"]
DRIVE = ["k h k s h h", "k h k s s s"]
DRUMS_TEXT = " | ".join(
    ["s s s s s s s s s s s s", "s s s s s s s s s s s s"]
    + [GROOVE[i % 2] for i in range(A + B)]
    + [DRIVE[i % 2] for i in range(A2 + END - 2)]
    + ["k h k s s s s s s s s s", "k . . . . ."])
CRASH = " | ".join(("c - - - - -" if bar in (INTRO, INTRO + A, INTRO + A + B, INTRO + A + B + A2,
                                              INTRO + A + B + A2 + END - 1) else ".")
                   for bar in range(INTRO + A + B + A2 + END))

SONG = {
    "title": "Промо: «Пятнадцать копеек»",
    "bpm": BPM,
    "parts": {
        "lead": {**LEAD, "text": LEAD_TEXT},
        "harm": {**LEAD, "wave": "square12", "vol": 0.2, "text": HARM_TEXT},
        "arp": {**ARP, "text": CHORDS},
        "bass": {**BASS, "text": "G2 - - D2 - - | G2 - D2 G2 D3 G3 | " + BASS_TEXT.split(" | ", 2)[2]},
        "droneLow": {**DRONE, "vol": 0.07, "text": DRONE_LOW},
        "droneHigh": {**DRONE, "vol": 0.045, "text": DRONE_HIGH},
        "drums": {"play": "drums", "vol": 0.4, "text": DRUMS_TEXT},
        "crash": {"play": "drums", "vol": 0.5, "text": CRASH},
    },
}

GAME_SFX = ["bomb", "explosion", "wall", "ghostNotice", "ghostLaugh", "crunch", "gnaw", "revive", "ghostKilled",
            "giftBurn", "doorOpen", "coin", "chest", "powerUp", "trap", "exit"]

# Звуки только для ролика, из тех же кирпичиков синтезатора.
EXTRA_JS = r"""({
  clink(s, o) {
    [2637, 3520, 2637, 3951].forEach((f, i) => s.tone('sfx', { wave: 'triangle', freq: f, at: o.at + i * 0.055, dur: 0.03, vol: 0.6, release: 0.2 }));
    s.noise('sfx', { filter: 'highpass', freq: 6000, at: o.at, dur: 0.01, vol: 0.35, release: 0.05 });
  },
  credit(s, o) {
    [659, 784, 988, 1319, 1568, 1976].forEach((f, i) => s.tone('sfx', { wave: 'square25', freq: f, at: o.at + i * 0.06, dur: 0.05, vol: 0.4, release: i === 5 ? 0.35 : 0.02 }));
  },
  slam(s, o) {
    s.tone('sfx', { wave: 'triangle', freq: 150, to: 38, at: o.at, dur: 0.1, vol: 1.0, release: 0.25 });
    s.noise('sfx', { filter: 'lowpass', freq: 2600, to: 300, rate: 0.5, at: o.at, dur: 0.05, vol: 0.7, release: 0.2 });
  },
  whoosh(s, o) {
    s.noise('sfx', { filter: 'bandpass', freq: 260, to: 5200, q: 1.1, at: o.at, dur: 2.8, attack: 2.4, vol: 0.55, release: 0.12 });
    s.tone('sfx', { wave: 'square12', freq: 180, to: 1500, at: o.at, dur: 2.8, attack: 2.4, vol: 0.1, release: 0.1 });
  },
  bigboom(s, o) {
    s.noise('sfx', { filter: 'lowpass', freq: 5200, to: 90, rate: 0.3, at: o.at, dur: 0.2, attack: 0.002, vol: 1.0, release: 1.6 });
    s.tone('sfx', { wave: 'triangle', freq: 95, to: 24, at: o.at, dur: 0.25, vol: 1.0, release: 0.8 });
    s.tone('sfx', { wave: 'square50', freq: 60, to: 24, at: o.at, dur: 0.1, vol: 0.3, release: 0.3 });
  },
  static(s, o) {
    s.noise('sfx', { filter: 'highpass', freq: 2500, at: o.at, dur: 0.35, attack: 0.01, vol: 0.28, release: 0.15 });
  },
  crtOff(s, o) {
    s.tone('sfx', { wave: 'sine', freq: 1500, to: 90, at: o.at, dur: 0.28, vol: 0.5, release: 0.05 });
    s.noise('sfx', { filter: 'highpass', freq: 3500, at: o.at, dur: 0.1, vol: 0.2, release: 0.15 });
  },
  crtOn(s, o) {
    s.tone('sfx', { wave: 'sine', freq: 90, to: 1100, at: o.at, dur: 0.22, vol: 0.32, release: 0.08 });
    s.noise('sfx', { filter: 'highpass', freq: 3000, at: o.at + 0.1, dur: 0.2, vol: 0.18, release: 0.2 });
  },
  tick(s, o) {
    s.tone('sfx', { wave: 'square25', freq: 1760, at: o.at, dur: 0.012, vol: 0.28, release: 0.015 });
  },
  fanfare(s, o) {
    [[880, 0], [1109, 0.1], [1319, 0.2], [1760, 0.3]].forEach(([f, t], i) =>
      s.tone('sfx', { wave: 'square50', freq: f, at: o.at + t, dur: 0.09, vol: 0.32, release: i === 3 ? 0.5 : 0.03 }));
  },
})"""

PAGE_HELPERS = r"""
window.__promoAudio = (async () => {
  const { Synth } = await import('/js/audio/synth.js');
  const { Sequencer } = await import('/js/audio/sequencer.js');
  const { SFX } = await import('/js/audio/sfx.js');
  const encode = (buffer) => {
    const n = buffer.length, out = new Int16Array(n * 2);
    const l = buffer.getChannelData(0), r = buffer.getChannelData(1);
    for (let i = 0; i < n; i++) {
      out[i * 2] = Math.max(-1, Math.min(1, l[i])) * 32767;
      out[i * 2 + 1] = Math.max(-1, Math.min(1, r[i])) * 32767;
    }
    let text = '';
    const bytes = new Uint8Array(out.buffer);
    for (let i = 0; i < bytes.length; i += 32768) text += String.fromCharCode.apply(null, bytes.subarray(i, i + 32768));
    return btoa(text);
  };
  const EXTRA = %EXTRA%;
  return {
    async song(song, seconds) {
      const ctx = new OfflineAudioContext(2, 48000 * seconds, 48000);
      const synth = new Synth(ctx);
      new Sequencer(synth, song).scheduleAll(0.02);
      return encode(await ctx.startRendering());
    },
    async sfx(name, seconds) {
      const ctx = new OfflineAudioContext(2, 48000 * seconds, 48000);
      const synth = new Synth(ctx);
      const options = { at: 0.01, pan: 0, pitch: 1, vol: 1 };
      (SFX[name] ?? { play: EXTRA[name] }).play(synth, options);
      return encode(await ctx.startRendering());
    },
  };
})();
"""


def save(path: Path, b64: str) -> None:
    with wave.open(str(path), "wb") as w:
        w.setnchannels(2)
        w.setsampwidth(2)
        w.setframerate(RATE)
        w.writeframes(base64.b64decode(b64))


async def main() -> None:
    OUT.mkdir(parents=True, exist_ok=True)
    records_file = WORK / "records.json"
    if not records_file.exists():
        records_file.write_text("[]", encoding="utf-8")
    server = subprocess.Popen([str(PYTHON), str(HERE / "capture_server.py"), str(PORT), str(records_file)])
    edge = subprocess.Popen([EDGE, "--headless=new", f"--remote-debugging-port={DEBUG_PORT}", "--remote-allow-origins=*",
                             r"--user-data-dir=C:\Temp\bombersys_promo_edge", "--mute-audio", "--no-first-run",
                             "about:blank"])
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
            await page.call("Page.navigate", url=f"http://127.0.0.1:{PORT}/api/version")
            await asyncio.sleep(0.8)
            await page.js(PAGE_HELPERS.replace("%EXTRA%", EXTRA_JS) + "; 0")
            seconds = (INTRO + A + B + A2 + END) * 1.5 + 4
            print(f"song: {seconds} s", flush=True)
            data = await page.js(f"window.__promoAudio.then((a) => a.song({json.dumps(SONG)}, {seconds}))")
            save(OUT / "song.wav", data)
            names = GAME_SFX + ["clink", "credit", "slam", "whoosh", "bigboom", "static", "crtOff", "crtOn", "tick", "fanfare"]
            for name in names:
                length = 4 if name in ("whoosh", "bigboom") else 2.5
                save(OUT / f"sfx_{name}.wav", await page.js(f"window.__promoAudio.then((a) => a.sfx('{name}', {length}))"))
                print("sfx", name, flush=True)
            for problem in page.problems:
                print("PROBLEM", problem, flush=True)
            reader.cancel()
    finally:
        edge.terminate()
        server.terminate()


if __name__ == "__main__":
    sys.stdout.reconfigure(encoding="utf-8")
    asyncio.run(main())
