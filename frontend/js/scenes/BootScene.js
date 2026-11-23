// Загрузка картинок и описание анимаций. Картинки сделаны из старых BMP скриптом
// tools/convert_assets.py; кадры в полосах идут с шагом «ширина + 1 пиксель разделителя».
// Герои — новые: их листы собирает tools/build_hero.py, а рисует heroView.js. Листы hero<N>_headless —
// те же кадры гибели, но без головы (её съела тварь): собирает mockups/hero/build_headless.py.
// Твари, змея, бонусы, панель и надписи поверх поля рисуются на холсте — картинок для них нет.

import { HEIGHT, WIDTH, textStyle } from '../layout.js';
import { createBlastTextures } from '../blastView.js';
import { createItemTextures } from '../itemView.js';
import { createBonesTextures } from '../bonesView.js';
import { HERO } from '../heroMeta.js';

const IMAGES = [
  'photo1', 'photo2',                                               // фотографии героев для панели
  'floor', 'walls', 'pillars', 'flame_near', 'flame_far',
];

const SHEETS = {
  hero1: [HERO.run.frame, HERO.run.frame, 0], hero2: [HERO.run.frame, HERO.run.frame, 0],
  hero1_death: [HERO.death.frame, HERO.death.frame, 0], hero2_death: [HERO.death.frame, HERO.death.frame, 0],
  hero1_headless: [HERO.death.frame, HERO.death.frame, 0], hero2_headless: [HERO.death.frame, HERO.death.frame, 0],
  hero1_half: [HERO.death.frame, HERO.death.frame, 0], hero2_half: [HERO.death.frame, HERO.death.frame, 0],
  bomb1: [49, 49, 1], bomb2: [49, 49, 1],
  explosion: [147, 147, 1],
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

    make('explosion', 'explosion', range(5, 18), 18, { hideOnComplete: true });
    createBlastTextures(this);
    createItemTextures(this);
    createBonesTextures(this);
    this.scene.start('menu');
  }
}
