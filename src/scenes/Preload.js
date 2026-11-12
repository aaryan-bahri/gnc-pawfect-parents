import { LOADING_TIPS } from '../content.js';
import { COATS, PUPPY_ANIMS, text } from '../ui.js';
import { GameScene } from '../view.js';

const UI = ['bubble_speech', 'bubble_speech_tail', 'bubble_thought', 'bubble_thought_tail', 'card_info', 'card_good', 'card_bad',
  'meter_frame', 'meter_heart', 'meter_fill_green', 'meter_fill_yellow', 'meter_fill_red', 'stamp_pawfect', 'swatch_ring',
  ...COATS.map(c => `swatch_${c}`), 'dialog_panel', 'portrait_frame', 'nameplate_parent', 'nameplate_vet', 'nameplate_sam', 'demo_dot',
  'level_card', 'pin', 'found_ring', 'found_ring_small', 'hover_frame'];
const ICONS = ['bowl', 'question', 'tummy', 'heart', 'treat', 'clean', 'scold', 'droplet', 'pad', 'bulb', 'check', 'cross', 'star',
  'sound_on', 'sound_off', 'pause', 'vet', 'help', 'magnifier', 'bath', 'ball', 'hot', 'leash', 'park', 'water', 'stop', 'run', 'sniff',
  'space', 'pet'];
const FOODS = ['kibble', 'chocolate', 'carrot', 'grapes', 'chicken', 'onion'];
const PANELS = ['bedroom', 'car_there', 'rescue', 'chosen', 'car', 'porch', 'fridge', 'supplies', 'afternoon', 'afternoon_sniff', 'night',
  'scratching', 'grooming_bag', 'clinic', 'vet_chart', 'vaccine', 'leash', 'park_gate', 'evening_home'];
// Level 2 close-ups: [part, sides]. Parts that show the dog come per coat.
const CLOSEUPS = [['teeth', 2], ['coat', 2], ['paws', 2], ['ears', 2], ['eyes', 1], ['tail', 1], ['toy', 2], ['toothpaste', 2], ['shampoo', 2],
  ['flea', 2], ['brush', 1]];
const COAT_CU = ['teeth', 'coat', 'paws', 'ears', 'eyes', 'tail', 'toy'];
const DIFFS = ['teeth', 'coat', 'paws', 'ears', 'toothpaste', 'shampoo', 'flea', 'toy'];
const PARTS = ['ears', 'teeth', 'eyes', 'paws', 'coat', 'tail', 'neck'];
const TRAY = [['toothpaste', 'dog'], ['toothpaste', 'home'], ['shampoo', 'dog'], ['shampoo', 'home'], ['flea', 'dog'], ['flea', 'home'],
  ['toy', 'dog'], ['toy', 'home'], ['brush', 'dog']];
const YOUNG_ANIMS = { idle: 4, wag: 9, sit: 2 };
const ADULT_ANIMS = { idle: 4, wag: 9, walk: 7, run: 12, carry: 7, tired: 4, pant: 4, flop: 2, rest: 1.5, drink: 4, sit: 2, lunge: 6,
  sniff: 4, nervous: 5, stress: 2, duck: 4, sad: 1.5 };
const FPS = { idle: 4, walk: 8, sit: 2, wag: 9, sniff: 4, circle: 6, pee: 3, eat: 5, refuse: 4, sad: 1.5, cower: 5 };
const SAM = { run: 8, walk: 5, stand: 1, hand: 1, pet: 1, wave: 1 };

// Boot: only what the loading screen itself shows.
export class Boot extends GameScene {
  constructor() { super('Boot'); }
  preload() {
    this.load.image('paw_empty', 'assets/screens/paw_empty.png');
    this.load.image('paw_full', 'assets/screens/paw_full.png');
    this.load.spritesheet('loading_pup', 'assets/sprites/puppy_caramel_circle.png', { frameWidth: 32, frameHeight: 32 });
  }
  create() { this.scene.start('Preload'); }
}

export class Preload extends GameScene {
  constructor() { super('Preload'); }

  preload() {
    this.anims.create({ key: 'loading_pup', frames: this.anims.generateFrameNumbers('loading_pup'), frameRate: 6, repeat: -1 });
    this.add.sprite(320, 152, 'loading_pup').setScale(2).play('loading_pup');
    const paws = Array.from({ length: 8 }, (_, i) => this.add.image(216 + i * 26, 210, 'paw_empty').setOrigin(0).setScale(2));
    const tip = Phaser.Utils.Array.GetRandom(LOADING_TIPS);
    text(this, 320, 256, `Tip: ${tip}`, 15, { color: '#8a6f66', wrap: 420, align: 'center' }).setOrigin(0.5, 0);
    this.load.on('progress', p => paws.forEach((paw, i) => paw.setTexture(i < Math.round(p * 8) ? 'paw_full' : 'paw_empty')));

    const L = this.load, sheet = (key, path, w, h) => L.spritesheet(key, path, { frameWidth: w, frameHeight: h });
    for (const k of ['living_room', 'counter_closeup', 'spot_bg', 'bath_bg', 'bath_tub_front', 'street', 'park']) L.image(k, `assets/bg/${k}.png`);
    for (const k of ['title_bg', 'logo', 'album_bg', 'polaroid', 'spotlight', 'select_bg', 'timecard_bg', 'finale_bg']) L.image(k, `assets/screens/${k}.png`);
    for (const c of COATS) {
      for (const p of PANELS) L.image(`panel_${p}_${c}`, `assets/screens/panel_${p}_${c}.png`);
      for (const t of ['thumb_home', 'thumb_clinic', 'thumb_park']) L.image(`${t}_${c}`, `assets/screens/${t}_${c}.png`);
      for (const a of PUPPY_ANIMS) sheet(`puppy_${c}_${a}`, `assets/sprites/puppy_${c}_${a}.png`, 32, 32);
      for (const a of Object.keys(YOUNG_ANIMS)) sheet(`young_${c}_${a}`, `assets/sprites/young_${c}_${a}.png`, 40, 40);
      for (const a of Object.keys(ADULT_ANIMS)) sheet(`adult_${c}_${a}`, `assets/sprites/adult_${c}_${a}.png`, 48, 48);
      sheet(`big_${c}`, `assets/sprites/big_${c}.png`, 76, 62);
    }
    for (const [part, n] of CLOSEUPS) {
      for (const side of ['healthy', 'yours'].slice(0, n)) {
        if (COAT_CU.includes(part)) for (const c of COATS) L.image(`cu_${part}_${side}_${c}`, `assets/screens/cu_${part}_${side}_${c}.png`);
        else L.image(`cu_${part}_${side}`, `assets/screens/cu_${part}_${side}.png`);
      }
    }
    for (const d of DIFFS) L.image(`found_cu_${d}`, `assets/ui/found_cu_${d}.png`);
    for (const n of ['nails', 'ears', 'teeth', 'fleas']) L.image(`issue_${n}`, `assets/sprites/issue_${n}.png`);
    for (const p of PARTS) { L.image(`part_${p}`, `assets/sprites/part_${p}.png`); L.image(`ring_${p}`, `assets/sprites/ring_${p}.png`); }
    for (const [t, s] of TRAY) L.image(`tray_${t}_${s}`, `assets/sprites/tray_${t}_${s}.png`);
    for (const k of ['toothbrush', 'clippers', 'ear', 'towel']) L.image(`care_${k}`, `assets/sprites/care_${k}.png`);
    sheet('foam', 'assets/sprites/foam.png', 76, 62);
    for (const k of ['kid_park', 'leash_slack', 'leash_tight', 'sandwich', 'park_tree', 'park_shade', 'fountain', 'ball', 'ball_shadow', 'sam_hand',
      'adult_part_head', 'adult_part_chest', 'adult_ring_head', 'adult_ring_chest']) L.image(k, `assets/sprites/${k}.png`);
    sheet('kid_walk', 'assets/sprites/kid_walk.png', 40, 62);
    sheet('squirrel', 'assets/sprites/squirrel.png', 20, 18);
    sheet('cat', 'assets/sprites/cat.png', 22, 18);
    sheet('water_bowl', 'assets/sprites/water_bowl.png', 22, 12);
    for (const p of Object.keys(SAM)) sheet(`sam_${p}`, `assets/sprites/sam_${p}.png`, 40, 62);
    for (const a of ['talk', 'idle']) {
      sheet(`parent_${a}`, `assets/sprites/parent_${a}.png`, 48, 48);
      sheet(`vet_${a}`, `assets/sprites/vet_${a}.png`, 48, 48);
      sheet(`sam_bust_${a}`, `assets/sprites/sam_bust_${a}.png`, 48, 48);
    }
    for (const f of FOODS) L.image(`foodbig_${f}`, `assets/sprites/foodbig_${f}.png`);
    for (const f of ['empty', ...FOODS]) L.image(`bowl_${f}`, `assets/sprites/bowl_${f}.png`);
    for (const p of ['pad', 'puddle']) L.image(p, `assets/sprites/prop_${p}.png`);
    for (const u of UI) L.image(u, `assets/ui/${u}.png`);
    for (const i of ICONS) L.image(`icon_${i}`, `assets/ui/icon_${i}.png`);
    for (const k of ['morning', 'afternoon', 'evening', 'night', 'later']) L.image(`time_${k}`, `assets/ui/time_${k}.png`);
    for (const b of ['mint', 'cream']) sheet(`button_${b}`, `assets/ui/button_${b}.png`, 16, 14);
    sheet('cue_arrow', 'assets/ui/cue_arrow.png', 13, 17);
    sheet('hand', 'assets/ui/hand.png', 18, 22);
    sheet('tap_ring', 'assets/ui/tap_ring.png', 20, 20);
  }

  create() {
    const A = this.anims, loop = (key, fps, tex = key) => A.create({ key, frames: A.generateFrameNumbers(tex), frameRate: fps, repeat: -1 });
    for (const c of COATS) {
      for (const a of PUPPY_ANIMS) loop(`puppy_${c}_${a}`, FPS[a]);
      for (const [a, fps] of Object.entries(YOUNG_ANIMS)) loop(`young_${c}_${a}`, fps);
      for (const [a, fps] of Object.entries(ADULT_ANIMS)) loop(`adult_${c}_${a}`, fps);
    }
    for (const who of ['parent', 'vet', 'sam_bust']) { loop(`${who}_talk`, 8); loop(`${who}_idle`, 3); }
    for (const [p, fps] of Object.entries(SAM)) loop(`sam_${p}`, fps);
    loop('kid_walk', 6);
    loop('squirrel', 3);
    loop('cat', 2);
    loop('cue_arrow', 6);
    A.create({ key: 'tap_ring', frames: A.generateFrameNumbers('tap_ring'), frameRate: 12, repeat: 0 });
    // let the loading screen be seen for a moment even when assets come from cache
    this.time.delayedCall(900, () => this.scene.start('Title'));
  }
}
