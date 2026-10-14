// Оформление «блиндаж»: дощатая стена и приколотые к ней листки. Всё рисуется на холсте, без готовых
// картинок — кроме фотографий героев (photo<N>.png: новые лица, их рисует и кладёт в игру mockups/photos)
// и бомбы на счётчике (та же, что на поле). Из этих кирпичиков собраны правая панель игры и меню и экран GAME OVER.

import { DETAIL, addCanvas, canvasTexture } from './canvasTexture.js';
import { CELL, DEPTH, FONT, HEIGHT, PANEL_X, WIDTH, textStyle } from './layout.js';

export const INK = '#120d0a';
export const PAPER = { text: '#2b1a0c', dim: '#6b5335', accent: '#a01818', photo: '#cdb98a', light: '#f6e7bd' };

const PANEL_W = WIDTH - PANEL_X;
const SEPIA = 0.5;                   // насколько фотография выцвела: 0 — цвета как были, 1 — одна коричневая сепия
const PHOTO = [5, 9, 98, 116];       // место фотографии на листке-карточке
const COUNTS = [151, 108, 130];      // листок со счётчиками героя: отступ слева, ширина, высота
const RED = '#e02424';               // штамп «ПОГИБ» и рамка «ВОСКРЕСИТЬ»
const cardY = (i) => 361 + 170 * i;  // карточки героев: Иван выше, Игорь ниже; под ними — полоса для кнопок страницы
export const BUTTONS = [PANEL_X + PANEL_W / 2, 714];   // середина этой полосы: сюда main.js ставит кнопки звука и экрана

const rnd = (i, k = 0) => {
  const v = Math.sin(i * 127.1 + k * 311.7) * 43758.5453;
  return v - Math.floor(v);
};

// ------------------------------------------------------------ стена, листки, значки

export function planks(g, w, h) {
  for (let x = 0, i = 0; x < w; i++) {
    const pw = 44 + 14 * rnd(i);
    const tone = 0.85 + 0.3 * rnd(i, 1);
    const paint = g.createLinearGradient(x, 0, x + pw, 0);
    paint.addColorStop(0, `rgb(${Math.round(96 * tone)}, ${Math.round(62 * tone)}, ${Math.round(32 * tone)})`);
    paint.addColorStop(1, `rgb(${Math.round(74 * tone)}, ${Math.round(46 * tone)}, ${Math.round(22 * tone)})`);
    g.fillStyle = paint;
    g.fillRect(x, 0, pw, h);
    g.strokeStyle = 'rgba(20, 10, 4, 0.35)';
    g.lineWidth = 1;
    for (let k = 0; k < 5; k++) {                             // волокна
      const gx = x + pw * rnd(i * 9 + k, 2);
      g.beginPath();
      g.moveTo(gx, 0);
      for (let y = 0; y <= h; y += 40) g.lineTo(gx + 3 * Math.sin(y * 0.02 + k + i), y);
      g.stroke();
    }
    g.fillStyle = 'rgba(15, 8, 3, 0.8)';                      // щель между досками
    g.fillRect(x + pw - 1.5, 0, 2, h);
    g.fillStyle = '#1c120a';                                  // шляпки гвоздей
    for (const y of [9, h - 9]) {
      g.beginPath();
      g.arc(x + pw / 2, y, 2, 0, Math.PI * 2);
      g.fill();
    }
    x += pw;
  }
}

// Листок бумаги с тенью; на больших — красная кнопка, которой он приколот.
export function sheet(g, x, y, w, h) {
  g.fillStyle = 'rgba(0, 0, 0, 0.4)';
  g.fillRect(x + 3, y + 4, w, h);
  const paint = g.createLinearGradient(x, y, x + w, y + h);
  paint.addColorStop(0, '#f0e0b6');
  paint.addColorStop(1, '#d6c08c');
  g.fillStyle = paint;
  g.fillRect(x, y, w, h);
  g.strokeStyle = '#8a6a33';
  g.lineWidth = 1.2;
  g.strokeRect(x + 0.5, y + 0.5, w - 1, h - 1);
  if (h < 40) return;
  g.beginPath();
  g.arc(x + w / 2, y + 6, 3.4, 0, Math.PI * 2);
  g.fillStyle = '#b3201c';
  g.fill();
  g.lineWidth = 1;
  g.strokeStyle = INK;
  g.stroke();
}

export function heart(g, x, y, k = 1) {
  g.save();
  g.translate(x, y);
  g.scale(k, k);
  g.beginPath();
  g.moveTo(0, 15);
  g.bezierCurveTo(-21, 0, -13, -18, 0, -7);
  g.bezierCurveTo(13, -18, 21, 0, 0, 15);
  g.closePath();
  const paint = g.createLinearGradient(-9, -12, 9, 14);
  paint.addColorStop(0, '#ff6a6a');
  paint.addColorStop(1, '#b0101c');
  g.fillStyle = paint;
  g.fill();
  g.lineWidth = 1.6;
  g.strokeStyle = INK;
  g.stroke();
  g.fillStyle = 'rgba(255, 255, 255, 0.6)';
  g.beginPath();
  g.ellipse(-6.5, -5.5, 3.4, 2.2, 0, 0, Math.PI * 2);
  g.fill();
  g.restore();
}

// Рабочий холст width × height точек: на нём картинку правят по точкам (edit получает [r, g, b, a, …]
// и номер точки), прежде чем положить на листок.
function retouched(width, height, draw, edit) {
  const canvas = document.createElement('canvas');
  canvas.width = width;
  canvas.height = height;
  const c = canvas.getContext('2d', { willReadFrequently: true });
  draw(c);
  const image = c.getImageData(0, 0, width, height);
  for (let i = 0; i < image.data.length; i += 4) edit(image.data, i, i / 4);
  c.putImageData(image, 0, 0);
  return canvas;
}

// Бомба на счётчике — та же связка динамита, что ставит герой n (первый кадр bomb<n>.png), в его цвете:
// красная у Ивана, зелёная у Игоря. Середина картинки — в (x, y); размер как на поле.
function bombIcon(g, scene, n, x, y) {
  const sprite = scene.textures.get(`bomb${n}`).getSourceImage();
  g.imageSmoothingEnabled = false;                            // точка в точку, как на поле
  g.drawImage(sprite, 0, 0, CELL, CELL, x - CELL / 2, y - CELL / 2, CELL, CELL);
  g.imageSmoothingEnabled = true;
}

// ------------------------------------------------------------ портреты

// Фотография героя n в прямоугольнике w × h с левым верхним углом (x, y): портрет photo<n>.png,
// состаренный под фотокарточку — цвета выцвели, зерно, тёмные углы, светлое поле по краю.
function photo(g, scene, n, x, y, w, h) {
  const face = scene.textures.get(`photo${n}`).getSourceImage();
  const width = w * DETAIL, height = h * DETAIL;
  const card = retouched(width, height, (c) => {
    c.imageSmoothingQuality = 'high';
    c.drawImage(face, 0, 0, width, height);
  }, (px, i, k) => {
    const cx = (k % width) / width - 0.5, cy = Math.floor(k / width) / height - 0.5;
    const shade = 1 - 0.9 * (cx * cx + cy * cy);              // к углам темнее
    const grain = (rnd(k, n) - 0.5) * 14;
    const light = 0.299 * px[i] + 0.587 * px[i + 1] + 0.114 * px[i + 2];
    [light * 1.08 + 14, light * 0.95 + 6, light * 0.74].forEach((brown, c) => {
      px[i + c] = (px[i + c] + (brown - px[i + c]) * SEPIA) * shade + grain;
    });
  });
  g.drawImage(card, x, y, w, h);
  g.strokeStyle = 'rgba(246, 231, 189, 0.85)';                // поле фотобумаги
  g.lineWidth = 2;
  g.strokeRect(x + 1.5, y + 1.5, w - 3, h - 3);
  g.strokeStyle = INK;
  g.lineWidth = 1;
  g.strokeRect(x + 0.5, y + 0.5, w - 1, h - 1);
}

// Та же фотография, но выцветшая и со штампом «ПОГИБ» — ложится поверх обычной.
function deadPhoto(scene, n) {
  const [, , w, h] = PHOTO;
  return canvasTexture(scene, `bunker_dead${n}`, w, h, (g) => {
    photo(g, scene, n, 0, 0, w, h);
    const image = g.getImageData(0, 0, g.canvas.width, g.canvas.height);
    const px = image.data;
    for (let i = 0; i < px.length; i += 4) {
      px[i] = px[i + 1] = px[i + 2] = (0.299 * px[i] + 0.587 * px[i + 1] + 0.114 * px[i + 2]) * 0.55;
    }
    g.putImageData(image, 0, 0);
    g.translate(w / 2, h / 2 + 3);
    g.rotate(-0.3);
    g.strokeStyle = RED;
    g.lineWidth = 2.5;
    g.strokeRect(-40, -13, 80, 26);
    g.font = `bold 20px ${FONT}`;
    g.textAlign = 'center';
    g.textBaseline = 'middle';
    g.fillStyle = RED;
    g.fillText('ПОГИБ', 0, 1);
  });
}

// Листок «ВОСКРЕСИТЬ» — ложится поверх счётчиков погибшего: кто из героев (name) и какой клавишей (key)
// может его поднять и чего это стоит.
function reviveNote(scene, name, key) {
  const [, w, h] = COUNTS;
  return canvasTexture(scene, `bunker_revive_${name}_${key}`, w, h, (g) => {
    const label = (text, y, font, color) => {
      g.font = `${font} ${FONT}`;
      g.fillStyle = color;
      g.fillText(text, w / 2, y);
    };
    sheet(g, 0, 0, w, h);
    g.textAlign = 'center';
    g.textBaseline = 'middle';
    label('ВОСКРЕСИТЬ', 27, 'bold 14px', PAPER.accent);
    label(`${name}, жми`, 49, '13px', PAPER.dim);
    g.font = `bold 14px ${FONT}`;                             // клавиша — «колпачок» по ширине надписи
    const cap = Math.max(30, g.measureText(key).width + 14);
    g.beginPath();
    if (g.roundRect) g.roundRect(w / 2 - cap / 2, 61, cap, 26, 5);
    else g.rect(w / 2 - cap / 2, 61, cap, 26);
    g.fillStyle = '#f4f4f4';
    g.fill();
    g.lineWidth = 1.5;
    g.strokeStyle = INK;
    g.stroke();
    label(key, 75, 'bold 14px', INK);
    heart(g, w / 2 - 19, 108, 0.62);                          // цена: одна своя жизнь
    g.font = `bold 18px ${FONT}`;
    g.fillStyle = PAPER.text;
    g.fillText('−1', w / 2 + 8, 109);
  });
}

// ------------------------------------------------------------ правая панель

// players — сколько героев в игре: карточка героя, которого нет, притушена.
// revive — для игры: [{ name, key }, …] по героям — как зовут и какой клавишей он воскрешает напарника.
// Возвращает надписи и листки, которые меняются по ходу игры.
export function addPanel(scene, players = 2, revive = null) {
  const key = canvasTexture(scene, `bunker_panel${players}`, PANEL_W, HEIGHT, (g) => {
    planks(g, PANEL_W, HEIGHT);
    sheet(g, 21, 10, 238, 148);                               // сводка: уровень, враги, очки
    sheet(g, 21, 166, 238, 188);                              // листок с хокку
    for (let i = 0; i < 2; i++) {
      const y = cardY(i);
      sheet(g, 21, y, 108, 130);
      photo(g, scene, i + 1, 21 + PHOTO[0], y + PHOTO[1], PHOTO[2], PHOTO[3]);
      sheet(g, COUNTS[0], y, COUNTS[1], COUNTS[2]);
      heart(g, 178, y + 36, 1.05);
      bombIcon(g, scene, i + 1, 177, y + 92);
      sheet(g, 21, y + 134, 108, 24);
      sheet(g, 151, y + 134, 108, 24);
      if (i >= players) {
        g.fillStyle = 'rgba(46, 28, 12, 0.62)';
        g.fillRect(17, y - 4, 248, 168);
      }
    }
  });
  addCanvas(scene, PANEL_X, 0, key).setDepth(DEPTH.panel);

  const top = DEPTH.panel + 1;
  const bold = { fontStyle: 'bold' };
  const text = (x, y, size, color, extra) =>
    scene.add.text(PANEL_X + x, y, '', textStyle(size, color, extra)).setOrigin(0.5).setDepth(top);
  return {
    title: text(140, 42, 27, PAPER.accent, bold),
    line1: text(140, 90, 22, PAPER.text),
    line2: text(140, 124, 22, PAPER.text),
    noteTitle: text(140, 194, 17, PAPER.accent, bold),
    note: text(140, 222, 16, PAPER.text, {
      fontStyle: 'italic', align: 'center', lineSpacing: 12, wordWrap: { width: 220 },
    }).setOrigin(0.5, 0),
    version: text(PANEL_W - 6, HEIGHT - 8, 11, PAPER.light).setOrigin(1, 0.5),
    heroes: [0, 1].map((i) => {
      const y = cardY(i);
      const parts = {
        lives: text(226, y + 37, 26, PAPER.text, bold),
        bombs: text(226, y + 92, 26, PAPER.text, bold),
        name: text(75, y + 147, 16, PAPER.text, bold),
        score: text(205, y + 147, 16, PAPER.text, bold),
      };
      if (i >= players) for (const part of Object.values(parts)) part.setAlpha(0.35);
      parts.dead = addCanvas(scene, PANEL_X + 21 + PHOTO[0], y + PHOTO[1], deadPhoto(scene, i + 1))
        .setDepth(top).setVisible(false);
      parts.revive = [];                 // листок «ВОСКРЕСИТЬ» и мигающая рамка: напарник может поднять этого героя
      if (revive && players === 2) {
        const [left, w, h] = COUNTS;
        const other = revive[1 - i];
        const frame = scene.add.rectangle(PANEL_X + left + w / 2, y + h / 2, w - 5, h - 5)
          .setStrokeStyle(3, Phaser.Display.Color.HexStringToColor(RED).color);
        scene.tweens.add({ targets: frame, alpha: { from: 1, to: 0.3 }, duration: 320, yoyo: true, repeat: -1 });
        parts.revive = [addCanvas(scene, PANEL_X + left, y, reviveNote(scene, other.name, other.key)), frame];
        parts.revive.forEach((part, layer) => part.setDepth(top + 1 + layer).setVisible(false));
      }
      return parts;
    }),
  };
}

export const count = (n) => `× ${n}`;
export const points = (n) => n.toLocaleString('ru-RU');
