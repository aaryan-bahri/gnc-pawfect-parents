// The dog (puppy or young dog): one sprite (origin at the paws), coat-specific animations, and promise-based walking.
import { W, WORLD } from './ui.js';

export class Dog {
  // stage: 'puppy' or 'young'. y is where the paws stand (canvas px); the default is the living-room floor.
  constructor(scene, coat, x, { stage = 'puppy', y = W(WORLD.groundY + 2) } = {}) {
    this.scene = scene;
    this.coat = coat;
    this.stage = stage;
    this.sprite = scene.add.sprite(x, y, `${stage}_${coat}_idle`).setOrigin(0.5, 1).setScale(2).setDepth(50);
    this.play('idle');
  }

  get x() { return this.sprite.x; }

  play(anim) {
    if (anim === 'circle') this.sprite.setFlipX(false);   // the circle frames already turn both ways
    this.sprite.play(`${this.stage}_${this.coat}_${anim}`, true);
    return this;
  }

  face(dir) { this.sprite.setFlipX(dir < 0); return this; }

  // One frame of following something at canvas x (a held treat). Returns true once the puppy is there.
  chase(x, dt, speed = 100) {
    const dx = x - this.sprite.x;
    if (Math.abs(dx) < 4) { this.play('idle'); return true; }
    this.face(dx).play('walk');
    this.sprite.x += Math.sign(dx) * Math.min(Math.abs(dx), speed * dt / 1000);
    return false;
  }

  // Walk to canvas x at `speed` px/s. Resolves on arrival (never if the tween is killed by a task restart).
  walkTo(x, speed = 110) {
    const dx = x - this.sprite.x;
    if (Math.abs(dx) < 2) return Promise.resolve();
    this.face(dx).play('walk');
    return new Promise(resolve => {
      this.scene.tweens.add({ targets: this.sprite, x, duration: Math.abs(dx) / speed * 1000, onComplete: () => {
        this.play('idle'); resolve();
      } });
    });
  }
}
