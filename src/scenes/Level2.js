// Level 2: Check-up Day (GAME_DESIGN.md §7). Task 1 Spot the Difference at the vet (a healthy dog and the right products vs your dog
// and the bag from home), the vaccine cutscene and "That evening", then Task 2 Bath Time (drag each care item onto the right part).
// Art and layout: asset group 10 (SPOT, CU_HITS, BATH in tools/sprites.py, mirrored in LEVEL2). Cancel/retry rules: see LevelBase.js.
import { LevelBase } from './LevelBase.js';
import { LEVEL2 } from '../content.js';
import { art, button, glow, nine, text, touchable, W, CURSOR } from '../ui.js';
import { sfx } from '../sfx.js';

const COAT_PARTS = ['teeth', 'coat', 'paws', 'ears', 'eyes', 'tail', 'toy'];   // close-ups that show the dog, so they come per coat
const CU = { y: 84, xs: [64, 336] };                                           // where the two close-ups sit (canvas px)
const BATH_PARTS = ['neck', 'ears', 'teeth', 'paws', 'coat'];                  // drop targets, most specific first

export class Level2 extends LevelBase {
  constructor() { super('Level2'); }

  create() {
    this.setup(LEVEL2, 2);
    const task = this.entry.task ?? 'spot';
    art(this, 0, 0, task === 'spot' ? 'spot_bg' : 'bath_bg');
    this.setupUi();
    this.startTask(task);
  }

  demos() {
    const L = LEVEL2.spot.layout, B = LEVEL2.bath.layout;
    const yx = W(L.frames[1] + L.dogDx), yy = W(L.dogFeet - L.bigGround);
    const dx = W(B.matX), dy = W(B.matFeet - B.bigGround), tx = W(B.tubX), ty = W(B.tubFeet - B.bigGround);
    return {
      spot: { caption: 'Tap any part of {name}, or any product on the tray, to look closer.', steps: [{ tap: [yx + W(56), yy + W(54)] }, { tap: [W(L.frames[1] + 46), W(156)] }] },
      closer: { caption: 'Tap the difference in either picture. If they look the same, tap Back.', steps: [{ tap: [CU.xs[1] + 120, CU.y + 80] }, { tap: [320, 332] }] },
      bath: { caption: 'Drag a thing from the shelf onto the right part of {name}.',
              steps: [{ drag: [[W(B.shelfX + 6), W(B.boards[0] - 6)], [dx + W(66), dy + W(28)]], carry: 'care_toothbrush', arc: 30 }] },
      scrub: { caption: 'Hold and rub back and forth over {name} to make bubbles.', steps: [{ rub: [[tx + W(18), ty + W(26)], [tx + W(52), ty + W(26)]] }] },
      dry: { caption: 'Hold and rub back and forth over {name} with the towel.', steps: [{ rub: [[dx + W(18), dy + W(26)], [dx + W(52), dy + W(26)]] }] },
    };
  }

  startTask(task, retry = false) {
    this.cancel();
    this.task = task;
    const run = this.run;
    this.meter.reset();
    this.setDemo(null);
    if (task === 'spot') { this.speaker = 'vet'; this.spot(run, retry); }
    else { this.speaker = 'parent'; this.hud.setTask('bath', 'Bath time  2 of 2'); this.bath(run, retry); }
  }

  // ---------------------------------------------------------------- Task 1: Spot the Difference
  async spot(run, retry) {
    const S = LEVEL2.spot, L = S.layout;
    this.found = new Set();
    this.hud.setTask('magnifier', `Found 0 of ${S.total}`);
    const sides = L.frames.map((fx, i) => this.picture(fx, i === 0 ? 'healthy' : 'yours'));
    // hovering a part (or product) lights it up in both pictures
    const pair = id => sides.map(s => s.parts[id]);
    for (const id of [...S.bodyParts, ...S.tray]) {
      const [a, b] = pair(id);
      for (const p of [a, b]) {
        p.hit.on('pointerover', () => { a.light.show(); b.light.show(); }).on('pointerout', () => { a.light.hide(); b.light.hide(); })
          .on('pointerup', () => { sfx.play('click'); this.onAct?.(id); });
      }
    }
    this.yours = sides[1];
    await this.say(retry ? S.closer : S.intro); if (!this.alive(run)) return;
    this.setDemo('spot');
    await this.showDemo('spot'); if (!this.alive(run)) return;
    this.nextHint();

    while (this.found.size < S.total) {
      const id = await new Promise(r => { this.onAct = r; }); if (!this.alive(run)) return;
      this.onAct = null;
      pair(id).forEach(p => p.light.hide());
      this.progress();
      await this.closer(id, run); if (!this.alive(run)) return;
      this.setDemo('spot');
      this.nextHint();
    }
    this.hintText = null;
    await this.say(S.done); if (!this.alive(run)) return;
    this.handOff('vaccine', 'bath');                    // the vaccine, "That evening", then back here for the bath
  }

  // One framed picture: the dog (with every problem on "your" side), the tray of products, invisible pixel-exact hit shapes and
  // hover rings. Returns { parts: { id: { hit, light } } } and the dog's top-left for placing found circles.
  picture(fx, side) {
    const S = LEVEL2.spot, L = S.layout, yours = side === 'yours';
    const x0 = W(fx + L.dogDx), y0 = W(L.dogFeet - L.bigGround);
    this.own(text(this, W(fx + 45) + 60, W(L.top + 3), yours ? this.dogName : 'Healthy', 14).setOrigin(0.5, 0).setDepth(20));
    this.own(art(this, x0, y0, `big_${this.coat}`).setDepth(10));
    if (yours) for (const n of ['nails', 'ears', 'teeth', 'fleas']) this.own(art(this, x0, y0, `issue_${n}`).setDepth(11));
    const parts = {};
    for (const id of S.bodyParts) {
      const ring = this.own(art(this, x0, y0, `ring_${id}`).setDepth(12).setVisible(false));
      const hit = this.own(art(this, x0, y0, `part_${id}`).setAlpha(0.001).setDepth(13));
      touchable(hit, { exact: true });
      parts[id] = { hit, light: { show: () => ring.setVisible(true), hide: () => ring.setVisible(false) } };
    }
    S.tray.forEach((id, i) => {
      const key = `tray_${id}_${yours && id !== 'brush' ? 'home' : 'dog'}`;
      const img = this.own(art(this, W(fx + L.itemXs[i]), W(L.itemBottom), key, 0.5, 1).setDepth(10));
      touchable(img, { pad: 4 });
      parts[id] = { hit: img, light: glow(this, img, { hover: false }) };
    });
    return { fx, x0, y0, parts };
  }

  nextHint() {
    const S = LEVEL2.spot;
    const left = Object.entries(S.diffs).find(([k]) => !this.found.has(k));
    if (left) this.setHint(S.hint.replace('{part}', S.names[left[1].part]));
  }

  // The closer look: both close-ups side by side. Tap the difference (+15 and the vet's fact), miss (-5), or Back.
  async closer(id, run) {
    const S = LEVEL2.spot;
    const diff = Object.entries(S.diffs).find(([, d]) => d.part === id);
    const key = side => `cu_${id}_${diff || side === 'healthy' ? side : 'healthy'}${COAT_PARTS.includes(id) ? '_' + this.coat : ''}`;
    sfx.play('page');
    const c = this.own(this.add.container(0, 0).setDepth(200));
    c.add(this.add.rectangle(0, 0, 640, 360, 0x3E2A24, 0.55).setOrigin(0).setInteractive());
    const rings = [];
    ['healthy', 'yours'].forEach((side, i) => {
      const x = CU.xs[i];
      c.add(nine(this, x - 8, 48, 'card_info', 256, 264, 6));
      c.add(text(this, x + 120, 58, side === 'healthy' ? 'Healthy' : this.dogName, 16).setOrigin(0.5, 0));
      const img = art(this, x, CU.y, key(side)).setInteractive({ cursor: CURSOR });
      c.add(img);
      img.on('pointerup', () => this.onCloser?.('miss'));
      if (diff) {
        const [hx, hy, hw, hh] = diff[1].hit;
        const z = this.add.zone(x + W(hx), CU.y + W(hy), W(hw), W(hh)).setOrigin(0).setInteractive({ cursor: CURSOR });
        z.on('pointerup', () => this.onCloser?.('hit'));
        c.add(z);
        const r = art(this, x + W(hx - 3), CU.y + W(hy - 3), `found_cu_${id}`).setVisible(this.found.has(diff[0]));
        c.add(r); rings.push(r);
      }
    });
    let back, foundNow = false;
    const done = new Promise(r => { back = button(this, 270, 316, 100, 32, 'Back', r, { size: 17 }); c.add(back); });
    await this.modal(async () => {
      this.setDemo('closer');
      if (!this.found.has(diff?.[0])) await this.showDemo('closer');
      if (!this.alive(run)) return;
      if (!diff) { await this.say(S.decoys[id]); return; }
      if (this.found.has(diff[0])) { await this.say(S.already); return; }
      let missed = false;
      for (;;) {
        const what = await Promise.race([done.then(() => 'back'), new Promise(r => { this.onCloser = r; })]);
        this.onCloser = null;
        if (!this.alive(run) || what === 'back') return;
        if (what === 'hit') {
          foundNow = true;
          rings.forEach(r => r.setVisible(true));
          this.markFound(diff[0]);
          await this.wait(500); if (!this.alive(run)) return;
          await this.card('good', diff[1].fact, 'Found it!');
          return;
        }
        if (!missed) { missed = true; this.gain(-5); await this.say(S.miss); }
        else await this.say(S.missAgain);
        if (!this.alive(run)) return;
      }
    });
    if (!this.alive(run)) return;
    if (!foundNow) await done;                          // decoys, repeats and misses: the player reads, then taps Back
    c.destroy();
  }

  markFound(d) {
    const S = LEVEL2.spot, L = S.layout, D = S.diffs[d], y = this.yours;
    this.found.add(d);
    this.gain(15);
    this.hud.setTask('magnifier', `Found ${this.found.size} of ${S.total}`);
    let x, top;
    if (D.ring) { x = y.x0 + W(D.ring[0]); top = y.y0 + W(D.ring[1]); }
    else {
      const img = y.parts[D.part].hit;
      x = img.x - 20; top = img.y - img.displayHeight / 2 - 18;
    }
    this.own(art(this, x, top, 'found_ring_small').setDepth(14));
  }

  // ---------------------------------------------------------------- Task 2: Bath Time
  async bath(run, retry) {
    const B = LEVEL2.bath, L = B.layout;
    this.tubFront = this.own(art(this, 0, 0, 'bath_tub_front').setDepth(15));   // over the dog only while it is in the tub
    // the dog (with the problems still showing), its hover rings and the shapes used to tell which part an item is over
    const dog = this.own(this.add.container(W(L.matX), W(L.matFeet - L.bigGround)).setDepth(20));
    this.bigDog = art(this, 0, 0, `big_${this.coat}`);
    dog.add(this.bigDog);
    this.issues = {};
    for (const n of ['nails', 'ears', 'teeth', 'fleas']) { this.issues[n] = art(this, 0, 0, `issue_${n}`); dog.add(this.issues[n]); }
    this.foam = this.add.sprite(0, 0, 'foam', 0).setOrigin(0).setScale(2).setVisible(false);
    dog.add(this.foam);
    this.rings = {};
    for (const p of BATH_PARTS) { this.rings[p] = art(this, 0, 0, `ring_${p}`).setVisible(false); dog.add(this.rings[p]); }
    this.dogBox = dog;

    this.done = new Set();
    this.phase = 'mat';
    B.order.forEach((id, i) => this.shelfItem(id, i, run));
    await this.say(retry ? B.hint : B.intro); if (!this.alive(run)) return;
    this.setDemo('bath');
    await this.showDemo('bath'); if (!this.alive(run)) return;
    this.setHint(B.hint);
    await new Promise(r => { this.bathDone = r; }); if (!this.alive(run)) return;
    this.hintText = null;
    this.bigDog.setFrame(1);
    sfx.play('wag');
    await this.say(B.done); if (!this.alive(run)) return;
    this.complete(run);
  }

  // A care item on the shelf: drag it onto the dog. Its own pixels are the grab area (the shelf is tight).
  shelfItem(id, i, run) {
    const B = LEVEL2.bath, L = B.layout;
    const key = { shampoo: 'tray_shampoo_dog', flea: 'tray_flea_dog' }[id] ?? `care_${id}`;
    const home = { x: W(L.shelfX + (i % 3) * 16 - 4), y: W(L.boards[Math.floor(i / 3)]) };
    const img = this.own(art(this, home.x, home.y, key, 0, 1).setDepth(40));
    touchable(img, { exact: true, draggable: true });
    glow(this, img);
    const back = () => this.tweens.add({ targets: img, x: home.x, y: home.y, duration: 220 });
    let over = null;
    img.on('dragstart', () => { this.progress(); sfx.play('click'); img.setDepth(60); });
    img.on('drag', (p, x, y) => {
      img.setPosition(Math.round(x / 2) * 2, Math.round(y / 2) * 2);
      const now = this.partAt(p.worldX, p.worldY);
      if (now !== over) { if (over) this.rings[over].setVisible(false); if (now) this.rings[now].setVisible(true); over = now; }
    });
    img.on('dragend', async () => {
      img.setDepth(40);
      if (over) this.rings[over].setVisible(false);
      const part = over;
      over = null;
      if (!part) { back(); return; }
      await this.drop(id, part, img, back, run);
    });
  }

  // Which body part (if any) is under a canvas point: the part masks, looked up by pixel.
  partAt(px, py) {
    const d = this.dogBox, x = Math.floor((px - d.x) / 2), y = Math.floor((py - d.y) / 2);
    if (x < 0 || y < 0 || x >= 76 || y >= 62) return null;
    return BATH_PARTS.find(p => this.textures.getPixelAlpha(x, y, `part_${p}`) > 0) ?? null;
  }

  async drop(id, part, img, back, run) {
    const B = LEVEL2.bath, it = B.items[id];
    const allowed = { mat: ['toothbrush', 'clippers', 'ear'], tub: ['shampoo'], dry: ['towel'], flea: ['flea'] }[this.phase] ?? [];
    back();
    if (this.done.has(id)) { await this.say(B.notYet.done); return; }
    if (!allowed.includes(id)) { await this.say(B.notYet[id] ?? B.hint); return; }
    if (it.part !== part && !(it.part === 'coat' && part !== 'neck' && (id === 'shampoo' || id === 'towel'))) {
      this.gain(-5);
      await this.say(B.wrong.replace('{item}', it.name).replace('{part}', it.part === 'paws' ? 'paws (nails)' : it.part));
      return;
    }
    // right place
    this.done.add(id);
    img.setVisible(false).disableInteractive();
    this.gain(15);
    if (it.issue) { this.tweens.add({ targets: this.issues[it.issue], alpha: 0, duration: 500 }); }
    this.bigDog.setFrame(1);
    this.time.delayedCall(700, () => this.bigDog.setFrame(0));
    await this.say(it.line); if (!this.alive(run)) return;
    if (id === 'shampoo' || id === 'towel') {
      if (!await this.rub(id, run)) return;
    }
    if (this.phase === 'mat' && this.done.size === 3) {
      await this.say(B.tub); if (!this.alive(run)) return;
      await this.moveDog(B.layout.tubX, B.layout.tubFeet, true); if (!this.alive(run)) return;
      this.phase = 'tub';
    } else if (this.phase === 'flea' && id === 'flea') {
      this.bathDone?.();
    }
  }

  // Rub back and forth over the dog: shampoo makes foam grow; the towel dries it off.
  async rub(id, run) {
    const B = LEVEL2.bath;
    this.setDemo(id === 'shampoo' ? 'scrub' : 'dry');
    await this.showDemo(this.demoKey); if (!this.alive(run)) return false;
    const d = this.dogBox;
    if (id === 'shampoo') this.foam.setFrame(0).setVisible(true).setAlpha(1);
    const zone = this.own(this.add.zone(d.x + W(10), d.y + W(8), W(56), W(40)).setOrigin(0).setDepth(50).setInteractive({ cursor: CURSOR }));
    glow(this, zone);
    let dist = 0, last = null;
    await new Promise(res => {
      zone.on('pointermove', p => {
        if (!p.isDown) { last = null; return; }
        if (last) dist += Math.abs(p.worldX - last.x) + Math.abs(p.worldY - last.y);
        last = { x: p.worldX, y: p.worldY };
        this.progress();
        const u = Math.min(1, dist / B.rubNeeded);
        if (id === 'shampoo') this.foam.setFrame(Math.min(2, Math.floor(u * 3)));
        else this.foam.setVisible(false);
        if (u >= 1) res();
      });
      zone.on('pointerup', () => { last = null; });
    });
    zone.destroy();
    if (!this.alive(run)) return false;
    this.setDemo('bath');
    sfx.play('wag');
    if (id === 'shampoo') {
      await this.say(B.scrubbed); if (!this.alive(run)) return false;
      this.tweens.add({ targets: this.foam, alpha: 0, duration: 400 });
      await this.moveDog(B.layout.matX, B.layout.matFeet, false); if (!this.alive(run)) return false;
      this.phase = 'dry';
    } else {
      await this.say(B.dried); if (!this.alive(run)) return false;
      this.phase = 'flea';
    }
    return true;
  }

  // The dog hops into (or out of) the tub: a little arc, with the tub's front drawn over it while inside.
  moveDog(x, feet, intoTub) {
    const d = this.dogBox, L = LEVEL2.bath.layout, x0 = d.x, y0 = d.y, x1 = W(x), y1 = W(feet - L.bigGround);
    if (!intoTub) this.tubFront.setDepth(15);
    sfx.play('bark');
    const t = { u: 0 };
    return new Promise(r => this.tweens.add({ targets: t, u: 1, duration: 600, ease: 'Sine.easeInOut',
      onUpdate: () => d.setPosition(Math.round((x0 + (x1 - x0) * t.u) / 2) * 2, Math.round((y0 + (y1 - y0) * t.u - 80 * t.u * (1 - t.u)) / 2) * 2),
      onComplete: () => { if (intoTub) this.tubFront.setDepth(30); r(); } }));
  }
}
