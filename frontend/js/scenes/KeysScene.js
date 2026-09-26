// Настройка клавиш. Выбрать клетку — мышью или стрелками + Enter, затем нажать новую клавишу.
// Если клавиша уже занята, две клавиши меняются местами. Всё сохраняется сразу.

import { FIELD_SIZE, FIELD_X, textStyle } from '../layout.js';
import { addButton, drawBackdrop } from '../backdrop.js';
import {
  ACTIONS, ACTION_NAMES, DEFAULT_BINDINGS, RESERVED, keyLabel, loadBindings, saveBindings,
} from '../keybindings.js';

const CENTER_X = FIELD_X + FIELD_SIZE / 2;
const COLUMNS = [CENTER_X - 10, CENTER_X + 190];
const ROW_Y = (row) => 200 + row * 62;

export class KeysScene extends Phaser.Scene {
  constructor() {
    super('keys');
  }

  create() {
    this.bindings = loadBindings();
    this.selected = { set: 0, row: 0 };
    this.capturing = false;
    this.handled = new WeakSet();

    drawBackdrop(this);
    this.add.rectangle(CENTER_X, 370, 660, 640, 0x000000, 0.75).setStrokeStyle(2, 0x0000c8);
    this.add.text(CENTER_X, 80, 'Настройка клавиш', textStyle(38, '#ffcc00')).setOrigin(0.5);
    ['Иван', 'Колян'].forEach((name, set) =>
      this.add.text(COLUMNS[set], 145, name, textStyle(26, '#0096ff')).setOrigin(0.5));

    this.cells = ACTIONS.map((action, row) => {
      this.add.text(CENTER_X - 290, ROW_Y(row), ACTION_NAMES[action], textStyle(24, '#ffffff')).setOrigin(0, 0.5);
      return COLUMNS.map((x, set) => {
        const box = this.add.rectangle(x, ROW_Y(row), 170, 46, 0x15093a).setStrokeStyle(2, 0x3355aa)
          .setInteractive({ useHandCursor: true });
        const label = this.add.text(x, ROW_Y(row), '', textStyle(22, '#ffffff')).setOrigin(0.5);
        box.on('pointerdown', () => {
          this.selected = { set, row };
          this.startCapture();
        });
        return { box, label };
      });
    });

    this.hint = this.add.text(CENTER_X, 530, '', textStyle(19, '#cccccc', { align: 'center' })).setOrigin(0.5);
    this.add.text(CENTER_X, 568, 'Заняты всегда:  P — пауза,  Esc — меню,  M — звук,  − / + — громкость',
      textStyle(17, '#8888aa')).setOrigin(0.5);
    addButton(this, CENTER_X - 140, 620, 'Сбросить (R)', () => this.reset(), 24);
    addButton(this, CENTER_X + 140, 620, 'Готово (Esc)', () => this.done(), 24);

    this.input.keyboard.on('keydown', (event) => this.onKey(event));
    this.refresh();
  }

  onKey(event) {
    // Phaser иногда передаёт одно и то же нажатие дважды — второй раз пропускаем.
    if (event.repeat || this.handled.has(event)) return;
    this.handled.add(event);
    if (this.capturing) {
      event.preventDefault();
      if (event.code === 'Escape') {
        this.capturing = false;
      } else if (RESERVED.includes(event.code)) {
        this.message = `${keyLabel(event.code)} занята: P — пауза, Esc — выход, M — звук, −/+ — громкость`;
      } else {
        this.assign(event.code);
      }
      this.refresh();
      return;
    }
    const { set, row } = this.selected;
    const moves = {
      ArrowUp: [set, (row + ACTIONS.length - 1) % ACTIONS.length],
      ArrowDown: [set, (row + 1) % ACTIONS.length],
      ArrowLeft: [0, row],
      ArrowRight: [1, row],
    };
    if (moves[event.code]) {
      event.preventDefault();
      [this.selected.set, this.selected.row] = moves[event.code];
      this.refresh();
    } else if (event.code === 'Enter' || event.code === 'NumpadEnter' || event.code === 'Space') {
      event.preventDefault();
      this.startCapture();
    } else if (event.code === 'KeyR') {
      this.reset();
    } else if (event.code === 'Escape') {
      this.done();
    }
  }

  startCapture() {
    this.capturing = true;
    this.message = '';
    this.refresh();
  }

  assign(code) {
    const { set, row } = this.selected;
    const action = ACTIONS[row];
    const old = this.bindings[set][action];
    // Клавиша уже у кого-то есть — отдаём тому нашу старую.
    this.bindings.forEach((keys) => {
      for (const other of ACTIONS) if (keys[other] === code) keys[other] = old;
    });
    this.bindings[set][action] = code;
    saveBindings(this.bindings);
    this.capturing = false;
    this.message = '';
  }

  reset() {
    this.bindings = structuredClone(DEFAULT_BINDINGS);
    saveBindings(this.bindings);
    this.capturing = false;
    this.message = 'Вернули клавиши по умолчанию';
    this.refresh();
  }

  done() {
    this.scene.start('menu');
  }

  refresh() {
    this.cells.forEach((row, r) => row.forEach((cell, set) => {
      const isSelected = this.selected.set === set && this.selected.row === r;
      const waiting = isSelected && this.capturing;
      cell.label.setText(waiting ? 'нажмите…' : keyLabel(this.bindings[set][ACTIONS[r]]));
      cell.label.setColor(waiting ? '#ffcc00' : '#ffffff');
      cell.box.setStrokeStyle(isSelected ? 3 : 2, isSelected ? 0xffcc00 : 0x3355aa);
    }));
    this.hint.setText(this.message || (this.capturing
      ? 'Нажмите новую клавишу (Esc — отмена)'
      : 'Выберите действие мышью или стрелками и нажмите Enter'));
  }
}
