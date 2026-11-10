// A made creature gives back what it holds on the graphics card when it is cleared away (freebody.js).
import test from 'node:test';
import assert from 'node:assert/strict';
import { readFileSync } from 'node:fs';
import { ownBody, freeBody } from '../../src/web_isometric/world3d/freebody.js';

const thing = () => ({ n: 0, dispose() { this.n++; } });
function body() {
  const coat = thing(), eye = thing(), g1 = thing(), g2 = thing();
  const parts = [{ geometry: g1, material: coat }, { geometry: g2, material: [coat, eye] }, {}];
  const root = { userData: {}, parts, traverse(fn) { fn(this); this.parts.forEach(fn); } };
  return { root, all: [coat, eye, g1, g2] };
}

test('a body owns each buffer and material once, and frees them once', () => {
  const { root, all } = body();
  assert.equal(ownBody(root), 4, 'the coat on two parts is counted once');
  const ring = thing();
  root.parts.push({ geometry: ring, material: ring });      // added later: a target ring, not its own
  assert.equal(freeBody(root), 4);
  assert.ok(all.every(x => x.n === 1) && ring.n === 0);
  assert.equal(freeBody(root), 0, 'a second clearing frees nothing');
  assert.ok(all.every(x => x.n === 1));
});

test('a body that was never marked (one loaded from a file, shared with its kind) is left alone', () => {
  const { root, all } = body();
  assert.equal(freeBody(root), 0);
  assert.equal(freeBody(null), 0);
  assert.ok(all.every(x => x.n === 0));
});

test('every place a creature leaves the scene frees it', () => {
  const src = f => readFileSync(new URL(`../../src/web_isometric/world3d/${f}`, import.meta.url), 'utf8');
  assert.ok(src('kin.js').includes('ownBody(a.root);'), 'a made creature is marked');
  assert.equal(src('entities.js').split('freeBody(').length - 1, 3, 'gone at once, gone quietly, and after dying');
  assert.ok(src('loot.js').includes('freeBody(l.body)'), 'and the body its corpse kept, with the corpse');
});

test('a quality chosen in Settings reaches every part that spends by it', () => {
  const src = f => readFileSync(new URL(`../../src/web_isometric/world3d/${f}`, import.meta.url), 'utf8');
  for (const f of ['fx.js', 'weather.js', 'audio.js', 'wards.js', 'adorn.js']) assert.ok(/\n  setTier\(/.test(src(f)), `${f} can be told`);
  assert.ok(src('main.js').includes('for (const part of [fx, sky, sound, wards, adorn]) part.setTier(tier);'));
  assert.ok(src('weather.js').includes('Math.max(...Object.values(COUNT))'), 'the sky has room for the most any quality asks');
});
