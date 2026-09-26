// Проигрыватель мелодий. Ноты записаны текстом, такты разделены «|».
// Такт (4 четверти) делится поровну между знаками в нём:
//   "C5 E5 G5 -"          — четыре четверти; «-» тянет предыдущую ноту, «.» — пауза;
//   "A4 - C5 - E5 - A5 G5" — восьмые.
// Партии бывают трёх видов (поле play):
//   notes — мелодия или бас: C5, F#4, Bb3 (нота + октава);
//   arp   — аккорды, сыгранные быстрым перебором нот, как на автоматах: C, Am, G7, Bb, F#m, Edim;
//   drums — удары: k, s, h, o, c (см. Synth.drum).
// Партия короче песни повторяется — удобно для барабанов из двух тактов.

const NOTE_NAMES = { C: 0, D: 2, E: 4, F: 5, G: 7, A: 9, B: 11 };
const CHORDS = {
  '': [0, 4, 7], m: [0, 3, 7], 7: [0, 4, 7, 10], m7: [0, 3, 7, 10], maj7: [0, 4, 7, 11],
  dim: [0, 3, 6], aug: [0, 4, 8], sus4: [0, 5, 7],
};
const ARP_STEP = 1 / 30;     // перебор аккорда: смена ноты 30 раз в секунду
const LOOKAHEAD = 0.2;       // на сколько секунд вперёд расписываем ноты
const TIMER_MS = 40;

export const noteFreq = (midi) => 440 * 2 ** ((midi - 69) / 12);

export function noteMidi(token) {
  const m = /^([A-G])([#b]?)(-?\d)$/.exec(token);
  if (!m) return null;
  const shift = m[2] === '#' ? 1 : m[2] === 'b' ? -1 : 0;
  return 12 * (Number(m[3]) + 1) + NOTE_NAMES[m[1]] + shift;
}

function chordMidis(token, octave) {
  const m = /^([A-G])([#b]?)(m7|maj7|m|7|dim|aug|sus4)?$/.exec(token);
  if (!m) return null;
  const root = noteMidi(`${m[1]}${m[2]}${octave}`);
  return CHORDS[m[3] ?? ''].map((i) => root + i);
}

// Текст партии → список событий {beat, len, value} (время — в долях-четвертях).
export function parsePart(name, part) {
  const bars = part.text.split('|').map((b) => b.trim()).filter(Boolean);
  const events = [];
  let last = null;
  bars.forEach((bar, b) => {
    const tokens = bar.split(/\s+/);
    const len = 4 / tokens.length;
    tokens.forEach((token, i) => {
      const beat = b * 4 + i * len;
      if (token === '-') {
        if (last) last.len += len;
        return;
      }
      if (token === '.') {
        last = null;
        return;
      }
      let value;
      if (part.play === 'drums') value = /^[ksohc]$/.test(token) ? token : null;
      else if (part.play === 'arp') value = chordMidis(token, part.octave ?? 4);
      else value = noteMidi(token);
      if (value === null) throw new Error(`партия ${name}, такт ${b + 1}: непонятный знак «${token}»`);
      last = { beat, len, value };
      events.push(last);
    });
  });
  return { events, beats: bars.length * 4 };
}

// Песня → общий отсортированный список событий и длина в долях.
export function compile(song) {
  const parts = Object.entries(song.parts).map(([name, part]) => ({ name, part, ...parsePart(name, part) }));
  const beats = Math.max(...parts.map((p) => p.beats));
  const events = [];
  for (const p of parts) {
    for (let offset = 0; offset < beats; offset += p.beats) {
      for (const e of p.events) {
        if (e.beat + offset < beats) events.push({ ...e, beat: e.beat + offset, part: p.part });
      }
    }
  }
  events.sort((a, b) => a.beat - b.beat);
  return { events, beats };
}

// Одно проигрывание песни. Ноты расписываются чуть вперёд по таймеру, поэтому темп
// можно менять на ходу (setTempo) — так музыка «нагнетает», когда остался последний призрак.
export class Sequencer {
  constructor(synth, song, { bus = 'music', loop = false, onEnd } = {}) {
    this.synth = synth;
    this.song = song;
    this.bus = bus;
    this.loop = loop;
    this.onEnd = onEnd;
    this.tempo = 1;
    ({ events: this.events, beats: this.beats } = compile(song));
    this.sources = new Set();
  }

  get secondsPerBeat() {
    return 60 / (this.song.bpm * this.tempo);
  }

  start(at = this.synth.now + 0.05) {
    this.index = 0;
    this.beat = 0;       // доля, до которой всё расписано…
    this.time = at;      // …и когда она прозвучит
    this.stopped = false;
    this.tick();
    this.timer = setInterval(() => this.tick(), TIMER_MS);
    return this;
  }

  setTempo(tempo) {
    this.tempo = tempo;
  }

  tick() {
    if (this.stopped) return;
    const now = this.synth.now;
    if (this.time < now - 0.1) this.time = now + 0.02;  // вкладка «спала» — не выпаливаем пропущенное разом
    while (!this.stopped) {
      if (this.index >= this.events.length) {
        const endTime = this.time + (this.beats - this.beat) * this.secondsPerBeat;
        if (this.loop) {
          this.index = 0;
          this.beat = 0;
          this.time = endTime;
          continue;
        }
        this.finish(endTime);
        return;
      }
      const e = this.events[this.index];
      const at = this.time + (e.beat - this.beat) * this.secondsPerBeat;
      if (at > now + LOOKAHEAD) return;
      this.playEvent(e, at);
      this.beat = e.beat;
      this.time = at;
      this.index++;
    }
  }

  // Для проверки без колонок: расписать всю песню один раз сразу (OfflineAudioContext).
  scheduleAll(at = 0) {
    for (const e of this.events) this.playEvent(e, at + e.beat * this.secondsPerBeat);
    return at + this.beats * this.secondsPerBeat;
  }

  playEvent(e, at) {
    const { part } = e;
    const dur = e.len * this.secondsPerBeat;
    const vol = part.vol ?? 0.5;
    let source;
    if (part.play === 'drums') {
      this.synth.drum(this.bus, e.value, at, vol);
      return;
    }
    if (part.play === 'arp') {
      const notes = e.value;
      const steps = [];
      for (let t = 0, i = 0; t < dur; t += ARP_STEP, i++) steps.push([t, noteFreq(notes[i % notes.length])]);
      source = this.synth.tone(this.bus, {
        wave: part.wave ?? 'square12', freq: noteFreq(notes[0]), steps, at, dur: dur * 0.95, vol, release: 0.02,
      });
    } else {
      source = this.synth.tone(this.bus, {
        wave: part.wave ?? 'square25', freq: noteFreq(e.value), at, dur: dur * (part.gate ?? 0.85), vol,
        attack: part.attack ?? 0.005, decay: part.decay ?? 0.08, sustain: part.sustain ?? 0.7,
        release: part.release ?? 0.04,
        vibrato: part.vibrato && dur > 0.25 ? part.vibrato : undefined,
      });
    }
    this.sources.add(source);
    source.addEventListener('ended', () => this.sources.delete(source));
  }

  finish(endTime) {
    this.stopped = true;
    clearInterval(this.timer);
    const wait = Math.max(0, (endTime - this.synth.now) * 1000);
    this.endTimer = setTimeout(() => this.onEnd?.(), wait);
  }

  stop() {
    this.stopped = true;
    clearInterval(this.timer);
    clearTimeout(this.endTimer);
    const now = this.synth.now;
    for (const source of this.sources) {
      try {
        source.stop(now + 0.03);
      } catch {
        // уже отзвучал
      }
    }
    this.sources.clear();
  }
}
