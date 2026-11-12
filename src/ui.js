// Shared UI built from the approved UI kits (asset groups 3 and 8). All art is drawn at 2x; text at 1x.
import { CARD, DIALOG, cardLayout, bodyWrapWidth } from './layout.js';
import { sfx } from './sfx.js';
import { view } from './view.js';

export const COATS = ['cream', 'caramel', 'chocolate'];
export const PUPPY_ANIMS = ['idle', 'walk', 'sit', 'wag', 'sniff', 'circle', 'pee', 'eat', 'refuse', 'sad', 'cower'];
// Room landmarks in world pixels (320x180). Keep in sync with tools/sprites.py.
export const WORLD = { floorY: 140, groundY: 165, spots: { door: 36, middle: 170, bowl: 246 }, counterSlots: [110, 210], counterTopY: 134,
  counter: { x: 223, y: 20, w: 93, h: 117 } };
export const W = n => n * 2;                      // world pixels -> canvas pixels
export const INK = '#5A3E36';
export const BUTTER = 0xFFE08A;
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
// so fingers can grab small things like the treat and the pee pad. `exact` uses the art's own pixels instead.
export function touchable(obj, { pad = 6, draggable = false, exact = false } = {}) {
  if (exact) obj.setInteractive({ pixelPerfect: true, alphaTolerance: 1, draggable, cursor: CURSOR });
  else obj.setInteractive({ hitArea: new Phaser.Geom.Rectangle(-pad, -pad, obj.width + 2 * pad, obj.height + 2 * pad),
    hitAreaCallback: Phaser.Geom.Rectangle.Contains, draggable, cursor: CURSOR });
  return obj;
}

// Hover highlight (replaces the old rings): a one-art-pixel butter outline round whatever is under the pointer (or the finger,
// while pressed). Sprites get four butter-tinted copies of themselves, one art pixel out on each side; zones get a nine-slice frame.
// `target` lets a hit zone light up a different object. Returns { show, hide } so code can light things up too (drop targets).
const OFFSETS = [[-2, 0], [2, 0], [0, -2], [0, 2]];
export function glow(scene, obj, { target = obj, hover = true } = {}) {
  let parts = null;
  const sync = () => {
    if (!parts) return;
    if (!target.active) return hide();
    if (target.type === 'Zone') return;
    parts.forEach((p, i) => p.setPosition(target.x + OFFSETS[i][0], target.y + OFFSETS[i][1]).setFrame(target.frame.name)
      .setFlipX(target.flipX).setVisible(target.visible && target.alpha > 0.05));
  };
  const show = () => {
    if (parts || !target.active) return;
    if (target.type === 'Zone') {
      parts = [nine(scene, target.x - 2, target.y - 2, 'hover_frame', target.width + 4, target.height + 4, 2).setDepth(target.depth + 1)];
    } else {
      parts = OFFSETS.map(() => scene.add.image(0, 0, target.texture.key, target.frame.name).setOrigin(target.originX, target.originY)
        .setScale(target.scaleX, target.scaleY).setTintFill(BUTTER).setDepth(target.depth - 0.1));
      target.parentContainer?.addAt(parts, target.parentContainer.getIndex(target));
    }
    scene.events.on('postupdate', sync);
    sync();
  };
  const hide = () => {
    parts?.forEach(p => p.destroy());
    parts = null;
    scene.events.off('postupdate', sync);
  };
  if (hover) obj.on('pointerover', show).on('pointerout', hide).on('dragstart', show).on('dragend', hide);
  obj.once('destroy', hide);
  return { show, hide };
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
  c.label = t;
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

// Two or more choice buttons (icon + label), stacked above the dialogue box. Resolves with the chosen option.
// side: the question sits on a card top-left and the buttons top-right, so the bottom of the screen (the dog) stays in view.
export function choice(scene, options, { side = null } = {}) {
  return new Promise(resolve => {
    const c = scene.add.container(0, 0).setDepth(300);
    c.add(blocker(scene, side ? 0.12 : 0));
    const bw = side ? 330 : 340, bh = 44, gap = 10, x = side ? 302 : 150;
    const top = side ? 48 : DIALOG.y - 12 - options.length * (bh + gap) + gap;
    if (side) {
      const t = text(scene, 26, 62, side, 16, { wrap: 236 });
      c.add([nine(scene, 8, 48, 'card_info', 272, Math.ceil((t.height + 28) / 2) * 2, 6), t]);
    }
    options.forEach((o, i) => c.add(button(scene, x, top + i * (bh + gap), bw, bh, o.label,
      () => { c.destroy(); resolve(o); }, { kind: 'cream', icon: o.icon, size: 15 })));
  });
}

// The blocking dialogue box (asset group 8): the scene dims and nothing else can be tapped until OK is pressed.
// Speakers: parent, vet, sam (portrait sprites <who>_talk / <who>_idle).
const SPEAKERS = { parent: { name: 'Parent', anim: 'parent', plate: 'nameplate_parent' }, vet: { name: 'Vet', anim: 'vet', plate: 'nameplate_vet' },
  sam: { name: 'Sam', anim: 'sam_bust', plate: 'nameplate_sam' } };
export class Dialog {
  constructor(scene) {
    const D = DIALOG;
    this.scene = scene;
    this.c = scene.add.container(0, 0).setDepth(290).setVisible(false);
    this.dim = blocker(scene, 0.28);
    this.c.add([this.dim, nine(scene, D.x, D.y, 'dialog_panel', D.w, D.h, 7), art(scene, 22, 246, 'portrait_frame')]);
    this.face = scene.add.sprite(24, 248, 'parent_idle').setOrigin(0).setScale(2);
    this.plate = nine(scene, D.plateX, D.plateY, 'nameplate_parent', D.plateW, 24, 4);
    this.name = text(scene, D.plateX + D.plateW / 2, D.plateY + 4, '', 14).setOrigin(0.5, 0);
    this.t = text(scene, D.textX, D.textY, '', D.size, { wrap: D.wrap });
    this.c.add([this.face, this.plate, this.name, this.t]);
    this.open = false;
  }

  // Shows a line and resolves when the button is pressed. ok: the button label, or null for no button (close() hides it).
  say(who, line, { ok = 'OK' } = {}) {
    const s = SPEAKERS[who] ?? SPEAKERS.parent, D = DIALOG;
    this.btn?.destroy();
    this.btn = null;
    this.t.setText(line);
    this.name.setText(s.name);
    this.plate.setTexture(s.plate);
    this.face.play(`${s.anim}_talk`);
    this.talkTimer?.remove();
    this.talkTimer = this.scene.time.delayedCall(Math.min(2600, 300 + line.length * 30), () => this.face.play(`${s.anim}_idle`));
    this.c.setVisible(true);
    this.open = true;
    sfx.play('page');
    return new Promise(resolve => {
      this.resolve = resolve;
      if (ok === null) return;
      this.btn = button(this.scene, D.okX, D.okY, D.okW, D.okH, ok, () => this.close(), { size: ok.length > 6 ? 15 : 18 });
      this.c.add(this.btn);
    });
  }

  close() {
    if (!this.open) return;
    this.open = false;
    this.c.setVisible(false);
    this.btn?.destroy();
    this.btn = null;
    const r = this.resolve;
    this.resolve = null;
    r?.();
  }
}

// Dog thought bubble that follows a sprite and holds one icon. `lift` raises it for bigger dogs.
export class Thought {
  constructor(scene, target, lift = 0) {
    this.target = target;
    this.lift = lift;
    this.c = scene.add.container(0, 0).setDepth(110).setVisible(false);
    this.c.add([nine(scene, 0, 0, 'bubble_thought', 52, 48, 6), art(scene, 10, 8, 'icon_bowl'), art(scene, 14, 46, 'bubble_thought_tail')]);
    this.icon = this.c.list[1];
  }
  show(icon) { this.icon.setTexture(`icon_${icon}`); this.c.setVisible(true); }
  hide() { this.c.setVisible(false); }
  update() {
    const t = this.target, dir = t.flipX ? -1 : 1;
    this.c.setPosition(Math.round(t.x + dir * 4 - 20), Math.round(t.y - 64 - 74 - this.lift));
  }
}

// Bobbing yellow arrow pointing down at (x, y). Level 1 only.
export function cue(scene, x, y) {
  return scene.add.sprite(x, y, 'cue_arrow').setOrigin(0.5, 1).setScale(2).setDepth(120).play('cue_arrow');
}

// The ghost-hand demo (asset group 8): over a dimmed scene, a hand taps, drags, holds or rubs on a loop with a caption, until
// "Got it!". steps: { tap: [x, y] } | { drag: [[x1, y1], [x2, y2]], carry: textureKey, arc: px } | { hold: [x, y], ms } | { rub: [[x1, y1], [x2, y2]] }
const HAND_TIP = [7.5 / 18, 1.5 / 22];
export function demo(scene, { caption, steps }) {
  return new Promise(resolve => {
    const c = scene.add.container(0, 0).setDepth(295);
    let alive = true;
    c.add(blocker(scene, 0.45));
    c.add(nine(scene, 104, 52, 'card_info', 432, 44, 6));
    c.add(art(scene, 114, 58, 'icon_bulb'));
    c.add(text(scene, 152, 64, caption, 16, { wrap: 372 }).setOrigin(0, 0));
    const layer = scene.add.container(0, 0);
    c.add(layer);
    const hand = scene.add.sprite(320, 200, 'hand', 0).setOrigin(...HAND_TIP).setScale(2);
    c.add(hand);
    c.add(button(scene, 440, 296, 112, 32, 'Got it!', () => { alive = false; c.destroy(); resolve(); }, { size: 17 }));
    const sleep = ms => new Promise(r => scene.time.delayedCall(ms, r));
    const move = (x, y, ms) => new Promise(r => scene.tweens.add({ targets: hand, x, y, duration: ms, ease: 'Sine.easeInOut', onComplete: r }));
    const ring = (x, y) => {
      const s = scene.add.sprite(x, y, 'tap_ring', 0).setScale(2);
      layer.add(s);
      s.play('tap_ring').once('animationcomplete', () => s.destroy());
    };
    const along = (a, b, arc, u) => [a[0] + (b[0] - a[0]) * u, a[1] + (b[1] - a[1]) * u - arc * 4 * u * (1 - u)];
    (async () => {
      while (alive) {
        for (const st of steps) {
          if (!alive) return;
          if (st.tap) {
            await move(...st.tap, 500); if (!alive) return;
            hand.setFrame(1); ring(...st.tap); await sleep(260); if (!alive) return;
            hand.setFrame(0); await sleep(500);
          } else if (st.hold) {
            await move(...st.hold, 500); if (!alive) return;
            hand.setFrame(1);
            for (let t = 0; t < (st.ms ?? 1600) && alive; t += 400) { ring(...st.hold); await sleep(400); }
            if (!alive) return;
            hand.setFrame(0); await sleep(500);
          } else if (st.drag || st.rub) {
            const [a, b] = st.drag ?? st.rub, arc = st.arc ?? 0;
            await move(...a, 500); if (!alive) return;
            hand.setFrame(1);
            const carried = st.carry ? scene.add.image(...a, st.carry).setScale(2) : null;
            if (carried) layer.add(carried);
            const dots = [];
            if (st.drag) for (let i = 1; i < 10; i++) {
              const d = scene.add.image(...along(a, b, arc, i / 10), 'demo_dot').setScale(2).setAlpha(0.9);
              layer.add(d); dots.push(d);
            }
            const legs = st.rub ? [[b, 0], [a, 0], [b, 0], [a, 0]] : [[b, arc]];
            let from = a;
            for (const [to, h] of legs) {
              const t0 = { u: 0 };
              await new Promise(r => scene.tweens.add({ targets: t0, u: 1, duration: st.rub ? 380 : 1100, ease: 'Sine.easeInOut',
                onUpdate: () => { const p = along(from, to, h, t0.u); hand.setPosition(...p); carried?.setPosition(p[0], p[1] - 10); },
                onComplete: r }));
              if (!alive) return;
              from = to;
            }
            hand.setFrame(0); await sleep(600);
            carried?.destroy(); dots.forEach(d => d.destroy());
          }
        }
        await sleep(500);
      }
    })();
  });
}

// HUD: meter (heart, frame, fill), dog name, task card, ? (replay the demo) and pause.
export class Hud {
  constructor(scene, meter, { name, onPause, onHelp }) {
    this.scene = scene; this.meter = meter; this.shown = meter.value;
    const d = 100;
    this.heart = art(scene, 21, 20, 'meter_heart', 0.5, 0.5).setDepth(d);
    art(scene, 36, 10, 'meter_frame').setDepth(d);
    this.fill = art(scene, 38, 12, 'meter_fill_green').setDepth(d);
    text(scene, 172, 9, name, 16).setDepth(d);
    nine(scene, 362, 6, 'card_info', 192, 32, 6).setDepth(d);
    this.taskIcon = art(scene, 370, 6, 'icon_bowl').setDepth(d);
    this.taskText = text(scene, 406, 13, '', 14).setDepth(d);
    this.help = scene.add.container(0, 0, [button(scene, 564, 6, 32, 32, '', onHelp, { kind: 'cream' }), art(scene, 564, 6, 'icon_help')]).setDepth(d);
    button(scene, 604, 6, 32, 32, '', onPause, { kind: 'cream' }).setDepth(d);
    art(scene, 604, 6, 'icon_pause').setDepth(d + 1);
  }
  setTask(icon, label) { this.taskIcon.setTexture(`icon_${icon}`); this.taskText.setText(label); }
  setHelp(on) { this.help.setVisible(on); }
  update(dt) {
    this.shown += (this.meter.value - this.shown) * Math.min(1, dt / 120);
    this.fill.setTexture(`meter_fill_${this.meter.state}`);
    this.fill.setCrop(0, 0, Math.round(62 * this.shown / 100), 6);
    // red = pulse by fading (scaling would break the one-pixel-size rule)
    this.heart.setAlpha(this.meter.state === 'red' ? 0.55 + 0.45 * Math.abs(Math.sin(this.scene.time.now / 220)) : 1);
  }
  bump() { this.scene.tweens.add({ targets: this.heart, y: 14, duration: 110, yoyo: true }); }
}

// A heart floats up from (x, y).
export function heart(scene, x, y) {
  const h = art(scene, x, y, 'icon_heart', 0.5, 0.5).setDepth(140);
  scene.tweens.add({ targets: h, y: y - 36, alpha: 0, duration: 900, onComplete: () => h.destroy() });
}
