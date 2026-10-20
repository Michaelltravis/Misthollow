// Towns, interiors and graveyards (owner's M1b order: towns and interiors after monsters).
//  - Streets ('city'): where a street borders an empty cell of the zone map, a row of
//    houses fills it, facing the street (shops, inns, smithies and temples by the street's
//    name); where it borders another room, a low town wall.
//  - Interiors ('inside' rooms named like a shop, inn, temple, bank, library, bedroom,
//    guild or hall): wood or stone floor, furniture along the walls and on roomgen's
//    obstacles, a rug, lamps; unnamed 'inside' rooms keep the dungeon look.
//  - Graveyards (outdoor rooms named so): graves in rows, fences, dead trees, lanterns.
// Pieces that stand on open floor are written into the room's grid as BLOCK so the hero
// walks around them (the server never sees this: it is furniture, not geometry).
import * as THREE from 'three';
import { trs } from './assets.js';
import { tinted } from './terrain-looks.js';
import { interiorStyle, FURNISHED, RUGS } from './terrain-interiors.js';

const BLOCK = 1, FLOOR = 0;
const CARD = { north: [0, -1], south: [0, 1], east: [1, 0], west: [-1, 0] };
const YAW = { north: 0, south: Math.PI, west: Math.PI / 2, east: -Math.PI / 2 };   // face into the room

export function interiorKind(layout) {
  const t = `${layout.name} ${layout.description}`.toLowerCase();
  if (/\b(temple|church|chapel|cathedral|shrine|altar|sanctuary|abbey|monastery|cloister)\b/.test(t)) return 'temple';
  if (/\b(tavern|inn|pub|bar|alehouse|taproom|common room|brewery)\b/.test(t)) return 'tavern';
  if (/\b(bank|vault|treasury|counting house|money ?changer)\b/.test(t)) return 'bank';
  if (/\b(library|study|archive|scriptorium|reading room)\b/.test(t)) return 'library';
  if (/\b(bedroom|bed ?chamber|sleeping|quarters|dormitory|guest room|nursery|bunks?)\b/.test(t)) return 'bedroom';
  if (/\b(throne|palace|great hall|audience|court)\b/.test(t)) return 'throne';
  if (/\b(shop|store|market|merchant|grocer|grocery|baker|bakery|general|armou?ry|weapon|smithy|forge|apothecary|herbalist|alchemist|jewell?er|tailor|outfitter|emporium|butcher|stable|pet)\b/.test(t)) return 'shop';
  if (/\b(guild|training|practice|academy|school|barracks|armory)\b/.test(t)) return 'guild';
  if (/\b(house|home|cottage|hut|kitchen|parlou?r|dining|living room|hall)\b/.test(t)) return 'house';
  return null;
}
export const isGraveyard = layout =>
  /\b(graveyard|cemetery|graves?|burial|boneyard|churchyard|tombstones?|mausoleum)\b/.test(`${layout.name} ${layout.description}`.toLowerCase());

// lanes from the room centre to each opening stay clear (roomgen keeps them too), and so do
// the stairs, portals and the spots beside them where people arrive
function laneTest(layout) {
  const { W, H, gaps } = layout;
  const mx = Math.floor(W / 2), my = Math.floor(H / 2);
  const keep = [layout.stairsUp, layout.stairsDown, ...(layout.portals || [])].filter(Boolean);
  return (x, y) => ((gaps.north || gaps.south) && Math.abs(x - mx) <= 4)
    || ((gaps.east || gaps.west) && Math.abs(y - my) <= 3)
    || Math.abs(x - mx) <= 1 && Math.abs(y - my) <= 1
    || keep.some(t => Math.abs(x - t.x) <= 3 && Math.abs(y - t.y) <= 2);
}

// ---------------------------------------------------------------- streets
const LANDMARK = [
  [/\b(tavern|inn|pub|alehouse|bar)\b/, 'building_tavern'],
  [/\b(smith|smithy|forge|armou?r|weapon)\b/, 'building_blacksmith'],
  [/\b(temple|church|chapel|cathedral|shrine)\b/, 'building_church'],
  [/\b(market|bazaar|square|fair|plaza|merchant)\b/, 'building_market'],
  [/\b(gate|guard|barracks|tower|wall|garrison)\b/, 'building_tower_A'],
  [/\b(mill)\b/, 'building_windmill'],
];
const COLORS = ['blue', 'red', 'yellow', 'green'];

// every town its own: two house colours and an accent, and a stone tint, picked from the zone's
// number (Garathorm reads red and blue, another town green and yellow); a desert town is sandstone
const TOWN_TINTS = [0xffffff, 0xf2e6d4, 0xe4e8ee, 0xf6ead0, 0xe8e0d8];
function townStyle(room) {
  const n = (room && room.zoneRef && room.zoneRef.num) || 0;
  const h = (n * 2654435761) >>> 0;
  const a = h % 4, b = (a + 1 + (h >> 3) % 3) % 4;
  const accent = [0, 1, 2, 3].find(i => i !== a && i !== b);
  const desert = /desert|sand|dune|oasis/i.test((room && room.zoneRef && room.zoneRef.name) || '');
  return { colors: [COLORS[a], COLORS[a], COLORS[b], COLORS[b], COLORS[accent]], tint: desert ? 0xf4d8a8 : TOWN_TINTS[(h >> 6) % TOWN_TINTS.length], key: `town${n}` };
}

// a house for the blocks beyond the streets (terrain.js fills a town's empty cells with them):
// the town's own colours and tint
export function townHouse(kits, room, rng) {
  if (!kits.town) return null;
  const style = townStyle(room);
  const T = style.tint === 0xffffff ? kits.town : { get: k => tinted(kits.town.get(k), style.tint, style.key) };
  const r = rng();
  const key = r < 0.45 ? 'building_home_A' : r < 0.8 ? 'building_home_B' : r < 0.9 ? 'building_tavern' : r < 0.96 ? 'building_blacksmith' : 'building_tower_A';
  return T.get(`${key}_${style.colors[Math.floor(rng() * style.colors.length)]}`) || T.get(`${key}_blue`);
}

// what part of town a street is, from its name and words: what stands on it and what lines it
const DISTRICTS = [
  ['market', /\b(market|bazaar|square|fair|plaza|merchant|stall|trade)\b/],
  ['docks', /\b(dock|docks|quay|wharf|harbou?r|pier|port|warehouse)\b/],
  ['guard', /\b(gate|guard|barracks|garrison|watch|wall|tower|armou?ry)\b/],
  ['temple', /\b(temple|church|chapel|cathedral|shrine|fountain|garden|park)\b/],
  ['poor', /\b(alley|slum|poor|beggar|dump|gutter|shanty)\b/],
  ['noble', /\b(noble|manor|palace|villa|estate|royal|lord)\b/],
];
function districtOf(layout) {
  const text = `${layout.name || ''} ${layout.description || ''}`.toLowerCase();
  return (DISTRICTS.find(([, re]) => re.test(text)) || ['street'])[0];
}
const DISTRICT_PROPS = {
  market: { big: ['tent', 'tent', 'building_market_X', 'crate_long_A'], small: ['crate_A_big', 'sack', 'crate_B_small', 'barrel', 'sack'] },
  docks: { big: ['pallet', 'resource_lumber', 'crate_long_A'], small: ['barrel', 'crate_A_big', 'barrel', 'crate_B_small', 'sack'] },
  guard: { big: ['weaponrack', 'target', 'crate_long_A'], small: ['barrel', 'weaponrack', 'crate_B_small'] },
  temple: { big: ['building_well_X', 'tree_single_A', 'trees_A_medium'], small: ['bucket_water', 'tree_single_A', 'sack'] },
  poor: { big: ['pallet', 'wheelbarrow', 'crate_long_A'], small: ['crate_B_small', 'sack', 'barrel', 'bucket_water'] },
  noble: { big: ['tree_single_A', 'trees_A_medium', 'building_well_X'], small: ['tree_single_A', 'barrel'] },
  street: { big: ['building_well_X', 'crate_long_A', 'wheelbarrow', 'tent', 'tree_single_A'], small: ['barrel', 'crate_A_big', 'sack', 'bucket_water', 'crate_B_small'] },
};
const PROP_SCALE = { tent: 2.2, tree_single_A: 3.2, trees_A_medium: 2.6, pallet: 4, resource_lumber: 3.5, weaponrack: 4, target: 4, wheelbarrow: 5, crate_long_A: 5 };

// a dead city (the 'necropolis' look, dead Morkai): the same streets in black stone, graves and
// bones for street furniture, ghost-green braziers in place of torches
const NECRO_STONE = 0x4a4652;
function darkTown(T) {
  return T && { get: k => tinted(T.get(k), NECRO_STONE, 'necro') };
}

export function townStreet(c) {
  const { layout, ox, oz, kits, room, b, rng, runs, occ } = c;
  const necro = layout.theme === 'necropolis';
  const style = townStyle(room);
  const district = districtOf(layout);
  const T = necro ? darkTown(kits.town) : kits.town && (style.tint === 0xffffff ? kits.town : { get: k => tinted(kits.town.get(k), style.tint, style.key) });
  const pickLandmark = text => (LANDMARK.find(([re]) => re.test(String(text || '').toLowerCase())) || [])[1];
  let streetLandmark = pickLandmark(`${layout.name} ${layout.description}`);
  for (const run of runs) {
    const side = run.horiz ? (run.line === 0 ? 'north' : 'south') : (run.line === 0 ? 'west' : 'east');
    const [dx, dy] = CARD[side];
    const nb = room && room.zoneRef ? room.zoneRef.cells.get(`${room.cx + dx},${room.cy + dy}`) : null;
    const L = run.b - run.a + 1;
    // what lies beyond this edge decides what stands on it:
    //   nothing  -> whole houses built out into the empty cell
    //   a building (an 'inside' room) -> its shopfront, two tiles deep (both walls' width)
    //   anything else (another street, the fields) -> a low stone town wall
    const mode = !nb ? 'houses' : nb.data.sector === 'inside' ? 'facade' : 'wall';
    if (mode === 'wall' || !T) {
      const wall = occ(T ? T.get('wall_straight') : kits.dungeon.get('wall'));
      const n = Math.max(1, Math.round(L / 2.5)), w = L / n;
      for (let i = 0; i < n; i++) {
        const along = run.a + (i + 0.5) * w;
        const [x, z] = run.horiz ? [ox + along, oz + run.line + 0.5] : [ox + run.line + 0.5, oz + along];
        b.add(wall, trs(x, 0, z, run.horiz ? 0 : Math.PI / 2, T ? w / 2 : w / 4, T ? 1.5 : 0.5, T ? 1.25 : 1));
      }
      continue;
    }
    // the shop behind a facade names its front (the Weapon Shop gets a smithy front...)
    let landmark = mode === 'facade' ? pickLandmark(nb.data.name) : streetLandmark;
    const maxDepth = mode === 'facade' ? 2 : run.horiz ? 7 : 11;
    let cursor = run.a;
    const end = run.b + 1;
    while (end - cursor > 2.2) {
      let key;
      if (landmark) { key = landmark; landmark = null; if (mode === 'houses') streetLandmark = null; }
      else if (mode === 'houses' && rng() < 0.12) {
        // a pocket garden between houses: a tree or two behind a fence
        const gw = 3.2;
        if (end - cursor < gw + 0.5) break;
        const along = cursor + gw / 2;
        const depth = 2.2;
        const [gx, gz] = side === 'north' ? [ox + along, oz + depth] : side === 'south' ? [ox + along, oz + 15 - depth]
          : side === 'west' ? [ox + depth, oz + along] : [ox + 24 - depth, oz + along];
        const tree = T.get(rng() < 0.5 ? 'tree_single_A' : 'trees_A_medium');
        if (tree) b.add(occ(tree), trs(gx, 0, gz, rng() * 6.28, 2.6 + rng() * 0.8));
        const fence = T.get(rng() < 0.5 ? 'fence_wood_straight' : 'fence_stone_straight');
        if (fence) b.add(occ(fence), trs(side === 'north' || side === 'south' ? gx : gx + (side === 'west' ? 1.4 : -1.4), 0,
          side === 'north' || side === 'south' ? gz + (side === 'north' ? 1.4 : -1.4) : gz, YAW[side], 3.2));
        cursor += gw + 0.35;
        continue;
      }
      else {
        const r = rng();
        key = district === 'guard' && r < 0.3 ? 'building_barracks' : district === 'docks' && r < 0.15 ? 'building_watermill'
          : r < 0.5 ? 'building_home_A' : r < 0.78 ? 'building_home_B' : r < 0.9 ? 'building_tavern' : 'building_blacksmith';
      }
      const model = T.get(`${key}_${style.colors[Math.floor(rng() * style.colors.length)]}`) || T.get(`${key}_blue`);
      if (!model) break;
      const size = new THREE.Vector3(); model.box.getSize(size);
      let s = 6;
      if (cursor + size.x * s > end) { s = (end - cursor) / size.x; if (s < 3.5) break; }
      // depth: whole houses keep their shape up to the room's half depth; facades are
      // pressed to two tiles so they never reach into a neighbour's floor
      const sz = Math.min(s, maxDepth / size.z);
      const w = size.x * s;
      const along = cursor + w / 2;
      const off = 1.0 - model.box.max.z * sz;        // front on the ring tile's inner edge
      let x, z;
      if (side === 'north') { x = ox + along; z = oz + off; }
      else if (side === 'south') { x = ox + along; z = oz + 15 - off; }
      else if (side === 'west') { x = ox + off; z = oz + along; }
      else { x = ox + 24 - off; z = oz + along; }
      b.add(occ(model), trs(x, 0, z, YAW[side], s, s, sz));
      cursor += w + 0.35;
    }
    if (end - cursor > 0.8) {
      const along = (cursor + end) / 2;
      const [x, z] = run.horiz ? [ox + along, oz + run.line + 0.5] : [ox + run.line + 0.5, oz + along];
      b.add(T.get('barrel'), trs(x, 0, z, rng() * 6.28, 4.5));
    }
  }
  // street furniture on roomgen's obstacles (they block in the grid already)
  const G = kits.graveyard;
  for (const o of layout.obstacles || []) {
    const cx = ox + o.x + (o.big ? 1 : 0.5), cz = oz + o.y + (o.big ? 1 : 0.5);
    if (necro && G) {
      // the dead city: a crypt, a shrine, dead trees, graves; bones and skulls underfoot
      const yaw = Math.floor(rng() * 4) * Math.PI / 2;
      if (o.big) {
        const key = ['crypt', 'shrine_candles', 'tree_dead_large', 'grave_A', 'grave_B'][Math.floor(rng() * 5)];
        b.add(occ(G.get(key)), trs(cx, 0, cz, yaw, key === 'crypt' ? 0.45 : key.startsWith('tree') ? 0.8 : 0.6));
      } else {
        const key = ['gravestone', 'gravemarker_A', 'ribcage', 'post_skull', 'bone_A', 'skull_candle'][Math.floor(rng() * 6)];
        b.add(G.get(key), trs(cx, 0, cz, rng() * 6.28, key.startsWith('grave') ? 0.55 : 0.9));
      }
      continue;
    }
    // the district's furniture: a market's tents and crates, the docks' pallets and lumber, the
    // guard's weapon racks, a temple square's well and trees...
    const kit = DISTRICT_PROPS[district] || DISTRICT_PROPS.street;
    if (o.big) {
      let key = kit.big[Math.floor(rng() * kit.big.length)].replace('_X', `_${style.colors[0]}`);
      const s = key.startsWith('building_well') ? 2.6 : key.startsWith('building_market') ? 1.4 : PROP_SCALE[key] || 5;
      b.add(occ(T.get(key) || T.get('barrel')), trs(cx, 0, cz, Math.floor(rng() * 4) * Math.PI / 2, s));
    } else {
      const key = kit.small[Math.floor(rng() * kit.small.length)];
      b.add(T.get(key) || T.get('barrel'), trs(cx, 0, cz, rng() * 6.28, PROP_SCALE[key] || 4.5));
    }
  }
}

// ---------------------------------------------------------------- interiors
const WALL_PIECES = {
  shop: ['shelf_B_large_decorated', 'cabinet_medium_decorated', 'shelf_B_large', 'cabinet_small_decorated'],
  tavern: ['shelf_A_big', 'cabinet_medium', 'lamp_standing'],
  bank: ['cabinet_medium_decorated', 'cabinet_small_decorated', 'pictureframe_large_A'],
  library: ['shelf_B_large_decorated', 'shelf_B_large_decorated', 'shelf_B_small_decorated'],
  bedroom: ['cabinet_small', 'lamp_standing', 'pictureframe_standing_A'],
  guild: ['shelf_A_big', 'cabinet_medium', 'pictureframe_large_B'],
  throne: ['lamp_standing', 'pictureframe_large_A', 'pictureframe_large_B'],
  house: ['shelf_A_big', 'cabinet_small_decorated', 'lamp_standing', 'pictureframe_medium'],
  temple: [],
};
const WOOD = new Set(['shop', 'tavern', 'library', 'bedroom', 'house', 'guild']);

// one wood per room (a mix of light and dark planks read as noise)
export function interiorFloorKey(kind, r, vnum = 0) {
  if (!WOOD.has(kind)) return null;
  return vnum % 3 === 0 ? 'floor_wood_small_dark' : 'floor_wood_small';
}

export function furnish(c, kind) {
  const { layout, ox, oz, kits, b, rng, occ, torches } = c;
  const F = kits.furniture, D = kits.dungeon, G = kits.graveyard, T = kits.town;
  const { W, H, grid } = layout;
  // a drow hall keeps only its altar or throne, benches and candles: its pillars, statues and
  // faerie fire come from drowDress, not a human hall's lamps, banners, rugs and pictures
  const drow = layout.theme === 'drow';
  // an interior in its zone's style keeps only the furniture of its use; terrain-interiors.js
  // dresses its walls, halls and light
  const style = interiorStyle(layout), styled = style && !FURNISHED.has(kind);
  const lane = laneTest(layout);
  const at = (x, y) => grid[y * W + x];
  const block = (x, y) => { if (x > 0 && y > 0 && x < W - 1 && y < H - 1) grid[y * W + x] = BLOCK; };
  const MOUNTED = /^(shelf_A_|pictureframe_(large|medium|small))/;
  const put = (kit, key, x, z, yaw, s = 1, opts) => {
    const m = kit && kit.get(key);
    if (m) b.add(opts && opts.occ ? occ(m) : m, trs(x, MOUNTED.test(key) ? 1.3 : 0, z, yaw, s), opts);
    return !!m;
  };

  // along the north wall (the one the camera faces by default) and the side walls
  const wallPieces = drow || style ? [] : WALL_PIECES[kind] || [];
  if (wallPieces.length) {
    for (let x = 2; x < W - 2; x += 3) {
      if (at(x, 1) !== FLOOR || at(x + 1, 1) !== FLOOR || lane(x, 1) || lane(x + 1, 1)) continue;
      const key = wallPieces[Math.floor(rng() * wallPieces.length)];
      const mounted = MOUNTED.test(key);
      put(F, key, ox + x + 1, oz + 1.05 + (mounted ? 0 : 0.3), 0, 0.85, { occ: true });   // see-through when in the way
      if (!mounted) { block(x, 1); block(x + 1, 1); }
    }
    for (const [x, yaw] of [[1, Math.PI / 2], [W - 2, -Math.PI / 2]]) {
      for (let y = 3; y < H - 3; y += 4) {
        if (at(x, y) !== FLOOR || lane(x, y) || rng() < 0.4) continue;
        const key = wallPieces[Math.floor(rng() * wallPieces.length)];
        if (MOUNTED.test(key) || key.startsWith('pictureframe')) continue;
        put(F, key, ox + x + 0.5 + (x === 1 ? -0.2 : 0.2), oz + y + 0.5, yaw, 0.8, { occ: true });
        block(x, y);
      }
    }
  }

  // centrepieces on roomgen's obstacles (already blocked)
  for (const o of drow || styled ? [] : layout.obstacles || []) {
    const cx = ox + o.x + (o.big ? 1 : 0.5), cz = oz + o.y + (o.big ? 1 : 0.5);
    const yaw = Math.floor(rng() * 4) * Math.PI / 2;
    if (kind === 'tavern') {
      put(F, o.big ? 'table_medium' : 'table_small', cx, cz, yaw, o.big ? 0.8 : 0.7, { occ: false });
      for (const [sx, sz] of o.big ? [[-1.3, 0], [1.3, 0], [0, -1.3], [0, 1.3]] : [[-0.9, 0], [0.9, 0]])
        put(F, 'chair_stool_wood', cx + sx, cz + sz, rng() * 6.28, 0.75, { shadow: false });
      if (o.big && D) put(D, 'keg', cx + 0.6, cz - 0.6, 0, 0.35);
    } else if (kind === 'shop') {
      if (o.big) put(F, 'table_medium_long', cx, cz, yaw, 0.85);
      else put(D, ['barrel_small', 'box_large'][Math.floor(rng() * 2)], cx, cz, rng() * 6.28, 0.7);
    } else if (kind === 'bedroom') {
      put(F, o.big ? (rng() < 0.5 ? 'bed_double_A' : 'bed_single_A') : 'cabinet_small', cx, cz, yaw, o.big ? 0.7 : 0.8);
    } else if (kind === 'library') {
      put(F, o.big ? 'table_medium' : 'shelf_B_small_decorated', cx, cz, yaw, 0.8);
      if (o.big) put(F, 'book_set', cx, cz, rng() * 6.28, 0.8, { shadow: false });
    } else if (kind === 'bank') {
      put(F, o.big ? 'table_medium_long' : 'cabinet_small_decorated', cx, cz, yaw, 0.85);
      if (o.big && D) put(D, 'chest_gold', cx, cz + 1.2, Math.PI, 0.6);
    } else if (kind === 'temple' || kind === 'throne') {
      if (o.big) put(D, 'pillar_decorated', cx, cz, 0, 1, { occ: true });
      else put(G, 'candle_triple', cx, cz, 0, 0.9);
    } else if (kind === 'guild') {
      put(o.big ? F : T, o.big ? 'table_medium' : 'weaponrack', cx, cz, yaw, o.big ? 0.8 : 4.5);
    } else {
      put(F, o.big ? 'table_medium' : 'chair_A_wood', cx, cz, yaw, 0.8);
    }
  }

  // the middle of the room: a rug (temples: a runner up the aisle) and an altar or throne
  const mx = W / 2, my = H / 2;
  if (kind === 'temple' || kind === 'throne') {
    if (!drow && !style) put(F, 'rug_rectangle_stripes_A', ox + mx, oz + my + 1, Math.PI / 2, 1.2, { shadow: false, receive: true });
    if (!layout.gaps.north) {
      if (kind === 'temple') put(G, 'shrine_candles', ox + mx, oz + 2.2, 0, 0.75);
      else if (!drow && !style) put(F, 'armchair_pillows', ox + mx, oz + 2.2, 0, 1.0);   // a drow throne is drowDress's, a styled one dressInterior's
      block(Math.floor(mx), 2); block(Math.floor(mx) - 1, 2);
      torches.push(new THREE.Vector3(ox + mx, 1.6, oz + 2.6));
    }
    // banners on the north wall
    if (!drow && !style) for (let x = 3; x < W - 3; x += 5) if (!layout.gaps.north || Math.abs(x - mx) > 5)
      put(D, ['banner_patternA_red', 'banner_patternB_blue', 'banner_shield_white'][x % 3], ox + x, oz + 0.8, 0, 0.65);
    // benches facing the altar on both sides of the aisle
    if (kind === 'temple') for (let y = 5; y < H - 3; y += 2) for (const x of [mx - 5, mx + 5]) {
      const tx = Math.floor(x), ty = Math.floor(y);
      if (at(tx, ty) !== FLOOR || at(tx + 1, ty) !== FLOOR || lane(tx, ty)) continue;
      put(G, 'bench', ox + x, oz + y, 0, 0.6);
      block(tx, ty); block(tx + 1, ty);
    }
  } else {
    const rug = ['rug_rectangle_A', 'rug_oval_A', 'rug_rectangle_B', 'rug_oval_B'][Math.floor(rng() * 4)];
    if (!style || RUGS.has(style)) put(F, rug, ox + mx, oz + my, rng() < 0.5 ? 0 : Math.PI / 2, 1, { shadow: false });
  }
  // lamps in the corners light the room
  for (const [x, y] of drow || style ? [] : [[1.6, 1.6], [W - 1.6, 1.6]]) {
    if (at(Math.floor(x), Math.floor(y)) !== FLOOR) continue;
    put(F, 'lamp_standing', ox + x, oz + y, 0, 0.7);
    block(Math.floor(x), Math.floor(y));
    torches.push(new THREE.Vector3(ox + x, 1.7, oz + y));
  }
  // small things on the props (walk-through)
  for (const p of styled ? [] : layout.props || []) {
    const key = kind === 'library' ? 'book_set' : kind === 'tavern' ? 'chair_stool_wood' : kind === 'temple' ? 'candle_triple' : 'book_single';
    put(kind === 'temple' ? G : F, key, ox + p.x + 0.5, oz + p.y + 0.5, rng() * 6.28, 0.6, { shadow: false });
  }
}

// ---------------------------------------------------------------- graveyards
export function graveyard(c) {
  const { layout, ox, oz, kits, b, rng, occ, torches, runs } = c;
  const G = kits.graveyard;
  if (!G) return;
  const { W, H, grid } = layout;
  const lane = laneTest(layout);
  const at = (x, y) => grid[y * W + x];
  // rows of graves on open ground, each blocking its tile
  for (let y = 3; y < H - 3; y += 3) for (let x = 3; x < W - 3; x += 3) {
    if (at(x, y) !== FLOOR || lane(x, y) || rng() < 0.25) continue;
    const key = ['grave_A', 'grave_B', 'gravestone', 'gravemarker_A', 'gravemarker_B', 'grave_A_destroyed'][Math.floor(rng() * 6)];
    b.add(occ(G.get(key)), trs(ox + x + 0.5, 0, oz + y + 0.5, (rng() - 0.5) * 0.3, 0.55));
    grid[y * W + x] = BLOCK;
  }
  // a fence along the edge of the ground, lanterns by the ways in and out
  for (const run of runs) {
    const L = run.b - run.a + 1;
    const n = Math.max(1, Math.round(L / 2.2)), w = L / n;
    for (let i = 0; i < n; i++) {
      const along = run.a + (i + 0.5) * w;
      const [x, z] = run.horiz ? [ox + along, oz + run.line + 0.5] : [ox + run.line + 0.5, oz + along];
      b.add(G.get(rng() < 0.8 ? 'fence' : 'fence_broken'), trs(x, 0, z, run.horiz ? 0 : Math.PI / 2, w / 4, 0.6, 0.6));
    }
  }
  for (const [dir, g] of Object.entries(layout.gaps)) {
    const pts = dir === 'north' || dir === 'south'
      ? [[g.x0 - 0.5, dir === 'north' ? 1 : H - 1], [g.x1 + 1.5, dir === 'north' ? 1 : H - 1]]
      : [[dir === 'west' ? 1 : W - 1, g.y0 - 0.5], [dir === 'west' ? 1 : W - 1, g.y1 + 1.5]];
    for (const [x, y] of pts) {
      b.add(G.get('lantern_standing'), trs(ox + x, 0, oz + y, 0, 1.0), { shadow: false });
      torches.push(new THREE.Vector3(ox + x, 0.8, oz + y));
    }
  }
}
