// Озвучка партии: по состоянию, которое 30 раз в секунду присылает сервер, решает, что и когда звучит.
// Сам сервер про звук ничего не знает — всё, что нужно, уже есть в его событиях и состоянии.

import { GRID } from '../layout.js';
import { sound } from './sound.js';

const LEVEL_SONGS = ['levelA', 'levelB'];
const HURRY_TEMPO = 1.2;          // остался последний призрак — музыка ускоряется
const NOTICE_REPEAT = 6;          // один и тот же призрак «ухает» не чаще раза в 6 с…
const NOTICE_GAP = 1.2;           // …а все вместе — не чаще раза в 1,2 с
const KILL_VOICE_GAP = 2.5;       // «Target destroyed!» не чаще раза в 2,5 с
const COINS = new Set(['bag', 'bigbag', 'gems', 'legacy']);
const KOLYAN_RATE = 0.86;         // у Коляна голос ниже — тот же диктор, но замедленный

const panOf = (x) => ((x / (GRID - 1)) * 2 - 1) * 0.7;
const heroRate = (player) => (player === 1 ? KOLYAN_RATE : 1);
const seconds = () => performance.now() / 1000;

export class GameAudio {
  constructor() {
    this.phase = null;
    this.chasing = new Map();     // id призрака → гнался ли он в прошлый раз
    this.noticedAt = new Map();   // id призрака → когда «ухнул»
    this.lastNotice = -Infinity;
    this.lastKillVoice = -Infinity;
  }

  update(state) {
    this.onPhase(state);
    this.onEvents(state);
    this.onEnemies(state);
  }

  onPhase(state) {
    const before = this.phase;
    const now = state.phase;
    this.phase = now;
    if (before === now) {
      if (now === 'playing') sound.tempo(state.enemies.length === 1 ? HURRY_TEMPO : 1);
      return;
    }
    if (before === 'paused' || now === 'paused') sound.pause(now === 'paused');
    if (now === 'ready') {
      sound.jingle('levelStart');
      sound.say('fighter_ready');
    } else if (now === 'playing' && before === 'ready') {
      sound.say('fighter_fight');
      sound.music(LEVEL_SONGS[(state.level - 1) % LEVEL_SONGS.length]);
    } else if (now === 'level_done') {
      const next = state.result === 'next';
      sound.jingle(next ? 'levelClear' : 'levelFail');
      sound.say(next ? 'female_mission_completed' : 'female_mission_failed');
    } else if (now === 'game_over') {
      sound.jingle('gameOver');
      sound.say('fighter_game_over');
    }
  }

  onEvents(state) {
    let explosions = 0;
    let walls = 0;
    const kills = [];
    for (const e of state.events) {
      const pan = e.x === undefined || e.x === null ? 0 : panOf(e.x);
      switch (e.type) {
        case 'bomb_placed':
          sound.play('bomb', { pan });
          break;
        case 'explosion':
          explosions++;
          break;
        case 'wall_destroyed':
          walls++;
          break;
        case 'enemy_killed':
          kills.push(e);
          sound.play('ghostKilled', { pan, pitch: 1 - e.tier * 0.12 });
          break;
        case 'all_enemies_killed':
          sound.say('female_objective_achieved');
          if (e.door_unlocked) sound.play('doorOpen', { pan: panOf(e.x), delay: 0.3 });
          break;
        case 'player_died':
          this.onDeath(state, e);
          break;
        case 'item_destroyed':
          sound.play('giftBurn', { pan });
          break;
        case 'door_locked':
          sound.play('doorBreak', { pan });
          sound.say('female_wrong');
          break;
        case 'door_closed':
          sound.play('doorClosed', { pan, minGap: 1 });
          break;
        case 'item_taken':
          this.onItem(e, pan);
          break;
        case 'extra_life':
          sound.jingle('oneUp', { overMusic: true });
          break;
        case 'player_exited':
          sound.play('exit');
          break;
        default:
          break;
      }
    }
    // Взрывы и стены за один «тик» — одним звуком, чуть громче, если их много.
    if (explosions) sound.play('explosion', { vol: Math.min(1.3, 0.85 + 0.15 * explosions), pitch: 0.9 + Math.random() * 0.2, minGap: 0.06 });
    if (walls) sound.play('wall', { minGap: 0.05 });
    if (kills.length >= 2) {
      sound.say('fighter_multi_kill');
    } else if (kills.length === 1 && seconds() - this.lastKillVoice > KILL_VOICE_GAP) {
      this.lastKillVoice = seconds();
      sound.say('male_war_target_destroyed', { rate: heroRate(kills[0].player) });
    }
  }

  onDeath(state, e) {
    const victim = state.players[e.player];
    const pan = victim ? panOf(victim.x) : 0;
    if (e.cause === 'enemy' || e.cause === 'trap') {
      if (e.cause === 'trap') sound.play('trap', { pan });
      // злорадствуют все призраки, но не больше трёх голосов, каждый своим тоном
      const laughers = Math.max(1, Math.min(3, state.enemies.length));
      [1, 0.8, 1.25].slice(0, laughers).forEach((pitch, i) =>
        sound.play('ghostLaugh', { pan: pan * (1 - i * 0.4), pitch, delay: (e.cause === 'trap' ? 0.3 : 0) + i * 0.18 }));
    } else if (e.cause === 'bomb' && e.killer !== null && e.killer !== undefined && e.killer !== e.player) {
      sound.jingle('victory', { overMusic: true });
      sound.say(e.kind === 'super' ? 'fighter_flawless_victory' : 'fighter_winner');
    }
  }

  onItem(e, pan) {
    if (COINS.has(e.kind)) sound.play('coin', { pan });
    else if (e.kind === 'chest') sound.play('chest', { pan });
    else if (e.kind === 'bomb') {
      sound.play('powerUp', { pan });
      sound.say('male_power_up', { rate: heroRate(e.player) });
    } else if (e.kind === 'life') sound.jingle('oneUp', { overMusic: true });
    // череп (death) озвучивается гибелью героя, дверь — входом в неё
  }

  // Призрак перестал бродить наугад и пошёл на игрока — «у-у?»
  onEnemies(state) {
    const now = seconds();
    const alive = new Set();
    for (const enemy of state.enemies) {
      alive.add(enemy.id);
      const was = this.chasing.get(enemy.id) ?? false;
      this.chasing.set(enemy.id, enemy.chasing);
      if (state.phase !== 'playing' || !enemy.chasing || was) continue;
      if (now - (this.noticedAt.get(enemy.id) ?? -Infinity) < NOTICE_REPEAT || now - this.lastNotice < NOTICE_GAP) continue;
      this.noticedAt.set(enemy.id, now);
      this.lastNotice = now;
      sound.play('ghostNotice', { pan: panOf(enemy.x), pitch: 1 - enemy.tier * 0.1 });
    }
    for (const id of this.chasing.keys()) {
      if (!alive.has(id)) {
        this.chasing.delete(id);
        this.noticedAt.delete(id);
      }
    }
  }
}
