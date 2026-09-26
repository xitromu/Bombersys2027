// Музыка игры — своя, написана для BOMBERSYS в духе автоматов 80–90-х.
// Как читать запись — см. sequencer.js. Меняйте ноты смело: страница sounds.html
// сразу даст послушать, а ошибку в записи покажет с номером такта.

const LEAD = { wave: 'square25', vol: 0.42, vibrato: { rate: 6, cents: 18, delay: 0.15 } };
const ARP = { play: 'arp', wave: 'square12', vol: 0.16, octave: 4 };
const BASS = { wave: 'triangle', vol: 0.85, gate: 0.8, decay: 0, sustain: 1 };
const DRUMS = { play: 'drums', vol: 0.55 };

const DRONE = { wave: 'square50', gate: 0.98, attack: 0.08, decay: 0, sustain: 1, release: 0.1 };

export const SONGS = {
  // Меню: «Холмы за околицей» — джига на 6/8 в ре мажоре, в духе кельтских мелодий.
  // Шесть знаков в такте — шесть восьмых; под мелодией, как у волынки, тянутся ре и ля.
  menu: {
    title: 'Меню: «Холмы за околицей»',
    bpm: 165,
    parts: {
      lead: { ...LEAD, text: `
        A5 - F#5 D5 - F#5 | G5 - B5 D6 - B5 | A5 - F#5 A5 B5 A5 | E5 F#5 E5 C#5 - A4 |
        D5 - F#5 A5 - D6 | B5 - G5 D6 - B5 | C#6 - B5 A5 G5 E5 | F#5 E5 D5 D5 - - |
        B5 - F#5 B5 - D6 | D6 - B5 G5 - B5 | A5 - F#5 D5 E5 F#5 | E5 - A4 C#5 - E5 |
        F#5 - D5 B4 - D5 | G5 - B5 D6 - E6 | E6 - D6 C#6 - A5 | D6 - A5 D6 - -` },
      arp: { ...ARP, vol: 0.1, text: 'D | G | D | A | D | G | A | D | Bm | G | D | A | Bm | G | A | D' },
      bass: { ...BASS, text: `
        D2 - A2 D3 - A2 | G2 - D3 G3 - D3 | D2 - A2 D3 - A2 | A2 - E3 A3 - E3 |
        D2 - A2 D3 - A2 | G2 - D3 G3 - D3 | A2 - E3 A3 - E3 | D2 - A2 D3 - - |
        B2 - F#3 B3 - F#3 | G2 - D3 G3 - D3 | D2 - A2 D3 - A2 | A2 - E3 A3 - E3 |
        B2 - F#3 B3 - F#3 | G2 - D3 G3 - D3 | A2 - E3 A3 - E3 | D2 - A2 D3 - -` },
      droneD: { ...DRONE, vol: 0.07, text: 'D3 - - - - - | - - - - - -' },
      droneA: { ...DRONE, vol: 0.045, text: 'A3 - - - - - | - - - - - -' },
      drums: { ...DRUMS, vol: 0.4, text: 'k h h s h h | k h h s h s' },   // как ирландский бойран
    },
  },

  // Уровень, вариант А: «Бомбы на марше», ля минор.
  levelA: {
    title: 'Уровень: «Бомбы на марше»',
    bpm: 150,
    parts: {
      lead: { ...LEAD, text: `
        A4 - C5 - E5 - A5 G5 | F5 - E5 - C5 - A4 C5 | D5 - B4 - G4 - B4 D5 | E5 - A4 - E5 D5 C5 B4 |
        A4 - C5 - E5 - A5 B5 | C6 - A5 - F5 - A5 C6 | B5 - G5 - D5 - G5 B5 | G#5 - - - E5 - . . |
        A5 - - A5 G5 - F5 - | G5 - - G5 F5 - E5 - | E5 - G5 - B5 - G5 E5 | A5 - - - E5 - C5 - |
        A5 - - A5 B5 - C6 - | D6 - - D6 C6 - B5 - | B5 - G#5 - E5 - G#5 B5 | E6 - - - . . . .` },
      arp: { ...ARP, text: 'Am | F | G | Am | Am | F | G | E | F | G | Em | Am | F | G | E | E' },
      bass: { ...BASS, text: `
        A2 A3 A2 A3 A2 A3 A2 A3 | F2 F3 F2 F3 F2 F3 F2 F3 | G2 G3 G2 G3 G2 G3 G2 G3 | A2 A3 A2 A3 A2 A3 G2 G3 |
        A2 A3 A2 A3 A2 A3 A2 A3 | F2 F3 F2 F3 F2 F3 F2 F3 | G2 G3 G2 G3 G2 G3 G2 G3 | E2 E3 E2 E3 E2 E3 G#2 B2 |
        F2 F3 F2 F3 F2 F3 F2 F3 | G2 G3 G2 G3 G2 G3 G2 G3 | E2 E3 E2 E3 E2 E3 E2 E3 | A2 A3 A2 A3 A2 A3 A2 A3 |
        F2 F3 F2 F3 F2 F3 F2 F3 | G2 G3 G2 G3 G2 G3 G2 G3 | E2 E3 E2 E3 E2 E3 E2 E3 | E2 E3 E2 E3 G#2 G#3 B2 B3` },
      drums: { ...DRUMS, text: `
        k h s h k k s h | k h s h k k s h | k h s h k k s h | k h s h k k s h |
        k h s h k k s h | k h s h k k s h | k h s h k k s h | k . s . s s s s` },
    },
  },

  // Уровень, вариант Б: «Прогулка призраков», ре минор, с «жутковатыми» полутонами.
  levelB: {
    title: 'Уровень: «Прогулка призраков»',
    bpm: 138,
    parts: {
      lead: { ...LEAD, text: `
        D5 - F5 - A5 - G#5 A5 | D6 - A5 - F5 - D5 - | Bb4 - D5 - F5 - Bb5 A5 | A5 - - - C#5 - E5 - |
        D5 F5 A5 D6 C#6 D6 A5 F5 | E5 F5 G5 A5 - - . . | Bb5 - A5 - G5 - F5 - | E5 - C#5 - A4 - . . |
        G5 - Bb5 - D6 - Bb5 G5 | A5 - F5 - D5 - F5 A5 | Bb5 - F5 - D5 - F5 Bb5 | C#6 - A5 - E5 - C#5 E5 |
        D6 - - C6 Bb5 - A5 - | A5 - - G5 F5 - E5 - | E5 - G5 - Bb5 - A5 G5 | A5 - - - . . . .` },
      arp: { ...ARP, text: 'Dm | Dm | Bb | A | Dm | Dm | Gm | A7 | Gm | Dm | Bb | A | Gm | Dm | A7 | A7' },
      bass: { ...BASS, text: `
        D3 D3 A2 D3 D3 D3 A2 D3 | D3 D3 A2 D3 D3 C3 A2 F2 | Bb2 Bb2 F2 Bb2 Bb2 Bb2 F2 Bb2 | A2 A2 E2 A2 A2 A2 C#3 E3 |
        D3 D3 A2 D3 D3 D3 A2 D3 | D3 D3 A2 D3 D3 C3 A2 F2 | G2 G2 D2 G2 G2 G2 D2 G2 | A2 A2 E2 A2 A2 G2 E2 C#2 |
        G2 G2 D2 G2 G2 G2 D2 G2 | D3 D3 A2 D3 D3 D3 A2 D3 | Bb2 Bb2 F2 Bb2 Bb2 Bb2 F2 Bb2 | A2 A2 E2 A2 A2 A2 C#3 E3 |
        G2 G2 D2 G2 G2 G2 D2 G2 | D3 D3 A2 D3 D3 C3 A2 F2 | A2 A2 E2 A2 A2 G2 E2 C#2 | A2 A2 E2 A2 A2 A2 A2 A2` },
      drums: { ...DRUMS, text: 'k . h k s . h . | k . h k s . h h' },
    },
  },
};

// Короткие заставки — играют один раз.
export const JINGLES = {
  levelStart: {
    title: 'Начало уровня',
    bpm: 170,
    parts: {
      lead: { ...LEAD, text: 'C5 . E5 . G5 . C6 - - - G5 . C6 - - -' },
      arp: { ...ARP, text: 'C' },
      bass: { ...BASS, text: 'C3 . C3 . C3 . C3 - - - G2 . C3 - - -' },
      drums: { ...DRUMS, text: 'k . . . s . . . k . s . s s s s' },
    },
  },
  levelClear: {
    title: 'Уровень пройден',
    bpm: 160,
    parts: {
      lead: { ...LEAD, text: 'G5 . C6 . E6 . D6 . C6 . D6 . E6 - - -' },
      arp: { ...ARP, text: 'C F G C' },
      bass: { ...BASS, text: 'C3 C4 F2 F3 G2 G3 C3 -' },
      drums: { ...DRUMS, text: 'k s k s k s c .' },
    },
  },
  levelFail: {
    title: 'Попробуем ещё раз',
    bpm: 140,
    parts: {
      lead: { ...LEAD, wave: 'square50', text: 'E5 - D#5 - D5 - C#5 - - - - - . . . .' },
      bass: { ...BASS, text: 'A2 - G#2 - G2 - F#2 - - - - - . . . .' },
    },
  },
  gameOver: {
    title: 'GAME OVER',
    bpm: 110,
    parts: {
      lead: { ...LEAD, text: 'C5 - G4 - Ab4 - F4 - | Eb4 - C4 - B3 - D4 - | C4 - - - - - . .' },
      arp: { ...ARP, octave: 3, text: 'Cm Fm | Ab G | Cm' },
      bass: { ...BASS, text: 'C3 - - - F2 - - - | Ab2 - - - G2 - - - | C2 - - - - - . .' },
      drums: { ...DRUMS, text: 'k . . . k . . . | k . . . k . k . | k . . . . . . .' },
    },
  },
  // эти две звучат поверх музыки
  oneUp: {
    title: '+1 жизнь',
    bpm: 180,
    parts: {
      lead: { ...LEAD, vol: 0.5, text: 'G5 C6 E6 G6 C7 - E6 G6 C7 - - - . . . .' },
    },
  },
  victory: {
    title: 'Победа над напарником',
    bpm: 170,
    parts: {
      lead: { ...LEAD, vol: 0.5, text: 'G4 . C5 . E5 . G5 - - . E5 . G5 - C6 -' },
      arp: { ...ARP, vol: 0.2, text: 'C' },
    },
  },
};
