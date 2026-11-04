// Crisp rendering. The game world is 640x360, but the canvas is sized in REAL screen pixels, using S screen pixels per world
// pixel (a whole or half number, see measure()). The camera zooms the world up by S (pixel art stays exact), and text is rasterised at
// the same density (see text() in ui.js). Without this the browser stretches a 640x360 bitmap by a fractional amount
// (e.g. 3.75x on a 150% display), which smears text and makes pixels uneven.
export const WORLD_W = 640, WORLD_H = 360;
export const view = { S: 1, dpr: 1 };

// Whole or half steps: all art is drawn at 2x, so each art pixel is still a whole number of screen pixels (2S).
// Half steps matter on phones, where a whole step can leave the game much smaller than the screen allows.
// Capped at 4 (a 2560x1440 canvas): bigger canvases measured at ~24 fps on a laptop GPU, and the game is already large and
// sharp at 4; on a huge window it simply sits centred.
function measure() {
  const dpr = window.devicePixelRatio || 1;
  const fit = Math.min(innerWidth * dpr / WORLD_W, innerHeight * dpr / WORLD_H);
  const S = Math.min(4, Math.max(1, Math.floor(fit * 2 + 1e-6) / 2));
  return { S, dpr };
}

// True when the main pointer is a finger (phones and tablets): wording says "tap" instead of "click".
export const isTouch = !!window.matchMedia?.('(pointer: coarse)').matches;
Object.assign(view, measure());

export function fitCamera(scene) {
  scene.cameras?.main?.setZoom(view.S).centerOn(WORLD_W / 2, WORLD_H / 2);
}

// Every scene extends this, so its camera is fitted before it draws anything.
export class GameScene extends Phaser.Scene {
  init() { fitCamera(this); }
}

function retext(objs) {
  for (const o of objs) {
    if (o.type === 'Text') o.setResolution(view.S);
    if (o.list) retext(o.list);
  }
}

// On window resize or browser zoom: re-measure, then re-fit the canvas, the cameras and any existing text.
export function refit(game) {
  const before = view.S;
  Object.assign(view, measure());
  game.scale.setZoom(1 / view.dpr);                 // canvas CSS size = canvas pixels / dpr, so it maps 1:1 to the screen
  if (view.S === before) return;
  game.scale.resize(WORLD_W * view.S, WORLD_H * view.S);
  for (const sc of game.scene.scenes) { fitCamera(sc); retext(sc.children?.list ?? []); }
}
