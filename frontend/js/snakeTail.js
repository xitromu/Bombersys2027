// Тело змеи: цепочка шаров за головой. Голова — обычный спрайт врага с глазами (см. GameScene).
// Облик временный: окончательный появится вместе с остальной новой графикой, через макет.

import { cellCenterX, cellCenterY } from './layout.js';

const LIGHT = [0x60c458, 0xee962a, 0xd63434, 0x9448d6];   // цвета по ступеням — те же, что у призраков
const DARK = [0x3e8a3a, 0xb06a14, 0x962020, 0x622a96];    // через один шар — темнее, получаются кольца
const NECK_RADIUS = 19;   // шар у головы, точек экрана
const TIP_RADIUS = 9;     // кончик хвоста
const JUMP = 0.6;         // за один шаг сервера точка тела так далеко не уползает — значит, змея развернулась

export class SnakeTail {
  constructor(scene, tier) {
    this.graphics = scene.add.graphics();
    this.tier = tier;
    this.from = null;
    this.to = null;
  }

  // Новое положение тела от сервера: точки [x, y] от шеи к кончику хвоста.
  // Возвращает true, если змея развернулась и «дорисовывать» движение нельзя.
  setTarget(body) {
    const jumped = !this.to || this.to.length !== body.length
      || body.some(([x, y], i) => Math.abs(x - this.to[i][0]) + Math.abs(y - this.to[i][1]) > JUMP);
    this.from = jumped ? body : this.to;
    this.to = body;
    return jumped;
  }

  // t — доля пути между двумя состояниями от сервера (0..1), как у остальных участников.
  draw(t, depth) {
    const g = this.graphics;
    g.clear().setDepth(depth);
    if (!this.to) return;
    const last = this.to.length - 1;
    for (let i = last; i >= 0; i--) {              // от кончика хвоста к шее: ближние шары поверх дальних
      const [fx, fy] = this.from[i];
      const [tx, ty] = this.to[i];
      const x = cellCenterX(fx + (tx - fx) * t);
      const y = cellCenterY(fy + (ty - fy) * t) + 2;
      const radius = NECK_RADIUS - (NECK_RADIUS - TIP_RADIUS) * (i / last);
      g.fillStyle(0x1a1a1a).fillCircle(x, y, radius + 1.5);
      g.fillStyle(i % 2 ? DARK[this.tier] : LIGHT[this.tier]).fillCircle(x, y, radius);
    }
  }

  destroy() {
    this.graphics.destroy();
  }
}
