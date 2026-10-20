// Room looks in the 3D client (Push 33): the server's `look` (room_looks.py) decides the
// theme, every look lays out a room you can walk through, and each has its mood and sounds.
//   node --test tests/web/
import { test } from 'node:test';
import assert from 'node:assert/strict';
import fs from 'node:fs';
import path from 'node:path';
import vm from 'node:vm';
import { fileURLToPath } from 'node:url';
import { surfaceFor, bedFor, musicFor, BEDS, SOUNDS, MUSIC } from '../../src/web_isometric/world3d/soundtable.js';

const ROOT = path.resolve(path.dirname(fileURLToPath(import.meta.url)), '../..');
const W = 24, H = 15, FLOOR = 0, BLOCK = 1, WATER = 4;
globalThis.window = globalThis;
globalThis.document = globalThis.document || { createElement: () => ({ getContext: () => null }) };
for (const f of ['world3d/hud-shim.js', 'shared/themes-zones.js', 'shared/roomgen.js']) {
  vm.runInThisContext(fs.readFileSync(path.join(ROOT, 'src/web_isometric', f), 'utf8'), { filename: f });
}
const MH = globalThis.MH;
const LOOKS = ['cave', 'mine', 'crypt', 'sewer', 'dungeon', 'desert', 'snow', 'shore', 'volcanic', 'swamp', 'web', 'castle', 'necropolis',
  'stones', 'village', 'camp', 'garden', 'ruins', 'terrace', 'drow'];

function sampleRooms(n = 60) {
  const out = [];
  const dir = path.join(ROOT, 'world/zones');
  for (const f of fs.readdirSync(dir).filter(f => /^zone_.*\.json$/.test(f)).sort()) {
    const data = JSON.parse(fs.readFileSync(path.join(dir, f), 'utf8'));
    const list = Array.isArray(data.rooms) ? data.rooms : Object.values(data.rooms || {});
    for (const r of list) if (r && r.vnum != null && out.length < n) out.push({ ...r, zone: data.number });
    if (out.length >= n) break;
  }
  return out;
}
const layout = (r, look) => {
  const exits = {};
  for (const [d, e] of Object.entries(r.exits || {})) if (e && !e.hidden && e.to_room != null) exits[d] = { to_room: e.to_room };
  return MH.generateRoomTopDown({ vnum: r.vnum, name: r.name, description: r.description || '', sector: r.sector_type,
    look, flags: r.flags || [], zone: r.zone, exits });
};
// every way out can be reached from the middle
function opensUp(L) {
  const seen = new Uint8Array(W * H), q = [[Math.floor(W / 2), Math.floor(H / 2)]];
  seen[q[0][1] * W + q[0][0]] = 1;
  while (q.length) {
    const [x, y] = q.shift();
    for (const [dx, dy] of [[1, 0], [-1, 0], [0, 1], [0, -1]]) {
      const xx = x + dx, yy = y + dy;
      if (xx < 0 || yy < 0 || xx >= W || yy >= H || seen[yy * W + xx] || L.grid[yy * W + xx] !== FLOOR) continue;
      seen[yy * W + xx] = 1; q.push([xx, yy]);
    }
  }
  const g = L.gaps || {}, mx = Math.floor(W / 2), my = Math.floor(H / 2);
  return (!g.north || seen[0 * W + mx]) && (!g.south || seen[(H - 1) * W + mx]) && (!g.west || seen[my * W]) && (!g.east || seen[my * W + W - 1]);
}

test("the server's look decides the theme, over the sector and the zone", () => {
  const r = sampleRooms(1)[0];
  for (const look of LOOKS) assert.equal(layout(r, look).theme, look, look);
  assert.equal(layout(r, 'nonsense').theme, MH.roomTheme({ sector: r.sector_type, zone: r.zone }), 'an unknown look falls back to the sector');
});

test('every look lays out rooms you can walk through, with its own shape', () => {
  const rooms = sampleRooms(60);
  for (const look of LOOKS) {
    let water = 0, rubble = 0;
    for (const r of rooms) {
      const L = layout(r, look);
      assert.ok(opensUp(L), `${look} room ${r.vnum}: every way out can be reached`);
      if (L.grid.includes(WATER)) water++;
      for (let y = 2; y < H - 2; y++) for (let x = 2; x < W - 2; x++) if (L.grid[y * W + x] === BLOCK) { rubble++; break; }
    }
    if (look === 'sewer') assert.ok(water >= rooms.length * 0.8, `most sewers have their channel (${water})`);
    if (look === 'shore') assert.ok(water >= rooms.length * 0.7, `most shores meet the water (${water})`);
    if (look === 'cave') assert.ok(rubble >= rooms.length * 0.5, `caves aren't tidy rectangles (${rubble})`);
  }
});

test('every look has its footsteps, ambience and music', () => {
  for (const look of LOOKS) {
    assert.ok(SOUNDS[surfaceFor({ theme: look })], `${look} footsteps`);
    assert.ok(BEDS[bedFor({ theme: look })], `${look} ambience`);
    assert.ok(MUSIC.includes(musicFor({ theme: look })), `${look} music`);
  }
  assert.equal(surfaceFor({ theme: 'snow' }), 'step_snow');
  assert.equal(bedFor({ theme: 'cave', zoneKey: 'midgaard' }), 'mines', "a cave sounds like a cave whatever its zone's old theme");
});

test('every look has its terrain branch, mood and minimap colour', () => {
  const src = f => fs.readFileSync(path.join(ROOT, 'src/web_isometric/world3d', f), 'utf8');
  const terrain = src('terrain.js') + src('terrain-looks.js') + src('terrain-castle.js'), engine = src('engine.js'), main = src('main.js'), mini = src('hud/minimap.js');
  for (const look of LOOKS) assert.ok(new RegExp(`'${look}'|${look}:`).test(terrain), `terrain draws ${look}`);
  for (const mood of ['cave', 'desert', 'snow', 'volcanic', 'web', 'necropolis']) assert.ok(new RegExp(`\\b${mood}: \\{`).test(engine), `mood ${mood}`);
  assert.ok(/mood = rock \? 'cave'/.test(main), 'the hero in a cave gets the cave mood');
  for (const look of ['mine', 'crypt', 'sewer', 'snow', 'shore', 'volcanic', 'web', 'castle', 'necropolis']) assert.ok(new RegExp(`\\b${look}: '#`).test(mini), `minimap ${look}`);
});

test('outdoor rooms that open onto each other share their whole side; a building keeps its doorway', () => {
  const base = { vnum: 4242, name: 'A Wood', description: '', sector_type: 'forest', zone: 1, flags: [] };
  const lay = (exits, look = 'forest') => MH.generateRoomTopDown({ vnum: base.vnum, name: base.name, description: '', sector: look, look, flags: [], zone: 1, exits });
  const L = lay({ east: { to_room: 1, kind: 'open', nlook: 'field' }, west: { to_room: 2, kind: 'open', nlook: 'inside' } });
  let eastOpen = 0, westOpen = 0;
  for (let y = 1; y < H - 1; y++) { if (L.grid[y * W + W - 1] === FLOOR) eastOpen++; if (L.grid[y * W] === FLOOR) westOpen++; }
  assert.equal(eastOpen, H - 2, 'the side onto the field is open its whole length');
  assert.ok(westOpen <= 5, `the side onto a building keeps its doorway (${westOpen})`);
  const P = lay({ east: { to_room: 1, kind: 'passage', nlook: 'field' } });
  let pOpen = 0; for (let y = 1; y < H - 1; y++) if (P.grid[y * W + W - 1] === FLOOR) pOpen++;
  assert.ok(pOpen <= 5, 'a passage (not side by side) keeps its doorway');
});

test('a water room is water from bank to bank, and you cross it', () => {
  for (const look of ['water_swim', 'water_noswim']) {
    const L = MH.generateRoomTopDown({ vnum: 777, name: 'On Mira Retrum', description: 'The river runs wide.', sector: look, look, flags: [], zone: 1,
      exits: { north: { to_room: 1 }, east: { to_room: 2, kind: 'open', nlook: look }, down: { to_room: 3 } } });
    let water = 0, floor = 0;
    for (let y = 1; y < H - 1; y++) for (let x = 1; x < W - 1; x++) { const t = L.grid[y * W + x]; if (t === WATER) water++; if (t === FLOOR) floor++; }
    assert.ok(L.swim, `${look}: water you move across`);
    assert.ok(water > (W - 2) * (H - 2) * 0.8, `${look}: mostly open water (${water})`);
  }
});
