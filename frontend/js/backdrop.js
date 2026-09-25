// Общий фон для меню и настроек: затемнённое игровое поле и правая панель с героями —
// вместо старой заставки (кадр из фильма «Мумия» убран).

import { CELL, FIELD_SIZE, FIELD_X, FIELD_Y, GRID, PANEL_X, textStyle } from './layout.js';

export function drawBackdrop(scene) {
  scene.add.graphics().lineStyle(5, 0x0000c8).strokeRect(1, 1, FIELD_SIZE + 5, FIELD_SIZE + 5);
  scene.add.image(FIELD_X, FIELD_Y, 'floor').setOrigin(0).setTint(0x666666);
  for (let y = 1; y < GRID; y += 2) {
    for (let x = 1; x < GRID; x += 2) {
      scene.add.image(FIELD_X, FIELD_Y, 'pillars').setOrigin(0)
        .setCrop(x * CELL, y * CELL, CELL, CELL).setTint(0x777777);
    }
  }

  scene.add.image(PANEL_X, 0, 'panel').setOrigin(0);
  scene.add.image(760, 10, 'level_box').setOrigin(0);
  scene.add.text(880, 16, 'BOMBERSYS', textStyle(26, '#9b0000')).setOrigin(0.5, 0);
  scene.add.text(880, 80, 'возрождение\nигры 2005 года', textStyle(20, '#15093a', { align: 'center' })).setOrigin(0.5, 0);
  ['Иван', 'Колян'].forEach((name, i) => {
    const y = 405 + 170 * i;
    scene.add.image(760, y, `face${i + 1}`).setOrigin(0);
    scene.add.image(890, y, `stats${i + 1}`).setOrigin(0);
    scene.add.text(814, y + 137, name, textStyle(18, '#0096ff')).setOrigin(0.5);
    scene.add.text(944, y + 137, '0', textStyle(18, '#0096ff')).setOrigin(0.5);
    scene.add.text(975, y + 40, '5', textStyle(32, '#0096ff')).setOrigin(0.5);
    scene.add.text(975, y + 90, '3', textStyle(32, '#0096ff')).setOrigin(0.5);
  });
}

export function drawTitle(scene, y = 90) {
  return scene.add.text(FIELD_X + FIELD_SIZE / 2, y, 'BOMBERMAN', {
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
