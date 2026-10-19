// A world that feels alive (docs/GAMEPLAY_POLISH.md group 3): the weather (world3d/weather.js), the
// ripples and footprints, small life (wildlife.js), grass that bends (assets.js).
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
const W = await import('../../src/web_isometric/world3d/weather.js');
const { Wildlife } = await import('../../src/web_isometric/world3d/wildlife.js');

const stubs = () => {
  const played = [], emitted = [];
  const engine = { scene: new THREE.Scene(), quality: { name: 'low' }, weather: null, flashes: 0, lightning() { this.flashes++; } };
  const fx = { p: { emit: (p, o) => emitted.push(o) }, glyph: (p, o) => emitted.push(o) };
  const sound = { play: n => played.push(n) };
  return { engine, fx, sound, played, emitted };
};

test("the server's weather as the hero sees it where they stand", () => {
  assert.equal(W.weatherKind({ sky: 'rainy' }, 'forest'), 'rain');
  assert.equal(W.weatherKind({ sky: 'stormy' }, 'field'), 'storm');
  assert.equal(W.weatherKind({ sky: 'rainy', wind: 20 }, 'desert'), 'dust', 'a desert storm is dust');
  assert.equal(W.weatherKind({ sky: 'rainy', wind: 3 }, 'desert'), 'cloudy');
  assert.equal(W.weatherKind({ sky: 'rainy' }, 'snow'), 'snow', 'on snowy ground rain falls as snow');
  assert.equal(W.weatherKind({ sky: 'foggy' }, 'swamp'), 'fog');
  assert.equal(W.weatherKind(null, 'field'), 'clear');
});

test('rain falls and splashes under open sky, dims the light; indoors none of it', () => {
  const s = stubs();
  const sky = new W.WeatherView(s.engine, s.fx, s.sound);
  const c = new THREE.Vector3(10, 0, 10);
  sky.set('storm', 25, true);
  assert.ok(s.engine.weather.dim > 0.5 && s.engine.weather.fog > 0.3, 'a storm dims and closes in');
  for (let i = 0; i < 300; i++) sky.update(1 / 30, i / 30, c);
  assert.ok(sky.rain.visible && sky.amount > 0.9, 'the rain comes in');
  assert.ok(sky.ripples.list.some(r => r.m.visible), 'drops splash on the ground');
  assert.ok(s.played.includes('rain'), 'and are heard');
  assert.ok(s.engine.flashes >= 1 && s.played.includes('thunder'), 'lightning, then thunder');
  assert.ok(s.emitted.some(o => o.glyph === 'leaf'), 'leaves on the strong wind');
  sky.set('storm', 25, false);
  assert.deepEqual(s.engine.weather, { dim: 0, fog: 0, grey: 0 }, 'indoors the sky does not reach');
  for (let i = 0; i < 600; i++) sky.update(1 / 30, 10 + i / 30, c);
  assert.ok(!sky.rain.visible, 'and the rain stops');
  sky.set('snow', 3, true);
  for (let i = 0; i < 300; i++) sky.update(1 / 30, i / 30, c);
  assert.ok(sky.snow.visible && !sky.rain.visible, 'snow drifts down');
});

test('footprints left in snow and sand fade; ripples grow and fade', () => {
  const scene = new THREE.Scene();
  const f = new W.Footprints(scene, 4);
  f.step(0, 0, 0, 0, 'snow'); f.step(0, 0, 1, 0, 'sand');
  assert.equal(f.list.filter(x => x.m.visible).length, 2);
  assert.notEqual(f.list[0].m.position.x, f.list[1].m.position.x, 'left foot, right foot');
  f.update(15);
  assert.equal(f.list.filter(x => x.m.visible).length, 0, 'gone after a while');
  const r = new W.Ripples(scene, 2);
  r.spawn(1, 0, 1); r.update(0.3);
  assert.ok(r.list[0].m.scale.x > 0.08 && r.list[0].m.material.opacity < 0.5);
  r.update(2);
  assert.equal(r.list[0].m.visible, false);
});

test('birds peck by day and take wing as the hero comes near; fireflies by night; a fish leaps', () => {
  const s = stubs();
  const ripples = new W.Ripples(s.engine.scene);
  const water = (x, z) => x > 20;
  const wild = new Wildlife(s.engine, s.fx, ripples, s.sound, water);
  const hero = new THREE.Vector3(0, 0, 0);
  wild.set('field', true, false, null);
  for (let i = 0; i < 200 && !wild.birds.length; i++) wild.update(0.1, i / 10, hero, false);
  assert.ok(wild.birds.length >= 3, 'a flock comes down');
  const b = wild.birds[0].g;
  hero.set(b.position.x, 0, b.position.z);
  wild.update(0.1, 30, hero, false);
  assert.ok(wild.birds.every(x => x.fly), 'and takes wing when the hero walks up');
  for (let i = 0; i < 60; i++) wild.update(0.1, 31 + i / 10, hero, false);
  assert.equal(wild.birds.length, 0, 'flown off');
  wild.set('swamp', true, true, null);
  s.emitted.length = 0;
  for (let i = 0; i < 20; i++) wild.update(0.1, i / 10, new THREE.Vector3(0, 0, 0), false);
  assert.ok(s.emitted.length >= 10, 'fireflies by night');
  const near = new THREE.Vector3(18, 0, 0);
  let leapt = false;
  for (let i = 0; i < 400 && !leapt; i++) { wild.update(0.1, i / 10, near, false); leapt = !!wild.leap; }
  assert.ok(leapt, 'a fish leaps from the water nearby');
});

test('grass bends round the hero and stirs in the wind (instanced Grass_* only, its own material)', () => {
  const src = readFileSync(path.join(HERE, '../../src/web_isometric/world3d/assets.js'), 'utf8');
  assert.match(src, /const grass = \/\^Grass_\//);
  assert.match(src, /part\.bendMat = part\.material\.clone\(\)/);
  assert.match(src, /gWorld\.xz \+= /);
  const main = readFileSync(path.join(HERE, '../../src/web_isometric/world3d/main.js'), 'utf8');
  assert.match(main, /GRASS\.hero\.value\.set\(p\.x, p\.y, p\.z\)/);
  assert.match(main, /sky\.prints\.step\(/);
});
