// Звук игры целиком: эффекты, голоса, музыка и заставки. Один на всю игру (sound).
//
// Браузер не даёт играть звук, пока человек ничего не нажал, поэтому звук «просыпается»
// с первой клавишей или щелчком. Режим (всё / без музыки / тишина) и громкость запоминаются в браузере.

import { Synth } from './synth.js';
import { Sequencer } from './sequencer.js';
import { SFX } from './sfx.js';
import { JINGLES, SONGS } from './songs.js';

// Голоса — Kenney.nl, лицензия CC0 (sounds/voice/LICENSE.txt).
export const VOICES = {
  fighter_ready: 'Ведущий: «Ready!» — приготовиться',
  fighter_fight: 'Ведущий: «Fight!» — уровень начался',
  fighter_winner: 'Ведущий: «Winner!» — подорвал напарника',
  fighter_flawless_victory: 'Ведущий: «Flawless victory!» — подорвал напарника вплотную',
  fighter_multi_kill: 'Ведущий: «Multi kill!» — два и больше призраков одним взрывом',
  fighter_game_over: 'Ведущий: «Game over»',
  female_mission_completed: 'Диспетчер: «Mission completed» — уровень пройден',
  female_mission_failed: 'Диспетчер: «Mission failed» — уровень заново',
  female_objective_achieved: 'Диспетчер: «Objective achieved» — все призраки повержены',
  female_new_highscore: 'Диспетчер: «New highscore» — новый рекорд',
  female_wrong: 'Диспетчер: «Wrong» — дверь заперта',
  male_war_target_destroyed: 'Герой: «Target destroyed!» — убил призрака',
  male_power_up: 'Герой: «Power up!» — ещё одна бомба',
};

export const MODES = ['all', 'sfx', 'off'];
export const MODE_LABELS = { all: '🔊 Звук и музыка', sfx: '🔉 Без музыки', off: '🔇 Без звука' };
const STORAGE_KEY = 'bombersys.sound';
const VOLUME_KEY = 'bombersys.volume';
const DEFAULT_VOLUME = 50;         // в процентах; 50% — примерно вчетверо тише полной громкости
const FULL_GAIN = 0.8;
const MUSIC_DUCK = { normal: 1, voice: 0.55, pause: 0.3 };
const VOICE_QUEUE = 2;
const MUSIC_LEVEL = 0.22;       // музыка — фоном, чтобы не глушить эффекты и голоса

class Sound {
  constructor() {
    this.synth = null;
    this.voices = {};
    this.mode = MODES[0];
    this.queue = [];
    this.speaking = false;
    this.lastPlayed = {};
    this.song = null;
    this.songName = null;
    this.paused = false;
    this.volume = DEFAULT_VOLUME;
    try {
      const saved = localStorage.getItem(STORAGE_KEY);
      if (MODES.includes(saved)) this.mode = saved;
      const volume = Number(localStorage.getItem(VOLUME_KEY) ?? NaN);
      if (volume >= 0 && volume <= 100) this.volume = volume;
    } catch {
      // хранилище недоступно — будут режим и громкость по умолчанию
    }
  }

  init() {
    if (this.synth) return;
    try {
      this.synth = new Synth();
    } catch (error) {
      console.warn('Звук недоступен:', error);
      return;
    }
    this.applyMode();
    const wake = () => {
      if (this.synth.ctx.state !== 'running') this.synth.ctx.resume();
    };
    for (const type of ['keydown', 'pointerdown', 'touchstart']) window.addEventListener(type, wake, true);
    this.loadVoices();
  }

  async loadVoices() {
    await Promise.all(Object.keys(VOICES).map(async (name) => {
      try {
        const response = await fetch(`sounds/voice/${name}.ogg`);
        this.voices[name] = await this.synth.ctx.decodeAudioData(await response.arrayBuffer());
      } catch (error) {
        console.warn(`Голос ${name} не загрузился:`, error);
      }
    }));
  }

  // ------------------------------------------------------------ режим и громкость

  cycleMode() {
    this.mode = MODES[(MODES.indexOf(this.mode) + 1) % MODES.length];
    this.remember(STORAGE_KEY, this.mode);
    this.applyMode();
    return this.mode;
  }

  // Громкость шагами по 10%. Слух воспринимает громкость «логарифмически», поэтому
  // усиление растёт как квадрат: 50% ≈ вчетверо тише полной, 10% — едва слышно.
  changeVolume(delta) {
    this.volume = Math.max(0, Math.min(100, this.volume + delta));
    if (this.volume > 0 && this.mode === 'off') this.mode = 'all';  // прибавили громкость — значит, звук нужен
    this.remember(VOLUME_KEY, String(this.volume));
    this.remember(STORAGE_KEY, this.mode);
    this.applyMode();
    return this.volume;
  }

  remember(key, value) {
    try {
      localStorage.setItem(key, value);
    } catch {
      // не запомнилось — ничего страшного
    }
  }

  applyMode() {
    if (!this.synth) return;
    const gain = this.mode === 'off' ? 0 : FULL_GAIN * (this.volume / 100) ** 2;
    this.synth.master.gain.setTargetAtTime(gain, this.synth.now, 0.02);
    this.updateMusicLevel();
  }

  updateMusicLevel() {
    if (!this.synth) return;
    let level = this.mode === 'all' ? MUSIC_LEVEL : 0;
    if (this.paused) level *= MUSIC_DUCK.pause;
    else if (this.speaking) level *= MUSIC_DUCK.voice;
    this.synth.buses.music.gain.setTargetAtTime(level, this.synth.now, 0.05);
  }

  // ------------------------------------------------------------ эффекты

  // minGap — не чаще, чем раз в столько секунд (чтобы десяток взрывов подряд не слились в рёв)
  play(name, { pan = 0, pitch = 1, vol = 1, delay = 0, minGap = 0 } = {}) {
    if (!this.synth || this.mode === 'off') return;
    const now = this.synth.now;
    if (minGap && now - (this.lastPlayed[name] ?? -Infinity) < minGap) return;
    this.lastPlayed[name] = now;
    SFX[name].play(this.synth, { at: now + 0.01 + delay, pan, pitch, vol });
  }

  jingle(name, { overMusic = false } = {}) {
    if (!this.synth) return;
    if (overMusic) {
      new Sequencer(this.synth, JINGLES[name], { bus: 'sfx' }).start();
      return;
    }
    // заставка на месте музыки: следующая музыка или заставка её прервёт
    this.stopMusic();
    this.songName = `jingle:${name}`;
    this.song = new Sequencer(this.synth, JINGLES[name]).start();
  }

  // ------------------------------------------------------------ голоса: по одному, без наложений

  say(name, { rate = 1 } = {}) {
    if (!this.synth || this.mode === 'off' || !this.voices[name]) return;
    if (this.queue.length >= VOICE_QUEUE) this.queue.shift();  // устаревшее выкидываем
    this.queue.push({ name, rate });
    if (!this.speaking) this.nextVoice();
  }

  nextVoice() {
    const item = this.queue.shift();
    this.speaking = Boolean(item);
    this.updateMusicLevel();
    if (!item) return;
    const source = this.synth.ctx.createBufferSource();
    source.buffer = this.voices[item.name];
    source.playbackRate.value = item.rate;
    source.connect(this.synth.buses.voice);
    source.onended = () => {
      source.disconnect();
      this.nextVoice();
    };
    source.start();
  }

  // ------------------------------------------------------------ музыка

  music(name) {
    if (!this.synth || this.songName === name) return;
    this.stopMusic();
    this.songName = name;
    this.song = new Sequencer(this.synth, SONGS[name], { loop: true }).start();
  }

  stopMusic() {
    this.song?.stop();
    this.song = null;
    this.songName = null;
  }

  tempo(value) {
    this.song?.setTempo(value);
  }

  pause(on) {
    this.paused = on;
    this.updateMusicLevel();
  }
}

export const sound = new Sound();
