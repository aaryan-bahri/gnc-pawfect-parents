// Code-made chiptune SFX (Web Audio). Audio starts only after the first click (browser rule).
let ctx = null;
let muted = false;

function tone(freq, start, dur, { type = 'square', vol = 0.08, slide = 0 } = {}) {
  const o = ctx.createOscillator();
  const g = ctx.createGain();
  o.type = type;
  o.frequency.setValueAtTime(freq, ctx.currentTime + start);
  if (slide) o.frequency.linearRampToValueAtTime(freq + slide, ctx.currentTime + start + dur);
  g.gain.setValueAtTime(vol, ctx.currentTime + start);
  g.gain.exponentialRampToValueAtTime(0.0001, ctx.currentTime + start + dur);
  o.connect(g).connect(ctx.destination);
  o.start(ctx.currentTime + start);
  o.stop(ctx.currentTime + start + dur + 0.02);
}

const SOUNDS = {
  chime: () => [523, 659, 784].forEach((f, i) => tone(f, i * 0.08, 0.18)),          // right answer
  boop:  () => tone(220, 0, 0.18, { type: 'triangle', vol: 0.12, slide: -60 }),     // gentle wrong
  wag:   () => [0, 0.09].forEach(t => tone(880, t, 0.05, { vol: 0.05 })),
  bark:  () => tone(420, 0, 0.09, { type: 'sawtooth', vol: 0.06, slide: -180 }),
  click: () => tone(660, 0, 0.04, { vol: 0.05 }),
  page:  () => tone(300, 0, 0.12, { type: 'triangle', vol: 0.07, slide: 400 }),
  win:   () => [523, 659, 784, 1047].forEach((f, i) => tone(f, i * 0.12, 0.25)),
};

export const sfx = {
  unlock() {
    if (!ctx) ctx = new (window.AudioContext || window.webkitAudioContext)();
    if (ctx.state === 'suspended') ctx.resume();
  },
  play(name) {
    if (muted || !ctx) return;
    SOUNDS[name]?.();
  },
  toggle() { muted = !muted; return muted; },
  get muted() { return muted; },
};
