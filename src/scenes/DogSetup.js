import { GameScene } from '../view.js';
import { art, button, nine, text, touchable, COATS } from '../ui.js';
import { DOG_NAMES } from '../content.js';
import { sfx } from '../sfx.js';
import { load, save } from '../save.js';

const MAX_NAME = 10;

export class DogSetup extends GameScene {
  constructor() { super('DogSetup'); }

  create() {
    const saved = load();
    this.coat = saved.coat;
    this.name = saved.name;
    this.input.once('pointerdown', () => sfx.unlock());

    art(this, 0, 0, 'title_bg');
    text(this, 320, 48, 'Meet your new puppy!', 24, { bold: true }).setOrigin(0.5, 0);
    this.pup = this.add.sprite(320, 308, `puppy_${this.coat}_wag`).setOrigin(0.5, 1).setScale(2);
    this.pup.play(`puppy_${this.coat}_wag`);

    // coat swatches
    text(this, 196, 100, 'Coat', 16);
    this.ring = art(this, 0, 98, 'swatch_ring', 0.5, 0);
    COATS.forEach((c, i) => {
      const x = 274 + i * 46;
      const s = touchable(art(this, x, 102, `swatch_${c}`, 0.5, 0), { pad: 3 });
      s.on('pointerup', () => { sfx.play('click'); this.setCoat(c, x); });
      if (c === this.coat) this.ring.x = x;
    });

    // name field (type on the keyboard) + random name button
    text(this, 196, 152, 'Name', 16);
    nine(this, 252, 144, 'card_info', 160, 36, 6);
    this.nameText = text(this, 266, 152, '', 18);
    this.caret = text(this, 266, 150, '|', 18);
    this.time.addEvent({ delay: 450, loop: true, callback: () => this.caret.setVisible(!this.caret.visible) });
    button(this, 418, 144, 36, 36, '', () => this.setName(Phaser.Utils.Array.GetRandom(DOG_NAMES)), { kind: 'cream' });
    art(this, 420, 146, 'icon_star');
    text(this, 460, 154, 'Random', 13, { color: '#8a6f66' });
    this.setName(this.name);

    // Native listener: Phaser's keyboard plugin delivered some keys twice in testing.
    const onKey = e => {
      if (e.repeat && e.key !== 'Backspace') return;
      if (e.key === 'Backspace') { e.preventDefault(); this.setName(this.name.slice(0, -1)); }
      else if (e.key === 'Enter') this.adopt();
      else if (/^[a-zA-Z]$/.test(e.key) && this.name.length < MAX_NAME) {
        this.setName(this.name.length ? this.name + e.key : e.key.toUpperCase());
      }
    };
    window.addEventListener('keydown', onKey);
    this.events.once('shutdown', () => window.removeEventListener('keydown', onKey));

    button(this, 260, 196, 120, 36, 'Adopt!', () => this.adopt(), { size: 18 });
  }

  setCoat(c, x) {
    this.coat = c;
    this.ring.x = x;
    this.pup.play(`puppy_${c}_wag`);
    sfx.play('wag');
  }

  setName(n) {
    this.name = n;
    this.nameText.setText(n);
    this.caret.x = 266 + this.nameText.width;
  }

  adopt() {
    const name = this.name.trim() || Phaser.Utils.Array.GetRandom(DOG_NAMES);
    save({ name, coat: this.coat });
    sfx.play('bark');
    this.scene.start('Cutscene', { key: 'opening', next: 'Level1' });
  }
}
