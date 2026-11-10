// The lantern posts along the world's roads (docs/world/WORLD_SPINE.md, pillar 2: "lantern posts
// line the roads: lit near the city, dark further out... a blue one is a warning"). Which open
// rooms have a post, and whether its lantern burns, by the region the room lies in. Pure: terrain.js
// draws what this says.
//
//   lit    a warm flame, and it lights the ground round it (the Lantern Vale; a peaceful room anywhere)
//   dark   the post stands, its lantern out (the country beyond the Vale)
//   cold   a cold flame that gives no warmth (where the mist rules: the Deep Road, the Reach, the Places Beyond)

const OPEN_SKY = new Set(['city', 'field', 'forest', 'hills', 'mountain', 'road', 'desert']);
// how often a room has a post (one room in N), and how its lantern stands, by region
const BY_REGION = {
  vale: { every: 2, state: 'lit' },
  marches: { every: 3, state: 'dark' },
  greenreach: { every: 4, state: 'dark' },
  stonemarch: { every: 4, state: 'dark' },
  frostmarch: { every: 4, state: 'dark' },
  sundersea: { every: 4, state: 'dark' },
  deeproad: { every: 4, state: 'cold' },
  reach: { every: 3, state: 'cold' },
  beyond: { every: 4, state: 'cold' },
};

// a room's own number, scrambled, so posts do not fall on every second vnum in a row
const mix = v => { let x = (Math.imul(v | 0, 0x9e3779b1) ^ 0x5bd1e995) >>> 0; x ^= x >>> 15; return (Math.imul(x, 0x85ebca6b) >>> 0) ^ (x >>> 13); };

// the post in a room: null (none), or { state: 'lit' | 'dark' | 'cold' }
export function postFor({ vnum, sector, flags = [], region = null } = {}) {
  const rule = BY_REGION[region];
  if (!rule || !OPEN_SKY.has(String(sector || ''))) return null;
  const f = new Set(flags || []);
  if (f.has('indoors') || f.has('deathtrap') || f.has('death')) return null;
  if ((mix(vnum) >>> 0) % rule.every !== 0) return null;
  // a peaceful room is someone's to keep: its lantern is tended, wherever it stands
  return { state: f.has('peaceful') && rule.state === 'dark' ? 'lit' : rule.state };
}

// where the post stands: the open cell nearest a corner of the room that has open ground on at
// least three sides (so it never plugs a narrow way). open(x, y) -> whether that cell can be
// walked; returns {x, y} or null. The corner is the room's own, by its number.
export function postCell(vnum, W, H, open) {
  const corners = [[3, 3], [W - 4, 3], [3, H - 4], [W - 4, H - 4]];
  const [cx, cy] = corners[(mix(vnum) >>> 8) % 4];
  let best = null, bestD = Infinity;
  for (let y = 1; y < H - 1; y++) {
    for (let x = 1; x < W - 1; x++) {
      if (!open(x, y)) continue;
      const sides = [[1, 0], [-1, 0], [0, 1], [0, -1]].filter(([dx, dy]) => open(x + dx, y + dy)).length;
      if (sides < 3) continue;
      const d = (x - cx) * (x - cx) + (y - cy) * (y - cy);
      if (d < bestD) { bestD = d; best = { x, y }; }
    }
  }
  return bestD <= 36 ? best : null;          // (no open ground within six cells of the corner: no post)
}
