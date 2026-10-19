// A mount's tack, fitted to the body it is on (steed.js): the body's surface is felt with rays
// (its back, its flanks, its belly) and every piece is shaped to it: a blanket draped over the
// back, a saddle with its pommel and cantle, skirts, a girth round the barrel, stirrups hanging;
// for a war mount a caparison to the knees with a crest on each flank, or plate (a chanfron on
// the face, a crinet down the neck, a peytral over the chest); a bridle on the head and reins to
// the rider's hands. Built in the steed's frame on its bind pose, then hung on the bones (the
// spine, the chest, the head), so it moves as the body moves.
import * as THREE from 'three';

const UP = new THREE.Vector3(0, 1, 0), DOWN = new THREE.Vector3(0, -1, 0);

// feeling the body: where its surface is, from above, from the side, from below
export function feeler(meshes) {
  for (const m of meshes) if (m.isSkinnedMesh && m.skeleton) m.skeleton.update();
  const rc = new THREE.Raycaster();
  const o = new THREE.Vector3(), d = new THREE.Vector3();
  const hit = () => { const h = rc.intersectObjects(meshes, false)[0]; return h ? h.point : null; };
  return {
    top(x, z) { rc.set(o.set(x, 60, z), DOWN); const p = hit(); return p ? p.y : null; },
    bottom(x, z) { rc.set(o.set(x, -60, z), UP); const p = hit(); return p ? p.y : null; },
    side(y, z, sx) { rc.set(o.set(sx * 60, y, z), d.set(-sx, 0, 0)); const p = hit(); return p ? Math.abs(p.x) : null; },
    front(x, y) { rc.set(o.set(x, y, 60), d.set(0, 0, -1)); const p = hit(); return p ? p.z : null; },
  };
}

// the barrel's cross-section at z: its top, bottom, middle, half-width and half-height
export function section(feel, z, fallback) {
  const t = feel.top(0, z), b = feel.bottom(0, z);
  if (t == null || b == null) return fallback || null;
  const c = (t + b) / 2;
  const a = feel.side(c, z, 1) ?? feel.side(c, z, -1) ?? (t - b) * 0.45;
  return { top: t, bottom: b, mid: c, a: Math.max(0.05, a), b: Math.max(0.05, (t - b) / 2) };
}

// a cloth (or leather) laid over the back and, past the flanks, hanging down to `hemY` (flaring
// out a little as it falls, to clear the legs): rows along z (z0..z1), columns across from one
// side round over the back to the other. `reach`: how far round from the top it goes (0..1, 1 =
// to the widest point). `lift`: how far off the body, a number or a function of t (0..1 along z).
// UVs: u across (the hems at 0 and 1; the back from 0.25 to 0.75 when it hangs), v along.
const HANG = 4;
export function drape(feel, { z0, z1, reach = 0.6, hemY = null, lift = 0.03, rows = 10, cols = 18, flare = 0.035, wave = 0 }) {
  const pos = [], uv = [], idx = [];
  const lf = typeof lift === 'function' ? lift : () => lift;
  const hangs = hemY != null;
  let last = null;
  for (let r = 0; r <= rows; r++) {
    const t = r / rows, z = z0 + (z1 - z0) * t;
    const s = section(feel, z, last);
    last = s;
    if (!s) continue;
    const l = lf(t);
    for (let k = 0; k <= cols; k++) {
      const u = k / cols * 2 - 1;                 // -1 .. 1, left to right
      const th = u * reach * Math.PI / 2;         // angle round from the top
      pos.push(Math.sin(th) * (s.a + l), s.mid + Math.cos(th) * (s.b + l), z);
      uv.push(hangs ? 0.25 + k / cols * 0.5 : k / cols, t);
    }
    // the hanging part on each side, down to the hem (a wavy hem when `wave`)
    if (hangs) {
      for (const side of [-1, 1]) {
        const th = side * reach * Math.PI / 2;
        const x = Math.sin(th) * (s.a + l), y0 = s.mid + Math.cos(th) * (s.b + l);
        for (let j = 1; j <= HANG; j++) {
          const f = j / HANG, y = y0 + (hemY + Math.sin(z * 9) * wave - y0) * f;
          pos.push(x + side * flare * f * f * 2, y, z);
          uv.push(side < 0 ? 0.25 - 0.25 * f : 0.75 + 0.25 * f, t);
        }
      }
    }
  }
  const per = cols + 1 + (hangs ? HANG * 2 : 0);
  const nrows = pos.length / 3 / per;
  for (let r = 0; r < nrows - 1; r++) {
    const a = r * per, b = (r + 1) * per;
    for (let k = 0; k < cols; k++) idx.push(a + k, b + k, a + k + 1, a + k + 1, b + k, b + k + 1);
    if (hangs) {
      // the left hang hangs off column 0, the right off column `cols`
      const hang = (startCol, first, flip) => {
        let pa = a + startCol, pb = b + startCol;
        for (let j = 0; j < HANG; j++) {
          const na = a + first + j, nb = b + first + j;
          if (flip) idx.push(pa, na, pb, na, nb, pb); else idx.push(pa, pb, na, na, pb, nb);
          pa = na; pb = nb;
        }
      };
      hang(0, cols + 1, true);
      hang(cols, cols + 1 + HANG, false);
    }
  }
  const g = new THREE.BufferGeometry();
  g.setAttribute('position', new THREE.Float32BufferAttribute(pos, 3));
  g.setAttribute('uv', new THREE.Float32BufferAttribute(uv, 2));
  g.setIndex(idx);
  g.computeVertexNormals();
  return g;
}

const leather = c => new THREE.MeshStandardMaterial({ color: c, roughness: 0.55, metalness: 0.05 });
// no environment to reflect, so metal is kept half-metallic with a little glow of its own, or it
// renders black
const metal = (c, rough = 0.32) => new THREE.MeshStandardMaterial({ color: c, roughness: rough, metalness: 0.5,
  emissive: new THREE.Color(c).multiplyScalar(0.12) });

const hex = c => '#' + new THREE.Color(c).getHexString();
const shade = (c, k) => hex(new THREE.Color(c).multiplyScalar(k));
// a shield-shaped crest (a star on a field), drawn at (cx, cy) `size` across
function crest(g, cx, cy, size, field, charge) {
  const shield = k => {
    const w = size * k / 2, h = size * k * 0.6;
    g.beginPath(); g.moveTo(cx - w, cy - h); g.lineTo(cx + w, cy - h); g.lineTo(cx + w, cy);
    g.quadraticCurveTo(cx + w, cy + h * 0.9, cx, cy + h * 1.25); g.quadraticCurveTo(cx - w, cy + h * 0.9, cx - w, cy); g.closePath();
  };
  shield(1); g.fillStyle = hex(charge); g.fill();
  shield(0.84); g.fillStyle = hex(field); g.fill();
  g.fillStyle = hex(charge); g.beginPath();
  for (let i = 0; i < 10; i++) { const r = i % 2 ? size * 0.09 : size * 0.22, an = -Math.PI / 2 + i * Math.PI / 5; g.lineTo(cx + Math.cos(an) * r, cy + Math.sin(an) * r); }
  g.closePath(); g.fill();
}
// the cloth's picture (u across, the hems at the left and right edges; v along): the colour with a
// woven pattern (a lattice of diamonds for a caparison, fine stripes for a blanket), a trim band
// round the edge with a dark line inside it, and for a caparison a crest on each flank and a
// scalloped (dagged) hem
const clothTex = new Map();
function clothTexture(color, trim, kind) {
  const key = color + ':' + trim + ':' + kind;
  if (clothTex.has(key)) return clothTex.get(key);
  if (typeof document === 'undefined') return null;
  const W = 256, H = 256, c = document.createElement('canvas');
  c.width = W; c.height = H;
  const g = c.getContext('2d');
  const cap = kind === 'cap';
  g.fillStyle = hex(color); g.fillRect(0, 0, W, H);
  if (cap) {
    g.strokeStyle = shade(color, 0.72); g.lineWidth = 3;
    for (let i = -8; i <= 8; i++) {
      g.beginPath(); g.moveTo(i * 32, 0); g.lineTo(i * 32 + H, H); g.stroke();
      g.beginPath(); g.moveTo(i * 32 + H, 0); g.lineTo(i * 32, H); g.stroke();
    }
    g.fillStyle = hex(trim);
    for (let x = 16; x < W; x += 32) for (let y = 0; y < H; y += 32) g.fillRect(x - 2, y - 2, 4, 4);
  } else {
    g.fillStyle = shade(color, 0.8);
    for (let y = 0; y < H; y += 24) g.fillRect(0, y, W, 6);
  }
  // the trim: along both hems (left and right) and both ends (top and bottom)
  const band = cap ? 22 : 16;
  g.fillStyle = hex(trim);
  g.fillRect(0, 0, band, H); g.fillRect(W - band, 0, band, H);
  g.fillRect(0, 0, W, band * 0.7); g.fillRect(0, H - band * 0.7, W, band * 0.7);
  g.strokeStyle = shade(color, 0.45); g.lineWidth = 2;
  g.strokeRect(band + 3, band * 0.7 + 3, W - 2 * band - 6, H - 1.4 * band - 6);
  if (cap) {
    crest(g, W * 0.13, H * 0.48, 44, color, trim);
    crest(g, W * 0.87, H * 0.48, 44, color, trim);
    // dagging: scallops cut along both hems
    g.globalCompositeOperation = 'destination-out';
    for (let y = 0; y < H; y += 21) for (const x of [0, W]) { g.beginPath(); g.arc(x, y + 10, 7, 0, Math.PI * 2); g.fill(); }
    g.globalCompositeOperation = 'source-over';
  }
  const tex = new THREE.CanvasTexture(c);
  tex.colorSpace = THREE.SRGBColorSpace;
  tex.anisotropy = 4;
  clothTex.set(key, tex);
  return tex;
}
const clothMat = (color, trim, kind) => {
  const map = clothTexture(color, trim, kind);
  return new THREE.MeshStandardMaterial(map ? { map, roughness: 0.82, side: THREE.DoubleSide, alphaTest: 0.5 }
    : { color, roughness: 0.82, side: THREE.DoubleSide });
};

// a curved plate (part of a tube round `axis`), centred at `at`, for barding
function plate(radius, length, arc, mat) {
  const g = new THREE.CylinderGeometry(radius, radius * 0.92, length, 14, 1, true, -arc / 2, arc);
  return new THREE.Mesh(g, mat);
}
function alignY(mesh, from, to) {
  const dir = to.clone().sub(from), len = dir.length();
  mesh.position.copy(from).addScaledVector(dir, 0.5);
  mesh.quaternion.setFromUnitVectors(UP, dir.normalize());
  return len;
}
// a tube through points (a strap round the chest)
const strap = (pts, r, mat) => new THREE.Mesh(new THREE.TubeGeometry(new THREE.CatmullRomCurve3(pts), 24, r, 6, false), mat);
// a plume of feathers: curved blades fanning up and back
function plume(color, h) {
  const g = new THREE.Group();
  const m = new THREE.MeshStandardMaterial({ color, roughness: 0.7, side: THREE.DoubleSide, emissive: new THREE.Color(color).multiplyScalar(0.15) });
  for (let i = 0; i < 5; i++) {
    const f = new THREE.Mesh(new THREE.SphereGeometry(1, 8, 6, 0, Math.PI * 2, 0, Math.PI / 2), m);
    f.scale.set(h * 0.1, h, h * 0.22);
    f.rotation.set(-0.35 - i * 0.12, 0, (i - 2) * 0.18);
    g.add(f);
  }
  return g;
}

// the whole set for one body. `bones`: {spine, chest, neck, head, muzzle} (world positions taken at
// bind pose); `look`: the mount's look (steedlogic.js MOUNT_LOOK); `saddle`: {z, y} where the rider
// sits. Returns {parts: [[object, bone]], bits: [left, right] world anchors for the reins (objects
// hung on the head), stirrups}
export function buildTack(feel, bones, look, saddle, L) {
  const parts = [];
  const pos = n => (bones[n] ? bones[n].getWorldPosition(new THREE.Vector3()) : null);
  const S = section(feel, saddle.z) || { top: saddle.y, bottom: saddle.y * 0.4, mid: saddle.y * 0.7, a: L * 0.12, b: saddle.y * 0.3 };
  const kind = look.tack || 'leather';
  const war = kind === 'war' || kind === 'dark';
  const leatherC = look.leather ?? (kind === 'dark' ? 0x221a18 : 0x5a3418);
  const trimC = look.trim ?? (kind === 'dark' ? 0x8a1a10 : 0xc8a050);
  const clothC = look.cloth ?? 0x7a2a22;
  const spine = bones.spine || bones.chest;
  const L1 = leather(leatherC), Tm = metal(trimC, 0.35);
  // ---- the caparison (war) or the blanket ----
  if (war) {
    const hem = S.bottom - (S.mid - S.bottom) * 1.1;       // well down the legs
    const g = drape(feel, { z0: saddle.z - L * 0.36, z1: saddle.z + L * 0.3, reach: 1, hemY: Math.max(0.1, hem), lift: 0.04,
      wave: 0.02, rows: 16, cols: 20, flare: 0.07 });
    parts.push([new THREE.Mesh(g, clothMat(clothC, trimC, 'cap')), spine]);
  } else {
    const g = drape(feel, { z0: saddle.z - L * 0.15, z1: saddle.z + L * 0.12, reach: 0.7, lift: 0.025, rows: 8, cols: 14 });
    parts.push([new THREE.Mesh(g, clothMat(clothC, trimC, 'blanket')), spine]);
  }
  // ---- the saddle: a dished seat rising to the pommel and the cantle, skirts with studs ----
  const z0 = saddle.z - L * 0.1, z1 = saddle.z + L * 0.08;
  const dish = t => 0.075 + 0.11 * Math.pow(Math.abs(t - 0.45) / 0.55, 3);
  const seat = new THREE.Mesh(drape(feel, { z0, z1, reach: 0.46, lift: dish, rows: 10, cols: 12 }),
    new THREE.MeshStandardMaterial({ color: leatherC, roughness: 0.5, side: THREE.DoubleSide }));
  parts.push([seat, spine]);
  const wseat = S.a * 0.55;
  const topAt = z => (feel.top(0, z) ?? S.top);
  // the pommel: a low arch over the withers, with a gilt horn; the cantle: a higher roll behind
  const pommel = new THREE.Mesh(new THREE.TorusGeometry(wseat, 0.03 + L * 0.006, 8, 16, Math.PI), L1);
  pommel.scale.y = 0.55;
  pommel.position.set(0, topAt(z1) + 0.1, z1);
  pommel.rotation.x = 0.35;
  parts.push([pommel, spine]);
  const horn = new THREE.Mesh(new THREE.CylinderGeometry(0.03, 0.022, 0.09, 8), Tm);
  horn.position.set(0, pommel.position.y + wseat * 0.55 + 0.03, z1 + 0.01);
  parts.push([horn, spine]);
  const knob = new THREE.Mesh(new THREE.SphereGeometry(0.038, 10, 8), Tm);
  knob.position.copy(horn.position); knob.position.y += 0.05;
  parts.push([knob, spine]);
  const cantle = new THREE.Mesh(new THREE.TorusGeometry(wseat * 1.12, 0.05 + L * 0.006, 8, 18, Math.PI), L1);
  cantle.scale.y = 0.42;
  cantle.position.set(0, topAt(z0) + 0.1, z0);
  cantle.rotation.x = -0.45;
  parts.push([cantle, spine]);
  const cTrim = new THREE.Mesh(new THREE.TorusGeometry(wseat * 1.12, 0.014, 6, 18, Math.PI), Tm);
  cTrim.position.copy(cantle.position); cTrim.position.y += 0.01; cTrim.position.z -= 0.02;
  cTrim.scale.y = 0.42; cTrim.rotation.x = -0.45;
  parts.push([cTrim, spine]);
  // skirts down each side under the seat, a gilt stud at each corner
  const th = 0.6 * Math.PI / 2;
  for (const side of [-1, 1]) {
    const flap = new THREE.Mesh(new THREE.BoxGeometry(0.025, S.b * 0.75, L * 0.15), L1);
    flap.position.set(side * (Math.sin(th) * (S.a + 0.07) + 0.012), S.mid + Math.cos(th) * (S.b + 0.07) - S.b * 0.28, saddle.z);
    flap.rotation.z = side * 0.28;
    parts.push([flap, spine]);
    for (const dz of [-1, 1]) for (const dy of [-1, 1]) {
      const st = new THREE.Mesh(new THREE.SphereGeometry(0.018, 8, 6), Tm);
      st.position.copy(flap.position).add(new THREE.Vector3(side * 0.016 + side * dy * -0.03, dy * S.b * 0.3, dz * L * 0.06));
      parts.push([st, spine]);
    }
  }
  // ---- the girth round the barrel, and a buckle ----
  const girth = new THREE.Mesh(new THREE.TorusGeometry(1, 0.022, 6, 28), L1);
  girth.scale.set(S.a + 0.035, S.b + 0.035, 1);
  girth.position.set(0, S.mid, saddle.z + L * 0.03);
  parts.push([girth, spine]);
  // ---- stirrups: leathers down the flanks, irons at the bottom ----
  const stirrups = [];
  for (const side of [-1, 1]) {
    const top = new THREE.Vector3(side * (S.a * 0.85 + 0.03), S.top - 0.02, saddle.z + L * 0.01);
    const bot = new THREE.Vector3(side * (S.a + 0.12), S.mid - S.b * 0.65, saddle.z + L * 0.03);
    const st = new THREE.Mesh(new THREE.BoxGeometry(0.035, 1, 0.01), L1);
    st.scale.y = alignY(st, top, bot);
    parts.push([st, spine]);
    const iron = new THREE.Mesh(new THREE.TorusGeometry(0.07, 0.014, 6, 14), metal(0xb8b8c0, 0.3));
    iron.scale.set(1, 1.15, 1);
    iron.position.copy(bot).add(new THREE.Vector3(0, -0.065, 0));
    iron.rotation.y = Math.PI / 2;
    parts.push([iron, spine]);
    stirrups.push(iron);
  }
  // ---- packs: bags behind the saddle and a bedroll (a camel's, a donkey's) ----
  if (kind === 'pack' || look.bags) {
    for (const side of [-1, 1]) {
      const bag = new THREE.Mesh(new THREE.BoxGeometry(0.11, S.b * 0.8, L * 0.13), leather(0x6a4a2a));
      bag.position.set(side * (S.a + 0.09), S.mid + S.b * 0.2, saddle.z - L * 0.18);
      bag.rotation.z = side * 0.15;
      parts.push([bag, spine]);
      const flapB = new THREE.Mesh(new THREE.BoxGeometry(0.115, S.b * 0.3, L * 0.135), leather(0x4a3018));
      flapB.position.copy(bag.position); flapB.position.y += S.b * 0.27; flapB.rotation.z = bag.rotation.z;
      parts.push([flapB, spine]);
      const bk = new THREE.Mesh(new THREE.BoxGeometry(0.02, 0.04, 0.04), Tm);
      bk.position.copy(flapB.position).add(new THREE.Vector3(side * 0.06, -S.b * 0.12, 0));
      parts.push([bk, spine]);
    }
    const roll = new THREE.Mesh(new THREE.CylinderGeometry(0.065 + L * 0.01, 0.065 + L * 0.01, S.a * 1.7, 12), new THREE.MeshStandardMaterial({ color: 0x8a6a4a, roughness: 0.9 }));
    roll.rotation.z = Math.PI / 2;
    const rz = saddle.z - L * 0.16;
    roll.position.set(0, (feel.top(0, rz) ?? S.top) + 0.09, rz);
    parts.push([roll, spine]);
    for (const dx of [-0.6, 0.6]) {
      const tie = new THREE.Mesh(new THREE.TorusGeometry(0.075 + L * 0.01, 0.01, 5, 12), L1);
      tie.position.copy(roll.position); tie.position.x = dx * S.a; tie.rotation.y = Math.PI / 2;
      parts.push([tie, spine]);
    }
  }
  const head = pos('head'), muzzle = pos('muzzle'), neck = pos('neck'), chest = pos('chest');
  // ---- a breastcollar: a strap from the saddle round the front of the chest, a medallion ----
  if (chest && kind !== 'pack') {
    const cs = section(feel, chest.z) || S;
    const y = cs.mid + cs.b * 0.15;
    const front = feel.front(0, y) ?? (chest.z + cs.a);
    const pts = [
      new THREE.Vector3(-(S.a + 0.03), S.mid + S.b * 0.35, saddle.z + L * 0.06),
      new THREE.Vector3(-(cs.a + 0.03), y, chest.z),
      new THREE.Vector3(0, y - cs.b * 0.12, front + 0.035),
      new THREE.Vector3(cs.a + 0.03, y, chest.z),
      new THREE.Vector3(S.a + 0.03, S.mid + S.b * 0.35, saddle.z + L * 0.06),
    ];
    parts.push([strap(pts, 0.022, L1), bones.chest]);
    const med = new THREE.Mesh(new THREE.CylinderGeometry(0.06 + L * 0.01, 0.06 + L * 0.01, 0.02, 16), Tm);
    med.rotation.x = Math.PI / 2;
    med.position.set(0, y - cs.b * 0.12, front + 0.05);
    parts.push([med, bones.chest]);
    const gem = new THREE.Mesh(new THREE.SphereGeometry(0.028, 10, 8), new THREE.MeshStandardMaterial({ color: clothC, emissive: new THREE.Color(clothC).multiplyScalar(0.5), roughness: 0.2, metalness: 0.3 }));
    gem.position.copy(med.position); gem.position.z += 0.015;
    parts.push([gem, bones.chest]);
  }
  // ---- plate barding: chanfron, crinet, peytral ----
  if (kind === 'plate' || look.plate) {
    const steel = metal(look.steel ?? 0xd0d4dc, 0.25), gild = metal(trimC, 0.3);
    if (head && muzzle) {
      const hw = Math.max(0.06, (feel.side(head.y, head.z, 1) ?? 0.12));
      const ch = plate(hw * 1.1, 1, Math.PI * 1.1, steel);
      ch.scale.y = alignY(ch, head.clone().add(new THREE.Vector3(0, hw * 0.4, 0)), muzzle.clone().add(new THREE.Vector3(0, hw * 0.25, 0)));
      ch.rotateY(Math.PI);
      parts.push([ch, bones.head]);
      const spike = new THREE.Mesh(new THREE.ConeGeometry(0.03, 0.14, 6), gild);
      spike.position.copy(head.clone().lerp(muzzle, 0.3)).add(new THREE.Vector3(0, hw * 1.25, 0));
      spike.quaternion.setFromUnitVectors(UP, muzzle.clone().sub(head).normalize().multiplyScalar(0.8).add(UP).normalize());
      parts.push([spike, bones.head]);
    }
    if (neck && head && chest) {
      for (let i = 0; i < 3; i++) {
        const a = chest.clone().lerp(head, 0.22 + i * 0.2), b = chest.clone().lerp(head, 0.44 + i * 0.2);
        const w = Math.max(0.07, feel.side(a.y, a.z, 1) ?? 0.14);
        const p = plate(w * 1.15, 1, Math.PI * 0.85, i % 2 ? gild : steel);
        p.scale.y = alignY(p, a.add(new THREE.Vector3(0, w * 0.55, 0)), b.add(new THREE.Vector3(0, w * 0.45, 0)));
        p.rotateY(Math.PI);
        parts.push([p, bones.neck || bones.chest]);
      }
    }
    if (chest) {
      const cs = section(feel, chest.z) || S;
      const r = Math.max(cs.a, cs.b) * 1.15;
      const pey = plate(r, cs.b * 1.3, Math.PI * 1.1, steel);
      pey.position.set(0, cs.mid - cs.b * 0.1, chest.z + cs.a * 0.15);
      pey.rotation.x = Math.PI / 2;
      parts.push([pey, bones.chest]);
      for (const dy of [-0.62, 0.62]) {
        const band = new THREE.Mesh(new THREE.TorusGeometry(r * 1.01, 0.014, 6, 20, Math.PI * 1.1), gild);
        band.position.copy(pey.position); band.position.y += dy * cs.b * 1.3 / 2 * 0.95;
        band.rotation.set(Math.PI / 2, 0, Math.PI / 2 - Math.PI * 0.55);
        parts.push([band, bones.chest]);
      }
    }
  }
  // ---- the bridle: noseband, headstall, browband, the bit's rings (the reins' ends); a plume ----
  const bits = [];
  if (head && muzzle) {
    const hw = Math.max(0.05, feel.side(muzzle.y, muzzle.z, 1) ?? 0.08);
    const dir = muzzle.clone().sub(head).normalize();
    const nose = new THREE.Mesh(new THREE.TorusGeometry(1, 0.018, 6, 18), L1);
    nose.scale.set(hw * 1.1, hw * 1.12, 1);
    nose.position.copy(head.clone().lerp(muzzle, 0.75));
    nose.quaternion.setFromUnitVectors(new THREE.Vector3(0, 0, 1), dir);
    parts.push([nose, bones.head]);
    const hw2 = Math.max(0.06, feel.side(head.y, head.z, 1) ?? 0.1);
    const hs = new THREE.Mesh(new THREE.TorusGeometry(1, 0.018, 6, 18), L1);
    hs.scale.set(hw2 * 1.1, hw2 * 1.2, 1);
    hs.position.copy(head);
    hs.quaternion.setFromUnitVectors(new THREE.Vector3(0, 0, 1), dir);
    parts.push([hs, bones.head]);
    const brow = new THREE.Mesh(new THREE.TorusGeometry(1, 0.014, 6, 18, Math.PI), Tm);
    brow.scale.set(hw2 * 1.12, hw2 * 1.1, 1);
    brow.position.copy(head.clone().lerp(muzzle, 0.18));
    brow.quaternion.setFromUnitVectors(new THREE.Vector3(0, 0, 1), dir);
    parts.push([brow, bones.head]);
    for (const side of [-1, 1]) {
      const ring = new THREE.Mesh(new THREE.TorusGeometry(0.032, 0.009, 6, 10), Tm);
      ring.position.copy(nose.position).add(new THREE.Vector3(side * hw * 1.12, -hw * 0.3, 0));
      ring.rotation.y = Math.PI / 2;
      parts.push([ring, bones.head]);
      bits.push(ring);
    }
    // a plume on a war mount's crown, in the cloth's colour (white for the celestial)
    if (war || kind === 'plate') {
      const pl = plume(look.plume ?? (kind === 'plate' ? trimC : clothC), Math.max(0.16, hw2 * 1.8));
      pl.position.copy(head).add(new THREE.Vector3(0, hw2 * 1.15, 0)).addScaledVector(dir, -hw2 * 0.4);
      parts.push([pl, bones.head]);
    }
  }
  return { parts, bits, stirrups, seatY: S.top + 0.07 };
}

// a strap from a to b (world), sagging a little: two thin boxes (the reins)
export function makeRein(mat) {
  const g = new THREE.Group();
  const s1 = new THREE.Mesh(new THREE.BoxGeometry(0.02, 0.02, 1), mat), s2 = s1.clone();
  g.add(s1, s2);
  const mid = new THREE.Vector3(), d = new THREE.Vector3(), Z = new THREE.Vector3(0, 0, 1);
  // a and b in the group's parent's frame (the steed's)
  g.userData.set = (a, b, sag = 0.08) => {
    mid.copy(a).lerp(b, 0.5); mid.y -= sag;
    for (const [s, p, q] of [[s1, a, mid], [s2, mid, b]]) {
      s.position.copy(p).lerp(q, 0.5);
      d.copy(q).sub(p);
      s.scale.z = Math.max(0.01, d.length());
      s.quaternion.setFromUnitVectors(Z, d.normalize());
    }
  };
  return g;
}
