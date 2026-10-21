// What lies past a room's edge, as rules the 3D client draws by (no Three.js here, so the tests
// can run them): which sides of a water room are land, and what an empty map cell is filled with.
//
// The owner, on the Sea of Storms: "ocean rooms that have no exit should just show more ocean on
// the horizon or a land mass if there's a description of land in the distance ... forests,
// marshes etc too". A water room's exitless sides are open water (roomgen.js: `deep`), save the
// sides that are land: the way out there leads onto land, the map's room there is dry land, or
// the room's own words put the shore or a breakwater right there (room_vistas.py: a `near`
// vista). And every empty cell round the zone is more of the country nearest it (far.js): the sea
// runs on as sea, a forest as forest.

export const WATERS = new Set(['water_swim', 'water_noswim']);
export const SIDES = { north: [0, -1], south: [0, 1], east: [1, 0], west: [-1, 0] };

const lookOf = r => String((r && r.data && (r.data.look || r.data.sector)) || '');

// room: {cx, cy, data: {look, sector, exits: {dir: {to}}, vista}}; zone: {cells: Map 'x,y' -> room,
// rooms: Map vnum -> room}; themeOf: look -> theme. Returns {north: true, ...} for the land sides.
export function landSides(room, zone, themeOf) {
  const out = {};
  if (!WATERS.has(themeOf(lookOf(room)))) return out;
  const isLand = r => { const t = themeOf(lookOf(r)); return !!r && !WATERS.has(t) && t !== 'underwater'; };
  const exits = (room.data && room.data.exits) || {};
  for (const [side, [dx, dy]] of Object.entries(SIDES)) {
    const e = exits[side];
    const there = e ? zone.rooms && zone.rooms.get(e.to) : zone.cells && zone.cells.get(`${room.cx + dx},${room.cy + dy}`);
    if (isLand(there)) out[side] = true;
  }
  // the room's own words: the shore at hand, the moles either side (room_vistas.py near vistas);
  // a shore named with no side lies where the boat cannot go
  const exitless = Object.keys(SIDES).filter(s => !exits[s]);
  for (const v of (room.data && room.data.vista) || []) {
    if (!v.near) continue;
    if (v.dir && SIDES[v.dir]) out[v.dir] = true;
    else for (const s of exitless) out[s] = true;
  }
  return out;
}

// What an empty cell is filled with: the nearest occupied cell's source (Chebyshev rings out to
// maxR; at one distance the commonest kind wins, a tie to the one seen first). source(x, y) ->
// {kind, ...} or null; returns {src, r} or null.
export function fillKind(source, cx, cy, maxR) {
  for (let r = 1; r <= maxR; r++) {
    const seen = new Map();          // kind -> {n, src}, in the order first seen
    for (let y = cy - r; y <= cy + r; y++) for (let x = cx - r; x <= cx + r; x++) {
      if (Math.max(Math.abs(x - cx), Math.abs(y - cy)) !== r) continue;
      const s = source(x, y);
      if (!s) continue;
      const e = seen.get(s.kind) || { n: 0, src: s };
      e.n++;
      seen.set(s.kind, e);
    }
    let best = null;
    for (const e of seen.values()) if (!best || e.n > best.n) best = e;
    if (best) return { src: best.src, r };
  }
  return null;
}

// Where a room's far vistas go (vista.js draws them): [{kind, side}]. Land named with a side goes
// there; named with none, off the sides the room has no way out of (else straight ahead, north);
// never on a side where the zone's own rooms stand within BLOCKED_REACH (far.js draws those).
const BLOCKED_REACH = 2;      // rooms of the zone this near on a side: no vista there

export function vistaPlaces(room, cells) {
  const d = room.data || {}, exits = d.exits || {};
  const busy = side => {
    const [dx, dy] = SIDES[side];
    for (let k = 1; k <= BLOCKED_REACH; k++) if (cells && cells.get(`${room.cx + dx * k},${room.cy + dy * k}`)) return true;
    return false;
  };
  const exitless = Object.keys(SIDES).filter(s => !exits[s]);
  const out = [];
  const seen = new Set();
  for (const v of d.vista || []) {
    if (v.near) continue;
    const sides = v.dir && SIDES[v.dir] ? [v.dir] : (exitless.length ? exitless.slice(0, 2) : ['north']);
    for (const side of sides) {
      if (busy(side) || seen.has(side)) continue;
      seen.add(side);
      out.push({ kind: v.kind, side });
    }
  }
  return out;
}

