// Клавиатура во время игры. Клавиши берутся из настроек (keybindings.js).
// В игре на одного обе раскладки управляют Иваном. В игре по сети обе раскладки
// управляют своим героем (seat): каждый играет на своём ноутбуке.

import { loadBindings } from './keybindings.js';

const DIRECTIONS = ['left', 'right', 'up', 'down'];

export class Controls {
  constructor(scene, players, net, { onPause, onQuit }, seat = null) {
    this.net = net;
    this.players = players;
    this.seat = seat;
    this.bindings = loadBindings();
    // Для каждого игрока — стопка зажатых направлений. Идём туда, что нажато последним;
    // отпустили — возвращаемся к предыдущему (как savemove в оригинале).
    this.held = [[], []];
    this.keyboard = scene.input.keyboard;
    this.keyboard.addCapture('SPACE,UP,DOWN,LEFT,RIGHT,DELETE,ENTER,TAB'); // не прокручивать страницу

    this.onDown = (event) => {
      if (event.repeat) return;
      if (event.code === 'KeyP' || event.code === 'Pause') return onPause();
      if (event.code === 'Escape') return onQuit();
      this.bindings.forEach((keys, set) => {
        const player = this.playerFor(set);
        const dir = DIRECTIONS.find((d) => keys[d] === event.code);
        if (dir) this.press(player, dir);
        if (keys.bomb === event.code) this.net.send({ type: 'bomb', player });
      });
    };
    this.onUp = (event) => {
      this.bindings.forEach((keys, set) => {
        const dir = DIRECTIONS.find((d) => keys[d] === event.code);
        if (dir) this.release(this.playerFor(set), dir);
      });
    };
    this.onBlur = () => this.releaseAll();

    this.keyboard.on('keydown', this.onDown);
    this.keyboard.on('keyup', this.onUp);
    window.addEventListener('blur', this.onBlur);
  }

  playerFor(set) {
    if (this.seat !== null) return this.seat;
    return this.players === 1 ? 0 : set;
  }

  press(player, dir) {
    const stack = this.held[player];
    const before = stack.join();
    const index = stack.indexOf(dir);
    if (index >= 0) stack.splice(index, 1);
    stack.push(dir);
    if (stack.join() !== before) this.sendDir(player);
  }

  release(player, dir) {
    const stack = this.held[player];
    const index = stack.indexOf(dir);
    if (index >= 0) {
      stack.splice(index, 1);
      this.sendDir(player);
    }
  }

  releaseAll() {
    const mine = this.seat !== null ? [this.seat] : [...Array(this.players).keys()];
    for (const player of mine) {
      this.held[player] = [];
      this.sendDir(player);
    }
  }

  // Отправляем последнюю зажатую стрелку и предыдущую: если свернул раньше прохода,
  // сервер поведёт героя по предыдущей, пока поворот не станет возможен.
  sendDir(player) {
    const stack = this.held[player];
    this.net.send({ type: 'dir', player, dir: stack.at(-1) ?? null, alt: stack.at(-2) ?? null });
  }

  destroy() {
    this.keyboard.off('keydown', this.onDown);
    this.keyboard.off('keyup', this.onUp);
    window.removeEventListener('blur', this.onBlur);
  }
}
