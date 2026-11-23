// Клетки большого фонового рисунка превращаем в отдельные текстуры и рисуем ровно там,
// где сервер поставил стену или колонну.

import { CELL, cellLeft, cellTop } from './layout.js';

export function fieldCellTexture(scene, sourceKey, x, y) {
  const key = `${sourceKey}_cell_${x}_${y}`;
  if (!scene.textures.exists(key)) {
    const source = scene.textures.get(sourceKey).getSourceImage();
    const texture = scene.textures.createCanvas(key, CELL, CELL);
    texture.getContext().drawImage(source, x * CELL, y * CELL, CELL, CELL, 0, 0, CELL, CELL);
    texture.refresh();
  }
  return key;
}

export function addFieldCell(scene, sourceKey, x, y, depth) {
  return scene.add.image(cellLeft(x), cellTop(y), fieldCellTexture(scene, sourceKey, x, y)).setDepth(depth);
}
