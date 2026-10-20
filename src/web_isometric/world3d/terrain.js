// Turns a room layout (MH.generateRoomTopDown: a 24x15 tile grid of FLOOR / BLOCK /
// WATER with gaps, obstacles and props) into 3D at a world offset. 1 tile = 1 m.
// World axes: x = east, z = south, y = up; a room's tile (0,0) corner sits at origin.
import { isDeadly, deathTrap } from './deathtrap.js';
import * as THREE from 'three';
import { Batcher, trs } from './assets.js';
import { cutout } from './cutout.js';
import { townStreet, furnish, interiorKind, interiorFloorKey, graveyard, isGraveyard, townHouse } from './terrain-town.js';
import { castleWalls, castleYard, zoneGates } from './terrain-castle.js';
import { drawFeatures, featureCells } from './terrain-features.js';
import { skirtPatches } from './skirt.js';
import { drowKind, drowDress, drowHallKind, bridgeCells, DROW_OPEN } from './terrain-drow.js';
import { interiorStyle, styleFloor, styleWall, dressInterior, STYLES } from './terrain-interiors.js';
import { underground, dressHall, outdoorEdge, outdoorDress, mountainCliffs, sunkenRuins, webDress, tinted, RUIN_RE, LOOK_GROUND, UNDERGROUND, SNOW_WOOD } from './terrain-looks.js';

export const ROOM_W = 24, ROOM_H = 15;
// the web words (room_looks.py LOOK_WORDS 'web'): two or more hang webs in a room of any look
const WEB_WORDS = /\b(webs?|webbed|webby|webbing|cobwebs?|cocoon\w*|egg ?sacs?|spider ?silk)\b/gi;
const webbed = layout => (`${layout.name || ''} ${layout.description || ''}`.match(WEB_WORDS) || []).length >= 2;
const FLOOR = 0, BLOCK = 1, WATER = 4;

const INDOOR = new Set(['inside', 'dungeon', 'cave', 'mine', 'crypt', 'sewer']);
export const isIndoor = theme => INDOOR.has(theme);
// stone floor and walls: interiors and dungeons, and town streets (walled, open sky)
// (caves and mines are rock, terrain-looks.js)
// a zone's stone (zone_tone.py) as a tint on the kit's grey: black basalt, white marble, red
// sandstone...
const TONE_STONE = {
  black: new THREE.Color(0.5, 0.5, 0.56), white: new THREE.Color(1.5, 1.47, 1.42), red: new THREE.Color(1.4, 0.92, 0.76),
  green: new THREE.Color(0.82, 1.12, 0.86), blue: new THREE.Color(0.86, 0.96, 1.32), gold: new THREE.Color(1.45, 1.22, 0.82),
  brown: new THREE.Color(1.08, 0.9, 0.74),
};
const PAVED = new Set(['inside', 'dungeon', 'crypt', 'sewer', 'city', 'castle', 'necropolis', 'drow', 'foundry']);
const CARD = { north: [0, -1], south: [0, 1], east: [1, 0], west: [-1, 0] };

// ---- deterministic noise (world-space, so neighbouring rooms join seamlessly) ----
function hash2(x, y) {
  let h = (Math.imul(x | 0, 374761393) + Math.imul(y | 0, 668265263)) | 0;
  h = Math.imul(h ^ (h >>> 13), 1274126177);
  return ((h ^ (h >>> 16)) >>> 0) / 4294967296;
}
function vnoise(x, y) {
  const xi = Math.floor(x), yi = Math.floor(y), xf = x - xi, yf = y - yi;
  const u = xf * xf * (3 - 2 * xf), v = yf * yf * (3 - 2 * yf);
  const a = hash2(xi, yi), b = hash2(xi + 1, yi), c = hash2(xi, yi + 1), d = hash2(xi + 1, yi + 1);
  return a + (b - a) * u + (c - a) * v + (a - b - c + d) * u * v;
}
const fbm = (x, y) => vnoise(x, y) * 0.55 + vnoise(x * 2.1 + 17, y * 2.1 - 9) * 0.3 + vnoise(x * 4.3 - 5, y * 4.3 + 3) * 0.15;

export const GROUND = {
  forest: { a: 0x45682f, b: 0x6a8f3e, path: 0x7b6343, wet: 0x2f4a32 },
  field: { a: 0x6f9445, b: 0x9bb65a, path: 0x8f7650, wet: 0x3c5a3a },
  hills: { a: 0x66874a, b: 0x8fa35e, path: 0x8a7352, wet: 0x3c5a3a },
  swamp: { a: 0x3f4b2c, b: 0x5a6436, path: 0x4c4130, wet: 0x26301f },
  desert: { a: 0xc9ab73, b: 0xdcc394, path: 0xb39062, wet: 0x8a6e48 },
  mountain: { a: 0x77746a, b: 0x8f8a7c, path: 0x6c6252, wet: 0x4a4c48 },
  default: { a: 0x5f7f44, b: 0x86a050, path: 0x85704e, wet: 0x3c5a3a },
  ...LOOK_GROUND,
};

// occluders get their own material copies with the see-through cut; floors keep theirs
const occCache = new WeakMap();
function occluder(mat) {
  if (Array.isArray(mat)) return mat.map(occluder);
  let m = occCache.get(mat);
  if (!m) { m = cutout.apply(mat.clone()); occCache.set(mat, m); }
  return m;
}
function asOccluder(model) {
  if (!model || model.occ) return model && model.occ;
  model.occ = { name: model.name + '#occ', box: model.box, parts: model.parts.map(p => ({ geometry: p.geometry, material: occluder(p.material) })) };
  return model.occ;
}

function runs(grid, W, H) {
  // maximal straight BLOCK runs along the four border lines (the room's walls)
  const out = [];
  const at = (x, y) => grid[y * W + x];
  for (const y of [0, H - 1]) {
    let x = 0;
    while (x < W) {
      if (at(x, y) !== BLOCK) { x++; continue; }
      const x0 = x; while (x < W && at(x, y) === BLOCK) x++;
      out.push({ horiz: true, line: y, a: x0, b: x - 1 });
    }
  }
  for (const x of [0, W - 1]) {
    let y = 1;
    while (y < H - 1) {
      if (at(x, y) !== BLOCK) { y++; continue; }
      const y0 = y; while (y < H - 1 && at(x, y) === BLOCK) y++;
      out.push({ horiz: false, line: x, a: y0, b: y - 1 });
    }
  }
  return out;
}

// `room` (optional) is the zone's room record: its exits place doors, passage markers
// and stairs. Returns the group, torch positions, door meshes and the geometries this
// room owns (to dispose when it is released).
export function buildRoom(layout, ox, oz, kits, room) {
  const { grid, W, H } = layout;
  // the drow city (terrain-drow.js): its tunnels are rock, the rest its own stone and spires
  const drowAs = layout.theme === 'drow' ? drowKind(layout, room) : null;
  const theme = drowAs === 'tunnel' ? 'cave' : layout.theme;
  const owned = [];
  const rng = MH.mulberry32((layout.vnum * 2246822519) ^ 0x3d);
  const group = new THREE.Group();
  group.name = `room_${layout.vnum}`;
  const torches = [];
  const ghostfires = [];    // a dead city's braziers: cold green flames, no warm light
  const b = new Batcher();
  const at = (x, y) => (x < 0 || y < 0 || x >= W || y >= H) ? BLOCK : grid[y * W + x];
  const D = kits.dungeon, N = kits.nature;

  // what the room's words say stands in it (terrain-features.js): its cells are drawn as open
  // floor (no wall or tree grows on them) and given back to the walkable grid as blocked after
  const featCells = featureCells(layout);
  for (const i of featCells) grid[i] = FLOOR;
  const ctx = () => ({ layout, ox, oz, kits, room, b, rng, runs: runs(grid, W, H), occ: asOccluder, torches, owned, group });
  if (UNDERGROUND.has(theme)) {
    // ---- caves and mines: rough rock ground, rock for walls (terrain-looks.js) ----
    groundSheet(layout, ox, oz, GROUND[theme], group, owned, { paths: theme === 'mine' });
    waterSurface(layout, ox, oz, group);
    underground(ctx(), theme);
    if (drowAs) drowDress(ctx(), drowAs);
  } else if (PAVED.has(theme)) {
    // (a dead city is a town's streets in black stone, terrain-town.js)
    const town = theme === 'city' || theme === 'necropolis', castle = theme === 'castle';
    const toneStone = layout.tone && TONE_STONE[layout.tone.stone];
    const drow = theme === 'drow', drowOpen = drow && DROW_OPEN.has(drowAs);
    // (a drow house is furnished only as a throne room or a temple; its other halls get statues,
    // crystals and faerie fire, terrain-drow.js)
    const kind = theme === 'inside' ? interiorKind(layout) : drow && !drowOpen ? drowHallKind(layout) : null;
    const abyss = drowAs === 'bridge' ? bridgeCells(layout) : null;
    // an interior in its zone's style: a castle's, a wizard's tower's, a cathedral's... (terrain-interiors.js)
    const style = interiorStyle(layout);
    const styleLit = style && STYLES[style].light != null;
    // ---- floor: KayKit stone tiles at 1 m ----
    for (let y = 0; y < H; y++) for (let x = 0; x < W; x++) {
      // under everything but the wall ring (obstacles stand ON the floor)
      if (at(x, y) === BLOCK && (x === 0 || y === 0 || x === W - 1 || y === H - 1)) continue;
      if (at(x, y) === WATER) continue;   // a sewer's channel (terrain-looks.js draws its water)
      if (abyss && !abyss.has(y * W + x)) continue;   // a drow bridge: nothing but the ways across
      const r = rng();
      const key = theme === 'necropolis' ? (r < 0.5 ? 'floor_tile_small_broken_A' : 'floor_tile_small')
        : drow ? (r < 0.12 ? 'floor_tile_small_broken_A' : 'floor_tile_small')
        : town ? (r < 0.1 ? 'floor_tile_small_weeds_A' : 'floor_tile_small_broken_A')
        : theme === 'sewer' ? (r < 0.35 ? 'floor_tile_small_weeds_A' : r < 0.55 ? 'floor_tile_small_broken_A' : 'floor_tile_small')
        : style ? styleFloor(style, r).key
        : (kind && interiorFloorKey(kind, r, layout.vnum))
        || (r < 0.07 ? 'floor_tile_small_broken_A' : r < 0.13 ? 'floor_tile_small_weeds_A' : 'floor_tile_small');
      // a dead city's paving is dark and grave-cold; a zone whose words say its stone is black,
      // white marble, red sandstone... has its floors in that stone (zone_tone.py)
      const tile = theme === 'necropolis' ? tinted(D.get(key), 0x6a6872, 'necro') : drow ? tinted(D.get(key), 0x4a4058, 'drow')
        : style && STYLES[style].tint ? tinted(D.get(key), STYLES[style].tint, `istyle_${style}`) : toneStone ? tinted(D.get(key), toneStone, `tone_${layout.tone.stone}`) : D.get(key);
      b.add(tile, trs(ox + x + 0.5, -0.05, oz + y + 0.5, Math.floor(rng() * 4) * Math.PI / 2, 0.5, 0.5, 0.5), { shadow: false });
    }
    // ---- walls: border runs as stretched KayKit wall pieces (in the zone's stone) ----
    const wall = asOccluder(drow ? tinted(D.get('wall'), 0x4a4060, 'drowwall') : style ? styleWall(D, style) : toneStone ? tinted(D.get('wall'), toneStone, `tone_${layout.tone.stone}`) : D.get('wall'));
    const WALL_H = 2.6;
    if (town && kits.town) townStreet(ctx());
    // a castle: tall walls with merlons, corner towers, gatehouses (terrain-castle.js)
    if (castle) castleWalls(ctx());
    for (const run of (town && kits.town) || castle || drowOpen ? [] : runs(grid, W, H)) {
      const L = run.b - run.a + 1;
      const n = Math.max(1, Math.round(L / 4)), w = L / n;
      for (let i = 0; i < n; i++) {
        const along = run.a + (i + 0.5) * w;
        const [x, z, yaw] = run.horiz ? [ox + along, oz + run.line + 0.5, 0] : [ox + run.line + 0.5, oz + along, Math.PI / 2];
        const piece = theme === 'dungeon' && rng() < 0.3 ? asOccluder(D.get('wall_broken')) || wall : wall;
        b.add(piece, trs(x, 0, z, yaw, w / 4, WALL_H / 4, 1));
      }
      // torches on the north wall, facing into the room, every ~6 m
      if (!town && !drow && !styleLit && run.horiz && run.line === 0 && L >= 4) {
        for (let tx = run.a + 2; tx <= run.b - 1; tx += 6) {
          if (at(tx, 1) === BLOCK) continue;
          b.add(D.get('torch_mounted'), trs(ox + tx + 0.5, 1.55, oz + 1.0, 0, 1), { shadow: false });
          torches.push(new THREE.Vector3(ox + tx + 0.5, 2.15, oz + 1.45));
        }
      }
    }
    // ---- interior obstacles (they block in the grid) ----
    if (kind && kits.furniture) furnish(ctx(), kind);
    if (style && kits.furniture) dressInterior(ctx(), style, kind);
    // a crypt's coffins and bones, a sewer's channel and pipes (terrain-looks.js)
    // the drow city's own dressing: spires, faerie fire, fungus, its landmarks (terrain-drow.js)
    if (drow) { drowDress(ctx(), drowAs); torches.length = 0; }   // (faerie fire, never warm torchlight)
    const dressed = castle ? (castleYard(ctx()), true) : drow || style ? true : !town && !kind && dressHall(ctx(), theme);
    for (const o of (kind && kits.furniture) || (town && kits.town) || dressed ? [] : layout.obstacles || []) {
      if (o.big) {
        const key = town ? ['crates_stacked', 'barrel_large', 'keg'][Math.floor(rng() * 3)]
          : theme === 'dungeon' && rng() < 0.4 ? 'rubble_large'
          : rng() < 0.55 ? 'pillar' : rng() < 0.5 ? 'crates_stacked' : 'barrel_large';
        const s = key === 'pillar' ? 1 : 0.9;
        b.add(asOccluder(D.get(key)), trs(ox + o.x + 1, 0, oz + o.y + 1, Math.floor(rng() * 4) * Math.PI / 2, s, key === 'pillar' ? 0.66 : s, s));
      } else {
        const key = ['barrel_small', 'box_large', 'column'][Math.floor(rng() * 3)];
        const s = key === 'box_large' ? 0.62 : key === 'column' ? 1.1 : 0.9;
        b.add(D.get(key), trs(ox + o.x + 0.5, 0, oz + o.y + 0.5, rng() * Math.PI * 2, s));
      }
    }
    // ---- decorative props (walk-through): small things only ----
    for (const p of (kind && kits.furniture) || (town && kits.town) || dressed ? [] : layout.props || []) {
      if (theme === 'necropolis') {
        // a brazier of cold green ghost-fire, or bones
        const G = kits.graveyard;
        if (rng() < 0.45) {
          b.add(D.get('torch_lit'), trs(ox + p.x + 0.5, 0.4, oz + p.y + 0.5, 0, 1.6), { shadow: false });
          ghostfires.push(new THREE.Vector3(ox + p.x + 0.5, 1.6, oz + p.y + 0.5));
        } else if (G) b.add(G.get(['bone_A', 'bone_B', 'bone_C', 'skull', 'candle_melted'][Math.floor(rng() * 5)]), trs(ox + p.x + 0.5, 0, oz + p.y + 0.5, rng() * 6.28, 0.9), { shadow: false });
        continue;
      }
      if (town) {
        // a standing torch lights the street
        if (rng() < 0.5) {
          b.add(D.get('torch_lit'), trs(ox + p.x + 0.5, 0.4, oz + p.y + 0.5, 0, 1.6), { shadow: false });
          torches.push(new THREE.Vector3(ox + p.x + 0.5, 1.6, oz + p.y + 0.5));
        } else b.add(D.get('barrel_small'), trs(ox + p.x + 0.5, 0, oz + p.y + 0.5, rng() * 6.28, 0.8));
        continue;
      }
      const key = ['candle_triple', 'candle_lit', 'coin_stack_large', 'candle_triple'][Math.floor(rng() * 4)];
      const s = key === 'coin_stack_large' ? 0.45 : 0.9;
      b.add(D.get(key), trs(ox + p.x + 0.5, 0, oz + p.y + 0.5, rng() * Math.PI * 2, s), { shadow: false });
    }
  } else {
    // ---- ground: one vertex-coloured sheet, noise in world space, dirt paths to exits ----
    groundSheet(layout, ox, oz, GROUND[theme] || GROUND.default, group, owned);
    waterSurface(layout, ox, oz, group);
    const midX = Math.floor(W / 2) + 0.5, midY = Math.floor(H / 2) + 0.5;
    const g = layout.gaps || {};

    // ---- a forest has trees standing in it, not only round its edge: single trunks scattered over
    // the open ground (BLOCK, so the hero walks round them), never on the ways through, the
    // middle, the stairs or where creatures stand ----
    const grove = new Set();
    // (a snowy wood too: the taiga, the Winterwood's paths)
    if (theme === 'forest' || (theme === 'snow' && SNOW_WOOD.test(`${layout.name || ''} ${layout.description || ''}`))) {
      const mx = Math.floor(W / 2), my = Math.floor(H / 2);
      const keep = (layout.spawnSlots || []).map(sp => [Math.floor(sp.x / 16), Math.floor(sp.y / 16)])
        .concat([layout.stairsUp, layout.stairsDown, ...(layout.portals || [])].filter(Boolean).map(t => [t.x, t.y]));
      const clear = (x, y) => ((g.north || g.south) && Math.abs(x - mx) <= 3) || ((g.east || g.west) && Math.abs(y - my) <= 2)
        || (Math.abs(x - mx) <= 2 && Math.abs(y - my) <= 2) || keep.some(([kx, ky]) => Math.abs(kx - x) <= 1 && Math.abs(ky - y) <= 1);
      for (let y = 2; y < H - 2; y++) for (let x = 2; x < W - 2; x++) {
        if (at(x, y) !== FLOOR || clear(x, y) || rng() > 0.1) continue;
        if ([[1, 0], [-1, 0], [0, 1], [0, -1], [1, 1], [-1, -1], [1, -1], [-1, 1]].some(([dx, dy]) => grove.has((y + dy) * W + x + dx))) continue;
        grid[y * W + x] = BLOCK;
        grove.add(y * W + x);
      }
    }

    // ---- the treeline: BLOCK cells become trees, bushes and rocks ----
    const depth = new Uint8Array(W * H).fill(255);
    const q = [];
    for (let i = 0; i < W * H; i++) if (grid[i] !== BLOCK) { depth[i] = 0; q.push(i); }
    for (let h = 0; h < q.length; h++) {
      const i = q[h], x = i % W, y = (i / W) | 0;
      for (const [dx, dy] of [[1, 0], [-1, 0], [0, 1], [0, -1], [1, 1], [-1, -1], [1, -1], [-1, 1]]) {
        const xx = x + dx, yy = y + dy;
        if (xx < 0 || yy < 0 || xx >= W || yy >= H) continue;
        const j = yy * W + xx;
        if (depth[j] > depth[i] + 1) { depth[j] = depth[i] + 1; q.push(j); }
      }
    }
    // a look's own edge (terrain-looks.js: frosted pines, scorched trees, bare sand), else the wilds'
    const edge = outdoorEdge(theme, kits, layout);
    const trees = edge ? edge.trees.filter(Boolean) : theme === 'swamp' ? ['DeadTree_1', 'DeadTree_2', 'Pine_1'].map(k => N.get(k)) :
      ['CommonTree_1', 'CommonTree_2', 'CommonTree_3', 'CommonTree_1', 'Pine_1', 'Pine_2'].map(k => N.get(k));
    const treeP = edge ? edge.treeP : theme === 'forest' ? 0.78 : theme === 'swamp' ? 0.3 : 0.22;
    const bare = !!edge;   // no bushes, ferns or grass
    for (let y = 0; y < H; y++) for (let x = 0; x < W; x++) {
      if (at(x, y) !== BLOCK || (edge && edge.cliffs)) continue;     // a mountain's cliffs: below
      const dd = depth[y * W + x];
      const jx = (rng() - 0.5) * 0.6, jz = (rng() - 0.5) * 0.6;
      const px = ox + x + 0.5 + jx, pz = oz + y + 0.5 + jz, yaw = rng() * Math.PI * 2;
      const r = rng();
      if (grove.has(y * W + x) && trees.length) {
        // a trunk standing in the wood
        const tree = trees[Math.floor(rng() * trees.length)];
        b.add(asOccluder(tree), trs(ox + x + 0.5, 0, oz + y + 0.5, yaw, 0.5 + rng() * 0.25));
      } else if ((dd >= 2 || (theme === 'forest' && dd >= 1)) && trees.length && r < treeP) {
        const tree = trees[Math.floor(rng() * trees.length)];
        b.add(asOccluder(tree), trs(px, 0, pz, yaw, 0.55 + rng() * 0.3));
      } else if (dd <= 2 && edge && edge.near) {
        // a place's own edge: a village's bushes and fences, a garden's hedges, a camp's stakes
        if (r < 0.7) { const m = edge.near(rng); if (m && m.model) b.add(asOccluder(m.model), trs(px, 0, pz, m.yaw === undefined ? yaw : m.yaw, m.s)); }
      } else if (dd <= 2 && r < 0.62) {
        const rr = rng();
        const key = bare || rr < 0.18 ? `Rock_Medium_${1 + Math.floor(rng() * 3)}` : rr < 0.8 ? 'Bush_Common' : 'Bush_Common_Flowers';
        const s = key.startsWith('Rock') ? 0.45 + rng() * 0.3 : 0.75 + rng() * 0.4;
        b.add(asOccluder(edge && key.startsWith('Rock') ? edge.rock(key) : N.get(key)), trs(px, 0, pz, yaw, s));
      } else if (bare) {
        continue;
      } else if (r < 0.85) {
        b.add(N.get('Fern_1'), trs(px, 0, pz, yaw, 0.7 + rng() * 0.4), { shadow: false });
      }
    }
    // obstacles inside the room: boulders and thickets
    for (const o of layout.obstacles || []) {
      const cx = ox + o.x + (o.big ? 1 : 0.5), cz = oz + o.y + (o.big ? 1 : 0.5);
      const key = bare || rng() < 0.6 ? `Rock_Medium_${1 + Math.floor(rng() * 3)}` : 'Bush_Common';
      const s = o.big ? 0.75 : 0.42;
      b.add(asOccluder(edge && key.startsWith('Rock') ? edge.rock(key) : N.get(key)), trs(cx, 0, cz, rng() * Math.PI * 2, key === 'Bush_Common' ? s * 1.6 : s));
    }
    // ground clutter on open floor (not on the paths): a look's own (terrain-looks.js), or grass
    if (edge && edge.cliffs) mountainCliffs(ctx(), theme === 'snow');
    if (theme === 'underwater' && RUIN_RE.test(layout.name || (room && room.data && room.data.name) || '')) sunkenRuins(ctx());
    if (theme === 'web') webDress(ctx());
    if (bare || theme === 'desert') outdoorDress(ctx(), theme);
    else {
      for (let y = 1; y < H - 1; y++) for (let x = 1; x < W - 1; x++) {
        if (at(x, y) !== FLOOR) continue;
        const onPath = (g.north || g.south) && Math.abs(x + 0.5 - midX) < 2 || (g.east || g.west) && Math.abs(y + 0.5 - midY) < 2;
        const r = rng();
        const px = ox + x + 0.2 + rng() * 0.6, pz = oz + y + 0.2 + rng() * 0.6, yaw = rng() * 6.28;
        if (onPath) { if (r < 0.06) b.add(N.get('Pebble_Round_1'), trs(px, 0, pz, yaw, 1.4), { shadow: false }); continue; }
        if (r < 0.26) b.add(N.get(rng() < 0.7 ? 'Grass_Common_Short' : 'Grass_Wispy_Tall'), trs(px, 0, pz, yaw, 0.7 + rng() * 0.4), { shadow: false });
        else if (r < 0.31) b.add(N.get('Clover_1'), trs(px, 0, pz, yaw, 0.8), { shadow: false });
        else if (r < 0.34) b.add(N.get(rng() < 0.5 ? 'Flower_3_Group' : 'Flower_4_Group'), trs(px, 0, pz, yaw, 0.6), { shadow: false });
        else if (r < 0.35) b.add(N.get('Mushroom_Common'), trs(px, 0, pz, yaw, 0.9), { shadow: false });
      }
    }
  }

  // the country beyond the room's edge where the zone map has no room: no void
  if (!PAVED.has(theme) && !UNDERGROUND.has(theme) && room && room.zoneRef) fillerLand(ctx(), theme);
  // a town's empty cells: more town (cobbles and roofs), not the sky showing through (owner: "the
  // town isn't seamless")
  else if ((theme === 'city' || theme === 'castle') && room && room.zoneRef && kits.town) fillerLand(ctx(), 'town');
  if (!PAVED.has(theme) && kits.graveyard && isGraveyard(layout)) graveyard(ctx());
  // a death trap: a ledge round a burning abyss, bones, skulls on poles at the ways in (deathtrap.js)
  if (room && isDeadly(room.data ? room.data.flags : room.flags)) deathTrap(ctx());
  // a webbed room or cave (the spider queens' dens, a cellar thick with cobweb): its webs hung in it
  if (theme !== 'web' && webbed(layout)) webDress(ctx(), { indoor: true });
  // a way into another region: a named stone gateway (terrain-castle.js)
  if (room) zoneGates(ctx(), theme);
  drawFeatures(ctx());
  // a set piece's own light (setpieces.py): a glow of its colour over the room
  if (layout.setpiece && layout.setpiece.light) {
    const l = new THREE.PointLight(new THREE.Color(layout.setpiece.light), 34, 18, 1.4);
    l.position.set(ox + W / 2, 3.4, oz + H / 2);
    group.add(l);
  }
  for (const i of featCells) grid[i] = BLOCK;
  b.build(group);
  const doors = room ? exitFeatures(group, layout, ox, oz, room, kits, owned) : {};
  // flames: tiny HDR spheres so the bloom pass picks them up
  for (const t of torches) {
    const f = new THREE.Mesh(FLAME_GEO, FLAME_MAT);
    f.position.copy(t).add(new THREE.Vector3(0, -0.05, -0.12));
    group.add(f);
  }
  for (const t of ghostfires) {
    const f = new THREE.Mesh(FLAME_GEO, GHOST_FLAME_MAT);
    f.position.copy(t).add(new THREE.Vector3(0, -0.05, -0.12));
    f.scale.setScalar(1.4);
    group.add(f);
  }
  return { group, torches, layout, ox, oz, doors, owned };
}

// the open ground: one vertex-coloured sheet, noise in world space, dirt paths from the middle
// out through each way out (no paths: a cave's floor is rock all over), darker under the edge
function groundSheet(layout, ox, oz, pal, group, owned, { paths = true } = {}) {
  const { grid, W, H } = layout;
  const at = (x, y) => (x < 0 || y < 0 || x >= W || y >= H) ? BLOCK : grid[y * W + x];
  const SEG = 2;
  const geo = new THREE.PlaneGeometry(W, H, W * SEG, H * SEG);
  geo.rotateX(-Math.PI / 2);
  geo.translate(ox + W / 2, 0, oz + H / 2);
  const pos = geo.attributes.position;
  const col = new Float32Array(pos.count * 3);
  const cA = new THREE.Color(pal.a), cB = new THREE.Color(pal.b), cP = new THREE.Color(pal.path), cW = new THREE.Color(pal.wet);
  const c = new THREE.Color();
  const midX = Math.floor(W / 2) + 0.5, midY = Math.floor(H / 2) + 0.5;
  const g = layout.gaps || {};
  for (let i = 0; i < pos.count; i++) {
    const wx = pos.getX(i), wz = pos.getZ(i);
    const lx = wx - ox, lz = wz - oz;
    const n = fbm(wx * 0.18, wz * 0.18);
    c.copy(cA).lerp(cB, THREE.MathUtils.smoothstep(n, 0.3, 0.75));
    if (paths) {
      let d = 99;
      if (g.north && lz <= midY) d = Math.min(d, Math.abs(lx - midX));
      if (g.south && lz >= midY) d = Math.min(d, Math.abs(lx - midX));
      if (g.west && lx <= midX) d = Math.min(d, Math.abs(lz - midY));
      if (g.east && lx >= midX) d = Math.min(d, Math.abs(lz - midY));
      d = Math.min(d, Math.hypot(lx - midX, lz - midY) - 1.2);
      const pw = (1 - THREE.MathUtils.smoothstep(d + (n - 0.5) * 1.6, 0.6, 1.9)) * 0.85;
      if (pw > 0) c.lerp(cP, pw);
    }
    // darken under the treeline (or the rock) and around water
    // (vertices on the far edges belong to the last tile, not the void beyond it)
    const tx = Math.min(W - 1, Math.floor(lx)), ty = Math.min(H - 1, Math.floor(lz));
    if (at(tx, ty) === BLOCK) c.multiplyScalar(0.72);
    if (at(tx, ty) === WATER) c.lerp(cW, 0.8);
    col[i * 3] = c.r; col[i * 3 + 1] = c.g; col[i * 3 + 2] = c.b;
    pos.setY(i, (n - 0.5) * 0.12 - (at(tx, ty) === WATER ? 0.35 : 0));
  }
  geo.setAttribute('color', new THREE.BufferAttribute(col, 3));
  geo.computeVertexNormals();
  owned.push(geo);
  const ground = new THREE.Mesh(geo, GROUND_MAT);
  ground.receiveShadow = true;
  group.add(ground);
}

function waterSurface(layout, ox, oz, group) {
  const { grid, W, H } = layout;
  const wq = [];
  for (let y = 0; y < H; y++) for (let x = 0; x < W; x++) if (grid[y * W + x] === WATER) wq.push([x, y]);
  if (!wq.length) return;
  const wm = new THREE.InstancedMesh(WATER_GEO, WATER_MAT, wq.length);
  wq.forEach(([x, y], i) => wm.setMatrixAt(i, trs(ox + x + 0.5, -0.12, oz + y + 0.5, 0, 1.02)));
  wm.receiveShadow = true;
  group.add(wm);
}

// ---- filler: the country beyond a room's edge where the zone map has no room ----
// Half-way into each empty neighbouring cell (so two rooms facing one empty cell fill it between
// them), and the corner between two empty sides: a ground skirt in the room's palette (the same
// world-space noise, so it joins the room's ground) with that country's trees, rocks or water.
// Scenery only: the cell stays blocked (zone.js), so nothing here needs collision.
const FILL = {
  forest: { trees: 0.2, bushes: 0.05, rocks: 0.01, grass: 0.06 },
  darkforest: { trees: 0.2, bushes: 0.05, rocks: 0.01, grass: 0.05 },
  web: { trees: 0.22, bushes: 0, rocks: 0.01, grass: 0 },
  field: { trees: 0.025, bushes: 0.035, rocks: 0.008, grass: 0.1 },
  hills: { trees: 0.04, bushes: 0.04, rocks: 0.03, grass: 0.08 },
  mountain: { trees: 0.02, bushes: 0, rocks: 0.13, grass: 0, cliff: true },
  desert: { trees: 0, bushes: 0, rocks: 0.02, grass: 0 },
  snow: { trees: 0.09, bushes: 0, rocks: 0.03, grass: 0 },
  swamp: { trees: 0.06, bushes: 0.03, rocks: 0, grass: 0.1 },
  volcanic: { trees: 0.03, bushes: 0, rocks: 0.07, grass: 0 },
  stones: { trees: 0.02, bushes: 0, rocks: 0.03, grass: 0.08 },
  village: { trees: 0.035, bushes: 0.04, rocks: 0.005, grass: 0.08 },
  camp: { trees: 0.03, bushes: 0.02, rocks: 0.01, grass: 0.05 },
  garden: { trees: 0.05, bushes: 0.08, rocks: 0, grass: 0.1 },
  terrace: { trees: 0.015, bushes: 0.01, rocks: 0, grass: 0 },
  ruins: { trees: 0.025, bushes: 0.02, rocks: 0.02, grass: 0.08 },
  shore: { water: true },
  water_swim: { water: true },
  water_noswim: { water: true },
  default: { trees: 0.03, bushes: 0.04, rocks: 0.01, grass: 0.08 },
  town: { houses: true },
};
function fillerLand(c, theme) {
  const { layout, ox, oz, kits, b, rng, occ, owned, group, room } = c;
  const { W, H } = layout;
  const N = kits.nature;
  const cells = room.zoneRef.cells;
  const empty = (dx, dy) => !cells.get(`${room.cx + dx},${room.cy + dy}`);
  const spec = FILL[theme] || FILL.default;
  const pal = GROUND[theme === 'town' ? 'city' : theme] || GROUND.default;
  const edge = outdoorEdge(theme, kits, layout);
  const trees = (edge ? edge.trees : theme === 'swamp' ? ['DeadTree_1', 'DeadTree_2'].map(k => N.get(k))
    : ['CommonTree_1', 'CommonTree_2', 'CommonTree_3', 'Pine_1', 'Pine_2'].map(k => N.get(k))).filter(Boolean);
  const rockOf = k => edge && edge.rock ? edge.rock(k) : N.get(k);
  // the empty cells round the room to fill, and how far (skirt.js)
  const patches = skirtPatches({ ox, oz, W, H, wild: !!room.zoneRef.wild, empty });
  if (!patches.length) return;
  const cA = new THREE.Color(pal.a), cB = new THREE.Color(pal.b), col = new THREE.Color();
  for (const [x0, z0, w, d, axis, sign, [bx, bz, bw, bd]] of patches) {
    // how far out from the room a point lies (0 at its edge, 1 at the patch's far edge), on the
    // whole patch this piece is cut from (skirt.js: where it meets another room's land)
    const outAt = (px, pz) => axis === 'z' ? (sign < 0 ? (bz + bd - pz) / bd : (pz - bz) / bd) : axis === 'x' ? (sign < 0 ? (bx + bw - px) / bw : (px - bx) / bw) : 1;
    if (spec.water) {
      const m = new THREE.Mesh(WATER_GEO, WATER_MAT);
      m.scale.set(w, 1, d); m.position.set(x0 + w / 2, -0.12, z0 + d / 2);
      group.add(m);
      continue;
    }
    // the ground skirt (a mountain's rises away from the room)
    const geo = new THREE.PlaneGeometry(w, d, Math.ceil(w), Math.ceil(d));
    geo.rotateX(-Math.PI / 2);
    geo.translate(x0 + w / 2, 0, z0 + d / 2);
    const pos = geo.attributes.position, arr = new Float32Array(pos.count * 3);
    for (let i = 0; i < pos.count; i++) {
      const wx = pos.getX(i), wz = pos.getZ(i);
      const n = fbm(wx * 0.18, wz * 0.18);
      col.copy(cA).lerp(cB, THREE.MathUtils.smoothstep(n, 0.3, 0.75)).multiplyScalar(0.92);
      arr[i * 3] = col.r; arr[i * 3 + 1] = col.g; arr[i * 3 + 2] = col.b;
      const out = outAt(wx, wz);
      pos.setY(i, (n - 0.5) * 0.12 - 0.02 + (spec.cliff ? out * out * 2.5 : 0));
    }
    geo.setAttribute('color', new THREE.BufferAttribute(arr, 3));
    geo.computeVertexNormals();
    owned.push(geo);
    const ground = new THREE.Mesh(geo, GROUND_MAT);
    ground.receiveShadow = true;
    group.add(ground);
    // a town: blocks of houses, roofs to the edge of sight, a tree here and there
    if (spec.houses) {
      for (let gz = z0 + 3.5; gz < z0 + d - 1; gz += 7) for (let gx = x0 + 3.5; gx < x0 + w - 1; gx += 7) {
        if (rng() < 0.1) {
          const tree = kits.town.get(rng() < 0.5 ? 'tree_single_A' : 'trees_A_medium');
          if (tree) b.add(tree, trs(gx, 0, gz, rng() * 6.28, 2.8), { shadow: false });
          continue;
        }
        const house = townHouse(kits, room, rng);
        if (house) b.add(occ(house), trs(gx + (rng() - 0.5), 0, gz + (rng() - 0.5), Math.floor(rng() * 4) * Math.PI / 2, 5.2 + rng() * 0.8), { shadow: false });
      }
      continue;
    }
    // what grows there, on a jittered grid so it doesn't clump
    const area = w * d, step = 1.0;
    for (let gz = z0 + 0.5; gz < z0 + d; gz += step) for (let gx = x0 + 0.5; gx < x0 + w; gx += step) {
      const px = gx + (rng() - 0.5) * 0.9, pz = gz + (rng() - 0.5) * 0.9, yaw = rng() * 6.28;
      const out = outAt(px, pz);
      const y = spec.cliff ? out * out * 2.5 : 0;
      const r = rng();
      // thinner the further out (beyond the fog's reach it is only a haze anyway)
      let acc = (spec.trees || 0) * (1 - 0.65 * Math.min(1, out));
      if (r < acc && trees.length) { b.add(occ(trees[Math.floor(rng() * trees.length)]), trs(px, y, pz, yaw, 0.55 + rng() * 0.35), { shadow: false }); continue; }
      acc += spec.rocks || 0;
      if (r < acc) {
        const big = spec.cliff ? 1.4 + rng() * 1.6 + out * 1.5 : 0.35 + rng() * 0.35;
        b.add(occ(rockOf(`Rock_Medium_${1 + Math.floor(rng() * 3)}`)), trs(px, y - 0.1, pz, yaw, big), { shadow: false });
        continue;
      }
      acc += spec.bushes || 0;
      if (r < acc) { b.add(N.get(rng() < 0.75 ? 'Bush_Common' : 'Bush_Common_Flowers'), trs(px, y, pz, yaw, 0.7 + rng() * 0.4), { shadow: false }); continue; }
      acc += spec.grass || 0;
      if (r < acc) b.add(N.get(rng() < 0.7 ? 'Grass_Common_Short' : 'Grass_Wispy_Tall'), trs(px, y, pz, yaw, 0.7 + rng() * 0.4), { shadow: false });
    }
  }
}

// ---- exits: doors in their doorways, glowing markers on passages, stairs and trapdoors ----
// Doors of shared openings are built by the room on the south/east side (one mesh per
// doorway); a door on a passage (a doorway whose rooms don't sit side by side) stands in
// this room's gap; a door on stairs is a trapdoor hatch over them. Every door mesh has
// userData.setOpen(open) and userData.setLocked(locked) (zone.setDoor drives both).
function exitFeatures(group, layout, ox, oz, room, kits, owned) {
  const doors = {};
  const zone = room.zoneRef;
  const where = e => {
    const t = zone && zone.rooms.get(e.to);
    if (t) return t.name;
    return e.kind === 'zone' ? (e.zoneName || e.toName || 'another region') : 'onward';
  };
  for (const [dir, e] of Object.entries(room.data.exits)) {
    const g = layout.gaps[dir];
    if (CARD[dir] && g) {
      const horiz = dir === 'north' || dir === 'south';
      const a = horiz ? g.x0 : g.y0, bnd = horiz ? g.x1 + 1 : g.y1 + 1;
      const mid = (a + bnd) / 2, span = bnd - a;
      // the boundary line of this side of the room
      const edge = dir === 'north' ? 0 : dir === 'south' ? ROOM_H : dir === 'west' ? 0 : ROOM_W;
      const [x, z] = horiz ? [ox + mid, oz + edge] : [ox + edge, oz + mid];
      const info = room.doors[dir];
      if (e.door && (e.kind !== 'open' || dir === 'south' || dir === 'east')) {
        const d = makeDoor(span, horiz);
        d.position.set(x, 0, z);
        group.add(d);
        doors[dir] = d;
      }
      if (e.kind !== 'open') {
        const zoneExit = e.kind === 'zone';
        const inward = horiz ? (dir === 'north' ? 0.35 : -0.35) : (dir === 'west' ? 0.35 : -0.35);
        // into another region: a gold glow under its gateway. Within the zone the path simply runs
        // on (owner: "some of the rooms are not seamless"): no sheet of mist, just its name
        const m = zoneExit ? new THREE.Mesh(CURTAIN_GEO, CURTAIN_GOLD) : new THREE.Object3D();
        m.scale.set(span, 1, 1);
        m.position.set(horiz ? x : x + inward, 1.25, horiz ? z + inward : z);
        if (!horiz) m.rotation.y = Math.PI / 2;
        group.add(m);
        const label = `↗ ${where(e)}`;
        const sp = labelSprite(label, zoneExit ? '#ffd88a' : '#cfe6ff', owned);
        // well inside its own room: the room across the edge may sign its way back on the same
        // edge, and the two signs must not lie on top of each other
        sp.position.set(horiz ? x : x + inward * 4, zoneExit ? 2.9 : 1.6, horiz ? z + inward * 4 : z);
        group.add(sp);
        // a closed door hides the glow behind it
        if (doors[dir]) {
          const setOpen = doors[dir].userData.setOpen;
          doors[dir].userData.setOpen = open => { setOpen(open); m.visible = open; };
        }
      }
      if (doors[dir] && info) {
        doors[dir].userData.setOpen(!info.closed);
        doors[dir].userData.setLocked(!!(info.closed && info.locked));
      }
    }
  }
  for (const [key, t] of [['up', layout.stairsUp], ['down', layout.stairsDown]]) {
    if (!t) continue;
    const cx = ox + t.x + 0.5, cz = oz + t.y + 0.5;
    const e = room.data.exits[key];
    if (key === 'up') {
      // the KayKit staircase climbs toward its -z; turned so the bottom step faces west (into
      // the room, where you arrive) and centred on the stairs tile
      const st = kits.dungeon.get('stairs');
      const sc = 0.4;
      if (st) for (const p of st.parts) {
        const mesh = new THREE.Mesh(p.geometry, p.material);
        mesh.applyMatrix4(trs(cx + 2.0 * sc, 0, cz, -Math.PI / 2, sc));
        mesh.castShadow = mesh.receiveShadow = true;
        group.add(mesh);
      }
    } else {
      group.add(stairwell(cx, cz));
    }
    if (e && e.door) {
      const h = makeHatch(key, cx, cz);
      group.add(h);
      doors[key] = h;
      const info = room.doors[key];
      if (info) { h.userData.setOpen(!info.closed); h.userData.setLocked(!!(info.closed && info.locked)); }
    }
    // into another region the arch over the stairs carries its name (terrain-castle zoneGates):
    // the label just says which way, low in the arch's mouth, clear of the plaque
    const zoneExit = e && e.kind === 'zone';
    const sp = labelSprite(`${key === 'up' ? '▲ Up' : '▼ Down'}${e && !zoneExit ? ` · ${where(e)}` : ''}`, zoneExit ? '#ffd88a' : '#e8e2c8', owned);
    sp.position.set(cx, zoneExit ? 1.8 : key === 'up' ? 2.9 : 2.2, cz);
    group.add(sp);
  }
  for (const pt of layout.portals || []) {
    const ring = new THREE.Mesh(PORTAL_GEO, PORTAL_MAT);
    ring.rotation.x = -Math.PI / 2;
    ring.position.set(ox + pt.x + 0.5, 0.06, oz + pt.y + 0.5);
    group.add(ring);
    const sp = labelSprite(`✦ ${pt.name}`, '#e6d0ff', owned);
    sp.position.set(ox + pt.x + 0.5, 2.2, oz + pt.y + 0.5);
    group.add(sp);
  }
  return doors;
}

// a way down: a dark opening in the floor with a stone rim and steps fading into the dark
// (it descends westward, away from where you arrive)
function stairwell(cx, cz) {
  const g = new THREE.Group();
  const W = 1.7, D = 2.0;
  const hole = new THREE.Mesh(PLANE_GEO, WELL_MAT);
  hole.scale.set(D, W, 1);
  hole.rotation.x = -Math.PI / 2;
  hole.position.set(cx, 0.012, cz);
  hole.renderOrder = 2;
  g.add(hole);
  for (let i = 0; i < 4; i++) {
    const step = new THREE.Mesh(STEP_GEO, STEP_MATS[i]);
    step.scale.set(D / 4 * 0.92, 1, W * 0.9);
    step.position.set(cx + D / 2 - (i + 0.5) * D / 4, 0.014 + 0.001 * i, cz);
    step.renderOrder = 3;
    g.add(step);
  }
  for (const [x, z, sx, sz] of [[cx, cz - W / 2 - 0.07, D + 0.28, 0.14], [cx, cz + W / 2 + 0.07, D + 0.28, 0.14], [cx - D / 2 - 0.07, cz, 0.14, W]]) {
    const rim = new THREE.Mesh(RIM_GEO, RIM_MAT);
    rim.scale.set(sx, 1, sz);
    rim.position.set(x, 0.06, z);
    rim.castShadow = rim.receiveShadow = true;
    g.add(rim);
  }
  return g;
}

// a plank door (double for wide openings) that swings open on its hinges; locked, it shows
// iron bands and a padlock
function makeDoor(span, horiz) {
  const g = new THREE.Group();
  const leaves = span > 5.5 ? 2 : 1, w = span / leaves;
  const parts = [], lockBits = [];
  for (let i = 0; i < leaves; i++) {
    const hinge = new THREE.Group();
    const along = -span / 2 + (i === 0 ? 0 : span);
    const leaf = new THREE.Mesh(DOOR_GEO, occluder(DOOR_MAT));          // see-through when in the way
    leaf.scale.set(w, 1, 1);
    leaf.position.x = i === 0 ? w / 2 : -w / 2;
    leaf.castShadow = leaf.receiveShadow = true;
    hinge.add(leaf);
    for (const y of [0.55, 1.85]) {
      const band = new THREE.Mesh(BAND_GEO, occluder(IRON_MAT));
      band.scale.set(w * 0.96, 1, 1);
      band.position.set(leaf.position.x, y, 0);
      hinge.add(band);
      lockBits.push(band);
    }
    if (i === 0) {
      const lock = new THREE.Mesh(LOCK_GEO, occluder(LOCK_MAT));
      lock.position.set(leaves === 2 ? w - 0.12 : w - 0.28, 1.15, 0);
      hinge.add(lock);
      lockBits.push(lock);
    }
    hinge.position.x = along;
    g.add(hinge);
    parts.push({ hinge, sign: i === 0 ? 1 : -1 });
  }
  if (!horiz) g.rotation.y = Math.PI / 2;
  g.userData.open = true;
  g.userData.setOpen = open => { g.userData.open = open; for (const p of parts) p.hinge.rotation.y = open ? p.sign * -1.45 : 0; };
  g.userData.setLocked = locked => { for (const b of lockBits) b.visible = !!locked; };
  g.userData.setLocked(false);
  return g;
}

// a trapdoor over stairs: flat on the floor over the way down, or a lid at the top of the
// way up; it swings up on a hinge along its west edge
function makeHatch(key, cx, cz) {
  const g = new THREE.Group();
  const W = key === 'down' ? 1.8 : 1.5, D = key === 'down' ? 2.1 : 1.2;
  const hinge = new THREE.Group();
  const lid = new THREE.Mesh(HATCH_GEO, DOOR_MAT);
  lid.scale.set(D, 1, W);
  lid.position.x = D / 2;
  lid.castShadow = lid.receiveShadow = true;
  hinge.add(lid);
  const lockBits = [];
  for (const z of [-W * 0.3, W * 0.3]) {
    const band = new THREE.Mesh(BAND_GEO, IRON_MAT);
    band.scale.set(D * 0.96, 0.6, 0.8);
    band.rotation.x = Math.PI / 2;
    band.position.set(D / 2, 0.06, z);
    hinge.add(band);
    lockBits.push(band);
  }
  const lock = new THREE.Mesh(LOCK_GEO, LOCK_MAT);
  lock.rotation.x = -Math.PI / 2;
  lock.position.set(D - 0.2, 0.08, 0);
  hinge.add(lock);
  lockBits.push(lock);
  // the up hatch sits at the top of the staircase (whose top is its east end)
  hinge.position.set(key === 'down' ? cx - D / 2 : cx + 0.15, key === 'down' ? 0.03 : 2.05, cz);
  g.add(hinge);
  g.userData.open = true;
  g.userData.setOpen = open => { g.userData.open = open; hinge.rotation.z = open ? 1.75 : 0; };
  g.userData.setLocked = locked => { for (const b of lockBits) b.visible = !!locked; };
  g.userData.setLocked(false);
  return g;
}

// where the hero stands and whether it is fighting (main.js sets them each frame): a passage's
// name is clear near the hero and faint far off, and steps back during a fight (it was sitting on
// top of the numbers over the hero) unless the hero stands at that very exit
export const LABEL_FADE = { hero: new THREE.Vector3(), combat: false, on: false };
const _lp = new THREE.Vector3();
function labelOpacity(sp) {
  if (!LABEL_FADE.on) return 1;
  const d = sp.getWorldPosition(_lp).setY(0).distanceTo(LABEL_FADE.hero);
  const far = d <= 8 ? 1 : d >= 18 ? 0.18 : 1 - 0.82 * (d - 8) / 10;
  return LABEL_FADE.combat && d > 4 ? Math.min(far, 0.22) : far;
}

// a passage's name over it, in the HUD's style: engraved capitals on dark glass, a gilded
// hairline, a diamond at each end (drawn at twice the size for crisp edges)
function labelSprite(text, color, owned) {
  const c = document.createElement('canvas');
  const ctx = c.getContext('2d');
  const K = 2, H = 46 * K, font = `600 ${27 * K}px Cinzel, Georgia, serif`;
  ctx.font = font;
  const w = Math.ceil(ctx.measureText(text).width) + 64 * K;
  c.width = w; c.height = H;
  const g = ctx.createLinearGradient(0, 0, 0, H);
  g.addColorStop(0, 'rgba(22,28,40,0.82)'); g.addColorStop(1, 'rgba(8,10,16,0.82)');
  ctx.fillStyle = g;
  ctx.beginPath(); ctx.roundRect(K, K, w - 2 * K, H - 2 * K, 12 * K); ctx.fill();
  ctx.strokeStyle = 'rgba(216,180,106,0.75)'; ctx.lineWidth = 1.5 * K;
  ctx.beginPath(); ctx.roundRect(K * 2, K * 2, w - 4 * K, H - 4 * K, 11 * K); ctx.stroke();
  ctx.fillStyle = '#f6dfa2';
  for (const x of [15 * K, w - 15 * K]) { ctx.beginPath(); ctx.moveTo(x, H / 2 - 5 * K); ctx.lineTo(x + 5 * K, H / 2); ctx.lineTo(x, H / 2 + 5 * K); ctx.lineTo(x - 5 * K, H / 2); ctx.closePath(); ctx.fill(); }
  ctx.font = font; ctx.fillStyle = color; ctx.textBaseline = 'middle'; ctx.textAlign = 'center';
  ctx.shadowColor = 'rgba(0,0,0,0.9)'; ctx.shadowBlur = 4 * K;
  ctx.fillText(text, w / 2, H / 2 + K);
  const tex = new THREE.CanvasTexture(c);
  tex.colorSpace = THREE.SRGBColorSpace;
  owned.push(tex);
  const sp = new THREE.Sprite(new THREE.SpriteMaterial({ map: tex, depthWrite: false, transparent: true }));
  sp.scale.set(w / H * 0.62, 0.62, 1);
  sp.renderOrder = 5;
  // eased toward how clear it should be, each time it is drawn
  sp.onBeforeRender = () => { const m = sp.material; m.opacity += (labelOpacity(sp) - m.opacity) * 0.15; };
  return sp;
}

function curtainTexture() {
  const c = document.createElement('canvas');
  c.width = 4; c.height = 64;
  const ctx = c.getContext('2d');
  const g = ctx.createLinearGradient(0, 0, 0, 64);
  g.addColorStop(0, 'rgba(255,255,255,0)');
  g.addColorStop(0.55, 'rgba(255,255,255,0.35)');
  g.addColorStop(1, 'rgba(255,255,255,0.9)');
  ctx.fillStyle = g; ctx.fillRect(0, 0, 4, 64);
  const t = new THREE.CanvasTexture(c);
  return t;
}
const CURTAIN_TEX = curtainTexture();
const CURTAIN_GEO = new THREE.PlaneGeometry(1, 2.5);
const curtain = color => new THREE.MeshBasicMaterial({ color, map: CURTAIN_TEX, transparent: true, depthWrite: false,
  blending: THREE.AdditiveBlending, side: THREE.DoubleSide });
// a zone's border: a gold glow under its gateway (a passage within the zone has no sheet at all:
// the owner wants the rooms seamless)
const CURTAIN_GOLD = curtain(new THREE.Color(1.8, 1.25, 0.45));
const PORTAL_GEO = new THREE.RingGeometry(0.55, 0.85, 32);
const PORTAL_MAT = new THREE.MeshBasicMaterial({ color: new THREE.Color(1.6, 0.9, 2.4), transparent: true, opacity: 0.85,
  blending: THREE.AdditiveBlending, depthWrite: false });
const DOOR_GEO = new THREE.BoxGeometry(1, 2.4, 0.18).translate(0, 1.2, 0);
const BAND_GEO = new THREE.BoxGeometry(1, 0.1, 0.24);
const LOCK_GEO = new THREE.BoxGeometry(0.2, 0.26, 0.3);
const HATCH_GEO = new THREE.BoxGeometry(1, 0.09, 1).translate(0, 0.045, 0);
const PLANE_GEO = new THREE.PlaneGeometry(1, 1);
const STEP_GEO = new THREE.PlaneGeometry(1, 1).rotateX(-Math.PI / 2);
const RIM_GEO = new THREE.BoxGeometry(1, 0.12, 1);
const IRON_MAT = new THREE.MeshStandardMaterial({ color: 0x2c2c30, roughness: 0.55, metalness: 0.7 });
const LOCK_MAT = new THREE.MeshStandardMaterial({ color: 0xb08a3a, roughness: 0.35, metalness: 0.85, emissive: 0x2a1c04 });
const WELL_MAT = new THREE.MeshBasicMaterial({ color: 0x050407, polygonOffset: true, polygonOffsetFactor: -2, polygonOffsetUnits: -2 });
const STEP_MATS = [0x4a4440, 0x2e2a28, 0x1a1817, 0x0e0d0d].map(c => new THREE.MeshStandardMaterial({ color: c, roughness: 0.95,
  polygonOffset: true, polygonOffsetFactor: -3, polygonOffsetUnits: -3 }));
const RIM_MAT = new THREE.MeshStandardMaterial({ color: 0x77736c, roughness: 0.9 });
const DOOR_MAT = new THREE.MeshStandardMaterial({ color: 0x6b4426, roughness: 0.85 });
const GROUND_MAT = new THREE.MeshStandardMaterial({ vertexColors: true, roughness: 0.95, metalness: 0 });
const WATER_GEO = new THREE.PlaneGeometry(1, 1).rotateX(-Math.PI / 2);

const WATER_MAT = new THREE.MeshStandardMaterial({ color: 0x2f6f86, roughness: 0.12, metalness: 0.2, transparent: true, opacity: 0.82 });
const FLAME_GEO = new THREE.SphereGeometry(0.11, 10, 8);
const FLAME_MAT = new THREE.MeshBasicMaterial({ color: new THREE.Color(6, 3.2, 1.1) });
const GHOST_FLAME_MAT = new THREE.MeshBasicMaterial({ color: new THREE.Color(1.2, 5, 2.4) });
