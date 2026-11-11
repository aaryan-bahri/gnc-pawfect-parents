// Shared UI built from the approved UI kit (asset group 3). All art is drawn at 2x; text at 1x.
import { CARD, cardLayout, bodyWrapWidth } from './layout.js';
import { sfx } from './sfx.js';
import { view } from './view.js';

export const COATS = ['cream', 'caramel', 'chocolate'];
export const PUPPY_ANIMS = ['idle', 'walk', 'sit', 'wag', 'sniff', 'circle', 'pee', 'eat', 'refuse', 'sad', 'cower'];
// Room landmarks in world pixels (320x180). Keep in sync with tools/sprites.py.
export const WORLD = { floorY: 140, groundY: 165, spots: { door: 36, middle: 170, bowl: 246 }, counterSlots: [110, 210], counterTopY: 134,
  counter: { x: 223, y: 20, w: 93, h: 117 } };
// The vet clinic in world pixels. Keep in sync with CLINIC in tools/sprites.py.
export const CLINIC = { tableTop: 124, dogX: 146, dogFeet: 122, vetX: 252, vetFeet: 168 };
export const W = n => n * 2;                      // world pixels -> canvas pixels
export const INK = '#5A3E36';
export const CURSOR = 'url(assets/ui/cursor_paw.png) 14 6, pointer';
const FONT = '"Pixelify Sans", monospace';

export const wait = (scene, ms) => new Promise(r => scene.time.delayedCall(ms, r));

export function text(scene, x, y, str, size = 16, { color = INK, wrap, align = 'left', bold = false } = {}) {
  return scene.add.text(x, y, str, { fontFamily: FONT, fontSize: `${size}px`, fontStyle: bold ? '600' : 'normal', color, align,
    wordWrap: wrap ? { width: wrap } : undefined, lineSpacing: 2, resolution: view.S });
}

// Nine-slice from a UI-kit sprite. x, y, w, h are canvas pixels (even numbers); the art is scaled 2x.
export function nine(scene, x, y, key, w, h, corner, frame) {
  return scene.add.nineslice(x, y, key, frame, w / 2, h / 2, corner, corner, corner, corner).setOrigin(0).setScale(2);
}

export function art(scene, x, y, key, originX = 0, originY = 0) {
  return scene.add.image(x, y, key).setOrigin(originX, originY).setScale(2);
}

// Makes an image interactive with an invisible hit area `pad` texture-pixels larger on every side (art is drawn at 2x),
// so fingers can grab small things like the treat and the pee pad.
export function touchable(obj, { pad = 6, draggable = false } = {}) {
  obj.setInteractive({ hitArea: new Phaser.Geom.Rectangle(-pad, -pad, obj.width + 2 * pad, obj.height + 2 * pad),
    hitAreaCallback: Phaser.Geom.Rectangle.Contains, draggable, cursor: CURSOR });
  return obj;
}

// Button: container of normal/hover/pressed nine-slices + label, clickable through an inner zone (a few px bigger than
// the art, for fingers; `slop: 0` for packed grids like the keyboard).
export function button(scene, x, y, w, h, label, onClick, { kind = 'mint', icon, size = 16, slop = 4 } = {}) {
  const key = `button_${kind}`;
  const states = [0, 1, 2].map(f => nine(scene, 0, 0, key, w, h, 5, f).setVisible(f === 0));
  const c = scene.add.container(x, y, states);
  const hasIcon = !!icon;
  if (hasIcon) c.add(art(scene, 10, (h - 32) / 2 - 1, `icon_${icon}`));
  const t = text(scene, hasIcon ? 50 : w / 2, h / 2 - 2, label, size, { align: 'center' }).setOrigin(hasIcon ? 0 : 0.5, 0.5);
  c.add(t);
  const show = i => states.forEach((s, j) => s.setVisible(i === j));
  const zone = scene.add.zone(-slop, -slop, w + 2 * slop, h + 2 * slop).setOrigin(0).setInteractive({ cursor: CURSOR });
  zone.on('pointerover', () => show(1)).on('pointerout', () => show(0)).on('pointerdown', () => { show(2); t.y = h / 2; })
    .on('pointerup', () => { show(1); t.y = h / 2 - 2; sfx.play('click'); onClick(); });
  c.add(zone);
  return c;
}

// Full-screen click blocker (and optional dim) under modals.
function blocker(scene, alpha) {
  return scene.add.rectangle(0, 0, 640, 360, 0x3E2A24, alpha).setOrigin(0).setInteractive();
}

// "Did you know?" card, sized from the measured text (src/layout.js). Resolves when OK is pressed.
export function factCard(scene, kind, body, title = 'Did you know?') {
  return new Promise(resolve => {
    const c = scene.add.container(0, 0).setDepth(300);
    c.add(blocker(scene, 0.35));
    const bodyT = text(scene, 0, 0, body, 14, { wrap: bodyWrapWidth() });
    const L = cardLayout(bodyT.height);
    const x = (640 - CARD.width) / 2, y = Math.round((360 - L.h) / 4) * 2;
    const titleCol = { good: '#6FA07E', bad: '#C95A52', info: INK }[kind];
    c.add(nine(scene, x, y, `card_${kind}`, CARD.width, L.h, 6));
    c.add(art(scene, x + CARD.pad, y + L.titleY, kind === 'bad' ? 'icon_cross' : kind === 'good' ? 'icon_check' : 'icon_bulb'));
    c.add(text(scene, x + CARD.pad + 40, y + L.titleY + 6, title, 18, { color: titleCol, bold: true }));
    c.add(bodyT.setPosition(x + CARD.pad, y + L.bodyY));
    c.add(button(scene, x + (CARD.width - CARD.buttonW) / 2, y + L.buttonY, CARD.buttonW, CARD.buttonH, 'OK!',
      () => { c.destroy(); resolve(); }, { size: 15 }));
    c.setAlpha(0);
    scene.tweens.add({ targets: c, alpha: 1, duration: 150 });
  });
}

// Two or more choice buttons (icon + label) in the middle of the screen. Resolves with the chosen option.
export function choice(scene, options) {
  return new Promise(resolve => {
    const c = scene.add.container(0, 0).setDepth(300);
    c.add(blocker(scene, 0.25));
    const bw = 300, bh = 48, gap = 14;
    const top = 180 - (options.length * bh + (options.length - 1) * gap) / 2 + 20;
    options.forEach((o, i) => c.add(button(scene, 170, top + i * (bh + gap), bw, bh, o.label,
      () => { c.destroy(); resolve(o); }, { kind: 'cream', icon: o.icon })));
  });
}

// Parent portrait (top-left) + speech bubble that grows to fit the line.
// `who` picks the portrait: 'parent' or 'vet' (sprites <who>_idle / <who>_talk).
export class ParentDialog {
  constructor(scene, who = 'parent') {
    this.scene = scene;
    this.who = who;
    this.c = scene.add.container(0, 0).setDepth(150).setVisible(false);
    this.c.add(nine(scene, 2, 40, 'card_info', 104, 100, 6));
    this.face = scene.add.sprite(6, 42, `${who}_idle`).setOrigin(0).setScale(2).play(`${who}_idle`);
    this.bubble = nine(scene, 116, 58, 'bubble_speech', 420, 60, 5);
    this.tail = art(scene, 100, 78, 'bubble_speech_tail');
    this.t = text(scene, 134, 70, '', 16, { wrap: 390 });
    this.c.add([this.face, this.bubble, this.tail, this.t]);
  }
  // `readMs`: hide the bubble again after that long (for tips shown over something the player needs to see).
  say(line, readMs = 0) {
    this.hideTimer?.remove();
    this.t.setText(line);
    const h = Math.max(60, Math.ceil((this.t.height + 24) / 2) * 2);
    this.bubble.setSize(210, h / 2);
    this.c.setVisible(true);
    this.face.play(`${this.who}_talk`);
    this.talkTimer?.remove();
    this.talkTimer = this.scene.time.delayedCall(Math.min(2400, 300 + line.length * 30), () => this.face.play(`${this.who}_idle`));
    if (readMs) this.hideTimer = this.scene.time.delayedCall(readMs, () => this.hide());
  }
  setWho(who) { if (who !== this.who) { this.who = who; this.face.play(`${who}_idle`); } }
  hide() { this.hideTimer?.remove(); this.c.setVisible(false); }
  show() { this.c.setVisible(true); }
  setDepth(d) { this.c.setDepth(d); }
}

// Dog thought bubble that follows a sprite and holds one icon.
export class Thought {
  constructor(scene, target) {
    this.target = target;
    this.c = scene.add.container(0, 0).setDepth(110).setVisible(false);
    this.c.add([nine(scene, 0, 0, 'bubble_thought', 52, 48, 6), art(scene, 10, 8, 'icon_bowl'), art(scene, 14, 46, 'bubble_thought_tail')]);
    this.icon = this.c.list[1];
  }
  show(icon) { this.icon.setTexture(`icon_${icon}`); this.c.setVisible(true); }
  hide() { this.c.setVisible(false); }
  update() {
    const t = this.target, dir = t.flipX ? -1 : 1;
    this.c.setPosition(Math.round(t.x + dir * 4 - 20), Math.round(t.y - 64 - 74));
  }
}

// Bobbing yellow arrow pointing down at (x, y). Level 1 only.
export function cue(scene, x, y) {
  return scene.add.sprite(x, y, 'cue_arrow').setOrigin(0.5, 1).setScale(2).setDepth(120).play('cue_arrow');
}

// HUD: meter (heart, frame, fill), dog name, task card, pause button.
export class Hud {
  constructor(scene, meter, { name, onPause }) {
    this.scene = scene; this.meter = meter; this.shown = meter.value;
    const d = 100;
    this.heart = art(scene, 21, 20, 'meter_heart', 0.5, 0.5).setDepth(d);
    art(scene, 36, 10, 'meter_frame').setDepth(d);
    this.fill = art(scene, 38, 12, 'meter_fill_green').setDepth(d);
    text(scene, 172, 9, name, 16).setDepth(d);
    nine(scene, 402, 6, 'card_info', 192, 32, 6).setDepth(d);
    this.taskIcon = art(scene, 410, 6, 'icon_bowl').setDepth(d);
    this.taskText = text(scene, 446, 13, '', 14).setDepth(d);
    button(scene, 604, 6, 32, 32, '', onPause, { kind: 'cream' }).setDepth(d);
    art(scene, 604, 6, 'icon_pause').setDepth(d + 1);
  }
  setTask(icon, label) { this.taskIcon.setTexture(`icon_${icon}`); this.taskText.setText(label); }
  update(dt) {
    this.shown += (this.meter.value - this.shown) * Math.min(1, dt / 120);
    this.fill.setTexture(`meter_fill_${this.meter.state}`);
    this.fill.setCrop(0, 0, Math.round(62 * this.shown / 100), 6);
    // red = pulse by fading (scaling would break the one-pixel-size rule)
    this.heart.setAlpha(this.meter.state === 'red' ? 0.55 + 0.45 * Math.abs(Math.sin(this.scene.time.now / 220)) : 1);
  }
  bump() { this.scene.tweens.add({ targets: this.heart, y: 14, duration: 110, yoyo: true }); }
}

// The shopping list as a sheet of paper (asset group 6): a top, one ruled line per item written, and a bottom. It grows as
// items are added, with one blank line ready. `labels` maps item id -> text. Lives at canvas (x, y).
export class ShoppingList {
  constructor(scene, x, y, capacity, labels) {
    this.scene = scene; this.labels = labels; this.cap = capacity; this.entries = {}; this.n = 0;
    this.c = scene.add.container(x, y).setDepth(120);
    this.c.add([art(scene, 0, 0, 'paper_top'), text(scene, 28, 14, 'Shopping list', 14)]);
    this.bottom = art(scene, 0, 0, 'paper_bottom');
    this.c.add(this.bottom);
    this.rows = 0;
    this.openRow();
  }
  rowY(i) { return 36 + i * 20; }
  openRow() {
    if (this.rows >= this.cap) return;
    this.c.add(art(this.scene, 0, this.rowY(this.rows), 'paper_row'));
    this.rows++;
    this.bottom.y = this.rowY(this.rows);
  }
  // Canvas position of the next line to be written (where a flying icon should land).
  nextPos() { return { x: this.c.x + 40, y: this.c.y + this.rowY(this.n) + 10 }; }
  add(id) {
    const y = this.rowY(this.n++);
    const box = art(this.scene, 26, y + 3, 'list_box');
    const label = text(this.scene, 46, y + 3, this.labels[id], 13);
    this.c.add([box, label]);
    this.entries[id] = { box };
    this.scene.tweens.add({ targets: [box, label], alpha: { from: 0, to: 1 }, duration: 250 });
    this.openRow();
  }
  tick(id, on = true) { this.entries[id].box.setTexture(on ? 'list_tick' : 'list_box'); }
  destroy() { this.c.destroy(); }
}
