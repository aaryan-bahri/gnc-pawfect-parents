// Plumbing shared by every level (Level1, Level2, ...): cancellable task runs, meter helpers, fact cards, the pause menu and the
// "meter ran out" retry screen. A level sets in create(): this.cfg (its content object), this.f (fill), this.meter, this.hud, this.talk,
// this.dog, this.run = 0, this.temp = [], this.wrongs = 0, and implements startTask(task, retry).
//
// Each task attempt has a run id; a retry bumps it, so awaits from a cancelled attempt just stop (`if (!this.alive(run)) return`).
import { GameScene } from '../view.js';
import { art, button, choice, factCard, nine, text, wait } from '../ui.js';
import { sfx } from '../sfx.js';

export class LevelBase extends GameScene {
  // Phaser reuses one scene object for every visit, so whatever a previous visit left behind (a destroyed dog, a pause menu, a
  // half-finished task) is still there when the scene starts again. Every level's create() calls this first.
  resetRun() {
    Object.assign(this, { dog: null, thought: null, list: null, layer: null, menu: null, onAct: null, onFrame: null, hintText: null,
      hintShown: false, lastProgress: 0, moving: false, failing: false, tilling: false, cueSeen: false, run: 0, temp: [], seen: new Set() });
  }

  update(_, dt) {
    this.meter.update(dt);
    this.hud.update(dt);
    this.thought?.update();
    if (!this.menu) this.onFrame?.(dt);                 // per-frame task logic (e.g. the puppy following the treat)
    if (this.hintText && !this.hintShown && !this.meter.paused && this.now() - this.lastProgress > this.cfg.hintAfterMs) {
      this.hintShown = true;
      this.say(this.hintText);
    }
  }

  alive(run) { return run === this.run; }
  own(o) { this.temp.push(o); return o; }
  wait(ms) { return wait(this, ms); }
  clickOn(obj) { return new Promise(r => obj.once('pointerup', r)); }
  // The scene clock (this.time.now) is still 0 while create() runs, so idle-hint timing uses the game loop's own clock.
  now() { return this.game.loop.time; }
  progress() { this.lastProgress = this.now(); this.hintShown = false; }
  setHint(t) { this.hintText = t; this.progress(); }
  say(line) { this.talk.say(this.f(line)); }

  gain(n) {
    this.meter.add(n);
    if (n > 0) { sfx.play('chime'); this.hud.bump(); }
    else { sfx.play('boop'); this.wrongs++; }
  }

  // A fact card is shown once per level: the same fact again returns false (and shows nothing), so callers can say something short.
  async card(kind, body, title) {
    const line = this.f(body);
    this.seen ??= new Set();
    if (this.seen.has(line)) return false;
    this.seen.add(line);
    this.meter.pause();
    await factCard(this, kind, line, title);
    this.meter.resume();
    this.progress();                                    // reading time doesn't count towards the idle hint
    return true;
  }

  async ask(question, options) {
    this.say(question);
    this.meter.pause();
    const o = await choice(this, options);
    this.meter.resume();
    this.progress();
    return o;
  }

  // Abandon the running task: bump the run id, stop timers and tweens, destroy everything registered with own().
  cancel() {
    this.run++;
    this.onFrame = null;
    this.time.removeAllEvents();
    this.tweens.killAll();
    this.temp.forEach(o => o.destroy());
    this.temp = [];
    this.dog?.sprite.removeAllListeners('pointerup').disableInteractive();
    this.onAct = null;
  }

  // A task set is done: fill the meter, then the album page. this.level is 1, 2, ...
  async complete(run) {
    this.meter.add(100);
    this.meter.pause();
    this.hintText = null;
    sfx.play('win');
    await this.wait(1600); if (!this.alive(run)) return;
    this.scene.start('LevelComplete', { level: this.level, wrongs: this.wrongs });
  }

  // The meter ran out: grey the scene, the sad dog sits in a spotlight, the parent explains, "Try again" restarts the task.
  fail() {
    this.cancel();
    this.hintText = null;
    sfx.play('boop');
    this.own(this.add.rectangle(0, 0, 640, 360, 0x3E2A24, 0.55).setOrigin(0).setDepth(250).setInteractive());
    if (this.dog) {
      this.own(art(this, this.dog.x, this.dog.sprite.y + 4, 'spotlight', 0.5, 1).setDepth(251));
      this.dog.sprite.setDepth(252).setFlipX(false);
      this.dog.play('sad');
    }
    this.failing = true;                                // (Level2.say keeps this bubble up: it is the point of the screen)
    this.speaker = 'parent';
    this.talk.setWho('parent');
    this.talk.setDepth(260);
    this.say(this.cfg.retry[this.task]);
    this.own(button(this, 256, 160, 128, 32, 'Try again', () => {
      this.failing = false;
      this.dog?.sprite.setDepth(50);
      this.talk.setDepth(150);
      this.startTask(this.task, true);
    }, { size: 18 }).setDepth(261));
  }

  pause() {
    if (this.menu) return;
    this.meter.pause();
    this.tweens.pauseAll();
    this.time.paused = true;
    this.anims.pauseAll();
    const m = this.menu = this.add.container(0, 0).setDepth(400);
    m.add(this.add.rectangle(0, 0, 640, 360, 0x3E2A24, 0.5).setOrigin(0).setInteractive());
    m.add(nine(this, 220, 84, 'card_info', 200, 192, 6));
    m.add(text(this, 320, 100, 'Paused', 20, { bold: true }).setOrigin(0.5, 0));
    m.add(button(this, 250, 136, 140, 32, 'Resume', () => this.unpause()));
    const sound = button(this, 250, 178, 140, 32, sfx.muted ? 'Sound: off' : 'Sound: on', () => {
      sound.list.find(o => o.type === 'Text').setText(sfx.toggle() ? 'Sound: off' : 'Sound: on');
    }, { kind: 'cream' });
    m.add(sound);
    m.add(button(this, 250, 220, 140, 32, 'Quit to title', () => { this.unpause(); this.scene.start('Title'); }, { kind: 'cream', size: 15 }));
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
