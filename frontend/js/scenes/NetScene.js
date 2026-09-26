// Игра по сети: создать партию и ждать второго или присоединиться к уже созданной.
// Хозяин — Иван, гость — Колян. Второй ноутбук открывает в браузере адрес хозяина
// (его показывает этот экран) и нажимает «4 — присоединиться».

import { FIELD_SIZE, FIELD_X, textStyle } from '../layout.js';
import { drawBackdrop, drawTitle } from '../backdrop.js';

const CENTER_X = FIELD_X + FIELD_SIZE / 2;

export class NetScene extends Phaser.Scene {
  constructor() {
    super('net');
  }

  init(data) {
    this.mode = data.mode;  // 'host' или 'join'
  }

  create() {
    const net = this.registry.get('net');
    drawBackdrop(this);
    drawTitle(this);
    this.add.rectangle(CENTER_X, 470, 640, 400, 0x000000, 0.75).setStrokeStyle(2, 0x0000c8);

    const title = this.add.text(CENTER_X, 300, '', textStyle(28, '#ffcc00')).setOrigin(0.5);
    const body = this.add.text(CENTER_X, 340, '', textStyle(20, '#ffffff', { align: 'center', lineSpacing: 8, wordWrap: { width: 600 } }))
      .setOrigin(0.5, 0);
    this.add.text(CENTER_X, 640, 'Esc — назад в меню', textStyle(18, '#aaaaaa')).setOrigin(0.5);

    if (this.mode === 'host') {
      title.setText('Ждём второго игрока…');
      body.setText('Создаём игру…');
    } else {
      title.setText('Подключаемся…');
    }

    const offMessage = net.onMessage((message) => {
      if (message.type === 'hosting') {
        const [main, ...other] = message.urls;
        body.setText(main
          ? `На втором ноутбуке (в той же Wi-Fi) откройте в браузере:\n\n${main}\n\nи нажмите «4 — присоединиться».\nВы — Иван, второй игрок — Колян.`
            + (other.length ? `\n\nЕсли не открывается, попробуйте: ${other.join(',  ')}` : '')
            + '\n\nНе подключается? Windows должна разрешить BOMBERSYS доступ к сети,'
            + ' а сеть — быть «частной». VPN на время игры лучше выключить.'
          : 'Этот компьютер не подключён к домашней сети — второму игроку не к чему подключиться.');
        body.setStyle({ fontSize: '18px' });
      } else if (message.type === 'joined') {
        this.scene.start('game', { players: 2, seat: message.seat });
      } else if (message.type === 'error') {
        title.setText('Не получилось');
        body.setText(`${message.text}.\n\nПусть первый игрок выберет в меню «3 — создать игру по сети», потом нажмите «4» ещё раз.`);
      }
    });
    const offStatus = net.onStatus((ok) => {
      if (ok) net.send({ type: this.mode === 'host' ? 'host' : 'join' });
      else body.setText('Нет связи с сервером');
    });
    this.events.once('shutdown', () => {
      offMessage();
      offStatus();
    });

    this.input.keyboard.on('keydown-ESC', () => {
      net.send({ type: 'quit' });
      this.scene.start('menu');
    });
  }
}
