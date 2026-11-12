import { GameScene } from '../view.js';
import { art, button, nine, text, touchable, COATS } from '../ui.js';
import { DOG_NAMES } from '../content.js';
import { sfx } from '../sfx.js';
import { load, save } from '../save.js';

const MAX_NAME = 10;
const KEY_ROWS = ['QWERTYUIOP', 'ASDFGHJKL', 'ZXCVBNM'];
const KEY_W = 50, KEY_H = 30, KEY_GAP = 4;              // canvas px; layout from keyboard_mockups() in tools/sprites.py (asset group 5)
const NAME_X = 124;                                     // where the typed name starts

export class DogSetup extends GameScene {
  constructor() { super('DogSetup'); }

  init(data) { super.init(); this.next = data?.next; }

  create() {
    const saved = load();
    this.coat = saved.coat;
    this.name = saved.name;
    this.input.once('pointerdown', () => sfx.unlock());

    art(this, 0, 0, 'title_bg');
    text(this, 320, 36, 'Meet your new puppy!', 20).setOrigin(0.5, 0);
    this.pup = this.add.sprite(320, 308, `puppy_${this.coat}_wag`).setOrigin(0.5, 1).setScale(2);
    this.pup.play(`puppy_${this.coat}_wag`);
    nine(this, 40, 62, 'card_info', 560, 192, 6);

    // coat swatches
    text(this, 64, 76, 'Coat', 16);
    this.ring = art(this, 0, 66, 'swatch_ring');
    COATS.forEach((c, i) => {
      const x = 132 + i * 44;
      const s = touchable(art(this, x, 70, `swatch_${c}`), { pad: 3 });
      s.on('pointerup', () => { sfx.play('click'); this.setCoat(c, x); });
      if (c === this.coat) this.ring.x = x - 4;
    });

    // name field (on-screen keys below, or the real keyboard) + random name + adopt
    text(this, 64, 118, 'Name', 16);
    nine(this, 112, 108, 'card_info', 160, 36, 6);
    this.nameText = text(this, NAME_X, 116, '', 18);
    this.caret = text(this, NAME_X, 114, '|', 18);
    this.time.addEvent({ delay: 450, loop: true, callback: () => this.caret.setVisible(!this.caret.visible) });
    button(this, 278, 108, 36, 36, '', () => { this.fresh = false; this.setName(Phaser.Utils.Array.GetRandom(DOG_NAMES)); }, { kind: 'cream' });
    art(this, 280, 110, 'icon_star');
    text(this, 320, 119, 'Random', 13, { color: '#8a6f66' });
    button(this, 440, 108, 120, 36, 'Adopt!', () => this.adopt(), { size: 18 });
    this.setName(this.name);
    this.fresh = true;                                  // the first key replaces the name that was filled in
    this.keyboard();

    // Native listener: Phaser's keyboard plugin delivered some keys twice in testing.
    const onKey = e => {
      if (e.repeat && e.key !== 'Backspace') return;
      if (e.key === 'Backspace') { e.preventDefault(); this.del(); }
      else if (e.key === 'Enter') this.adopt();
      else if (/^[a-zA-Z]$/.test(e.key)) this.type(e.key);
    };
    window.addEventListener('keydown', onKey);
    this.events.once('shutdown', () => window.removeEventListener('keydown', onKey));
  }

  // QWERTY rows with Del at the end of the last one. Keys are packed, so their tap zones get no extra slop.
  keyboard() {
    KEY_ROWS.forEach((row, r) => {
      const n = row.length;
      const total = n * KEY_W + (n - 1) * KEY_GAP + (r === 2 ? KEY_GAP + 2 * KEY_W + KEY_GAP : 0);
      const x0 = (640 - total) / 2, y = 152 + r * (KEY_H + KEY_GAP);
      [...row].forEach((ch, i) => button(this, x0 + i * (KEY_W + KEY_GAP), y, KEY_W, KEY_H, ch, () => this.type(ch), { kind: 'cream', slop: 0 }));
      if (r === 2) button(this, x0 + n * (KEY_W + KEY_GAP), y, 2 * KEY_W + KEY_GAP, KEY_H, 'Del', () => this.del(), { kind: 'cream', slop: 0, size: 15 });
    });
  }

  type(ch) {
    if (this.fresh) { this.fresh = false; this.name = ''; }
    if (this.name.length >= MAX_NAME) return;
    this.setName(this.name.length ? this.name + ch.toLowerCase() : ch.toUpperCase());   // "Biscuit", whatever the case of the key
  }

  del() { this.fresh = false; this.setName(this.name.slice(0, -1)); }

  setCoat(c, x) {
    this.coat = c;
    this.ring.x = x - 4;
    this.pup.play(`puppy_${c}_wag`);
    sfx.play('wag');
  }

  setName(n) {
    this.name = n;
    this.nameText.setText(n);
    this.caret.x = NAME_X + this.nameText.width;
  }

  adopt() {
    const name = this.name.trim() || Phaser.Utils.Array.GetRandom(DOG_NAMES);
    save({ name, coat: this.coat, adopted: true });
    sfx.play('bark');
    const next = this.next ?? { scene: 'Cutscene', data: { key: 'l1_home', next: { scene: 'Level1', data: {} } } };
    this.scene.start(next.scene, next.data);
  }
}
