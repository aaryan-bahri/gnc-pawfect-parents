// Level 1: First Day Home (GAME_DESIGN.md §7). Task 1 Snack Time, then the "Later that afternoon" cutscene, then Task 2 Potty
// Training, which starts with an accident on the rug. Task structure and cancel/retry rules: see LevelBase.js.
import { LevelBase } from './LevelBase.js';
import { LEVEL1 } from '../content.js';
import { Dog } from '../dog.js';
import { art, cue, glow, heart, nine, text, touchable, Thought, W, WORLD, CURSOR } from '../ui.js';
import { sfx } from '../sfx.js';

const FLOOR = W(WORLD.groundY + 1);       // canvas y where floor props rest
// The treat sits on the kitchen countertop (world y=101). The treat icon's bone ends 11px down its 16px frame.
const TREAT = { x: W(296), y: W(101), originY: 11 / 16 };
const PAD_HOME = { x: W(115), y: FLOOR };

export class Level1 extends LevelBase {
  constructor() { super('Level1'); }

  create() {
    this.setup(LEVEL1, 1);
    art(this, 0, 0, 'living_room');
    this.bowl = art(this, W(WORLD.spots.bowl), FLOOR, 'bowl_empty', 0.5, 1).setDepth(40);
    this.dog = new Dog(this, this.coat, 300);
    this.thought = new Thought(this, this.dog.sprite);
    this.setupUi();
    this.startTask(this.entry.task ?? 'snack');
  }

  demos() {
    return {
      snack: { caption: 'Tap the kitchen counter to look at the food.', steps: [{ tap: [W(268), W(76)] }] },
      food: { caption: 'Tap the food you think is safe for {name}.', steps: [{ tap: [W(WORLD.counterSlots[0]), W(110)] }] },
      pad: { caption: 'Drag the pad onto the floor. Try to find a good spot!', steps: [{ drag: [[PAD_HOME.x, FLOOR - 10], [W(70), FLOOR - 10]], carry: 'pad', arc: 30 }] },
      lead: { caption: 'Hold the treat and drag it slowly. {name} follows it to the pad.',
              steps: [{ drag: [[TREAT.x, TREAT.y - 6], [W(WORLD.spots.door), FLOOR - 40]], carry: 'icon_treat', arc: 24 }] },
      reward: { caption: 'Drag the treat onto {name} and let go: a reward, right away!',
                steps: [{ drag: [[TREAT.x, TREAT.y - 6], [this.dog.x, this.dog.sprite.y - 30]], carry: 'icon_treat', arc: 24 }] },
    };
  }

  startTask(task, retry = false) {
    this.cancel();
    this.task = task;
    const run = this.run;
    this.meter.reset();
    this.bowl.setTexture('bowl_empty');
    this.dog.play('idle');
    this.setDemo(null);
    if (task === 'snack') { this.hud.setTask('bowl', 'Snack time  1 of 2'); this.snack(run, retry); }
    else { this.hud.setTask('pad', 'Potty time  2 of 2'); this.potty(run, retry); }
  }

  // ---------------------------------------------------------------- Task 1: Snack Time
  async snack(run, retry) {
    const S = LEVEL1.snack;
    this.dog.sprite.x = 300;
    await this.dog.walkTo(W(205)); if (!this.alive(run)) return;
    let swap = Math.random() < 0.5, missed = false;

    for (let r = 0; r < S.rounds.length;) {
      this.dog.face(1).play('sit');
      this.thought.show('bowl');
      await this.say(retry && r === 0 && !missed ? S.hint : missed ? S.again : r === 0 ? S.intro : S.next[r - 1]);
      if (!this.alive(run)) return;
      this.setDemo('snack');
      await this.showDemo('snack'); if (!this.alive(run)) return;
      this.setHint(S.hint);
      const c = WORLD.counter;
      const counter = this.own(this.add.zone(W(c.x), W(c.y), W(c.w), W(c.h)).setOrigin(0).setDepth(30).setInteractive({ cursor: CURSOR }));
      glow(this, counter);
      const arrow = this.own(cue(this, W(270), W(98)));
      await new Promise(res => counter.once('pointerup', res)); if (!this.alive(run)) return;
      counter.destroy(); arrow.destroy();
      this.thought.hide();                              // the close-up should be uncluttered
      sfx.play('page');

      const pick = await this.closeUp(S.rounds[r], swap, run); if (!this.alive(run)) return;
      this.progress();
      this.bowl.setTexture(`bowl_${pick.id}`);
      await this.dog.walkTo(W(WORLD.spots.bowl) - 30); if (!this.alive(run)) return;
      this.dog.face(1).play('sniff');
      await this.wait(900); if (!this.alive(run)) return;

      if (pick.safe) {
        this.dog.play('eat');
        await this.wait(1400); if (!this.alive(run)) return;
        this.bowl.setTexture('bowl_empty');
        this.dog.play('wag'); sfx.play('wag');
        heart(this, this.dog.x, this.dog.sprite.y - 70);
        this.gain(20);
        await this.card('good', pick.fact); if (!this.alive(run)) return;
        r++; missed = false;
      } else {
        this.dog.play('refuse');
        this.thought.show('tummy');
        this.gain(-5);
        await this.wait(1000); if (!this.alive(run)) return;
        await this.card('bad', pick.fact); if (!this.alive(run)) return;
        this.thought.hide();
        await this.say(S.wrongParent); if (!this.alive(run)) return;
        await this.toCupboard(); if (!this.alive(run)) return;
        swap = !swap; missed = true;                                   // same pair again, positions swapped
      }
      await this.dog.walkTo(W(205)); if (!this.alive(run)) return;
    }

    this.hintText = null;
    this.thought.hide();
    this.dog.play('wag');
    await this.say(S.done); if (!this.alive(run)) return;
    this.handOff('afternoon', 'potty');                 // "Later that afternoon", then back here for the potty task
  }

  // Counter close-up with two big foods. Resolves with the picked food ({ id, label, fact, safe }).
  async closeUp(round, swap, run) {
    const box = this.own(this.add.container(0, 0).setDepth(90));
    box.add(art(this, 0, 0, 'counter_closeup'));
    const foods = [{ ...round.safe, safe: true }, { ...round.unsafe, safe: false }];
    if (swap) foods.reverse();
    const imgs = foods.map((f, i) => {
      const x = W(WORLD.counterSlots[i]), y = W(WORLD.counterTopY);
      const img = art(this, x, y, `foodbig_${f.id}`, 0.5, 1).setInteractive({ cursor: CURSOR });
      box.add([img, nine(this, x - 64, 290, 'card_info', 128, 26, 6), text(this, x, 294, f.label, 14).setOrigin(0.5, 0)]);
      glow(this, img);
      return img;
    });
    this.setDemo('food');
    await this.showDemo('food'); if (!this.alive(run)) return null;
    return new Promise(resolve => imgs.forEach((img, i) => img.on('pointerup', () => { sfx.play('click'); box.destroy(); resolve(foods[i]); })));
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
    this.dog.sprite.x = W(WORLD.spots.middle) + 30;
    if (!retry) {
      // It starts with an accident: the puppy sniffs, circles and pees on the rug before the player can do anything.
      this.dog.face(-1).play('sniff');
      this.thought.show('question');
      await this.wait(1400); if (!this.alive(run)) return;
      this.dog.play('circle');
      await this.wait(1300); if (!this.alive(run)) return;
      if (!await this.accident(run)) return;
      await this.say(P.accident.after); if (!this.alive(run)) return;
    }

    // Part A: drag the pad to a spot
    await this.say(retry ? P.hintPad : P.introPad); if (!this.alive(run)) return;
    this.setDemo('pad');
    await this.showDemo('pad'); if (!this.alive(run)) return;
    this.setHint(P.hintPad);
    this.dog.walkTo(W(150));
    const pad = this.own(touchable(art(this, PAD_HOME.x, PAD_HOME.y, 'pad', 0.5, 1).setDepth(45), { pad: 8, draggable: true }));
    glow(this, pad);
    pad.on('drag', (p, x, y) => pad.setPosition(Math.round(x / 2) * 2, Math.round(y / 2) * 2));
    const arrows = P.spots.map(s => this.own(cue(this, W(WORLD.spots[s.id]), FLOOR - 24)));
    const goHome = () => this.tweens.add({ targets: pad, x: PAD_HOME.x, y: PAD_HOME.y, duration: 220 });
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
    pad.disableInteractive();

    // Part B: read the potty signs and lead the puppy to the pad
    await this.say(P.introLead); if (!this.alive(run)) return;
    let wins = 0;
    while (wins < P.successesNeeded) {
      this.setDemo(null);
      this.hintText = null;
      const until = this.time.now + Phaser.Math.Between(3500, 6000);
      while (this.time.now < until) {
        await this.dog.walkTo(Phaser.Math.Between(W(70), W(300)), 70); if (!this.alive(run)) return;
        await this.wait(Phaser.Math.Between(400, 1000)); if (!this.alive(run)) return;
      }
      const result = await this.pottyRound(pad, P.cueWindowMs, run); if (!this.alive(run)) return;

      if (result === 'rewarded') {
        this.gain(20);
        if (!await this.card('good', P.reward.fact, P.reward.title)) await this.say(P.reward.again);   // the lesson once, then a short line
        if (!this.alive(run)) return;
        wins++;
      } else {
        if (!await this.accident(run)) return;
      }
      this.dog.play('idle');
    }

    this.hintText = null;
    this.dog.play('wag');
    await this.say(P.done); if (!this.alive(run)) return;
    await this.card('info', P.tip); if (!this.alive(run)) return;
    this.complete(run);
  }

  // The puppy pees where it stands, then the player chooses: scold, or clean up calmly. Resolves false if the run was cancelled.
  async accident(run) {
    const A = LEVEL1.potty.accident;
    this.dog.face(1).play('pee');
    this.thought.hide();
    const puddle = this.own(art(this, this.dog.x - 14, FLOOR, 'puddle', 0.5, 1).setDepth(44));
    await this.wait(1500); if (!this.alive(run)) return false;
    this.dog.play('idle');
    const o = await this.ask(A.question, A.choices); if (!this.alive(run)) return false;
    this.gain(o.delta);
    if (o.id === 'scold') this.dog.play('cower');
    await this.card(o.delta > 0 ? 'good' : 'bad', o.fact); if (!this.alive(run)) return false;
    this.tweens.add({ targets: puddle, alpha: 0, duration: 400 });
    this.dog.play('idle');
    return true;
  }

  // The puppy shows the potty signs. The player drags a treat off the counter and the puppy follows it to the pad,
  // goes potty, then the player drops the treat on the puppy as a reward.
  // Resolves 'rewarded', or 'late' if the time window runs out before the puppy reaches the pad.
  async pottyRound(pad, windowMs, run) {
    const P = LEVEL1.potty, dog = this.dog;
    dog.play('sniff');
    this.thought.show('droplet');
    this.time.delayedCall(900, () => dog.play('circle'));
    await this.say(this.cueSeen ? P.cueAgain : P.cue);   // explain the signs when they happen; the clock starts after OK
    if (!this.alive(run)) return null;
    this.cueSeen = true;
    this.setDemo('lead');
    await this.showDemo('lead'); if (!this.alive(run)) return null;
    this.setHint(P.hintLead);

    return new Promise(resolve => {
      let state = 'wait', dragging = false;             // wait -> lead -> pee -> reward -> done
      dog.play('circle');
      const arrow = this.own(cue(this, TREAT.x, TREAT.y - 50));
      const treat = this.own(touchable(art(this, TREAT.x, TREAT.y, 'icon_treat', 0.5, TREAT.originY).setDepth(130),
        { pad: 6, draggable: true }));
      glow(this, treat);
      const target = glow(this, dog.sprite, { hover: false });       // the puppy lights up while a reward is dragged over it
      const toHome = () => this.tweens.add({ targets: treat, x: TREAT.x, y: TREAT.y, duration: 200 });
      const timer = this.time.delayedCall(windowMs, () => { if (state === 'wait' || state === 'lead') finish('late'); });
      const finish = r => { timer.remove(); this.onFrame = null; target.hide(); arrow.destroy(); treat.destroy(); resolve(r); };

      treat.on('dragstart', () => {
        this.tweens.killTweensOf(treat);
        dragging = true;
        sfx.play('click');
        this.progress();
        if (state === 'wait') { state = 'lead'; arrow.setPosition(pad.x, pad.y - 26); }
      });
      treat.on('drag', (p, x, y) => {
        treat.setPosition(Math.round(x / 2) * 2, Math.round(y / 2) * 2);
        if (state === 'reward') (this.overDog(treat) ? target.show : target.hide)();
      });
      treat.on('dragend', () => {
        dragging = false;
        target.hide();
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
        this.wait(1600).then(async () => {
          if (!this.alive(run)) return;
          dog.play('wag'); sfx.play('wag');
          this.thought.show('treat');
          await this.say(P.reward.prompt); if (!this.alive(run)) return;
          this.setDemo('reward');
          await this.showDemo('reward'); if (!this.alive(run)) return;
          state = 'reward';
          arrow.setPosition(dog.x, dog.sprite.y - 150).setVisible(true);
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
    heart(this, d.x, d.sprite.y - 70);
    await this.wait(700);
  }
}
