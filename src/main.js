import { Boot, Preload } from './scenes/Preload.js';
import { Title } from './scenes/Title.js';
import { DogSetup } from './scenes/DogSetup.js';
import { Cutscene } from './scenes/Cutscene.js';
import { Level1 } from './scenes/Level1.js';
import { LevelComplete } from './scenes/LevelComplete.js';
import { view, refit, WORLD_W, WORLD_H } from './view.js';
import { sfx } from './sfx.js';

// Text must be measured with the real font, so wait for Pixelify Sans before Phaser starts.
await Promise.all([
  document.fonts.load('16px "Pixelify Sans"'),
  document.fonts.load('600 16px "Pixelify Sans"'),
]).catch(() => {});

// The canvas is WORLD x S real pixels; zoom 1/dpr makes it fill exactly that many screen pixels (see view.js).
const game = new Phaser.Game({
  type: Phaser.AUTO,
  parent: 'game',
  width: WORLD_W * view.S,
  height: WORLD_H * view.S,
  pixelArt: true,
  backgroundColor: '#FFF4E0',
  scale: { mode: Phaser.Scale.NONE, zoom: 1 / view.dpr },
  scene: [Boot, Preload, Title, DogSetup, Cutscene, Level1, LevelComplete],
});
addEventListener('resize', () => refit(game));
addEventListener('orientationchange', () => setTimeout(() => refit(game), 250));

// Phones only start audio from a real tap, and a long-press must not open a context menu.
for (const e of ['pointerup', 'touchend', 'click', 'keydown']) addEventListener(e, () => sfx.unlock(), { passive: true });
addEventListener('contextmenu', e => e.preventDefault());
window.game = game;   // handy for debugging from the console
