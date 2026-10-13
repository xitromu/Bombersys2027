// Экран GAME OVER в оформлении «блиндаж»: дощатая стена, полоса пола, на которой всё кончилось,
// и листок с результатом партии и таблицей рекордов (хранится на сервере).

import { CELL, GRID, HEIGHT, WIDTH, textStyle } from '../layout.js';
import { PAPER, planks, points, sheet } from '../bunker.js';
import { addCanvas, canvasTexture } from '../canvasTexture.js';
import { drawChomper } from '../enemyView.js';
import { HERO } from '../heroMeta.js';
import { sound } from '../audio/sound.js';

const STRIP_X = (WIDTH - GRID * CELL) / 2;  // полоса пола: три ряда клеток во всю ширину поля
const STRIP_Y = 215;
const MID = WIDTH / 2;
const SHEET = [MID - 300, 395, 600, 290];   // листок с результатом
// Погибшие на полосе: герой, клетка, вид гибели и куда смотрел.
const BODIES = [[1, 5, 'thrown', 'right'], [2, 9, 'rocket', 'left']];
// Твари над ними: клетка, ступень (цвет), куда смотрит.
const GHOSTS = [[3.3, 0, 1], [6.9, 2, 1], [7.6, 1, -1], [11.2, 3, -1], [12.4, 0, -1]];

function oval(g, x, y, rx, ry, color) {
  g.fillStyle = color;
  g.beginPath();
  g.ellipse(x, y, rx, ry, 0, 0, Math.PI * 2);
  g.fill();
}

// Неподвижная часть экрана: стена, полоса пола с погибшими и тварями, пустой листок.
function drawWall(g, scene, players) {
  const image = (key) => scene.textures.get(key).getSourceImage();
  planks(g, WIDTH, HEIGHT);
  g.fillStyle = 'rgba(0, 0, 0, 0.5)';
  g.fillRect(STRIP_X - 4, STRIP_Y - 4, GRID * CELL + 8, 3 * CELL + 8);
  g.drawImage(image('floor'), 0, 0, GRID * CELL, 3 * CELL, STRIP_X, STRIP_Y, GRID * CELL, 3 * CELL);

  const y = STRIP_Y + 1.5 * CELL;
  const frame = HERO.death.frame;
  for (const [n, cell, kind, facing] of BODIES.slice(0, players)) {
    const x = STRIP_X + cell * CELL + CELL / 2;
    oval(g, x, y + 2, 19, 13, '#560808');                    // лужа крови
    oval(g, x, y + 2, 16, 10.5, '#8c0f0f');
    const table = HERO.death.kinds[kind];                     // последний кадр гибели — герой лежит
    g.drawImage(image(`hero${n}_death`),
      (table.frames.length - 1) * frame, (table.row + HERO.dirs.indexOf(facing)) * frame, frame, frame,
      x - frame * HERO.death.origin[0], y - frame * HERO.death.origin[1] + 5, frame, frame);
  }
  GHOSTS.forEach(([cell, tier, look], i) => {
    g.save();
    g.translate(STRIP_X + cell * CELL, y + (i % 2 ? -22 : 20));
    // сытые: пасти разинуты по-разному, смотрят на погибших
    drawChomper(g, tier, { walked: i * 5, look: [look, 0.3], open: 0.35 + 0.15 * (i % 3) });
    g.restore();
  });
  sheet(g, ...SHEET);
}

export class GameOverScene extends Phaser.Scene {
  constructor() {
    super('gameover');
  }

  init(data) {
    this.result = data;
  }

  create() {
    const { level, score, records = [], players = 2 } = this.result;
    const mine = score > 0 ? records.findIndex((r) => r.score === score && r.level === level) : -1;
    if (mine >= 0) this.time.delayedCall(1500, () => sound.say('female_new_highscore'));  // попали в таблицу рекордов

    addCanvas(this, 0, 0, canvasTexture(this, `bunker_over${players}`, WIDTH, HEIGHT, (g) => drawWall(g, this, players)));
    this.add.text(MID, 120, 'GAME OVER', textStyle(118, '#e02424', {
      fontStyle: 'bold', stroke: '#000000', strokeThickness: 10,
    })).setOrigin(0.5);

    const bold = { fontStyle: 'bold' };
    this.add.text(MID, 432, `Уровень ${level}        Очки: ${points(score)}`, textStyle(28, PAPER.accent, bold)).setOrigin(0.5);
    this.add.text(MID, 478, 'Лучшие походы', textStyle(20, PAPER.dim)).setOrigin(0.5);
    // Рекордов бывает до десяти: чем их больше, тем плотнее и мельче строки — чтобы уместились на листке.
    const step = Math.min(34, 176 / Math.max(records.length, 1));
    const size = Math.min(22, Math.round(step * 0.82));
    records.forEach((r, i) => {
      const y = 499 + step * (i + 0.5);
      const style = textStyle(size, i === mine ? PAPER.accent : PAPER.text, i === mine ? bold : {});
      this.add.text(MID - 250, y, `${i + 1}.`, style).setOrigin(0, 0.5);
      this.add.text(MID - 210, y, r.names, style).setOrigin(0, 0.5);
      this.add.text(MID + 60, y, `уровень ${r.level}`, style).setOrigin(0, 0.5);
      this.add.text(MID + 250, y, points(r.score), style).setOrigin(1, 0.5);
    });

    const hint = this.add.text(MID, 712, 'Любая клавиша — в меню', textStyle(20, PAPER.light)).setOrigin(0.5).setAlpha(0);
    // Небольшая пауза, чтобы случайно не пролистать экран клавишей из игры.
    this.time.delayedCall(1200, () => {
      hint.setAlpha(1);
      this.input.keyboard.once('keydown', () => this.scene.start('menu'));
    });
  }
}
