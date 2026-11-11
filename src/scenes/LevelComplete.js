import { GameScene } from '../view.js';
import { art, button, text } from '../ui.js';
import { LEVEL1, LEVEL2 } from '../content.js';
import { sfx } from '../sfx.js';
import { load, save } from '../save.js';

// Album page after a level. data = { level, wrongs } (no wrong answers = Pawfect! stamp). Then the growth cutscene.
const ALBUM = { 1: { ...LEVEL1.album, stage: 'puppy', next: { key: 'growth1', next: { scene: 'Cutscene', data: { key: 'level2', next: 'Level2' } } } },
                2: { ...LEVEL2.album, stage: 'young', next: { key: 'growth2', next: 'End' } } };
export class LevelComplete extends GameScene {
  constructor() { super('LevelComplete'); }

  create({ level = 1, wrongs = 0 }) {
    const { name, coat } = load();
    const A = ALBUM[level];
    save({ level });
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
    button(this, 380, 280, 112, 32, 'Next', () => this.scene.start('Cutscene', A.next), { size: 18 });
    sfx.play('page');
  }
}
