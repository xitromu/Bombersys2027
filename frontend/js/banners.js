// Надписи поверх поля в оформлении «блиндаж»: доски на гвоздях, буквы набиты краской по трафарету.
// Начало уровня — доски «УРОВЕНЬ N» и «ПРИГОТОВЬТЕСЬ» въезжают с двух сторон и уезжают обратно;
// пауза — поле притушено, доски «ПАУЗА» и «P — продолжить». Всё рисуется на холсте, готовых картинок нет.

import { DETAIL, canvasTexture } from './canvasTexture.js';
import { DEPTH, FIELD_SIZE, FIELD_X, FIELD_Y, FONT } from './layout.js';
import { INK } from './bunker.js';

const PAINT = '#f3e2b0';             // краска букв
const PAD = [3, 3, 9, 11];           // поля холста вокруг доски: слева, сверху, справа и снизу (там тень)
const MID = [FIELD_X + FIELD_SIZE / 2, FIELD_Y + FIELD_SIZE / 2 - 20];   // вокруг этой точки поля стоят доски
const AWAY = 620;                    // на столько точек доска уезжает за край поля
const IN = 280, OUT = 220;           // въезжает и уезжает за столько миллисекунд
const DIM = 0.5;                     // насколько поле притушено на паузе

// Доски: [ширина, высота, сдвиг от MID по x и y, наклон, шрифт, обводка букв].
const BOARDS = {
  level: [300, 62, 0, -47, -0.02, 'bold 38px', 5],
  ready: [470, 78, 0, 33, 0.015, 'bold 48px', 6],
  pause: [340, 96, 0, -14, -0.02, 'bold 72px', 7],
  hint: [260, 44, 0, 66, 0.02, 'bold 22px', 4],
};

const rnd = (i, k = 0) => {
  const v = Math.sin(i * 127.1 + k * 311.7) * 43758.5453;
  return v - Math.floor(v);
};

// Доска w × h с надписью text: тень, волокна, два гвоздя. seed — у каждой доски свой рисунок дерева.
function board(g, w, h, text, font, outline, seed) {
  const [x, y] = PAD;
  g.fillStyle = 'rgba(0, 0, 0, 0.45)';
  g.fillRect(x + 5, y + 7, w, h);
  const tone = 0.9 + 0.25 * rnd(seed);
  const paint = g.createLinearGradient(0, y, 0, y + h);
  paint.addColorStop(0, `rgb(${Math.round(112 * tone)}, ${Math.round(72 * tone)}, ${Math.round(38 * tone)})`);
  paint.addColorStop(1, `rgb(${Math.round(76 * tone)}, ${Math.round(47 * tone)}, ${Math.round(23 * tone)})`);
  g.fillStyle = paint;
  g.fillRect(x, y, w, h);
  g.strokeStyle = 'rgba(20, 10, 4, 0.35)';
  g.lineWidth = 1;
  for (let k = 0; k < 6; k++) {                               // волокна
    const gy = y + h * rnd(seed * 9 + k, 2);
    g.beginPath();
    g.moveTo(x, gy);
    for (let px = 0; px <= w; px += 40) g.lineTo(x + px, gy + 3 * Math.sin(px * 0.02 + k + seed));
    g.stroke();
  }
  g.strokeStyle = INK;
  g.lineWidth = 2;
  g.strokeRect(x, y, w, h);
  g.fillStyle = '#1c120a';                                    // шляпки гвоздей
  for (const nx of [x + 14, x + w - 14]) {
    g.beginPath();
    g.arc(nx, y + h / 2, 3.2, 0, Math.PI * 2);
    g.fill();
  }
  g.font = `${font} ${FONT}`;
  g.textAlign = 'center';
  g.textBaseline = 'middle';
  g.lineJoin = 'round';
  g.lineWidth = outline;
  g.strokeStyle = INK;
  g.strokeText(text, x + w / 2, y + h / 2 + 1);
  g.fillStyle = PAINT;
  g.fillText(text, x + w / 2, y + h / 2 + 1);
}

export class Banners {
  constructor(scene) {
    this.scene = scene;
    this.phase = null;
    // доски не выезжают за поле на панель: видны только в его пределах
    this.mask = scene.make.graphics().fillRect(FIELD_X, FIELD_Y, FIELD_SIZE, FIELD_SIZE).createGeometryMask();
    this.dim = scene.add.rectangle(FIELD_X, FIELD_Y, FIELD_SIZE, FIELD_SIZE, 0x080503, DIM)
      .setOrigin(0).setDepth(DEPTH.overlay - 1).setVisible(false);
    this.level = this.add('level', '', 1);                    // надпись появится вместе с номером уровня
    this.ready = this.add('ready', 'ПРИГОТОВЬТЕСЬ', 2);
    this.pause = [this.add('pause', 'ПАУЗА', 3), this.add('hint', 'P — продолжить', 4)];
  }

  // Картинка доски kind с надписью text; держим её за середину доски.
  add(kind, text, seed) {
    const [w, h, dx, dy, tilt] = BOARDS[kind];
    const image = this.scene.add.image(MID[0] + dx, MID[1] + dy, this.texture(kind, text, seed))
      .setOrigin((PAD[0] + w / 2) / (w + PAD[0] + PAD[2]), (PAD[1] + h / 2) / (h + PAD[1] + PAD[3]))
      .setScale(1 / DETAIL).setRotation(tilt).setDepth(DEPTH.overlay).setMask(this.mask).setVisible(false);
    image.home = MID[0] + dx;
    return image;
  }

  texture(kind, text, seed) {
    const [w, h, , , , font, outline] = BOARDS[kind];
    return canvasTexture(this.scene, `banner_${kind}_${text}`, w + PAD[0] + PAD[2], h + PAD[1] + PAD[3],
      (g) => board(g, w, h, text, font, outline, seed));
  }

  // Доска въезжает сбоку (side: −1 слева, 1 справа) или уезжает туда же.
  slide(image, side, show) {
    this.scene.tweens.killTweensOf(image);
    const away = image.home + side * AWAY;
    if (show) image.setX(away).setVisible(true);
    this.scene.tweens.add({
      targets: image, x: show ? image.home : away, duration: show ? IN : OUT,
      ease: show ? 'Cubic.easeOut' : 'Cubic.easeIn',
      onComplete: () => image.setVisible(show),
    });
  }

  // Вызывается с каждым состоянием от сервера: phase — этап партии, level — номер уровня.
  update(phase, level) {
    if (phase === this.phase) return;
    const was = this.phase;
    this.phase = phase;
    if (phase === 'ready') {
      this.level.setTexture(this.texture('level', `УРОВЕНЬ ${level}`, 1));
      this.slide(this.level, -1, true);
      this.slide(this.ready, 1, true);
    } else if (was === 'ready') {
      this.slide(this.level, -1, false);
      this.slide(this.ready, 1, false);
    }
    const paused = phase === 'paused';
    this.dim.setVisible(paused);
    for (const image of this.pause) image.setVisible(paused);
  }
}
