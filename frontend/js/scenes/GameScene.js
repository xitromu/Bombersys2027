// Игровой экран. Сам ничего не решает: 30 раз в секунду получает от сервера
// состояние игры и рисует его. Между получениями плавно «дорисовывает»
// движение (интерполяция), чтобы картинка не дёргалась.

import {
  CELL, DEPTH, FIELD_SIZE, FIELD_X, FIELD_Y, GRID, HEIGHT, PANEL_X, TICK_MS, WIDTH,
  actorDepth, cellCenterX, cellCenterY, cellLeft, cellTop, textStyle,
} from '../layout.js';
import { Controls } from '../controls.js';
import { EnemyEyes } from '../enemyEyes.js';
import { GameAudio } from '../audio/gameAudio.js';
import { sound } from '../audio/sound.js';
import { gameVersion } from '../version.js';
import { CRIES, DEATH_PHRASES, EPIC_PHRASES, HAIKU, START_HAIKU, pick } from '../texts.js';

const HERO_COLORS = ['#66ccff', '#99ff66'];  // Иван, Колян

// Кадры ходьбы в PLAYER1.bmp: влево 0–6, вправо 7–13, вверх 14–20, вниз 21–27.
const IDLE = { left: 0, right: 13, up: 14, down: 21 };
const WALK_BASE = { left: 0, right: 7, up: 14, down: 21 };
// Смещения героя при «суперсмерти» — таблицы SXY и STXY из Player::NextStep.
const SXY = [0, 0, 5, 19, 27, 32, 37, 43, 43, 43, 43, 43];
const STXY = [0, 5, 7, 7, 20, 20, 20, 20, 20, 20, 20, 20];
const SUPER_FRAME_MS = 1000 / 8;

const ITEM_POPUP = {
  door: ['Выход!', '#66ff66'], chest: ['+1000', '#ffcc00'], bag: ['+100', '#ffcc00'],
  bigbag: ['+200', '#ffcc00'], gems: ['+500', '#ffcc00'], legacy: ['+1000', '#ffcc00'],
  bomb: ['+1 бомба', '#66ccff'], life: ['+1 жизнь', '#66ff66'], death: ['Ловушка!', '#ff4444'],
};

export class GameScene extends Phaser.Scene {
  constructor() {
    super('game');
  }

  init(data) {
    this.playerCount = data.players;
    this.seat = data.seat ?? null;   // игра по сети: 0 — я Иван, 1 — я Колян; null — своя игра
  }

  create() {
    this.net = this.registry.get('net');
    this.curr = null;
    this.currAt = 0;
    this.finished = false;
    this.walls = new Map();
    this.items = new Map();
    this.bombs = new Map();
    this.flames = new Map();
    this.enemies = new Map();
    this.audio = new GameAudio();

    this.drawField();
    this.createPlayers();
    this.createHud();

    this.controls = new Controls(this, this.playerCount, this.net, {
      onPause: () => this.net.send({ type: 'pause' }),
      onQuit: () => this.quit(),
    }, this.seat);
    const offState = this.net.onState((state) => this.onState(state));
    const offStatus = this.net.onStatus((ok) => {
      if (!ok && !this.finished) {
        this.finished = true;
        this.message.setText('Связь с сервером потеряна');
        this.time.delayedCall(2000, () => this.scene.start('menu'));
      }
    });
    // игра по сети: второй вышел — партия окончена
    const offMessage = this.net.onMessage((message) => {
      if (message.type === 'left' && !this.finished) {
        this.finished = true;
        this.message.setText(`${message.name} вышел из игры`);
        this.time.delayedCall(2500, () => this.scene.start('menu'));
      }
    });
    this.events.once('shutdown', () => {
      offState();
      offStatus();
      offMessage();
      this.controls.destroy();
      sound.pause(false);  // вышли из игры на паузе — музыка меню не должна остаться приглушённой
    });

    // в игре по сети партию уже запустил сервер, когда пришёл второй игрок
    if (this.seat === null) this.net.send({ type: 'start', players: this.playerCount });
  }

  quit() {
    this.finished = true;
    this.net.send({ type: 'quit' });
    this.scene.start('menu');
  }

  // ------------------------------------------------------------ неподвижные части

  drawField() {
    this.add.graphics().setDepth(DEPTH.floor)
      .lineStyle(5, 0x0000c8).strokeRect(1, 1, FIELD_SIZE + 5, FIELD_SIZE + 5);
    this.add.image(FIELD_X, FIELD_Y, 'floor').setOrigin(0).setDepth(DEPTH.floor);
    for (let y = 1; y < GRID; y += 2) {
      for (let x = 1; x < GRID; x += 2) {
        this.cellPiece('pillars', x, y).setDepth(DEPTH.pillars);
      }
    }
    this.add.image(PANEL_X, 0, 'panel').setOrigin(0).setDepth(DEPTH.panel);
  }

  // Кусок большой текстуры размером с клетку — так в оригинале рисовались стены.
  cellPiece(texture, x, y) {
    return this.add.image(FIELD_X, FIELD_Y, texture).setOrigin(0).setCrop(x * CELL, y * CELL, CELL, CELL);
  }

  createPlayers() {
    this.playerSprites = [];
    for (let i = 0; i < this.playerCount; i++) {
      const sprite = this.add.sprite(0, 0, `player${i + 1}`, i === 0 ? IDLE.right : IDLE.left)
        .setOrigin(0).setDepth(DEPTH.actors).setVisible(false);
      sprite.mode = null;
      this.playerSprites.push(sprite);
    }
  }

  createHud() {
    const top = DEPTH.panel + 1;
    this.add.image(760, 10, 'level_box').setOrigin(0).setDepth(DEPTH.panel);
    this.levelText = this.add.text(880, 16, '', textStyle(26, '#9b0000')).setOrigin(0.5, 0).setDepth(top);
    this.enemiesText = this.add.text(880, 72, '', textStyle(22, '#15093a')).setOrigin(0.5, 0).setDepth(top);
    this.totalText = this.add.text(880, 106, '', textStyle(22, '#15093a')).setOrigin(0.5, 0).setDepth(top);

    this.hud = [0, 1].map((i) => {
      const y = 405 + 170 * i;
      const parts = {
        face: this.add.image(760, y, `face${i + 1}`).setOrigin(0),
        stats: this.add.image(890, y, `stats${i + 1}`).setOrigin(0),
        name: this.add.text(814, y + 137, ['Иван', 'Колян'][i], textStyle(18, '#0096ff')).setOrigin(0.5),
        score: this.add.text(944, y + 137, '0', textStyle(18, '#0096ff')).setOrigin(0.5),
        lives: this.add.text(975, y + 40, '', textStyle(32, '#0096ff')).setOrigin(0.5),
        bombs: this.add.text(975, y + 90, '', textStyle(32, '#0096ff')).setOrigin(0.5),
      };
      for (const part of Object.values(parts)) {
        part.setDepth(top);
        if (i >= this.playerCount) part.setAlpha(0.25); // второго игрока нет — панель приглушена
      }
      return parts;
    });

    this.createHaikuPanel();

    // номер версии — мелко в самом низу панели
    const versionText = this.add.text(WIDTH - 8, HEIGHT - 2, '', textStyle(12, '#8888aa'))
      .setOrigin(1, 1).setDepth(top);
    gameVersion.then((version) => {
      if (version && versionText.active) versionText.setText(`v${version}`);
    });

    this.readyImage = this.add.image(250, 340, 'ready').setOrigin(0).setDepth(DEPTH.overlay).setVisible(false);
    this.pauseImage = this.add.image(315, 340, 'pause').setOrigin(0).setDepth(DEPTH.overlay).setVisible(false);
    this.message = this.add.text(FIELD_X + FIELD_SIZE / 2, 290, '',
      textStyle(44, '#ffcc00', { stroke: '#000000', strokeThickness: 6, align: 'center' }))
      .setOrigin(0.5).setDepth(DEPTH.overlay);
  }

  // Хокку живёт на правой панели, поверх «космического взрыва».
  createHaikuPanel() {
    const depth = DEPTH.panel + 1;
    this.haikuBox = this.add.rectangle(763, 166, 232, 232, 0x000000, 0.72).setOrigin(0)
      .setStrokeStyle(1, 0x6655cc).setDepth(depth);
    this.haikuTitle = this.add.text(879, 178, '', textStyle(17, '#ffcc00')).setOrigin(0.5, 0).setDepth(depth);
    this.haikuText = this.add.text(879, 216, '', textStyle(16, '#ffffff', {
      fontStyle: 'italic', align: 'center', lineSpacing: 10, wordWrap: { width: 224 },
    })).setOrigin(0.5, 0).setDepth(depth);
    this.showHaiku(START_HAIKU.title, START_HAIKU.text);
  }

  showHaiku(title, text) {
    this.haikuTitle.setText(title);
    this.haikuText.setText(text);
    this.tweens.add({ targets: [this.haikuTitle, this.haikuText], alpha: { from: 0, to: 1 }, duration: 1200 });
    this.tweens.add({ targets: this.haikuBox, alpha: { from: 0, to: 1 }, duration: 1200 });
  }

  // ------------------------------------------------------------ новое состояние от сервера

  onState(state) {
    if (this.finished) return;
    this.curr = state;
    this.currAt = performance.now();

    this.audio.update(state);
    for (const event of state.events) this.handleEvent(event);
    this.syncWalls(state.grid);
    this.sync(this.items, state.items, (o) => o.id,
      (o) => this.add.image(cellLeft(o.x), cellTop(o.y), `item_${o.kind}`).setOrigin(0).setDepth(DEPTH.items),
      (image, o) => (o.locked ? image.setTint(0xff4040) : image.clearTint()));  // запертая дверь — красная
    this.sync(this.bombs, state.bombs, (o) => o.id,
      (o) => this.add.sprite(cellLeft(o.x), cellTop(o.y), `bomb${o.owner + 1}`, 0).setOrigin(0).setDepth(DEPTH.bombs),
      (sprite, o) => sprite.setFrame(Math.min(4, Math.floor(o.progress * 5))));
    this.sync(this.flames, state.flames, (o) => `${o.x},${o.y},${o.kind}`,
      (o) => this.add.image(cellLeft(o.x), cellTop(o.y), `flame_${o.kind}`).setOrigin(0).setDepth(DEPTH.flames));
    this.sync(this.enemies, state.enemies, (o) => o.id,
      (o) => this.createEnemy(o),
      (sprite, o) => {
        this.setTarget(sprite, o);
        sprite.eyes.setAlert(o.chasing);
        sprite.look = o.look;
      });
    this.syncPlayers(state.players);
    this.updateHud(state);
    this.updateOverlay(state);

    if (state.phase === 'game_over') {
      this.finished = true;
      const score = state.players.reduce((sum, p) => sum + p.score, 0);
      this.time.delayedCall(2500, () =>
        this.scene.start('gameover', { level: state.level, score, records: state.records }));
    }
  }

  // Приводит набор картинок на экране в соответствие со списком от сервера:
  // новое — создаёт, исчезнувшее — удаляет, остальное — обновляет.
  sync(map, list, keyOf, create, update) {
    const seen = new Set();
    for (const obj of list) {
      const key = keyOf(obj);
      seen.add(key);
      let view = map.get(key);
      if (!view) {
        view = create(obj);
        map.set(key, view);
      }
      if (update) update(view, obj);
    }
    for (const [key, view] of map) {
      if (!seen.has(key)) {
        view.destroy();
        map.delete(key);
      }
    }
  }

  syncWalls(grid) {
    for (let i = 0; i < grid.length; i++) {
      const isWall = grid[i] === 'w';
      const wall = this.walls.get(i);
      if (isWall && !wall) {
        this.walls.set(i, this.cellPiece('walls', i % GRID, Math.floor(i / GRID)).setDepth(DEPTH.walls));
      } else if (!isWall && wall) {
        this.walls.delete(i);
        this.tweens.add({ targets: wall, alpha: 0, duration: 350, onComplete: () => wall.destroy() });
      }
    }
  }

  // Запоминаем, откуда и куда движется объект, — update() дорисует промежуточные положения.
  setTarget(sprite, obj) {
    const to = { x: obj.x, y: obj.y };
    const from = sprite.to ?? to;
    const jump = Math.abs(from.x - to.x) + Math.abs(from.y - to.y) > 1.5; // телепорт на новый уровень
    sprite.from = jump ? to : from;
    sprite.to = to;
  }

  createEnemy(o) {
    const sprite = this.add.sprite(0, 0, 'enemies').setOrigin(0).play(`enemy${o.tier}`);
    sprite.eyes = new EnemyEyes(this);
    sprite.once('destroy', () => sprite.eyes.destroy());
    return sprite;
  }

  syncPlayers(players) {
    players.forEach((p, i) => {
      const sprite = this.playerSprites[i];
      sprite.info = p;
      this.setTarget(sprite, p);
      if (p.state === 'alive' && sprite.mode !== 'alive') {
        sprite.mode = 'alive';
        sprite.anims.stop();
        sprite.setTexture(`player${i + 1}`, IDLE[p.facing]).setAlpha(1).setVisible(true);
        sprite.from = sprite.to;
      } else if ((p.state === 'dying' || p.state === 'dead') && sprite.mode !== 'dying') {
        this.startDeath(sprite, p, i + 1);
      } else if (p.state === 'exited' && sprite.mode !== 'exited') {
        sprite.mode = 'exited';
        this.tweens.add({ targets: sprite, alpha: 0, duration: 400 });
      } else if (p.state === 'out') {
        sprite.mode = 'out';
        sprite.setVisible(false);
      }
      if (p.state === 'dead') sprite.setDepth(DEPTH.corpses);  // тело легло на пол
    });
  }

  startDeath(sprite, p, n) {
    sprite.mode = 'dying';
    sprite.death = { kind: p.death, facing: p.facing, x: p.x, y: p.y, start: performance.now() };
    const prefix = p.death === 'super' ? 'super' : 'death';
    sprite.setTexture(p.death === 'super' ? `superdeath${n}` : `death${n}`);
    sprite.play(`${prefix}${n}-${p.facing}`);
    // обычная смерть — сразу на пол; при эпичной герой сначала летит поверх всех
    sprite.setDepth(p.death === 'super' ? actorDepth(p.y) + 0.5 : DEPTH.corpses);
  }

  handleEvent(event) {
    switch (event.type) {
      case 'explosion': {
        const boom = this.add.sprite(cellCenterX(event.x), cellCenterY(event.y), 'explosion')
          .setDepth(DEPTH.explosion).play('explosion');
        boom.once('animationcomplete', () => boom.destroy());
        break;
      }
      case 'enemy_killed': {
        const ghost = this.add.image(cellLeft(event.x), cellTop(event.y), 'enemies', event.tier * 4)
          .setOrigin(0).setDepth(actorDepth(event.y)).setTintFill(0xffffff);
        this.tweens.add({
          targets: ghost, alpha: 0, scaleX: 1.4, scaleY: 0.2, y: ghost.y + 30, duration: 450,
          onComplete: () => ghost.destroy(),
        });
        this.popup(cellCenterX(event.x), cellTop(event.y), `+${event.score}`, '#ffcc00');
        break;
      }
      case 'item_destroyed': {
        const boom = this.add.sprite(cellCenterX(event.x), cellCenterY(event.y), 'explosion')
          .setDepth(DEPTH.explosion).setScale(0.6).play('explosion');
        boom.once('animationcomplete', () => boom.destroy());
        break;
      }
      case 'door_locked':
        this.popup(cellCenterX(event.x), cellTop(event.y), 'Дверь заперта! Убейте всех врагов', '#ff6666', 2600);
        break;
      case 'door_closed':
        this.popup(cellCenterX(event.x), cellTop(event.y), 'Сначала убейте всех врагов!', '#ff6666');
        break;
      case 'all_enemies_killed':
        this.popup(FIELD_X + FIELD_SIZE / 2, 250, 'Все враги повержены!', '#66ff66', 2200);
        if (event.door_unlocked) this.popup(cellCenterX(event.x), cellTop(event.y), 'Дверь открыта!', '#66ff66', 2200);
        break;
      case 'player_died': {
        const victim = this.curr.players[event.player];
        const phrase = pick(event.kind === 'super' ? EPIC_PHRASES : DEATH_PHRASES);
        this.popup(cellCenterX(victim.x), cellTop(victim.y) - 10, phrase, '#ffffff', 2800, 26);
        // подорвал напарника — у того, кто подорвал, свой клич
        if (event.killer !== null && event.killer !== undefined && event.killer !== event.player) {
          const killer = this.curr.players[event.killer];
          this.popup(cellCenterX(killer.x), cellTop(killer.y) - 40, pick(CRIES[event.killer]),
            HERO_COLORS[event.killer], 3000, 30);
          this.cameras.main.shake(200, 0.004);
        }
        break;
      }
      case 'level_done':
        if (event.result === 'next') {
          this.showHaiku(`Хокку уровня ${this.curr.level}`, HAIKU[(this.curr.level - 1) % HAIKU.length]);
        }
        break;
      case 'item_taken': {
        const [text, color] = ITEM_POPUP[event.kind] ?? ['', '#ffffff'];
        this.popup(cellCenterX(event.x), cellTop(event.y), text, color);
        break;
      }
      case 'extra_life': {
        const hud = this.hud[event.player];
        this.popup(hud.lives.x - 60, hud.lives.y - 20, '+1 жизнь', '#66ff66');
        break;
      }
      default:
        break;
    }
  }

  // Всплывающая надпись. Не даём ей вылезти за край: над полем — в пределах поля,
  // над панелью — в пределах экрана; и оставляем место сверху, чтобы было куда всплыть.
  popup(x, y, text, color, duration = 1100, size = 22) {
    const RISE = 40;
    const label = this.add.text(x, y, text, textStyle(size, color, {
      stroke: '#000000', strokeThickness: 4, align: 'center', wordWrap: { width: FIELD_SIZE - 60 },
    })).setOrigin(0.5).setDepth(DEPTH.popups);
    const [left, right] = x < PANEL_X ? [FIELD_X, FIELD_X + FIELD_SIZE] : [PANEL_X, WIDTH];
    const half = label.width / 2 + 6;
    label.x = Phaser.Math.Clamp(x, left + half, Math.max(left + half, right - half));
    label.y = Math.max(y, label.height / 2 + RISE + 6);
    this.tweens.add({
      targets: label, y: label.y - RISE, alpha: { from: 1, to: 0 }, ease: 'Quad.easeIn', duration,
      onComplete: () => label.destroy(),
    });
  }

  updateHud(state) {
    this.levelText.setText(`Уровень ${state.level}`);
    const locked = state.items.some((i) => i.locked);
    this.enemiesText.setText(locked ? `Врагов: ${state.enemies.length} — дверь заперта` : `Врагов: ${state.enemies.length}`)
      .setFontSize(locked ? 16 : 22).setColor(locked ? '#b00000' : '#15093a');
    this.totalText.setText(`Очки: ${state.players.reduce((sum, p) => sum + p.score, 0)}`);
    state.players.forEach((p, i) => {
      const hud = this.hud[i];
      hud.name.setText(i === this.seat ? `${p.name} (вы)` : p.name);
      hud.score.setText(String(p.score));
      hud.lives.setText(String(p.lives));
      hud.bombs.setText(String(p.bombs));
    });
  }

  updateOverlay(state) {
    this.readyImage.setVisible(state.phase === 'ready');
    this.pauseImage.setVisible(state.phase === 'paused');
    const text = {
      ready: `Уровень ${state.level}`,
      level_done: state.result === 'next' ? 'Уровень пройден!' : 'Попробуем ещё раз',
      game_over: 'GAME OVER',
    }[state.phase];
    this.message.setText(text ?? '');
  }

  // ------------------------------------------------------------ каждый кадр экрана

  update() {
    if (!this.curr) return;
    const t = Phaser.Math.Clamp((performance.now() - this.currAt) / TICK_MS, 0, 1);
    const lerp = (s) => ({ x: s.from.x + (s.to.x - s.from.x) * t, y: s.from.y + (s.to.y - s.from.y) * t });

    for (const sprite of this.enemies.values()) {
      const pos = lerp(sprite);
      sprite.setPosition(cellLeft(pos.x), cellTop(pos.y)).setDepth(actorDepth(pos.y));
      sprite.eyes.follow(sprite, sprite.look);
    }
    for (const sprite of this.playerSprites) {
      if (sprite.mode === 'alive') {
        const pos = lerp(sprite);
        sprite.setPosition(cellLeft(pos.x), cellTop(pos.y)).setDepth(actorDepth(pos.y) + 0.005);
        sprite.setFrame(this.walkFrame(sprite.info, pos));
      } else if (sprite.mode === 'dying') {
        this.placeDeadBody(sprite);
      }
    }
  }

  // Кадр ходьбы зависит от того, где герой внутри клетки: 7 кадров на клетку, как в оригинале.
  walkFrame(info, pos) {
    if (!info.moving) return IDLE[info.facing];
    const along = info.facing === 'left' || info.facing === 'right' ? pos.x : pos.y;
    const phase = Math.floor((along - Math.floor(along)) * 7) % 7;
    return info.facing === 'left' ? 6 - phase : WALK_BASE[info.facing] + phase;
  }

  placeDeadBody(sprite) {
    const { kind, facing, x, y, start } = sprite.death;
    let left = cellLeft(x);
    let top = cellTop(y);
    if (kind === 'super') {
      top -= 13; // картинка 64×64 выше обычной
      const step = Math.min(SXY.length - 1, Math.floor((performance.now() - start) / SUPER_FRAME_MS));
      if (facing === 'left') left += SXY[step];
      if (facing === 'right') left -= SXY[step];
      if (facing === 'up') top += SXY[step];
      if (facing === 'down') top -= STXY[step];
    }
    sprite.setPosition(left, top);
  }
}
