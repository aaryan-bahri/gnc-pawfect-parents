// Happiness meter: soft timer + feedback (GAME_DESIGN.md §3.2). Pure logic, no Phaser.
export class HappinessMeter {
  constructor({ start = 80, drainPerSec = 0.25, onEmpty = () => {} } = {}) {
    this.start = start;
    this.drainPerSec = drainPerSec;
    this.onEmpty = onEmpty;
    this.reset();
  }

  reset() {
    this.value = this.start;
    this.pauses = 0;      // counter so nested pauses (card over cutscene) resolve cleanly
    this.emptied = false;
  }

  pause() { this.pauses++; }
  resume() { this.pauses = Math.max(0, this.pauses - 1); }
  get paused() { return this.pauses > 0; }

  update(dtMs) {
    if (this.paused || this.emptied) return;
    this.set(this.value - this.drainPerSec * dtMs / 1000);
  }

  add(n) { if (!this.emptied) this.set(this.value + n); }

  set(v) {
    this.value = Math.min(100, Math.max(0, v));
    if (this.value === 0 && !this.emptied) {
      this.emptied = true;
      this.onEmpty();
    }
  }

  // green > 60, yellow 30–60, red < 30
  get state() { return this.value > 60 ? 'green' : this.value >= 30 ? 'yellow' : 'red'; }
}
