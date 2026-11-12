// Level select (asset group 8): a cork board with a pinned card per level. Every level is open.
import { GameScene } from '../view.js';
import { art, button, glow, nine, text, CURSOR } from '../ui.js';
import { LEVELS } from '../content.js';
import { sfx } from '../sfx.js';
import { load } from '../save.js';

// Where a level starts: its intro cutscene (Level 1's story goes through naming the puppy). Levels 2 and 3 ask for a dog first if
// none was adopted yet.
export function startLevel(scene, n) {
  const L = LEVELS[n - 1];
  const next = n === 1
    ? { scene: 'DogSetup', data: { next: { scene: 'Cutscene', data: { key: 'l1_home', next: { scene: 'Level1', data: {} } } } } }
    : { scene: `Level${n}`, data: {} };
  const intro = { scene: 'Cutscene', data: { key: L.intro, next } };
  if (n > 1 && !load().adopted) scene.scene.start('DogSetup', { next: intro });
  else scene.scene.start(intro.scene, intro.data);
}

export class LevelSelect extends GameScene {
  constructor() { super('LevelSelect'); }

  create() {
    const { coat } = load();
    this.input.once('pointerdown', () => sfx.unlock());
    art(this, 0, 0, 'select_bg');
    text(this, 320, 13, 'Choose a level', 22).setOrigin(0.5, 0);
    button(this, 12, 10, 80, 30, 'Back', () => this.scene.start('Title', {}), { kind: 'cream', size: 15 });
    button(this, 488, 10, 140, 30, 'Change dog', () => this.scene.start('DogSetup', { next: { scene: 'LevelSelect', data: {} } }), { kind: 'cream', size: 15 });
    LEVELS.forEach((L, i) => {
      const x = 40 + i * 192, y = 72;
      nine(this, x, y, 'level_card', 176, 200, 6);
      art(this, x + 8, y + 8, `${L.thumb}_${coat}`);
      art(this, x + 80, y - 6, 'pin');
      text(this, x + 88, y + 128, `Level ${L.n}`, 18).setOrigin(0.5, 0);
      text(this, x + 88, y + 150, L.title, 15).setOrigin(0.5, 0);
      text(this, x + 88, y + 174, L.sub, 12, { color: '#8a6f66' }).setOrigin(0.5, 0);
      const zone = this.add.zone(x, y, 176, 200).setOrigin(0).setInteractive({ cursor: CURSOR });
      glow(this, zone);
      zone.on('pointerup', () => { sfx.play('click'); startLevel(this, L.n); });
    });
  }
}
