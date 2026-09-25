// Загрузка картинок и описание анимаций. Картинки сделаны из старых BMP скриптом
// tools/convert_assets.py; кадры в полосах идут с шагом «ширина + 1 пиксель разделителя».

import { WIDTH, HEIGHT, textStyle } from '../layout.js';

const IMAGES = [
  'gameover', 'panel', 'level_box', 'stats1', 'stats2', 'face1', 'face2',
  'pause', 'ready', 'floor', 'walls', 'pillars', 'flame_near', 'flame_far',
  'item_door', 'item_chest', 'item_bomb', 'item_life', 'item_death',
  'item_bag', 'item_bigbag', 'item_gems', 'item_legacy',
];

const SHEETS = {
  player1: [49, 49, 1], player2: [49, 49, 1],
  death1: [49, 49, 1], death2: [49, 49, 1],
  superdeath1: [64, 64, 1], superdeath2: [64, 64, 1],
  bomb1: [49, 49, 1], bomb2: [49, 49, 1],
  explosion: [147, 147, 1],
  enemies: [49, 49, 0],
};

const range = (from, to) => {
  const step = from <= to ? 1 : -1;
  const frames = [];
  for (let i = from; i !== to + step; i += step) frames.push(i);
  return frames;
};

export class BootScene extends Phaser.Scene {
  constructor() {
    super('boot');
  }

  preload() {
    const label = this.add.text(WIDTH / 2, HEIGHT / 2, 'Загрузка…', textStyle(28, '#ffffff')).setOrigin(0.5);
    this.load.on('progress', (p) => label.setText(`Загрузка… ${Math.round(p * 100)}%`));
    for (const name of IMAGES) this.load.image(name, `assets/${name}.png`);
    for (const [name, [frameWidth, frameHeight, spacing]] of Object.entries(SHEETS)) {
      this.load.spritesheet(name, `assets/${name}.png`, { frameWidth, frameHeight, spacing });
    }
  }

  create() {
    const make = (key, sheet, frames, frameRate, extra = {}) =>
      this.anims.create({
        key,
        frames: this.anims.generateFrameNumbers(sheet, { frames }),
        frameRate,
        ...extra,
      });

    for (const n of [1, 2]) {
      // Обычная смерть — в сторону, куда смотрел герой (кадры из Player::NextStep).
      make(`death${n}-left`, `death${n}`, range(0, 14), 10);
      make(`death${n}-right`, `death${n}`, range(29, 15), 10);
      make(`death${n}-up`, `death${n}`, range(30, 43), 10);
      make(`death${n}-down`, `death${n}`, range(44, 57), 10);
      // «Суперсмерть» — героя отбрасывает взрывом назад.
      make(`super${n}-left`, `superdeath${n}`, range(0, 10), 8);   // смотрел влево — летит вправо
      make(`super${n}-right`, `superdeath${n}`, range(21, 11), 8); // смотрел вправо — летит влево
      make(`super${n}-up`, `superdeath${n}`, range(22, 32), 8);    // смотрел вверх — летит вниз
      make(`super${n}-down`, `superdeath${n}`, range(33, 43), 8);  // смотрел вниз — летит вверх
    }
    make('explosion', 'explosion', range(5, 18), 18, { hideOnComplete: true });
    for (let tier = 0; tier < 4; tier++) {
      make(`enemy${tier}`, 'enemies', range(tier * 4, tier * 4 + 3), 6, { repeat: -1 });
    }
    this.scene.start('menu');
  }
}
