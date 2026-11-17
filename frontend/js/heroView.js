// Герой на экране: бег, гибель, тень под ногами и лужа крови под телом.
// Картинки и таблицы (heroMeta.js) собирает tools/build_hero.py из кадров Blender.
//
// Стоящего героя держим за ступни — они чуть ниже центра клетки, а голова заходит на клетку выше.
// Лежащего — за середину тела: пока герой падает, она съезжает в центр клетки, чтобы руки и ноги
// не легли на соседние стены и колонны. Отброшенный взрывом ложится в центр клетки позади.
//
// Что остаётся от героя, зависит от того, кто до него добрался:
//   тварь    — съедает голову: убитый ею падает уже без головы, а у лежащего голова пропадает, когда
//              тварь по нему пройдёт (те же кадры гибели, лист hero<N>_headless);
//   крупная  — босс и матка откусывают половину туловища (лист hero<N>_half, собирает build_half.py);
//   змея     — обгладывает целиком: тело тает, на его месте остаются кости (bonesView.js).
// Лужа крови есть, только пока лежит тело: под костями её нет, а воскрес герой — пропадает вместе с телом.

import { DETAIL } from './canvasTexture.js';
import { CELL, DEPTH, actorDepth, cellCenterX, cellCenterY } from './layout.js';
import { HERO } from './heroMeta.js';
import { bonesKey } from './bonesView.js';

const STEP = { right: [1, 0], left: [-1, 0], up: [0, -1], down: [0, 1] };
const OPPOSITE = { right: 'left', left: 'right', up: 'down', down: 'up' };
const ROW = Object.fromEntries(HERO.dirs.map((dir, i) => [dir, i]));
const RUN_COLUMNS = HERO.run.frames + 1;       // кадры бега и в конце строки — «стоит»
const SHADOW_ALPHA = 0.3;
const TOP_ROW_DROP = 6;                        // в верхнем ряду герой бежит ниже на столько точек: шапка не уходит за край
const BONES_PAUSE = 0.35;                      // съеденный змеёй: упал, столько секунд лежит…
const BONES_TIME = 0.5;                        // …и за столько тает, а на его месте проступают кости
const BITE = 0.5;                              // враг ближе этого (в клетках) к лежащему телу — ест
const HEAD_UP = 30;                            // голова стоящего героя — на столько точек выше центра клетки
const HEAD_ALONG = 20;                         // голова лежащего — на столько точек от середины тела
const FADE = 450;                              // воскрес: за столько миллисекунд тает тело на месте гибели
const BLINK = 0.2;                             // воскрешённый мигает: один миг — столько секунд

// На сколько точек ступни ниже центра клетки. y — в клетках; ниже верхнего ряда добавка плавно сходит на нет.
const feet = (y) => HERO.feet + TOP_ROW_DROP * Phaser.Math.Clamp(1 - y, 0, 1);

// Лужа крови: пятна [x, y, ширина, высота] в долях радиуса; растекается за секунду. Вокруг — брызги [x, y, размер].
const BLOOD = 0x8c0f0f;
const BLOOD_EDGE = 0x560808;
const POOL_RADIUS = 16.5;
const POOL = [[0, 0, 1.0, 0.8], [0.55, 0.15, 0.6, 0.5], [-0.5, -0.2, 0.65, 0.5], [0.15, 0.5, 0.55, 0.45],
  [-0.25, 0.45, 0.5, 0.4], [0.3, -0.45, 0.5, 0.4]];
const DROPS = [[1.5, 0.3, 0.13], [-1.35, 0.6, 0.10], [0.9, -1.0, 0.11], [-0.8, -0.95, 0.08], [1.2, 0.95, 0.07],
  [-1.6, -0.2, 0.09], [0.2, 1.25, 0.08]];

export class HeroView {
  constructor(scene, index) {
    this.scene = scene;
    this.number = index + 1;
    this.run = `hero${this.number}`;
    this.fall = `hero${this.number}_death`;
    this.eaten = `hero${this.number}_headless`;
    this.half = `hero${this.number}_half`;
    this.pool = this.newPool();
    this.shadow = scene.add.ellipse(0, 0, 26, 10, 0x000000).setVisible(false);
    this.sprite = scene.add.sprite(0, 0, this.run).setVisible(false);
    this.bones = scene.add.image(0, 0, bonesKey('pile')).setScale(1 / DETAIL)
      .setDepth(DEPTH.corpses + 0.01).setVisible(false);
    this.mode = null;
    this.info = null;
    this.death = null;
    this.path = 0;        // сколько точек экрана герой пробежал: по нему выбирается кадр бега
    this.at = null;
  }

  newPool() {
    return this.scene.add.graphics().setDepth(DEPTH.corpses - 0.05);
  }

  // Новое состояние героя от сервера. Куда и откуда он движется (from, to), записывает экран игры.
  // partner — напарник ещё в игре: лужу крови рисуем только тогда (иначе уровень сразу кончается).
  sync(p, partner) {
    this.info = p;
    if (p.state === 'alive' && this.mode !== 'alive') {
      this.mode = 'alive';
      this.death = null;
      this.from = this.to;
      this.at = null;
      this.pool.clear();
      this.bones.setVisible(false);
      this.scene.tweens.killTweensOf(this.sprite);
      this.sprite.setTexture(this.run).setOrigin(...HERO.run.origin).setAlpha(1).setVisible(true);
      this.shadow.setScale(1).setAlpha(SHADOW_ALPHA).setVisible(true);
    } else if ((p.state === 'dying' || p.state === 'dead') && this.mode !== 'dying') {
      this.mode = 'dying';
      const table = HERO.death.kinds[p.death_anim];
      const [dx, dy] = STEP[p.facing];
      const back = table.frames.at(-1)[0] ? 1 : 0;   // отброшен — ложится на клетку позади, иначе в своей
      this.death = { table, facing: p.facing, x: p.x, y: p.y,
        restX: Math.round(p.x) - dx * back, restY: Math.round(p.y) - dy * back,
        flying: p.death === 'super', blood: partner, headless: false, half: false, bones: null,
        start: performance.now(), still: false };
      this.scene.tweens.killTweensOf(this.sprite);
      this.sprite.setTexture(this.fall).setOrigin(...HERO.death.origin).setAlpha(1).setVisible(true);
      this.bones.setVisible(false);
      this.pool.clear().setAlpha(1);
      if (p.cause === 'enemy') {                        // тварь убила — голову съела сразу, крупная — полтуловища
        if (p.half) this.loseHalf();
        else this.loseHead();
      }
      // remains — что останется от съеденного змеёй (skeleton или pile): упал, полежал — и обглодан дочиста
      if (p.remains) this.gnaw(p.remains, table.frames.length / HERO.death.fps + BONES_PAUSE, true);
    } else if (p.state === 'exited' && this.mode !== 'exited') {
      this.mode = 'exited';
      this.shadow.setVisible(false);
      this.scene.tweens.add({ targets: this.sprite, alpha: 0, duration: 400 });
    } else if (p.state === 'out' && this.mode !== 'out') {
      this.mode = 'out';                             // жизни кончились: на новом уровне нет ни тела, ни костей, ни лужи
      this.death = null;
      this.sprite.setVisible(false);
      this.shadow.setVisible(false);
      this.bones.setVisible(false);
      this.pool.clear();
    }
  }

  // Каждый кадр экрана. t — доля пути между двумя состояниями от сервера (0..1).
  draw(t) {
    if (this.mode === 'alive') this.drawAlive(t);
    else if (this.mode === 'dying') this.drawDeath();
  }

  drawAlive(t) {
    const x = this.from.x + (this.to.x - this.from.x) * t;
    const y = this.from.y + (this.to.y - this.from.y) * t;
    const moved = this.at ? Math.abs(x - this.at.x) + Math.abs(y - this.at.y) : 0;
    if (moved < 1) this.path += moved * CELL;      // перенос на новое место (новый уровень) в путь не идёт
    this.at = { x, y };
    // Кадр бега — по пройденному пути: ноги не скользят, с какой бы скоростью герой ни шёл.
    const column = this.info.moving
      ? Math.floor((this.path / HERO.run.cycle) % 1 * HERO.run.frames) : HERO.run.frames;
    this.place(cellCenterX(x), cellCenterY(y) + feet(y), actorDepth(y) + 0.005,
      ROW[this.info.facing] * RUN_COLUMNS + column);
    // только что воскрешён: пока сервер держит его неуязвимым (shield), герой мигает (на паузе часы экрана стоят)
    const blink = Math.sin(this.scene.clock * 2 * Math.PI / BLINK);
    this.sprite.setAlpha(this.info.shield ? 0.6 + 0.4 * blink : 1);
  }

  // Сколько секунд прошло с гибели и лежит ли уже тело (показан последний кадр падения).
  fallen() {
    const time = (performance.now() - this.death.start) / 1000;
    return { time, lying: time * HERO.death.fps >= this.death.table.frames.length - 1 };
  }

  drawDeath() {
    const death = this.death;
    if (death.still) return;
    const { table, facing } = death;
    const { time } = this.fallen();
    const last = table.frames.length - 1;
    const i = Math.min(last, Math.floor(time * HERO.death.fps));
    const [shift, lie, shadowAlpha, shadowScale] = table.frames[i];
    const [dx, dy] = STEP[facing];
    const flown = table.frames[last][0];           // на сколько точек отбрасывает этот вид гибели (0 — падает на месте)
    const moved = flown ? shift / flown : lie;     // какую долю пути до места, где ляжет, тело уже прошло
    const [fitX, fitY] = table.rest[ROW[facing]];  // поправка: лежащее тело — ровно посередине клетки
    const x = cellCenterX(death.x + (death.restX - death.x) * moved) + fitX * lie;
    const y = cellCenterY(death.y + (death.restY - death.y) * moved) + feet(death.y) * (1 - lie) + fitY * lie;
    const landed = time - table.landed;            // сколько секунд тело уже лежит
    // пока падает — поверх всех (при «суперсмерти» ещё и летит), легло — на пол, под огонь и бомбы
    const depth = landed >= 0 ? DEPTH.corpses : actorDepth(death.y) + (death.flying ? 0.5 : 0.005);
    this.place(x, y, depth, (table.row + ROW[facing]) * HERO.death.columns + i);
    this.shadow.setScale(shadowScale).setAlpha(shadowAlpha);
    let melted = 0;                                // насколько тело истаяло и проступили кости (0..1)
    if (death.bones) {
      melted = Phaser.Math.Clamp((time - death.bones.at) / BONES_TIME, 0, 1);
      this.sprite.setAlpha(1 - melted);
      this.bones.setAlpha(melted);
    }
    // Лужа — под телом, ближе к голове. Убитый змеёй обглодан дочиста, лужи не было и нет;
    // если змея добралась до уже лежащего — лужа уходит вместе с телом.
    if (death.blood && !death.bones?.clean) {
      const head = (death.half ? 0 : table.head) * HERO.death.pool;   // укус крупного — лужа у среза, не у головы
      this.drawPool(x - fitX * lie + dx * head, y - fitY * lie + dy * head, landed);
      this.pool.setAlpha(1 - melted);
    }
    // упал, лужа растеклась, тело истаяло — рисовать больше нечего
    death.still = i === last && landed > 1 && (!death.bones || melted === 1);
  }

  place(x, y, depth, frame) {
    this.sprite.setPosition(x, y).setDepth(depth).setFrame(frame);
    this.shadow.setPosition(x, y + 1).setDepth(depth - 0.001);
  }

  drawPool(x, y, since) {
    const g = this.pool.clear();
    if (since <= 0) return;
    const radius = POOL_RADIUS * (0.35 + 0.65 * (1 - (1 - Math.min(1, since)) ** 2));
    for (const [color, scale] of [[BLOOD_EDGE, 1], [BLOOD, 0.86]]) {
      g.fillStyle(color);
      for (const [px, py, w, h] of POOL) {
        g.fillEllipse(x + px * radius, y + py * radius, 2 * w * radius * scale, 2 * h * radius * scale);
      }
    }
    g.fillStyle(BLOOD);
    for (const [px, py, size] of DROPS) g.fillCircle(x + px * POOL_RADIUS, y + py * POOL_RADIUS, size * POOL_RADIUS);
  }

  // ------------------------------------------------------------ съели

  // Голову съели: дальше кадры берём из листа без головы (шапка пропадает вместе с ней).
  loseHead() {
    this.death.headless = true;
    this.death.still = false;
    this.sprite.setTexture(this.eaten).setOrigin(...HERO.death.origin);
  }

  // Крупная тварь откусила половину туловища: остаётся нижняя половина с рваной кромкой укуса.
  loseHalf() {
    this.death.headless = true;
    this.death.half = true;
    this.death.still = false;
    this.sprite.setTexture(this.half).setOrigin(...HERO.death.origin);
  }

  // Змея обглодала: с секунды at (от гибели) тело тает, на его месте проступают кости kind.
  // clean — змея и убила: крови не было вовсе.
  gnaw(kind, at, clean = false) {
    const death = this.death;
    death.bones = { at, clean };
    death.still = false;
    // череп — там же, где лежала голова: отброшенный взрывом лежит головой назад
    const headTo = death.table.head > 0 ? death.facing : OPPOSITE[death.facing];
    this.bones.setTexture(bonesKey(kind, headTo)).setAlpha(0).setVisible(true)
      .setPosition(cellCenterX(death.restX), cellCenterY(death.restY));
  }

  // Враги из состояния сервера прошли рядом с лежащим телом: тварь съедает голову, змея обгладывает до костей.
  // Возвращает, что случилось сейчас: 'head', 'bones' или null. Решает экран, а не сервер, но оба игрока
  // в игре по сети получают одни и те же положения врагов — и видят одно и то же.
  nibble(enemies) {
    const death = this.death;
    if (this.mode !== 'dying' || !death || death.bones) return null;
    const { time, lying } = this.fallen();
    if (!lying) return null;
    for (const enemy of enemies) {
      if (enemy.in_wall) continue;                 // призрак в стене безвреден — и тело не тронет
      const snake = enemy.kind === 'snake';
      const big = enemy.kind === 'boss' || enemy.kind === 'queen';
      if (!snake && (big ? death.half : death.headless)) continue;
      if (Math.hypot(enemy.x - death.restX, enemy.y - death.restY) > BITE) continue;
      if (!snake) {
        if (big) {
          this.loseHalf();
          return 'half';
        }
        this.loseHead();
        return 'head';
      }
      this.gnaw(enemy.id % 2 ? 'skeleton' : 'pile', time);
      return 'bones';
    }
    return null;
  }

  // Где на экране голова погибшего: у лежащего — сбоку от середины тела, у ещё стоящего — над клеткой.
  headSpot() {
    const death = this.death;
    if (!death) return [this.sprite.x, this.sprite.y - HEAD_UP - HERO.feet];
    if (!this.fallen().lying) return [cellCenterX(death.x), cellCenterY(death.y) - HEAD_UP];
    const [dx, dy] = STEP[death.facing];
    const along = death.table.head * HEAD_ALONG;
    return [cellCenterX(death.restX) + dx * along, cellCenterY(death.restY) + dy * along];
  }

  // Середина клетки, где лежит тело (или кости).
  restSpot() {
    return [cellCenterX(this.death.restX), cellCenterY(this.death.restY)];
  }

  // ------------------------------------------------------------ воскрес

  // Напарник воскресил: тело (или кости) и лужа на месте гибели тают, а сам герой встаёт в своём углу и мигает.
  // Вызывается до sync() с новым состоянием.
  vanish() {
    if (this.mode !== 'dying') return;            // жизни кончились ещё в прошлом раунде — тела на поле нет
    const fade = (target) => this.scene.tweens.add({
      targets: target, alpha: 0, duration: FADE, onComplete: () => target.destroy(),
    });
    for (const part of [this.sprite, this.bones]) {
      if (!part.visible || part.alpha <= 0) continue;
      fade(this.scene.add.image(part.x, part.y, part.texture.key, part.frame.name)
        .setOrigin(part.originX, part.originY).setScale(part.scaleX, part.scaleY)
        .setDepth(part.depth).setAlpha(part.alpha));
    }
    fade(this.pool);                               // прежняя лужа дотает сама, для следующей — новый холст
    this.pool = this.newPool();
  }
}
