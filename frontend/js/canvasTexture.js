// Картинки, нарисованные на холсте при запуске, — вместо готовых файлов. Холсты вдвое подробнее экрана:
// когда игру растягивают на весь экран, картинка остаётся чёткой.

export const DETAIL = 2;

// Холст-текстура key размером width × height точек экрана; draw(g) рисует в точках экрана.
// Готовую второй раз не рисуем.
export function canvasTexture(scene, key, width, height, draw) {
  if (scene.textures.exists(key)) return key;
  const texture = scene.textures.createCanvas(key, width * DETAIL, height * DETAIL);
  texture.context.scale(DETAIL, DETAIL);
  draw(texture.context);
  texture.refresh();
  return key;
}

// Картинка из такой текстуры: левый верхний угол в (x, y), размер — в точках экрана.
export const addCanvas = (scene, x, y, key) => scene.add.image(x, y, key).setOrigin(0).setScale(1 / DETAIL);
