// Точка входа: создаёт связь с сервером и запускает Phaser со сценами игры.
// Сцена — это «экран»: загрузка → меню (↔ настройка клавиш, ↔ игра по сети) → игра → GAME OVER → снова меню.

import { Net } from './net.js';
import { WIDTH, HEIGHT } from './layout.js';
import { BootScene } from './scenes/BootScene.js';
import { MenuScene } from './scenes/MenuScene.js';
import { KeysScene } from './scenes/KeysScene.js';
import { GameScene } from './scenes/GameScene.js';
import { GameOverScene } from './scenes/GameOverScene.js';
import { NetScene } from './scenes/NetScene.js';
import { MODE_LABELS, sound } from './audio/sound.js';

const game = new Phaser.Game({
  type: Phaser.AUTO,
  parent: 'game',
  width: WIDTH,
  height: HEIGHT,
  backgroundColor: '#000000',
  scale: { mode: Phaser.Scale.FIT, autoCenter: Phaser.Scale.CENTER_BOTH },
  scene: [BootScene, MenuScene, KeysScene, NetScene, GameScene, GameOverScene],
});

// Общие для всех сцен вещи кладём в registry — «общую полку» Phaser.
game.registry.set('net', new Net());

// Звук: M или кнопка в углу переключают «всё → без музыки → тишина», − и + — громкость.
sound.init();
const soundButton = document.getElementById('sound');
const showSound = () => {
  soundButton.textContent = sound.mode === 'off' ? MODE_LABELS.off : `${MODE_LABELS[sound.mode]} · ${sound.volume}%`;
};
const SOUND_KEYS = {
  KeyM: () => sound.cycleMode(),
  Minus: () => sound.changeVolume(-10), NumpadSubtract: () => sound.changeVolume(-10),
  Equal: () => sound.changeVolume(10), NumpadAdd: () => sound.changeVolume(10),
};
showSound();
for (const [id, action] of [['sound', 'KeyM'], ['volume-down', 'Minus'], ['volume-up', 'Equal']]) {
  const button = document.getElementById(id);
  button.addEventListener('click', () => {
    SOUND_KEYS[action]();
    showSound();
    button.blur(); // иначе Пробел/Enter в игре снова «нажмут» кнопку
  });
}
window.addEventListener('keydown', (event) => {
  if (SOUND_KEYS[event.code] && !(event.repeat && event.code === 'KeyM')) {
    SOUND_KEYS[event.code]();
    showSound();
  }
});

// Кнопка «На весь экран» — обычная HTML-кнопка поверх игры.
const fullscreen = document.getElementById('fullscreen');
if (!document.fullscreenEnabled) fullscreen.hidden = true;
fullscreen.addEventListener('click', () => {
  if (document.fullscreenElement) document.exitFullscreen();
  else document.documentElement.requestFullscreen();
  fullscreen.blur(); // иначе Пробел/Enter в игре снова «нажмут» кнопку
});
document.addEventListener('fullscreenchange', () => {
  fullscreen.textContent = document.fullscreenElement ? '✕ Обычный экран' : '⛶ На весь экран';
});
