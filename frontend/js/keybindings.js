// Раскладка клавиш: какие клавиши у кого. Хранится в браузере (localStorage),
// поэтому после настройки запоминается навсегда — для этого компьютера и браузера.
// Клавиши записаны «физически» (event.code), так что русская раскладка не мешает.

export const ACTIONS = ['up', 'down', 'left', 'right', 'bomb', 'revive'];
export const ACTION_NAMES = {
  up: 'Вверх', down: 'Вниз', left: 'Влево', right: 'Вправо', bomb: 'Бомба', revive: 'Воскресить',
};
// пауза, выход, звук и громкость — заняты всегда
export const RESERVED = ['KeyP', 'Pause', 'Escape', 'KeyM', 'Minus', 'Equal', 'NumpadSubtract', 'NumpadAdd'];

export const DEFAULT_BINDINGS = [
  { up: 'KeyW', down: 'KeyS', left: 'KeyA', right: 'KeyD', bomb: 'Space', revive: 'KeyE' },
  { up: 'ArrowUp', down: 'ArrowDown', left: 'ArrowLeft', right: 'ArrowRight', bomb: 'Enter', revive: 'ShiftRight' },
];

const STORAGE_KEY = 'bombersys.keys';

export function loadBindings() {
  try {
    const saved = JSON.parse(localStorage.getItem(STORAGE_KEY));
    if (Array.isArray(saved) && saved.length === 2) {
      const bindings = saved.map((set, i) => ({ ...DEFAULT_BINDINGS[i], ...set }));
      // Действие появилось в игре позже, чем раскладку сохранили, а его клавишу игрок уже отдал
      // другому действию — оставляем его без клавиши: назначат в настройке.
      const taken = saved.flatMap((set) => Object.values(set ?? {}));
      bindings.forEach((keys, i) => {
        for (const action of ACTIONS) {
          if (!(action in (saved[i] ?? {})) && taken.includes(keys[action])) keys[action] = null;
        }
      });
      return bindings;
    }
  } catch {
    // нет доступа к хранилищу или там мусор — берём раскладку по умолчанию
  }
  return structuredClone(DEFAULT_BINDINGS);
}

export function saveBindings(bindings) {
  try {
    localStorage.setItem(STORAGE_KEY, JSON.stringify(bindings));
  } catch {
    // не сохранилось — раскладка проработает до перезагрузки страницы
  }
}

const SPECIAL = {
  Space: 'Пробел', Enter: 'Enter', NumpadEnter: 'Enter (цифр.)', Delete: 'Delete', Backspace: 'Backspace',
  ArrowUp: '↑', ArrowDown: '↓', ArrowLeft: '←', ArrowRight: '→', Tab: 'Tab', Insert: 'Insert',
  ShiftLeft: 'Shift левый', ShiftRight: 'Shift правый', ControlLeft: 'Ctrl левый', ControlRight: 'Ctrl правый',
  AltLeft: 'Alt левый', AltRight: 'Alt правый', Home: 'Home', End: 'End', PageUp: 'PgUp', PageDown: 'PgDn',
};

// Понятное название клавиши: KeyW → W, Digit5 → 5, Numpad8 → Цифр. 8
export function keyLabel(code) {
  if (!code) return '—';
  if (SPECIAL[code]) return SPECIAL[code];
  if (code.startsWith('Key')) return code.slice(3);
  if (code.startsWith('Digit')) return code.slice(5);
  if (code.startsWith('Numpad')) return `Цифр. ${code.slice(6)}`;
  return code;
}
