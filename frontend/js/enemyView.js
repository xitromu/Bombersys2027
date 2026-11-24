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
const rect = (g, x, y, w, h, r = 0) => {
  g.beginPath();
  if (r) g.roundRect(x, y, w, h, r);
  else g.rect(x, y, w, h);
};
const poly = (g, points) => {
  g.beginPath();
  points.forEach(([x, y]) => g.lineTo(x, y));
  g.closePath();
};
const line = (g, x0, y0, x1, y1, width = 1, color = INK) => {
  g.beginPath();
  g.moveTo(x0, y0);
  g.lineTo(x1, y1);
  g.lineWidth = width;
  g.lineCap = 'round';
  g.strokeStyle = color;
  g.stroke();
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

// Блик — светлое пятно на поверхности.
const shine = (g, x, y, rx, ry, alpha = 0.4) => {
  oval(g, x, y, rx, ry);
  fill(g, `rgba(255, 255, 255, ${alpha})`);
};
// Тот же глаз, только меньше: для зверьков, у которых глаза-бусинки.
const smallEye = (g, x, y, look, k = 0.75) => {
  g.save();
  g.translate(x, y);
  g.scale(k, k);
  eye(g, 0, 0, look, false);
  g.restore();
};

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

// Куча земли, которую крот выкинул из норы.
function mound(g, x, y) {
  g.beginPath();
  g.moveTo(x - 18, y + 4);
  g.quadraticCurveTo(x - 9, y - 7, x, y - 5);
  g.quadraticCurveTo(x + 9, y - 7, x + 18, y + 4);
  g.closePath();
  pair(g, ['#7a6244', '#3e2d1b'], 1.2);
  for (const [dx, dy, r] of [[-7, 0, 2.2], [4, 1, 2.6], [11, -1, 1.6], [-1, -3, 1.4]]) {
    oval(g, x + dx, y + dy, r);
    fill(g, '#8f7654');
    stroke(g, 0.8);
  }
}
// Комья, летящие из-под лап: t — доля полёта 0..1.
function crumbs(g, clock, x0, y0, reach = 9, lift = 11) {
  for (let i = 0; i < 3; i++) {
    const t = (clock * 1.4 + i / 3) % 1, side = i % 2 ? 1 : -1;
    oval(g, x0 + side * (reach * t), y0 - lift * Math.sin(Math.PI * t), 1.3, 1.1);
    fill(g, '#5d4a33');
    stroke(g, 0.7);
  }
}

const MINER_FUR = ['#f8e2a2', '#d4a842', '#7c5c18'];   // охристый мех
const MINER_HAT = ['#fffdf4', '#d6cfba'];              // белая каска

function lampGlow(g, x, y) {
  const glow = g.createRadialGradient(x, y, 1, x, y, 10);
  glow.addColorStop(0, 'rgba(255, 236, 120, 0.6)');
  glow.addColorStop(1, 'rgba(255, 236, 120, 0)');
  g.fillStyle = glow;
  g.fillRect(x - 11, y - 11, 22, 22);
}
function lamp(g, x, y) {
  oval(g, x, y, 3.4, 3.7);
  fill(g, '#ffe14a');
  stroke(g, 1.1);
  shine(g, x - 1, y - 1.2, 1, 0.8, 0.9);
}
function hardHat(g, y) {
  g.beginPath();
  g.arc(0, y, 12.5, Math.PI, 0);
  g.closePath();
  pair(g, MINER_HAT, 1.5);
  rect(g, -15, y - 1.4, 30, 3.6, 1.6);
  pair(g, MINER_HAT, 1.3);
}

// Крот — шахтёр: охристый пушистый зверь в белой каске с фонариком. Глаза-бусинки, ухмылка с двумя
// зубками, лапы с когтями гребут вперёд и из-под них летит земля. Под землёй видны только каска
// с фонарём над кучей выброшенной земли.
function drawMole(g, { clock = 0, walked = 0, look = [0, 0.4], burrowed = false }) {
  const step = Math.sin(walked / STRIDE);
  oval(g, 0, 21, 16, 4);
  fill(g, 'rgba(0, 0, 0, 0.32)');
  if (burrowed) {
    lampGlow(g, 0, 0);
    g.save();
    g.translate(0, 11);
    hardHat(g, -2);
    g.restore();
    lamp(g, 0, 1.5);
    mound(g, 0, 19);
    return;
  }
  g.save();
  g.translate(0, 1 - Math.abs(step) * 1.6);
  g.rotate(look[0] * 0.08 + step * 0.07);
  for (const side of [-1, 1]) {                      // лапы с когтями гребут по очереди
    g.save();
    g.translate(side * 13, 13 - Math.max(0, side * step) * 3.5);
    g.scale(side, 1);
    g.rotate(0.35);
    oval(g, 0, 0, 6, 4.6);
    pair(g, [MINER_FUR[0], MINER_FUR[2]], 1.3);
    for (let i = 0; i < 3; i++) {
      oval(g, 2.4 + i * 1, -2.4 + i * 2.4, 1.2);
      fill(g, '#fff7de');
      stroke(g, 0.8);
    }
    g.restore();
  }
  g.beginPath();                                     // грушевидное тело
  g.moveTo(-15, 9);
  g.bezierCurveTo(-17, -8, -8, -15, 0, -15);
  g.bezierCurveTo(8, -15, 17, -8, 15, 9);
  g.bezierCurveTo(12, 18, -12, 18, -15, 9);
  g.closePath();
  volume(g, MINER_FUR);
  stroke(g, 1.7);
  crumbs(g, clock, 0, 16, 11, 8);
  for (const side of [-1, 1]) {                      // слепые глазки-бусинки и усы
    smallEye(g, side * 5.8, -0.5, look);
    for (let i = 0; i < 3; i++) {
      const dy = -1 + i * 2;
      line(g, side * 4.5, 3 + dy, side * 12.5, 1.5 + dy * 1.6, 0.8, 'rgba(124, 92, 24, 0.95)');
    }
  }
  g.beginPath();                                     // ухмылка с двумя зубками
  g.moveTo(-5.5, 7);
  g.quadraticCurveTo(0, 13, 5.5, 7);
  g.closePath();
  fill(g, '#3a0d10');
  stroke(g, 1);
  for (const x of [-3.4, 0.3]) {
    poly(g, [[x, 7], [x + 3.1, 7], [x + 1.5, 10]]);
    fill(g, '#fffdf4');
    stroke(g, 0.8);
  }
  oval(g, 0, 3, 3.5, 2.6);                           // нос
  pair(g, ['#ffb9a0', '#d96a5a'], 1.2);
  shine(g, -1, 2.2, 1, 0.6, 0.7);
  hardHat(g, -7);
  lampGlow(g, 0, -10.5);
  lamp(g, 0, -10.5);
  g.restore();
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
  queen: ['#ffd9f0', '#d95fa8', '#6e1a4a'],     // матка — розовая, крупнее
  bomber: ['#e0ddd2', '#8a877c', '#33312a'],    // подрывник — серый, с бомбой за спиной
  thief: ['#e8e0b0', '#a89a58', '#5a4c22'],     // воришка — мешковатый бежево-зелёный
};
// Боссы разных уровней — разные: багровый (5-й), железный (10-й), змеиный (15-й), древний (20-й)
const BOSS_TONES = [
  ['#ff9a8a', '#a31414', '#4a0808'],
  ['#e3e5ec', '#7a7d88', '#33353d'],
  ['#b6f59a', '#3fae45', '#134f24'],
  ['#dcc0ff', '#8a4fe0', '#3a1474'],
];
const BOSS_SCALE = [1.5, 1.5, 1.55, 1.62];
const KIND_SCALE = { queen: 1.15 };

let serial = 0;

export class EnemyView {
  // enemy — враг из состояния сервера ({ id, tier, kind, … }); для украшения меню хватит { tier }.
  constructor(scene, enemy) {
    this.scene = scene;
    this.kind = enemy.kind ?? 'ghost';
    this.tier = this.kind === 'boss' ? 3 : enemy.tier;
    this.rank = enemy.rank ?? 0;       // у босса: какой он по счёту (вид и сила)
    this.scale = this.kind === 'boss' ? BOSS_SCALE[this.rank] : (KIND_SCALE[this.kind] ?? 1);
    this.armor = enemy.armor ?? 0;
    this.enraged = false;
    this.inWall = false;
    this.burrowed = false;             // крот под землёй
    this.loot = false;                 // воришка несёт бонус
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
    this.burrowed = Boolean(enemy.burrowed);
    this.loot = Boolean(enemy.loot);
    this.rank = enemy.rank ?? this.rank;
    if (this.kind === 'phantom') this.image.setAlpha(this.inWall ? 0.45 : 0.85);
    if (this.kind === 'mole') this.image.setAlpha(this.burrowed ? 0.55 : 1);
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
    else if (this.kind === 'mole') drawMole(g, { clock: clock + this.beat, walked, look: this.eyes, burrowed: this.burrowed });
    else {
      const tones = this.kind === 'boss' ? BOSS_TONES[this.rank] : (KIND_TONES[this.kind] ?? null);
      drawChomper(g, this.tier, { clock: clock + this.beat, walked, look: this.eyes,
        alert: this.kind === 'boss' ? 1 : this.alert, tones });
      this.paintKind(g, tones);
    }
    this.texture.refresh();
  }

  paintKind(g, tones = null) {
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
      for (let i = this.armor; i < 4; i++) {         // трещины на панцире: чем больше снято, тем заметнее
        const x = i % 2 ? 4 : -4;
        g.beginPath();
        g.moveTo(x, 9); g.lineTo(x - 1, 10.5); g.lineTo(x + 1, 11.5); g.lineTo(x, 13);
        stroke(g, 1.2);
      }
      if (this.rank >= 1) {                          // железный: наплечники
        for (const side of [-1, 1]) {
          oval(g, side * 14, -5, 6.4, 4.6);
          metal(g, IRON, 1.1);
        }
      }
      if (this.rank >= 2) {                          // змеиный: чешуйчатый гребень
        for (const [x, y] of [[-7, -13.5], [0, -15], [7, -13.5]]) {
          oval(g, x, y, 3.4, 2.2);
          fill(g, tones ? tones[0] : '#b6f59a');
          stroke(g, 0.8);
        }
      }
      if (this.rank >= 3) {                          // древний: корона
        poly(g, [[-9, -13], [-6, -20], [-3, -13], [0, -21], [3, -13], [6, -20], [9, -13]]);
        fill(g, '#ffd24a');
        stroke(g, 1.1);
      }
    } else if (this.kind === 'thief') {
      g.beginPath();                                 // повязка вора через глаза
      g.roundRect(-11.5, -10.2, 23, 4.6, 2);
      fill(g, '#26221c');
      stroke(g, 1);
      if (this.loot) {                               // добыча на спине: вещмешок
        poly(g, [[-6, -13], [6, -13], [8, -19], [0, -15.5], [-8, -19]]);
        fill(g, '#8a7a52');
        stroke(g, 1);
        oval(g, 0, -8.5, 7, 6.2);
        fill(g, '#b49a62');
        stroke(g, 1.2);
        line(g, -4, -10, 4, -10, 1, 'rgba(18, 13, 10, 0.5)');
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
