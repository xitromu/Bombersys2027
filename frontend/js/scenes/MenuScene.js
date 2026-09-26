// Главное меню: своя игра на одного или двоих, игра по сети, настройка клавиш.

import { FIELD_SIZE, FIELD_X, HEIGHT, textStyle } from '../layout.js';
import { addButton, drawBackdrop, drawTitle } from '../backdrop.js';
import { ACTIONS, keyLabel, loadBindings } from '../keybindings.js';
import { EnemyEyes } from '../enemyEyes.js';
import { sound } from '../audio/sound.js';
import { gameVersion } from '../version.js';

const CENTER_X = FIELD_X + FIELD_SIZE / 2;

export class MenuScene extends Phaser.Scene {
  constructor() {
    super('menu');
  }

  create() {
    const net = this.registry.get('net');
    sound.music('menu');
    drawBackdrop(this);
    drawTitle(this);

    // Немного жизни на фоне: взрыв и пара врагов.
    const boom = this.add.sprite(CENTER_X, 205, 'explosion').setAlpha(0.9);
    const replay = () => boom.setVisible(true).play('explosion');
    replay();
    this.time.addEvent({ delay: 2200, loop: true, callback: replay });
    // Зелёный спокойно озирается, красный уже «заметил» игрока.
    this.decor = [[150, 0, false], [590, 2, true]].map(([x, tier, alert]) => {
      const sprite = this.add.sprite(x, 205, 'enemies').play(`enemy${tier}`).setScale(1.4);
      const eyes = new EnemyEyes(this);
      eyes.setAlert(alert);
      return { sprite, eyes };
    });

    this.add.rectangle(CENTER_X, 480, 600, 420, 0x000000, 0.7).setStrokeStyle(2, 0x0000c8);
    const start = (players) => {
      if (net.connected) this.scene.start('game', { players });
    };
    const network = (mode) => {
      if (net.connected) this.scene.start('net', { mode });
    };
    addButton(this, CENTER_X, 300, '1  —  играть одному', () => start(1), 28);
    addButton(this, CENTER_X, 342, '2  —  вдвоём за одной клавиатурой', () => start(2), 28);
    addButton(this, CENTER_X, 384, '3  —  создать игру по сети', () => network('host'), 28);
    addButton(this, CENTER_X, 426, '4  —  присоединиться к игре по сети', () => network('join'), 28);
    addButton(this, CENTER_X, 468, 'K  —  настроить клавиши', () => this.scene.start('keys'), 28);

    const keys = loadBindings();
    const describe = (set) => {
      const move = ACTIONS.slice(0, 4).map((a) => keyLabel(set[a])).join(' ');
      return `ходить: ${move}    бомба: ${keyLabel(set.bomb)}`;
    };
    this.add.text(CENTER_X, 510,
      `Иван —  ${describe(keys[0])}\nКолян —  ${describe(keys[1])}\n\nP — пауза,   Esc — в меню,   M — звук,   − / + — громкость`,
      textStyle(19, '#cccccc', { align: 'center', lineSpacing: 6 })).setOrigin(0.5, 0);

    const status = this.add.text(CENTER_X, 700, '', textStyle(20, '#ff6666')).setOrigin(0.5);

    // Номер версии внизу — чтобы сразу видеть, какая версия открыта (нет его — браузер показывает старую).
    const versionText = this.add.text(10, HEIGHT - 8, '', textStyle(15, '#777799')).setOrigin(0, 1);
    gameVersion.then((version) => {
      if (version && versionText.active) versionText.setText(`версия ${version}`);
    });
    const unsubscribe = net.onStatus((ok) => status.setText(ok ? '' : 'Нет связи с сервером — запущен ли он?'));
    this.events.once('shutdown', unsubscribe);

    this.input.keyboard.on('keydown', (event) => {
      const players = { Digit1: 1, Numpad1: 1, Digit2: 2, Numpad2: 2 }[event.code];
      if (players) start(players);
      const mode = { Digit3: 'host', Numpad3: 'host', Digit4: 'join', Numpad4: 'join' }[event.code];
      if (mode) network(mode);
      if (event.code === 'KeyK') this.scene.start('keys');
    });
  }

  update(time) {
    const angle = time / 900;
    this.decor[0].eyes.follow(this.decor[0].sprite, [Math.cos(angle), Math.sin(angle * 0.7) * 0.6]);
    this.decor[1].eyes.follow(this.decor[1].sprite, [-1, 0.3]);
  }
}
