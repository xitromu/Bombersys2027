// Маленький синтезатор в духе игровых автоматов 80–90-х: прямоугольная волна разной «ширины»,
// треугольная (ею играли басы) и шум (взрывы и барабаны). Из этих кирпичиков собраны
// и музыка, и все звуковые эффекты — готовых звуковых файлов для них не нужно.
//
// Звук идёт по трём «шинам» со своей громкостью: музыка, эффекты, голоса.

const PULSES = { square12: 0.125, square25: 0.25, square50: 0.5 };
const NOISE_SECONDS = 1;

export class Synth {
  // context можно передать свой — например, OfflineAudioContext для проверки звуков без колонок
  constructor(context) {
    this.ctx = context ?? new (window.AudioContext || window.webkitAudioContext)();
    // ограничитель: срезает только пики у самого потолка, чтобы звук не «хрипел»,
    // когда разом рвётся десяток бомб; тихое не подтягивает — баланс громкостей сохраняется
    const limiter = this.ctx.createDynamicsCompressor();
    limiter.threshold.value = -3;
    limiter.knee.value = 0;
    limiter.ratio.value = 20;
    limiter.attack.value = 0.003;
    limiter.release.value = 0.25;
    limiter.connect(this.ctx.destination);
    this.master = this.gain(limiter, 0.8);
    this.buses = {
      music: this.gain(this.master, 0.22),
      sfx: this.gain(this.master, 0.6),
      voice: this.gain(this.master, 1.0),
    };
    this.waves = {};
    for (const [name, duty] of Object.entries(PULSES)) this.waves[name] = this.pulseWave(duty);
    this.noiseBuffer = this.ctx.createBuffer(1, this.ctx.sampleRate * NOISE_SECONDS, this.ctx.sampleRate);
    const data = this.noiseBuffer.getChannelData(0);
    for (let i = 0; i < data.length; i++) data[i] = Math.random() * 2 - 1;
  }

  get now() {
    return this.ctx.currentTime;
  }

  gain(destination, value) {
    const node = this.ctx.createGain();
    node.gain.value = value;
    node.connect(destination);
    return node;
  }

  // Прямоугольная волна со «скважностью» duty — из суммы гармоник (ряд Фурье).
  pulseWave(duty) {
    const n = 64;
    const real = new Float32Array(n);
    const imag = new Float32Array(n);
    for (let k = 1; k < n; k++) {
      real[k] = Math.sin(2 * Math.PI * k * duty) / (k * Math.PI);
      imag[k] = (1 - Math.cos(2 * Math.PI * k * duty)) / (k * Math.PI);
    }
    return this.ctx.createPeriodicWave(real, imag);
  }

  // Выход звука: огибающая громкости (нарастание → спад → удержание → затухание) и панорама.
  envelope(bus, { at, dur, vol = 0.5, attack = 0.005, decay = 0, sustain = 1, release = 0.04, pan = 0 }) {
    const env = this.ctx.createGain();
    const g = env.gain;
    g.setValueAtTime(0, at);
    g.linearRampToValueAtTime(vol, at + attack);
    if (decay > 0) g.linearRampToValueAtTime(vol * sustain, at + attack + decay);
    const holdUntil = Math.max(at + attack + decay, at + dur);
    g.setValueAtTime(decay > 0 ? vol * sustain : vol, holdUntil);
    g.linearRampToValueAtTime(0, holdUntil + release);
    let out = this.buses[bus];
    if (pan && this.ctx.createStereoPanner) {
      const panner = this.ctx.createStereoPanner();
      panner.pan.value = Math.max(-1, Math.min(1, pan));
      panner.connect(out);
      out = panner;
    }
    env.connect(out);
    return { node: env, end: holdUntil + release };
  }

  // Тон. freq — частота в Гц; to — куда «съехать» за время звучания;
  // steps — [[секунды от начала, частота], …] для арпеджио; vibrato — {rate, cents, delay}.
  tone(bus, { wave = 'square50', freq, to, steps, vibrato, ...env }) {
    const { node, end } = this.envelope(bus, env);
    const osc = this.ctx.createOscillator();
    if (this.waves[wave]) osc.setPeriodicWave(this.waves[wave]);
    else osc.type = wave;
    const f = osc.frequency;
    f.setValueAtTime(freq, env.at);
    if (to) f.exponentialRampToValueAtTime(to, end);
    for (const [offset, value] of steps ?? []) f.setValueAtTime(value, env.at + offset);
    if (vibrato) {
      const lfo = this.ctx.createOscillator();
      const depth = this.ctx.createGain();
      lfo.frequency.value = vibrato.rate ?? 6;
      depth.gain.setValueAtTime(0, env.at);
      depth.gain.linearRampToValueAtTime(vibrato.cents ?? 20, env.at + (vibrato.delay ?? 0.1) + 0.05);
      lfo.connect(depth).connect(osc.detune);
      lfo.start(env.at);
      lfo.stop(end);
    }
    osc.connect(node);
    return this.run(osc, env.at, end);
  }

  // Шум через фильтр. rate < 1 делает шум «крупнее» и грязнее — как на старых приставках.
  noise(bus, { filter = 'lowpass', freq = 2000, to, q = 1, rate = 1, ...env }) {
    const { node, end } = this.envelope(bus, env);
    const src = this.ctx.createBufferSource();
    src.buffer = this.noiseBuffer;
    src.loop = true;
    src.playbackRate.value = rate;
    const biquad = this.ctx.createBiquadFilter();
    biquad.type = filter;
    biquad.Q.value = q;
    biquad.frequency.setValueAtTime(freq, env.at);
    if (to) biquad.frequency.exponentialRampToValueAtTime(to, end);
    src.connect(biquad).connect(node);
    return this.run(src, env.at, end, Math.random() * (NOISE_SECONDS - 0.1));
  }

  run(source, at, end, offset = 0) {
    source.start(at, offset);
    source.stop(end + 0.02);
    source.onended = () => source.disconnect();
    return source;
  }

  // Ударные для музыки: k — бочка, s — малый барабан, h — закрытый хэт, o — открытый, c — тарелка.
  drum(bus, hit, at, vol = 1) {
    switch (hit) {
      case 'k':
        this.tone(bus, { wave: 'triangle', freq: 160, to: 40, at, dur: 0.08, vol: 0.9 * vol, release: 0.06 });
        this.noise(bus, { filter: 'lowpass', freq: 1200, at, dur: 0.01, vol: 0.3 * vol, release: 0.02 });
        break;
      case 's':
        this.noise(bus, { filter: 'bandpass', freq: 1800, q: 0.8, rate: 0.6, at, dur: 0.03, vol: 0.7 * vol, release: 0.1 });
        this.tone(bus, { wave: 'triangle', freq: 220, to: 140, at, dur: 0.03, vol: 0.4 * vol, release: 0.04 });
        break;
      case 'h':
        this.noise(bus, { filter: 'highpass', freq: 7000, at, dur: 0.01, vol: 0.25 * vol, release: 0.03 });
        break;
      case 'o':
        this.noise(bus, { filter: 'highpass', freq: 6000, at, dur: 0.05, vol: 0.22 * vol, release: 0.15 });
        break;
      case 'c':
        this.noise(bus, { filter: 'highpass', freq: 4500, rate: 0.8, at, dur: 0.05, vol: 0.35 * vol, release: 0.8 });
        break;
      default:
        throw new Error(`неизвестный удар «${hit}»`);
    }
  }
}
