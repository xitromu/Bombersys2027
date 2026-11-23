// Разрушаемая стена и невзрываемая колонна рисуются единым образцом, а не клеткой
// старого фонового рисунка: иначе часть препятствий выглядела как пол или не тот материал.

import { CELL, cellLeft, cellTop } from './layout.js';

const SAMPLES = {
  wall: { texture: 'walls', x: 1, y: 1 },
  pillar: { texture: 'pillars', x: 0, y: 0 },
};

export function fieldCellTexture(scene, kind) {
  const key = `${kind}_cell`;
  if (!scene.textures.exists(key)) {
    const sample = SAMPLES[kind];
    const source = scene.textures.get(sample.texture).getSourceImage();
    const texture = scene.textures.createCanvas(key, CELL, CELL);
    texture.getContext().drawImage(source, sample.x * CELL, sample.y * CELL, CELL, CELL, 0, 0, CELL, CELL);
    texture.refresh();
  }
  return key;
}

export function addFieldCell(scene, kind, x, y, depth) {
  return scene.add.image(cellLeft(x), cellTop(y), fieldCellTexture(scene, kind)).setOrigin(0).setDepth(depth);
}
