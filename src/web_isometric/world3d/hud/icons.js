// Painted icons, drawn in code when first needed (no image files), cached as data URLs.
//
// An ability's icon is composed from its own recipe (abilityfx-table.js), so every ability of
// every class gets one of its own: a gem of its school's colours, the class's sigil faint
// behind, a pictogram of what it does (the weapon it swings, what it throws, how it lands or
// what it leaves on you), a badge for how the body moves (a leap's arc, a blink, a spin) and a
// frame in the class's metal. Menu icons (helm, satchel, tome, scroll, map...) share the style.
import { RECIPES } from '../abilityfx-table.js';
import { recipeFor, THEMES } from '../abilityfx.js';
import { DRAW, drawGlyph, sigilCanvas } from '../glyphs.js';

const TAU = Math.PI * 2;
const SCHOOL_RGB = {
  fire: [255, 122, 42], frost: [140, 205, 255], lightning: [170, 195, 255], arcane: [176, 112, 255], holy: [255, 214, 120],
  shadow: [130, 74, 200], necrotic: [110, 230, 120], nature: [130, 210, 80], poison: [170, 230, 70], sound: [255, 120, 220],
  physical: [200, 200, 210], blood: [220, 40, 50],
};
const hex = n => [(n >> 16) & 255, (n >> 8) & 255, n & 255];
const rgb = (c, a = 1) => `rgba(${c[0] | 0},${c[1] | 0},${c[2] | 0},${a})`;
const mix = (a, b, k) => [a[0] + (b[0] - a[0]) * k, a[1] + (b[1] - a[1]) * k, a[2] + (b[2] - a[2]) * k];
const hash = s => { let h = 2166136261; for (const ch of String(s)) { h ^= ch.charCodeAt(0); h = Math.imul(h, 16777619); } return h >>> 0; };

function canvas(n) { const c = document.createElement('canvas'); c.width = c.height = n; return c; }
const fillPath = (c, pts) => { c.beginPath(); pts.forEach(([x, y], i) => (i ? c.lineTo(x, y) : c.moveTo(x, y))); c.closePath(); c.fill(); };
const line = (c, w, pts) => { c.lineWidth = w; c.lineCap = 'round'; c.lineJoin = 'round'; c.beginPath(); pts.forEach(([x, y], i) => (i ? c.lineTo(x, y) : c.moveTo(x, y))); c.stroke(); };
const disc = (c, x, y, r) => { c.beginPath(); c.arc(x, y, r, 0, TAU); c.fill(); };
const ring = (c, x, y, r, w) => { c.lineWidth = w; c.beginPath(); c.arc(x, y, r, 0, TAU); c.stroke(); };

// ---- pictograms: white shapes in a -50..50 box ----
export const PICTO = {
  sword(c) {
    c.save(); c.rotate(-Math.PI / 4);
    fillPath(c, [[0, -46], [7, -36], [6, 16], [-6, 16], [-7, -36]]);
    c.fillRect(-20, 16, 40, 7); c.fillRect(-4, 23, 8, 18); disc(c, 0, 44, 6);
    c.globalAlpha = .35; c.fillStyle = '#000'; c.fillRect(-1, -34, 2, 48); c.restore();
  },
  axe(c) {
    // a great axe: a broad crescent blade on a long haft
    c.save(); c.rotate(-Math.PI / 6);
    c.fillRect(-4, -40, 8, 88); disc(c, 0, 48, 6);
    c.beginPath(); c.moveTo(3, -40); c.bezierCurveTo(30, -50, 46, -30, 42, 4); c.bezierCurveTo(30, -6, 16, -4, 3, 2); c.closePath(); c.fill();
    c.beginPath(); c.moveTo(-3, -34); c.bezierCurveTo(-16, -36, -22, -26, -20, -16); c.bezierCurveTo(-14, -18, -8, -18, -3, -14); c.closePath(); c.fill();
    c.restore();
  },
  daggers(c) {
    for (const s of [-1, 1]) {
      c.save(); c.rotate(s * Math.PI / 4);
      fillPath(c, [[0, -44], [6, -30], [5, 8], [-5, 8], [-6, -30]]);
      c.fillRect(-14, 8, 28, 5); c.fillRect(-3, 13, 6, 14); disc(c, 0, 30, 4);
      c.restore();
    }
  },
  horseshoe(c) {
    // a horseshoe, open end down, its nail holes dark (the ride / dismount button)
    c.lineWidth = 16; c.lineCap = 'butt'; c.strokeStyle = c.fillStyle;
    c.beginPath(); c.arc(0, -6, 30, Math.PI * 0.82, Math.PI * 2.18); c.stroke();
    c.fillRect(-36, 8, 14, 30); c.fillRect(22, 8, 14, 30);
    c.save(); c.globalCompositeOperation = 'destination-out';
    for (const a of [1.05, 1.35, 1.65, 1.95]) disc(c, Math.cos(Math.PI * a) * 30, -6 + Math.sin(Math.PI * a) * 30, 3);
    for (const s of [-1, 1]) disc(c, s * 29, 22, 3);
    c.restore();
  },
  boot(c) { fillPath(c, [[-14, -40], [10, -40], [10, 6], [34, 14], [38, 30], [-16, 30], [-18, 10]]); c.fillRect(-18, 32, 58, 7); },
  fist(c) {
    c.beginPath(); c.roundRect(-26, -18, 52, 44, 12); c.fill();
    for (let i = 0; i < 4; i++) { c.beginPath(); c.roundRect(-26 + i * 13, -34, 12, 22, 6); c.fill(); }
    c.beginPath(); c.roundRect(-38, -8, 16, 26, 7); c.fill();
  },
  bow(c) {
    c.strokeStyle = '#fff';
    c.lineWidth = 7; c.lineCap = 'round'; c.beginPath(); c.arc(-50, 0, 58, -0.85, 0.85); c.stroke();
    line(c, 2.5, [[-11, -43], [-11, 43]]);
    line(c, 4, [[-30, 0], [40, 0]]); fillPath(c, [[44, 0], [32, -7], [32, 7]]);
    fillPath(c, [[-30, 0], [-38, -8], [-30, -8], [-24, 0], [-30, 8], [-38, 8]]);
  },
  arrow(c) {
    c.save(); c.rotate(-Math.PI / 4);
    c.fillRect(-2.5, -30, 5, 70); fillPath(c, [[0, -46], [10, -28], [-10, -28]]);
    fillPath(c, [[0, 30], [10, 44], [3, 44], [0, 38], [-3, 44], [-10, 44]]);
    c.restore();
  },
  arrows(c) { for (const a of [-0.35, 0, 0.35]) { c.save(); c.rotate(a); c.scale(0.8, 0.8); c.translate(0, 6); PICTO.arrowUp(c); c.restore(); } },
  arrowUp(c) { c.fillRect(-2.5, -30, 5, 70); fillPath(c, [[0, -46], [10, -28], [-10, -28]]); },
  rain(c) { for (const [x, y] of [[-26, -18], [0, -30], [26, -14], [-12, 8], [16, 16]]) { c.save(); c.translate(x, y); c.rotate(Math.PI + 0.25); c.scale(0.42, 0.42); PICTO.arrowUp(c); c.restore(); } },
  orb(c) {
    const g = c.createRadialGradient(-10, -10, 2, 0, 0, 32); g.addColorStop(0, '#fff'); g.addColorStop(.6, 'rgba(255,255,255,.85)'); g.addColorStop(1, 'rgba(255,255,255,0)');
    c.fillStyle = g; disc(c, 0, 0, 32); c.fillStyle = '#fff';
    c.globalAlpha = .7; c.strokeStyle = '#fff'; c.lineWidth = 3; c.beginPath(); c.arc(0, 0, 40, -2.2, -0.7); c.stroke(); c.beginPath(); c.arc(0, 0, 40, 0.9, 2.4); c.stroke(); c.globalAlpha = 1;
  },
  orbs(c) { for (const [x, y, r] of [[-22, 14, 14], [4, -18, 17], [26, 16, 12]]) disc(c, x, y, r); c.globalAlpha = .45; line(c, 3, [[-40, 34], [-22, 14]]); line(c, 3, [[-22, 38], [4, -18]]); c.globalAlpha = 1; },
  beam(c) { c.fillRect(-9, -48, 18, 96); c.globalAlpha = .45; c.fillRect(-17, -48, 34, 96); c.globalAlpha = 1; disc(c, 0, 34, 14); },
  chain(c) {
    c.strokeStyle = '#fff'; c.lineWidth = 7;
    for (const [x, y] of [[-24, 22], [0, 0], [24, -22]]) { c.save(); c.translate(x, y); c.rotate(-Math.PI / 4); c.beginPath(); c.ellipse(0, 0, 18, 9, 0, 0, TAU); c.stroke(); c.restore(); }
  },
  tether(c) {
    c.strokeStyle = '#fff'; c.lineWidth = 6; c.lineCap = 'round';
    c.beginPath(); c.moveTo(-40, 26); c.bezierCurveTo(-16, -40, 16, 40, 40, -26); c.stroke();
    disc(c, -40, 26, 9); disc(c, 40, -26, 9);
    for (const t of [0.3, 0.5, 0.7]) disc(c, -40 + 80 * t, 26 - 52 * t + Math.sin(t * Math.PI * 2) * 6, 4);
  },
  meteor(c) {
    disc(c, 16, 16, 20);
    c.globalAlpha = .55; fillPath(c, [[2, 4], [-44, -40], [-30, -44], [10, -6]]); fillPath(c, [[24, 0], [-14, -46], [-2, -48], [32, 4]]); c.globalAlpha = 1;
  },
  wave(c) { c.strokeStyle = '#fff'; c.lineCap = 'round'; for (const [y, w] of [[-18, 7], [2, 6], [22, 5]]) { c.lineWidth = w; c.beginPath(); c.moveTo(-42, y); for (let x = -42; x <= 42; x += 4) c.lineTo(x, y + Math.sin(x / 9) * 8); c.stroke(); } },
  fan(c) { c.beginPath(); c.moveTo(-36, 30); c.arc(-36, 30, 80, -1.35, -0.2); c.closePath(); c.globalAlpha = .45; c.fill(); c.globalAlpha = 1; for (const a of [-1.2, -0.78, -0.36]) line(c, 5, [[-36, 30], [-36 + Math.cos(a) * 76, 30 + Math.sin(a) * 76]]); },
  shield(c) {
    c.beginPath(); c.moveTo(0, -44); c.lineTo(36, -30); c.quadraticCurveTo(34, 22, 0, 46); c.quadraticCurveTo(-34, 22, -36, -30); c.closePath(); c.fill();
    c.globalCompositeOperation = 'destination-out'; c.lineWidth = 4; c.beginPath(); c.moveTo(0, -34); c.lineTo(26, -24); c.quadraticCurveTo(24, 16, 0, 35); c.quadraticCurveTo(-24, 16, -26, -24); c.closePath(); c.stroke();
    c.globalCompositeOperation = 'source-over';
  },
  burst(c) { for (let i = 0; i < 12; i++) { c.save(); c.rotate(i * TAU / 12); fillPath(c, [[-5, -16], [0, i % 2 ? -36 : -46], [5, -16]]); c.restore(); } disc(c, 0, 0, 15); },
  blast(c) { PICTO.burst(c); c.globalAlpha = .4; ring(c, 0, 0, 40, 4); c.globalAlpha = 1; },
  crack(c) {
    c.strokeStyle = '#fff'; c.lineJoin = 'round';
    line(c, 6, [[0, -44], [-8, -20], [6, -4], [-6, 14], [4, 44]]); line(c, 4, [[-8, -20], [-30, -28]]); line(c, 4, [[6, -4], [32, 4]]); line(c, 3, [[-6, 14], [-30, 30]]);
    c.fillRect(-46, 40, 92, 6);
  },
  vines(c) {
    c.strokeStyle = '#fff'; c.lineCap = 'round';
    for (const [x, k] of [[-20, 1], [10, -1], [32, 1]]) { c.lineWidth = 5; c.beginPath(); c.moveTo(x, 46); c.bezierCurveTo(x + 18 * k, 18, x - 18 * k, -6, x + 6 * k, -40); c.stroke(); }
    for (const [x, y, a] of [[-10, 8, 0.6], [16, -14, -0.6], [36, 0, 0.6], [-24, -18, -0.6]]) { c.save(); c.translate(x, y); c.rotate(a); c.scale(0.28, 0.28); DRAW.leaf(c); c.restore(); }
  },
  spikes(c) { for (const [x, h] of [[-30, 50], [-10, 72], [10, 58], [30, 80]]) fillPath(c, [[x - 9, 44], [x, 44 - h], [x + 9, 44]]); c.fillRect(-46, 42, 92, 6); },
  cage(c) { for (const x of [-30, -15, 0, 15, 30]) c.fillRect(x - 3, -40, 6, 82); c.fillRect(-40, -44, 80, 7); c.fillRect(-40, 38, 80, 7); },
  rock(c) { fillPath(c, [[-34, 30], [-38, 0], [-20, -26], [6, -34], [32, -16], [38, 18], [20, 34]]); c.globalCompositeOperation = 'destination-out'; line(c, 3, [[-20, -26], [-6, 4], [20, 34]]); line(c, 3, [[-6, 4], [32, -16]]); c.globalCompositeOperation = 'source-over'; },
  crosshair(c) { c.strokeStyle = '#fff'; ring(c, 0, 0, 30, 6); ring(c, 0, 0, 12, 4); for (const a of [0, 1, 2, 3]) { c.save(); c.rotate(a * Math.PI / 2); c.fillRect(-3, -48, 6, 22); c.restore(); } disc(c, 0, 0, 4); },
  fountain(c) { for (const [x, h] of [[-18, 30], [0, 44], [18, 30]]) { c.globalAlpha = .9; fillPath(c, [[x - 6, 40], [x, 40 - h], [x + 6, 40]]); } c.globalAlpha = 1; for (const [x, y] of [[-30, -6], [30, -6], [-12, -30], [12, -30]]) disc(c, x, y, 5); c.fillRect(-40, 38, 80, 7); },
  halo(c) { c.strokeStyle = '#fff'; c.lineWidth = 7; c.beginPath(); c.ellipse(0, -26, 34, 12, 0, 0, TAU); c.stroke(); disc(c, 0, 16, 18); fillPath(c, [[-28, 46], [-18, 26], [18, 26], [28, 46]]); },
  wings(c) {
    for (const s of [-1, 1]) {
      c.save(); c.scale(s, 1);
      for (let i = 0; i < 5; i++) { c.save(); c.translate(8, 6); c.rotate(-0.5 - i * 0.24); c.beginPath(); c.ellipse(18 + i * 2, 0, 24 - i * 2, 6, 0, 0, TAU); c.fill(); c.restore(); }
      c.restore();
    }
    disc(c, 0, 4, 8);
  },
  banner(c) {
    c.fillRect(-26, -46, 6, 94); disc(c, -23, -46, 6);
    fillPath(c, [[-20, -38], [34, -38], [34, 22], [7, 10], [-20, 22]]);
    c.globalCompositeOperation = 'destination-out';
    c.save(); c.translate(7, -12); c.scale(0.3, 0.3); DRAW.chevron(c); c.restore();
    c.globalCompositeOperation = 'source-over';
  },
  implode(c) {
    // eight chevrons pointing in at a hollow black core
    for (let i = 0; i < 8; i++) { c.save(); c.rotate(i * TAU / 8); fillPath(c, [[-10, -47], [0, -31], [10, -47], [0, -41]]); c.restore(); }
    disc(c, 0, 0, 21);
    c.globalCompositeOperation = 'destination-out'; disc(c, 0, 0, 13); c.globalCompositeOperation = 'source-over';
    disc(c, 0, 0, 5);
  },
  seraph(c) {
    // a figure with a halo and great swept wings
    for (const s of [-1, 1]) {
      c.save(); c.scale(s, 1);
      for (let i = 0; i < 4; i++) { c.save(); c.translate(6, -4); c.rotate(-0.95 - i * 0.3); c.beginPath(); c.ellipse(24 + i * 2, 0, 26 - i * 3, 5.5, 0, 0, TAU); c.fill(); c.restore(); }
      c.restore();
    }
    disc(c, 0, -14, 9);
    fillPath(c, [[-11, -2], [11, -2], [17, 44], [-17, 44]]);
    c.strokeStyle = '#fff'; c.lineWidth = 4.5; c.beginPath(); c.ellipse(0, -31, 14, 5, 0, 0, TAU); c.stroke();
  },
  pierce(c) {
    // an arrow straight through two rings
    c.strokeStyle = '#fff'; c.lineWidth = 6;
    for (const x of [-12, 16]) { c.beginPath(); c.ellipse(x, 0, 9, 22, 0, 0, TAU); c.stroke(); }
    c.fillRect(-46, -3, 84, 6);
    fillPath(c, [[38, -12], [50, 0], [38, 12]]);
    fillPath(c, [[-46, -3], [-54, -12], [-40, -3]]); fillPath(c, [[-46, 3], [-54, 12], [-40, 3]]);
  },
  clones(c) {
    // three hooded shapes, one in front
    for (const [x, y, s, a] of [[-24, -4, 0.62, 0.55], [24, -4, 0.62, 0.55], [0, 6, 0.8, 1]]) {
      c.save(); c.translate(x, y); c.scale(s, s); c.globalAlpha = a;
      c.beginPath(); c.moveTo(0, -46); c.bezierCurveTo(30, -42, 36, 6, 32, 46); c.lineTo(-32, 46); c.bezierCurveTo(-36, 6, -30, -42, 0, -46); c.fill();
      c.restore();
    }
    c.globalAlpha = 1;
  },
  lich(c) {
    // a skull wearing a crown
    c.save(); c.translate(0, 12); c.scale(0.68, 0.68); DRAW.skull(c); c.restore();
    fillPath(c, [[-26, -16], [-26, -40], [-14, -28], [-6, -46], [0, -30], [6, -46], [14, -28], [26, -40], [26, -16]]);
  },
  hood(c) {
    c.beginPath(); c.moveTo(0, -44); c.bezierCurveTo(34, -40, 40, 6, 36, 44); c.lineTo(-36, 44); c.bezierCurveTo(-40, 6, -34, -40, 0, -44); c.fill();
    c.globalCompositeOperation = 'destination-out'; c.beginPath(); c.ellipse(0, -2, 18, 24, 0, 0, TAU); c.fill(); c.globalCompositeOperation = 'source-over';
    c.globalAlpha = .9; disc(c, -7, -4, 3.5); disc(c, 7, -4, 3.5); c.globalAlpha = 1;
  },
  mirror(c) {
    for (const [x, a] of [[-16, 0.45], [16, 1]]) {
      c.globalAlpha = a; disc(c, x, -24, 11); c.beginPath(); c.moveTo(x - 18, 42); c.quadraticCurveTo(x - 18, -8, x, -10); c.quadraticCurveTo(x + 18, -8, x + 18, 42); c.closePath(); c.fill();
    }
    c.globalAlpha = 1;
  },
  smoke(c) { for (const [x, y, r] of [[-20, 10, 18], [6, -4, 22], [26, 14, 16], [-2, 22, 18]]) disc(c, x, y, r); },
  rings(c) { c.strokeStyle = '#fff'; c.lineCap = 'round'; for (const r of [14, 28, 42]) { c.lineWidth = 5; c.beginPath(); c.arc(-30, 0, r, -0.8, 0.8); c.stroke(); } disc(c, -30, 0, 6); },
  cross(c) { c.fillRect(-11, -42, 22, 84); c.fillRect(-42, -11, 84, 22); },
  heal(c) { PICTO.cross(c); c.globalAlpha = .45; ring(c, 0, 0, 44, 4); c.globalAlpha = 1; },
  swirl(c) { c.save(); c.scale(1.1, 1.1); DRAW.wisp(c); c.restore(); },
  pillar(c) { PICTO.beam(c); },
  book(c) {
    c.beginPath(); c.roundRect(-38, -32, 76, 64, 6); c.fill();
    c.globalCompositeOperation = 'destination-out'; line(c, 3, [[0, -28], [0, 30]]);
    for (const y of [-16, -4, 8]) { line(c, 2.5, [[-30, y], [-8, y]]); line(c, 2.5, [[8, y], [30, y]]); }
    c.globalCompositeOperation = 'source-over';
  },
  satchel(c) {
    c.beginPath(); c.roundRect(-38, -16, 76, 56, 10); c.fill();
    c.strokeStyle = '#fff'; c.lineWidth = 6; c.beginPath(); c.arc(0, -16, 22, Math.PI, 0); c.stroke();
    c.globalCompositeOperation = 'destination-out'; c.beginPath(); c.roundRect(-30, -10, 60, 20, 6); c.fill(); c.globalCompositeOperation = 'source-over';
    c.fillRect(-6, -6, 12, 18);
  },
  helm(c) {
    c.beginPath(); c.moveTo(-34, 30); c.lineTo(-34, -6); c.bezierCurveTo(-34, -46, 34, -46, 34, -6); c.lineTo(34, 30); c.lineTo(10, 30); c.lineTo(10, 4); c.lineTo(-10, 4); c.lineTo(-10, 30); c.closePath(); c.fill();
    c.globalCompositeOperation = 'destination-out'; c.fillRect(-26, -10, 52, 6); c.globalCompositeOperation = 'source-over';
    c.fillRect(-3, -46, 6, 14);
  },
  scroll(c) {
    c.beginPath(); c.roundRect(-30, -36, 60, 72, 4); c.fill();
    disc(c, -30, -36, 8); disc(c, 30, -36, 8); disc(c, -30, 36, 8); disc(c, 30, 36, 8);
    c.globalCompositeOperation = 'destination-out'; for (const y of [-20, -8, 4, 16]) line(c, 3, [[-18, y], [18, y]]); c.globalCompositeOperation = 'source-over';
  },
  map(c) {
    fillPath(c, [[-42, -30], [-14, -40], [14, -30], [42, -40], [42, 34], [14, 44], [-14, 34], [-42, 44]]);
    c.globalCompositeOperation = 'destination-out'; line(c, 2.5, [[-14, -40], [-14, 34]]); line(c, 2.5, [[14, -30], [14, 44]]);
    c.setLineDash([5, 5]); line(c, 3, [[-32, 26], [-6, 0], [22, 10], [34, -24]]); c.setLineDash([]); c.globalCompositeOperation = 'source-over';
  },
  question(c) { c.font = 'bold 92px Georgia, serif'; c.textAlign = 'center'; c.textBaseline = 'middle'; c.fillText('?', 0, 6); },
  gear(c) {
    for (let i = 0; i < 8; i++) { c.save(); c.rotate(i * TAU / 8); c.fillRect(-7, -44, 14, 16); c.restore(); }
    disc(c, 0, 0, 32); c.globalCompositeOperation = 'destination-out'; disc(c, 0, 0, 13); c.globalCompositeOperation = 'source-over';
  },
  armor(c) {
    fillPath(c, [[-18, -40], [18, -40], [40, -26], [32, 0], [24, -6], [24, 42], [-24, 42], [-24, -6], [-32, 0], [-40, -26]]);
    c.globalCompositeOperation = 'destination-out'; line(c, 3, [[0, -40], [0, 40]]); line(c, 3, [[-24, 10], [24, 10]]); c.globalCompositeOperation = 'source-over';
  },
  flee(c) {
    disc(c, 10, -32, 9);
    fillPath(c, [[4, -20], [20, -18], [26, 4], [14, 2], [10, 22], [26, 44], [14, 46], [0, 28], [-12, 46], [-24, 42], [-6, 18], [-2, -2], [-16, 6], [-24, -2]]);
    for (const y of [-6, 8, 22]) { c.globalAlpha = .5; c.fillRect(-46, y, 18, 4); }
    c.globalAlpha = 1;
  },
  people(c) {
    for (const [x, s, a] of [[-22, .8, .6], [22, .8, .6], [0, 1, 1]]) {
      c.globalAlpha = a; c.save(); c.translate(x, 6); c.scale(s, s);
      disc(c, 0, -26, 14); c.beginPath(); c.moveTo(-24, 40); c.quadraticCurveTo(-24, -6, 0, -8); c.quadraticCurveTo(24, -6, 24, 40); c.closePath(); c.fill();
      c.restore();
    }
    c.globalAlpha = 1;
  },
};

// a picture of their own for abilities of one class that would otherwise look alike
// ({picto: PICTO name} or {glyph: glyphs.js name})
export const ICON_OVERRIDE = {
  warrior: {
    cleave: {picto: 'sword'}, heroic_leap: {picto: 'arrowUp'}, heroic_throw: {picto: 'tether'}, rallying_cry: {picto: 'banner'},
    mortal_strike: {picto: 'sword'}, protect: {picto: 'shield'},
  },
  paladin: {
    unfettered: {picto: 'chain'}, lay_on_hands: {glyph: 'cross'}, holy_shield: {picto: 'armor'},
    protect: {picto: 'helm'}, avenging_wrath: {picto: 'banner'}, ascendant_hour: {picto: 'people'},
    verdict_of_the_order: {glyph: 'sun'}, beacon_of_light: {glyph: 'star'}, layhands: {glyph: 'drop'},
    shield_of_faith: {glyph: 'ring'}, divine_shield: {picto: 'cage'}, divine_shield_master: {picto: 'wings'},
    divine_guardian: {glyph: 'feather'},
  },
  cleric: {
    dispel_evil: {glyph: 'cross'}, group_heal: {picto: 'heal'}, divine_hymn: {glyph: 'notes'},
    heal: {glyph: 'cross'}, summon: {glyph: 'skull'}, word_of_recall: {picto: 'burst'},
    resurrect: {glyph: 'sun'}, cure_serious: {glyph: 'drop'}, cure_critical: {picto: 'fountain'},
    renew: {glyph: 'petal'}, shield_of_faith: {picto: 'armor'}, divine_shield: {picto: 'helm'},
    power_word_shield: {picto: 'rings'}, aegis_ward: {glyph: 'ring'}, cleansing_rite: {glyph: 'sun'},
    font_of_the_vigil: {glyph: 'drop'}, shadow_word_pain: {picto: 'rings'}, inner_focus: {glyph: 'eye'},
    holy_aura: {glyph: 'feather'}, protection_from_evil: {picto: 'cage'}, pain_suppression: {glyph: 'wisp'},
    guardian_spirit: {glyph: 'bone'}, break_door: {picto: 'crack'},
  },
  mage: {
    enchant_weapon: {picto: 'sword'}, tower_echoes: {picto: 'rings'}, phase_step: {glyph: 'wisp'},
    stepwise: {picto: 'boot'}, arcane_power: {picto: 'fist'}, magic_missile: {picto: 'arrows'},
    arcane_missiles: {picto: 'blast'}, summon: {picto: 'people'}, singularity: {glyph: 'ring'},
    rimeheart: {picto: 'crack'}, deep_freeze: {picto: 'cage'}, pyroblast: {picto: 'blast'},
    identify: {picto: 'book'}, meteor_storm: {picto: 'rain'}, shield: {picto: 'armor'},
    mana_shield: {picto: 'helm'}, resonance_burst: {glyph: 'sun'}, block_door: {picto: 'chain'},
  },
  necromancer: {
    imbue: {glyph: 'rune'}, soulstone: {picto: 'lich'}, leechcraft: {glyph: 'drop'},
    energy_drain: {picto: 'arrows'}, dark_mending: {picto: 'heal'}, siphon_unlife: {picto: 'implode'},
    soul_harvest: {picto: 'people'}, ritual: {picto: 'rings'}, mistgrasp: {glyph: 'star'},
    corpse_shield: {picto: 'shield'}, mass_animate: {glyph: 'wisp'}, curse: {glyph: 'eye'},
    animate: {picto: 'clones'}, raise: {picto: 'arrowUp'},
  },
  thief: {
    jackpot: {picto: 'crosshair'}, circle: {picto: 'sword'}, eviscerate: {picto: 'axe'},
    knife_toss: {glyph: 'dagger'}, kidneyshot: {picto: 'crack'}, fade: {glyph: 'wisp'}, marked_for_death_thief: {glyph: 'skull'},
    shadow_step: {picto: 'boot'}, cover_tracks: {glyph: 'paw'},
  },
  assassin: {
    execute_contract: {picto: 'sword'}, feint: {picto: 'axe'}, shadowstrike: {picto: 'pierce'},
    fan_of_knives: {picto: 'fan'}, death_mark: {glyph: 'skull'}, rupture: {glyph: 'drop'},
    shadow_blades_master: {glyph: 'wisp'}, hide: {glyph: 'wisp'}, envenom: {glyph: 'star'},
    cover_tracks: {glyph: 'paw'},
  },
  ranger: {
    bestial_wrath: {picto: 'banner'}, briskness: {glyph: 'chevron'}, detect_magic: {picto: 'book'},
    volley: {picto: 'arrows'}, wyvern_sting: {glyph: 'drop'}, stampede: {picto: 'horseshoe'},
  },
  bard: {
    pick_lock: {glyph: 'coin'}, lore: {picto: 'book'}, polymorph: {picto: 'swirl'},
    mesmerize: {glyph: 'petal'}, charm_person: {glyph: 'die'}, epic_tale: {picto: 'scroll'},
    song_of_battle: {picto: 'banner'}, perform: {glyph: 'star'}, invisibility: {picto: 'smoke'},
    magnum_opus: {glyph: 'sun'}, mass_charm: {glyph: 'skull'}, refrain_of_hope: {picto: 'arrows'},
    chord_of_disruption: {glyph: 'bone'}, bless: {glyph: 'sun'}, legend_lore: {glyph: 'eye'},
    identify: {picto: 'question'}, anthem_of_defense: {glyph: 'notes'}, discordant_chord: {glyph: 'cross'},
    grand_illusion: {picto: 'rings'},
  },
};

// which pictogram shows what an ability does: what it throws, else how it lands, else what it
// leaves on you; a weapon blow shows the class's weapon
function pictoFor(r, cls) {
  const t = r.travel, l = r.land, a = r.aura;
  // a marquee ability is its centrepiece: the banner, the seraph, the lich
  if (a && ['banner', 'seraph', 'lich'].includes(a.kind)) return { picto: a.kind };
  const weapon = /^d/.test(r.clip) ? 'daggers' : /2$/.test(r.clip) && !/^bow|^aim/.test(r.clip) ? 'axe'
    : r.clip === 'kick' ? 'boot' : r.clip === 'punch' ? 'fist' : /^bow|^aim/.test(r.clip) ? 'bow' : 'sword';
  if (t) {
    const map = { slash: weapon, orb: 'orb', orbs: 'orbs', bolt: 'bolt', sky: 'bolt', chain: 'chain', ray: 'beam', skyray: 'beam',
      tether: 'tether', link: 'tether', arrow: 'bow', arrows: 'arrows', rain: 'rain', rainglyph: 'rain', meteor: 'meteor', meteors: 'meteor',
      wave: 'wave', cone: 'fan', blade: 'dagger', blades: 'daggers', shards: 'shard', pierce: 'pierce' };
    if (t.kind === 'glyph' || t.kind === 'motif') return { glyph: t.arg || (t.kind === 'glyph' ? THEMES[cls].glyph : THEMES[cls].motif) };
    const p = map[t.kind];
    if (p === 'bolt' || p === 'dagger' || p === 'shard') return { glyph: p };
    return { picto: p || weapon };
  }
  if (l) {
    const map = { hit: weapon, sparks: weapon, nova: 'burst', blast: 'blast', pillar: 'pillar', crack: 'crack', quake: 'crack',
      bubble: 'shield', dome: 'shield', mark: 'crosshair', swirl: 'swirl', geyser: 'fountain', fountain: 'fountain', halo: 'halo',
      wings: 'wings', smoke: 'smoke', rings: 'rings', heal: 'heal', cloud: 'smoke', implode: 'implode', clones: 'clones' };
    if (l.kind === 'growth') return { picto: { vines: 'vines', bones: 'spikes', ice: 'spikes', crystals: 'spikes', bars: 'cage', thorns: 'spikes', stones: 'rock', spikes: 'spikes', spears: 'spikes' }[l.arg] || 'spikes' };
    if (l.kind === 'burst' || l.kind === 'motifs') return { glyph: l.arg || (l.kind === 'burst' ? THEMES[cls].glyph : THEMES[cls].motif) };
    if (l.kind === 'freeze') return { glyph: 'snow' };
    if (l.kind === 'shatter') return { glyph: 'shard' };
    if (l.kind === 'sigil') return { sigil: true };
    if (l.kind === 'mark' && l.arg) return { glyph: l.arg };
    if (l.kind === 'fountain' && l.arg) return { glyph: l.arg };
    return { picto: map[l.kind] || weapon };
  }
  if (a) {
    const map = { banner: 'banner', fade: 'hood', shroud: 'hood', mirror: 'mirror', glow: 'fist', rage: 'fist', bubble: 'shield',
      halo: 'halo', wings: 'wings', sigil: null, smoke: 'smoke', seraph: 'seraph', lich: 'lich' };
    const glyphs = { frost: 'snow', flames: 'flame', notes: 'notes', leaves: 'leaf', stone: null, bark: 'leaf', ghost: 'wisp', motes: 'star',
      poison: 'drop', bleed: 'drop', embers: 'flame', runes: 'rune', blades: 'dagger' };
    if (a.kind === 'orbit') return { glyph: a.arg || THEMES[cls].glyph, orbit: true };
    if (a.kind === 'stone') return { picto: 'rock' };
    if (a.kind === 'sigil') return { sigil: true };
    if (glyphs[a.kind]) return { glyph: glyphs[a.kind], orbit: a.kind === 'runes' || a.kind === 'blades' };
    return { picto: map[a.kind] || 'burst' };
  }
  if (r.cast) return { glyph: THEMES[cls].glyph };
  return { picto: weapon };
}

// a little badge in the corner: how the body moves
function motionBadge(c, motion, S) {
  if (!motion) return;
  c.save();
  c.translate(S * 0.79, S * 0.79);
  c.fillStyle = 'rgba(10,8,6,.78)'; disc(c, 0, 0, S * 0.15);
  c.strokeStyle = '#ffe9b0'; c.fillStyle = '#ffe9b0'; c.lineWidth = S * 0.025; c.lineCap = 'round';
  const k = S * 0.09;
  c.beginPath();
  switch (motion) {
    case 'leap': c.arc(0, k * 0.4, k, Math.PI * 1.05, Math.PI * 1.95); c.stroke(); fillPath(c, [[k, k * 0.2], [k * 0.5, -k * 0.1], [k * 1.2, -k * 0.35]]); break;
    case 'dash': case 'lunge': for (const y of [-0.5, 0, 0.5]) line(c, S * 0.022, [[-k, y * k], [k * 0.6, y * k]]); fillPath(c, [[k * 1.1, 0], [k * 0.5, -k * 0.5], [k * 0.5, k * 0.5]]); break;
    case 'blink': c.setLineDash([S * 0.03, S * 0.025]); c.arc(0, 0, k, 0, TAU); c.stroke(); c.setLineDash([]); disc(c, 0, 0, k * 0.35); break;
    case 'blinks': c.setLineDash([S * 0.025, S * 0.02]); c.arc(-k * 0.45, 0, k * 0.7, 0, TAU); c.stroke(); c.beginPath(); c.arc(k * 0.55, 0, k * 0.7, 0, TAU); c.stroke(); c.setLineDash([]); disc(c, k * 0.55, 0, k * 0.28); break;
    case 'spin': case 'spin2': c.arc(0, 0, k, 0.3, Math.PI * 1.7); c.stroke(); fillPath(c, [[k * 0.95, -k * 0.55], [k * 1.35, -k * 0.05], [k * 0.45, -k * 0.05]]); break;
    case 'rise': case 'hover': case 'hop': line(c, S * 0.025, [[0, k], [0, -k * 0.6]]); fillPath(c, [[0, -k * 1.1], [-k * 0.6, -k * 0.3], [k * 0.6, -k * 0.3]]); break;
    case 'backstep': line(c, S * 0.025, [[k, 0], [-k * 0.6, 0]]); fillPath(c, [[-k * 1.1, 0], [-k * 0.3, -k * 0.6], [-k * 0.3, k * 0.6]]); break;
    case 'sidestep': line(c, S * 0.025, [[0, -k], [0, k]]); line(c, S * 0.025, [[-k, 0], [k, 0]]); break;
    default: break;
  }
  c.restore();
}

const cache = new Map();

// What an ability's icon shows, and in what colour: the picture its recipe suggests, unless two
// of a class's abilities would then look alike (stepwise and tower echoes both fell back to the
// mage's rune): those get a picture of their own (ICON_OVERRIDE; the animations are untouched).
// tests/web/icons.test.mjs keeps every class's icons distinct.
export function iconOf(id, cls, type = 'skill') {
  cls = THEMES[String(cls || '').toLowerCase()] ? String(cls).toLowerCase() : 'creature';
  const theme = THEMES[cls] || THEMES.creature;
  const r = recipeFor(RECIPES, id, cls, { k: type === 'spell' ? 'spell' : 'ability' });
  const cc = hex(theme.core), ac = hex(theme.accent);
  // the gem's colour: an element's own (fire, frost...) when it has one; else the class's two
  // tones — its main colour for blows and bolts, its second for wards, heals and help
  const guard = r.flags.has('ally') || ['bubble', 'banner', 'seraph', 'halo', 'wings', 'sigil', 'glow', 'stone', 'bark', 'mirror', 'fade', 'shroud'].includes(r.aura && r.aura.kind)
    || ['heal', 'bubble', 'dome', 'halo', 'wings', 'pillar'].includes(r.land && r.land.kind);
  const sc = r.school && SCHOOL_RGB[r.school] ? SCHOOL_RGB[r.school] : guard ? ac : cc;
  const own = (ICON_OVERRIDE[cls] || {})[id];
  return { r, theme, cc, ac, sc, p: own ? { ...own } : pictoFor(r, cls) };
}

// an ability's icon (a data URL), `cls` the class it is drawn for, `type` spell | skill
export function abilityIcon(id, cls, { type = 'skill', passive = false, size = 96 } = {}) {
  cls = THEMES[String(cls || '').toLowerCase()] ? String(cls).toLowerCase() : 'creature';
  const key = `${cls}:${id}:${type}:${passive}:${size}`;
  if (cache.has(key)) return cache.get(key);
  const S = size, cv = canvas(S), c = cv.getContext('2d');
  const { r, theme, cc, ac, sc, p } = iconOf(id, cls, type);
  const h = hash(`${cls}:${id}`);
  const R = S * 0.16;
  // the gem, lit from the upper left
  c.save();
  c.beginPath(); c.roundRect(0, 0, S, S, R); c.clip();
  const base = mix(sc, cc, r.school ? 0.25 : 0.12);
  const g = c.createRadialGradient(S * 0.36, S * 0.3, S * 0.05, S * 0.5, S * 0.55, S * 0.78);
  g.addColorStop(0, rgb(mix(base, [255, 255, 255], 0.25))); g.addColorStop(0.45, rgb(mix(base, [0, 0, 0], 0.35))); g.addColorStop(1, rgb(mix(base, [0, 0, 0], 0.82)));
  c.fillStyle = g; c.fillRect(0, 0, S, S);
  // the class's sigil, faint and turned a little (each ability its own angle)
  const sig = sigilCanvas(theme.sigil, 128);
  if (sig) {
    c.save(); c.globalAlpha = 0.16; c.translate(S / 2, S / 2); c.rotate(((h % 360) * Math.PI) / 180);
    c.drawImage(sig, -S * 0.62, -S * 0.62, S * 1.24, S * 1.24); c.restore();
  }
  // a spell's inner rune ring; a skill's steel sheen
  if (type === 'spell') { c.strokeStyle = rgb(mix(sc, [255, 255, 255], 0.6), 0.28); ring(c, S / 2, S / 2, S * 0.36, S * 0.012); }
  else { const sh = c.createLinearGradient(0, 0, S, S); sh.addColorStop(0.35, 'rgba(255,255,255,0)'); sh.addColorStop(0.5, 'rgba(255,255,255,.10)'); sh.addColorStop(0.65, 'rgba(255,255,255,0)'); c.fillStyle = sh; c.fillRect(0, 0, S, S); }
  // the pictogram (drawn apart, so its cut-outs don't pierce the gem), tinted, glowing in the
  // school's light
  const tilt = (((h >> 8) % 21) - 10) * Math.PI / 180;
  const pc = canvas(S), px = pc.getContext('2d');
  px.translate(S / 2, S / 2); px.rotate(p.picto === 'sword' || p.picto === 'axe' || p.picto === 'daggers' ? 0 : tilt);
  px.scale(S / 100 * 0.72, S / 100 * 0.72);
  px.fillStyle = '#fff'; px.strokeStyle = '#fff';
  if (p.sigil && sig) px.drawImage(sig, -46, -46, 92, 92);
  else if (p.glyph) (DRAW[p.glyph] || DRAW.star)(px);
  else (PICTO[p.picto] || PICTO.burst)(px);
  px.setTransform(1, 0, 0, 1, 0, 0);
  px.globalCompositeOperation = 'source-atop';
  px.fillStyle = rgb(mix([255, 252, 240], sc, 0.18)); px.fillRect(0, 0, S, S);
  c.save();
  c.shadowColor = rgb(mix(sc, [255, 255, 255], 0.3), 0.95); c.shadowBlur = S * 0.12;
  c.drawImage(pc, 0, 0);
  c.shadowBlur = 0; c.globalAlpha = 0.35; c.drawImage(pc, 0, 0);
  c.restore();
  if (p.orbit) {
    c.save(); c.fillStyle = rgb(mix(ac, [255, 255, 255], 0.4)); c.shadowColor = rgb(ac); c.shadowBlur = S * 0.06;
    for (let i = 0; i < 3; i++) { const an = i * TAU / 3 - 0.6; drawGlyph(c, theme.glyph, S / 2 + Math.cos(an) * S * 0.36, S / 2 + Math.sin(an) * S * 0.36, S * 0.17); }
    c.restore();
  }
  // vignette and bevel
  const v = c.createRadialGradient(S / 2, S / 2, S * 0.3, S / 2, S / 2, S * 0.74);
  v.addColorStop(0, 'rgba(0,0,0,0)'); v.addColorStop(1, 'rgba(0,0,0,.55)');
  c.fillStyle = v; c.fillRect(0, 0, S, S);
  const bev = c.createLinearGradient(0, 0, 0, S);
  bev.addColorStop(0, 'rgba(255,255,255,.22)'); bev.addColorStop(0.12, 'rgba(255,255,255,0)'); bev.addColorStop(0.88, 'rgba(0,0,0,0)'); bev.addColorStop(1, 'rgba(0,0,0,.4)');
  c.fillStyle = bev; c.fillRect(0, 0, S, S);
  c.restore();
  motionBadge(c, r.motion, S);
  // the frame: the class's metal, a dark line inside it
  c.lineWidth = S * 0.045; c.strokeStyle = rgb(mix(cc, [255, 240, 200], 0.25));
  c.beginPath(); c.roundRect(S * 0.025, S * 0.025, S * 0.95, S * 0.95, R * 0.9); c.stroke();
  c.lineWidth = S * 0.012; c.strokeStyle = 'rgba(0,0,0,.65)';
  c.beginPath(); c.roundRect(S * 0.06, S * 0.06, S * 0.88, S * 0.88, R * 0.7); c.stroke();
  // studs at the corners in the class's mark
  c.fillStyle = rgb(mix(cc, [255, 255, 255], 0.5));
  for (const [x, y] of [[0.1, 0.1], [0.9, 0.1], [0.1, 0.9]]) drawGlyph(c, cls === 'creature' ? 'dot' : theme.glyph, S * x, S * y, S * 0.1);
  if (passive) { c.fillStyle = 'rgba(0,0,0,.35)'; c.fillRect(0, 0, S, S); }
  const url = cv.toDataURL('image/png');
  cache.set(key, url);
  return url;
}

// the menu's and the bar's own icons (helm, satchel, tome, scroll, map, gear, attack, flee...)
export function uiIcon(name, { size = 64, color = '#f3d999', glow = 'rgba(243,210,140,.6)' } = {}) {
  const key = `ui:${name}:${size}:${color}`;
  if (cache.has(key)) return cache.get(key);
  const S = size, shape = canvas(S), p = shape.getContext('2d');
  p.translate(S / 2, S / 2);
  p.scale(S / 100 * 0.74, S / 100 * 0.74);
  p.fillStyle = '#fff'; p.strokeStyle = '#fff';
  const fn = PICTO[name] || DRAW[name];
  if (fn) fn(p);
  p.setTransform(1, 0, 0, 1, 0, 0);
  p.globalCompositeOperation = 'source-atop'; p.fillStyle = color; p.fillRect(0, 0, S, S);
  const cv = canvas(S), c = cv.getContext('2d');
  c.shadowColor = glow; c.shadowBlur = S * 0.1;
  c.drawImage(shape, 0, 0);
  const url = cv.toDataURL('image/png');
  cache.set(key, url);
  return url;
}
