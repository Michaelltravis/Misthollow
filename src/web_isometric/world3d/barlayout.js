// Where the extra action bars float (hud/bars.js), pure (tests/web run it). Each extra bar is a
// panel the player drags by its grip; it stays wholly on screen, lies along or across (vertical),
// can be locked (where it sits, and what is on it), and how many show is the player's choice
// (0-3). The main bar has a lock of its own. Kept per character and device in
// localStorage: a convenience, so anything odd read back falls to the defaults.
export const BAR_COUNT = 3;
export const SLOT_PX = 54;          // one slot (48) and its gap (6), unscaled
export const GRIP_PX = 26;          // the grip and its buttons at the bar's start

// a bar's size in px at UI scale `ui`: 8 slots and the grip, along or across
export function barSize(vertical, ui = 1) {
  const long = (8 * SLOT_PX + GRIP_PX + 12) * ui, short = (SLOT_PX + 12) * ui;
  return vertical ? { w: short, h: long } : { w: long, h: short };
}

// the first place each bar shows: centred above the main bar (which takes `mainH` px at the
// bottom), the next ones stacked above it, never over the main bar or each other
export function defaultPos(i, vw, vh, { ui = 1, mainH = 170 } = {}) {
  const s = barSize(false, ui);
  return clamp({ x: Math.round((vw - s.w) / 2), y: Math.round(vh - mainH * ui - (i + 1) * (s.h + 8 * ui)) }, s, vw, vh);
}

// keep a bar wholly on screen
export function clamp(pos, size, vw, vh) {
  const x = Math.min(Math.max(0, Math.round(+pos.x || 0)), Math.max(0, Math.round(vw - size.w)));
  const y = Math.min(Math.max(0, Math.round(+pos.y || 0)), Math.max(0, Math.round(vh - size.h)));
  return { x, y };
}

// the saved layout: {count, mainLocked, bars: [{x, y, vertical, locked} | null] × 3}
export function defaults() {
  return { count: 1, mainLocked: false, bars: new Array(BAR_COUNT).fill(null) };
}
export function parse(text) {
  const out = defaults();
  let d = null;
  try { d = JSON.parse(text); } catch { return out; }
  if (!d || typeof d !== 'object') return out;
  const n = Number(d.count);
  if (Number.isInteger(n) && n >= 0 && n <= BAR_COUNT) out.count = n;
  out.mainLocked = d.mainLocked === true;
  if (Array.isArray(d.bars)) {
    for (let i = 0; i < BAR_COUNT; i++) {
      const b = d.bars[i];
      if (b && Number.isFinite(+b.x) && Number.isFinite(+b.y)) {
        out.bars[i] = { x: +b.x, y: +b.y, vertical: !!b.vertical, locked: !!b.locked };
      }
    }
  }
  return out;
}
export function serialize(layout) {
  return JSON.stringify({ count: layout.count, mainLocked: !!layout.mainLocked, bars: layout.bars.map(b => (b ? { x: Math.round(b.x), y: Math.round(b.y), vertical: !!b.vertical, locked: !!b.locked } : null)) });
}

// is slot i (abilities.js: the main bar's 16, then 8 for each extra bar) on a locked bar
export function slotLocked(layout, i) {
  if (!(i >= 0)) return false;
  if (i < 16) return !!layout.mainLocked;
  const b = layout.bars[Math.floor((i - 16) / 8)];
  return !!(b && b.locked);
}

// do two rectangles overlap (for tests and the default stacking)
export function overlaps(a, b) {
  return a.x < b.x + b.w && b.x < a.x + a.w && a.y < b.y + b.h && b.y < a.y + a.h;
}
