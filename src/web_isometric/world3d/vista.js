// Land in the distance, where the hero's room's own words put it (room_vistas.py: "South lies the
// harbor to Timeless Island", "Close beyond the bergs looms the black headland of Cape Voogk"): a
// low-poly silhouette far out in the haze, in the named direction. Land named with no direction
// lies off the sides the room has no way out of (the sea goes on where its ways out go), else
// straight ahead, the way the camera looks. Near land (a shore at hand) is the room's own bank
// instead (edges.js landSides); a side where the zone's own rooms stand is drawn by them (far.js).
//
// The owner, on the Sea of Storms: "ocean rooms that have no exit should just show more ocean on
// the horizon or a land mass if there's a description of land in the distance".
import * as THREE from 'three';
import { mergeGeometries } from 'three/addons/utils/BufferGeometryUtils.js';
import { ROOM_W, ROOM_H } from './terrain.js';
import { SIDES, vistaPlaces } from './edges.js';

// how far out a vista stands from the room's middle, by side, and how large: the camera looks
// down on the room from the south and sees some 20 m either side and 40 m ahead, so land seen in
// the distance is drawn where the view ends, low in the haze, smaller than life
export const VISTA_DIST = { north: 34, south: 28, east: 22, west: 22 };
const VISTA_SCALE = 0.5;

const MAT = new THREE.MeshLambertMaterial({ vertexColors: true, flatShading: true });
const C = {
  rock: 0x5e6066, dark: 0x3e4048, green: 0x4a6a44, pine: 0x34503a, sand: 0xb8a578, snow: 0xe6ecf2,
  roof: 0x7a4a3a, wall: 0xb0a690, hill: 0x5e7a4c,
};

// a geometry painted one colour (merged below into one mesh per vista)
function painted(geo, hex) {
  const g = geo.toNonIndexed();
  const col = new THREE.Color(hex), n = g.attributes.position.count, arr = new Float32Array(n * 3);
  for (let i = 0; i < n; i++) { arr[i * 3] = col.r; arr[i * 3 + 1] = col.g; arr[i * 3 + 2] = col.b; }
  g.setAttribute('color', new THREE.BufferAttribute(arr, 3));
  g.deleteAttribute('uv');
  return g;
}

// the shapes of one vista, in its own frame: x along the horizon, z away from the room, y up
export function vistaParts(kind, rnd) {
  const parts = [];
  const add = (geo, hex, x, y, z, sx = 1, sy = 1, sz = 1, yaw = 0) => {
    geo.scale(sx, sy, sz); geo.rotateY(yaw); geo.translate(x, y, z);
    parts.push(painted(geo, hex));
  };
  // (a hump is w wide along the horizon and d deep away from the room: kept shallow, so a long
  // shore never reaches back over the room itself)
  const hump = (x, z, w, h, hex, d = Math.min(w, 24) * 0.7) => add(new THREE.SphereGeometry(1, 9, 5, 0, Math.PI * 2, 0, Math.PI / 2), hex, x, -0.5, z, w, h, d);
  const cone = (x, z, w, h, hex, seg = 6, y0 = 0) => add(new THREE.ConeGeometry(1, 1, seg), hex, x, y0 + h / 2 - 0.5, z, w, h, w);
  if (kind === 'island') {
    hump(0, 0, 34, 9, C.green);
    hump(-18, 6, 18, 5, C.hill);
    for (let i = 0; i < 9; i++) cone(-22 + rnd() * 40, -6 + rnd() * 12, 2.2, 6 + rnd() * 3, C.pine, 5);
    hump(0, -2, 40, 1.2, C.sand, 10);
  } else if (kind === 'coast') {
    for (let i = 0; i < 9; i++) hump(-120 + i * 30 + rnd() * 8, 6 + rnd() * 10, 22 + rnd() * 10, 4 + rnd() * 5, i % 2 ? C.hill : C.green);
    hump(0, -6, 150, 1.4, C.sand, 8);
  } else if (kind === 'cliffs') {
    for (let i = 0; i < 10; i++) {
      const h = 12 + rnd() * 9;
      add(new THREE.BoxGeometry(1, 1, 1), i % 3 ? C.rock : C.dark, -90 + i * 20 + rnd() * 6, h / 2 - 1, rnd() * 6, 18 + rnd() * 8, h, 16, (rnd() - 0.5) * 0.4);
    }
    hump(0, 10, 110, 6, C.hill, 16);
  } else if (kind === 'mountains') {
    for (let i = 0; i < 6; i++) {
      const h = 34 + rnd() * 26, w = 26 + rnd() * 14, x = -110 + i * 44 + rnd() * 14, z = 18 + rnd() * 30;
      cone(x, z, w, h, C.rock, 7);
      cone(x, z, w * 0.37, h * 0.37, C.snow, 7, h * 0.635);     // the snow on its top
    }
  } else if (kind === 'hills') {
    for (let i = 0; i < 8; i++) hump(-100 + i * 28 + rnd() * 10, 10 + rnd() * 18, 24 + rnd() * 12, 9 + rnd() * 8, i % 2 ? C.hill : C.green);
  } else if (kind === 'forest') {
    for (let i = 0; i < 40; i++) cone(-100 + rnd() * 200, rnd() * 18, 3 + rnd() * 1.5, 8 + rnd() * 4, i % 3 ? C.pine : C.green, 5);
  } else if (kind === 'town') {
    hump(0, 6, 46, 3, C.hill, 14);
    for (let i = 0; i < 14; i++) {
      const x = -24 + rnd() * 48, z = -2 + rnd() * 14, h = 4 + rnd() * 4;
      add(new THREE.BoxGeometry(1, 1, 1), C.wall, x, h / 2, z, 5 + rnd() * 3, h, 4 + rnd() * 2);
      cone(x, z, 4, 3, C.roof, 4, h);
    }
    for (let i = 0; i < 2; i++) {
      const x = -14 + i * 26, h = 14 + rnd() * 6;
      add(new THREE.CylinderGeometry(1, 1, 1, 7), C.wall, x, h / 2, 8, 2.6, h, 2.6);
    }
  }
  return parts;
}

export class Vistas {
  constructor(scene) {
    this.scene = scene;
    this.group = new THREE.Group();
    this.group.name = 'vistas';
    scene.add(this.group);
    this.key = '';
  }

  // the hero's room: its far vistas, built afresh when the room changes
  set(room, cells, outdoors) {
    const places = outdoors && room ? vistaPlaces(room, cells) : [];
    const key = room ? `${room.vnum}:${places.map(p => p.kind + p.side).join(',')}` : '';
    if (key === this.key) return;
    this.key = key;
    this.clear();
    if (!places.length) return;
    const cx = room.ox + ROOM_W / 2, cz = room.oz + ROOM_H / 2;
    for (const p of places) {
      const rnd = MH.mulberry32(((room.vnum * 2654435761) ^ (p.side.length * 7919) ^ p.kind.length) >>> 0);
      const parts = vistaParts(p.kind, rnd);
      if (!parts.length) continue;
      const geo = mergeGeometries(parts, false);
      parts.forEach(g => g.dispose());
      geo.computeVertexNormals();
      const m = new THREE.Mesh(geo, MAT);
      const [dx, dz] = SIDES[p.side];
      // the frame's +z points away from the room
      m.rotation.y = Math.atan2(dx, dz);
      m.position.set(cx + dx * VISTA_DIST[p.side], -0.4, cz + dz * VISTA_DIST[p.side]);
      m.scale.setScalar(VISTA_SCALE);
      m.castShadow = m.receiveShadow = false;
      m.name = `vista_${p.kind}_${p.side}`;
      this.group.add(m);
    }
  }

  clear() {
    for (const m of [...this.group.children]) { m.geometry.dispose(); this.group.remove(m); }
  }

  dispose() {
    this.clear();
    this.scene.remove(this.group);
  }
}
