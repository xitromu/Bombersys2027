// Бомба и взрыв на экране. Картинки прежние (bomb*.png, explosion.png, flame_*.png); здесь то, что их оживляет:
// частицы огня текут от центра по коридорам, искры разлетаются и отскакивают, отсвет на стенах, дым, копоть,
// угольки, обломки сгоревшей стены. Образец — макет mockups/boom, вариант 1.
//
// Огонь в клетке живёт столько, сколько его держит сервер: пока клетка смертельна, огонь на ней виден.
// Всё остальное — украшение: считается от времени после взрыва, без памяти между кадрами.
// Время (now) — секунды игры: на паузе оно стоит, и взрывы замирают вместе с игрой.

import { CELL, DEPTH, FIELD_SIZE, FIELD_X, FIELD_Y, cellCenterX, cellCenterY, cellLeft, cellTop } from './layout.js';

const ADD = Phaser.BlendModes.ADD;
const AXES = [[1, 0], [-1, 0], [0, -1], [0, 1]];
const REACH = 2;                // на сколько клеток бьёт взрыв
const FLAME_TIME = 0.75;        // сколько секунд горит огонь (как FLAME_TIME на сервере): к концу он бледнеет
const FLAME_FLOOR = 0.35;       // ...но не слабее этого, пока сервер его не погасил
const BLAST_TIME = 2.5;         // через столько секунд от взрыва не остаётся и копоти
const SPARKS = 46;
const SMOKE = 16;
const EMBERS = 16;
const CHUNKS = 7;
const SOOT = [0.75, 0.3, 0.19]; // копоть: в центре, в соседней клетке, в дальней
const FLASH = 0.35;             // вспышка на всё поле в миг взрыва
const INK = 0x120d0a;
const BRICKS = [0x8a5a3a, 0x6e4630, 0xa87850];
// Два слоя частиц огня: скорость (точек в секунду), картинка (вторая повёрнута на пол-оборота), непрозрачность.
const LAYERS = [[70, '', 1], [118, '_back', 0.75]];
const FUSE_TIPS = [[44, 21], [42, 22], [39.5, 23.5], [36, 25.5], [32, 27]];   // где горит фитиль в каждом кадре bomb*.png
// Цвет по жару: от тёмно-красного (почти погасло) до белого пекла.
const HEAT = [[70, 12, 4], [150, 24, 4], [230, 60, 6], [255, 120, 14], [255, 180, 50], [255, 225, 130], [255, 250, 225]];

const clamp = (u) => Math.max(0, Math.min(1, u));
const smooth = (u) => { const v = clamp(u); return v * v * (3 - 2 * v); };
// «Случайные» числа, одинаковые в каждом кадре: i — номер частицы, k — какое по счёту число нужно.
const rnd = (i, k = 0) => { const v = Math.sin(i * 127.1 + k * 311.7) * 43758.5453; return v - Math.floor(v); };

function heatColor(heat) {
  const f = clamp(heat) * (HEAT.length - 1), i = Math.min(HEAT.length - 2, Math.floor(f));
  const [r, g, b] = HEAT[i].map((v, n) => Math.round(v + (HEAT[i + 1][n] - v) * (f - i)));
  return (r << 16) | (g << 8) | b;
}

// Высота над полом: взлёт, падение и один отскок.
function hop(time, lift) {
  const G = 420, first = 2 * lift / G, second = lift * 0.35;
  if (time < first) return lift * time - G * time * time / 2;
  const rest = time - first;
  return rest < 2 * second / G ? second * rest - G * rest * rest / 2 : 0;
}

// Светящаяся точка: яркая сердцевина и слабый ореол.
function glint(g, x, y, r, color, alpha) {
  if (alpha <= 0.01) return;
  g.fillStyle(color, alpha * 0.3).fillCircle(x, y, r * 0.75);
  g.fillStyle(color, alpha).fillCircle(x, y, r * 0.38);
}

// Текстуры рисуются один раз при загрузке: мягкие пятна (свет, искра, дым, копоть) и перевёрнутые картинки огня.
export function createBlastTextures(scene) {
  const dot = (key, r, g, b) => {
    const texture = scene.textures.createCanvas(key, 64, 64);
    const paint = texture.context.createRadialGradient(32, 32, 0, 32, 32, 32);
    for (const [at, alpha] of [[0, 1], [0.35, 0.55], [0.7, 0.14], [1, 0]]) paint.addColorStop(at, `rgba(${r}, ${g}, ${b}, ${alpha})`);
    texture.context.fillStyle = paint;
    texture.context.fillRect(0, 0, 64, 64);
    texture.refresh();
  };
  dot('fx_glow', 255, 120, 14);
  dot('fx_spark', 255, 180, 50);
  dot('fx_smoke', 44, 40, 38);
  dot('fx_soot', 14, 8, 5);
  for (const kind of ['near', 'far']) {
    const texture = scene.textures.createCanvas(`flame_${kind}_back`, CELL, CELL);
    texture.context.translate(CELL, CELL);
    texture.context.rotate(Math.PI);
    texture.context.drawImage(scene.textures.get(`flame_${kind}`).getSourceImage(), 0, 0);
    texture.refresh();
  }
}

// Бомба: кадр фитиля — по времени до взрыва; искра светится, под конец бомба дрожит всё чаще.
export class BombView {
  constructor(scene, bomb, now) {
    this.x = cellCenterX(bomb.x);
    this.y = cellCenterY(bomb.y);
    // бомба подрывника (owner < 0) — та же связка, но тёмная, «чужая»
    this.enemy = bomb.owner < 0;
    this.sprite = scene.add.sprite(this.x, this.y, `bomb${this.enemy ? 1 : bomb.owner + 1}`, 0).setDepth(DEPTH.bombs);
    if (this.enemy) this.sprite.setTint(0x8a8a8a);
    this.glow = scene.add.image(this.x, this.y, 'fx_spark').setBlendMode(ADD).setDepth(DEPTH.bombs + 0.01)
      .setDisplaySize(18, 18);
    this.at = now;
    this.shake = 0;
    this.sync(bomb);
  }

  sync(bomb) {
    this.progress = bomb.progress;
    this.frame = Math.min(FUSE_TIPS.length - 1, Math.floor(bomb.progress * FUSE_TIPS.length));
    this.sprite.setFrame(this.frame);
    if (!this.enemy) {
      if (bomb.remote) this.sprite.setTint(0x7ab8ff);   // пультовая: ждёт клавиши, синяя
      else this.sprite.clearTint();
    }
  }

  draw(now) {
    this.shake += (now - this.at) * (9 + 52 * this.progress);
    this.at = now;
    const pulse = 1 + 0.07 * smooth((this.progress - 0.55) / 0.45) * Math.sin(this.shake);
    const [tx, ty] = FUSE_TIPS[this.frame];
    this.sprite.setScale(pulse);
    this.glow.setPosition(this.x + (tx - CELL / 2) * pulse, this.y + (ty - CELL / 2) * pulse)
      .setAlpha(0.55 + 0.25 * Math.sin(now * 47));
  }

  destroy() {
    this.sprite.destroy();
    this.glow.destroy();
  }
}

// Огонь в одной клетке: отсвет и два слоя частиц, которые текут от центра взрыва и заворачиваются по кругу.
export class FlameView {
  // blasts — взрывы, пришедшие с тем же состоянием: по ним понятно, в какую сторону от центра течёт огонь.
  constructor(scene, flame, blasts, now) {
    const away = (b) => Math.abs(flame.x - b.x) + Math.abs(flame.y - b.y);
    const from = blasts.filter((b) => (b.x === flame.x || b.y === flame.y) && away(b) <= REACH)
      .sort((a, b) => away(a) - away(b))[0];
    this.scene = scene;
    this.dx = from ? Math.sign(flame.x - from.x) : 0;
    this.dy = from ? Math.sign(flame.y - from.y) : 0;
    this.step = from ? away(from) : 0;
    this.left = cellLeft(flame.x);
    this.top = cellTop(flame.y);
    this.flicker = flame.x * 3 + flame.y * 5;
    this.born = now;
    this.count = 0;
    this.seen = 0;
    this.glow = scene.add.image(cellCenterX(flame.x), cellCenterY(flame.y), 'fx_glow').setBlendMode(ADD)
      .setDepth(DEPTH.flames - 0.01).setDisplaySize(62, 62).setAlpha(0);
    this.layers = LAYERS.map(([speed, suffix, alpha]) => ({
      speed, alpha,
      parts: [0, 1].map(() => scene.add.image(0, 0, `flame_${flame.kind}${suffix}`).setOrigin(0)
        .setDepth(DEPTH.flames).setAlpha(0)),
    }));
  }

  // Вызывается после каждого состояния от сервера. В клетку добавился ещё один огонь (цепочка взрывов) —
  // он разгорается заново.
  settle(now) {
    if (this.seen > this.count) this.born = now;
    this.count = this.seen;
    this.seen = 0;
  }

  draw(now) {
    const age = now - this.born;
    const live = smooth((age - this.step * 0.035) / 0.05)
      * (1 - (1 - FLAME_FLOOR) * smooth((age - (FLAME_TIME - 0.16)) / 0.16));
    const flows = this.dx !== 0 || this.dy !== 0;
    this.glow.setAlpha(0.5 * live);
    for (const { speed, alpha, parts } of this.layers) {
      const shift = flows ? Math.floor(age * speed) % CELL : 0;
      const shown = live * alpha * (0.82 + 0.18 * Math.sin(now * 40 + this.flicker + speed));
      parts.forEach((part, n) => {
        // картинка сдвинута от угла клетки; видна только та её часть, что внутри клетки, остальное дорисует вторая
        const ox = this.dx * (shift - n * CELL), oy = this.dy * (shift - n * CELL);
        const width = CELL - Math.abs(ox), height = CELL - Math.abs(oy);
        part.setVisible(width > 0 && height > 0 && (n === 0 || flows));
        if (!part.visible) return;
        part.setPosition(this.left + ox, this.top + oy).setAlpha(shown)
          .setCrop(Math.max(0, -ox), Math.max(0, -oy), width, height);
      });
    }
  }

  // Сервер погасил огонь — на экране он быстро сходит на нет.
  destroy() {
    const targets = [this.glow, ...this.layers.flatMap((layer) => layer.parts)];
    this.scene.tweens.add({ targets, alpha: 0, duration: 90, onComplete: () => targets.forEach((t) => t.destroy()) });
  }
}

// Клетки, которые накрыл этот взрыв: центр и рукава креста — докуда дошёл огонь (в клетках поля).
function blastCells(event, state) {
  const burning = new Set(state.flames.map((f) => `${f.x},${f.y}`));
  const burnt = new Set(state.events.filter((e) => e.type === 'wall_destroyed').map((e) => `${e.x},${e.y}`));
  const cells = [{ x: event.x, y: event.y, step: 0 }];
  for (const [dx, dy] of AXES) {
    for (let step = 1; step <= REACH; step++) {
      const x = event.x + dx * step, y = event.y + dy * step;
      if (!burning.has(`${x},${y}`)) break;
      cells.push({ x, y, step });
      if (burnt.has(`${x},${y}`)) break;       // стена сгорела и дальше огонь не пустила
    }
  }
  return cells;
}

// Всё, что взрыв добавляет к огненному шару: вспышка, отсвет, искры, дым, копоть и угольки.
export class BlastView {
  // event — событие «explosion», state — состояние игры, с которым оно пришло.
  constructor(scene, event, state, now) {
    this.start = now;
    this.seed = event.id * 97;
    this.x = cellCenterX(event.x);
    this.y = cellCenterY(event.y);
    this.cells = blastCells(event, state).map((c) => ({ x: cellCenterX(c.x), y: cellCenterY(c.y), step: c.step }));
    this.flash = scene.add.rectangle(FIELD_X, FIELD_Y, FIELD_SIZE, FIELD_SIZE, 0xfffadc).setOrigin(0).setDepth(DEPTH.flash);
    this.light = scene.add.image(this.x, this.y, 'fx_glow').setBlendMode(ADD).setDepth(DEPTH.glow).setDisplaySize(350, 350);
    this.soot = this.cells.map((cell) => scene.add.image(cell.x, cell.y, 'fx_soot').setDepth(DEPTH.soot)
      .setDisplaySize(cell.step ? 54 : 68, cell.step ? 54 : 68));
    this.embers = scene.add.graphics().setBlendMode(ADD).setDepth(DEPTH.embers);
    this.sparks = scene.add.graphics().setBlendMode(ADD).setDepth(DEPTH.air);
    this.smoke = Array.from({ length: SMOKE }, () => scene.add.image(0, 0, 'fx_smoke').setDepth(DEPTH.air).setVisible(false));
    this.draw(now);
  }

  // Каждый кадр экрана. Возвращает false, когда от взрыва ничего не осталось.
  draw(now) {
    const s = now - this.start;
    if (s >= BLAST_TIME) return false;
    this.flash.setAlpha(s < 0.09 ? FLASH * (1 - s / 0.09) : 0);
    this.light.setAlpha(0.55 * Math.exp(-s * 7) + (s < FLAME_TIME ? 0.16 * (1 - s / FLAME_TIME) : 0));
    const soot = smooth(s / 0.12) * (1 - smooth((s - (BLAST_TIME - 0.5)) / 0.5));
    this.soot.forEach((image, i) => image.setAlpha(soot * SOOT[this.cells[i].step]));
    this.drawSparks(s);
    this.drawEmbers(s);
    this.drawSmoke(s);
    return true;
  }

  // Искры летят по дуге, чаще вдоль коридоров, падают и отскакивают; за каждой — короткий след.
  drawSparks(s) {
    const g = this.sparks.clear();
    for (let i = 0; i < SPARKS; i++) {
      const id = this.seed + 100 + i, life = 0.45 + 0.9 * rnd(id, 6);
      if (s >= life) continue;
      const [dx, dy] = AXES[Math.floor(rnd(id, 2) * AXES.length)];
      const angle = rnd(id, 1) < 0.65 ? Math.atan2(dy, dx) + (rnd(id, 3) - 0.5) * 0.4 : rnd(id, 3) * Math.PI * 2;
      const speed = 0.9 * (170 + 380 * rnd(id, 4)), lift = 40 + 130 * rnd(id, 5);
      const at = (time) => {
        const far = speed / 4.5 * (1 - Math.exp(-4.5 * time));
        return [this.x + Math.cos(angle) * far, this.y + Math.sin(angle) * far - hop(time, lift)];
      };
      const [x, y] = at(s), [px, py] = at(Math.max(0, s - 0.016));
      const heat = 1 - s / life;
      g.lineStyle(1.1, heatColor(0.35 + 0.65 * heat), 0.4 + 0.6 * heat).lineBetween(px, py, x, y);
      glint(g, x, y, 3.4, heatColor(0.5 + 0.5 * heat), 0.8 * heat);
    }
  }

  // Угольки тлеют на полу после огня.
  drawEmbers(s) {
    const g = this.embers.clear();
    if (s < 0.15) return;
    for (let i = 0; i < EMBERS; i++) {
      const id = this.seed + 250 + i, end = 0.9 + 1.3 * rnd(id, 4);
      if (s >= end) continue;
      const cell = this.cells[Math.floor(rnd(id, 1) * this.cells.length)], k = 1 - s / end;
      glint(g, cell.x + (rnd(id, 2) - 0.5) * 42, cell.y + (rnd(id, 3) - 0.5) * 42, 2.8,
        heatColor(0.3 + 0.5 * k), k * (0.6 + 0.4 * Math.sin(s * 14 + id)));
    }
  }

  // Клубы дыма поднимаются над сгоревшими клетками (чаще над центром), растут и тают.
  drawSmoke(s) {
    this.smoke.forEach((puff, i) => {
      const id = this.seed + 200 + i, age = s - (0.12 + 0.7 * rnd(id, 3)), life = 0.8 + 0.6 * rnd(id, 4);
      puff.setVisible(age >= 0 && age < life);
      if (!puff.visible) return;
      const cell = rnd(id, 1) < 0.4 ? this.cells[0] : this.cells[Math.floor(rnd(id, 2) * this.cells.length)];
      const u = age / life, size = 2 * (9 + 15 * u);
      puff.setPosition(cell.x + (rnd(id, 5) - 0.5) * 30 + 5 * Math.sin(age * 2.5 + id),
        cell.y + (rnd(id, 6) - 0.5) * 26 - 6 - 30 * age)
        .setDisplaySize(size, size).setAlpha(0.72 * Math.min(1, u * 5) * (1 - u));
    });
  }

  destroy() {
    for (const part of [this.flash, this.light, this.embers, this.sparks, ...this.soot, ...this.smoke]) part.destroy();
  }
}

// Обломки сгоревшей стены: летят высоко, падают, отскакивают и остаются лежать, пока не растают.
export class WallChunks {
  // event — событие «wall_destroyed».
  constructor(scene, event, now) {
    this.start = now;
    this.x = cellCenterX(event.x);
    this.y = cellCenterY(event.y);
    this.seed = 50 + event.x * 31 + event.y * 17;
    this.g = scene.add.graphics().setDepth(DEPTH.explosion + 0.1);
  }

  draw(now) {
    const s = now - this.start, fade = 1 - smooth((s - 1.5) / 0.7), g = this.g.clear();
    if (fade <= 0) return false;
    for (let i = 0; i < CHUNKS; i++) {
      const id = this.seed + i, angle = rnd(id, 1) * Math.PI * 2;
      const far = (60 + 150 * rnd(id, 2)) / 3 * (1 - Math.exp(-3 * s)), high = hop(s, 110 + 120 * rnd(id, 3));
      const x = this.x + Math.cos(angle) * far, y = this.y + Math.sin(angle) * far, size = 2.6 + 2.6 * rnd(id, 4);
      g.fillStyle(0x000000, 0.3 * fade * smooth((s - 0.45) / 0.3)).fillEllipse(x, y + 1.5, size * 1.6, size * 0.7);
      g.save();
      g.translateCanvas(x, y - high);
      g.rotateCanvas(rnd(id, 5) * 6 + (high > 0 ? s * (7 + 9 * rnd(id, 6)) : 0));
      g.fillStyle(BRICKS[i % BRICKS.length], fade).fillRect(-size / 2, -size * 0.36, size, size * 0.72);
      g.lineStyle(0.8, INK, fade).strokeRect(-size / 2, -size * 0.36, size, size * 0.72);
      g.restore();
    }
    return true;
  }

  destroy() {
    this.g.destroy();
  }
}
