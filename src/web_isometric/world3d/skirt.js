// The land round an outdoor room: which of the empty cells next to it it fills, and how far.
// Pure logic (no THREE), so it runs in Node tests; terrain.js fillerLand draws what it plans.
//
// A room fills half of each empty cell beside it (a room on that cell's far side fills the other
// half); in an opened zone (wilds.py) the land at the zone's edge runs on a cell and a half, into
// the fog. `empty(dx, dy)` says whether the cell that far from the room is free.

// the patches to fill, in world metres: [x0, z0, w, d, outward axis ('x'|'z'|'c'), outward sign]
export function skirtPatches({ ox, oz, W, H, wild, empty }) {
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
