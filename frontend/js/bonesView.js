// Что остаётся от героя, которого обглодала змея: скелет в сапогах или кучка костей с черепом.
// Какое из двух — выбирает сервер. Шапки и прочего при костях нет: змея съедает всё.
// Нарисовано на холсте при запуске (createBonesTextures), готовых картинок нет.

import { canvasTexture } from './canvasTexture.js';

const INK = '#120d0a';
const BONE = ['#f6f1df', '#b4ab93'];
const SIZE = 72;                      // сторона картинки: лежащий скелет длиннее клетки
// Скелет лежит головой туда же, куда упал герой.
const ANGLE = { right: 0, left: Math.PI, up: -Math.PI / 2, down: Math.PI / 2 };

// ------------------------------------------------------------ кисти

// Заливает текущий контур переходом от светлого к тёмному и обводит.
function ink(g, [light, dark], width = 1.1) {
  const paint = g.createLinearGradient(-6, -8, 6, 8);
  paint.addColorStop(0, light);
  paint.addColorStop(1, dark);
  g.fillStyle = paint;
  g.fill();
  g.lineWidth = width;
  g.lineJoin = 'round';
  g.strokeStyle = INK;
  g.stroke();
}
const rect = (g, x, y, w, h, r) => {
  g.beginPath();
  if (g.roundRect) g.roundRect(x, y, w, h, r);
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
const line = (g, x0, y0, x1, y1, width, color = INK) => {
  g.beginPath();
  g.moveTo(x0, y0);
  g.lineTo(x1, y1);
  g.lineCap = 'round';
  g.lineWidth = width;
  g.strokeStyle = color;
  g.stroke();
};
const fill = (g, color) => {
  g.fillStyle = color;
  g.fill();
};

// Кость: палочка с утолщениями на концах.
function bone(g, x0, y0, x1, y1, w = 2.2) {
  for (const [width, color] of [[w + 2, INK], [w, BONE[0]]]) {
    line(g, x0, y0, x1, y1, width, color);
    for (const [x, y] of [[x0, y0], [x1, y1]]) {
      oval(g, x, y, (width + 1.1) / 2);
      fill(g, color);
    }
  }
}

// Череп сверху: макушка в сторону +x, лицом вверх.
function skullTop(g, x) {
  g.save();
  g.translate(x, 0);
  rect(g, -8.2, -3.4, 4.6, 6.8, 1.6);                           // челюсть
  ink(g, BONE);
  for (const y of [-1.6, 0, 1.6]) line(g, -8, y, -4.4, y, 0.7);
  oval(g, 0, 0, 6.6, 5.9);
  ink(g, BONE, 1.2);
  for (const side of [-1, 1]) {
    oval(g, -1.2, side * 2.5, 1.9, 1.7);
    fill(g, INK);
  }
  poly(g, [[-3.4, 0], [-4.8, -1], [-4.8, 1]]);
  fill(g, INK);
  g.restore();
}

// ------------------------------------------------------------ кости (рисуются вокруг центра клетки)

// Скелет лежит вдоль оси x, головой в сторону +x; середина тела в нуле. Остались одни сапоги.
function skeleton(g) {
  bone(g, -9.5, -3.2, -17.5, -4.3);                             // ноги
  bone(g, -17.5, -4.3, -25, -3.6, 1.9);
  bone(g, -9.5, 3.2, -17.5, 4.3);
  bone(g, -17.5, 4.3, -25, 3.6, 1.9);
  for (const side of [-1, 1]) {                                 // сапоги
    rect(g, -29.5, side * 3.6 - 2.9, 7.5, 5.8, 2);
    ink(g, ['#6a4a2c', '#2c1c0e']);
  }
  poly(g, [[-6, -5.6], [-10.6, -4.2], [-11.2, 0], [-10.6, 4.2], [-6, 5.6], [-7.6, 0]]);   // таз
  ink(g, BONE);
  bone(g, 10.5, 0, -7, 0, 2);                                   // хребет
  for (let i = 0; i < 4; i++) {                                 // рёбра
    const x = 8.4 - i * 2.5, far = 6.6 - i * 0.35;
    for (const side of [-1, 1]) {
      for (const [width, color] of [[3, INK], [1.5, BONE[0]]]) {
        g.beginPath();
        g.moveTo(x, 0);
        g.quadraticCurveTo(x + 1.3, side * (far - 1), x - 1.5, side * far);
        g.lineCap = 'round';
        g.lineWidth = width;
        g.strokeStyle = color;
        g.stroke();
      }
    }
  }
  for (const side of [-1, 1]) {                                 // руки вдоль тела
    bone(g, 8.5, side * 6.8, 1.5, side * 10.2, 1.9);
    bone(g, 1.5, side * 10.2, -5, side * 8.6, 1.7);
  }
  skullTop(g, 17.2);
}

// Кучка: череп смотрит на нас, под ним кости крест-накрест.
function pile(g) {
  bone(g, -15, 9, 15, -1, 2.6);
  bone(g, -15, -1, 15, 9, 2.6);
  for (const [x, a] of [[-9, 0.5], [9, -0.5]]) {
    g.save();
    g.translate(x, 12);
    g.rotate(a);
    bone(g, -5, 0, 5, 0, 1.7);
    g.restore();
  }
  rect(g, -5.6, 3.5, 11.2, 7.5, 2.4);
  ink(g, BONE);
  oval(g, 0, -1.5, 9.6, 8.8);
  ink(g, BONE, 1.3);
  for (const side of [-1, 1]) {
    oval(g, side * 3.9, -1, 2.8, 3.1);
    fill(g, INK);
  }
  poly(g, [[0, 2.4], [-1.5, 5.2], [1.5, 5.2]]);
  fill(g, INK);
  for (const x of [-2.7, 0, 2.7]) line(g, x, 7, x, 11, 0.9);
}

// Скелет — по картинке на каждую сторону, куда упал герой; кучка — одна.
// Тень под костями уже в картинке (и не поворачивается вместе со скелетом).
export function createBonesTextures(scene) {
  const onShadow = (draw) => (g) => {
    g.translate(SIZE / 2, SIZE / 2);
    oval(g, 1, 3, 22, 10);
    fill(g, 'rgba(0, 0, 0, 0.22)');
    draw(g);
  };
  for (const [facing, angle] of Object.entries(ANGLE)) {
    canvasTexture(scene, bonesKey('skeleton', facing), SIZE, SIZE, onShadow((g) => {
      g.rotate(angle);
      g.scale(0.94, 0.94);
      skeleton(g);
    }));
  }
  canvasTexture(scene, bonesKey('pile'), SIZE, SIZE, onShadow((g) => {
    g.translate(0, 2);
    pile(g);
  }));
}

// Какая картинка нужна: kind — skeleton или pile (как прислал сервер), facing — куда смотрел герой,
// когда упал. Середина картинки — центр клетки.
export const bonesKey = (kind, facing) => (kind === 'pile' ? 'bones_pile' : `bones_skeleton_${facing}`);
