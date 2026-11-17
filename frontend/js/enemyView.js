// Тварь на экране — «зубастик»: круглый живоглот на коротких лапах, почти весь — пасть. Идёт — перебирает
// лапами (по пройденному пути, как герой), глаза следят за тем, куда идёт; заметил героя — глаза краснеют
// и он лязгает зубами. Ступени — зелёный, оранжевый, красный, фиолетовый: у старших больше зубов, брови,
// гребень, рога. Рисуется на своём холсте каждый кадр, готовых картинок нет.

import { DETAIL } from './canvasTexture.js';
import { CELL, actorDepth, cellCenterX, cellCenterY } from './layout.js';

const INK = '#120d0a';
const BONE = ['#f6efd8', '#b9a877'];
const IRON = ['#c3c6d0', '#555862'];
const SIZE = 64;                     // сторона холста в точках экрана: тварь с рогами и тенью и поля вокруг
const STRIDE = 9;                    // столько точек пути — один взмах лапы
// Цвет ступени — три тона: свет, середина, тень.
const TONES = [
  ['#b6f59a', '#3fae45', '#134f24'], ['#ffd98a', '#f08a1c', '#8a3c06'],
  ['#ffa590', '#d92c22', '#6e0f10'], ['#dcc0ff', '#8a4fe0', '#3a1474'],
];

// ------------------------------------------------------------ кисти

const oval = (g, x, y, rx, ry = rx, turn = 0) => {
  g.beginPath();
  g.ellipse(x, y, rx, ry, turn, 0, Math.PI * 2);
};
const poly = (g, points) => {
  g.beginPath();
  points.forEach(([x, y]) => g.lineTo(x, y));
  g.closePath();
};
const fill = (g, color) => {
  g.fillStyle = color;
  g.fill();
};
const stroke = (g, width = 1.5) => {
  g.lineWidth = width;
  g.lineJoin = 'round';
  g.lineCap = 'round';
  g.strokeStyle = INK;
  g.stroke();
};
// Объём: свет слева сверху, тень справа снизу.
function volume(g, [light, mid, dark]) {
  const paint = g.createRadialGradient(-6, -12, 1.5, 0, 0, 27);
  paint.addColorStop(0, light);
  paint.addColorStop(0.5, mid);
  paint.addColorStop(1, dark);
  fill(g, paint);
}
function pair(g, [light, dark], width = 1.2) {
  const paint = g.createLinearGradient(-6, -10, 6, 10);
  paint.addColorStop(0, light);
  paint.addColorStop(1, dark);
  fill(g, paint);
  stroke(g, width);
}

// Глаз: зрачок следит за look; заметил героя — радужка красная.
function eye(g, x, y, look, alert) {
  const rx = 3.9, ry = 4.3;
  oval(g, x, y, rx, ry);
  fill(g, '#fffdf4');
  stroke(g, 1);
  const px = x + look[0] * rx * 0.42, py = y + look[1] * ry * 0.42;
  if (alert) {
    oval(g, px, py, rx * 0.62);
    fill(g, '#d01818');
  }
  oval(g, px, py, rx * (alert ? 0.34 : 0.5));
  fill(g, INK);
  oval(g, px - rx * 0.18, py - ry * 0.2, rx * 0.16);
  fill(g, '#fff');
}

// Ряд из n клыков вдоль отрезка: вниз (dir = 1) или вверх (dir = -1).
function teeth(g, x0, x1, y, n, size, dir = 1) {
  const w = (x1 - x0) / n;
  for (let k = 0; k < n; k++) {
    poly(g, [[x0 + w * k, y], [x0 + w * (k + 1), y], [x0 + w * (k + 0.5), y + size * dir]]);
    fill(g, '#fffdf4');
    stroke(g, 0.7);
  }
}

// ------------------------------------------------------------ рисунок

// Зубастик ступени tier вокруг центра клетки (0, 0). clock — секунды, walked — пройденный путь в точках,
// look — куда смотрит [x, y] длиной до 1, alert — насколько заметил героя (0..1).
// open — насколько разинута пасть (0..1); не задано — живёт сама: дышит, а в погоне лязгает.
// tones — свои цвета вместо цветов ступени (босс, матка, подрывник).
export function drawChomper(g, tier, { clock = 0, walked = 0, look = [0, 0.4], alert = 0, open = null, tones = null }) {
  tones = tones ?? TONES[tier];
  const step = Math.sin(walked / STRIDE);
  const squash = 1 + 0.04 * Math.sin(2 * walked / STRIDE);
  const calm = 0.18 + 0.06 * Math.sin(clock * 3), snap = 0.55 + 0.45 * Math.sin(clock * 13);
  const gape = 2.5 + 8.5 * (open ?? calm + (snap - calm) * alert);

  oval(g, 0, 20, 13, 3.9);                           // тень
  fill(g, 'rgba(0, 0, 0, 0.32)');
  for (const side of [-1, 1]) {                      // лапы шагают по очереди
    oval(g, side * 6.5 + look[0] * 1.5, 17.5 - Math.max(0, side * step) * 3, 5, 3.2);
    fill(g, tones[2]);
    stroke(g, 1.3);
  }
  g.save();
  g.translate(0, 1 - Math.abs(step) * 1.2);
  g.scale(squash, 1 / squash);
  if (tier === 3) {                                  // рога — под телом, чтобы основание ушло под него
    for (const side of [-1, 1]) {
      g.save();
      g.translate(side * 9.5, -11.5);
      g.scale(side * 1.1, 1.1);
      g.rotate(0.55);
      g.beginPath();
      g.moveTo(-3.2, 2);
      g.quadraticCurveTo(-3.5, -7, 1.5, -11);
      g.quadraticCurveTo(2.8, -4, 3.2, 2);
      g.closePath();
      pair(g, BONE, 1.1);
      g.restore();
    }
  }
  if (tier >= 2) {                                   // гребень из шипов
    for (const turn of [-0.5, 0, 0.5]) {
      g.save();
      g.rotate(turn);
      poly(g, [[-2.6, -14], [0, -20.5], [2.6, -14]]);
      pair(g, [tones[1], tones[2]], 1.1);
      g.restore();
    }
  }
  oval(g, 0, 0, 15.5, 15);                           // тело
  volume(g, tones);
  stroke(g, 1.6);
  oval(g, -8, -9.5, 3.8, 2, -0.5);                   // блик
  fill(g, 'rgba(255, 255, 255, 0.5)');

  g.save();                                          // пасть: тёмный провал, язык, клыки сверху и снизу
  oval(g, 0, 5, 11.5, gape);
  fill(g, '#3a0508');
  stroke(g, 1.3);
  oval(g, 0, 5, 11.5, gape);
  g.clip();
  oval(g, 1, 5 + gape * 0.75, 6, gape * 0.45);
  fill(g, '#e8627a');
  const count = 3 + tier;
  teeth(g, -10.5, 10.5, 5 - gape * 0.92, count, tier >= 2 ? 5 : 3.2);
  teeth(g, -9, 9, 5 + gape * 0.92, Math.max(2, count - 1), tier >= 2 ? 4.2 : 2.6, -1);
  g.restore();

  eye(g, -5.4, -7.5, look, alert > 0.5);
  eye(g, 5.4, -7.5, look, alert > 0.5);
  if (tier >= 1) {                                   // брови: чем злее, тем круче
    const tilt = 2 + alert;
    for (const side of [-1, 1]) {
      g.beginPath();
      g.moveTo(side * 8.8, -12.6 - tilt);
      g.lineTo(side * 1.8, -12.6 + tilt * 0.4);
      stroke(g, 2.2);
    }
  }
  g.restore();
}

function drawPhantom(g, clock) {
  g.beginPath();
  g.arc(0, -6, 12, Math.PI, 0);
  for (let x = 12; x >= -12; x -= 3) g.lineTo(x, 14 + 3 * Math.sin(x * 0.8 + clock * 4));
  g.closePath();
  const paint = g.createLinearGradient(0, -18, 0, 16);
  paint.addColorStop(0, '#f4fbff');
  paint.addColorStop(1, '#8fc3de');
  fill(g, paint);
  stroke(g, 1.4);
  for (const side of [-1, 1]) {
    oval(g, side * 5, -6, 3, 4.5);
    fill(g, '#1a2a38');
  }
  oval(g, 0, 3, 3, 4);
  fill(g, '#1a2a38');
}

function metal(g, tones = IRON, width = 1.2) {
  const paint = g.createLinearGradient(-9, -15, 9, 15);
  paint.addColorStop(0, tones[0]);
  paint.addColorStop(1, tones[1]);
  fill(g, paint);
  stroke(g, width);
}

// ------------------------------------------------------------ тварь в игре

const KIND_TONES = {
  boss: ['#ff9a8a', '#a31414', '#4a0808'],
  queen: ['#ffd9f0', '#d95fa8', '#6e1a4a'],     // матка — розовая, крупнее
  bomber: ['#e0ddd2', '#8a877c', '#33312a'],    // подрывник — серый, с бомбой за спиной
};
const KIND_SCALE = { boss: 1.5, queen: 1.15 };

let serial = 0;

export class EnemyView {
  // enemy — враг из состояния сервера ({ id, tier, kind, … }); для украшения меню хватит { tier }.
  constructor(scene, enemy) {
    this.scene = scene;
    this.kind = enemy.kind ?? 'ghost';
    this.tier = this.kind === 'boss' ? 3 : enemy.tier;
    this.scale = KIND_SCALE[this.kind] ?? 1;
    this.armor = enemy.armor ?? 0;
    this.enraged = false;
    this.inWall = false;
    this.key = `enemy_canvas_${serial++}`;
    this.texture = scene.textures.createCanvas(this.key, SIZE * DETAIL, SIZE * DETAIL);
    this.image = scene.add.image(0, 0, this.key).setScale(this.scale / DETAIL);
    this.from = this.to = null;      // прошлое и новое положение от сервера, в клетках
    this.walked = 0;                 // сколько точек прошла — по этому счёту шагают лапы
    this.moved = 0;                  // …из них за последний шаг сервера
    this.chasing = false;
    this.alert = 0;                  // 0 — спокойна, 1 — заметила героя
    this.look = [0, 0.4];            // куда надо смотреть…
    this.eyes = [0, 0.4];            // …и куда глаза уже довернулись
    this.beat = ((enemy.id ?? 0) * 0.37) % 1 * 6;   // у каждой свой такт: не лязгают хором
    this.lastClock = null;
    this.dying = false;
  }

  // Новое состояние от сервера.
  sync(enemy) {
    const to = { x: enemy.x, y: enemy.y };
    const jump = !this.to || Math.abs(to.x - this.to.x) + Math.abs(to.y - this.to.y) > 1.5;
    this.from = jump ? to : this.to;
    this.to = to;
    this.moved = Math.hypot(to.x - this.from.x, to.y - this.from.y) * CELL;
    this.walked += this.moved;
    this.chasing = enemy.chasing;
    this.look = enemy.look[0] || enemy.look[1] ? enemy.look : [0, 0.4];
    this.armor = enemy.armor ?? 0;
    this.enraged = Boolean(enemy.enraged);
    this.inWall = Boolean(enemy.in_wall);
    if (this.kind === 'phantom') this.image.setAlpha(this.inWall ? 0.45 : 0.85);
    if (this.enraged) this.image.setTint(0xff9090);
    else this.image.clearTint();
  }

  // t — доля пути между двумя состояниями от сервера (0..1); clock — секунды игры (на паузе стоят).
  draw(t, clock) {
    if (!this.to || this.dying) return;
    const x = this.from.x + (this.to.x - this.from.x) * t, y = this.from.y + (this.to.y - this.from.y) * t;
    this.paint(clock, this.look, this.chasing, this.walked - (1 - t) * this.moved);
    this.image.setPosition(cellCenterX(x), cellCenterY(y)).setDepth(actorDepth(y));
  }

  // Перерисовывает холст: взгляд и злость меняются плавно, а не рывком.
  paint(clock, look, chasing, walked = 0) {
    const dt = this.lastClock === null ? 0 : Math.max(0, clock - this.lastClock);
    this.lastClock = clock;
    this.alert += ((chasing ? 1 : 0) - this.alert) * Math.min(1, dt * 7);
    this.eyes = this.eyes.map((v, i) => v + (look[i] - v) * Math.min(1, dt * 10));
    const g = this.texture.context;
    g.setTransform(1, 0, 0, 1, 0, 0);
    g.clearRect(0, 0, SIZE * DETAIL, SIZE * DETAIL);
    g.setTransform(DETAIL, 0, 0, DETAIL, SIZE / 2 * DETAIL, SIZE / 2 * DETAIL);
    if (this.kind === 'phantom') drawPhantom(g, clock + this.beat);
    else {
      drawChomper(g, this.tier, { clock: clock + this.beat, walked, look: this.eyes,
        alert: this.kind === 'boss' ? 1 : this.alert, tones: KIND_TONES[this.kind] ?? null });
      this.paintKind(g);
    }
    this.texture.refresh();
  }

  paintKind(g) {
    if (this.kind === 'armored' && this.armor > 0) {
      g.beginPath();
      g.arc(0, -12, 11, Math.PI, 0);
      g.closePath();
      metal(g);
      g.beginPath();
      g.roundRect(-13, -13.5, 26, 3, 1);
      metal(g, ['#e3e5ec', '#7a7d88'], 1);
      for (const x of [-6.6, 0, 6.6]) {
        oval(g, x, -18.05, 1.2);
        fill(g, '#4a4d57');
      }
      for (const side of [-1, 1]) {
        oval(g, side * 13, 4, 5, 3.5);
        metal(g, IRON, 1.1);
      }
    } else if (this.kind === 'boss') {
      g.beginPath();
      g.roundRect(-12, 9, 24, 4, 1.5);
      metal(g, IRON, 1.1);
      for (const x of [-8, 0, 8]) {
        oval(g, x, 11, 1.2);
        fill(g, '#22242a');
      }
      for (let i = this.armor; i < 2; i++) {
        const x = i ? 4 : -4;
        g.beginPath();
        g.moveTo(x, 9); g.lineTo(x - 1, 10.5); g.lineTo(x + 1, 11.5); g.lineTo(x, 13);
        stroke(g, 1.2);
      }
    } else if (this.kind === 'queen') {
      poly(g, [[-8, -14], [-5, -21], [-2, -14], [0, -22], [2, -14], [5, -21], [8, -14]]);
      fill(g, '#ffd24a');
      stroke(g, 1.1);
    } else if (this.kind === 'bomber') {
      oval(g, 0, -13, 5.2);
      fill(g, '#22201c');
      stroke(g, 1.2);
      g.beginPath();
      g.moveTo(0, -18);
      g.quadraticCurveTo(3, -23, 6, -21);
      g.lineWidth = 1.4;
      g.strokeStyle = '#c9b48a';
      g.stroke();
      oval(g, 6.5, -21.5, 1.6);
      fill(g, '#ffb21a');
    }
  }

  // Сгорела: белеет, сплющивается и тает; холст убирает сама.
  die() {
    this.dying = true;
    this.image.setTintFill(0xffffff);
    this.scene.tweens.add({
      targets: this.image, alpha: 0, scaleX: this.scale * 1.4 / DETAIL, scaleY: this.scale * 0.2 / DETAIL,
      y: this.image.y + 30, duration: 450,
      onComplete: () => this.remove(),
    });
  }

  remove() {
    this.image.destroy();
    this.scene.textures.remove(this.key);
  }

  destroy() {
    if (!this.dying) this.remove();
  }
}
