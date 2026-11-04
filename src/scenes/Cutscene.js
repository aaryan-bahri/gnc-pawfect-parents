import { GameScene, isTouch } from '../view.js';
import { art, button, nine, text, W, WORLD, CURSOR } from '../ui.js';
import { CUTSCENES, fill } from '../content.js';
import { sfx } from '../sfx.js';
import { load } from '../save.js';

// Letterboxed panels with the parent's face + line in the bottom bar. data = { key, next } (next: scene key or 'End').
export class Cutscene extends GameScene {
  constructor() { super('Cutscene'); }

  init(data) { super.init(); this.key = data.key; this.next = data.next; this.i = 0; }

  create() {
    const { name, coat } = load();
    this.dogName = name; this.coat = coat;
    this.panels = CUTSCENES[this.key];
    this.input.once('pointerdown', () => sfx.unlock());

    this.stage = this.add.container(0, 0);
    this.add.rectangle(0, 0, 640, 30, 0xD7C4EC).setOrigin(0);
    this.add.rectangle(0, 292, 640, 68, 0xD7C4EC).setOrigin(0);
    nine(this, 8, 296, 'card_info', 60, 60, 6);
    // parent's face: crop the 48x48 bust to its 26x26 face, drawn at 2x like everything else
    this.face = this.add.sprite(12 - 22, 300 - 10, 'parent_talk').setOrigin(0).setScale(2).setCrop(11, 5, 26, 26);
    nine(this, 82, 302, 'bubble_speech', 540, 52, 5);
    this.line = text(this, 98, 310, '', 16, { wrap: 510 });
    this.more = text(this, 614, 336, `${isTouch ? 'tap' : 'click'} to continue`, 11, { color: '#8a6f66' }).setOrigin(1, 0);
    const skip = text(this, 640, 4, 'Skip', 13).setOrigin(1, 0).setPadding(14, 4, 14, 8).setInteractive({ cursor: CURSOR });
    skip.on('pointerup', () => this.finish());

    this.input.on('pointerup', (p, over) => { if (!over.includes(skip) && !this.ended) this.advance(); });
    this.show();
  }

  show() {
    const p = this.panels[this.i];
    this.stage.removeAll(true);
    if (p.panel === 'growth') {
      this.stage.add(art(this, 0, -60, 'living_room'));
      const floor = W(WORLD.groundY + 2) - 60;
      this.stage.add(this.add.sprite(250, floor, `puppy_${this.coat}_sit`).setOrigin(0.5, 1).setScale(2).play(`puppy_${this.coat}_sit`));
      this.stage.add(this.add.sprite(380, floor, `young_${this.coat}_wag`).setOrigin(0.5, 1).setScale(2).play(`young_${this.coat}_wag`));
      for (const [x, y] of [[196, 186], [300, 190], [430, 168]]) {
        const s = art(this, x, y, 'icon_star');
        this.tweens.add({ targets: s, y: y - 6, duration: 600, yoyo: true, repeat: -1, delay: x });
        this.stage.add(s);
      }
      sfx.play('win');
    } else {
      this.stage.add(art(this, 0, 0, `panel_${p.panel}_${this.coat}`));
    }
    this.stage.setAlpha(0);
    this.tweens.add({ targets: this.stage, alpha: 1, duration: 250 });
    this.line.setText(fill(p.text, this.dogName));
    this.face.play('parent_talk');
    this.time.delayedCall(Math.min(2400, 300 + p.text.length * 30), () => this.face.stop().setFrame(0));
    sfx.play('page');
  }

  advance() {
    if (this.i < this.panels.length - 1) { this.i++; this.show(); }
    else this.finish();
  }

  finish() {
    if (this.ended) return;
    this.ended = true;
    if (this.next !== 'End') { this.scene.start(this.next); return; }
    // end of the prototype
    this.add.rectangle(0, 0, 640, 360, 0x3E2A24, 0.45).setOrigin(0).setInteractive();
    nine(this, 150, 96, 'card_good', 340, 168, 6);
    art(this, 166, 112, 'icon_star');
    text(this, 206, 118, 'Thanks for playing!', 18, { bold: true, color: '#6FA07E' });
    text(this, 166, 156, `${this.dogName} finished Day 1. Levels 2 and 3 (the vet and pet store, then the park) come next.`,
      14, { wrap: 308 });
    button(this, 240, 218, 160, 30, 'Back to title', () => this.scene.start('Title'), { size: 15 });
  }
}
