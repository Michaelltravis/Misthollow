// Your own action bar and the spellbook's bookkeeping. Pure (no DOM): tests/web run it.
//
// The player payload lists every ability of the class (`abilities`: id, name, type, pct,
// level it unlocks at, known, cost, cooldown, range, target, description) and the bar the
// player arranged (`bar`: SLOTS ability ids or null). The main bar is the first 16 (keys 1-8,
// then Shift+1-8); three extra bars of 8 follow (Alt+1-8, Alt+Shift+1-8, and one you click),
// floating panels the player places (hud/bars.js). Abilities are
// learned by reaching their level (at 50%), improve as they are used (to 85%, "Mastered"),
// and a trainer teaches the rest (to 100%).
export const MAIN = 16;
export const EXTRA = [[16, 24], [24, 32], [32, 40]];
export const SLOTS = 40;

// the key a slot answers to, as the slot shows it ('' for the click-only bar); `long` for tips
export function keyOf(i, long = false) {
  if (i < 8) return String(i + 1);
  if (i < 16) return long ? `Shift+${i - 7}` : `⇧${i - 7}`;
  if (i < 24) return long ? `Alt+${i - 15}` : `A${i - 15}`;
  if (i < 32) return long ? `Alt+Shift+${i - 23}` : `A⇧${i - 23}`;
  return '';
}
// the slot a key press means: digit 1-8 with Shift/Alt held, or -1
export function slotForKey(n, { shift = false, alt = false } = {}) {
  if (!(n >= 1 && n <= 8)) return -1;
  return (alt ? 16 : 0) + (shift ? 8 : 0) + n - 1;
}
export const BY_USE = 85;

// what a proficiency is called
export function rankOf(pct) {
  const p = Number(pct) || 0;
  return p >= 100 ? 'Perfected' : p >= BY_USE ? 'Mastered' : p >= 80 ? 'Expert' : p >= 70 ? 'Adept' : p >= 60 ? 'Apprentice' : p > 0 ? 'Novice' : 'Not learned';
}

// the abilities you can put on the bar (passives work on their own)
export const usable = a => !!(a && a.known && !a.passive);
export function knownIds(abilities) {
  return new Set((abilities || []).filter(usable).map(a => a.id));
}

// a bar from the server, kept to abilities you still know, always SLOTS long
export function cleanBar(bar, abilities) {
  const known = knownIds(abilities), out = new Array(SLOTS).fill(null), seen = new Set();
  (Array.isArray(bar) ? bar : []).slice(0, SLOTS).forEach((id, i) => {
    if (id && known.has(id) && !seen.has(id)) { out[i] = id; seen.add(id); }
  });
  return out;
}

// a first bar for a character who never arranged one: the class's usual order, then the rest
// of what is known by the level it came at
export function defaultBar(abilities, order = []) {
  const known = (abilities || []).filter(usable);
  const rank = id => { const i = order.indexOf(id); return i < 0 ? 1e3 : i; };
  const ids = known.slice().sort((a, b) => rank(a.id) - rank(b.id) || (a.level || 0) - (b.level || 0) || String(a.id).localeCompare(b.id))
    .map(a => a.id);
  const bar = new Array(SLOTS).fill(null);
  ids.slice(0, MAIN).forEach((id, i) => { bar[i] = id; });     // the main bar; the extra bars are yours
  return bar;
}

// a slot on a bar the player locked (hud/bars.js): what is on it stays, and nothing new goes on
const UNLOCKED = () => false;

// newly learned abilities take the first free slots (the main bar first, then the extra bars
// shown: `upto` slots), not a locked bar's; returns where
export function placeNew(bar, ids, upto = SLOTS, locked = UNLOCKED) {
  const out = bar.slice(), placed = [];
  while (out.length < SLOTS) out.push(null);
  for (const id of ids) {
    if (out.includes(id)) continue;
    const i = out.findIndex((x, k) => x === null && !locked(k));
    if (i < 0 || i >= upto) break;
    out[i] = id;
    placed.push({ id, slot: i });
  }
  return { bar: out, placed };
}

// put an ability in a slot: one already on the bar swaps places with what is there. A locked
// slot neither takes an ability nor gives up the one it holds: the bar comes back as it was
export function putOnBar(bar, id, slot, locked = UNLOCKED) {
  if (slot < 0 || slot >= SLOTS || locked(slot)) return bar.slice();
  const out = bar.slice(), from = out.indexOf(id);
  if (from === slot || (from >= 0 && locked(from))) return out;
  if (from >= 0) out[from] = out[slot];
  out[slot] = id;
  return out;
}

export function takeOffBar(bar, slot, locked = UNLOCKED) {
  const out = bar.slice();
  if (slot >= 0 && slot < SLOTS && !locked(slot)) out[slot] = null;
  return out;
}

// a bar you changed, keeping what you could not see: an ability the arrangement holds that the
// shown bar lacks (the class's book not come yet, a payload without it) stays where it was,
// unless something now sits there. Only the server knows what you know, and it keeps what is so
export function keepUnseen(next, arranged, shown) {
  const out = next.slice(), seen = new Set(shown.filter(Boolean));
  (Array.isArray(arranged) ? arranged : []).slice(0, SLOTS).forEach((id, i) => {
    if (id && !seen.has(id) && out[i] == null && !out.includes(id)) out[i] = id;
  });
  return out;
}

// what changed between two payloads: abilities learned, and proficiencies that grew
export function diffAbilities(prev, next) {
  const before = new Map((prev || []).map(a => [a.id, a]));
  const learned = [], improved = [];
  for (const a of next || []) {
    const b = before.get(a.id);
    if (a.known && !(b && b.known)) learned.push(a.id);
    else if (a.known && b && (a.pct || 0) > (b.pct || 0)) improved.push({ id: a.id, from: b.pct || 0, to: a.pct || 0 });
  }
  return { learned, improved };
}

// the line under an ability's name: cost, cooldown, range
export function costLine(a) {
  if (a.passive) return 'Passive — always at work';
  const parts = [];
  if (a.cost) parts.push(`${a.cost} ${a.res || 'mana'}`);
  if (a.cd) parts.push(`${a.cd >= 60 ? `${Math.round(a.cd / 60)} min` : `${a.cd} s`} cooldown`);
  if (a.target === 'self') parts.push('yourself');
  else if (a.target === 'area') parts.push(a.range ? `all around, ${a.range} m` : 'all around');
  else if (a.range) parts.push(a.range <= 3 ? 'melee' : `${a.range} m`);
  return parts.join(' · ');
}
