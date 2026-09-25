// Глаза врагов рисуются отдельно от тела, поверх спрайта:
// обычно белые и смотрят туда, куда враг идёт; в погоне — красные и следят за игроком.

const EYE_X = [18.5, 30.5];      // центры глаз внутри кадра 49×49 (как в tools/convert_assets.py)
const EYE_Y = 24.5;
const BOB = [0, 1.5, 0, -1.5];   // тело подпрыгивает — глаза вместе с ним (по кадрам анимации)

// Текстуры глаз рисуются один раз при загрузке — в двойном размере, чтобы были чёткими.
export function createEyeTextures(scene) {
  const g = scene.make.graphics({ x: 0, y: 0 }, false);
  const eye = (key, fill) => {
    g.clear();
    g.fillStyle(0x1a1a1a).fillEllipse(10, 12, 20, 24);
    g.fillStyle(fill).fillEllipse(10, 12, 17, 21);
    g.generateTexture(key, 20, 24);
  };
  eye('eye', 0xffffff);
  eye('eye_alert', 0xff2a2a);
  g.clear();
  g.fillStyle(0x14141e).fillCircle(5, 5, 5);
  g.generateTexture('pupil', 10, 10);
  g.destroy();
}

export class EnemyEyes {
  constructor(scene) {
    this.whites = EYE_X.map(() => scene.add.image(0, 0, 'eye'));
    this.pupils = EYE_X.map(() => scene.add.image(0, 0, 'pupil'));
    this.alert = false;
  }

  setAlert(alert) {
    if (alert === this.alert) return;
    this.alert = alert;
    this.whites.forEach((white) => white.setTexture(alert ? 'eye_alert' : 'eye'));
  }

  // Ставит глаза на спрайт врага; look — направление взгляда [x, y] длиной до 1.
  follow(sprite, look = [0, 0]) {
    const scale = sprite.scaleX;
    const left = sprite.x - sprite.displayOriginX * scale;
    const top = sprite.y - sprite.displayOriginY * scale;
    const bob = BOB[Number(sprite.frame.name) % 4];
    const [lx, ly] = look[0] || look[1] ? [look[0] * 1.9, look[1] * 2.3] : [0, 1.2];
    EYE_X.forEach((ex, i) => {
      const x = left + ex * scale;
      const y = top + (EYE_Y - bob) * scale;
      this.whites[i].setPosition(x, y).setScale(scale / 2).setDepth(sprite.depth + 0.001).setAlpha(sprite.alpha);
      this.pupils[i].setPosition(x + lx * scale, y + ly * scale).setScale(scale / 2)
        .setDepth(sprite.depth + 0.002).setAlpha(sprite.alpha);
    });
  }

  destroy() {
    [...this.whites, ...this.pupils].forEach((part) => part.destroy());
  }
}
