// Бонусы и дверь на поле — набор «фронтовой склад», в тон партизанам и блиндажу: дверь землянки, ящик
// с патронами, связка динамита, аптечка, мина, вещмешок, вещмешок с котелком, орден. Объёмные и «живые» —
// покачиваются, под ними мягкое свечение, изредка вспыхивает искра, чтобы их было труднее не заметить;
// на мине мигает красный огонёк. Нарисованы на холсте при запуске (createItemTextures), готовых картинок нет.

import { DETAIL, addCanvas, canvasTexture } from './canvasTexture.js';
import { CELL, DEPTH, cellLeft, cellTop } from './layout.js';

const INK = '#120d0a';
const GOLD = ['#ffe17a', '#c98a12'], DARKWOOD = ['#8a5a2e', '#4a2c12'], IRON = ['#c3c6d0', '#555862'];
const RED = ['#ff6a5a', '#a31414'], KHAKI = ['#b4bb72', '#4f5628'], ROPE = ['#d9c9a0', '#8a7a52'];
const SPARK = 7;                      // искра: полуразмер картинки и самый длинный луч
const SPARK_AT = [7, -9];             // где она вспыхивает — от центра клетки
const LAMP = 6;                       // огонёк мины: полуразмер картинки
const LAMP_AT = [0, 3.2];             // где он горит — от центра клетки

// ------------------------------------------------------------ кисти

// Заливает текущий контур переходом от светлого к тёмному и обводит.
function ink(g, [light, dark], width = 1.4) {
  const paint = g.createLinearGradient(-9, -15, 9, 15);
  paint.addColorStop(0, light);
  paint.addColorStop(1, dark);
  g.fillStyle = paint;
  g.fill();
  g.lineWidth = width;
  g.lineJoin = 'round';
  g.strokeStyle = INK;
  g.stroke();
}
const rect = (g, x, y, w, h, r = 0) => {
  g.beginPath();
  if (r && g.roundRect) g.roundRect(x, y, w, h, r);
  else g.rect(x, y, w, h);
};
const oval = (g, x, y, rx, ry = rx) => {
  g.beginPath();
  g.ellipse(x, y, rx, ry, 0, 0, Math.PI * 2);
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
const shine = (g, x, y, rx, ry, alpha = 0.5) => {              // блик
  oval(g, x, y, rx, ry);
  fill(g, `rgba(255, 255, 255, ${alpha})`);
};
// Звезда с n лучами: r — до кончика луча, inner — доля радиуса во впадинах.
const star = (g, x, y, r, inner = 0.42, n = 5) => {
  g.beginPath();
  for (let i = 0; i < n * 2; i++) {
    const a = -Math.PI / 2 + i * Math.PI / n, k = i % 2 ? r * inner : r;
    g.lineTo(x + Math.cos(a) * k, y + Math.sin(a) * k);
  }
  g.closePath();
};
// Дуга с тёмной обводкой: проволочная ручка, кольцо, дужка замка.
const wire = (g, x, y, r, from, to, width, color, back = false) => {
  g.beginPath();
  g.arc(x, y, r, from, to, back);
  g.lineCap = 'round';
  g.lineWidth = width * 2;
  g.strokeStyle = INK;
  g.stroke();
  g.lineWidth = width;
  g.strokeStyle = color;
  g.stroke();
};

function padlock(g, x, y, k) {                                 // висячий замок
  g.save();
  g.translate(x, y);
  g.scale(k, k);
  wire(g, 0, -1, 4.2, Math.PI, 0, 2.1, '#d9dce6');
  rect(g, -6, -1, 12, 9.5, 2);
  ink(g, GOLD, 1.2);
  oval(g, 0, 3, 1.5);
  fill(g, INK);
  line(g, 0, 3, 0, 6, 1.4);
  g.restore();
}

function sack(g, k) {                                          // вещмешок: k — размер
  g.save();
  g.scale(k, k);
  poly(g, [[-5.5, -8], [5.5, -8], [8, -15.5], [3, -13.5], [0, -15.5], [-3, -13.5], [-8, -15.5]]);
  ink(g, KHAKI);
  g.beginPath();
  g.moveTo(-6, -8);
  g.bezierCurveTo(-17, -2, -16, 14, -8, 15.5);
  g.lineTo(8, 15.5);
  g.bezierCurveTo(16, 14, 17, -2, 6, -8);
  g.closePath();
  ink(g, KHAKI);
  rect(g, -6.5, -9.8, 13, 3.2, 1);                             // завязка
  ink(g, ROPE, 1.1);
  shine(g, -8, 0, 2, 5, 0.3);
  rect(g, -6, 2, 12, 9.5, 1.5);                                // карман
  ink(g, ['#9aa25e', '#434a20'], 1.1);
  line(g, -6, 5.2, 6, 5.2, 0.9, 'rgba(18, 13, 10, 0.5)');
  g.restore();
}

function door(g, locked) {                                     // дверь землянки: сруб, доски, перекладины, укосина
  rect(g, -15.5, -20.5, 31, 41, 2);
  ink(g, ['#8a6a45', '#3d2a18']);
  rect(g, -12, -17.5, 24, 38, 1);
  ink(g, locked ? ['#b87058', '#5e2a1c'] : ['#b08a58', '#6b4a28'], 1.2);
  for (const x of [-4, 4]) line(g, x, -17, x, 20, 1, 'rgba(18, 13, 10, 0.5)');
  for (const y of [-13, 11]) {
    rect(g, -12, y, 24, 4.4);
    ink(g, DARKWOOD, 1);
  }
  line(g, -11, 10.5, 11, -8.5, 3.6);
  line(g, -11, 10.5, 11, -8.5, 2.2, DARKWOOD[0]);
  if (locked) {                                                // засов и замок
    rect(g, -15.5, -3.4, 31, 6.4, 1.5);
    ink(g, IRON, 1.2);
    padlock(g, 6.5, 4.2, 0.9);
  } else {                                                     // кольцо вместо ручки
    wire(g, 7.5, 2, 2.6, 0, Math.PI * 2, 1.3, '#d9dce6');
  }
}

// ------------------------------------------------------------ предметы (рисуются вокруг центра клетки)

const DRAW = {
  door: (g) => door(g, false),
  door_locked: (g) => door(g, true),
  chest(g) {                                                   // ящик с патронами
    poly(g, [[-16, -7], [-11, -14], [17, -14], [16, -7]]);     // крышка сверху
    ink(g, ['#a9c476', '#5d7a3a']);
    rect(g, -16, -7, 32, 21, 1.5);
    ink(g, ['#7d9a52', '#35491f']);
    line(g, -16, -1, 16, -1, 1, 'rgba(18, 13, 10, 0.55)');
    for (const x of [-12.5, 12.5]) {
      rect(g, x - 1.8, -7, 3.6, 21);
      ink(g, ['#5d7a3a', '#263617'], 0.9);
    }
    for (const x of [-16, 16]) wire(g, x, 4, 3.4, -Math.PI / 2, Math.PI / 2, 1.4, ROPE[0], x < 0);   // верёвочные ручки
    star(g, 0, 5.5, 6.2);
    ink(g, ['#ffe17a', '#d9a012'], 1);
    shine(g, -6, -11, 5, 1.2, 0.35);
  },
  bomb(g) {                                                    // связка динамита с фитилём и зелёным плюсом
    g.beginPath();
    g.moveTo(0, -9);
    g.quadraticCurveTo(3, -18, 9, -14);
    g.lineCap = 'round';
    g.lineWidth = 3.2;
    g.strokeStyle = INK;
    g.stroke();
    g.lineWidth = 1.7;
    g.strokeStyle = '#c9b48a';
    g.stroke();
    star(g, 9.5, -14, 4.6, 0.4, 6);
    fill(g, '#ffb21a');
    oval(g, 9.5, -14, 1.6);
    fill(g, '#fff6c8');
    for (const x of [-7.4, 7.4, 0]) {
      rect(g, x - 3.9, -9, 7.8, 23, 2.6);
      ink(g, RED);
      oval(g, x, -9, 3.9, 1.6);
      ink(g, ['#ffb0a0', '#c8442e'], 1);
      shine(g, x - 1.6, 2, 0.9, 7, 0.35);
    }
    rect(g, -12.4, -1.5, 24.8, 5.2, 1);
    ink(g, ['#efe2b4', '#9a8757'], 1.1);
    oval(g, 10, 11, 6.2);
    ink(g, ['#6fdc6a', '#1f8a2c'], 1.2);
    line(g, 6.7, 11, 13.3, 11, 2.3, '#ffffff');
    line(g, 10, 7.7, 10, 14.3, 2.3, '#ffffff');
  },
  life(g) {                                                    // аптечка
    wire(g, 0, -9, 5.5, Math.PI, 0, 2, '#8a6a45');           // ручка
    rect(g, -15, -9, 30, 22, 3.5);
    ink(g, ['#f6f3e8', '#aaa48f']);
    line(g, -15, -3.5, 15, -3.5, 1, 'rgba(18, 13, 10, 0.45)');
    rect(g, -2, -5.5, 4, 4, 1);
    ink(g, IRON, 0.9);
    rect(g, -2.6, 0, 5.2, 11);
    fill(g, '#d81e1e');
    rect(g, -6, 3, 12, 5);
    fill(g, '#d81e1e');
    shine(g, -9, -6.2, 4, 1.1, 0.6);
  },
  death(g) {                                                   // ловушка — мина; огонёк на ней мигает отдельно
    oval(g, 0, 8.5, 16.5, 8);                                  // борт
    ink(g, ['#4d6233', '#1c2912']);
    oval(g, 0, 4.5, 16.5, 8);
    ink(g, ['#8aa85c', '#3d5527']);
    oval(g, 0, 3.6, 8.5, 4.1);                                 // нажимная крышка
    ink(g, ['#a9c476', '#56733a'], 1.1);
    for (const a of [0.5, 2.1, 3.7, 5.3]) {                    // усики
      line(g, Math.cos(a) * 12.5, 4.5 + Math.sin(a) * 6, Math.cos(a) * 12.5, 1.5 + Math.sin(a) * 6, 2);
    }
    oval(g, ...LAMP_AT, 2.3);
    fill(g, '#8a1010');
    g.lineWidth = 0.9;
    g.strokeStyle = INK;
    g.stroke();
    shine(g, -8, 0.5, 4, 1.3, 0.35);
  },
  bag: (g) => sack(g, 0.86),
  bigbag(g) {                                                  // вещмешок побольше и котелок
    g.save();
    g.translate(-4, -2);
    sack(g, 1.06);
    g.restore();
    wire(g, 11, 6, 5.6, Math.PI, 0, 1.2, '#d9dce6');
    rect(g, 4.6, 5.5, 12.8, 11, 2.5);
    ink(g, IRON, 1.2);
    oval(g, 11, 5.8, 6.4, 2);
    ink(g, ['#e3e5ec', '#7a7d88'], 1);
  },
  gems(g) {                                                    // орден на колодке
    poly(g, [[-7.5, -18], [7.5, -18], [5, -4], [-5, -4]]);
    ink(g, ['#e8402e', '#8f1414']);
    for (const x of [-2.6, 2.6]) line(g, x * 1.35, -17.5, x, -4.5, 1.6, '#ffd24a');
    star(g, 0, 6.5, 12.5, 0.45);
    ink(g, GOLD);
    oval(g, 0, 6.5, 4.6);
    ink(g, RED, 1);
    star(g, 0, 6.5, 2.6);
    fill(g, '#ffe17a');
    shine(g, -4.5, 1, 2.4, 1.1, 0.7);
  },
};

export function createItemTextures(scene) {
  const centered = (draw) => (g) => {
    g.translate(CELL / 2, CELL / 2);
    draw(g);
  };
  for (const [kind, draw] of Object.entries(DRAW)) canvasTexture(scene, `bonus_${kind}`, CELL, CELL, centered(draw));
  canvasTexture(scene, 'bonus_shadow', CELL, CELL, centered((g) => {
    oval(g, 1, 17.5, 14, 3.6);
    fill(g, 'rgba(0, 0, 0, 0.28)');
  }));
  canvasTexture(scene, 'bonus_glow', CELL, CELL, centered((g) => {
    const glow = g.createRadialGradient(0, 4, 2, 0, 4, 23);
    glow.addColorStop(0, 'rgba(255, 236, 150, 0.55)');
    glow.addColorStop(1, 'rgba(255, 236, 150, 0)');
    oval(g, 0, 4, 23);
    fill(g, glow);
  }));
  canvasTexture(scene, 'bonus_spark', 2 * SPARK, 2 * SPARK, (g) => {
    const r = SPARK - 1, s = r * 0.22;
    g.translate(SPARK, SPARK);
    poly(g, [[0, -r], [s, -s], [r, 0], [s, s], [0, r], [-s, s], [-r, 0], [-s, -s]]);
    fill(g, '#ffffff');
  });
  canvasTexture(scene, 'bonus_lamp', 2 * LAMP, 2 * LAMP, (g) => {
    g.translate(LAMP, LAMP);
    const glow = g.createRadialGradient(0, 0, 0.5, 0, 0, LAMP);
    glow.addColorStop(0, 'rgba(255, 70, 50, 1)');
    glow.addColorStop(0.35, 'rgba(255, 50, 30, 0.55)');
    glow.addColorStop(1, 'rgba(255, 40, 30, 0)');
    oval(g, 0, 0, LAMP);
    fill(g, glow);
  });
}

// ------------------------------------------------------------ предмет на поле

export class ItemView {
  constructor(scene, item) {
    const x = cellLeft(item.x), y = cellTop(item.y);
    this.kind = item.kind;
    this.seed = item.id;                 // у каждого предмета своё время покачивания и искры
    this.top = y;
    this.glow = addCanvas(scene, x, y, 'bonus_glow').setDepth(DEPTH.items - 0.2);
    this.shadow = addCanvas(scene, x, y, 'bonus_shadow').setDepth(DEPTH.items - 0.1);
    this.body = addCanvas(scene, x, y, `bonus_${item.kind}`).setDepth(DEPTH.items);
    // поверх — искра, а у мины — красный огонёк
    const mine = item.kind === 'death';
    const [dx, dy] = mine ? LAMP_AT : SPARK_AT;
    this.sparkY = CELL / 2 + dy;
    this.spark = scene.add.image(x + CELL / 2 + dx, 0, mine ? 'bonus_lamp' : 'bonus_spark')
      .setDepth(DEPTH.items + 0.05).setScale(mine ? 1 / DETAIL : 0);
    this.locked = null;
    this.sync(item);
  }

  // Дверь, в которую попал огонь, запирается: краснеет, на ней засов и замок. Мина и запертая дверь не светятся.
  sync(item) {
    const locked = Boolean(item.locked);
    if (locked === this.locked) return;
    this.locked = locked;
    this.body.setTexture(locked ? 'bonus_door_locked' : `bonus_${this.kind}`);
    this.glow.setVisible(this.kind !== 'death' && !locked);
  }

  // clock — секунды игры (на паузе стоят). Дверь стоит на месте, остальное покачивается.
  draw(clock) {
    const door = this.kind === 'door';
    const lift = door ? 0 : -1.2 + 1.6 * Math.sin(clock * 3.2 + this.seed);
    this.body.y = this.top + lift;
    this.spark.y = this.top + this.sparkY + lift;
    if (this.kind === 'death') {         // огонёк мины мигает
      this.spark.setAlpha(Math.sin(clock * 7 + this.seed) > 0 ? 1 : 0.12);
      return;
    }
    // искра: раз в пару секунд, у каждого в своё время
    const phase = ((clock + this.seed * 0.37) % 2.2) / 0.35;
    this.spark.setScale(!door && phase < 1 ? Math.sin(phase * Math.PI) / DETAIL : 0);
  }

  destroy() {
    for (const part of [this.glow, this.shadow, this.body, this.spark]) part.destroy();
  }
}
