// What lies past a room's edge (world3d/edges.js): a water room's land sides, what an empty map
// cell is filled with, and where a room's far vistas stand.
//   node --test tests/web/
import { test } from 'node:test';
import assert from 'node:assert/strict';
import { landSides, fillKind, vistaPlaces } from '../../src/web_isometric/world3d/edges.js';

const themeOf = s => s || 'default';
const room = (vnum, cx, cy, look, exits = {}, vista = []) => ({ vnum, cx, cy, data: { look, exits, vista } });
const zoneOf = rooms => ({ rooms: new Map(rooms.map(r => [r.vnum, r])), cells: new Map(rooms.map(r => [`${r.cx},${r.cy}`, r])) });

test('a water room: land where the map, a way out or its own words put it; open sea elsewhere', () => {
  const sea = room(1, 5, 5, 'water_noswim', { north: { to: 2 }, east: { to: 3 } });
  const z = zoneOf([sea, room(2, 5, 4, 'water_noswim'), room(3, 6, 5, 'shore'), room(4, 4, 5, 'forest')]);
  assert.deepEqual(landSides(sea, z, themeOf), { east: true, west: true }, 'a way out onto the shore; dry land on the map with no way to it');
  const beach = room(5, 0, 0, 'water_noswim', { north: { to: 9 } }, [{ kind: 'coast', dir: null, near: true }]);
  assert.deepEqual(landSides(beach, zoneOf([beach]), themeOf), { south: true, east: true, west: true },
    '"the shore is close at hand": every side with no way out (the sea opens out where the ways go)');
  const moles = room(6, 0, 0, 'water_swim', {}, [{ kind: 'cliffs', dir: 'east', near: true }, { kind: 'island', dir: 'north', near: false }]);
  assert.deepEqual(landSides(moles, zoneOf([moles]), themeOf), { east: true }, 'a far island is no bank');
  assert.deepEqual(landSides(room(7, 0, 0, 'forest'), zoneOf([]), themeOf), {}, 'a land room has no land sides to keep');
});

test('an empty cell is more of the country nearest it', () => {
  const at = new Map([['0,0', { kind: 'water' }], ['1,0', { kind: 'water' }], ['4,0', { kind: 'forest' }]]);
  const src = (x, y) => at.get(`${x},${y}`) || null;
  assert.equal(fillKind(src, 0, 1, 4).src.kind, 'water', 'next to the sea: sea');
  assert.equal(fillKind(src, 5, 1, 4).src.kind, 'forest', 'next to the forest: forest');
  assert.equal(fillKind(src, 2, 1, 4).src.kind, 'water', 'two water rooms against one forest at the same distance: water');
  assert.equal(fillKind(src, 0, 9, 4), null, 'beyond the reach: nothing (the haze)');
});

test('far vistas stand where the words put them, off the open sides, never over the zone\'s own rooms', () => {
  const r = room(1, 5, 5, 'water_swim', { north: { to: 2 }, south: { to: 3 } },
    [{ kind: 'town', dir: 'south', near: false }, { kind: 'island', dir: null, near: false }, { kind: 'coast', dir: null, near: true }]);
  const cells = new Map([['5,6', r], ['5,4', r]]);
  assert.deepEqual(vistaPlaces(r, new Map()), [{ kind: 'town', side: 'south' }, { kind: 'island', side: 'east' }, { kind: 'island', side: 'west' }]);
  assert.deepEqual(vistaPlaces(r, cells).map(p => p.side), ['east', 'west'], 'the zone\'s own rooms south: no harbour drawn over them');
  assert.deepEqual(vistaPlaces(room(2, 0, 0, 'field', { north: {}, south: {}, east: {}, west: {} }, [{ kind: 'mountains', dir: null }]), new Map()),
    [{ kind: 'mountains', side: 'north' }], 'ways out all round: straight ahead');
});
