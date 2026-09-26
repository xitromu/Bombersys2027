// Страница sounds.html: послушать каждый звук отдельно и в игровых ситуациях.
// sounds.html?check — самопроверка без колонок: всё «проигрывается» в память (OfflineAudioContext),
// на странице — длительность, пиковая и средняя громкость каждого звука или ошибка.

import { Synth } from './synth.js';
import { Sequencer } from './sequencer.js';
import { SFX } from './sfx.js';
import { JINGLES, SONGS } from './songs.js';
import { VOICES, sound } from './sound.js';
import { GameAudio } from './gameAudio.js';

const $ = (html) => {
  const t = document.createElement('template');
  t.innerHTML = html.trim();
  return t.content.firstChild;
};

function section(title, hint) {
  const box = $(`<section><h2>${title}</h2>${hint ? `<p class="hint">${hint}</p>` : ''}<div class="grid"></div></section>`);
  document.getElementById('app').append(box);
  return box.querySelector('.grid');
}

function button(grid, label, note, onClick) {
  const b = $(`<button type="button"><b></b><span></span></button>`);
  b.querySelector('b').textContent = label;
  b.querySelector('span').textContent = note ?? '';
  b.addEventListener('click', () => onClick(b));
  grid.append(b);
  return b;
}

// Выдуманное состояние игры — чтобы прогнать настоящую озвучку (gameAudio.js) без сервера.
const enemy = (id, x, chasing = false, tier = 0) => ({ id, x, y: 5, tier, chasing });
const hero = (index, x) => ({ index, x, y: 5, lives: 3 });
const state = (events, extra = {}) => ({
  phase: 'playing', level: 1, events, players: [hero(0, 2), hero(1, 12)], enemies: [enemy(1, 7)], ...extra,
});

const SCENES = [
  ['Цепочка из 5 бомб', 'взрывы с шагом 0,1 с', (a) => [0, 1, 2, 3, 4].forEach((i) => setTimeout(() =>
    a.update(state([{ type: 'explosion', x: 3 + i * 2, y: 5 }, { type: 'wall_destroyed', x: 4 + i * 2, y: 5 }])), i * 100))],
  ['Призрак почуял Ивана', 'слева', (a) => {
    a.update(state([], { enemies: [enemy(1, 2, false)] }));
    a.update(state([], { enemies: [enemy(1, 2, true)] }));
  }],
  ['Три призрака поймали героя', 'злорадный хор', (a) =>
    a.update(state([{ type: 'player_died', player: 0, kind: 'normal', cause: 'enemy', killer: null }],
      { enemies: [enemy(1, 3), enemy(2, 7), enemy(3, 11)] }))],
  ['Наступил на череп', 'ловушка', (a) =>
    a.update(state([{ type: 'player_died', player: 0, kind: 'normal', cause: 'trap', killer: null }]))],
  ['Иван убил призрака', '«пуф» и возглас', (a) =>
    a.update(state([{ type: 'enemy_killed', id: 1, x: 7, y: 5, tier: 0, player: 0, score: 100 }], { enemies: [enemy(2, 3)] }))],
  ['Колян убил двух призраков разом', 'Multi kill', (a) =>
    a.update(state([{ type: 'enemy_killed', id: 1, x: 7, y: 5, tier: 1, player: 1, score: 200 },
      { type: 'enemy_killed', id: 2, x: 8, y: 5, tier: 2, player: 1, score: 400 }], { enemies: [enemy(3, 3)] }))],
  ['Иван подорвал Коляна', 'фанфара и Winner', (a) =>
    a.update(state([{ type: 'player_died', player: 1, kind: 'normal', cause: 'bomb', killer: 0 }]))],
  ['Колян подорвал Ивана вплотную', 'Flawless victory', (a) =>
    a.update(state([{ type: 'player_died', player: 0, kind: 'super', cause: 'bomb', killer: 1 }]))],
  ['Сгорел подарок и заперлась дверь', '', (a) => {
    a.update(state([{ type: 'item_destroyed', kind: 'chest', x: 4, y: 5 }]));
    setTimeout(() => a.update(state([{ type: 'door_locked', x: 10, y: 5 }])), 900);
  }],
  ['Колян взял бомбу', 'голос Коляна ниже', (a) =>
    a.update(state([{ type: 'item_taken', player: 1, kind: 'bomb', x: 12, y: 5 }]))],
  ['Последний призрак убит, дверь открыта', '', (a) =>
    a.update(state([{ type: 'enemy_killed', id: 1, x: 7, y: 5, tier: 0, player: 0, score: 100 },
      { type: 'all_enemies_killed', door_unlocked: true, x: 10, y: 5 }], { enemies: [] }))],
];

function buildPage() {
  sound.init();
  let playing = null;
  const stopAll = () => {
    sound.stopMusic();
    playing?.classList.remove('on');
    playing = null;
  };

  const music = section('Музыка', 'Щелчок — играть по кругу, ещё щелчок — стоп.');
  for (const [name, song] of Object.entries(SONGS)) {
    button(music, song.title, `${song.bpm} ударов в минуту`, (b) => {
      const again = playing === b;
      stopAll();
      if (again) return;
      sound.music(name);
      playing = b;
      b.classList.add('on');
    });
  }
  button(music, 'Нагнетание ×1,2', 'так музыка ускоряется, когда остался последний призрак', (b) => {
    b.classList.toggle('on');
    sound.tempo(b.classList.contains('on') ? 1.2 : 1);
  });

  const jingles = section('Заставки', 'Короткие, звучат один раз.');
  for (const [name, jingle] of Object.entries(JINGLES)) {
    button(jingles, jingle.title, '', () => {
      stopAll();
      sound.jingle(name);
    });
  }

  const effects = section('Эффекты');
  for (const [name, fx] of Object.entries(SFX)) button(effects, fx.title, name, () => sound.play(name));

  const voices = section('Голоса', 'Готовые записи Kenney.nl (свободная лицензия CC0).');
  for (const [name, title] of Object.entries(VOICES)) button(voices, title, name, () => sound.say(name));

  const scenes = section('Игровые ситуации', 'Настоящая озвучка игры на выдуманных событиях — так это прозвучит в партии.');
  for (const [title, note, run] of SCENES) button(scenes, title, note, () => run(new GameAudio()));
}

// ------------------------------------------------------------ самопроверка

async function measure(label, schedule) {
  const rate = 22050;
  const ctx = new OfflineAudioContext(2, rate * 30, rate);
  const synth = new Synth(ctx);
  synth.master.gain.value = 0.8;
  synth.buses.music.gain.value = 0.22;
  const end = Math.min(30, schedule(synth) + 0.5);
  const data = (await ctx.startRendering()).getChannelData(0).subarray(0, Math.ceil(end * rate));
  let peak = 0;
  let sum = 0;
  for (const v of data) {
    peak = Math.max(peak, Math.abs(v));
    sum += v * v;
  }
  if (!Number.isFinite(peak)) throw new Error('в звуке «не число»');
  const db = (v) => (v > 0 ? (20 * Math.log10(v)).toFixed(1) : '-inf');
  return `${label.padEnd(22)} ${end.toFixed(2).padStart(6)} с   пик ${db(peak).padStart(6)} дБ   средн. ${db(Math.sqrt(sum / data.length)).padStart(6)} дБ`;
}

async function check() {
  const report = document.getElementById('report');
  const lines = [];
  let errors = 0;
  const run = async (label, schedule) => {
    try {
      lines.push(await measure(label, schedule));
    } catch (error) {
      errors++;
      lines.push(`${label}: ОШИБКА ${error.message}`);
    }
  };
  for (const [name, song] of Object.entries({ ...SONGS, ...JINGLES })) {
    await run(name, (synth) => new Sequencer(synth, song).scheduleAll(0.05));
  }
  for (const [name, fx] of Object.entries(SFX)) {
    await run(name, (synth) => {
      fx.play(synth, { at: 0.05, pan: 0, pitch: 1, vol: 1 });
      return 1.5;
    });
  }
  for (const name of Object.keys(VOICES)) {
    const ok = (await fetch(`sounds/voice/${name}.ogg`)).ok;
    if (!ok) errors++;
    lines.push(`${name.padEnd(28)} ${ok ? 'файл есть' : 'ФАЙЛА НЕТ'}`);
  }
  report.textContent = `${lines.join('\n')}\nИТОГ: ${errors ? `ошибок ${errors}` : 'ошибок нет'}`;
  document.title = errors ? 'CHECK-FAIL' : 'CHECK-OK';
}

window.addEventListener('error', (e) => {
  document.getElementById('report').textContent += `\nОШИБКА: ${e.message}`;
  document.title = 'CHECK-FAIL';
});

if (new URLSearchParams(location.search).has('check')) check();
else buildPage();
