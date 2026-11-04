// Tiny localStorage save (dog name, coat, furthest level). Storage can be blocked, so never throw.
const KEY = 'pawfect-parents';
const DEFAULT = { name: 'Biscuit', coat: 'caramel', level: 0 };

export function load() {
  try { return { ...DEFAULT, ...JSON.parse(localStorage.getItem(KEY) || '{}') }; }
  catch { return { ...DEFAULT }; }
}

export function save(patch) {
  const next = { ...load(), ...patch };
  try { localStorage.setItem(KEY, JSON.stringify(next)); } catch { /* private mode: play on without saving */ }
  return next;
}
