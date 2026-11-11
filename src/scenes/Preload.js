import { LOADING_TIPS } from '../content.js';
import { COATS, PUPPY_ANIMS, text } from '../ui.js';
import { GameScene } from '../view.js';

const UI = ['bubble_speech', 'bubble_speech_tail', 'bubble_thought', 'bubble_thought_tail', 'card_info', 'card_good', 'card_bad',
  'meter_frame', 'meter_heart', 'meter_fill_green', 'meter_fill_yellow', 'meter_fill_red', 'stamp_pawfect', 'swatch_ring',
  ...COATS.map(c => `swatch_${c}`), 'paper_top', 'paper_row', 'paper_bottom', 'list_box', 'list_tick', 'arrow_left', 'arrow_right', 'coin_small'];
const ICONS = ['bowl', 'question', 'tummy', 'heart', 'treat', 'clean', 'scold', 'droplet', 'pad', 'bulb', 'check', 'cross',
  'star', 'sound_on', 'sound_off', 'pause', 'vet', 'toothbrush', 'toothpaste', 'flea', 'clippers', 'ear', 'coin'];
const FOODS = ['kibble', 'chocolate', 'carrot', 'grapes', 'chicken', 'onion'];
const PANELS = ['car', 'porch', 'fridge', 'supplies', 'clinic', 'vaccine'];
const CLOSEUPS = ['teeth', 'coat', 'paws', 'ears'];
const SHOP = ['toothbrush', 'toothpaste', 'toothpaste_human', 'flea', 'flea_cat', 'ear', 'clippers', 'brush', 'shampoo_dog', 'shampoo_human',
  'chew', 'ball_squeak', 'ball_tiny', 'tag', 'bags', 'bandana', 'bow', 'sweater', 'collar', 'bed'];
const YOUNG_ANIMS = { idle: 4, wag: 9, sit: 2, nervous: 6, sad: 1.5 };
const FPS = { idle: 4, walk: 8, sit: 2, wag: 9, sniff: 4, circle: 6, pee: 3, eat: 5, refuse: 4, sad: 1.5, cower: 5 };

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

    const L = this.load;
    L.image('living_room', 'assets/bg/living_room.png');
    L.image('counter_closeup', 'assets/bg/counter_closeup.png');
    L.image('vet_clinic', 'assets/bg/vet_clinic.png');
    for (const k of ['store_aisle', 'store_till']) L.image(k, `assets/bg/${k}.png`);
    for (const k of SHOP) L.image(`shop_${k}`, `assets/sprites/shop_${k}.png`);
    L.spritesheet('coin_jar', 'assets/ui/coin_jar.png', { frameWidth: 12, frameHeight: 14 });
    L.spritesheet('basket', 'assets/ui/basket.png', { frameWidth: 30, frameHeight: 24 });
    for (const k of ['title_bg', 'logo', 'album_bg', 'polaroid', 'spotlight']) L.image(k, `assets/screens/${k}.png`);
    for (const p of PANELS) for (const c of COATS) L.image(`panel_${p}_${c}`, `assets/screens/panel_${p}_${c}.png`);
    for (const c of COATS) {
      for (const a of PUPPY_ANIMS) L.spritesheet(`puppy_${c}_${a}`, `assets/sprites/puppy_${c}_${a}.png`, { frameWidth: 32, frameHeight: 32 });
      for (const a of Object.keys(YOUNG_ANIMS)) L.spritesheet(`young_${c}_${a}`, `assets/sprites/young_${c}_${a}.png`, { frameWidth: 40, frameHeight: 40 });
      for (const a of ['idle', 'wag']) L.spritesheet(`adult_${c}_${a}`, `assets/sprites/adult_${c}_${a}.png`, { frameWidth: 48, frameHeight: 48 });
      for (const k of CLOSEUPS) L.image(`closeup_${k}_${c}`, `assets/screens/closeup_${k}_${c}.png`);
    }
    for (const a of ['talk', 'idle']) L.spritesheet(`parent_${a}`, `assets/sprites/parent_${a}.png`, { frameWidth: 48, frameHeight: 48 });
    for (const a of ['talk', 'idle']) L.spritesheet(`vet_${a}`, `assets/sprites/vet_${a}.png`, { frameWidth: 48, frameHeight: 48 });
    L.spritesheet('vet_stand', 'assets/sprites/vet_stand.png', { frameWidth: 36, frameHeight: 82 });
    L.spritesheet('spot_ring', 'assets/ui/spot_ring.png', { frameWidth: 10, frameHeight: 10 });
    for (const f of FOODS) L.image(`foodbig_${f}`, `assets/sprites/foodbig_${f}.png`);
    for (const f of ['empty', ...FOODS]) L.image(`bowl_${f}`, `assets/sprites/bowl_${f}.png`);
    for (const p of ['pad', 'puddle']) L.image(p, `assets/sprites/prop_${p}.png`);
    for (const u of UI) L.image(u, `assets/ui/${u}.png`);
    for (const i of ICONS) L.image(`icon_${i}`, `assets/ui/icon_${i}.png`);
    for (const b of ['mint', 'cream']) L.spritesheet(`button_${b}`, `assets/ui/button_${b}.png`, { frameWidth: 16, frameHeight: 14 });
    L.spritesheet('cue_arrow', 'assets/ui/cue_arrow.png', { frameWidth: 13, frameHeight: 17 });
  }

  create() {
    const A = this.anims;
    for (const c of COATS) {
      for (const a of PUPPY_ANIMS) {
        A.create({ key: `puppy_${c}_${a}`, frames: A.generateFrameNumbers(`puppy_${c}_${a}`), frameRate: FPS[a], repeat: -1 });
      }
      A.create({ key: `adult_${c}_idle`, frames: A.generateFrameNumbers(`adult_${c}_idle`), frameRate: 4, repeat: -1 });
      A.create({ key: `adult_${c}_wag`, frames: A.generateFrameNumbers(`adult_${c}_wag`), frameRate: 9, repeat: -1 });
      for (const [a, fps] of Object.entries(YOUNG_ANIMS)) {
        A.create({ key: `young_${c}_${a}`, frames: A.generateFrameNumbers(`young_${c}_${a}`), frameRate: fps, repeat: -1 });
      }
    }
    A.create({ key: 'parent_talk', frames: A.generateFrameNumbers('parent_talk'), frameRate: 8, repeat: -1 });
    A.create({ key: 'parent_idle', frames: A.generateFrameNumbers('parent_idle'), frameRate: 3, repeat: -1 });
    A.create({ key: 'vet_talk', frames: A.generateFrameNumbers('vet_talk'), frameRate: 8, repeat: -1 });
    A.create({ key: 'vet_idle', frames: A.generateFrameNumbers('vet_idle'), frameRate: 3, repeat: -1 });
    A.create({ key: 'vet_stand', frames: A.generateFrameNumbers('vet_stand'), frameRate: 3, repeat: -1 });
    A.create({ key: 'spot_ring', frames: A.generateFrameNumbers('spot_ring'), frameRate: 3, repeat: -1 });
    A.create({ key: 'cue_arrow', frames: A.generateFrameNumbers('cue_arrow'), frameRate: 6, repeat: -1 });
    // let the loading screen be seen for a moment even when assets come from cache
    this.time.delayedCall(900, () => this.scene.start('Title'));
  }
}
