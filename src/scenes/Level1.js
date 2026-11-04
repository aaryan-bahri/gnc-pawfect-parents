// Level 1: First Day Home (GAME_DESIGN.md §7). Task 1 Snack Time, Task 2 Potty Training.
// Each task attempt has a run id; a retry bumps it, so awaits from a cancelled attempt just stop (`if (!this.alive(run)) return`).
import { GameScene } from '../view.js';
import { HappinessMeter } from '../meter.js';
import { LEVEL1, fill } from '../content.js';
import { Dog } from '../dog.js';
import { art, button, choice, cue, factCard, nine, text, touchable, wait, Hud, ParentDialog, Thought, W, WORLD, CURSOR } from '../ui.js';
import { sfx } from '../sfx.js';
import { load } from '../save.js';

const FLOOR = W(WORLD.groundY + 1);       // canvas y where floor props rest
// The treat sits on the kitchen countertop (world y=101). The treat icon's bone ends 11px down its 16px frame.
const TREAT = { x: W(296), y: W(101), originY: 11 / 16 };

export class Level1 extends GameScene {
  constructor() { super('Level1'); }

  create() {
    const { name, coat } = load();
    this.f = s => fill(s, name);
    this.input.once('pointerdown', () => sfx.unlock());
    art(this, 0, 0, 'living_room');
    this.bowl = art(this, W(WORLD.spots.bowl), FLOOR, 'bowl_empty', 0.5, 1).setDepth(40);
    this.dog = new Dog(this, coat, 300);
    this.meter = new HappinessMeter({ drainPerSec: LEVEL1.drainPerSec, onEmpty: () => this.fail() });
    this.hud = new Hud(this, this.meter, { name, onPause: () => this.pause() });
    this.talk = new ParentDialog(this);
    this.thought = new Thought(this, this.dog.sprite);
    this.wrongs = 0;
    this.run = 0;
    this.temp = [];
    this.startTask('snack');
  }

  update(_, dt) {
    this.meter.update(dt);
    this.hud.update(dt);
    this.thought.update();
    if (!this.menu) this.onFrame?.(dt);                 // per-frame task logic (puppy following the treat)
    // compare scene-clock times (this.time.now), not the game-loop timestamp
    if (this.hintText && !this.hintShown && !this.meter.paused && this.time.now - this.lastProgress > LEVEL1.hintAfterMs) {
      this.hintShown = true;
      this.talk.say(this.f(this.hintText));
    }
  }

  // ---------------------------------------------------------------- plumbing
  alive(run) { return run === this.run; }
  own(o) { this.temp.push(o); return o; }
  wait(ms) { return wait(this, ms); }
  clickOn(obj) { return new Promise(r => obj.once('pointerup', r)); }
  progress() { this.lastProgress = this.time.now; this.hintShown = false; }
  setHint(t) { this.hintText = t; this.progress(); }

  gain(n) {
    this.meter.add(n);
    if (n > 0) { sfx.play('chime'); this.hud.bump(); }
    else { sfx.play('boop'); this.wrongs++; }
  }

  async card(kind, body, title) {
    this.meter.pause();
    await factCard(this, kind, this.f(body), title);
    this.meter.resume();
    this.progress();                                    // reading time doesn't count towards the idle hint
  }

  async ask(question, options) {
    this.talk.say(this.f(question));
    this.meter.pause();
    const o = await choice(this, options);
    this.meter.resume();
    this.progress();
    return o;
  }

  cancel() {
    this.run++;
    this.onFrame = null;
    this.time.removeAllEvents();
    this.tweens.killAll();
    this.temp.forEach(o => o.destroy());
    this.temp = [];
    this.dog.sprite.removeAllListeners('pointerup').disableInteractive();
    this.thought.hide();
  }

  startTask(task, retry = false) {
    this.cancel();
    this.task = task;
    const run = this.run;
    this.meter.reset();
    this.bowl.setTexture('bowl_empty');
    this.dog.play('idle');
    if (task === 'snack') { this.hud.setTask('bowl', 'Snack time  1 of 2'); this.snack(run, retry); }
    else { this.hud.setTask('pad', 'Potty time  2 of 2'); this.potty(run, retry); }
  }

  // ---------------------------------------------------------------- Task 1: Snack Time
  async snack(run, retry) {
    const S = LEVEL1.snack;
    this.setHint(S.hint);
    this.talk.say(this.f(retry ? S.hint : S.intro));
    await this.dog.walkTo(W(205)); if (!this.alive(run)) return;
    let swap = Math.random() < 0.5;

    for (let r = 0; r < S.rounds.length;) {
      this.dog.face(1).play('sit');
      this.thought.show('bowl');
      const c = WORLD.counter;
      const counter = this.own(this.add.zone(W(c.x), W(c.y), W(c.w), W(c.h)).setOrigin(0).setInteractive({ cursor: CURSOR }));
      const arrow = this.own(cue(this, W(270), W(98)));
      await this.clickOn(counter); if (!this.alive(run)) return;
      counter.destroy(); arrow.destroy();
      this.thought.hide();                              // the close-up should be uncluttered:
      this.talk.hide();                                 // no thought bubble, no parent bubble over the counter
      sfx.play('page');

      const pick = await this.closeUp(S.rounds[r], swap); if (!this.alive(run)) return;
      this.talk.show();
      this.progress();
      this.thought.hide();
      this.bowl.setTexture(`bowl_${pick.id}`);
      await this.dog.walkTo(W(WORLD.spots.bowl) - 30); if (!this.alive(run)) return;
      this.dog.face(1).play('sniff');
      await this.wait(900); if (!this.alive(run)) return;

      if (pick.safe) {
        this.dog.play('eat');
        await this.wait(1400); if (!this.alive(run)) return;
        this.bowl.setTexture('bowl_empty');
        this.dog.play('wag'); sfx.play('wag');
        this.gain(20);
        await this.card('good', pick.fact); if (!this.alive(run)) return;
        r++;
      } else {
        this.dog.play('refuse');
        this.thought.show('tummy');
        this.gain(-5);
        await this.wait(1000); if (!this.alive(run)) return;
        await this.card('bad', pick.fact); if (!this.alive(run)) return;
        this.talk.say(this.f(S.wrongParent));
        await this.toCupboard(); if (!this.alive(run)) return;
        swap = !swap;                                   // same pair again, positions swapped
      }
      await this.dog.walkTo(W(205)); if (!this.alive(run)) return;
    }

    this.thought.hide();
    this.talk.say(this.f(S.done));
    this.dog.play('wag');
    await this.wait(2200); if (!this.alive(run)) return;
    this.startTask('potty');
  }

  // Counter close-up with two big foods. Resolves with the picked food ({ id, label, fact, safe }).
  closeUp(round, swap) {
    return new Promise(resolve => {
      const box = this.own(this.add.container(0, 0).setDepth(90));
      box.add(art(this, 0, 0, 'counter_closeup'));
      const foods = [{ ...round.safe, safe: true }, { ...round.unsafe, safe: false }];
      if (swap) foods.reverse();
      foods.forEach((f, i) => {
        const x = W(WORLD.counterSlots[i]), y = W(WORLD.counterTopY);
        const img = art(this, x, y, `foodbig_${f.id}`, 0.5, 1).setInteractive({ cursor: CURSOR });
        img.on('pointerover', () => { img.y = y - 4; }).on('pointerout', () => { img.y = y; });
        img.on('pointerup', () => { sfx.play('click'); box.destroy(); resolve(f); });
        box.add([img, nine(this, x - 64, 290, 'card_info', 128, 26, 6), text(this, x, 294, f.label, 14).setOrigin(0.5, 0)]);
      });
    });
  }

  // The parent puts the unsafe food up in the high cupboard.
  toCupboard() {
    this.bowl.setTexture('bowl_empty');
    const s = this.own(art(this, this.bowl.x, this.bowl.y - 24, 'icon_star', 0.5, 0.5).setDepth(60));
    return new Promise(r => this.tweens.add({ targets: s, x: W(270), y: W(40), duration: 800, ease: 'Sine.easeInOut',
      onComplete: () => { s.destroy(); r(); } }));
  }

  // ---------------------------------------------------------------- Task 2: Potty Training
  async potty(run, retry) {
    const P = LEVEL1.potty;
    this.setHint(P.hintPad);
    this.talk.say(this.f(retry ? P.hintPad : P.introPad));
    this.dog.walkTo(W(150));

    // Part A: drag the pad to a spot
    const home = { x: W(115), y: FLOOR };
    const pad = this.own(touchable(art(this, home.x, home.y, 'pad', 0.5, 1).setDepth(45), { pad: 8, draggable: true }));
    pad.on('drag', (p, x, y) => pad.setPosition(Math.round(x / 2) * 2, Math.round(y / 2) * 2));
    const arrows = P.spots.map(s => this.own(cue(this, W(WORLD.spots[s.id]), FLOOR - 24)));
    const goHome = () => this.tweens.add({ targets: pad, x: home.x, y: home.y, duration: 220 });
    for (;;) {
      await new Promise(r => pad.once('dragend', r)); if (!this.alive(run)) return;
      const spot = P.spots.map(s => ({ ...s, dist: Math.abs(W(WORLD.spots[s.id]) - pad.x) })).sort((a, b) => a.dist - b.dist)[0];
      if (spot.dist > W(30) || pad.y < W(WORLD.floorY)) { goHome(); continue; }
      this.progress();
      pad.setPosition(W(WORLD.spots[spot.id]), FLOOR);
      if (spot.correct) {
        this.gain(20);
        await this.card('good', spot.fact); if (!this.alive(run)) return;
        break;
      }
      this.gain(-5);
      await this.card('bad', spot.fact); if (!this.alive(run)) return;
      goHome();
    }
    arrows.forEach(a => a.destroy());
    this.input.setDraggable(pad, false);

    // Part B: read the potty signs and lead the puppy to the pad
    this.setHint(P.hintLead);
    this.talk.say(this.f(P.introLead));
    let wins = 0;
    while (wins < P.successesNeeded) {
      const until = this.time.now + Phaser.Math.Between(3500, 6000);
      while (this.time.now < until) {
        await this.dog.walkTo(Phaser.Math.Between(W(70), W(300)), 70); if (!this.alive(run)) return;
        await this.wait(Phaser.Math.Between(400, 1000)); if (!this.alive(run)) return;
      }
      this.setHint(P.hintLead);
      const result = await this.pottyRound(pad, P.cueWindowMs); if (!this.alive(run)) return;

      if (result === 'rewarded') {
        this.gain(20);
        await this.card('good', P.reward.fact, P.reward.title); if (!this.alive(run)) return;
        wins++;
      } else {
        this.dog.face(1).play('pee');
        const puddle = this.own(art(this, this.dog.x - 14, FLOOR, 'puddle', 0.5, 1).setDepth(44));
        await this.wait(1400); if (!this.alive(run)) return;
        this.thought.hide();
        const o = await this.ask(P.tooLate.question, P.tooLate.choices); if (!this.alive(run)) return;
        this.gain(o.delta);
        if (o.id === 'scold') this.dog.play('cower');
        await this.card(o.delta > 0 ? 'good' : 'bad', o.fact); if (!this.alive(run)) return;
        this.tweens.add({ targets: puddle, alpha: 0, duration: 400 });
      }
      this.dog.play('idle');
      if (wins < P.successesNeeded) this.talk.say(this.f(P.introLead));
    }

    this.talk.say(this.f(P.done));
    this.dog.play('wag');
    await this.card('info', P.tip); if (!this.alive(run)) return;
    this.complete(run);
  }

  // The puppy shows the potty signs. The player drags a treat off the counter and the puppy follows it to the pad,
  // goes potty, then the player drops the treat on the puppy as a reward.
  // Resolves 'rewarded', or 'late' if the time window runs out before the puppy reaches the pad.
  pottyRound(pad, windowMs) {
    const run = this.run, P = LEVEL1.potty, dog = this.dog;
    return new Promise(resolve => {
      let state = 'wait', dragging = false;             // wait -> lead -> pee -> reward -> done
      dog.play('sniff');
      this.thought.show('droplet');
      this.time.delayedCall(900, () => { if (state === 'wait') dog.play('circle'); });
      const arrow = this.own(cue(this, TREAT.x, TREAT.y - 50));
      const treat = this.own(touchable(art(this, TREAT.x, TREAT.y, 'icon_treat', 0.5, TREAT.originY).setDepth(130),
        { pad: 6, draggable: true }));
      const toHome = () => this.tweens.add({ targets: treat, x: TREAT.x, y: TREAT.y, duration: 200 });
      const timer = this.time.delayedCall(windowMs, () => { if (state === 'wait' || state === 'lead') finish('late'); });
      const finish = r => { timer.remove(); this.onFrame = null; arrow.destroy(); treat.destroy(); resolve(r); };

      treat.on('dragstart', () => {
        this.tweens.killTweensOf(treat);
        dragging = true;
        sfx.play('click');
        this.progress();
        if (state === 'wait') { state = 'lead'; arrow.setPosition(pad.x, pad.y - 26); }
      });
      treat.on('drag', (p, x, y) => treat.setPosition(Math.round(x / 2) * 2, Math.round(y / 2) * 2));
      treat.on('dragend', () => {
        dragging = false;
        if (state === 'reward' && this.overDog(treat)) {
          state = 'done';
          this.giveTreat(treat).then(() => { if (this.alive(run)) finish('rewarded'); });
          return;
        }
        toHome();                                       // let go early and the treat goes back
        if (state === 'lead') { state = 'wait'; dog.play('circle'); arrow.setPosition(TREAT.x, TREAT.y - 50); }
      });

      // While the treat is held the puppy follows it. Reaching the pad makes the puppy go potty.
      this.onFrame = dt => {
        if (state !== 'lead' || !dragging) return;
        dog.chase(Phaser.Math.Clamp(treat.x, 30, 610), dt, 100);
        if (Math.abs(dog.x - pad.x) > 28) return;       // over the pad (it is 96px wide)
        state = 'pee';
        this.tweens.add({ targets: dog.sprite, x: pad.x, duration: 200 });   // settle onto the middle of the pad
        dog.play('pee');
        this.thought.hide();
        arrow.setVisible(false);
        this.wait(1600).then(() => {
          if (!this.alive(run)) return;
          state = 'reward';
          dog.play('wag'); sfx.play('wag');
          this.thought.show('treat');
          arrow.setPosition(dog.x, dog.sprite.y - 150).setVisible(true);
          this.talk.say(this.f(P.reward.prompt));
          this.setHint(P.reward.prompt);                // an idle hint now repeats the reward prompt
        });
      };
    });
  }

  overDog(o) {
    const d = this.dog.sprite;
    return Math.abs(o.x - d.x) < 48 && o.y > d.y - 100 && o.y < d.y + 10;
  }

  // The treat goes into the puppy's mouth, the puppy munches and wags, and a heart floats up.
  async giveTreat(treat) {
    const run = this.run, d = this.dog;
    this.input.setDraggable(treat, false);
    await new Promise(r => this.tweens.add({ targets: treat, x: d.x + (d.sprite.flipX ? -14 : 14), y: d.sprite.y - 36,
      duration: 220, onComplete: r }));
    if (!this.alive(run)) return;
    treat.destroy();
    this.thought.hide();
    d.play('eat'); sfx.play('chime');
    await this.wait(1000); if (!this.alive(run)) return;
    d.play('wag'); sfx.play('wag');
    const h = this.own(art(this, d.x, d.sprite.y - 70, 'icon_heart', 0.5, 0.5).setDepth(140));
    this.tweens.add({ targets: h, y: h.y - 36, alpha: 0, duration: 900, onComplete: () => h.destroy() });
    await this.wait(700);
  }

  // ---------------------------------------------------------------- end, fail, pause
  async complete(run) {
    this.meter.add(100);
    this.meter.pause();
    this.hintText = null;
    sfx.play('win');
    await this.wait(1600); if (!this.alive(run)) return;
    this.scene.start('LevelComplete', { wrongs: this.wrongs });
  }

  fail() {
    this.cancel();
    this.hintText = null;
    sfx.play('boop');
    this.own(this.add.rectangle(0, 0, 640, 360, 0x3E2A24, 0.55).setOrigin(0).setDepth(250).setInteractive());
    this.own(art(this, this.dog.x, FLOOR + 6, 'spotlight', 0.5, 1).setDepth(251));
    this.dog.sprite.setDepth(252).setFlipX(false);
    this.dog.play('sad');
    this.talk.setDepth(260);
    this.talk.say(this.f(LEVEL1.retry[this.task]));
    this.own(button(this, 256, 160, 128, 32, 'Try again', () => {
      this.dog.sprite.setDepth(50);
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
