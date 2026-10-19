// Little pictures for the ability effects, drawn in code when the page loads (no image
// files): glyphs (notes, skulls, coins, leaves, runes...) packed in one atlas for the glyph
// particles, and ground sigils (each class's circle, cracks, scorch, frost) for decals.
// Everything is drawn white on transparent; the effects tint it.
//
// Glyphs are drawn in a box of -50..50 around their centre and kept inside a circle of
// radius ~45, so a particle can spin without its corners being cut off.

export const GLYPHS = ['dot', 'star', 'note', 'notes', 'skull', 'bone', 'cross', 'snow', 'bolt', 'leaf', 'feather',
  'coin', 'die', 'rune', 'sun', 'drop', 'flame', 'petal', 'shard', 'dagger', 'eye', 'chevron', 'paw', 'wisp', 'ring', 'bubble', 'zzz', 'heart', 'hush'];
export const ATLAS_COLS = 5;
export const CELL = 96;
export const glyphIndex = name => Math.max(0, GLYPHS.indexOf(name));

const TAU = Math.PI * 2;
const poly = (c, pts) => { c.beginPath(); pts.forEach(([x, y], i) => (i ? c.lineTo(x, y) : c.moveTo(x, y))); c.closePath(); c.fill(); };
const disc = (c, x, y, r) => { c.beginPath(); c.arc(x, y, r, 0, TAU); c.fill(); };
const ellipse = (c, x, y, rx, ry, rot = 0) => { c.beginPath(); c.ellipse(x, y, rx, ry, rot, 0, TAU); c.fill(); };
// cut a hole (eye sockets, a leaf's vein, a coin's rim)
function hole(c, draw) { c.save(); c.globalCompositeOperation = 'destination-out'; c.shadowBlur = 0; draw(); c.restore(); }
function stroke(c, w, pts) {
  c.lineWidth = w; c.lineCap = 'round'; c.lineJoin = 'round';
  c.beginPath(); pts.forEach(([x, y], i) => (i ? c.lineTo(x, y) : c.moveTo(x, y))); c.stroke();
}

export const DRAW = {
  dot(c) {
    const g = c.createRadialGradient(0, 0, 0, 0, 0, 44);
    g.addColorStop(0, 'rgba(255,255,255,1)'); g.addColorStop(0.35, 'rgba(255,255,255,0.7)'); g.addColorStop(1, 'rgba(255,255,255,0)');
    c.fillStyle = g; c.shadowBlur = 0; disc(c, 0, 0, 44);
  },
  star(c) { poly(c, [[0, -44], [9, -9], [44, 0], [9, 9], [0, 44], [-9, 9], [-44, 0], [-9, -9]]); },
  note(c) {
    ellipse(c, -10, 24, 15, 10, -0.45);
    c.fillRect(2, -36, 6, 60);
    c.beginPath(); c.moveTo(8, -36); c.bezierCurveTo(30, -26, 30, -8, 20, 2); c.bezierCurveTo(24, -10, 18, -20, 8, -22); c.closePath(); c.fill();
  },
  notes(c) {
    ellipse(c, -24, 26, 13, 9, -0.45); ellipse(c, 18, 18, 13, 9, -0.45);
    c.fillRect(-15, -26, 5, 50); c.fillRect(27, -34, 5, 50);
    poly(c, [[-15, -26], [32, -34], [32, -22], [-15, -14]]);
  },
  skull(c) {
    disc(c, 0, -8, 30);
    c.beginPath(); c.roundRect(-17, 6, 34, 26, 6); c.fill();
    hole(c, () => { disc(c, -12, -6, 9); disc(c, 12, -6, 9); poly(c, [[0, 6], [-5, 15], [5, 15]]);
      for (const x of [-9, 0, 9]) c.fillRect(x - 1.5, 24, 3, 9); });
  },
  bone(c) {
    c.save(); c.rotate(-0.6);
    c.fillRect(-30, -6, 60, 12);
    for (const x of [-32, 32]) { disc(c, x, -8, 10); disc(c, x, 8, 10); }
    c.restore();
  },
  cross(c) { c.fillRect(-8, -42, 16, 84); c.fillRect(-30, -24, 60, 16); },
  snow(c) {
    c.strokeStyle = '#fff';
    for (let i = 0; i < 6; i++) {
      c.save(); c.rotate(i * TAU / 6);
      stroke(c, 6, [[0, 0], [0, -42]]);
      stroke(c, 5, [[0, -26], [-11, -36]]); stroke(c, 5, [[0, -26], [11, -36]]);
      c.restore();
    }
  },
  bolt(c) { poly(c, [[10, -44], [-18, 4], [-2, 4], [-12, 44], [20, -8], [3, -8], [16, -44]]); },
  leaf(c) {
    c.beginPath(); c.moveTo(0, -44); c.bezierCurveTo(30, -24, 30, 22, 0, 40); c.bezierCurveTo(-30, 22, -30, -24, 0, -44); c.fill();
    hole(c, () => { c.lineWidth = 3; c.strokeStyle = '#000'; stroke(c, 3, [[0, -34], [0, 36]]);
      for (const y of [-14, 4, 20]) { stroke(c, 2.5, [[0, y + 6], [-13, y - 4]]); stroke(c, 2.5, [[0, y + 6], [13, y - 4]]); } });
  },
  feather(c) {
    c.save(); c.rotate(0.35);
    c.beginPath(); c.moveTo(0, -46); c.bezierCurveTo(22, -30, 20, 18, 3, 34); c.lineTo(-3, 34);
    c.bezierCurveTo(-18, 14, -20, -28, 0, -46); c.fill();
    hole(c, () => { stroke(c, 2.5, [[0, -38], [0, 30]]); for (const y of [-20, -4, 12]) stroke(c, 2, [[0, y], [14, y - 9]]); });
    c.fillRect(-1.5, 30, 3, 14);
    c.restore();
  },
  coin(c) {
    disc(c, 0, 0, 34);
    hole(c, () => { c.lineWidth = 4; c.beginPath(); c.arc(0, 0, 26, 0, TAU); c.stroke(); });
    poly(c, [[0, -14], [12, 0], [0, 14], [-12, 0]]);
  },
  die(c) {
    c.beginPath(); c.roundRect(-34, -34, 68, 68, 12); c.fill();
    hole(c, () => { for (const [x, y] of [[-17, -17], [17, -17], [0, 0], [-17, 17], [17, 17]]) disc(c, x, y, 7); });
  },
  rune(c) {
    c.strokeStyle = '#fff';
    stroke(c, 8, [[-12, -38], [-12, 38]]);
    stroke(c, 8, [[-12, -38], [16, -18], [-12, 2], [18, 38]]);
    stroke(c, 5, [[-30, 22], [-2, 22]]);
  },
  sun(c) {
    disc(c, 0, 0, 17);
    for (let i = 0; i < 8; i++) { c.save(); c.rotate(i * TAU / 8); poly(c, [[-6, -22], [0, -44], [6, -22]]); c.restore(); }
  },
  drop(c) { c.beginPath(); c.moveTo(0, -44); c.bezierCurveTo(14, -16, 26, 2, 26, 16); c.arc(0, 16, 26, 0, Math.PI); c.bezierCurveTo(-26, 2, -14, -16, 0, -44); c.fill(); },
  flame(c) {
    c.beginPath(); c.moveTo(0, -46); c.bezierCurveTo(10, -22, 30, -12, 28, 12); c.bezierCurveTo(26, 34, 8, 42, 0, 42);
    c.bezierCurveTo(-8, 42, -26, 34, -28, 12); c.bezierCurveTo(-30, -6, -14, -12, -8, -30);
    c.bezierCurveTo(-4, -18, 2, -14, 0, -46); c.fill();
    hole(c, () => { c.beginPath(); c.moveTo(0, 0); c.bezierCurveTo(10, 10, 14, 24, 0, 34); c.bezierCurveTo(-14, 24, -10, 10, 0, 0); c.fill(); });
  },
  petal(c) {
    c.beginPath(); c.moveTo(0, 40); c.bezierCurveTo(-36, 8, -26, -38, -6, -40); c.quadraticCurveTo(0, -30, 6, -40);
    c.bezierCurveTo(26, -38, 36, 8, 0, 40); c.fill();
  },
  shard(c) { poly(c, [[0, -46], [16, -12], [9, 42], [-9, 42], [-16, -12]]); hole(c, () => poly(c, [[0, -30], [4, -10], [0, 30], [-2, -10]])); },
  dagger(c) {
    c.save(); c.rotate(Math.PI / 4);
    poly(c, [[0, -46], [8, -14], [6, 12], [-6, 12], [-8, -14]]);
    c.fillRect(-20, 12, 40, 7); c.fillRect(-4, 19, 8, 18); disc(c, 0, 40, 6);
    c.restore();
  },
  eye(c) {
    c.beginPath(); c.moveTo(-44, 0); c.quadraticCurveTo(0, -38, 44, 0); c.quadraticCurveTo(0, 38, -44, 0); c.fill();
    hole(c, () => { c.beginPath(); c.moveTo(-34, 0); c.quadraticCurveTo(0, -27, 34, 0); c.quadraticCurveTo(0, 27, -34, 0); c.fill(); });
    disc(c, 0, 0, 15);
    hole(c, () => ellipse(c, 0, 0, 5, 11));
  },
  chevron(c) {
    for (const y of [-14, 16]) poly(c, [[-38, y + 6], [0, y - 22], [38, y + 6], [38, y + 22], [0, y - 6], [-38, y + 22]]);
  },
  paw(c) {
    ellipse(c, 0, 16, 20, 17);
    ellipse(c, -27, -6, 8, 11, -0.4); ellipse(c, -10, -26, 8, 12, -0.1); ellipse(c, 10, -26, 8, 12, 0.1); ellipse(c, 27, -6, 8, 11, 0.4);
  },
  wisp(c) {
    c.strokeStyle = '#fff';
    c.lineCap = 'round';
    for (let i = 0; i < 26; i++) {
      const a = i / 26 * TAU * 1.25, r = 6 + i * 1.35;
      c.lineWidth = 2 + i * 0.32;
      c.beginPath(); c.arc(0, 0, r, a, a + 0.32); c.stroke();
    }
    disc(c, 0, 0, 7);
  },
  ring(c) { c.strokeStyle = '#fff'; c.lineWidth = 7; c.beginPath(); c.arc(0, 0, 36, 0, TAU); c.stroke(); },
  // a bubble: a thin skin, a faint inside and a glint
  bubble(c) {
    c.fillStyle = 'rgba(255,255,255,0.16)'; c.beginPath(); c.arc(0, 0, 34, 0, TAU); c.fill();
    c.strokeStyle = '#fff'; c.lineWidth = 4; c.beginPath(); c.arc(0, 0, 34, 0, TAU); c.stroke();
    c.lineWidth = 6; c.lineCap = 'round'; c.beginPath(); c.arc(0, 0, 22, -2.6, -1.75); c.stroke();
  },
  // a sleeper's Z, a charm's heart, a silenced word (a speech bubble struck through)
  zzz(c) {
    c.strokeStyle = '#fff'; c.lineWidth = 9; c.lineJoin = 'round'; c.lineCap = 'round';
    c.beginPath(); c.moveTo(-26, -26); c.lineTo(26, -26); c.lineTo(-26, 26); c.lineTo(26, 26); c.stroke();
  },
  heart(c) {
    c.fillStyle = '#fff'; c.beginPath(); c.moveTo(0, 34);
    c.bezierCurveTo(-46, 4, -34, -38, 0, -16); c.bezierCurveTo(34, -38, 46, 4, 0, 34); c.fill();
  },
  hush(c) {
    c.strokeStyle = '#fff'; c.lineWidth = 6; c.lineJoin = 'round';
    c.beginPath(); c.moveTo(-34, -26); c.lineTo(34, -26); c.lineTo(34, 14); c.lineTo(-4, 14); c.lineTo(-18, 32); c.lineTo(-16, 14); c.lineTo(-34, 14); c.closePath(); c.stroke();
    c.lineWidth = 8; c.beginPath(); c.moveTo(-40, 36); c.lineTo(40, -36); c.stroke();
  },
};

function canvas(w, h) {
  if (typeof document !== 'undefined') { const cv = document.createElement('canvas'); cv.width = w; cv.height = h; return cv; }
  if (typeof OffscreenCanvas !== 'undefined') return new OffscreenCanvas(w, h);
  return null;
}

// draw one glyph centred at (x, y), `size` pixels across
export function drawGlyph(c, name, x, y, size, rot = 0) {
  const fn = DRAW[name];
  if (!fn) return;
  c.save();
  c.translate(x, y); c.rotate(rot); c.scale(size / 100, size / 100);
  c.fillStyle = '#fff'; c.strokeStyle = '#fff';
  fn(c);
  c.restore();
}

// every glyph in one canvas, ATLAS_COLS across, each softly glowing
export function glyphAtlas() {
  const rows = Math.ceil(GLYPHS.length / ATLAS_COLS);
  const cv = canvas(ATLAS_COLS * CELL, rows * CELL);
  if (!cv) return null;
  const c = cv.getContext('2d');
  GLYPHS.forEach((name, i) => {
    const x = (i % ATLAS_COLS + 0.5) * CELL, y = (Math.floor(i / ATLAS_COLS) + 0.5) * CELL;
    c.save();
    c.shadowColor = 'rgba(255,255,255,0.9)'; c.shadowBlur = CELL * 0.08;
    drawGlyph(c, name, x, y, CELL * 0.86);
    c.restore();
  });
  return cv;
}

// ---- ground sigils: drawn in a -100..100 box, radius ~96 ----
const ringLine = (c, r, w) => { c.lineWidth = w; c.beginPath(); c.arc(0, 0, r, 0, TAU); c.stroke(); };
const around = (n, fn, off = 0) => { for (let i = 0; i < n; i++) fn(off + i * TAU / n, i); };
function placeGlyph(c, name, a, r, size, turn = true) {
  drawGlyph(c, name, Math.sin(a) * r, -Math.cos(a) * r, size, turn ? a : 0);
}

export const SIGILS = {
  // warrior: a war circle — rank chevrons and blade marks around a shield
  crest(c) {
    ringLine(c, 94, 5); ringLine(c, 80, 2.5);
    around(24, a => { c.save(); c.rotate(a); c.fillRect(-1.6, -94, 3.2, 12); c.restore(); });
    around(4, a => placeGlyph(c, 'chevron', a, 64, 22), Math.PI / 4);
    c.beginPath(); c.moveTo(0, -46); c.lineTo(36, -32); c.quadraticCurveTo(34, 18, 0, 46); c.quadraticCurveTo(-34, 18, -36, -32); c.closePath();
    c.lineWidth = 6; c.stroke();
    c.lineWidth = 5; for (const s of [-1, 1]) { c.beginPath(); c.moveTo(-26 * s, -26); c.lineTo(26 * s, 26); c.stroke(); }
  },
  // paladin: the sun wheel
  sunwheel(c) {
    ringLine(c, 92, 6); ringLine(c, 58, 3);
    around(16, (a, i) => { c.save(); c.rotate(a); c.beginPath(); c.moveTo(-5, -60); c.lineTo(0, i % 2 ? -78 : -88); c.lineTo(5, -60); c.closePath(); c.fill(); c.restore(); });
    disc(c, 0, 0, 24);
    around(8, a => { c.save(); c.rotate(a); c.fillRect(-2, -54, 4, 26); c.restore(); });
  },
  // cleric: a rose window
  rosette(c) {
    ringLine(c, 94, 4); ringLine(c, 86, 2);
    around(8, a => placeGlyph(c, 'petal', a, 52, 46), 0);
    around(8, a => placeGlyph(c, 'feather', a, 82, 16), Math.PI / 8);
    c.lineWidth = 3; ringLine(c, 22, 3); disc(c, 0, 0, 10);
  },
  // mage: a rune circle with a hexagram
  runeCircle(c) {
    ringLine(c, 94, 4); ringLine(c, 74, 3);
    around(12, a => placeGlyph(c, 'rune', a, 84, 16));
    c.lineWidth = 3;
    for (const off of [0, Math.PI]) { c.beginPath(); around(3, (a, i) => { const x = Math.sin(a + off) * 72, y = -Math.cos(a + off) * 72; i ? c.lineTo(x, y) : c.moveTo(x, y); }); c.closePath(); c.stroke(); }
    ringLine(c, 30, 2.5); disc(c, 0, 0, 6);
  },
  // necromancer: skulls and bones
  boneCircle(c) {
    ringLine(c, 94, 3); ringLine(c, 70, 3);
    around(8, a => placeGlyph(c, 'skull', a, 82, 22, false));
    around(8, a => placeGlyph(c, 'bone', a, 82, 18), Math.PI / 8);
    c.lineWidth = 3; c.beginPath(); around(5, (a, i) => { const x = Math.sin(a * 2) * 66, y = -Math.cos(a * 2) * 66; i ? c.lineTo(x, y) : c.moveTo(x, y); }); c.closePath(); c.stroke();
  },
  // thief: a ring of coins and dice
  coinRing(c) {
    ringLine(c, 92, 3); ringLine(c, 62, 2);
    around(10, (a, i) => placeGlyph(c, i % 5 === 0 ? 'die' : 'coin', a, 77, 22, false));
    around(4, a => placeGlyph(c, 'coin', a, 30, 26, false), Math.PI / 4);
  },
  // assassin: the crosshair
  crosshair(c) {
    ringLine(c, 90, 4); ringLine(c, 40, 3);
    around(4, a => { c.save(); c.rotate(a); c.fillRect(-3, -98, 6, 46); c.fillRect(-2, -34, 4, 18); c.restore(); });
    around(4, a => { c.save(); c.rotate(a); c.fillRect(-1.5, -90, 3, 10); c.restore(); }, Math.PI / 4);
    disc(c, 0, 0, 5);
  },
  // ranger: a wreath of leaves
  leafRing(c) {
    ringLine(c, 70, 2);
    around(16, a => placeGlyph(c, 'leaf', a, 84, 22), 0);
    around(16, a => placeGlyph(c, 'leaf', a + 0.6, 60, 14), Math.PI / 16);
    placeGlyph(c, 'paw', 0, 0, 34, false);
  },
  // bard: a musical staff bent into a ring, notes riding it
  staffRing(c) {
    for (let i = 0; i < 5; i++) ringLine(c, 62 + i * 7, 2);
    around(7, (a, i) => placeGlyph(c, i % 2 ? 'notes' : 'note', a, 76, 22), 0.3);
    ringLine(c, 30, 3); placeGlyph(c, 'note', 0, 0, 30, false);
  },
  ring(c) { ringLine(c, 92, 6); ringLine(c, 80, 2); },
  frost(c) {
    ringLine(c, 92, 3);
    around(6, a => { c.save(); c.rotate(a);
      stroke(c, 5, [[0, 0], [0, -88]]);
      for (const y of [-30, -52, -72]) { stroke(c, 4, [[0, y], [-14, y - 14]]); stroke(c, 4, [[0, y], [14, y - 14]]); }
      c.restore(); });
  },
  scorch(c) {
    const g = c.createRadialGradient(0, 0, 10, 0, 0, 96);
    g.addColorStop(0, 'rgba(255,255,255,0.95)'); g.addColorStop(0.6, 'rgba(255,255,255,0.6)'); g.addColorStop(1, 'rgba(255,255,255,0)');
    c.fillStyle = g; disc(c, 0, 0, 96);
  },
  crack(c, rnd = Math.random) {
    c.lineCap = 'round';
    const branch = (x, y, a, len, w, depth) => {
      let px = x, py = y;
      const n = 5;
      for (let i = 0; i < n; i++) {
        a += (rnd() - 0.5) * 0.9;
        const nx = px + Math.sin(a) * len / n, ny = py - Math.cos(a) * len / n;
        c.lineWidth = w * (1 - i / n * 0.6);
        c.beginPath(); c.moveTo(px, py); c.lineTo(nx, ny); c.stroke();
        if (depth < 2 && rnd() < 0.35) branch(nx, ny, a + (rnd() < 0.5 ? -0.7 : 0.7), len * 0.45, w * 0.6, depth + 1);
        px = nx; py = ny;
      }
    };
    around(7, a => branch(0, 0, a + (rnd() - 0.5) * 0.5, 70 + rnd() * 26, 6, 0));
    disc(c, 0, 0, 10);
  },
};

// one sigil as a canvas (size px square); `seed` varies the cracks
export function sigilCanvas(name, size = 256, seed = 1) {
  const cv = canvas(size, size);
  if (!cv) return null;
  const c = cv.getContext('2d');
  c.translate(size / 2, size / 2);
  c.scale(size / 200, size / 200);
  c.fillStyle = '#fff'; c.strokeStyle = '#fff';
  c.shadowColor = 'rgba(255,255,255,0.8)'; c.shadowBlur = 4;
  let s = seed * 9301 + 49297;
  const rnd = () => { s = (s * 9301 + 49297) % 233280; return s / 233280; };
  (SIGILS[name] || SIGILS.ring)(c, rnd);
  return cv;
}

// a feathered wing (the left one; mirrored for the right), for the wings effect
export function wingCanvas(size = 256) {
  const cv = canvas(size, size);
  if (!cv) return null;
  const c = cv.getContext('2d');
  c.scale(size / 200, size / 200);
  c.fillStyle = '#fff';
  c.shadowColor = 'rgba(255,255,255,0.9)'; c.shadowBlur = 6;
  // feathers fan out from the root at the bottom right toward the upper left
  for (let i = 0; i < 9; i++) {
    const k = i / 8;
    c.save();
    c.translate(188, 170);
    c.rotate(-Math.PI * 0.18 - k * Math.PI * 0.42);
    const len = 170 - k * 70, w = 16 - k * 5;
    c.globalAlpha = 0.55 + (1 - k) * 0.45;
    c.beginPath(); c.moveTo(0, 0); c.quadraticCurveTo(w, -len * 0.5, 0, -len); c.quadraticCurveTo(-w, -len * 0.5, 0, 0); c.fill();
    c.restore();
  }
  return cv;
}

// a war banner's cloth: a coloured field, a pale border, the class's sigil in the middle and a
// swallow-tailed hem (transparent notch), for the banner effect
export function bannerCanvas(field = '#a8321e', sigil = 'crest', size = 256) {
  const cv = canvas(size, Math.round(size * 1.4));
  if (!cv) return null;
  const c = cv.getContext('2d'), w = cv.width, h = cv.height;
  c.fillStyle = field;
  c.beginPath(); c.moveTo(0, 0); c.lineTo(w, 0); c.lineTo(w, h); c.lineTo(w / 2, h * 0.84); c.lineTo(0, h); c.closePath(); c.fill();
  c.strokeStyle = 'rgba(255,240,210,0.9)'; c.lineWidth = w * 0.035;
  c.beginPath(); c.moveTo(w * 0.06, h * 0.03); c.lineTo(w * 0.94, h * 0.03); c.lineTo(w * 0.94, h * 0.93); c.lineTo(w / 2, h * 0.79); c.lineTo(w * 0.06, h * 0.93); c.closePath(); c.stroke();
  const s = sigilCanvas(sigil, Math.round(w * 0.8));
  if (s) c.drawImage(s, w * 0.1, h * 0.12);
  return cv;
}
