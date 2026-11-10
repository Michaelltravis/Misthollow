// The buff bar's list (hud.js renderBuffs): one icon a spell. A spell sets several affects (Armor
// both its armour and its ward), each its own entry; they show as one, with the longest time left.
export function buffList(aff, max = 12) {
  const seen = new Map();
  for (const a of aff || []) {
    if (!a || !(a.name || a.spell)) continue;
    const k = String(a.name || a.spell).toLowerCase();
    const was = seen.get(k);
    const left = x => (x.remaining != null ? x.remaining : x.duration) || 0;
    if (!was || left(a) > left(was)) seen.set(k, a);
  }
  return [...seen.values()].slice(0, max);
}

// the spell an affect's icon is drawn for: a skill's part effects (shield_wall_invuln) as the skill
export const auraBase = name => String(name || '').toLowerCase().replace(/\s+/g, '_')
  .replace(/_(invuln|damage|speed|mend|crit|stealth|haste|stun|regen|bonus)$/, '');

// what a nameplate shows of the buffs and debuffs on someone (map_system._auras: {n, h, r, d}):
// the debuffs first, then the buffs, each {id, label, bad, frac (of its time left), secs}; at most
// `max`. `tick` is an affect tick in seconds.
export function plateAuras(auras, { max = 8, tick = 6 } = {}) {
  const out = [];
  for (const a of auras || []) {
    if (!a || !a.n) continue;
    const r = a.r || 0, d = a.d || 0;
    out.push({ id: auraBase(a.n), label: String(a.n).replace(/_/g, ' '), bad: !!a.h,
      frac: d > 0 ? Math.max(0, Math.min(1, r / d)) : 1, secs: d > 0 ? Math.max(0, Math.round(r * tick)) : null });
  }
  out.sort((x, y) => (y.bad - x.bad));
  return out.slice(0, max);
}
