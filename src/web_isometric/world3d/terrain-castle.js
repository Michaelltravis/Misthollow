// Castles and the ways into other regions (room_looks.py 'castle'; zone exits).
//
// A castle's yard, walls and gates: a tall curtain wall with merlons along its outer edge and
// buttresses on its inner face, a tower at each closed corner, banners and torches on the walls
// the camera looks at, a gatehouse (two great pillars, a lintel with merlons, a raised
// portcullis) over every way out, and a yard of a well, crates, weapon racks and targets.
//
// A way into another region (an exit of kind 'zone') is a stone gateway in any room: two great
// pillars and a lintel carrying the region's name, banners, and a fire either side.
import * as THREE from 'three';
import { trs } from './assets.js';
import { tinted } from './terrain-looks.js';

const BLOCK = 1;
const WALL_H = 3.8;                   // a castle's curtain wall (a dungeon's is 2.6)
const NEAR_H = 1.7;                   // the side nearest the camera: a parapet, so the yard shows
const TOWER_COLORS = ['blue', 'red', 'green', 'yellow'];
const BANNERS = ['banner_patternA_red', 'banner_patternB_blue', 'banner_shield_white'];
// which way is into the room from each side, and the side's yaw (a model's front faces +z)
const INWARD = { north: [0, 1], south: [0, -1], west: [1, 0], east: [-1, 0] };
const FACE = { north: 0, south: Math.PI, west: Math.PI / 2, east: -Math.PI / 2 };

const IRON = new THREE.MeshStandardMaterial({ color: 0x2c2a2e, roughness: 0.55, metalness: 0.7 });
const BAR = { name: 'castle_bar', parts: [{ geometry: new THREE.BoxGeometry(1, 1, 1), material: IRON }],
  box: new THREE.Box3(new THREE.Vector3(-0.5, -0.5, -0.5), new THREE.Vector3(0.5, 0.5, 0.5)) };
const SPIKE = { name: 'castle_spike', parts: [{ geometry: new THREE.ConeGeometry(0.5, 1, 4).rotateX(Math.PI), material: IRON }],
  box: new THREE.Box3(new THREE.Vector3(-0.5, -0.5, -0.5), new THREE.Vector3(0.5, 0.5, 0.5)) };

// the castle's stone, from its words: black, white or red stone, else the kit's own grey
function stoneOf(text) {
  const t = String(text || '').toLowerCase();
  if (/\b(black|obsidian|dark stone|basalt|ebon|onyx|shadow)\b/.test(t)) return [0x56525a, 'castle_black'];
  if (/\b(white|marble|pale|alabaster|limestone)\b/.test(t)) return [0xf2eee4, 'castle_white'];
  if (/\b(red stone|sandstone|ochre|brick)\b/.test(t)) return [0xd8a888, 'castle_red'];
  if (/\b(bone|bones|skull)\b/.test(t)) return [0xe8dcc0, 'castle_bone'];
  return null;
}

// a model stood on its base at (x, z): its box's bottom at y, centred on its footprint
function stand(b, model, x, y, z, yaw, sx, sy = sx, sz = sx, opts) {
  if (!model) return;
  const bx = model.box;
  const cx = (bx.min.x + bx.max.x) / 2 * sx, cz = (bx.min.z + bx.max.z) / 2 * sz;
  const c = Math.cos(yaw), s = Math.sin(yaw);
  b.add(model, trs(x - (cx * c + cz * s), y - bx.min.y * sy, z - (-cx * s + cz * c), yaw, sx, sy, sz), opts);
}

const sizeOf = model => { const v = new THREE.Vector3(); if (model) model.box.getSize(v); return v; };

// the room-relative line of a side and a point `along` it, in world space
function onSide(side, along, ox, oz, W, H, inset = 0.5) {
  if (side === 'north') return [ox + along, oz + inset];
  if (side === 'south') return [ox + along, oz + H - inset];
  if (side === 'west') return [ox + inset, oz + along];
  return [ox + W - inset, oz + along];
}
const sideOfRun = (run, W, H) => run.horiz ? (run.line === 0 ? 'north' : 'south') : (run.line === 0 ? 'west' : 'east');

// ---- a gateway over a gap: two pillars, a lintel; merlons, a portcullis, banners, fires ----
// gap: { a, b } the open tiles along the side (inclusive). opts: height, merlons, portcullis,
// banners, fires, plaque (a canvas texture of the name), stone (a tinted pair), column (plain
// pillars, not a knight's shields: the drow's)
export function gateway(c, side, gap, opts = {}) {
  const { layout, ox, oz, kits, b, occ, torches } = c;
  const D = kits.dungeon;
  const { W, H } = layout;
  // the side nearest the camera stays low and open (no lintel walk, no portcullis), its name
  // turned to face the camera
  const near = side === 'south';
  const height = near ? Math.min(opts.height || 4.6, 3.3) : opts.height || 4.6;
  if (near) opts = { ...opts, merlons: false, portcullis: false };
  const stone = m => (opts.stone && m ? tinted(m, opts.stone[0], opts.stone[1]) : m);
  const [ix, iz] = INWARD[side];
  const yaw = FACE[side];
  const horiz = side === 'north' || side === 'south';
  const left = gap.a - 0.5, right = gap.b + 1.5;       // the pillars' centres along the side
  const mid = (gap.a + gap.b + 1) / 2, span = right - left;
  const pillar = stone(D.get(opts.column ? 'column' : 'pillar_decorated'));
  const ps = sizeOf(pillar);
  for (const along of [left, right]) {
    const [x, z] = onSide(side, along, ox, oz, W, H);
    stand(b, occ(pillar), x, 0, z, yaw, 1.5 / (ps.x || 2.2), height / (ps.y || 4), 1.4 / (ps.z || 1.7));
  }
  // the lintel across the tops, and its merlons
  const wall = stone(D.get('wall'));
  const LT = 0.9;
  const [lx, lz] = onSide(side, mid, ox, oz, W, H);
  stand(b, occ(wall), lx, height - LT, lz, horiz ? 0 : Math.PI / 2, (span + 1.4) / 4, LT / 4, 1.5);
  if (opts.merlons !== false) {
    for (let t = left - 0.6; t <= right + 0.61; t += 1.1) {
      const [mx, mz] = onSide(side, t, ox, oz, W, H, 0.5 - 0.5);
      stand(b, occ(wall), mx, height, mz, horiz ? 0 : Math.PI / 2, 0.55 / 4, 0.6 / 4, 0.45);
    }
  }
  // a raised portcullis: its spiked bottom edge shows under the lintel
  if (opts.portcullis) {
    const n = Math.max(3, Math.round((span - 1.4) / 0.42));
    const y0 = height - LT - 0.55;
    for (let i = 0; i <= n; i++) {
      const t = left + 0.7 + (span - 1.4) * i / n;
      const [px, pz] = onSide(side, t, ox, oz, W, H, 0.5);
      b.add(BAR, trs(px, y0 + 0.3, pz, 0, 0.07, 0.6, 0.07), { shadow: false });
      b.add(SPIKE, trs(px, y0 - 0.1, pz, 0, 0.12, 0.22, 0.12), { shadow: false });
    }
    const [cx, cz] = onSide(side, mid, ox, oz, W, H, 0.5);
    b.add(BAR, trs(cx, y0 + 0.15, cz, horiz ? 0 : Math.PI / 2, span - 1.4, 0.07, 0.07), { shadow: false });
  }
  // banners down the pillars' inner faces
  if (opts.banners) {
    for (const [i, along] of [[0, left], [1, right]]) {
      const [x, z] = onSide(side, along, ox, oz, W, H, 0.5 + 0.75);
      const ban = D.get(opts.banners[i % opts.banners.length]);
      stand(b, ban, x, height - LT - 2.35, z, yaw, 0.62, 0.7, 0.62, { shadow: false });
    }
  }
  // a fire either side, out in front
  if (opts.fires) {
    for (const along of [left - 0.6, right + 0.6]) {
      const [x, z] = onSide(side, along, ox, oz, W, H, 0.5 + 2.2);
      stand(b, D.get('torch_lit'), x, 0, z, 0, 1.45, 1.45, 1.45, { shadow: false });
      torches.push(new THREE.Vector3(x, 1.5, z));
    }
  }
  // the name carved over the way through, on the lintel's inner face
  if (opts.plaque) {
    const [px, pz] = onSide(side, mid, ox, oz, W, H, near ? 0.5 - 0.77 : 0.5 + 0.77);
    const w = Math.min(span - 0.6, 6), h = w / opts.plaque.aspect;
    const geo = new THREE.PlaneGeometry(w, Math.min(h, LT * 0.86));
    const mat = new THREE.MeshStandardMaterial({ map: opts.plaque.tex, roughness: 0.8, emissive: 0xffffff, emissiveMap: opts.plaque.tex, emissiveIntensity: 0.35 });
    c.owned.push(geo, mat);
    const m = new THREE.Mesh(geo, mat);
    m.position.set(px, height - LT / 2, pz);
    m.rotation.y = near ? 0 : yaw;
    c.group.add(m);
  }
}

// the region's name cut into a stone plaque (a canvas texture)
function plaqueTexture(text, owned) {
  if (typeof document === 'undefined') return null;
  const cv = document.createElement('canvas');
  const ctx = cv.getContext('2d');
  const H = 96, font = `700 52px Cinzel, Georgia, serif`;
  ctx.font = font;
  const W = Math.max(320, Math.ceil(ctx.measureText(text).width) + 96);
  cv.width = W; cv.height = H;
  const g = ctx.createLinearGradient(0, 0, 0, H);
  g.addColorStop(0, '#5a5248'); g.addColorStop(1, '#3a342c');
  ctx.fillStyle = g; ctx.fillRect(0, 0, W, H);
  ctx.strokeStyle = '#c9a45a'; ctx.lineWidth = 4; ctx.strokeRect(6, 6, W - 12, H - 12);
  ctx.font = font; ctx.textAlign = 'center'; ctx.textBaseline = 'middle';
  ctx.fillStyle = '#1a1612'; ctx.fillText(text, W / 2 + 2, H / 2 + 4);
  ctx.fillStyle = '#f2d48a'; ctx.fillText(text, W / 2, H / 2 + 2);
  const tex = new THREE.CanvasTexture(cv);
  tex.colorSpace = THREE.SRGBColorSpace;
  owned.push(tex);
  return { tex, aspect: W / H };
}

// a room's gaps as { side: {a, b} } along their side (only the four cardinal ways)
function gapsOf(layout) {
  const out = {};
  for (const [side, g] of Object.entries(layout.gaps || {})) {
    if (!INWARD[side] || !g) continue;
    out[side] = side === 'north' || side === 'south' ? { a: g.x0, b: g.x1 } : { a: g.y0, b: g.y1 };
  }
  return out;
}

// ---- the castle's walls (instead of the plain dungeon ring) ----
export function castleWalls(c) {
  const { layout, ox, oz, kits, room, b, rng, runs, occ, torches } = c;
  const { W, H, grid } = layout;
  const D = kits.dungeon, T = kits.town;
  const at = (x, y) => (x < 0 || y < 0 || x >= W || y >= H) ? BLOCK : grid[y * W + x];
  const words = `${layout.name || ''} ${layout.description || ''}`;
  const stone = stoneOf(words);
  const st = m => (stone && m ? tinted(m, stone[0], stone[1]) : m);
  const wall = occ(st(D.get('wall')));
  const pillar = st(D.get('pillar'));
  const seed = MH.hashStr(String((room && room.zoneRef && room.zoneRef.id) || layout.zoneKey || layout.vnum));
  const color = TOWER_COLORS[seed % TOWER_COLORS.length];
  const banners = [BANNERS[seed % 3], BANNERS[(seed + 1) % 3]];
  for (const run of runs) {
    const side = sideOfRun(run, W, H);
    const [ix, iz] = INWARD[side];
    const L = run.b - run.a + 1;
    const hgt = side === 'south' ? NEAR_H : WALL_H;
    const n = Math.max(1, Math.round(L / 4)), w = L / n;
    for (let i = 0; i < n; i++) {
      const along = run.a + (i + 0.5) * w;
      const [x, z] = onSide(side, along, ox, oz, W, H);
      stand(b, wall, x, 0, z, run.horiz ? 0 : Math.PI / 2, w / 4, hgt / 4, 1.25);
    }
    // merlons along the outer edge of the wall walk
    for (let t = run.a + 0.3; t <= run.b + 0.71; t += 1.1) {
      const [x, z] = onSide(side, t, ox, oz, W, H, 0.5 - 0.42);
      stand(b, wall, x, hgt, z, run.horiz ? 0 : Math.PI / 2, 0.55 / 4, 0.65 / 4, 0.4);
    }
    // buttresses on the inner face, every ~6 m
    if (pillar && side !== 'south') {
      const ps = sizeOf(pillar);
      for (let t = run.a + 2.5; t <= run.b - 1.5; t += 6) {
        const [x, z] = onSide(side, t + 0.5, ox, oz, W, H, 0.5 + 0.62);
        stand(b, occ(pillar), x, 0, z, 0, 0.75 / (ps.x || 1.5), (WALL_H + 0.25) / (ps.y || 4), 0.6 / (ps.z || 1.5));
      }
    }
    // the walls the camera faces get banners and torches between the buttresses
    if (side !== 'south' && L >= 4) {
      let k = 0;
      for (let t = run.a + 1.5; t <= run.b - 1; t += 3, k++) {
        if (at(Math.round(side === 'north' ? t : side === 'west' ? 1 : W - 2), Math.round(side === 'north' ? 1 : t)) === BLOCK) continue;
        const [x, z] = onSide(side, t + 0.5, ox, oz, W, H, 0.5 + 0.66);
        if (k % 2 === 0) stand(b, D.get(banners[(k / 2) % 2]), x, 0.75, z, FACE[side], 0.62, 0.72, 0.62, { shadow: false });
        else {
          stand(b, D.get('torch_mounted'), x, 1.7, z, FACE[side], 1, 1, 1, { shadow: false });
          torches.push(new THREE.Vector3(x + ix * 0.45, 2.3, z + iz * 0.45));
        }
      }
    }
  }
  // a tower at each corner where two walls meet
  const tower = T && T.get(`building_tower_A_${color}`);
  for (const [cx, cy, side] of [[0, 0, 'north'], [W - 1, 0, 'north'], [0, H - 1, 'south'], [W - 1, H - 1, 'south']]) {
    const dx = cx === 0 ? 1 : -1, dy = cy === 0 ? 1 : -1;
    if (at(cx, cy) !== BLOCK || at(cx + dx, cy) !== BLOCK || at(cx, cy + dy) !== BLOCK) continue;
    const x = ox + cx + 0.5 - dx * 0.3, z = oz + cy + 0.5 - dy * 0.3;
    if (tower) {
      const s = 3.3 / (sizeOf(tower).x || 1);
      stand(b, occ(st(tower)), x, 0, z, FACE[side], s, side === 'south' ? s * 0.55 : s, s);
    } else if (pillar) {
      stand(b, occ(pillar), x, 0, z, 0, 2, (WALL_H + 1.6) / 4, 2);
    }
  }
  // a gatehouse over every way out
  for (const [side, gap] of Object.entries(gapsOf(layout))) {
    if (gap.b - gap.a > 10) continue;                      // a whole open side: no gate
    gateway(c, side, gap, { height: side === 'south' ? NEAR_H + 1.9 : WALL_H + 0.8, portcullis: true, stone, banners: null });
  }
}

// ---- the castle's yard: what stands on roomgen's obstacles and props ----
export function castleYard(c) {
  const { layout, ox, oz, kits, b, rng, occ, torches } = c;
  const D = kits.dungeon, T = kits.town;
  const indoors = /\b(hall|chamber|room|corridor|stair|passage|keep|inside)\b/i.test(layout.name || '');
  for (const o of layout.obstacles || []) {
    const cx = ox + o.x + (o.big ? 1 : 0.5), cz = oz + o.y + (o.big ? 1 : 0.5);
    const yaw = Math.floor(rng() * 4) * Math.PI / 2;
    if (o.big) {
      const r = rng();
      if (!indoors && r < 0.25 && T) stand(b, occ(T.get('building_well_blue')), cx, 0, cz, yaw, 2.6);
      else if (r < 0.5) stand(b, occ(D.get('crates_stacked')), cx, 0, cz, yaw, 0.9);
      else if (r < 0.7) stand(b, occ(D.get('barrel_large')), cx, 0, cz, yaw, 0.9);
      else stand(b, occ(D.get('pillar_decorated')), cx, 0, cz, yaw, 0.7, 0.75, 0.7);
    } else {
      const r = rng();
      if (T && r < 0.35) stand(b, T.get('weaponrack'), cx, 0, cz, yaw, 4.5);
      else if (T && r < 0.55 && !indoors) stand(b, T.get('target'), cx, 0, cz, yaw, 4.5);
      else if (r < 0.8) stand(b, D.get('barrel_small'), cx, 0, cz, rng() * 6.28, 0.9);
      else stand(b, D.get('box_large'), cx, 0, cz, yaw, 0.62);
    }
  }
  for (const p of layout.props || []) {
    const x = ox + p.x + 0.5, z = oz + p.y + 0.5;
    const r = rng();
    if (r < 0.45) {
      stand(b, D.get('torch_lit'), x, 0, z, 0, 1.6, 1.6, 1.6, { shadow: false });
      torches.push(new THREE.Vector3(x, 1.65, z));
    } else if (r < 0.7) stand(b, D.get('sword_shield'), x, 0, z, rng() * 6.28, 0.5, 0.5, 0.5, { shadow: false });
    else if (r < 0.85 && T) stand(b, T.get('sack'), x, 0, z, rng() * 6.28, 4.5);
    else stand(b, D.get('barrel_small'), x, 0, z, rng() * 6.28, 0.8);
  }
}

// ---- a free-standing arch over stairs into another region, facing the camera ----
function standingGate(c, cx, cz, opts = {}) {
  const { kits, b, occ, torches, group, owned } = c;
  const D = kits.dungeon;
  const height = opts.height || 3.8, LT = 0.8, half = 2.7;
  const stone = m => (opts.stone && m ? tinted(m, opts.stone[0], opts.stone[1]) : m);
  const pillar = stone(D.get(opts.column ? 'column' : 'pillar_decorated'));
  const ps = sizeOf(pillar);
  for (const x of [cx - half, cx + half]) stand(b, occ(pillar), x, 0, cz, 0, 1.2 / (ps.x || 2.2), height / (ps.y || 4), 1.1 / (ps.z || 1.7));
  stand(b, occ(stone(D.get('wall'))), cx, height - LT, cz, 0, (2 * half + 1.3) / 4, LT / 4, 1.1);
  if (opts.banners) {
    for (const [i, x] of [[0, cx - half], [1, cx + half]]) {
      stand(b, D.get(opts.banners[i % opts.banners.length]), x, height - LT - 2.2, cz + 0.62, 0, 0.55, 0.65, 0.55, { shadow: false });
    }
  }
  if (opts.fires) {
    for (const x of [cx - half - 0.9, cx + half + 0.9]) {
      stand(b, D.get('torch_lit'), x, 0, cz + 1.0, 0, 1.3, 1.3, 1.3, { shadow: false });
      torches.push(new THREE.Vector3(x, 1.35, cz + 1.0));
    }
  }
  if (opts.plaque) {
    const w = Math.min(2 * half - 0.4, 4.6), h = Math.min(w / opts.plaque.aspect, LT * 0.86);
    const geo = new THREE.PlaneGeometry(w, h);
    const mat = new THREE.MeshStandardMaterial({ map: opts.plaque.tex, roughness: 0.8, emissive: 0xffffff, emissiveMap: opts.plaque.tex, emissiveIntensity: 0.35 });
    owned.push(geo, mat);
    const m = new THREE.Mesh(geo, mat);
    m.position.set(cx, height - LT / 2, cz + 0.57);
    group.add(m);
  }
}

// ---- the ways into other regions: a gateway with the region's name over it ----
export function zoneGates(c, theme) {
  const { layout, room } = c;
  if (!room || !room.data || !room.data.exits) return;
  const gaps = gapsOf(layout);
  const underground = theme === 'cave' || theme === 'mine';
  const indoor = theme === 'inside' || theme === 'dungeon' || theme === 'crypt' || theme === 'sewer';
  // the drow's: black stone, plain columns, no banners or torches (their light is faerie fire)
  const drow = theme === 'drow';
  const look = drow ? { stone: [0x2a2434, 'drowgate'], column: true, banners: null, fires: false } : {};
  for (const [side, e] of Object.entries(room.data.exits)) {
    if (!e || e.kind !== 'zone') continue;
    // stairs up or down into another region: an arch over them, its name toward the camera
    const st = side === 'up' ? layout.stairsUp : side === 'down' ? layout.stairsDown : null;
    if (st) {
      const name = e.zoneName || e.toName || '';
      const seed = MH.hashStr(name);
      standingGate(c, c.ox + st.x + 0.5, c.oz + st.y - 0.6, {
        height: indoor || underground ? 3.2 : 3.8,
        stone: underground ? [0x8a7a68, 'gate_rock'] : null,
        banners: indoor || underground ? null : [BANNERS[seed % 3], BANNERS[(seed + 1) % 3]],
        fires: true,
        plaque: name ? plaqueTexture(name, c.owned) : null,
        ...look,
      });
      continue;
    }
    if (!gaps[side]) continue;
    if (theme === 'castle') continue;                       // a castle's gatehouse is already there
    let gap = gaps[side];
    // a whole open side: the gate stands over its middle
    if (gap.b - gap.a > 8) {
      const mid = Math.floor((gap.a + gap.b) / 2), half = side === 'north' || side === 'south' ? 3 : 2;
      gap = { a: mid - half, b: mid + half };
    }
    const name = e.zoneName || e.toName || '';
    const seed = MH.hashStr(name);
    gateway(c, side, gap, {
      height: indoor ? 3.4 : underground ? 3.8 : 5.2,
      merlons: !indoor && !underground && !drow,
      stone: underground ? [0x8a7a68, 'gate_rock'] : null,
      banners: indoor || underground ? null : [BANNERS[seed % 3], BANNERS[(seed + 1) % 3]],
      fires: true,
      plaque: name ? plaqueTexture(name, c.owned) : null,
      ...look,
    });
  }
}
