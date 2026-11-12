// Tiny localStorage save (dog name, coat, furthest level, whether a dog was adopted, demos already seen). Storage can be blocked,
// so never throw.
const KEY = 'pawfect-parents';
const DEFAULT = { name: 'Biscuit', coat: 'caramel', level: 0, adopted: false, demos: [] };

export function load() {
  try { return { ...DEFAULT, ...JSON.parse(localStorage.getItem(KEY) || '{}') }; }
  catch { return { ...DEFAULT }; }
}

export function save(patch) {
  const next = { ...load(), ...patch };
  try { localStorage.setItem(KEY, JSON.stringify(next)); } catch { /* private mode: play on without saving */ }
  return next;
}
