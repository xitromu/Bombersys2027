// Точка входа: создаёт связь с сервером и запускает Phaser со сценами игры.
// Сцена — это «экран»: загрузка → меню (↔ настройка клавиш) → игра → GAME OVER → снова меню.

import { Net } from './net.js';
import { WIDTH, HEIGHT } from './layout.js';
import { BootScene } from './scenes/BootScene.js';
import { MenuScene } from './scenes/MenuScene.js';
import { KeysScene } from './scenes/KeysScene.js';
import { GameScene } from './scenes/GameScene.js';
import { GameOverScene } from './scenes/GameOverScene.js';

const game = new Phaser.Game({
  type: Phaser.AUTO,
  parent: 'game',
  width: WIDTH,
  height: HEIGHT,
  backgroundColor: '#000000',
  scale: { mode: Phaser.Scale.FIT, autoCenter: Phaser.Scale.CENTER_BOTH },
  scene: [BootScene, MenuScene, KeysScene, GameScene, GameOverScene],
});

// Общие для всех сцен вещи кладём в registry — «общую полку» Phaser.
game.registry.set('net', new Net());

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
