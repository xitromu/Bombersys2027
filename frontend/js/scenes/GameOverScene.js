// Экран GAME OVER: результат партии и таблица рекордов (хранится на сервере).

import { WIDTH, textStyle } from '../layout.js';
import { sound } from '../audio/sound.js';

export class GameOverScene extends Phaser.Scene {
  constructor() {
    super('gameover');
  }

  init(data) {
    this.result = data;
  }

  create() {
    const { level, score, records = [] } = this.result;
    if (score > 0 && records.some((r) => r.score === score && r.level === level)) {
      this.time.delayedCall(1500, () => sound.say('female_new_highscore'));  // попали в таблицу рекордов
    }
    this.add.image(0, 0, 'gameover').setOrigin(0);

    this.add.rectangle(40, 30, 420, 60 + 28 * Math.max(records.length, 1) + 70, 0x000000, 0.7)
      .setOrigin(0).setStrokeStyle(2, 0xc80000);
    this.add.text(60, 44, `Уровень ${level},  очков: ${score}`, textStyle(24, '#ffcc00'));
    this.add.text(60, 84, 'Рекорды', textStyle(22, '#ffffff'));
    records.forEach((r, i) => {
      const y = 116 + i * 28;
      const style = textStyle(18, '#dddddd');
      this.add.text(60, y, `${i + 1}. ${r.names}`, style);
      this.add.text(300, y, `ур. ${r.level}`, style);
      this.add.text(440, y, String(r.score), style).setOrigin(1, 0);
    });

    const hint = this.add.text(WIDTH / 2, 700, 'Нажмите любую клавишу', textStyle(22, '#ffffff'))
      .setOrigin(0.5).setAlpha(0);
    // Небольшая пауза, чтобы случайно не пролистать экран клавишей из игры.
    this.time.delayedCall(1200, () => {
      hint.setAlpha(1);
      this.input.keyboard.once('keydown', () => this.scene.start('menu'));
    });
  }
}
