// Level 3: Park Day (GAME_DESIGN.md §7). The walk to the park (hold to walk, let go when the dog pulls), the park gate cutscene,
// Task 1 Fetch (throw, notice the panting, rest in the shade, give water), "A little later", Task 2 meeting Sam (read the dog,
// greet safely). No pointer cues and no timed hints: help comes after a wrong action. Art: asset group 11. Cancel/retry: LevelBase.js.
import { LevelBase } from './LevelBase.js';
import { LEVEL3 } from '../content.js';
import { Dog } from '../dog.js';
import { art, glow, heart, Thought, touchable, W, CURSOR } from '../ui.js';
import { sfx } from '../sfx.js';

export class Level3 extends LevelBase {
  constructor() { super('Level3'); }

  create() {
    this.setup(LEVEL3, 3);
    const task = this.entry.task ?? 'walk';
    this.setupScene(task);
    this.setupUi();
    this.startTask(task);
  }

  setupScene(task) {
    if (task === 'walk') {
      const L = LEVEL3.walk.layout;
      this.street = this.add.container(0, 0);
      this.street.add(art(this, 0, 0, 'street'));
      this.sights = L.distractions.map(([id, x, y]) => {
        const s = id === 'sandwich' ? art(this, W(x), W(y), 'sandwich', 0.5, 1) : this.add.sprite(W(x), W(y), id, 0).setOrigin(0.5, 1).setScale(2).play(id);
        this.street.add(s);
        return { id, x, s, seen: false };
      });
      this.kid = this.add.sprite(W(L.kidX), W(L.ground), 'kid_walk', 0).setOrigin(0, 1).setScale(2).setDepth(40);
      this.leash = art(this, W(L.kidX + L.hand[0]), W(L.ground + L.hand[1]), 'leash_slack').setDepth(41);
      this.dog = new Dog(this, this.coat, this.dogX(false), { stage: 'adult', y: W(L.ground) });
      this.dog.sprite.setDepth(42);
    } else {
      const P = LEVEL3.fetch.layout;
      art(this, 0, 0, 'park');
      this.shade = art(this, W(P.shade[0]), W(P.shade[1]), 'park_shade').setDepth(2);
      this.tree = art(this, W(-4), W(P.ground - 122), 'park_tree').setDepth(3);
      art(this, W(274), W(P.ground + 2 - 52), 'fountain').setDepth(3);
      this.kid = art(this, W(P.kidX), W(P.ground), 'kid_park', 0, 1).setDepth(40);
      this.dog = new Dog(this, this.coat, W(task === 'fetch' ? P.dogX : 150), { stage: 'adult', y: W(P.ground) });
      this.dog.sprite.setDepth(45);
    }
    this.thought = new Thought(this, this.dog.sprite, 32);
  }

  // Where the dog stands on the walk: at the end of a loose (or tight) leash.
  dogX(tight) {
    const L = LEVEL3.walk.layout;
    return W(L.kidX + L.hand[0] + (tight ? L.tight : L.slack) - L.collar[0]);
  }

  demos() {
    const P = LEVEL3.fetch.layout, b = [W(P.ball[0]), W(P.ball[1]) - 8], d = this.dog?.sprite;
    return {
      walk: { caption: 'Press and hold anywhere to walk. Let go to stop.', steps: [{ hold: [400, 250], ms: 2000 }] },
      throw: { caption: 'Drag the ball back, then let go to throw it.', steps: [{ drag: [b, [b[0] - 50, b[1] + 10]], carry: 'ball' }] },
      rest: { caption: 'Tap the shady tree so {name} can rest. Then drag the water bowl to {name}.',
              steps: [{ tap: [W(40), W(100)] }, { drag: [[W(P.bowl[0]), W(P.bowl[1]) - 10], [W(P.restX), W(P.ground) - 30]], carry: 'water_bowl', arc: 30 }] },
      pet: { caption: "Drag Sam's hand onto {name}.", steps: [{ drag: [[W(LEVEL3.greet.samX) - 12, W(P.ground) - 54], [d ? d.x - 10 : 290, d ? d.y - 60 : 240]], carry: 'sam_hand', arc: 10 }] },
    };
  }

  startTask(task, retry = false) {
    this.cancel();
    this.task = task;
    const run = this.run;
    this.meter.reset();
    this.setDemo(null);
    if (task === 'walk') { this.hud.setTask('leash', 'Walk to the park'); this.walk(run, retry); }
    else if (task === 'fetch') { this.hud.setTask('ball', 'Fetch  1 of 2'); this.fetch(run, retry); }
    else { this.hud.setTask('pet', 'New friend  2 of 2'); this.greet(run, retry); }
  }

  // ---------------------------------------------------------------- The walk (hold to walk, let go when the dog pulls)
  async walk(run, retry) {
    const Wk = LEVEL3.walk, L = Wk.layout, end = W(L.width - 320);
    let offset = 0, holding = false, state = 'stopped', pullMs = 0, sight = null, told = false;
    this.street.x = 0;
    this.sights.forEach(s => { s.seen = false; s.s.setVisible(true).setPosition(W(s.x), W(L.distractions.find(d => d[0] === s.id)[2])).setAlpha(1); });
    this.kid.stop().setFrame(0);
    this.dog.sprite.x = this.dogX(false);
    this.dog.play('idle');
    this.leash.setTexture('leash_slack');

    await this.say(retry ? Wk.stopped : Wk.intro); if (!this.alive(run)) return;
    this.setDemo('walk');
    await this.showDemo('walk'); if (!this.alive(run)) return;

    const pad = this.own(this.add.zone(0, 0, 640, 360).setOrigin(0).setDepth(5).setInteractive());
    pad.on('pointerdown', () => { holding = true; });
    const up = () => { holding = false; };
    pad.on('pointerup', up).on('pointerout', up);
    this.input.on('pointerup', up);
    this.events.once('shutdown', () => this.input.off('pointerup', up));

    const lunge = s => {                                // a distraction: the dog pulls towards it
      state = 'lunge'; sight = s; pullMs = 0;
      s.seen = true;
      this.dog.play('lunge');
      this.leash.setTexture('leash_tight');
      this.tweens.add({ targets: this.dog.sprite, x: this.dogX(true), duration: 160 });
      sfx.play('bark');
    };
    const stop = async () => {                          // let go during a pull: the dog stops, sits, and the leash goes loose
      state = 'busy';
      this.leash.setTexture('leash_slack');
      this.tweens.add({ targets: this.dog.sprite, x: this.dogX(false), duration: 220 });
      this.dog.play('sit');
      this.gain(10);
      heart(this, this.dog.x, this.dog.sprite.y - 100);
      const s = sight.s;
      if (sight.id !== 'sandwich') this.tweens.add({ targets: s, y: s.y - 60, alpha: 0, duration: 700 });   // the squirrel and cat run off
      await this.wait(600); if (!this.alive(run)) return;
      if (!told) { told = true; await this.say(Wk.stopped); if (!this.alive(run)) return; }
      state = 'stopped';
    };

    await new Promise(done => {
      this.onFrame = async dt => {
        if (this.modals || state === 'busy') return;
        if (state === 'lunge') {
          if (!holding) { stop(); return; }
          pullMs += dt;
          if (pullMs > 700) {                           // kept walking while the dog pulled: it drags ahead
            state = 'busy';
            this.gain(-5);
            this.tweens.add({ targets: this.street, x: this.street.x - W(16), duration: 400 });
            const shown = await this.card('bad', Wk.pulled.fact, Wk.pulled.title); if (!this.alive(run)) return;
            if (!shown) await this.say(Wk.pulledAgain);
            if (!this.alive(run)) return;
            holding = false;
            stop();
          }
          return;
        }
        if (!holding) {
          if (state === 'walking') { state = 'stopped'; this.kid.stop().setFrame(0); this.dog.play('idle'); }
          return;
        }
        if (state !== 'walking') { state = 'walking'; this.kid.play('kid_walk'); this.dog.play('walk'); }
        offset = Math.min(end, offset + W(Wk.speed) * dt / 1000);
        this.street.x = -Math.round(offset / 2) * 2;
        this.progress();
        const next = this.sights.find(s => !s.seen && W(s.x) + this.street.x - this.dog.x < W(40));
        if (next) { this.kid.stop().setFrame(0); lunge(next); return; }
        if (offset >= end) { this.onFrame = null; done(); }
      };
    });
    if (!this.alive(run)) return;
    pad.destroy();
    this.kid.stop().setFrame(0);
    this.dog.play('wag');
    await this.say(Wk.done); if (!this.alive(run)) return;
    this.handOff('park', 'fetch');
  }

  // ---------------------------------------------------------------- Task 1: Fetch (and noticing when to stop)
  async fetch(run, retry) {
    const F = LEVEL3.fetch, P = F.layout, rest = { x: W(P.ball[0]), y: W(P.ball[1]) };
    let fetches = 0, busy = false, flopped = false, rested = false, watered = false, tired = false;
    this.dog.sprite.setPosition(W(P.dogX), W(P.ground)).setFlipX(false);
    this.dog.play('sit');
    const ball = this.own(touchable(art(this, rest.x, rest.y, 'ball', 0.5, 1).setDepth(50), { pad: 8, draggable: true }));
    glow(this, ball);
    const shadow = this.own(art(this, rest.x, rest.y, 'ball_shadow', 0.5, 0.5).setDepth(4).setVisible(false));
    const dots = Array.from({ length: 9 }, () => this.own(art(this, 0, 0, 'demo_dot', 0.5, 0.5).setDepth(49).setVisible(false)));
    const bowlHome = { x: W(P.bowl[0]), y: W(P.bowl[1]) };
    const bowl = this.own(touchable(this.add.sprite(bowlHome.x, bowlHome.y, 'water_bowl', 1).setOrigin(0.5, 1).setScale(2).setDepth(48), { pad: 6, draggable: true }));
    glow(this, bowl);
    const treeHit = this.own(this.add.zone(W(0), W(P.ground - 122), W(90), W(122 + 10)).setOrigin(0).setDepth(6).setInteractive({ cursor: CURSOR }));
    glow(this, treeHit, { target: this.tree });
    glow(this, treeHit, { target: this.shade });

    await this.say(retry ? F.flopLine : F.intro); if (!this.alive(run)) return;
    this.setDemo('throw');
    await this.showDemo('throw'); if (!this.alive(run)) return;

    const landing = pull => W(Phaser.Math.Clamp(P.land[0] + pull * 0.75, P.land[0], P.land[1]));
    const arcAt = (x1, u) => [rest.x + (x1 - rest.x) * u, rest.y - 6 - 120 * u * (1 - u)];
    ball.on('drag', (p, x, y) => {
      if (busy || flopped || rested) return;
      const dx = Phaser.Math.Clamp(x - rest.x, -W(40), 0), dy = Phaser.Math.Clamp(y - rest.y, -W(12), W(12));
      ball.setPosition(Math.round((rest.x + dx) / 2) * 2, Math.round((rest.y + dy) / 2) * 2);
      const x1 = landing(-dx / 2);
      dots.forEach((d, i) => d.setPosition(...arcAt(x1, (i + 1) / 10)).setVisible(-dx > 8));
    });
    const finish = () => {
      if (!(rested && watered)) return;
      this.done?.();
    };
    ball.on('dragend', async () => {
      dots.forEach(d => d.setVisible(false));
      const pull = (rest.x - ball.x) / 2;
      if (busy || flopped || rested || pull < 4) { ball.setPosition(rest.x, rest.y); return; }
      busy = true;
      this.progress();
      const x1 = landing(pull), t = { u: 0 };
      sfx.play('click');
      shadow.setVisible(true);
      await new Promise(r => this.tweens.add({ targets: t, u: 1, duration: 750, onUpdate: () => {
        const [bx, by] = arcAt(x1, t.u);
        ball.setPosition(Math.round(bx / 2) * 2, Math.round(by / 2) * 2);
        shadow.setPosition(Math.round(bx / 2) * 2, rest.y - 2);
      }, onComplete: r }));
      if (!this.alive(run)) return;
      shadow.setVisible(false);
      ball.setPosition(x1, rest.y);
      if (fetches >= F.tiredAfter + 1) {               // too tired: flops down instead of fetching
        flopped = true;
        this.dog.play('flop');
        this.thought.show('hot');
        this.gain(-5);
        await this.wait(900); if (!this.alive(run)) return;
        await this.card('bad', F.flop.fact, F.flop.title); if (!this.alive(run)) return;
        await this.say(F.flopLine); if (!this.alive(run)) return;
        this.setDemo('rest');
        await this.showDemo('rest'); if (!this.alive(run)) return;
        busy = false;
        return;
      }
      const speed = tired ? 70 : 220;
      this.dog.play(tired ? 'tired' : 'run');
      await this.dog.walkTo(x1 - W(14), speed, tired ? 'tired' : 'run'); if (!this.alive(run)) return;
      ball.setVisible(false);
      await this.dog.walkTo(W(P.dogX), tired ? 60 : 160, tired ? 'tired' : 'carry'); if (!this.alive(run)) return;
      this.dog.face(1);
      ball.setPosition(rest.x, rest.y).setVisible(true);
      fetches++;
      this.gain(10);
      heart(this, this.dog.x, this.dog.sprite.y - 100);
      tired = fetches >= F.tiredAfter;
      this.dog.play(tired ? 'pant' : 'sit');           // the signs: panting, then slowing down. No cue: the player has to notice.
      busy = false;
    });

    treeHit.on('pointerup', async () => {
      if (busy || rested || this.modals) return;
      if (!tired && !flopped) { await this.say(F.tooSoon); return; }
      busy = true;
      this.thought.hide();
      ball.setVisible(false);
      await this.dog.walkTo(W(P.restX), 70, 'tired'); if (!this.alive(run)) return;
      this.dog.face(1).play('rest');
      rested = true; flopped = false;
      this.gain(15);
      await this.say(watered ? F.shade : `${F.shade} ${F.needWater}`); if (!this.alive(run)) return;
      busy = false;
      finish();
    });

    bowl.on('drag', (p, x, y) => bowl.setPosition(Math.round(x / 2) * 2, Math.round(y / 2) * 2));
    bowl.on('dragend', async () => {
      const d = this.dog.sprite, over = Math.abs(bowl.x - d.x) < 70 && bowl.y > d.y - 110 && bowl.y < d.y + 20;
      if (!over || busy || watered || this.modals) { this.tweens.add({ targets: bowl, x: bowlHome.x, y: bowlHome.y, duration: 250 }); return; }
      if (!tired && !flopped) { this.tweens.add({ targets: bowl, x: bowlHome.x, y: bowlHome.y, duration: 250 }); await this.say(F.tooSoon); return; }
      busy = true;
      bowl.setPosition(d.x + (d.flipX ? -W(20) : W(20)), d.y).disableInteractive();
      this.dog.play('drink');
      sfx.play('wag');
      await this.wait(1600); if (!this.alive(run)) return;
      bowl.setFrame(0);
      watered = true;
      this.thought.hide();
      this.gain(15);
      this.dog.play(rested ? 'rest' : 'pant');
      await this.say(rested ? F.water : `${F.water} ${F.needShade}`); if (!this.alive(run)) return;
      busy = false;
      finish();
    });

    await new Promise(r => { this.done = r; }); if (!this.alive(run)) return;
    this.done = null;
    this.dog.play('rest');
    await this.card('info', F.tip.fact, F.tip.title); if (!this.alive(run)) return;
    await this.say(F.done); if (!this.alive(run)) return;
    this.handOff('l3_later', 'greet');
  }

  // ---------------------------------------------------------------- Task 2: Meeting a new friend (Sam)
  async greet(run, retry) {
    const G = LEVEL3.greet, P = LEVEL3.fetch.layout, ground = W(P.ground);
    const stressed = this.entry.stressed ?? Math.random() < 0.5;   // one of two variants: the dog shows stress signals (data.stressed forces one, for testing)
    this.dog.sprite.setPosition(W(150), ground).setFlipX(false);
    this.dog.play('idle');
    const sam = this.own(this.add.sprite(W(340), ground, 'sam_run', 0).setOrigin(0.5, 1).setScale(2).setFlipX(true).setDepth(44));
    const samTo = (x, anim, ms) => {
      sam.play(anim);
      return new Promise(r => this.tweens.add({ targets: sam, x: W(x), duration: ms, onComplete: () => { sam.stop(); r(); } }));
    };
    const samPose = pose => sam.stop().setTexture(`sam_${pose}`, 0);

    await samTo(280, 'sam_run', 900); if (!this.alive(run)) return;
    samPose('run');
    await this.say(G.hello, 'sam'); if (!this.alive(run)) return;

    // Step 1: Sam wants to run over
    for (;;) {
      const o = await this.ask(G.step1.question, G.step1.choices, 'parent'); if (!this.alive(run)) return;
      if (o.ok) { this.gain(15); await this.card('good', G.step1.good); if (!this.alive(run)) return; break; }
      await samTo(G.samX + 10, 'sam_run', 500); if (!this.alive(run)) return;
      samPose('stand');
      this.dog.play('nervous'); sfx.play('bark');
      this.gain(-5);
      await this.wait(700); if (!this.alive(run)) return;
      await this.card('bad', G.step1.bad); if (!this.alive(run)) return;
      await this.say(G.step1.again); if (!this.alive(run)) return;
      this.dog.play('idle');
      await samTo(280, 'sam_walk', 900); if (!this.alive(run)) return;
      sam.setFlipX(true); samPose('run');
    }
    await this.say(G.step1.samSlow, 'sam'); if (!this.alive(run)) return;
    await samTo(G.samX, 'sam_walk', 1600); if (!this.alive(run)) return;
    samPose('stand');

    // Step 2: read the dog. Calm: a loose wag. Stressed: lip licking, yawning, whale eye, tail tucked.
    this.dog.play(stressed ? 'stress' : 'wag');
    await this.wait(1400); if (!this.alive(run)) return;
    const S2 = G.step2, lines = stressed ? S2.stressed : S2.calm;
    for (;;) {
      const o = await this.ask(S2.question, S2.choices, 'parent', { side: true }); if (!this.alive(run)) return;
      const right = stressed ? o.id === 'space' : o.id === 'sniff';
      if (right) {
        this.gain(15);
        if (stressed) {
          await this.card('good', lines.space, this.f(lines.title)); if (!this.alive(run)) return;
          samPose('wave');
          await this.say(S2.samBye, 'sam'); if (!this.alive(run)) return;
        } else {
          samPose('hand');
          await this.say(S2.samSniff, 'sam'); if (!this.alive(run)) return;
          this.dog.play('sniff');
          await this.wait(1500); if (!this.alive(run)) return;
          this.dog.play('wag'); sfx.play('wag');
          heart(this, this.dog.x + 20, this.dog.sprite.y - 100);
          await this.card('good', lines.sniff); if (!this.alive(run)) return;
          samPose('stand');
        }
        break;
      }
      if (!stressed && o.id === 'space') { await this.say(lines.space); if (!this.alive(run)) return; continue; }
      this.gain(-5);
      if (o.id === 'pet' && !stressed) { this.dog.play('duck'); }
      const shown = await this.card('bad', lines[o.id]); if (!this.alive(run)) return;
      if (!shown) { await this.say(stressed ? S2.stressed.space : S2.calm.pet); if (!this.alive(run)) return; }
      this.dog.play(stressed ? 'stress' : 'wag');
    }

    // Step 3 (calm only): where to pet. Drag Sam's hand onto the dog: the head (no) or the side of the neck and chest (yes).
    if (!stressed) {
      const S3 = G.step3;
      await this.say(S3.prompt); if (!this.alive(run)) return;
      this.setDemo('pet');
      await this.showDemo('pet'); if (!this.alive(run)) return;
      const d = this.dog.sprite, x0 = d.x - 48, y0 = d.y - 96;
      const rings = { head: this.own(art(this, x0, y0, 'adult_ring_head').setDepth(46).setVisible(false)),
                      chest: this.own(art(this, x0, y0, 'adult_ring_chest').setDepth(46).setVisible(false)) };
      const partAt = (px, py) => {
        const x = Math.floor((px - x0) / 2), y = Math.floor((py - y0) / 2);
        if (x < 0 || y < 0 || x >= 48 || y >= 48) return null;
        return ['head', 'chest'].find(p => this.textures.getPixelAlpha(x, y, `adult_part_${p}`) > 0) ?? null;
      };
      const home = { x: W(G.samX) - 12, y: ground - 54 };
      const hand = this.own(touchable(art(this, home.x, home.y, 'sam_hand', 0.5, 0.5).setFlipX(true).setDepth(60), { pad: 8, draggable: true }));
      glow(this, hand);
      await new Promise(done => {
        let over = null, busy = false;
        hand.on('drag', (p, x, y) => {
          hand.setPosition(Math.round(x / 2) * 2, Math.round(y / 2) * 2);
          const now = partAt(hand.x - 8, hand.y);
          if (now !== over) { if (over) rings[over].setVisible(false); if (now) rings[now].setVisible(true); over = now; }
        });
        hand.on('dragend', async () => {
          if (over) rings[over].setVisible(false);
          const part = over; over = null;
          if (!part || busy) { this.tweens.add({ targets: hand, x: home.x, y: home.y, duration: 220 }); return; }
          busy = true;
          if (part === 'head') {
            this.gain(-5);
            this.dog.play('duck');
            hand.setPosition(home.x, home.y);
            await this.wait(900); if (!this.alive(run)) return;
            const shown = await this.card('bad', S3.head); if (!this.alive(run)) return;
            if (!shown) await this.say(S3.headAgain);
            if (!this.alive(run)) return;
            this.dog.play('wag');
            busy = false;
            return;
          }
          hand.setVisible(false).disableInteractive();
          samPose('pet');
          this.dog.play('wag'); sfx.play('wag');
          this.gain(15);
          heart(this, d.x + 10, d.y - 100);
          this.time.delayedCall(400, () => heart(this, d.x - 10, d.y - 110));
          await this.wait(1000); if (!this.alive(run)) return;
          await this.card('good', S3.chest); if (!this.alive(run)) return;
          await this.say(S3.samHappy, 'sam'); if (!this.alive(run)) return;
          done();
        });
      });
      if (!this.alive(run)) return;
      samPose('wave');
    }

    await this.card('info', G.both.fact, G.both.title); if (!this.alive(run)) return;
    sam.setFlipX(false);
    await samTo(360, 'sam_walk', 1800); if (!this.alive(run)) return;
    this.dog.play('wag');
    this.complete(run);
  }
}
