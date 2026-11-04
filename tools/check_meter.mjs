// node tools/check_meter.mjs
import assert from 'node:assert/strict';
import { HappinessMeter } from '../src/meter.js';

let empties = 0;
const m = new HappinessMeter({ start: 80, drainPerSec: 0.25, onEmpty: () => empties++ });

m.update(4000);
assert.equal(m.value, 79, 'drains 0.25/s');

m.pause(); m.pause(); m.update(10000); m.resume();
assert.equal(m.value, 79, 'nested pause holds');
m.resume(); m.update(4000);
assert.equal(m.value, 78, 'resumes after both pauses released');

m.add(50);
assert.equal(m.value, 100, 'clamps at 100');
assert.equal(m.state, 'green');
m.set(45); assert.equal(m.state, 'yellow');
m.set(10); assert.equal(m.state, 'red');

m.add(-100); m.update(1000); m.add(-5);
assert.equal(m.value, 0, 'clamps at 0');
assert.equal(empties, 1, 'onEmpty fires once');
m.add(20);
assert.equal(m.value, 0, 'no gains after empty until reset');

m.reset();
assert.equal(m.value, 80); assert.equal(m.paused, false);
console.log('ok: meter checks pass');
