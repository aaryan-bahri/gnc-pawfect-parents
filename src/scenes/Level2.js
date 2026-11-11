// Level 2: Check-up & Shopping (GAME_DESIGN.md §7). Task 1 Help the Vet, Task 2 Pet Store Run. Task structure and cancel/retry rules:
// see LevelBase.js.
import { LevelBase } from './LevelBase.js';
import { HappinessMeter } from '../meter.js';
import { LEVEL2, fill } from '../content.js';
import { Dog } from '../dog.js';
import { art, button, cue, nine, text, touchable, Hud, ParentDialog, ShoppingList, W, CLINIC, CURSOR } from '../ui.js';
import { sfx } from '../sfx.js';
import { load } from '../save.js';

const LENS = { x: W(166), y: W(124) };                  // where close-ups happen: items fly out from here to the shopping list
const ITEM_IDS = LEVEL2.shop.vetNeeds;

export class Level2 extends LevelBase {
  constructor() { super('Level2'); }

  // data = { task: 'vet' | 'shop', wrongs } (the vaccine cutscene sits between the two tasks and passes the state back)
  init(data) { super.init(); this.entry = data ?? {}; }

  create() {
    this.resetRun();
    const { name, coat } = load();
    this.f = s => fill(s, name);
    this.cfg = LEVEL2;
    this.input.once('pointerdown', () => sfx.unlock());
    const task = this.entry.task ?? 'vet';
    this.level = 2;
    if (task === 'vet') {                               // the clinic, the vet and the nervous dog on the table
      art(this, 0, 0, 'vet_clinic');
      this.add.sprite(W(CLINIC.vetX), W(CLINIC.vetFeet), 'vet_stand').setOrigin(0.5, 1).setScale(2).setDepth(40).play('vet_stand');
      this.dog = new Dog(this, coat, W(CLINIC.dogX), { stage: 'young', y: W(CLINIC.dogFeet) });
    } else {                                            // the store (the dog waits at home, so there is no dog here)
      art(this, 0, 0, 'store_aisle');
    }
    this.meter = new HappinessMeter({ drainPerSec: LEVEL2.drainPerSec, onEmpty: () => this.fail() });
    this.hud = new Hud(this, this.meter, { name, onPause: () => this.pause() });
    this.speaker = task === 'vet' ? 'vet' : 'parent';
    this.talk = new ParentDialog(this, this.speaker);
    this.wrongs = this.entry.wrongs ?? 0;
    this.startTask(task);
  }

  // A line from whoever is speaking (the vet in the clinic, the parent for the shopping trip and retries).
  // In the shop the bubble would sit on the aisle sign, the arrows and the top of the shelf, so a line there is only shown for
  // as long as it takes to read (and it goes the moment the player acts). The till and the retry screen keep theirs.
  say(line) {
    this.talk.setWho(this.speaker);
    const tip = this.task === 'shop' && !this.tilling && !this.failing;
    this.talk.say(this.f(line), tip ? 2400 + line.length * 45 : 0);
  }

  startTask(task, retry = false) {
    this.cancel();
    this.task = task;
    const run = this.run;
    this.meter.reset();
    if (task === 'vet') { this.hud.setTask('vet', 'Check-up  1 of 2'); this.vet(run, retry); }
    else { this.hud.setTask('coin', 'Shopping  2 of 2'); this.shop(run, retry); }
  }

  // ---------------------------------------------------------------- Task 1: Help the Vet
  async vet(run, retry) {
    const V = LEVEL2.vet;
    this.speaker = 'vet';
    this.setHint(V.hint);
    this.say(retry ? V.hint : V.intro);
    this.dog.play('nervous');
    this.list = this.own(new ShoppingList(this, 4, 206, ITEM_IDS.length, LEVEL2.items));
    const spots = V.spots.map(s => this.makeSpot(s));
    let arrow = this.own(cue(this, W(spots[0].s.ring[0]), W(spots[0].s.ring[1]) - 13));   // a pointer cue on the first spot only
    this.dog.sprite.setInteractive({ cursor: CURSOR }).on('pointerup', () => this.onAct?.({ id: 'pat' }));

    let petReady = true, told = false;                  // one calming pat per gap between checks (+5)
    while (spots.some(sp => !sp.done)) {
      const act = await new Promise(r => { this.onAct = r; }); if (!this.alive(run)) return;
      this.onAct = null;                                // clicks are ignored until the next wait

      if (act.id === 'pat') {
        if (!petReady) continue;
        petReady = false;
        this.progress();
        this.dog.play('wag'); sfx.play('wag');
        const h = this.own(art(this, this.dog.x + 10, this.dog.sprite.y - 90, 'icon_heart', 0.5, 0.5).setDepth(140));
        this.tweens.add({ targets: h, y: h.y - 30, alpha: 0, duration: 900, onComplete: () => h.destroy() });
        this.gain(5);
        this.say(V.patDone);
        await this.wait(1100); if (!this.alive(run)) return;
        this.dog.play('nervous');
        continue;
      }

      const sp = spots.find(x => x.s.id === act.id);
      if (sp.done) continue;
      arrow?.destroy(); arrow = null;
      await this.closeUp(sp, run); if (!this.alive(run)) return;
      sp.done = true;
      sp.ring.stop().setTexture('icon_check');
      sp.pill.setAlpha(0.6);
      sp.zones.forEach(z => z.disableInteractive());
      petReady = true;
      this.setHint(V.hint);
      if (!told && spots.some(x => !x.done)) { told = true; this.say(V.pat); }
    }

    this.hintText = null;
    this.dog.play('sit');
    this.say(V.done);
    await this.wait(2600); if (!this.alive(run)) return;
    // the vaccine is a cutscene beat; the shopping trip follows it
    this.scene.start('Cutscene', { key: 'vaccine', next: { scene: 'Level2', data: { task: 'shop', wrongs: this.wrongs } } });
  }

  // One spot to check: a blinking ring on the dog, a label next to it, and a hit zone for each (fingers need the label).
  makeSpot(s) {
    const [rx, ry] = s.ring, [px, py] = s.pill;
    const sp = { s, done: false, zones: [] };
    sp.ring = this.own(this.add.sprite(W(rx), W(ry), 'spot_ring').setScale(2).setDepth(60).play('spot_ring'));
    sp.pill = this.own(this.add.container(W(px), W(py), [nine(this, 0, 0, 'card_info', 52, 28, 6),
      text(this, 26, 5, s.label, 13).setOrigin(0.5, 0)]).setDepth(60));
    const hit = (x, y, w, h) => {
      const z = this.own(this.add.zone(x, y, w, h).setOrigin(0).setDepth(61).setInteractive({ cursor: CURSOR }));
      z.on('pointerup', () => { sfx.play('click'); this.onAct?.({ id: s.id }); });
      sp.zones.push(z);
    };
    hit(W(rx) - 12, W(ry) - 12, 24, 24);
    hit(W(px) - 4, W(py) - 4, 60, 36);
    return sp;
  }

  // The magnifying-glass close-up: the vet explains, what it found flies onto the shopping list, then "Next".
  async closeUp(sp, run) {
    const { coat } = load(), s = sp.s;
    this.meter.pause();                                 // reading time is free
    sfx.play('page');
    const box = this.own(this.add.container(0, 0).setDepth(90));
    box.add(art(this, 0, 0, `closeup_${s.id}_${coat}`));
    this.say(s.say);
    await this.wait(800); if (!this.alive(run)) return;
    for (const id of s.items) { await this.flyToList(id, run); if (!this.alive(run)) return; }
    await new Promise(r => { const b = this.own(button(this, 504, 296, 112, 32, 'Next', () => { b.destroy(); r(); }, { size: 18 }).setDepth(95)); });
    if (!this.alive(run)) return;
    box.destroy();
    this.meter.resume();
    this.progress();
  }

  flyToList(id, run) {
    const to = this.list.nextPos();
    const icon = this.own(art(this, LENS.x, LENS.y, `icon_${id}`, 0.5, 0.5).setDepth(200));
    return new Promise(r => this.tweens.add({ targets: icon, x: to.x, y: to.y, duration: 600, ease: 'Sine.easeInOut',
      onComplete: () => { icon.destroy(); if (this.alive(run)) { this.list.add(id); sfx.play('chime'); this.hud.bump(); } r(); } }));
  }

  // ---------------------------------------------------------------- Task 2: Pet Store Run
  // Four aisles (tap an item for its price, then Add), a basket, a coin jar, and a till where each item is explained.
  // Needs = the nine things on the paper. Wants = optional extras that must not eat the needs' coins. Look-alikes = wrong pick (-5).
  async shop(run, retry) {
    const S = LEVEL2.shop;
    this.speaker = 'parent';
    this.needs = [...S.vetNeeds, ...S.parentNeeds];
    this.tilling = false;
    this.coins = S.budget; this.basket = []; this.paid = new Set(); this.sawWant = false; this.announced = false; this.aisle = 0; this.layer = null; this.moving = false;   // (a retry can kill a slide mid-way)
    this.list = this.own(new ShoppingList(this, 4, 132, this.needs.length, LEVEL2.items));
    S.vetNeeds.forEach(id => this.list.add(id));
    this.buildStoreUi();
    this.showAisle(0);

    if (retry) S.parentNeeds.forEach(id => this.list.add(id));
    else {                                              // the parent writes four more things on the list
      this.meter.pause();
      this.say(S.intro);
      await this.wait(2600); if (!this.alive(run)) return;
      this.say(S.parent);
      for (const id of S.parentNeeds) { await this.wait(500); if (!this.alive(run)) return; this.list.add(id); sfx.play('chime'); }
      await this.wait(2800); if (!this.alive(run)) return;
      this.meter.resume();
    }
    this.say(S.hint);
    this.setHint(S.hint);

    for (;;) {
      const act = await new Promise(r => { this.onAct = r; }); if (!this.alive(run)) return;
      this.onAct = null;                                // taps are ignored while an action plays out
      this.talk.hide();                                 // the player is shopping: get the bubble off the shelf
      if (act.type === 'item') { await this.tryAdd(act.id, run); if (!this.alive(run)) return; continue; }
      const go = await this.basketPanel(); if (!this.alive(run)) return;
      if (go !== 'checkout') continue;
      if (this.needs.some(id => !this.basket.includes(id))) { this.say(S.missing); this.progress(); continue; }
      await this.till(run);
      return;
    }
  }

  // Coin jar card, aisle sign + arrows, basket button.
  buildStoreUi() {
    this.own(nine(this, 282, 6, 'card_info', 112, 32, 6).setDepth(100));
    this.jar = this.own(this.add.sprite(290, 8, 'coin_jar', 5).setOrigin(0).setScale(2).setDepth(101));
    this.coinText = this.own(text(this, 324, 12, String(LEVEL2.shop.budget), 16).setDepth(101));
    this.signText = this.own(text(this, 408, 110, '', 16).setOrigin(0.5, 0).setDepth(65));
    this.arrows = [['arrow_left', 266, -1], ['arrow_right', 550, 1]].map(([key, x, dir]) => {
      const a = this.own(touchable(art(this, x, 106, key).setDepth(65), { pad: 8 }));
      a.on('pointerup', () => { sfx.play('click'); this.go(dir); });
      return a;
    });
    this.basketBtn = this.own(touchable(this.add.sprite(578, 288, 'basket', 0).setOrigin(0).setScale(2).setDepth(62), { pad: 4 }));
    this.basketBtn.on('pointerup', () => { sfx.play('click'); this.onAct?.({ type: 'basket' }); });
    this.basketTag = this.own(nine(this, 594, 262, 'card_info', 28, 24, 6).setDepth(62));           // the count sits on a little tag above the basket
    this.basketText = this.own(text(this, 608, 266, '0', 14).setOrigin(0.5, 0).setDepth(63));
  }

  updateCoins() {
    const S = LEVEL2.shop;
    this.coinText.setText(String(this.coins));
    this.jar.setFrame(Math.min(5, Math.ceil(this.coins / S.budget * 5)));
    this.basketText.setText(String(this.basket.length));
    this.basketBtn.setFrame(this.basket.length ? 1 : 0);
  }

  // Canvas position of an item's centre on the current aisle (the shelf layout in tools/sprites.py: STORE, STORE_AISLES).
  slots(ids) { return ids.length === 3 ? [146, 204, 262] : [175, 233]; }
  itemPos(id) {
    const rows = LEVEL2.shop.aisles[this.aisle].rows;
    for (let r = 0; r < rows.length; r++) {
      const k = rows[r].indexOf(id);
      if (k >= 0) return { x: W(this.slots(rows[r])[k]), y: W([112, 156][r]) - 22 };
    }
    return { x: 320, y: 200 };
  }

  go(dir) {
    if (this.moving) return;
    const n = LEVEL2.shop.aisles.length;
    this.aisle = (this.aisle + dir + n) % n;
    this.talk.hide();
    this.showAisle(this.aisle, dir);
    this.progress();
  }

  // The shelves of one aisle: item sprites (hidden once in the basket) with a price on each shelf edge.
  showAisle(i, dir = 0) {
    const S = LEVEL2.shop, A = S.aisles[i];
    const layer = this.own(this.add.container(0, 0).setDepth(60));
    this.signText.setText(A.name);
    A.rows.forEach((ids, r) => {
      const xs = this.slots(ids), bt = [112, 156][r];
      ids.forEach((id, k) => {
        if (!this.basket.includes(id)) {
          const img = touchable(art(this, W(xs[k]), W(bt + 1), `shop_${id}`, 0.5, 1), { pad: 6 });
          img.on('pointerup', () => { sfx.play('click'); this.onAct?.({ type: 'item', id }); });
          layer.add(img);
        }
        layer.add([art(this, W(xs[k] - 11), W(bt + 4), 'coin_small'), text(this, W(xs[k] - 1), W(bt + 4), String(S.items[id].price), 12)]);
      });
    });
    const old = this.layer;
    this.layer = layer;
    if (!old) return;
    if (!dir) { old.destroy(); return; }
    this.moving = true;                                 // slide the old shelf out and the new one in
    layer.x = dir * 400;
    this.tweens.add({ targets: old, x: -dir * 400, duration: 220, onComplete: () => old.destroy() });
    this.tweens.add({ targets: layer, x: 0, duration: 220, onComplete: () => { this.moving = false; } });
  }

  // An item flies from a to b (canvas centre points) and resolves when it lands.
  flyItem(id, a, b, ms = 350) {
    const s = this.own(art(this, a.x, a.y, `shop_${id}`, 0.5, 0.5).setDepth(200));
    return new Promise(r => this.tweens.add({ targets: s, x: b.x, y: b.y, duration: ms, ease: 'Sine.easeInOut', onComplete: () => { s.destroy(); r(); } }));
  }

  // The card that opens when an item is tapped: name, price and the coins left afterwards. Resolves true for "Add".
  itemModal(id) {
    const it = LEVEL2.shop.items[id], after = this.coins - it.price;
    this.meter.pause();
    return new Promise(res => {
      const c = this.own(this.add.container(0, 0).setDepth(280));
      const done = v => { c.destroy(); this.meter.resume(); res(v); };
      c.add(this.add.rectangle(0, 0, 640, 360, 0x3E2A24, 0.4).setOrigin(0).setInteractive());
      c.add(nine(this, 200, 100, 'card_info', 240, 164, 6));
      c.add(text(this, 320, 112, it.name, 18, { bold: true }).setOrigin(0.5, 0));
      c.add(art(this, 216, 142, `shop_${id}`));
      c.add(text(this, 272, 144, `Costs ${it.price} coins`, 14));
      c.add(text(this, 272, 164, after >= 0 ? `After: ${after} coins left` : 'Not enough coins', 14, { color: after >= 0 ? '#6FA07E' : '#C95A52' }));
      c.add(button(this, 214, 222, 108, 32, 'Add', () => done(true), { size: 16 }));
      c.add(button(this, 338, 222, 92, 32, 'Not now', () => done(false), { kind: 'cream', size: 14 }));
    });
  }

  async tryAdd(id, run) {
    const S = LEVEL2.shop, it = S.items[id];
    const from = this.itemPos(id), to = { x: 608, y: 300 };
    this.progress();
    if (!await this.itemModal(id)) return; if (!this.alive(run)) return;

    // a wrong pick (look-alike) or a want that would starve the needs: it goes to the basket, the card explains, and it goes back
    const owed = this.needs.filter(n => !this.basket.includes(n)).reduce((a, n) => a + S.items[n].price, 0);
    const starves = it.kind === 'want' && this.coins - it.price < owed;
    if (it.kind === 'wrong' || starves) {
      await this.flyItem(id, from, to); if (!this.alive(run)) return;
      this.gain(-5);
      const shown = await (starves ? this.card('bad', S.nudge.fact, S.nudge.title) : this.card('bad', it.fact, S.wrongTitle));
      if (!this.alive(run)) return;
      if (!shown) this.say(starves ? S.nudge.again : S.wrongAgain);                  // the lesson was already shown: a short line instead
      await this.flyItem(id, to, from);
      return;
    }
    if (it.price > this.coins) { this.say(S.tooMuch); return; }

    await this.flyItem(id, from, to); if (!this.alive(run)) return;
    this.coins -= it.price; this.basket.push(id);
    this.updateCoins(); this.showAisle(this.aisle); this.hud.bump();
    if (this.needs.includes(id)) {
      this.list.tick(id);
      if (!this.paid.has(id)) {                         // +10 once per need, so taking it out and back in can't be farmed
        this.paid.add(id);
        this.gain(10);
        if (it.fact) { await this.card('good', it.fact); if (!this.alive(run)) return; }
      }
    } else if (!this.sawWant) {
      this.sawWant = true;
      await this.card('info', S.wantFact, 'Looking good!'); if (!this.alive(run)) return;
    }
    if (!this.announced && this.needs.every(n => this.basket.includes(n))) { this.announced = true; this.say(S.allDone); }
  }

  removeFromBasket(id) {
    const it = LEVEL2.shop.items[id];
    this.coins += it.price;
    this.basket.splice(this.basket.indexOf(id), 1);
    if (this.needs.includes(id)) this.list.tick(id, false);
    this.updateCoins(); this.showAisle(this.aisle); this.progress();
    sfx.play('click');
  }

  // Everything bought so far; tap an item to put it back. Resolves 'checkout' or 'close'.
  basketPanel() {
    const S = LEVEL2.shop;
    this.meter.pause();
    return new Promise(res => {
      const c = this.own(this.add.container(0, 0).setDepth(280));
      const close = v => { c.destroy(); this.meter.resume(); res(v); };
      const draw = () => {
        c.removeAll(true);
        c.add(this.add.rectangle(0, 0, 640, 360, 0x3E2A24, 0.45).setOrigin(0).setInteractive());
        c.add(nine(this, 150, 60, 'card_info', 340, 280, 6));
        c.add(text(this, 170, 74, 'Your basket', 18, { bold: true }));
        if (!this.basket.length) c.add(text(this, 320, 150, 'Your basket is empty.', 14).setOrigin(0.5, 0));
        this.basket.forEach((id, n) => {
          const img = touchable(art(this, 174 + (n % 5) * 58, 100 + Math.floor(n / 5) * 56, `shop_${id}`), { pad: 4 });
          img.on('pointerup', () => { this.removeFromBasket(id); draw(); });
          c.add(img);
        });
        c.add(text(this, 170, 262, `Total: ${S.budget - this.coins} of ${S.budget} coins`, 14, { bold: true }));
        c.add(text(this, 170, 282, 'Tap an item to put it back.', 12, { color: '#8a6f66' }));
        c.add(button(this, 184, 304, 112, 32, 'Checkout', () => close('checkout'), { size: 16 }));
        c.add(button(this, 312, 304, 130, 32, 'Keep shopping', () => close('close'), { kind: 'cream', size: 14 }));
      };
      draw();
    });
  }

  // At the till each item is matched, one by one, to the reason it is in the basket (the vet's finding for the health items).
  async till(run) {
    const S = LEVEL2.shop;
    this.meter.pause();
    this.hintText = null;
    this.tilling = true;
    [this.layer, this.basketBtn, this.basketText, this.basketTag, this.signText, ...this.arrows].forEach(o => o.destroy());   // nothing underneath stays tappable
    this.own(art(this, 0, 0, 'store_till').setDepth(70));
    const skip = this.own(this.add.zone(0, 0, 640, 360).setOrigin(0).setDepth(90).setInteractive());           // tap to move on
    const order = [...this.needs, ...this.basket.filter(id => !this.needs.includes(id))];
    for (const id of order) {
      const it = S.items[id];
      const img = this.own(art(this, 400, 224, `shop_${id}`, 0.5, 1).setDepth(80));
      this.say(it.kind === 'need' ? it.why : S.tillWant);
      sfx.play('page');
      await Promise.race([this.wait(3000), new Promise(r => skip.once('pointerup', r))]); if (!this.alive(run)) return;
      await new Promise(r => this.tweens.add({ targets: img, y: 190, alpha: 0, duration: 300, onComplete: r })); if (!this.alive(run)) return;
    }
    this.say(S.tillDone);
    await this.wait(2800); if (!this.alive(run)) return;
    this.complete(run);
  }
}
