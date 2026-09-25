// Размеры и координаты экрана — те же, что в оригинале 2005 года (окно 1018×742).

export const WIDTH = 1018;
export const HEIGHT = 742;

export const GRID = 15;
export const CELL = 49;          // клетка 49×49 пикселей
export const FIELD_X = 4;        // левый верхний угол поля
export const FIELD_Y = 4;
export const FIELD_SIZE = GRID * CELL;
export const PANEL_X = 739;      // правая панель «космический взрыв»

export const TICK_MS = 1000 / 30; // сервер присылает состояние 30 раз в секунду

// Левый верхний угол клетки (x, y) в пикселях. Дробные x, y — между клетками.
export const cellLeft = (x) => FIELD_X + x * CELL;
export const cellTop = (y) => FIELD_Y + y * CELL;
export const cellCenterX = (x) => cellLeft(x) + CELL / 2;
export const cellCenterY = (y) => cellTop(y) + CELL / 2;

// Слои: что рисуется поверх чего (больше — выше).
// Тела погибших лежат на полу (corpses). Живые игроки и враги (actors) сортируются по высоте:
// кто ниже на экране — тот рисуется поверх, как в оригинале.
export const DEPTH = {
  floor: 0, pillars: 1, walls: 2, items: 3, corpses: 3.5, flames: 4, bombs: 5,
  explosion: 6, actors: 7, popups: 9, panel: 10, overlay: 20,
};
export const actorDepth = (y) => DEPTH.actors + y / 100;

export const FONT = 'Arial, Helvetica, sans-serif';

export function textStyle(size, color, extra = {}) {
  return { fontFamily: FONT, fontSize: `${size}px`, color, resolution: 2, ...extra };
}
