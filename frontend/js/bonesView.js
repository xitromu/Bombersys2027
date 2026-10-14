// Что остаётся от героя, которого обглодала змея: скелет или кучка костей с черепом — одни кости, без одежды и обуви.
// Какое из двух — выбирает сервер. Размер — как у лежащего героя: скелет длиной с тело (около 60 точек).
// Картинки героя сняты сверху наискосок, и лежащий вдоль экрана вверх-вниз выглядит короче — скелет тоже.
// Нарисовано на холсте при запуске (createBonesTextures), готовых картинок нет.

import { canvasTexture } from './canvasTexture.js';

const INK = '#120d0a';
const BONE = ['#f6f1df', '#b4ab93'];
const SIZE = 72;                      // сторона картинки: лежащий скелет длиннее клетки
const SQUASH = 0.58;                  // во сколько раз короче то, что лежит вдоль экрана вверх-вниз
const SQUASH_ACROSS = 0.8;            // так же для ширины тела: у героя её добавляет толщина тела
// Куда головой лежит скелет — туда же, куда упал герой.
const HEAD_TO = { right: [1, 0], left: [-1, 0], up: [0, -1], down: [0, 1] };

// ------------------------------------------------------------ кисти

// Заливает текущий контур переходом от светлого к тёмному и обводит.
function ink(g, [light, dark], width = 0.8) {
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
function bone(g, x0, y0, x1, y1, w = 1.4) {
  for (const [width, color] of [[w + 1.4, INK], [w, BONE[0]]]) {
    line(g, x0, y0, x1, y1, width, color);
    for (const [x, y] of [[x0, y0], [x1, y1]]) {
      oval(g, x, y, (width + 0.7) / 2);
      fill(g, color);
    }
  }
}

// ------------------------------------------------------------ кости (рисуются вокруг центра клетки)

// Скелет лежит на спине: u — вдоль тела (ступни −30, макушка +30), v — поперёк (правая рука −, левая +).
// at переводит такую точку на экран: поворачивает головой к [dx, dy] и укорачивает то, что вдоль экрана вверх-вниз.
function skeleton(g, [dx, dy]) {
  const at = (u, v) => [dx * u - dy * v, dy * u * SQUASH + dx * v * SQUASH_ACROSS];
  const b = (u0, v0, u1, v1, w) => bone(g, ...at(u0, v0), ...at(u1, v1), w);
  const ovalAt = (u, v, ru, rv) => oval(g, ...at(u, v), Math.abs(dx) * ru + Math.abs(dy) * rv,
    Math.abs(dy) * ru * SQUASH + Math.abs(dx) * rv * SQUASH_ACROSS);
  for (const s of [-1, 1]) {                                    // ноги
    b(-1.5, s * 3.8, -14.5, s * 3.4, 1.7);
    b(-14.5, s * 3.4, -26.5, s * 3.2, 1.4);
    b(-26.5, s * 3.2, -29.5, s * 3.8, 1.1);
  }
  poly(g, [[3, -5.2], [-1, -5.8], [-3.6, -2.6], [-3.6, 2.6], [-1, 5.8], [3, 5.2], [1, 0]].map(([u, v]) => at(u, v)));
  ink(g, BONE);                                                 // таз
  b(1, 0, 19.5, 0, 1.3);                                        // хребет
  for (let i = 0; i < 5; i++) {                                 // рёбра
    const u = 16 - i * 2.2, far = 5.4 - i * 0.35;
    for (const s of [-1, 1]) {
      for (const [width, color] of [[2.2, INK], [1, BONE[0]]]) {
        g.beginPath();
        g.moveTo(...at(u, 0));
        g.quadraticCurveTo(...at(u + 1, s * (far - 1)), ...at(u - 1.6, s * far));
        g.lineCap = 'round';
        g.lineWidth = width;
        g.strokeStyle = color;
        g.stroke();
      }
    }
  }
  for (const s of [-1, 1]) {                                    // ключицы и руки вдоль тела
    b(18, s * 1, 17.5, s * 6.6, 1);
    b(17.5, s * 7.4, 6.5, s * 8.4, 1.3);
    b(6.5, s * 8.4, -2.5, s * 8.2, 1.1);
    b(-2.5, s * 8.2, -6.5, s * 7.6, 1);
  }
  ovalAt(21.6, 0, 1.6, 2.4);                                    // череп лицом вверх: челюсть, голова
  ink(g, BONE);
  ovalAt(26, 0, 4.2, 3.2);
  ink(g, BONE, 0.9);
  for (const s of [-1, 1]) {
    ovalAt(25, s * 1.4, 1.1, 1);                                // глазницы
    fill(g, INK);
  }
  ovalAt(23.2, 0, 0.6, 0.5);                                    // нос
  fill(g, INK);
}

// Кучка: череп смотрит на нас, под ним кости крест-накрест; череп — с голову героя.
function pile(g) {
  bone(g, -8, 4.5, 8, -1, 1.6);
  bone(g, -8, -1, 8, 4.5, 1.6);
  for (const [x, a] of [[-5, 0.5], [5, -0.5]]) {
    g.save();
    g.translate(x, 6.5);
    g.rotate(a);
    bone(g, -3, 0, 3, 0, 1.1);
    g.restore();
  }
  rect(g, -3, 1.6, 6, 4, 1.3);                                  // челюсть
  ink(g, BONE);
  for (const x of [-1.4, 0, 1.4]) line(g, x, 3.6, x, 5.6, 0.5);
  oval(g, 0, -1, 5.2, 4.8);
  ink(g, BONE, 0.9);
  for (const side of [-1, 1]) {
    oval(g, side * 2.1, -0.6, 1.5, 1.7);
    fill(g, INK);
  }
  poly(g, [[0, 1.2], [-0.8, 2.7], [0.8, 2.7]]);
  fill(g, INK);
}

// Скелет — по картинке на каждую сторону, куда упал герой; кучка — одна. Тень под костями уже в картинке.
export function createBonesTextures(scene) {
  for (const [facing, [dx, dy]] of Object.entries(HEAD_TO)) {
    canvasTexture(scene, bonesKey('skeleton', facing), SIZE, SIZE, (g) => {
      g.translate(SIZE / 2, SIZE / 2);
      oval(g, 0, 1.5, dx ? 31 : 10, dx ? 10 * SQUASH_ACROSS : 31 * SQUASH);
      fill(g, 'rgba(0, 0, 0, 0.22)');
      skeleton(g, [dx, dy]);
    });
  }
  canvasTexture(scene, bonesKey('pile'), SIZE, SIZE, (g) => {
    g.translate(SIZE / 2, SIZE / 2);
    oval(g, 0.5, 4.5, 11, 4.5);
    fill(g, 'rgba(0, 0, 0, 0.22)');
    pile(g);
  });
}

// Какая картинка нужна: kind — skeleton или pile (как прислал сервер), facing — куда смотрел герой,
// когда упал. Середина картинки — центр клетки.
export const bonesKey = (kind, facing) => (kind === 'pile' ? 'bones_pile' : `bones_skeleton_${facing}`);
