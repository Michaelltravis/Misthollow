// The dead on the ground (world3d/corpse.js): whose corpse it is, a body falling and resting on
// the floor (a death clip held, a code-built body's own death, or tipped over), darkened on its own
// materials, and a hero's grave.   node --test tests/web/*.test.mjs
import { test } from 'node:test';
import assert from 'node:assert/strict';
import path from 'node:path';
import { register } from 'node:module';
import { fileURLToPath, pathToFileURL } from 'node:url';

// the page's import map gives `three`; here it is the vendored copy
const THREE_URL = pathToFileURL(path.join(path.dirname(fileURLToPath(import.meta.url)), '../../src/web_isometric/vendor/three/three.module.min.js')).href;
register('data:text/javascript,' + encodeURIComponent(
  `export async function resolve(s, c, next) { return s === 'three' ? { url: ${JSON.stringify(THREE_URL)}, shortCircuit: true } : next(s, c); }`));
const THREE = await import('three');
const C = await import('../../src/web_isometric/world3d/corpse.js');

const box = (w, h, d) => {
  const root = new THREE.Group();
  const m = new THREE.Mesh(new THREE.BoxGeometry(w, h, d), new THREE.MeshStandardMaterial({ color: 0xffffff }));
  m.position.y = h / 2;
  root.add(m);
  return root;
};
const bounds = root => { root.updateMatrixWorld(true); return new THREE.Box3().setFromObject(root, true); };   // precise: a rotated stone's own points

test("whose corpse it is, and names compared as the creature's", () => {
  assert.equal(C.victimOf('corpse of the goblin'), 'the goblin');
  assert.equal(C.victimOf('The corpse of Vyrkothas the Frost Wyrm'), 'Vyrkothas the Frost Wyrm');
  assert.equal(C.nameKey('The Goblin'), C.nameKey('goblin'));
  assert.equal(C.nameKey('a large rat'), 'large rat');
});

test('a body with no death of its own tips over and rests on the floor', () => {
  const root = box(0.6, 1.8, 0.4);            // standing tall
  root.position.y = 1.2;                      // a flyer, in the air
  const fall = C.fallOver({ root }, { ground: 0, side: 1 });
  let n = 0;
  while (fall.update(0.1) && n < 50) n++;
  const b = bounds(root);
  assert.ok(Math.abs(root.rotation.z) > 1.4, 'on its side');
  assert.ok(Math.abs(b.min.y) < 0.05, `resting on the floor (${b.min.y.toFixed(3)})`);
  assert.ok(b.max.y - b.min.y < 0.7, 'lying, not standing');
});

test("a code-built body's own death plays and holds; one still standing then goes over", () => {
  const root = box(0.5, 1.2, 0.5);
  let played = null, t = 0;
  const actor = { root, once: n => { played = n; return 0.5; }, update: dt => { t += dt; } };
  const fall = C.fallOver(actor, { ground: 0 });
  while (fall.update(0.1)) ;
  assert.equal(played, 'Death_A');
  assert.ok(t > 0.45, 'its death played to the end');
  assert.ok(bounds(root).max.y < 0.7, 'and it lies down');
});

test('a long low body that has fallen stays as it lies', () => {
  const root = box(1.6, 0.4, 0.6);
  C.settle(root, 0);
  assert.equal(root.rotation.z, 0);
  assert.ok(Math.abs(bounds(root).min.y) < 0.05);
});

test("darkened on its own copies: the living keep theirs", () => {
  const shared = new THREE.MeshStandardMaterial({ color: 0xffffff });
  const a = new THREE.Group(), b = new THREE.Group();
  a.add(new THREE.Mesh(new THREE.BoxGeometry(1, 1, 1), shared));
  b.add(new THREE.Mesh(new THREE.BoxGeometry(1, 1, 1), shared));
  const made = C.deaden(a);
  assert.equal(made.length, 1);
  assert.ok(a.children[0].material !== shared && a.children[0].material.color.r < 0.9, 'the dead one is darker');
  assert.equal(b.children[0].material, shared, 'the other keeps the shared material');
  assert.equal(shared.color.r, 1);
});

test("a hero's grave: a mound, stones and a marker, all its own", () => {
  let seed = 1;
  const g = C.grave(() => ((seed = (seed * 16807) % 2147483647) / 2147483647));
  const meshes = [];
  g.traverse(o => { if (o.isMesh) meshes.push(o); });
  assert.ok(meshes.length >= 9, `mound, stones and a cross (${meshes.length})`);
  assert.ok(meshes.every(m => m.userData.own), 'loot.js may dispose every part of it');
  const b = bounds(g);
  assert.ok(b.min.y > -0.1 && b.max.y > 0.6, 'on the floor (its stones half-sunk), the marker standing');
});

test('the dead keep their colours: a little greyer and darker, a red still red', () => {
  const g = new THREE.Group();
  g.add(new THREE.Mesh(new THREE.BoxGeometry(1, 1, 1), new THREE.MeshStandardMaterial({ color: 0xc03020 })));
  C.deaden(g);
  const c = g.children[0].material.color;
  assert.ok(c.r > c.g * 2 && c.r > 0.35, `still red (${c.r.toFixed(2)}, ${c.g.toFixed(2)}, ${c.b.toFixed(2)})`);
});

test("a big body built in code goes over whole, its wings folded and kept off the floor's reckoning", () => {
  const root = box(1.2, 3.2, 3.0);               // a dragon standing 3.2 m
  const wing = new THREE.Group();
  wing.userData.wing = 1;
  const web = new THREE.Mesh(new THREE.BoxGeometry(2, 0.05, 1), new THREE.MeshStandardMaterial());
  web.position.x = 1; wing.add(web); wing.position.y = 2.5; root.add(wing);
  let deathPlayed = false;
  const actor = { root, once: () => { deathPlayed = true; return 1; }, update: () => {} };
  const fall = C.fallOver(actor, { ground: 0, side: 1 });
  while (fall.update(0.1)) ;
  assert.equal(deathPlayed, false, "not its own death (that rolls the torso alone)");
  assert.ok(Math.abs(root.rotation.z) > 1.4, 'on its side');
  assert.ok(Math.abs(wing.rotation.z) > 1.2, 'its wing folded');
  assert.ok(Math.abs(C.bodyBox(root).min.y) < 0.05, 'its body rests on the floor (the wing may pass under it)');
});

test('each creature dies as what it is (deathStyle), and leaves its remains', () => {
  const cases = { 'a wailing ghost': 'dissolve', 'the lich king': 'dissolve', 'a green slime': 'burst', 'a gelatinous cube': 'burst',
    'a fire elemental': 'burn', 'an imp': 'burn', 'a stone golem': 'shatter', 'an ice elemental': 'shatter', 'a goblin': 'fall',
    'a grey wolf': 'fall', 'the cityguard': 'fall' };
  for (const [name, style] of Object.entries(cases)) assert.equal(C.deathStyle(name), style, name);
  assert.equal(C.deathStyle(null, 'a shimmering spectre'), 'dissolve', 'the short description counts too');
  for (const style of ['dissolve', 'burst', 'burn', 'shatter']) {
    const g = C.remains(style, new THREE.Vector3(3, 0, 4));
    assert.ok(g.children.length >= 1 && g.position.x === 3, `${style} leaves something`);
  }
});
