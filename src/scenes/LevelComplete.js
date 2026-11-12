import { GameScene } from '../view.js';
import { art, button, text } from '../ui.js';
import { LEVEL1, LEVEL2, LEVEL3 } from '../content.js';
import { sfx } from '../sfx.js';
import { load, save } from '../save.js';

// Album page after a level. data = { level, wrongs } (no wrong answers = Pawfect! stamp). Then the growth cutscene and the next
// level's story, or (after Level 3) the finale.
const ALBUM = {
  1: { ...LEVEL1.album, stage: 'puppy', next: s => s.scene.start('Cutscene', { key: 'growth1', next: { scene: 'Cutscene', data: { key: 'l2_intro', next: { scene: 'Level2', data: {} } } } }) },
  2: { ...LEVEL2.album, stage: 'young', next: s => s.scene.start('Cutscene', { key: 'growth2', next: { scene: 'Cutscene', data: { key: 'l3_intro', next: { scene: 'Level3', data: {} } } } }) },
  3: { ...LEVEL3.album, stage: 'adult', next: s => s.scene.start('Finale', {}) },
};

export class LevelComplete extends GameScene {
  constructor() { super('LevelComplete'); }

  create({ level = 1, wrongs = 0 }) {
    const { name, coat } = load();
    const A = ALBUM[level];
    save({ level: Math.max(level, load().level) });
    art(this, 0, 0, 'album_bg');
    art(this, 82, 62, 'polaroid');
    this.add.sprite(148, 166, `${A.stage}_${coat}_wag`).setOrigin(0.5, 1).setScale(2).play(`${A.stage}_${coat}_wag`);
    text(this, 159, 36, A.title, 24, { bold: true }).setOrigin(0.5, 0);
    text(this, 146, 186, name, 16).setOrigin(0.5, 0);

    text(this, 340, 40, 'You learned:', 18, { bold: true });
    A.skills.forEach((s, i) => {
      const y = 84 + i * 48;
      art(this, 340, y, `icon_${s.icon}`);
      text(this, 380, y + 8, s.label, 16);
      const check = art(this, 530, y, 'icon_check').setAlpha(0);
      this.tweens.add({ targets: check, alpha: 1, delay: 400 + i * 350, duration: 200, onStart: () => sfx.play('chime') });
    });

    if (wrongs === 0) {
      const stamp = art(this, 380, 196, 'stamp_pawfect').setAlpha(0);
      this.tweens.add({ targets: stamp, alpha: 1, y: { from: 186, to: 196 }, delay: 1300, duration: 180, onStart: () => sfx.play('win') });
    } else {
      text(this, 340, 202, `${wrongs} slip${wrongs > 1 ? 's' : ''} along the way, and that's how we learn!`, 13,
        { color: '#8a6f66', wrap: 230 });
    }
    button(this, 380, 280, 112, 32, 'Next', () => A.next(this), { size: 18 });
    sfx.play('page');
  }
}

// The end of the game: an album spread with a photo from each level (asset group 11).
export class Finale extends GameScene {
  constructor() { super('Finale'); }

  create() {
    const { name, coat } = load();
    art(this, 0, 0, 'finale_bg');
    text(this, 320, 16, "You're a Pawfect Parent!", 24, { bold: true }).setOrigin(0.5, 0);
    [['puppy', 30, 'Day 1'], ['young', 122, 'Check-up Day'], ['adult', 214, 'Park Day']].forEach(([stage, x, label], i) => {
      const s = this.add.sprite((x + 38) * 2, 114 * 2, `${stage}_${coat}_wag`).setOrigin(0.5, 1).setScale(2).play(`${stage}_${coat}_wag`).setAlpha(0);
      this.tweens.add({ targets: s, alpha: 1, delay: 300 + i * 500, duration: 300, onStart: () => sfx.play('chime') });
      text(this, (x + 38) * 2, 284, label, 15).setOrigin(0.5, 0);
    });
    text(this, 320, 52 * 2 - 40, `${name} grew from a nervous puppy into a happy, healthy dog.`, 14).setOrigin(0.5, 0);
    button(this, 176, 312, 136, 30, 'Level select', () => this.scene.start('LevelSelect', {}), { size: 15 });
    button(this, 328, 312, 136, 30, 'Back to title', () => this.scene.start('Title', {}), { kind: 'cream', size: 15 });
    sfx.play('win');
  }
}
