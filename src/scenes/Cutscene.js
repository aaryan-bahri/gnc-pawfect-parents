import { GameScene, isTouch } from '../view.js';
import { art, nine, text, W, WORLD, CURSOR } from '../ui.js';
import { CUTSCENES, fill } from '../content.js';
import { sfx } from '../sfx.js';
import { load } from '../save.js';

// Letterboxed story beats (CUTSCENES in content.js): a panel with the speaker's face (parent, vet, or none for narration) and the
// line in the bottom bar, a full-screen time card ("Later that afternoon"), or the growth panel.
// data = { key, next } (next: a scene key or { scene, data }).
export class Cutscene extends GameScene {
  constructor() { super('Cutscene'); }

  // A cutscene that hands over to another cutscene is this same scene restarting, so every per-run flag is reset here.
  init(data) { super.init(); this.key = data.key; this.next = data.next; this.i = 0; this.ended = false; }

  create() {
    const { name, coat } = load();
    this.dogName = name; this.coat = coat;
    this.panels = CUTSCENES[this.key];
    this.input.once('pointerdown', () => sfx.unlock());

    this.stage = this.add.container(0, 0);
    this.bars = this.add.container(0, 0, [this.add.rectangle(0, 0, 640, 30, 0xD7C4EC).setOrigin(0), this.add.rectangle(0, 292, 640, 68, 0xD7C4EC).setOrigin(0)]);
    this.faceBox = nine(this, 8, 296, 'card_info', 60, 60, 6);
    // the speaker's face: crop the 48x48 bust to its 26x26 face, drawn at 2x like everything else
    this.face = this.add.sprite(12 - 22, 300 - 10, 'parent_talk').setOrigin(0).setScale(2).setCrop(11, 5, 26, 26);
    this.bubble = nine(this, 82, 302, 'bubble_speech', 540, 52, 5);
    this.line = text(this, 98, 310, '', 16, { wrap: 510 });
    this.bars.add([this.faceBox, this.face, this.bubble, this.line]);
    this.more = text(this, 614, 336, `${isTouch ? 'tap' : 'click'} to continue`, 11, { color: '#8a6f66' }).setOrigin(1, 0);
    const skip = text(this, 640, 4, 'Skip', 13).setOrigin(1, 0).setPadding(14, 4, 14, 8).setInteractive({ cursor: CURSOR }).setDepth(10);
    skip.on('pointerup', () => this.finish());

    this.input.on('pointerup', (p, over) => { if (!over.includes(skip) && !this.ended && this.time.now - this.shownAt > 250) this.advance(); });
    this.show();
  }

  show() {
    const p = this.panels[this.i];
    this.stage.removeAll(true);
    this.shownAt = this.time.now;
    this.time.removeAllEvents();
    if (p.card) {                                         // a jump in time
      this.bars.setVisible(false);
      this.stage.add([art(this, 0, 0, 'timecard_bg'), art(this, 288, 82, `time_${p.icon}`),
        text(this, 320, 166, p.card, 26).setOrigin(0.5, 0)]);
      this.more.setColor('#5A3E36');
    } else {
      this.bars.setVisible(true);
      this.more.setColor('#8a6f66');
      if (p.panel === 'growth') this.growth(p);
      else this.stage.add(art(this, 0, 0, `panel_${p.panel}_${this.coat}`));
      const who = p.face === undefined ? 'parent' : p.face;   // whose face is in the text bar (null: narration, no face)
      this.faceBox.setVisible(!!who);
      this.face.setVisible(!!who);
      const x0 = who ? 82 : 20;
      this.bubble.setPosition(x0, 302).setSize((622 - x0) / 2, 26);
      this.line.setPosition(x0 + 16, 310).setWordWrapWidth(600 - x0 - 12).setText(fill(p.text, this.dogName));
      if (who) {
        this.face.play(`${who}_talk`);
        this.time.delayedCall(Math.min(2400, 300 + p.text.length * 30), () => this.face.stop().setFrame(0));
      }
    }
    this.stage.setAlpha(0);
    this.tweens.add({ targets: this.stage, alpha: 1, duration: 250 });
    sfx.play('page');
  }

  growth(p) {
    this.stage.add(art(this, 0, -60, 'living_room'));
    const floor = W(WORLD.groundY + 2) - 60;
    const [before, after] = p.stage === 'adult' ? ['young', 'adult'] : ['puppy', 'young'];     // who grew into whom
    this.stage.add(this.add.sprite(250, floor, `${before}_${this.coat}_sit`).setOrigin(0.5, 1).setScale(2).play(`${before}_${this.coat}_sit`));
    this.stage.add(this.add.sprite(380, floor, `${after}_${this.coat}_wag`).setOrigin(0.5, 1).setScale(2).play(`${after}_${this.coat}_wag`));
    for (const [x, y] of [[196, 186], [300, 190], [430, 168]]) {
      const s = art(this, x, y, 'icon_star');
      this.tweens.add({ targets: s, y: y - 6, duration: 600, yoyo: true, repeat: -1, delay: x });
      this.stage.add(s);
    }
    sfx.play('win');
  }

  advance() {
    if (this.i < this.panels.length - 1) { this.i++; this.show(); }
    else this.finish();
  }

  finish() {
    if (this.ended) return;
    this.ended = true;
    // {} on purpose: with no data Phaser re-sends the previous run's data
    if (typeof this.next === 'string') this.scene.start(this.next, {});
    else this.scene.start(this.next.scene, this.next.data ?? {});
  }
}
