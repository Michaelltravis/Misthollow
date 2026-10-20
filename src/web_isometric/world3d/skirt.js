// The land round an outdoor room: which of the empty cells next to it it fills, and how far.
// Pure logic (no THREE), so it runs in Node tests; terrain.js fillerLand draws what it plans.
//
// A room fills half of each empty cell beside it (a room on that cell's far side fills the other
// half); in an opened zone (wilds.py) the land at the zone's edge runs on a cell and a half, into
// the fog. `empty(dx, dy)` says whether the cell that far from the room is free.
//
// No two rooms' land lies on the same ground: where it would, one gives way (`yields`), so one
// room's trees never stand in the strip of land in front of another (A Leader Strand was hidden
// behind the trees of the room round the corner).

// the patches as each room would lay them alone: [x0, z0, w, d, outward axis ('x'|'z'|'c'), sign]
function rawPatches(ox, oz, W, H, wild, empty) {
  const far = (dx, dy) => (wild && empty(2 * dx, 2 * dy) ? 1.5 : 0.5);
  const HWx = dx => W * far(dx, 0), HHy = dy => H * far(0, dy);
  const patches = [];
  if (empty(0, -1)) patches.push([ox, oz - HHy(-1), W, HHy(-1), 'z', -1]);
  if (empty(0, 1)) patches.push([ox, oz + H, W, HHy(1), 'z', 1]);
  if (empty(-1, 0)) patches.push([ox - HWx(-1), oz, HWx(-1), H, 'x', -1]);
  if (empty(1, 0)) patches.push([ox + W, oz, HWx(1), H, 'x', 1]);
  for (const [dx, dy] of [[-1, -1], [1, -1], [-1, 1], [1, 1]]) {
    if (empty(dx, dy) && empty(dx, 0) && empty(0, dy)) {
      // (a corner runs on a cell and a half only over cells that are empty: Before The Gates Of
      // Mahn-Tor was buried under the cliffs of the mountain room a cell up and a cell across)
      const wide = wild && empty(2 * dx, 2 * dy);
      const cw = Math.min(HWx(dx), wide && empty(2 * dx, dy) ? HWx(dx) : W / 2), cd = Math.min(HHy(dy), wide && empty(dx, 2 * dy) ? HHy(dy) : H / 2);
      patches.push([dx < 0 ? ox - cw : ox + W, dy < 0 ? oz - cd : oz + H, cw, cd, 'c', 0]);
    }
  }
  return patches;
}

const RANK = { z: 0, x: 1, c: 2 };
const overlap = (a, b) => Math.min(a[0] + a[2], b[0] + b[2]) - Math.max(a[0], b[0]) > 1e-6
  && Math.min(a[1] + a[3], b[1] + b[3]) - Math.max(a[1], b[1]) > 1e-6;

// whether patch `a` of the room at cell `ca` gives way to patch `b` of the room at `cb` where they
// meet: the room nearer the ground they share keeps it; as near, the land straight north or south
// of a room before the land east or west of it (the cell in front of the camera is the room's
// behind it), then corners; then the room further north, then west (both decide the same way)
export function yields(a, ca, b, cb, W, H) {
  const mx = (Math.max(a[0], b[0]) + Math.min(a[0] + a[2], b[0] + b[2])) / 2 / W;
  const mz = (Math.max(a[1], b[1]) + Math.min(a[1] + a[3], b[1] + b[3])) / 2 / H;
  const dist = c => Math.hypot(c[0] + 0.5 - mx, c[1] + 0.5 - mz);
  const da = dist(ca), db = dist(cb);
  if (Math.abs(da - db) > 1e-9) return da > db;
  if (RANK[a[4]] !== RANK[b[4]]) return RANK[a[4]] > RANK[b[4]];
  return ca[1] !== cb[1] ? ca[1] > cb[1] : ca[0] > cb[0];
}

// rect minus rect: what is left of `r` outside `cut`, as up to four rects
function subtract(r, cut) {
  const [x0, z0, w, d] = r, x1 = x0 + w, z1 = z0 + d;
  const cx0 = Math.max(x0, cut[0]), cz0 = Math.max(z0, cut[1]), cx1 = Math.min(x1, cut[0] + cut[2]), cz1 = Math.min(z1, cut[1] + cut[3]);
  if (cx1 - cx0 <= 1e-6 || cz1 - cz0 <= 1e-6) return [r];
  const out = [];
  if (cz0 - z0 > 1e-6) out.push([x0, z0, w, cz0 - z0]);
  if (z1 - cz1 > 1e-6) out.push([x0, cz1, w, z1 - cz1]);
  if (cx0 - x0 > 1e-6) out.push([x0, cz0, cx0 - x0, cz1 - cz0]);
  if (x1 - cx1 > 1e-6) out.push([cx1, cz0, x1 - cx1, cz1 - cz0]);
  return out;
}

// the patches to fill, in world metres: [x0, z0, w, d, outward axis ('x'|'z'|'c'), outward sign,
// the whole patch it is a piece of ([x0, z0, w, d]: how far out a point lies is measured on it)]
export function skirtPatches({ ox, oz, W, H, wild, empty }) {
  const own = rawPatches(ox, oz, W, H, wild, empty);
  if (!own.length) return [];
  const cx = Math.round(ox / W), cy = Math.round(oz / H);
  // the rooms near enough for their land to meet this room's, and theirs
  const others = [];
  for (let dx = -3; dx <= 3; dx++) for (let dy = -3; dy <= 3; dy++) {
    if ((!dx && !dy) || empty(dx, dy)) continue;
    const theirs = rawPatches(ox + dx * W, oz + dy * H, W, H, wild, (ex, ey) => empty(dx + ex, dy + ey));
    for (const p of theirs) others.push([p, [cx + dx, cy + dy]]);
  }
  const res = [];
  for (const p of own) {
    let pieces = [p.slice(0, 4)];
    for (const [q, cq] of others) {
      if (!overlap(p, q) || !yields(p, [cx, cy], q, cq, W, H)) continue;
      pieces = pieces.flatMap(r => subtract(r, q));
      if (!pieces.length) break;
    }
    for (const r of pieces) res.push([...r, p[4], p[5], p.slice(0, 4)]);
  }
  return res;
}
