// Reasons to keep playing (docs/GAMEPLAY_POLISH.md group 4): herb patches and ore veins drawn and
// worked (world3d/nodes.js), a rare's gold glow (wards.js), the world's news (net.js, hud.js herald).
//   node --test tests/web/*.test.mjs
import { test } from 'node:test';
import assert from 'node:assert/strict';
import path from 'node:path';
import { readFileSync } from 'node:fs';
import { register } from 'node:module';
import { fileURLToPath, pathToFileURL } from 'node:url';

const HERE = path.dirname(fileURLToPath(import.meta.url));
const THREE_URL = pathToFileURL(path.join(HERE, '../../src/web_isometric/vendor/three/three.module.min.js')).href;
register('data:text/javascript,' + encodeURIComponent(
  `export async function resolve(s, c, next) { return s === 'three' ? { url: ${JSON.stringify(THREE_URL)}, shortCircuit: true } : next(s, c); }`));
const THREE = await import('three');
const { GatherNodes } = await import('../../src/web_isometric/world3d/nodes.js');
const { WARDS, wardPlan } = await import('../../src/web_isometric/world3d/wards.js');
const src = p => readFileSync(path.join(HERE, '../../src/web_isometric', p), 'utf8');

test('herb patches and ore veins: drawn where the server says, dull when spent, gone when out of reach', () => {
  const engine = { scene: new THREE.Scene(), camera: new THREE.PerspectiveCamera() };
  const rooms = new Map([[10, { ox: 0, oz: 0 }], [11, { ox: 24, oz: 0 }]]);
  let sparks = 0;
  const g = new GatherNodes(engine, () => ({ rooms }), { p: { emit: () => sparks++ } });
  g.sync({ nearby: [{ vnum: 10, node: { k: 'herb', x: 5, z: 6, ready: true } }, { vnum: 11, node: { k: 'ore', x: 3, z: 4, ready: false } }, { vnum: 12 }] });
  assert.equal(g.list.size, 2);
  assert.deepEqual([g.list.get(11).root.position.x, g.list.get(11).root.position.z], [27, 4]);
  assert.equal(g.list.get(10).ready, true);
  assert.equal(g.list.get(11).root.userData.glow[0].emissiveIntensity, 0, 'a worked vein is dull');
  for (let i = 0; i < 40; i++) g.update(0.1);
  assert.ok(sparks > 0, 'a ready patch glints');
  g.sync({ nearby: [{ vnum: 10, node: { k: 'herb', x: 5, z: 6, ready: false } }] });
  assert.equal(g.list.size, 1, 'one out of reach is cleared');
  assert.equal(g.list.get(10).ready, false);
  const main = src('world3d/main.js');
  assert.match(main, /MH\.sendCommand\(n\.kind === 'ore' \? 'mine' : 'forage'\)/, 'a click walks over and works it');
});

test("a rare's gold glow; the world's news reaches the page and is heralded", () => {
  assert.ok(WARDS.elite && wardPlan(['elite']).ring === WARDS.elite.ring);
  assert.match(src('shared/net.js'), /startsWith\('world_'\)\) MH\.bus\.emit\(`world\.\$\{payload\.type\.slice\(6\)\}`/);
  assert.match(src('world3d/main.js'), /MH\.bus\.on\('world\.rare'/);
  assert.match(src('world3d/main.js'), /MH\.bus\.on\('world\.achievement'/);
  assert.match(src('world3d/hud/hud.js'), /function herald\(/);
  assert.match(src('world3d/play.html'), /id="herald"/);
});
