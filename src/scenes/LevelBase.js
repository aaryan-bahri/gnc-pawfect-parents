// Plumbing shared by every level (Level1, Level2, Level3): cancellable task runs, meter helpers, the blocking dialogue, fact cards,
// choices, demos (the ? button), the pause menu and the "meter ran out" retry screen.
// A level calls setup() then setupUi() in create(), and implements startTask(task, retry) and demos() (demo specs by key).
//
// Each task attempt has a run id; a retry bumps it, so awaits from a cancelled attempt just stop (`if (!this.alive(run)) return`).
// Anything modal (dialogue, card, choice, demo) goes through modal(): it pauses the meter and holds back the idle hint.
import { GameScene } from '../view.js';
import { art, button, choice, demo, Dialog, factCard, Hud, nine, text, wait } from '../ui.js';
import { HappinessMeter } from '../meter.js';
import { fill } from '../content.js';
import { sfx } from '../sfx.js';
import { load, save } from '../save.js';

export class LevelBase extends GameScene {
  // data = { task, wrongs } when a level comes back from a cutscene between its two tasks
  init(data) { super.init(); this.entry = data ?? {}; }

  // Phaser reuses one scene object for every visit, so whatever a previous visit left behind (a destroyed dog, a pause menu, a
  // half-finished task) is still there when the scene starts again. setup() clears it first.
  setup(cfg, level) {
    Object.assign(this, { dog: null, thought: null, menu: null, onAct: null, onFrame: null, hintText: null, hintShown: false,
      lastProgress: 0, failing: false, cueSeen: false, run: 0, temp: [], seen: new Set(), modals: 0, demoKey: null, speaker: 'parent' });
    const { name, coat } = load();
    Object.assign(this, { cfg, level, coat, dogName: name, f: s => fill(s, name), wrongs: this.entry.wrongs ?? 0 });
    this.input.once('pointerdown', () => sfx.unlock());
    this.meter = new HappinessMeter({ drainPerSec: cfg.drainPerSec, onEmpty: () => this.fail() });
  }

  setupUi() {
    this.hud = new Hud(this, this.meter, { name: this.dogName, onPause: () => this.pause(), onHelp: () => this.help() });
    this.hud.setHelp(false);
    this.dialog = new Dialog(this);
  }

  update(_, dt) {
    this.meter.update(dt);
    this.hud.update(dt);
    this.thought?.update();
    if (!this.menu) this.onFrame?.(dt);                 // per-frame task logic (e.g. the puppy following the treat)
    const H = this.cfg.hintAfterMs;                     // Level 3 has none: hints only come after a wrong action
    if (H && this.hintText && !this.hintShown && !this.modals && !this.meter.paused && this.now() - this.lastProgress > H) {
      this.hintShown = true;
      this.say(this.hintText);
    }
  }

  alive(run) { return run === this.run; }
  own(o) { this.temp.push(o); return o; }
  wait(ms) { return wait(this, ms); }
  // The scene clock (this.time.now) is still 0 while create() runs, so idle-hint timing uses the game loop's own clock.
  now() { return this.game.loop.time; }
  progress() { this.lastProgress = this.now(); this.hintShown = false; }
  setHint(t) { this.hintText = t; this.progress(); }

  async modal(fn) {
    this.modals++;
    this.meter.pause();
    try { return await fn(); }
    finally { this.modals--; this.meter.resume(); this.progress(); }
  }

  // A line in the dialogue box. Nothing else can be tapped until OK. who: parent | vet | sam.
  say(line, who = this.speaker, opts) { return this.modal(() => this.dialog.say(who, this.f(line), opts)); }

  gain(n) {
    this.meter.add(n);
    if (n > 0) { sfx.play('chime'); this.hud.bump(); }
    else { sfx.play('boop'); this.wrongs++; }
  }

  // A fact card is shown once per level: the same fact again returns false (and shows nothing), so callers can say something short.
  async card(kind, body, title) {
    const line = this.f(body);
    if (this.seen.has(line)) return false;
    this.seen.add(line);
    await this.modal(() => factCard(this, kind, line, title));
    return true;
  }

  // The question stays in the dialogue box while the choice buttons sit above it. side: true keeps the bottom of the screen in view
  // (the question goes on a small card) for questions about what the dog is doing.
  ask(question, options, who = this.speaker, { side = false } = {}) {
    return this.modal(async () => {
      if (!side) this.dialog.say(who, this.f(question), { ok: null });
      const o = await choice(this, options.map(o => ({ ...o, label: this.f(o.label) })), { side: side ? this.f(question) : null });
      this.dialog.close();
      return o;
    });
  }

  // Demos: each plays by itself the first time (remembered in the save), and the HUD ? button replays the current one.
  setDemo(key) { this.demoKey = key; this.hud.setHelp(!!key); }
  showDemo(key, auto = true) {
    const spec = key && this.demos()[key];
    if (!spec) return Promise.resolve();
    const seen = load().demos;
    if (auto && seen.includes(key)) return Promise.resolve();
    if (!seen.includes(key)) save({ demos: [...seen, key] });
    return this.modal(() => demo(this, { ...spec, caption: this.f(spec.caption) }));
  }
  help() { if (!this.modals && !this.menu && !this.failing) this.showDemo(this.demoKey, false); }

  // Abandon the running task: bump the run id, stop timers and tweens, destroy everything registered with own().
  cancel() {
    this.run++;
    this.onFrame = null;
    this.onAct = null;
    this.time.removeAllEvents();
    this.tweens.killAll();
    this.temp.forEach(o => o.destroy());
    this.temp = [];
    this.thought?.hide();
    this.dialog?.close();
  }

  // Go to a cutscene, then come back to this level for its next task.
  handOff(key, task) {
    this.scene.start('Cutscene', { key, next: { scene: this.scene.key, data: { task, wrongs: this.wrongs } } });
  }

  // The level is done: fill the meter, then (an outro cutscene and) the album page.
  async complete(run) {
    this.meter.add(100);
    this.meter.pause();
    this.hintText = null;
    this.setDemo(null);
    sfx.play('win');
    await this.wait(1600); if (!this.alive(run)) return;
    const data = { level: this.level, wrongs: this.wrongs };
    if (this.cfg.outro) this.scene.start('Cutscene', { key: this.cfg.outro, next: { scene: 'LevelComplete', data } });
    else this.scene.start('LevelComplete', data);
  }

  // The meter ran out: grey the scene, the sad dog sits in a spotlight, the parent explains, "Try again" restarts the task.
  async fail() {
    this.cancel();
    this.hintText = null;
    this.failing = true;
    sfx.play('boop');
    this.own(this.add.rectangle(0, 0, 640, 360, 0x3E2A24, 0.55).setOrigin(0).setDepth(250).setInteractive());
    const d = this.dog?.sprite;
    if (d?.active) {
      this.own(art(this, d.x, d.y + 4, 'spotlight', 0.5, 1).setDepth(251));
      this.dogDepth = d.depth;
      d.setDepth(252).setFlipX(false);
      this.dog.play('sad');
    }
    await this.say(this.cfg.retry[this.task], 'parent', { ok: 'Try again' });
    this.failing = false;
    if (d?.active) d.setDepth(this.dogDepth);
    this.startTask(this.task, true);
  }

  pause() {
    if (this.menu || this.modals) return;
    this.meter.pause();
    this.tweens.pauseAll();
    this.time.paused = true;
    this.anims.pauseAll();
    const m = this.menu = this.add.container(0, 0).setDepth(400);
    m.add(this.add.rectangle(0, 0, 640, 360, 0x3E2A24, 0.5).setOrigin(0).setInteractive());
    m.add(nine(this, 220, 64, 'card_info', 200, 232, 6));
    m.add(text(this, 320, 80, 'Paused', 20, { bold: true }).setOrigin(0.5, 0));
    m.add(button(this, 250, 116, 140, 32, 'Resume', () => this.unpause()));
    const sound = button(this, 250, 158, 140, 32, sfx.muted ? 'Sound: off' : 'Sound: on', () => {
      sound.label.setText(sfx.toggle() ? 'Sound: off' : 'Sound: on');
    }, { kind: 'cream' });
    m.add(sound);
    m.add(button(this, 250, 200, 140, 32, 'Level select', () => { this.unpause(); this.scene.start('LevelSelect', {}); }, { kind: 'cream', size: 15 }));
    m.add(button(this, 250, 242, 140, 32, 'Quit to title', () => { this.unpause(); this.scene.start('Title', {}); }, { kind: 'cream', size: 15 }));
  }

  unpause() {
    this.menu.destroy();
    this.menu = null;
    this.meter.resume();
    this.tweens.resumeAll();
    this.time.paused = false;
    this.anims.resumeAll();
  }
}
