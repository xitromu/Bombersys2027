// Змея на экране: гадюка с зигзагом по спине. Тело — лента вдоль ломаной, которую присылает сервер
// (от головы к кончику хвоста): гнётся на поворотах, слегка извивается, а в тупике складывается
// петлёй — голова ползёт обратно вдоль собственного тела. Рисуется на своём холсте каждый кадр.

import { CELL, actorDepth, cellCenterX, cellCenterY } from './layout.js';

const DETAIL = 2;                    // холст вдвое подробнее экрана
const SIZE = 4 * CELL;               // сторона холста в точках экрана: змея длиной в две клетки и поля вокруг
const LENGTH = 2 * CELL;             // от центра головы до кончика хвоста — как SNAKE_LENGTH на сервере
const STEP = 2;                      // тело считаем через каждые две точки
const HALF = 7.8;                    // полуширина тела в самом толстом месте
const LANE = 9;                      // петля: на столько каждая половина тела отходит от середины коридора
const ROUND = 5;                     // скругление поворотов: точка — среднее соседних, по стольку с каждой стороны
const MARGIN = 2 * ROUND * STEP;     // запас пути перед головой и за хвостом — чтобы концы тоже скруглялись
const WAVE = 2.6, WAVE_LENGTH = 40;  // извивы: размах и длина волны
const SNOUT = 13.5;                  // от центра головы до кончика носа
const DARK = '#120d0a';              // цвет контура — как у героя
const SHADE = 'rgba(0, 0, 0, 0.28)';
// Цвет у змеи свой, не как у призраков: зелёная, жёлтая, красная, фиолетовая — от старшей ступени.
const RANKS = [['#60c458', '#3e8a3a'], ['#ecc92e', '#a8861a'], ['#d63434', '#962020'], ['#a56ce8', '#54208e']];

const smooth = (u) => {
  const v = Math.max(0, Math.min(1, u));
  return v * v * (3 - 2 * v);
};
function mix(a, b, t) {
  const part = (hex, i) => parseInt(hex.slice(1 + 2 * i, 3 + 2 * i), 16);
  return `#${[0, 1, 2].map((i) => Math.round(part(a, i) + (part(b, i) - part(a, i)) * t).toString(16).padStart(2, '0')).join('')}`;
}
const COLORS = RANKS.map(([base, dark]) => ({ base, dark, deep: mix(dark, DARK, 0.5) }));
// rank — цвет змеи по уровню: 0 — зелёная, 1 — жёлтая, 2 — красная, 3 — фиолетовая.
const colorsOf = (rank) => COLORS[Math.max(0, Math.min(COLORS.length - 1, rank))];

// Толщина тела вдоль змеи: u = 0 — голова, 1 — кончик хвоста. Шея чуть уже, к хвосту сходит на нет.
function taper(u) {
  const neck = 0.78 + 0.22 * smooth(u / 0.22);
  return neck * (u < 0.5 ? 1 : 1 - 0.88 * ((u - 0.5) / 0.5) ** 1.6);
}

const dot = (g, x, y, r, color) => {
  g.beginPath();
  g.arc(x, y, r, 0, Math.PI * 2);
  g.fillStyle = color;
  g.fill();
};

// ------------------------------------------------------------ линия тела

// Ломаная в точках экрана → частые точки через STEP, от −MARGIN (перед головой) до length + MARGIN (за хвостом).
// У каждой: d — расстояние от головы вдоль тела, (tx, ty) — куда ползёт эта часть змеи.
function sample(line, length) {
  const points = [];
  let i = 0, start = 0;                           // start — расстояние от головы до line[i]
  const ahead = (k) => Math.hypot(line[k + 1][0] - line[k][0], line[k + 1][1] - line[k][1]);
  for (let d = -MARGIN; d <= length + MARGIN; d += STEP) {
    while (i < line.length - 2 && d > start + ahead(i)) start += ahead(i++);
    const [ax, ay] = line[i], [bx, by] = line[i + 1];
    const segment = ahead(i) || 1;
    const k = (d - start) / segment;              // за пределами ломаной — продолжаем крайний отрезок
    points.push({ d, x: ax + (bx - ax) * k, y: ay + (by - ay) * k, tx: (ax - bx) / segment, ty: (ay - by) / segment });
  }
  return points;
}

// Места, где тело сложено вдвое (голова повернула назад): расстояния от головы вдоль тела.
function folds(line) {
  const found = [];
  let walked = 0;
  for (let i = 1; i < line.length - 1; i++) {
    const [ax, ay] = line[i - 1], [bx, by] = line[i], [cx, cy] = line[i + 1];
    const before = Math.hypot(bx - ax, by - ay), after = Math.hypot(cx - bx, cy - by);
    walked += before;
    if (before > 0.01 && after > 0.01 && ((bx - ax) * (cx - bx) + (by - ay) * (cy - by)) / (before * after) < -0.5) {
      found.push(walked);
    }
  }
  return found;
}

// У петли обе половины тела держатся «правой стороны дороги» и поэтому ложатся рядом, а не друг на друга.
// Петля раскрывается, пока голова отходит от сгиба, и сходит на нет, когда в сгиб втягивается хвост;
// вдали от сгиба тело возвращается на середину коридора.
function spread(points, line, length) {
  for (const at of folds(line)) {
    const open = smooth(at / 14) * smooth((length - at) / 14);
    for (const p of points) {
      const lane = LANE * open * (1 - smooth((Math.abs(p.d - at) - 20) / 70));
      p.x -= p.ty * lane;
      p.y += p.tx * lane;
    }
  }
}

// Повороты скругляем: каждая точка — среднее соседних. Саму голову не трогаем — она идёт точно по клеткам.
function round(points) {
  let xs = points.map((p) => p.x), ys = points.map((p) => p.y);
  for (let pass = 0; pass < 2; pass++) {
    const average = (values) => values.map((_, i) => {
      let sum = 0;
      for (let j = -ROUND; j <= ROUND; j++) sum += values[Math.max(0, Math.min(values.length - 1, i + j))];
      return sum / (2 * ROUND + 1);
    });
    [xs, ys] = [average(xs), average(ys)];
  }
  points.forEach((p, i) => {
    const k = smooth(p.d / 14);
    p.x += (xs[i] - p.x) * k;
    p.y += (ys[i] - p.y) * k;
  });
}

// Направление «вперёд» (tx, ty) и «вбок» (nx, ny) в каждой точке — по соседним точкам.
function aim(points) {
  points.forEach((p, i) => {
    const a = points[Math.max(0, i - 1)], b = points[Math.min(points.length - 1, i + 1)];
    const length = Math.hypot(a.x - b.x, a.y - b.y) || 1;
    p.tx = (a.x - b.x) / length;
    p.ty = (a.y - b.y) / length;
    p.nx = -p.ty;
    p.ny = p.tx;
  });
}

// ------------------------------------------------------------ рисование

// Точка на теле: d — расстояние от головы, side — от −1 до 1 поперёк тела.
function spot(pts, d, side) {
  const p = pts[Math.max(0, Math.min(pts.length - 1, Math.round(d / STEP)))];
  return [p.x + p.nx * p.h * side, p.y + p.ny * p.h * side];
}

// Очертание тела: k — доля толщины, (ox, oy) — сдвиг, grow — прибавка к толщине (под контур),
// tip — закруглить ли конец (кончик хвоста).
function outline(g, pts, k, ox, oy, grow, tip = true) {
  g.beginPath();
  for (let i = 0; i < pts.length; i++) {
    const p = pts[i], h = p.h * k + grow;
    g.lineTo(p.x + p.nx * h + ox, p.y + p.ny * h + oy);
  }
  for (let i = pts.length - 1; i >= 0; i--) {
    const p = pts[i], h = p.h * k + grow;
    g.lineTo(p.x - p.nx * h + ox, p.y - p.ny * h + oy);
  }
  g.closePath();
  if (!tip) return;
  const end = pts[pts.length - 1];
  g.moveTo(end.x + ox + end.h * k + grow, end.y + oy);
  g.arc(end.x + ox, end.y + oy, end.h * k + grow, 0, Math.PI * 2);
}

function paint(g, pts, k, ox, oy, grow, color, tip = true) {
  outline(g, pts, k, ox, oy, grow, tip);
  g.fillStyle = color;
  g.fill();
}

// Зигзаг по спине и точки по бокам.
function pattern(g, pts, c, length) {
  g.beginPath();
  let j = 0;
  for (let d = 9; d < length - 4; d += 6, j++) g.lineTo(...spot(pts, d, j % 2 ? 0.62 : -0.62));
  g.lineWidth = 3.1;
  g.lineJoin = 'miter';
  g.miterLimit = 4;
  g.strokeStyle = c.deep;
  g.stroke();
  j = 0;
  for (let d = 9; d < length - 16; d += 6, j++) dot(g, ...spot(pts, d, j % 2 ? -0.82 : 0.82), 1.05, c.deep);
}

// Голова гадюки: нос смотрит вправо, центр в нуле.
function headShape(g) {
  g.beginPath();
  g.moveTo(13.5, 0);
  g.bezierCurveTo(12, 5, 6, 10.8, -1.5, 10.8);
  g.bezierCurveTo(-7, 10.8, -9.5, 6, -9.5, 0);
  g.bezierCurveTo(-9.5, -6, -7, -10.8, -1.5, -10.8);
  g.bezierCurveTo(6, -10.8, 12, -5, 13.5, 0);
  g.closePath();
}

function face(g, c, alert) {
  g.beginPath();
  g.moveTo(-6.5, 6.2);
  g.lineTo(3, 0);
  g.lineTo(-6.5, -6.2);
  g.lineWidth = 2;
  g.lineJoin = 'round';
  g.strokeStyle = c.deep;
  g.stroke();
  for (const side of [-1, 1]) {
    g.beginPath();
    g.ellipse(6.2, side * 6.3, 2.6, 1.9, 0, 0, Math.PI * 2);
    g.fillStyle = alert > 0.5 ? '#ff2a2a' : '#ffd23a';   // заметила героя — глаза загораются красным
    g.fill();
    g.lineWidth = 0.9;
    g.strokeStyle = DARK;
    g.stroke();
    g.beginPath();
    g.ellipse(6.2, side * 6.3, 2.1, 0.6, 0, 0, Math.PI * 2);
    g.fillStyle = DARK;
    g.fill();
    dot(g, 11.6, side * 1.5, 0.7, DARK);
  }
}

function tongue(g, out) {
  const length = 7 * out;
  g.beginPath();
  g.moveTo(SNOUT - 2, 0);
  g.lineTo(SNOUT + length, 0);
  g.moveTo(SNOUT + length, 0);
  g.lineTo(SNOUT + length + 3.4 * out, 2);
  g.moveTo(SNOUT + length, 0);
  g.lineTo(SNOUT + length + 3.4 * out, -2);
  g.lineWidth = 1.3;
  g.lineCap = 'round';
  g.strokeStyle = '#d8242f';
  g.stroke();
}

function drawHead(g, c, x, y, angle, flick, alert) {
  const local = (dx, dy, k, draw) => {
    g.save();
    g.translate(x + dx, y + dy);
    g.rotate(angle);
    g.scale(k, k);
    draw();
    g.restore();
  };
  local(2, 3, 1, () => { headShape(g); g.fillStyle = SHADE; g.fill(); });
  if (flick > 0) local(0, 0, 1, () => tongue(g, flick));
  local(0, 0, 1, () => {
    headShape(g);
    g.lineWidth = 2.6;
    g.strokeStyle = DARK;
    g.stroke();
    g.fillStyle = c.dark;
    g.fill();
  });
  local(-0.7, -0.9, 0.82, () => { headShape(g); g.fillStyle = c.base; g.fill(); });   // свет сверху слева
  local(0, 0, 1, () => face(g, c, alert));
}

function drawBody(g, pts, c, length) {
  paint(g, pts, 1, 2, 3, 1, SHADE);
  // Тело рисуем кусками от хвоста к голове, каждый со своим контуром: там, где змея ползёт вдоль себя,
  // ближняя к голове часть ложится поверх дальней и не сливается с ней.
  const PIECE = 4;
  for (let to = pts.length - 1; to > 0; to -= PIECE) {
    const piece = pts.slice(Math.max(0, to - PIECE - 1), to + 1);
    const tip = to === pts.length - 1;
    paint(g, piece, 1, 0, 0, 1.3, DARK, tip);
    paint(g, piece, 1, 0, 0, 0, c.dark, tip);
    g.save();
    outline(g, piece, 1, 0, 0, 0, tip);
    g.clip();
    paint(g, pts, 0.74, -0.6, -0.8, 0, c.base);
    pattern(g, pts, c, length);
    paint(g, pts, 0.2, -2.6, -3, 0, 'rgba(255, 255, 255, 0.28)');   // блик
    g.restore();
  }
}

// ------------------------------------------------------------ змея в игре

let serial = 0;

export class SnakeView {
  constructor(scene, enemy) {
    this.scene = scene;
    this.colors = colorsOf(enemy.rank);
    this.key = `snake_canvas_${serial++}`;
    this.texture = scene.textures.createCanvas(this.key, SIZE * DETAIL, SIZE * DETAIL);
    this.image = scene.add.image(0, 0, this.key).setOrigin(0).setScale(1 / DETAIL);
    this.from = this.to = null;      // ломаные тела в клетках: прошлая и новая от сервера
    this.crawled = 0;                // сколько точек проползла голова — по этому счёту идут извивы
    this.moved = 0;                  // …из них за последний шаг сервера
    this.alert = 0;                  // 0 — спокойна, 1 — заметила героя
    this.chasing = false;
    this.angle = 0;                  // куда смотрит голова
    this.turned = false;             // голова уже хоть раз повернулась по ходу движения
    this.lastClock = null;
  }

  // Новое состояние от сервера: path — ломаная [x, y] в клетках от головы к кончику хвоста.
  sync(enemy) {
    this.colors = colorsOf(enemy.rank);
    const jump = !this.to || Math.abs(enemy.x - this.to[0][0]) + Math.abs(enemy.y - this.to[0][1]) > 1.5;
    this.from = jump ? enemy.path : this.to;
    this.to = enemy.path;
    this.moved = Math.hypot(this.to[0][0] - this.from[0][0], this.to[0][1] - this.from[0][1]) * CELL;
    this.crawled += this.moved;
    this.chasing = enemy.chasing;
  }

  // t — доля пути между двумя состояниями от сервера (0..1), как у остальных участников;
  // clock — секунды игры (на паузе стоят).
  draw(t, clock) {
    if (!this.to) return;
    const px = ([x, y]) => [cellCenterX(x), cellCenterY(y)];
    const [fx, fy] = this.from[0], [hx, hy] = this.to[0];
    const head = [fx + (hx - fx) * t, fy + (hy - fy) * t];
    // Голова — между прошлым и новым положением; хвост за этот шаг ещё не дополз — его конец берём из прошлого.
    const line = [head, ...this.to.slice(1), this.from[this.from.length - 1]].map(px)
      .filter((p, i, all) => i === 0 || Math.hypot(p[0] - all[i - 1][0], p[1] - all[i - 1][1]) > 0.01);
    let length = 0;                                 // длина тела — как у сервера (пока змея выползает, она короче)
    for (let i = 1; i < this.to.length; i++) {
      length += Math.hypot(this.to[i][0] - this.to[i - 1][0], this.to[i][1] - this.to[i - 1][1]) * CELL;
    }

    const dt = this.lastClock === null ? 0 : Math.max(0, clock - this.lastClock);
    this.lastClock = clock;
    this.alert += ((this.chasing ? 1 : 0) - this.alert) * Math.min(1, dt * 7);

    let pts = [{ d: 0, x: line[0][0], y: line[0][1], tx: Math.cos(this.angle), ty: Math.sin(this.angle) }];
    if (line.length > 1 && length > STEP) {
      const all = sample(line, length);
      spread(all, line, length);
      round(all);
      pts = all.filter((p) => p.d >= 0 && p.d <= length + 0.01);
      aim(pts);
      const crawled = this.crawled - (1 - t) * this.moved;
      for (const p of pts) {                        // извивы «стоят» на полу, а тело сквозь них протекает
        const w = WAVE * smooth(p.d / 18) * Math.sin((crawled - p.d) / WAVE_LENGTH * 2 * Math.PI);
        p.x += p.nx * w;
        p.y += p.ny * w;
      }
      aim(pts);
      // Голова смотрит от шеи и доворачивается плавно, а не рывком: на угле — за десятую долю секунды,
      // при развороте петлёй — за две.
      const neck = pts[Math.min(pts.length - 1, 5)];
      if (Math.hypot(pts[0].x - neck.x, pts[0].y - neck.y) > 3) {
        const wanted = Math.atan2(pts[0].y - neck.y, pts[0].x - neck.x);
        this.angle = this.turned ? Phaser.Math.Angle.RotateTo(this.angle, wanted, dt * 14) : wanted;
        this.turned = true;
      }
    }
    const full = Math.max(length, 1);
    for (const p of pts) p.h = HALF * taper(p.d / full) * Math.min(1, length / 24);

    // Холст ставим так, чтобы змея была посередине, и рисуем на нём в точках экрана.
    const xs = pts.map((p) => p.x), ys = pts.map((p) => p.y);
    const left = Math.round((Math.min(...xs) + Math.max(...xs)) / 2 - SIZE / 2);
    const top = Math.round((Math.min(...ys) + Math.max(...ys)) / 2 - SIZE / 2);
    const g = this.texture.context;
    g.setTransform(1, 0, 0, 1, 0, 0);
    g.clearRect(0, 0, SIZE * DETAIL, SIZE * DETAIL);
    g.setTransform(DETAIL, 0, 0, DETAIL, -left * DETAIL, -top * DETAIL);
    if (pts.length > 2) drawBody(g, pts, this.colors, length);
    const period = this.chasing ? 0.9 : 1.8;        // язык: заметила героя — пробует воздух чаще
    const phase = (clock % period) / period;
    drawHead(g, this.colors, pts[0].x, pts[0].y, this.angle, phase < 0.2 ? Math.sin(phase / 0.2 * Math.PI) : 0, this.alert);
    this.texture.refresh();
    this.image.setPosition(left, top).setDepth(actorDepth(head[1]));
  }

  destroy() {
    this.image.destroy();
    this.scene.textures.remove(this.key);
  }
}
