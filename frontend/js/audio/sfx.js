// Звуковые эффекты: каждый собран из тонов и шума синтезатора (synth.js).
// o.at — когда прозвучать, o.pan — панорама (−1 слева … +1 справа), o.pitch — во сколько раз выше.
// Заголовки (title) показываются на странице проверки звуков sounds.html.

const B = 'sfx';

export const SFX = {
  bomb: {
    title: 'Поставил бомбу — «тук»',
    play(s, o) {
      s.tone(B, { wave: 'triangle', freq: 190 * o.pitch, to: 70, at: o.at, dur: 0.05, vol: 0.9, release: 0.06, pan: o.pan });
      s.noise(B, { filter: 'lowpass', freq: 900, at: o.at, dur: 0.01, vol: 0.35, release: 0.03, pan: o.pan });
    },
  },

  explosion: {
    title: 'Взрыв бомбы',
    play(s, o) {
      const v = o.vol;
      // грубый «крупный» шум, который глохнет, и низкий удар под ним
      s.noise(B, { filter: 'lowpass', freq: 3200, to: 120, rate: 0.35, at: o.at, dur: 0.12, attack: 0.002,
        vol: 1.0 * v, release: 0.75, pan: o.pan });
      s.tone(B, { wave: 'triangle', freq: 110 * o.pitch, to: 28, at: o.at, dur: 0.12, vol: 0.9 * v, release: 0.35, pan: o.pan });
      s.tone(B, { wave: 'square50', freq: 70 * o.pitch, to: 30, at: o.at, dur: 0.06, vol: 0.25 * v, release: 0.15, pan: o.pan });
    },
  },

  wall: {
    title: 'Разрушилась стена — хруст',
    play(s, o) {
      s.noise(B, { filter: 'bandpass', freq: 900, q: 1.5, rate: 0.5, at: o.at + 0.05, dur: 0.04, vol: 0.8, release: 0.08, pan: o.pan });
      s.noise(B, { filter: 'bandpass', freq: 600, q: 1.5, rate: 0.4, at: o.at + 0.12, dur: 0.03, vol: 0.7, release: 0.1, pan: o.pan });
    },
  },

  ghostNotice: {
    title: 'Призрак почуял игрока — «у-у?»',
    play(s, o) {
      s.tone(B, { wave: 'sine', freq: 300 * o.pitch, to: 560 * o.pitch, at: o.at, dur: 0.35, attack: 0.08, vol: 0.45,
        release: 0.12, vibrato: { rate: 7, cents: 45, delay: 0.05 }, pan: o.pan });
      s.tone(B, { wave: 'triangle', freq: 600 * o.pitch, to: 1120 * o.pitch, at: o.at, dur: 0.35, attack: 0.08, vol: 0.12,
        release: 0.12, vibrato: { rate: 7, cents: 45, delay: 0.05 }, pan: o.pan });
    },
  },

  ghostLaugh: {
    title: 'Призрак поймал человека — злорадное «хи-хи-хи»',
    play(s, o) {
      const p = o.pitch;
      [0, 1, 2, 3, 4].forEach((i) => {
        const at = o.at + i * 0.12;
        const f = (880 - i * 45) * p;
        s.noise(B, { filter: 'highpass', freq: 3500, at, dur: 0.015, vol: 0.18, release: 0.02, pan: o.pan });  // «х»
        s.tone(B, { wave: 'square25', freq: f, to: f * 0.8, at: at + 0.015, dur: 0.05, vol: 0.4, release: 0.03,
          vibrato: { rate: 30, cents: 60, delay: 0 }, pan: o.pan });                                                // «и»
      });
    },
  },

  crunch: {
    title: 'Тварь откусила голову — «хрум!»',
    play(s, o) {
      // сухой треск, удар челюстей под ним и два затихающих «дожёвывания»
      s.noise(B, { filter: 'bandpass', freq: 1900, q: 2, rate: 0.5, at: o.at, dur: 0.03, vol: 1.0, release: 0.05, pan: o.pan });
      s.tone(B, { wave: 'triangle', freq: 170, to: 60, at: o.at, dur: 0.05, vol: 0.55, release: 0.06, pan: o.pan });
      s.noise(B, { filter: 'bandpass', freq: 1200, q: 1.5, rate: 0.4, at: o.at + 0.1, dur: 0.035, vol: 0.7, release: 0.07, pan: o.pan });
      s.noise(B, { filter: 'lowpass', freq: 800, rate: 0.3, at: o.at + 0.19, dur: 0.03, vol: 0.45, release: 0.1, pan: o.pan });
    },
  },

  gnaw: {
    title: 'Змея обгладывает кости — «хрум-хрум-хрум»',
    play(s, o) {
      [0, 1, 2, 3, 4, 5].forEach((i) => {
        const at = o.at + i * 0.1;
        s.noise(B, { filter: 'bandpass', freq: i % 2 ? 2100 : 1500, q: 2, rate: 0.5, at, dur: 0.025, vol: 0.75 - i * 0.06,
          release: 0.04, pan: o.pan });
        s.tone(B, { wave: 'triangle', freq: 150, to: 70, at, dur: 0.03, vol: 0.3, release: 0.04, pan: o.pan });
      });
    },
  },

  revive: {
    title: 'Напарник воскрес — светлый перелив вверх',
    play(s, o) {
      [392, 523, 659, 784, 1047, 1319].forEach((f, i) =>
        s.tone(B, { wave: 'triangle', freq: f, at: o.at + i * 0.07, dur: 0.08, vol: 0.4, release: 0.25, pan: o.pan }));
      s.tone(B, { wave: 'sine', freq: 523, to: 1047, at: o.at, dur: 0.5, attack: 0.15, vol: 0.18, release: 0.3,
        vibrato: { rate: 6, cents: 25, delay: 0.1 }, pan: o.pan });
      s.noise(B, { filter: 'highpass', freq: 6000, at: o.at + 0.4, dur: 0.05, attack: 0.02, vol: 0.12, release: 0.4, pan: o.pan });
    },
  },

  ghostKilled: {
    title: 'Призрак уничтожен — «пуф»',
    play(s, o) {
      s.tone(B, { wave: 'square12', freq: 1100 * o.pitch, to: 180, at: o.at, dur: 0.18, vol: 0.4, release: 0.08, pan: o.pan });
      s.noise(B, { filter: 'highpass', freq: 2500, to: 800, at: o.at + 0.05, dur: 0.1, vol: 0.3, release: 0.15, pan: o.pan });
    },
  },

  giftBurn: {
    title: 'Сгорел подарок — «дзынь-пшшш»',
    play(s, o) {
      s.tone(B, { wave: 'triangle', freq: 1568, at: o.at, dur: 0.05, vol: 0.5, release: 0.25, pan: o.pan });
      s.tone(B, { wave: 'sine', freq: 3136, at: o.at, dur: 0.03, vol: 0.2, release: 0.2, pan: o.pan });
      s.tone(B, { wave: 'triangle', freq: 1318, to: 660, at: o.at + 0.12, dur: 0.1, vol: 0.35, release: 0.2, pan: o.pan });
      s.noise(B, { filter: 'highpass', freq: 5000, to: 1500, at: o.at + 0.1, dur: 0.15, attack: 0.03, vol: 0.3,
        release: 0.35, pan: o.pan });
    },
  },

  doorBreak: {
    title: 'Сломалась (заперлась) дверь — лязг и щелчок замка',
    play(s, o) {
      s.noise(B, { filter: 'bandpass', freq: 2400, q: 9, at: o.at, dur: 0.05, vol: 0.9, release: 0.3, pan: o.pan });
      s.tone(B, { wave: 'square50', freq: 130, to: 95, at: o.at, dur: 0.08, vol: 0.3, release: 0.12, pan: o.pan });
      s.tone(B, { wave: 'square12', freq: 1760, at: o.at + 0.02, dur: 0.02, vol: 0.2, release: 0.2, pan: o.pan });
      s.noise(B, { filter: 'highpass', freq: 3000, at: o.at + 0.4, dur: 0.01, vol: 0.6, release: 0.02, pan: o.pan });
      s.noise(B, { filter: 'bandpass', freq: 1500, q: 4, at: o.at + 0.47, dur: 0.02, vol: 0.5, release: 0.04, pan: o.pan });
    },
  },

  doorClosed: {
    title: 'Ткнулся в запертую дверь — «бз-з»',
    play(s, o) {
      s.tone(B, { wave: 'square50', freq: 98, to: 92, at: o.at, dur: 0.22, vol: 0.4, release: 0.04, pan: o.pan });
    },
  },

  doorOpen: {
    title: 'Дверь открылась',
    play(s, o) {
      [523, 659, 784, 1047].forEach((f, i) =>
        s.tone(B, { wave: 'square25', freq: f, at: o.at + i * 0.07, dur: 0.06, vol: 0.3, release: 0.1, pan: o.pan }));
    },
  },

  coin: {
    title: 'Монеты и камни — «динь»',
    play(s, o) {
      s.tone(B, { wave: 'square25', freq: 988 * o.pitch, at: o.at, dur: 0.05, vol: 0.5, release: 0.01, pan: o.pan });
      s.tone(B, { wave: 'square25', freq: 1319 * o.pitch, at: o.at + 0.06, dur: 0.12, vol: 0.5, release: 0.18, pan: o.pan });
    },
  },

  chest: {
    title: 'Сундук — «динь-динь-динь»',
    play(s, o) {
      [988, 1319, 1568, 1976].forEach((f, i) =>
        s.tone(B, { wave: 'square25', freq: f, at: o.at + i * 0.06, dur: 0.05, vol: 0.45, release: i === 3 ? 0.25 : 0.02,
          pan: o.pan }));
    },
  },

  powerUp: {
    title: 'Ещё одна бомба — восходящее арпеджио',
    play(s, o) {
      [523, 659, 784, 1047, 1319, 1568].forEach((f, i) =>
        s.tone(B, { wave: 'square12', freq: f, at: o.at + i * 0.045, dur: 0.04, vol: 0.5, release: 0.03, pan: o.pan }));
    },
  },

  trap: {
    title: 'Наступил на череп — зловещий аккорд',
    play(s, o) {
      [110, 116.5, 155.6].forEach((f) =>
        s.tone(B, { wave: 'square50', freq: f, to: f * 0.85, at: o.at, dur: 0.5, vol: 0.18, release: 0.3,
          vibrato: { rate: 5, cents: 30, delay: 0.1 }, pan: o.pan }));
    },
  },

  exit: {
    title: 'Вошёл в дверь — «вжух» вверх',
    play(s, o) {
      s.tone(B, { wave: 'square25', freq: 300, to: 1400, at: o.at, dur: 0.3, vol: 0.45, release: 0.08, pan: o.pan });
    },
  },

  thiefGrab: {
    title: 'Воришка схватил бонус — писк «и-и!»',
    play(s, o) {
      const p = o.pitch;
      s.tone(B, { wave: 'square25', freq: 1400 * p, to: 2100 * p, at: o.at, dur: 0.09, vol: 0.4, release: 0.05, pan: o.pan });
      s.tone(B, { wave: 'square25', freq: 2100 * p, to: 1500 * p, at: o.at + 0.09, dur: 0.1, vol: 0.35, release: 0.08, pan: o.pan });
      s.noise(B, { filter: 'highpass', freq: 4000, at: o.at + 0.02, dur: 0.02, vol: 0.12, release: 0.04, pan: o.pan });
    },
  },

  moleDig: {
    title: 'Крот нырнул (вынырнул) — земляной шорох',
    play(s, o) {
      s.noise(B, { filter: 'lowpass', freq: 700, to: 250, rate: 0.4, at: o.at, dur: 0.16, attack: 0.01, vol: 0.8, release: 0.18, pan: o.pan });
      s.noise(B, { filter: 'bandpass', freq: 350, q: 1.2, rate: 0.3, at: o.at + 0.1, dur: 0.12, vol: 0.5, release: 0.2, pan: o.pan });
      s.tone(B, { wave: 'triangle', freq: 90 * o.pitch, to: 55, at: o.at, dur: 0.12, vol: 0.35, release: 0.15, pan: o.pan });
    },
  },

  moleEat: {
    title: 'Крот сожрал бонус — глоток «хряп»',
    play(s, o) {
      s.tone(B, { wave: 'square12', freq: 240 * o.pitch, to: 90, at: o.at, dur: 0.12, vol: 0.45, release: 0.1, pan: o.pan });
      s.noise(B, { filter: 'lowpass', freq: 1100, rate: 0.3, at: o.at + 0.08, dur: 0.1, vol: 0.5, release: 0.14, pan: o.pan });
    },
  },
};
