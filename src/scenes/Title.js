import { GameScene } from '../view.js';
import { art, button } from '../ui.js';
import { sfx } from '../sfx.js';
import { load } from '../save.js';

export class Title extends GameScene {
  constructor() { super('Title'); }

  create() {
    const { coat } = load();
    this.input.once('pointerdown', () => sfx.unlock());
    art(this, 0, 0, 'title_bg');
    art(this, 216, 52, 'logo');
    this.add.sprite(320, 308, `puppy_${coat}_wag`).setOrigin(0.5, 1).setScale(2).play(`puppy_${coat}_wag`);
    button(this, 264, 178, 112, 32, 'Play', () => this.scene.start('LevelSelect', {}), { size: 18 });
    button(this, 604, 8, 32, 32, '', () => icon.setTexture(sfx.toggle() ? 'icon_sound_off' : 'icon_sound_on'), { kind: 'cream' });
    const icon = art(this, 604, 8, sfx.muted ? 'icon_sound_off' : 'icon_sound_on');
  }
}
