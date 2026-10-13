// Общий фон для меню и настроек: затемнённое игровое поле и правая панель с героями —
// вместо старой заставки (кадр из фильма «Мумия» убран).

import { addPanel, count } from './bunker.js';
import { CELL, FIELD_SIZE, FIELD_X, FIELD_Y, GRID, textStyle } from './layout.js';
import { START_HAIKU } from './texts.js';

export function drawBackdrop(scene) {
  scene.add.graphics().lineStyle(5, 0x0000c8).strokeRect(1, 1, FIELD_SIZE + 5, FIELD_SIZE + 5);
  scene.add.image(FIELD_X, FIELD_Y, 'floor').setOrigin(0).setTint(0x666666);
  for (let y = 1; y < GRID; y += 2) {
    for (let x = 1; x < GRID; x += 2) {
      scene.add.image(FIELD_X, FIELD_Y, 'pillars').setOrigin(0)
        .setCrop(x * CELL, y * CELL, CELL, CELL).setTint(0x777777);
    }
  }

  const panel = addPanel(scene);                    // та же панель «блиндаж», что в игре
  panel.title.setText('BOMBERSYS');
  panel.line1.setText('возрождение');
  panel.line2.setText('игры 2005 года');
  panel.noteTitle.setText(START_HAIKU.title);
  panel.note.setText(START_HAIKU.text);
  ['Иван', 'Игорь'].forEach((name, i) => {
    const hero = panel.heroes[i];
    hero.name.setText(name);
    hero.score.setText('0');
    hero.lives.setText(count(5));
    hero.bombs.setText(count(3));
  });
}

export function drawTitle(scene, y = 90, text = 'BOMBERMAN') {
  return scene.add.text(FIELD_X + FIELD_SIZE / 2, y, text, {
    fontFamily: '"Times New Roman", Georgia, serif',
    fontSize: '96px',
    fontStyle: 'italic',
    color: '#ff1010',
    stroke: '#000000',
    strokeThickness: 8,
    resolution: 2,
  }).setOrigin(0.5);
}

// Кнопка-надпись: подсвечивается под мышью, по щелчку вызывает action.
export function addButton(scene, x, y, label, action, size = 26) {
  const text = scene.add.text(x, y, label, textStyle(size, '#ffffff')).setOrigin(0.5)
    .setInteractive({ useHandCursor: true });
  text.on('pointerover', () => text.setColor('#ffcc00'));
  text.on('pointerout', () => text.setColor('#ffffff'));
  text.on('pointerdown', action);
  return text;
}
