// Игровой экран. Сам ничего не решает: 30 раз в секунду получает от сервера
// состояние игры и рисует его. Между получениями плавно «дорисовывает»
// движение (интерполяция), чтобы картинка не дёргалась.

import {
  CELL, DEPTH, FIELD_SIZE, FIELD_X, FIELD_Y, GRID, PANEL_X, TICK_MS, WIDTH,
  actorDepth, cellCenterX, cellCenterY, cellTop, textStyle,
} from '../layout.js';
import { Banners } from '../banners.js';
import { BlastView, BombView, FlameView, WallChunks } from '../blastView.js';
import { PAPER, addModifierStrip, addPanel, count, points, updateModifiers } from '../bunker.js';
import { Controls } from '../controls.js';
import { EnemyView } from '../enemyView.js';
import { HeroView } from '../heroView.js';
import { ItemView } from '../itemView.js';
import { keyLabel, loadBindings } from '../keybindings.js';
import { SnakeView } from '../snakeView.js';
import { GameAudio } from '../audio/gameAudio.js';
import { sound } from '../audio/sound.js';
import { gameVersion } from '../version.js';
import {
  CRIES, DEATH_PHRASES, EATEN_PHRASES, EPIC_PHRASES, GNAWED_PHRASES, HAIKU, REVIVED_PHRASES, REVIVE_CRIES,
  START_HAIKU, TRAP_PHRASES, pick,
} from '../texts.js';

const HERO_COLORS = ['#66ccff', '#99ff66'];  // Иван, Игорь
const HERO_NAMES = ['Иван', 'Игорь'];
const HEAD_UP = 30;        // голова стоящего героя — на столько точек выше центра клетки
const GNAW_AFTER = 1500;   // съеденный змеёй падает, и через столько миллисекунд она его обгладывает
// Фраза над погибшим — смотря от чего погиб (вплотную к бомбе — свои, см. ниже).
const CAUSE_PHRASES = { enemy: EATEN_PHRASES, snake: GNAWED_PHRASES, trap: TRAP_PHRASES };

const ITEM_POPUP = {
  door: ['Выход!', '#66ff66'], chest: ['+1000', '#ffcc00'], bag: ['+100', '#ffcc00'],
  bigbag: ['+200', '#ffcc00'], gems: ['+500', '#ffcc00'],
  bomb: ['+1 бомба', '#66ccff'], life: ['+1 жизнь', '#66ff66'], death: ['Ловушка!', '#ff4444'],
  remote: ['Пульт подрыва', '#66ccff'], fire: ['Огонь +1', '#ff9944'],
  shield: ['Щит', '#66ccff'], boots: ['Сапоги', '#99ff66'],
};

export class GameScene extends Phaser.Scene {
  constructor() {
    super('game');
  }

  init(data) {
    this.playerCount = data.players;
    this.seat = data.seat ?? null;   // игра по сети: 0 — я Иван, 1 — я Игорь; null — своя игра
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
    this.effects = [];    // взрывы и обломки стен: живут пару секунд и убирают себя сами
    this.clock = 0;       // секунды игры: на паузе стоит, по нему идут взрывы
    this.audio = new GameAudio();

    this.drawField();
    this.heroes = Array.from({ length: this.playerCount }, (_, i) => new HeroView(this, i));
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
  }

  // Кусок большой текстуры размером с клетку — так в оригинале рисовались стены.
  cellPiece(texture, x, y) {
    return this.add.image(FIELD_X, FIELD_Y, texture).setOrigin(0).setCrop(x * CELL, y * CELL, CELL, CELL);
  }

  createHud() {
    // правая панель «блиндаж», см. bunker.js; на листке «ВОСКРЕСИТЬ» — клавиша того, кто может поднять напарника
    const keys = loadBindings();
    this.panel = addPanel(this, this.playerCount,
      HERO_NAMES.map((name, i) => ({ name, key: keyLabel(keys[i].revive) })));
    this.panel.heroes.forEach((hero, i) => {
      hero.name.setText(HERO_NAMES[i]);
      hero.modifiers = this.createModifiers(i);
    });
    this.showHaiku(START_HAIKU.title, START_HAIKU.text);

    // номер версии — мелко в самом низу панели
    gameVersion.then((version) => {
      if (version && this.panel.version.active) this.panel.version.setText(`v${version}`);
    });

    this.banners = new Banners(this);   // «ПРИГОТОВЬТЕСЬ» и «ПАУЗА» — доски с трафаретом, см. banners.js
    this.message = this.add.text(FIELD_X + FIELD_SIZE / 2, 290, '',
      textStyle(44, '#ffcc00', { stroke: '#000000', strokeThickness: 6, align: 'center' }))
      .setOrigin(0.5).setDepth(DEPTH.overlay);
  }

  createModifiers(index) {
    return addModifierStrip(this, index);
  }

  // Хокку живёт на правой панели, на своём листке.
  showHaiku(title, text) {
    const { noteTitle, note } = this.panel;
    noteTitle.setText(title);
    note.setText(text);
    this.tweens.add({ targets: [noteTitle, note], alpha: { from: 0, to: 1 }, duration: 1200 });
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
      (o) => new ItemView(this, o),
      (item, o) => item.sync(o));               // запертая дверь — красная, с замком
    this.sync(this.bombs, state.bombs, (o) => o.id,
      (o) => new BombView(this, o, this.clock),
      (bomb, o) => bomb.sync(o));
    const blasts = state.events.filter((event) => event.type === 'explosion');
    this.sync(this.flames, state.flames, (o) => `${o.x},${o.y},${o.kind}`,
      (o) => new FlameView(this, o, blasts, this.clock),
      (flame) => { flame.seen += 1; });
    for (const flame of this.flames.values()) flame.settle(this.clock);
    // враги рисуют себя сами: змея — snakeView.js, остальные твари — enemyView.js
    this.sync(this.enemies, state.enemies, (o) => o.id,
      (o) => (o.kind === 'snake' ? new SnakeView(this, o) : new EnemyView(this, o)),
      (enemy, o) => enemy.sync(o));
    state.players.forEach((p, i) => {
      this.setTarget(this.heroes[i], p);
      this.heroes[i].sync(p, state.players.some((other) => other !== p && other.state === 'alive'));
    });
    if (state.phase === 'playing') {
      for (const hero of this.heroes) {             // враг дошёл до лежащего тела — ест
        const bite = hero.nibble(state.enemies);
        if (bite) this.onBite(hero, bite);
      }
    }
    this.updateHud(state);
    this.updateOverlay(state);

    if (state.phase === 'game_over') {
      this.finished = true;
      const score = state.players.reduce((sum, p) => sum + p.score, 0);
      this.time.delayedCall(2500, () =>
        this.scene.start('gameover', { level: state.level, score, records: state.records, players: this.playerCount }));
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
        this.tweens.addCounter({                    // стена сгорает: чернеет и тает
          from: 0, to: 0.6, duration: 600,
          onUpdate: (tween) => {
            const s = tween.getValue(), gone = Phaser.Math.SmoothStep(s, 0, 0.6);
            const light = Math.round(255 * (1 - 0.7 * Phaser.Math.SmoothStep(s, 0, 0.2) * (1 - gone)));
            wall.setAlpha(1 - gone).setTint(Phaser.Display.Color.GetColor(light, light, light));
          },
          onComplete: () => wall.destroy(),
        });
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

  handleEvent(event) {
    switch (event.type) {
      case 'explosion': {
        const boom = this.add.sprite(cellCenterX(event.x), cellCenterY(event.y), 'explosion')
          .setDepth(DEPTH.explosion).play('explosion');
        boom.once('animationcomplete', () => boom.destroy());
        this.effects.push(new BlastView(this, event, this.curr, this.clock));
        this.cameras.main.shake(150, 0.002);    // экран вздрагивает: на пару точек
        break;
      }
      case 'wall_destroyed':
        this.effects.push(new WallChunks(this, event, this.clock));
        break;
      case 'level_start':                       // новое поле — копоть и дым прежнего не нужны
        for (const effect of this.effects) effect.destroy();
        this.effects = [];
        break;
      case 'enemy_killed': {
        if (event.kind !== 'snake') this.enemies.get(event.id)?.die();   // тварь белеет, сплющивается и тает
        const body = event.kind === 'snake' ? [[event.x, event.y], ...event.body] : [];
        for (const [bx, by] of body) {               // змея: вспышка вдоль всего тела, от головы до хвоста
          const puff = this.add.circle(cellCenterX(bx), cellCenterY(by), 14, 0xffffff).setDepth(actorDepth(by));
          this.tweens.add({ targets: puff, alpha: 0, scale: 1.6, duration: 450, onComplete: () => puff.destroy() });
        }
        if (event.score > 0) this.popup(cellCenterX(event.x), cellTop(event.y), `+${event.score}`, '#ffcc00');
        break;
      }
      case 'armor_cracked':
        this.popup(cellCenterX(event.x), cellTop(event.y), 'Панцирь треснул!', '#ffcc00');
        this.cameras.main.shake(180, 0.003);
        break;
      case 'boss_phase':
        this.popup(cellCenterX(event.x), cellTop(event.y),
          event.armor > 0 ? 'Панцирь треснул! Он зовёт подмогу!' : 'Последний панцирь! Добивай!', '#ff6666', 2200);
        this.cameras.main.shake(250, 0.005);
        break;
      case 'enemy_enraged':
        this.popup(cellCenterX(event.x), cellTop(event.y), 'ЯРОСТЬ!', '#ff6666', 1800, 26);
        break;
      case 'loot_grabbed':
        this.popup(cellCenterX(event.x), cellTop(event.y), 'Воришка!', '#ffd24a');
        break;
      case 'loot_hidden':
        this.popup(cellCenterX(event.x), cellTop(event.y), 'Спрятал под стеной!', '#ffd24a', 1600, 20);
        break;
      case 'loot_dropped':
        this.popup(cellCenterX(event.x), cellTop(event.y), 'Выронил!', '#ffd24a', 1300, 20);
        break;
      case 'mole_ate':
        this.popup(cellCenterX(event.x), cellTop(event.y), 'Крот всё сожрал!', '#c9a8ff', 1600, 20);
        break;
      case 'mole_burrowed':
      case 'mole_surfaced': {
        const x = cellCenterX(event.x), y = cellCenterY(event.y);
        for (let i = 0; i < 5; i++) {              // комья земли
          const a = i * 1.3 + x;
          const clod = this.add.circle(x, y + 8, 2.2, 0x5d4a33).setDepth(actorDepth(event.y));
          this.tweens.add({
            targets: clod, x: x + Math.cos(a) * 16, y: y + 8 - Math.abs(Math.sin(a)) * 18, alpha: 0,
            ease: 'Quad.easeOut', duration: 600, onComplete: () => clod.destroy(),
          });
        }
        break;
      }
      case 'door_appeared':
        this.popup(cellCenterX(event.x), cellTop(event.y), 'Дверь открыта!', '#66ff66', 2200);
        break;
      case 'shield_saved': {
        const saved = this.curr.players[event.player];
        this.popup(cellCenterX(saved.x), cellTop(saved.y) - 10, 'Щит спас!', '#66ccff', 1800, 24);
        break;
      }
      case 'item_destroyed': {
        const boom = this.add.sprite(cellCenterX(event.x), cellCenterY(event.y), 'explosion')
          .setDepth(DEPTH.explosion).setScale(0.6).play('explosion');
        boom.once('animationcomplete', () => boom.destroy());
        break;
      }
      case 'life_burned':
        this.popup(cellCenterX(event.x), cellTop(event.y),
          `Жизнь взорвана! Выходят ${event.enemies} врага`, '#ff6666', 2600);
        break;
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
        const phrase = pick(event.kind === 'super' ? EPIC_PHRASES : CAUSE_PHRASES[event.cause] ?? DEATH_PHRASES);
        const say = () => this.popup(cellCenterX(victim.x), cellTop(victim.y) - 10, phrase, '#ffffff', 2800, 26);
        if (event.cause === 'enemy') {              // тварь откусила голову (крупная — полтуловища): «ХРУМ!», фраза — следом
          const biteY = cellCenterY(victim.y) - (victim.half ? 10 : HEAD_UP);
          this.crunch(cellCenterX(victim.x), biteY, 'ХРУМ!', true);
          this.time.delayedCall(500, say);
        } else {
          say();
        }
        if (event.cause === 'snake') {              // змея обгладывает уже упавшего
          const hero = this.heroes[event.player];
          this.time.delayedCall(GNAW_AFTER, () => {
            if (hero.death?.bones) this.crunch(...hero.restSpot(), 'хрум-хрум-хрум', false);
          });
        }
        // подорвал напарника — у того, кто подорвал, свой клич
        if (event.killer !== null && event.killer !== undefined && event.killer !== event.player) {
          const killer = this.curr.players[event.killer];
          this.popup(cellCenterX(killer.x), cellTop(killer.y) - 40, pick(CRIES[event.killer]),
            HERO_COLORS[event.killer], 3000, 30);
          this.cameras.main.shake(200, 0.004);
        }
        break;
      }
      case 'player_revived': {
        // тело на месте гибели тает, а воскресший встаёт в своём углу — во вспышке света
        this.heroes[event.player].vanish();
        const light = this.add.image(cellCenterX(event.x), cellCenterY(event.y), 'fx_spark')
          .setBlendMode(Phaser.BlendModes.ADD).setDepth(DEPTH.air).setScale(0.5);
        this.tweens.add({ targets: light, scale: 3.2, alpha: 0, duration: 700, onComplete: () => light.destroy() });
        this.popup(cellCenterX(event.x), cellTop(event.y) - 10, pick(REVIVED_PHRASES),
          HERO_COLORS[event.player], 3000, 24);
        const saviour = this.curr.players[event.by];
        this.popup(cellCenterX(saviour.x), cellTop(saviour.y) - 30, pick(REVIVE_CRIES[event.by]),
          HERO_COLORS[event.by], 3000, 24);
        const { lives } = this.panel.heroes[event.by];
        this.popup(lives.x - 60, lives.y - 20, '−1 жизнь', '#ff6666');
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
        const { lives } = this.panel.heroes[event.player];
        this.popup(lives.x - 60, lives.y - 20, '+1 жизнь', '#66ff66');
        break;
      }
      default:
        break;
    }
  }

  // Враг дошёл до лежащего тела: тварь съела голову (head), крупная откусила полтуловища (half),
  // змея обглодала до костей (bones).
  onBite(hero, kind) {
    if (kind === 'head') this.crunch(...hero.headSpot(), 'ХРУМ!', true);
    else if (kind === 'half') this.crunch(...hero.restSpot(), 'ХРУМ!', true);
    else this.crunch(...hero.restSpot(), 'хрум-хрум-хрум', false);
    this.audio.bite(kind === 'bones' ? 'bones' : 'head', hero.info.x);
  }

  // Надпись вроде «ХРУМ!» в точке экрана (x, y): выскакивает и тает; splash — с брызгами.
  crunch(x, y, text, splash) {
    for (let i = 0; splash && i < 9; i++) {
      const angle = i * 0.7 + x, far = 10 + 1.4 * ((i * 37) % 10);
      const drop = this.add.circle(x, y, 1.8, 0xaa1010).setDepth(DEPTH.air);
      this.tweens.add({
        targets: drop, x: x + Math.cos(angle) * far, y: y + Math.sin(angle) * far * 0.7 + 14, alpha: 0,
        ease: 'Quad.easeOut', duration: 900, onComplete: () => drop.destroy(),
      });
    }
    const label = this.add.text(x, y - 14, text, textStyle(17, '#ffffff', {
      fontStyle: 'bold', stroke: '#000000', strokeThickness: 4,
    })).setOrigin(0.5).setDepth(DEPTH.popups);
    const half = label.width / 2 + 4;
    label.x = Phaser.Math.Clamp(x, FIELD_X + half, FIELD_X + FIELD_SIZE - half);
    label.y = Math.max(label.y, label.height / 2 + 4);
    this.tweens.add({
      targets: label, scale: { from: 0.6, to: 1.35 }, alpha: { from: 1, to: 0 }, ease: 'Quad.easeIn', duration: 900,
      onComplete: () => label.destroy(),
    });
  }

  // Всплывающая надпись. Не даём ей вылезти за край: над полем — в пределах поля,
  // над панелью — в пределах экрана; и оставляем место сверху, чтобы было куда всплыть.
  popup(x, y, text, color, duration = 1100, size = 22) {
    const RISE = 40;
    const label = this.add.text(x, y, text, textStyle(size, color, {
      stroke: '#000000', strokeThickness: 4, align: 'center', wordWrap: { width: FIELD_SIZE - 60 },
    })).setOrigin(0.5).setDepth(x < PANEL_X ? DEPTH.popups : DEPTH.panel + 3);   // над панелью — поверх её листков
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
    const { title, line1, line2, heroes } = this.panel;
    title.setText(`Уровень ${state.level}`);
    const locked = state.items.some((i) => i.locked);
    line1.setText(locked ? `Врагов: ${state.enemies.length} — дверь заперта` : `Врагов: ${state.enemies.length}`)
      .setFontSize(locked ? 16 : 22).setColor(locked ? PAPER.accent : PAPER.text);
    line2.setText(`Очки: ${points(state.players.reduce((sum, p) => sum + p.score, 0))}`);
    state.players.forEach((p, i) => {
      const hero = heroes[i];
      hero.name.setText(i === this.seat ? `${p.name} (вы)` : p.name);
      hero.score.setText(points(p.score));
      hero.lives.setText(count(p.lives));
      hero.bombs.setText(count(p.bombs));
      updateModifiers(hero.modifiers, p);
      hero.dead.setVisible(['dying', 'dead', 'out'].includes(p.state));  // на портрете — штамп «ПОГИБ»
      // напарник может воскресить этого героя — поверх его счётчиков листок «ВОСКРЕСИТЬ»
      const offer = Boolean(state.players[1 - i]?.can_revive);
      hero.revive.forEach((part) => part.setVisible(offer));
    });
  }

  updateOverlay(state) {
    this.banners.update(state.phase, state.level);
    const text = {
      level_done: state.result === 'next' ? 'Уровень пройден!' : 'Попробуем ещё раз',
      game_over: 'GAME OVER',
    }[state.phase];
    this.message.setText(text ?? '');
  }

  // ------------------------------------------------------------ каждый кадр экрана

  update(time, delta) {
    if (!this.curr) return;
    if (this.curr.phase !== 'paused') this.clock += delta / 1000;
    const t = Phaser.Math.Clamp((performance.now() - this.currAt) / TICK_MS, 0, 1);

    for (const enemy of this.enemies.values()) enemy.draw(t, this.clock);
    for (const hero of this.heroes) hero.draw(t);
    for (const item of this.items.values()) item.draw(this.clock);
    for (const bomb of this.bombs.values()) bomb.draw(this.clock);
    for (const flame of this.flames.values()) flame.draw(this.clock);
    this.effects = this.effects.filter((effect) => {
      const alive = effect.draw(this.clock);
      if (!alive) effect.destroy();
      return alive;
    });
  }
}
