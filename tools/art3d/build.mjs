// Build the 3D client's art from the downloaded CC0 packs (see fetch.sh and
// docs/art/SOURCES.md). Usage:
//   cd tools/art3d && npm ci && node build.mjs <cache dir from fetch.sh>
// Output goes to src/web_isometric/art3d/. The kinds of job:
//   char  - one rigged character, animations stripped (they live in the shared rig file)
//   equip - the equipment kit: every adventurer body part and piece on ONE rig with ONE palette
//           texture, so the client can dress a hero in any mix and draw them as one mesh
//   anims - the shared animation set for every KayKit humanoid (same 41-joint rig)
//   kit   - many static models merged into ONE file: shared textures are stored once and
//           the client loads a whole kit with one request; each model is a top-level
//           node named after its key
//   mob   - an animated creature from an FBX (Quaternius packs): converted with FBX2glTF,
//           its texture attached, turned to face +Z, scaled to 1 m tall with its feet at
//           the origin, animation names cleaned ("MonsterArmature|Walk" -> "Walk")
//   blend - a model made in Blender by tools/art3d/blender (run.sh models/<name>.py): its .glb
//           and sidecar .json from blender/out, optimised into art3d/bodies/ with an index.json.
//           Only these:   node build.mjs blend [name]
import fs from 'node:fs';
import os from 'node:os';
import { spawnSync } from 'node:child_process';
import path from 'node:path';
import { NodeIO, getBounds, TextureInfo } from '@gltf-transform/core';
import { ALL_EXTENSIONS } from '@gltf-transform/extensions';
import { dedup, prune, weld, resample, meshopt, textureCompress, mergeDocuments, unpartition } from '@gltf-transform/functions';
import { MeshoptEncoder, MeshoptDecoder } from 'meshoptimizer';
import sharp from 'sharp';

const BLEND_ONLY = process.argv[2] === 'blend';
const CACHE = path.resolve(BLEND_ONLY ? '.cache' : (process.argv[2] || '.cache'));
const BLEND = path.resolve(path.dirname(new URL(import.meta.url).pathname), 'blender/out');
const OUT = path.resolve(path.dirname(new URL(import.meta.url).pathname), '../../src/web_isometric/art3d');

const ADV = 'kaykit-adventurers/addons/kaykit_character_pack_adventures/Characters/gltf';
const SKEL = 'kaykit-skeletons/addons/kaykit_character_pack_skeletons/Characters/gltf';
const DUN = 'kaykit-dungeon/addons/kaykit_dungeon_remastered/Assets/gltf';
const NAT = 'quaternius-nature/glTF';

const DUNGEON = ['wall', 'wall_corner', 'wall_doorway', 'wall_half', 'wall_broken', 'wall_arched',
  'wall_pillar', 'wall_endcap', 'floor_tile_large', 'floor_tile_small', 'floor_tile_small_broken_A',
  'floor_tile_small_weeds_A', 'floor_dirt_large', 'floor_dirt_large_rocky', 'pillar', 'pillar_decorated',
  'column', 'torch_mounted', 'torch_lit', 'barrel_large', 'barrel_small', 'box_large', 'box_stacked',
  'crates_stacked', 'chest', 'chest_gold', 'banner_patternA_red', 'banner_thin_red', 'rubble_large',
  'rubble_half', 'candle_lit', 'candle_triple', 'table_long_decorated_A', 'keg', 'stairs',
  'coin_stack_large', 'sword_shield', 'floor_wood_small', 'floor_wood_small_dark', 'floor_wood_large',
  'shelf_large', 'shelves', 'banner_patternB_blue', 'banner_shield_white'];
const NATURE = ['CommonTree_1', 'CommonTree_2', 'CommonTree_3', 'Pine_1', 'Pine_2', 'TwistedTree_1',
  'DeadTree_1', 'DeadTree_2', 'Bush_Common', 'Bush_Common_Flowers', 'Fern_1', 'Grass_Common_Short',
  'Grass_Common_Tall', 'Grass_Wispy_Tall', 'Flower_3_Group', 'Flower_4_Group', 'Mushroom_Common',
  'Rock_Medium_1', 'Rock_Medium_2', 'Rock_Medium_3', 'Pebble_Round_1', 'Pebble_Round_3',
  'RockPath_Round_Wide', 'Plant_1', 'Plant_7', 'Clover_1'];

const CUTE = 'quaternius-cute-monsters/Cute Animated Monsters - Aug 2020';
const ANV2 = 'quaternius-animals-2/Animal Pack Vol.2 by @Quaternius';
const ANV1 = 'quaternius-animals/Animals Pack by Quaternius';
const FARM = 'quaternius-farm/Farm Animals by @Quaternius';
const QMON = 'quaternius-monsters/Animated Monster Pack by @Quaternius';
const QCHR = 'quaternius-characters/Ultimate Animated Character Pack - Nov 2019';
// yaw (radians) turns each model to face +Z, the way the client points every actor
const MOBS = [
  ...['Alien', 'Alien_Tall', 'Bat', 'Bee', 'Cactus', 'Chicken', 'Crab', 'Cthulhu', 'Cyclops', 'Deer', 'Demon',
    'Ghost', 'GreenDemon', 'Mushroom', 'Panda', 'Penguin', 'Pig', 'Skull', 'Tree', 'YellowDragon', 'Yeti']
    .map(n => ({ name: n.toLowerCase(), fbx: `${CUTE}/FBX/${n}.fbx`, tex: `${CUTE}/Textures/${n}_Texture.png`, yaw: 0 })),
  ...['Cat', 'Dog', 'Eagle', 'Piranha', 'Wolf'].map(n => ({ name: n.toLowerCase(), fbx: `${ANV2}/FBX/${n}.fbx`, yaw: 0 })),
  ...[['Red Fox', 'fox'], ['Fish', 'fish'], ['bird', 'bird'], ['Chick', 'chick'], ['Whale', 'whale']]
    .map(([n, k]) => ({ name: k, fbx: `${ANV1}/FBX/${n}.fbx`, yaw: 0 })),
  ...['Cow', 'Horse', 'Llama', 'Pig', 'Pug', 'Sheep', 'Zebra']
    .map(n => ({ name: n === 'Pig' ? 'farm_pig' : n.toLowerCase(), fbx: `${FARM}/FBX/${n}.fbx`, yaw: 0 })),
  // their clips are named for the model ("Dragon_Flying"): renamed to the names assets.js maps
  // (these two packs' FBX colours come through linearised twice: gamma undoes one)
  ...['Dragon', 'Bat', 'Slime'].map(n => ({ name: `q_${n.toLowerCase()}`, fbx: `${QMON}/FBX/${n}.fbx`, yaw: 0, gamma: true,
    rename: { [`${n}_Flying`]: 'Flying', [`${n}_Idle`]: 'Idle', [`${n}_Walk`]: 'Walk', [`${n}_Attack`]: 'Bite_Front',
      [`${n}_Attack2`]: 'Bite_InPlace', [`${n}_Hit`]: 'HitRecieve', [`${n}_Death`]: 'Death' } })),
  ...[['Goblin_Male', 'goblin_m'], ['Goblin_Female', 'goblin_f'], ['Zombie_Male', 'zombie_m'], ['Zombie_Female', 'zombie_f']]
    .map(([n, k]) => ({ name: k, fbx: `${QCHR}/FBX/${n}.fbx`, yaw: 0, gamma: true,
      rename: { Punch: 'Bite_Front', RecieveHit: 'HitRecieve', Victory: 'Jump', Idle: 'Idle', Walk: 'Walk' } })),   // 'Defeat' kneels: no death clip, so corpse.js tips them over
];
const MOB_YAW = JSON.parse(fs.existsSync(new URL('./mob-yaw.json', import.meta.url)) ? fs.readFileSync(new URL('./mob-yaw.json', import.meta.url), 'utf8') : '{}');

// all model files under a pack folder, by base name
function packModels(dir) {
  const out = new Map();
  const walk = d => {
    for (const f of fs.readdirSync(path.join(CACHE, d), { withFileTypes: true })) {
      const rel = `${d}/${f.name}`;
      if (f.isDirectory()) walk(rel);
      else if (/\.(gltf|glb)$/.test(f.name)) out.set(f.name.replace(/\.gltf\.glb$|\.gltf$|\.glb$/, ''), rel);
    }
  };
  if (fs.existsSync(path.join(CACHE, dir))) walk(dir);
  return out;
}
const kitFrom = (dir, pick = () => true) => [...packModels(dir)].filter(([k]) => pick(k)).sort().map(([key, src]) => ({ key, src }));

const JOBS = [
  ...['Knight', 'Barbarian', 'Mage', 'Rogue', 'Rogue_Hooded'].map(n =>
    ({ kind: 'char', src: `${ADV}/${n}.glb`, out: `chars/${n.toLowerCase()}.glb` })),
  ...['Skeleton_Warrior', 'Skeleton_Minion', 'Skeleton_Mage', 'Skeleton_Rogue'].map(n =>
    ({ kind: 'char', src: `${SKEL}/${n}.glb`, out: `chars/${n.toLowerCase()}.glb` })),
  // one quantization volume for the whole kit, so every part shares one skin
  { kind: 'equip', out: 'chars/equip.glb', quantizationVolume: 'scene' },
  // the skeleton pack's set is a superset (95 clips) of the adventurers' (76), same rig
  { kind: 'anims', src: `${SKEL}/Skeleton_Warrior.glb`, out: 'chars/rig_anims.glb' },
  { kind: 'kit', out: 'kits/dungeon.glb', items: DUNGEON.map(k => ({ key: k, src: findFile(DUN, k) })) },
  // Quaternius meshes carry COLOR_0 as wind/shading masks for their own shader; glTF
  // multiplies it into the base colour, which paints the leaves red. Drop it.
  { kind: 'kit', out: 'kits/nature.glb', texture: 512, dropNormalMaps: true, dropVertexColors: true, greenLeaves: true,
    items: NATURE.map(k => ({ key: k, src: `${NAT}/${k}.gltf` })) },
  ...MOBS.map(m => ({ kind: 'mob', ...m, out: `mobs/${m.name}.glb`, texture: 256 })),
  // towns: KayKit Medieval Hexagon houses, shops, temple, walls and street props
  { kind: 'kit', out: 'kits/town.glb', items: kitFrom('kaykit-hexagon') },
  // interiors: KayKit Furniture Bits; graveyards: KayKit Halloween Bits
  { kind: 'kit', out: 'kits/furniture.glb', items: kitFrom('kaykit-furniture') },
  { kind: 'kit', out: 'kits/graveyard.glb', items: kitFrom('kaykit-halloween') },
];

function findFile(dir, key) {
  for (const f of [`${key}.gltf.glb`, `${key}.glb`]) if (fs.existsSync(path.join(CACHE, dir, f))) return `${dir}/${f}`;
  if (BLEND_ONLY || process.argv[3]) return null;   // building only some files: other packs may be absent
  throw new Error(`missing ${dir}/${key}`);
}

const io = new NodeIO().registerExtensions(ALL_EXTENSIONS).registerDependencies({
  'meshopt.encoder': MeshoptEncoder, 'meshopt.decoder': MeshoptDecoder,
});

async function finish(doc, job) {
  const tf = [dedup(), prune({ keepLeaves: false })];
  if (job.texture) {
    tf.push(textureCompress({ encoder: sharp, targetFormat: 'webp', resize: [job.texture, job.texture] }));
  }
  tf.push(meshopt({ encoder: MeshoptEncoder, level: 'medium', ...(job.quantizationVolume ? { quantizationVolume: job.quantizationVolume } : {}) }),
    unpartition());
  await doc.transform(...tf);
  const out = path.join(OUT, job.out);
  fs.mkdirSync(path.dirname(out), { recursive: true });
  await io.write(out, doc);
  return fs.statSync(out).size;
}

// Disposing an Animation alone leaves its samplers holding every keyframe accessor
// (a "mesh only" character stayed 2 MB); dispose the parts first.
function dropAnimation(a) {
  for (const c of a.listChannels()) c.dispose();
  for (const s of a.listSamplers()) s.dispose();
  a.dispose();
}

// The clips the client plays. The full set is 95; the rest (chairs, jumps, T-pose...) is
// dead weight in the one file every character needs before it can move.
const CLIPS = new Set(['Idle', 'Idle_B', 'Idle_Combat', 'Unarmed_Idle', '2H_Melee_Idle',
  'Walking_A', 'Walking_B', 'Walking_C', 'Walking_Backwards', 'Walking_D_Skeletons',
  'Running_A', 'Running_B', 'Running_C', 'Running_Strafe_Left', 'Running_Strafe_Right',
  '1H_Melee_Attack_Chop', '1H_Melee_Attack_Slice_Diagonal', '1H_Melee_Attack_Slice_Horizontal',
  '1H_Melee_Attack_Stab', '1H_Melee_Attack_Jump_Chop', '2H_Melee_Attack_Chop', '2H_Melee_Attack_Slice',
  '2H_Melee_Attack_Spin', '2H_Melee_Attack_Stab', 'Dualwield_Melee_Attack_Chop',
  'Dualwield_Melee_Attack_Slice', 'Dualwield_Melee_Attack_Stab', 'Unarmed_Melee_Attack_Punch_A',
  'Unarmed_Melee_Attack_Kick', '1H_Ranged_Aiming', '1H_Ranged_Shoot', '2H_Ranged_Aiming',
  '2H_Ranged_Shoot', 'Throw', 'Spellcast_Long', 'Spellcast_Raise', 'Spellcast_Shoot', 'Spellcasting',
  'Spellcast_Summon', 'Block', 'Blocking', 'Block_Hit', 'Block_Attack', 'Hit_A', 'Hit_B',
  'Dodge_Forward', 'Dodge_Backward', 'Dodge_Left', 'Dodge_Right', 'Death_A', 'Death_A_Pose',
  'Death_B', 'Death_B_Pose', 'Death_C_Skeletons', 'Cheer', 'Taunt', 'Interact', 'PickUp', 'Use_Item',
  'Sit_Floor_Down', 'Sit_Floor_Idle', 'Sit_Floor_StandUp', 'Lie_Down', 'Lie_Idle', 'Lie_StandUp',
  'Skeletons_Awaken_Floor', 'Skeletons_Awaken_Standing', 'Skeletons_Inactive_Floor_Pose',
  'Spawn_Ground_Skeletons']);

async function buildChar(job) {
  const doc = await io.read(path.join(CACHE, job.src));
  for (const a of doc.getRoot().listAnimations()) dropAnimation(a);
  await doc.transform(weld());
  return finish(doc, job);
}

async function buildAnims(job) {
  const doc = await io.read(path.join(CACHE, job.src));
  for (const n of doc.getRoot().listNodes()) { if (n.getMesh()) n.setMesh(null); n.setSkin(null); }
  for (const a of doc.getRoot().listAnimations()) if (!CLIPS.has(a.getName())) dropAnimation(a);
  await doc.transform(resample());
  return finish(doc, job);
}

async function buildKit(job) {
  const doc = await io.read(path.join(CACHE, job.items[0].src));
  const scene = doc.getRoot().getDefaultScene() || doc.getRoot().listScenes()[0];
  const wrap = (sc, key) => {
    const holder = doc.createNode(key);
    for (const child of sc.listChildren()) { sc.removeChild(child); holder.addChild(child); }
    return holder;
  };
  const first = wrap(scene, job.items[0].key);
  scene.addChild(first);
  for (const it of job.items.slice(1)) {
    const src = await io.read(path.join(CACHE, it.src));
    const map = mergeDocuments(doc, src);
    for (const sc of src.getRoot().listScenes()) {
      const merged = map.get(sc);
      scene.addChild(wrap(merged, it.key));
      merged.dispose();
    }
  }
  if (job.dropVertexColors) {
    for (const m of doc.getRoot().listMeshes()) for (const p of m.listPrimitives()) p.setAttribute('COLOR_0', null);
  }
  // the bushes share the twisted tree's autumn-red leaf atlas; a forest of red bushes
  // read as a bug, so their leaves are turned green (channel remix keeps the shading)
  for (const m of doc.getRoot().listMaterials()) {
    const tex = m.getBaseColorTexture();
    if (!job.greenLeaves || !tex || !/TwistedTree/i.test(m.getName())) continue;
    const img = await sharp(Buffer.from(tex.getImage()))
      .recomb([[0.25, 0.15, 0], [0.85, 0.25, 0], [0.1, 0.1, 0.2]]).png().toBuffer();
    tex.setImage(new Uint8Array(img)).setMimeType('image/png');
  }
  if (job.dropNormalMaps) {
    for (const m of doc.getRoot().listMaterials()) { m.setNormalTexture(null); m.setOcclusionTexture(null); }
  }
  await doc.transform(weld());
  return finish(doc, job);
}

// ---- the equipment kit ----
// The five KayKit adventurers share one 41-joint rig (same joints, same order, same bind
// matrices) and paint everything from one texture each: an 8x4 grid of vertical colour ramps.
// So: every body part (6 per model) and every piece (weapons, shields, hats, capes, plus the
// pack's standalone pieces) goes onto the knight's rig, and every UV is re-pointed at one
// shared palette with a column per ramp. Recolouring a piece is then a change of column, and
// a dressed hero merges into one mesh with one material (equip.js).
const ADV_ROOT = 'kaykit-adventurers/addons/kaykit_character_pack_adventures';
const RAMPS = JSON.parse(fs.readFileSync(new URL('./ramps.json', import.meta.url), 'utf8'));
const EQUIP_MODELS = [['knight', 'Knight', 'knight'], ['barbarian', 'Barbarian', 'barbarian'], ['mage', 'Mage', 'mage'],
  ['rogue', 'Rogue', 'rogue'], ['rogue_hooded', 'Rogue_Hooded', 'rogue']];
const zQuat = deg => [0, 0, Math.sin(deg * Math.PI / 360), Math.cos(deg * Math.PI / 360)];
// the pack's standalone pieces hang where the matching piece in a character hangs
const EQUIP_EXTRAS = [
  { key: 'shield_round_color', tex: 'knight', like: 'knight-Round_Shield' },
  { key: 'shield_badge_color', tex: 'knight', like: 'knight-Badge_Shield' },
  { key: 'shield_square_color', tex: 'knight', like: 'knight-Rectangle_Shield' },
  { key: 'shield_spikes_color', tex: 'knight', like: 'knight-Spike_Shield' },
  { key: 'sword_2handed_color', tex: 'knight', like: 'knight-2H_Sword' },
  // on the back, leaning so the arrows rise over the right shoulder
  { key: 'quiver', tex: 'rogue', mount: { bone: 'chest', t: [-0.1, 0.12, -0.3], r: zQuat(24), s: [0.8, 0.8, 0.8] } },
];
const PAL_W = 4, PAL_H = 128;
const hexRgb = h => [1, 3, 5].map(i => parseInt(h.slice(i, i + 2), 16));
const mixRgb = (a, b, t) => a.map((v, i) => Math.round(v + (b[i] - v) * t));
const rampOf = (top, mid, bot) => Array.from({ length: PAL_H }, (_, r) => {
  const f = r / (PAL_H - 1);
  return f < 0.5 ? mixRgb(top, mid, f / 0.5) : mixRgb(mid, bot, (f - 0.5) / 0.5);
});
// tier 0: dull and a little dark; a metal's darker parts (the knight's dark steel starts where steel ends)
const wornOf = rows => rows.map(c => { const l = 0.3 * c[0] + 0.59 * c[1] + 0.11 * c[2]; return c.map(v => Math.round((v + (l - v) * 0.4) * 0.92)); });
const darkOf = rows => { const b = rows[rows.length - 1]; return rampOf(b, b.map(v => v * 0.83), b.map(v => v * 0.66)); };
const FAMILY_ROLE = { metal: 'metal', leather: 'leather', fur: 'fur', wood: 'wood', cloth: 'cloth', gem: 'gem', skin: 'skin' };

async function buildEquip(job) {
  const srcs = [];
  for (const [key, file, tex] of EQUIP_MODELS) {
    const doc = await io.read(path.join(CACHE, `${ADV_ROOT}/Characters/gltf/${file}.glb`));
    for (const a of doc.getRoot().listAnimations()) dropAnimation(a);
    srcs.push({ key, tex, doc });
  }
  // the rig must be the same in every model, or parts can't share it
  const base = srcs[0].doc;
  const baseSkin = base.getRoot().listSkins()[0];
  const joints = baseSkin.listJoints();
  const jointNames = joints.map(j => j.getName());
  const ibm0 = baseSkin.getInverseBindMatrices();
  for (const s of srcs.slice(1)) {
    const sk = s.doc.getRoot().listSkins()[0];
    if (sk.listJoints().map(j => j.getName()).join() !== jointNames.join()) throw new Error(`equip: ${s.key} has another rig`);
    const ibm = sk.getInverseBindMatrices();
    for (let i = 0; i < joints.length; i++) {
      const a = ibm0.getElement(i, []), b = ibm.getElement(i, []);
      if (a.some((v, k) => Math.abs(v - b[k]) > 1e-4)) throw new Error(`equip: ${s.key} binds ${jointNames[i]} differently`);
    }
  }

  // ---- the palette: a column per (texture, swatch) the models use, then the authored ramps ----
  const cols = [];
  const colOf = new Map();
  const addCol = (name, rows, role, family = null) => { colOf.set(name, cols.length); cols.push({ name, rows, role, family }); };
  const harvested = new Set();
  for (const s of srcs) {
    if (harvested.has(s.tex)) continue;
    harvested.add(s.tex);
    const img = s.doc.getRoot().listTextures()[0].getImage();
    const { data, info } = await sharp(Buffer.from(img)).raw().ensureAlpha().toBuffer({ resolveWithObject: true });
    const at = (x, y) => { const i = (y * info.width + x) * 4; return [data[i], data[i + 1], data[i + 2]]; };
    for (const [sw, role] of Object.entries(RAMPS.swatchRoles[s.tex])) {
      const sx = +sw % 8, sy = Math.floor(+sw / 8);
      const x = Math.round((sx * 128 + 52) * info.width / 1024), y0 = sy * info.height / 4, step = info.height / 4 / PAL_H;
      const rows = Array.from({ length: PAL_H }, (_, r) => {
        const a = at(x, Math.floor(y0 + r * step)), b = at(x, Math.min(info.height - 1, Math.floor(y0 + r * step + step / 2)));
        return a.map((v, k) => Math.round((v + b[k]) / 2));
      });
      addCol(`${s.tex}:${sw}`, rows, role);
    }
  }
  for (const [name, a] of Object.entries(RAMPS.authored)) addCol(name, rampOf(...a.c.map(hexRgb)), FAMILY_ROLE[a.family], a.family);
  for (const [cls, [a, b]] of Object.entries(RAMPS.classes)) addCol(`class_${cls}`, rampOf(mixRgb(hexRgb(a), [255, 255, 255], 0.3), hexRgb(a), hexRgb(b)), 'cloth', 'cloth');
  for (const [set, [a, b, accent]] of Object.entries(RAMPS.sets)) {
    addCol(`set_${set}`, rampOf(mixRgb(hexRgb(a), [255, 255, 255], 0.3), hexRgb(a), hexRgb(b)), 'cloth', 'cloth');
    addCol(`set_${set}_accent`, rampOf(mixRgb(hexRgb(accent), [255, 255, 255], 0.35), hexRgb(accent), mixRgb(hexRgb(accent), [0, 0, 0], 0.5)), 'gem', 'gem');
  }
  for (const c of [...cols]) {
    // a gem or an element that shines (tier 4 and up, a legendary, a prestige emblem): the same
    // colour, a little brighter; equip.js lights exactly these columns from within
    if (c.family === 'gem' || c.name === 'gold' || c.name === 'silver') {
      addCol(`${c.name}~glow`, c.rows.map(px => px.map(v => Math.min(255, Math.round(v * 1.12 + 18)))), 'gem', 'glow');
    }
    if (!c.family || !['metal', 'leather', 'cloth', 'fur', 'wood'].includes(c.family)) continue;
    addCol(`${c.name}~worn`, wornOf(c.rows), c.role, c.family);
    if (c.family === 'metal' || c.family === 'cloth') {
      // a metal's darker parts, a cloth's shadowed panels
      const role = c.family === 'metal' ? 'metal_dark' : 'cloth_dark';
      addCol(`${c.name}~dark`, darkOf(c.rows), role, c.family);
      addCol(`${c.name}~worn~dark`, darkOf(wornOf(c.rows)), role, c.family);
    }
  }
  const N = cols.length;
  const W = N * PAL_W;
  const rgb = Buffer.alloc(W * PAL_H * 3), mr = Buffer.alloc(W * PAL_H * 3);
  cols.forEach((c, i) => {
    const worn = c.name.includes('~worn');
    const rough = Math.min(1, (RAMPS.roughness[c.role] ?? 0.8) + (worn ? 0.15 : 0));
    const metal = (RAMPS.metalness[c.role] ?? 0) * (worn ? 0.4 : 1);
    for (let y = 0; y < PAL_H; y++) for (let x = 0; x < PAL_W; x++) {
      const o = (y * W + i * PAL_W + x) * 3;
      rgb[o] = c.rows[y][0]; rgb[o + 1] = c.rows[y][1]; rgb[o + 2] = c.rows[y][2];
      mr[o] = 255; mr[o + 1] = Math.round(rough * 255); mr[o + 2] = Math.round(metal * 255);
    }
  });
  const png = buf => sharp(buf, { raw: { width: W, height: PAL_H, channels: 3 } }).png({ compressionLevel: 9 }).toBuffer();
  const palTex = base.createTexture('equip_palette').setImage(new Uint8Array(await png(rgb))).setMimeType('image/png');
  const mrTex = base.createTexture('equip_palette_mr').setImage(new Uint8Array(await png(mr))).setMimeType('image/png');
  const mat = base.createMaterial('equip').setBaseColorTexture(palTex).setMetallicRoughnessTexture(mrTex)
    .setMetallicFactor(1).setRoughnessFactor(1);
  for (const ti of [mat.getBaseColorTextureInfo(), mat.getMetallicRoughnessTextureInfo()]) {
    ti.setMinFilter(TextureInfo.MinFilter.LINEAR).setMagFilter(TextureInfo.MagFilter.LINEAR)
      .setWrapS(TextureInfo.WrapMode.CLAMP_TO_EDGE).setWrapT(TextureInfo.WrapMode.CLAMP_TO_EDGE);
  }

  // every UV onto its ramp's column: u picks the column, v keeps the place in the ramp (the shade)
  const pieces = {};
  const readdress = (mesh, tex) => {
    const used = {};
    for (const prim of mesh.listPrimitives()) {
      const uv = prim.getAttribute('TEXCOORD_0');
      const out = uv.clone();
      const el = [];
      for (let i = 0; i < uv.getCount(); i++) {
        uv.getElement(i, el);
        const sx = Math.min(7, Math.max(0, Math.floor(el[0] * 8))), sy = Math.min(3, Math.max(0, Math.floor(el[1] * 4)));
        const col = colOf.get(`${tex}:${sx + 8 * sy}`);
        if (col === undefined) throw new Error(`equip: ${tex} swatch ${sx + 8 * sy} has no role in ramps.json`);
        used[col] = cols[col].role;
        const fv = Math.min(1 - 0.5 / PAL_H, Math.max(0.5 / PAL_H, el[1] * 4 - sy));
        out.setElement(i, [(col + 0.5) / N, fv]);
      }
      prim.setAttribute('TEXCOORD_0', out);
      prim.setMaterial(mat);
    }
    return used;
  };
  const tris = mesh => mesh.listPrimitives().reduce((n, p) => n + (p.getIndices() ? p.getIndices().getCount() : p.getAttribute('POSITION').getCount()) / 3, 0);
  const rig = base.getRoot().listNodes().find(n => n.getName() === 'Rig');
  const bone = name => joints.find(j => j.getName() === name);
  const models = {};
  const PART = /_(Head_Hooded|Head|Body|ArmLeft|ArmRight|LegLeft|LegRight)$/;
  for (const s of srcs) {
    const map = s.doc === base ? null : mergeDocuments(base, s.doc);
    const here = n => (map ? map.get(n) : n);
    const kept = new Set();
    for (const n of s.doc.getRoot().listNodes()) {
      if (!n.getMesh()) continue;
      const node = here(n);
      if (n.getSkin()) {
        const m = PART.exec(n.getName());
        if (!m) throw new Error(`equip: unknown body part ${n.getName()}`);
        const part = m[1] === 'Head_Hooded' ? 'HeadHooded' : m[1];
        if (s.key === 'rogue_hooded' && part !== 'HeadHooded') continue;   // the rest is the rogue's
        const model = s.key === 'rogue_hooded' ? 'rogue' : s.key;
        const name = `${model}-${part}`;
        node.getParentNode()?.removeChild(node);
        rig.addChild(node);
        node.setName(name).setSkin(baseSkin);
        kept.add(node);
        pieces[name] = { type: 'part', model, part, tris: tris(node.getMesh()), cols: readdress(node.getMesh(), s.tex) };
        (models[model] ||= {})[part] = name;
      } else {
        if (s.key === 'rogue_hooded') continue;
        const boneName = n.getParentNode().getName();
        const name = `${s.key}-${n.getName()}`;
        node.getParentNode()?.removeChild(node);
        bone(boneName).addChild(node);
        node.setName(name);
        kept.add(node);
        pieces[name] = { type: 'prop', model: s.key, bone: boneName, tris: tris(node.getMesh()),
          mount: { t: node.getTranslation(), r: node.getRotation(), s: node.getScale() }, cols: readdress(node.getMesh(), s.tex) };
      }
    }
    if (map) {
      // the copy's own rig, and the parts and pieces it duplicates, go
      for (const n of s.doc.getRoot().listNodes()) if (!kept.has(map.get(n))) map.get(n).dispose();
      for (const sk of s.doc.getRoot().listSkins()) map.get(sk).dispose();
      for (const sc of s.doc.getRoot().listScenes()) map.get(sc).dispose();
    }
  }
  for (const x of EQUIP_EXTRAS) {
    const doc = await io.read(path.join(CACHE, `${ADV_ROOT}/Assets/gltf/${x.key}.gltf`));
    const map = mergeDocuments(base, doc);
    const n = map.get(doc.getRoot().listNodes().find(nd => nd.getMesh()));
    const mount = x.like ? { bone: pieces[x.like].bone, ...pieces[x.like].mount } : x.mount;
    n.getParentNode()?.removeChild(n);
    for (const sc of doc.getRoot().listScenes()) map.get(sc).dispose();
    bone(mount.bone).addChild(n);
    const name = `kit-${x.key}`;
    n.setName(name).setTranslation(mount.t).setRotation(mount.r).setScale(mount.s);
    pieces[name] = { type: 'prop', model: 'kit', bone: mount.bone, tris: tris(n.getMesh()),
      mount: { t: mount.t, r: mount.r, s: mount.s }, cols: readdress(n.getMesh(), x.tex) };
  }
  // pieces made in Blender on the same rig (blender/out/equip: a .glb and its sidecar, e.g.
  // models/archmage.py --export): skinned, every joint found again by name, and every UV a cell of
  // the model's own small palette, whose kit column the sidecar names
  const EQUIP_BLEND = path.join(BLEND, 'equip');
  for (const f of fs.existsSync(EQUIP_BLEND) ? fs.readdirSync(EQUIP_BLEND).filter(f => f.endsWith('.json')).sort() : []) {
    const side = JSON.parse(fs.readFileSync(path.join(EQUIP_BLEND, f), 'utf8'));
    const doc = await io.read(path.join(EQUIP_BLEND, `${side.name}.glb`));
    for (const a of doc.getRoot().listAnimations()) dropAnimation(a);
    const order = doc.getRoot().listSkins()[0].listJoints().map(j => jointNames.indexOf(j.getName()));
    if (order.some(i => i < 0)) throw new Error(`equip: ${side.name} has joints the rig lacks`);
    const { cols: pc, rows: pr, keys } = side.palette;
    const map = mergeDocuments(base, doc);
    const kept = new Set();
    for (const n of doc.getRoot().listNodes()) {
      if (!n.getMesh() || !n.getSkin()) continue;
      const node = map.get(n);
      const used = {};
      for (const prim of node.getMesh().listPrimitives()) {
        const J = prim.getAttribute('JOINTS_0'), uv = prim.getAttribute('TEXCOORD_0');
        const j2 = J.clone(), uv2 = uv.clone(), el = [];
        for (let i = 0; i < J.getCount(); i++) { J.getElement(i, el); j2.setElement(i, el.map(j => order[j])); }
        for (let i = 0; i < uv.getCount(); i++) {
          uv.getElement(i, el);
          // (glTF's v runs down the image; the Blender palette's rows count up from the bottom)
          const up = (1 - el[1]) * pr, cx = Math.min(pc - 1, Math.floor(el[0] * pc)), cy = Math.min(pr - 1, Math.floor(up));
          const name = keys[cy * pc + cx];
          const col = colOf.get(name);
          if (col === undefined) throw new Error(`equip: ${side.name} paints with ${name}, which the palette lacks`);
          used[col] = cols[col].role;
          const light = Math.min(1, Math.max(0, (up - cy - 0.15) / 0.7));
          uv2.setElement(i, [(col + 0.5) / N, Math.min(1 - 0.5 / PAL_H, Math.max(0.5 / PAL_H, 1 - light))]);
        }
        prim.setAttribute('JOINTS_0', j2).setAttribute('TEXCOORD_0', uv2).setMaterial(mat);
      }
      node.getParentNode()?.removeChild(node);
      rig.addChild(node);
      node.setSkin(baseSkin);
      kept.add(node);
      const bone = side.pieces[n.getName()];
      pieces[n.getName()] = { type: 'worn', model: side.name, bone: bone === 'skinned' ? null : bone, tris: tris(node.getMesh()), cols: used };
    }
    for (const n of doc.getRoot().listNodes()) if (!kept.has(map.get(n))) map.get(n).dispose();
    for (const sk of doc.getRoot().listSkins()) map.get(sk).dispose();
    for (const sc of doc.getRoot().listScenes()) map.get(sc).dispose();
  }
  for (const m of base.getRoot().listMaterials()) if (m !== mat) m.dispose();
  for (const t of base.getRoot().listTextures()) if (t !== palTex && t !== mrTex) t.dispose();
  await base.transform(weld());
  const size = await finish(base, job);
  // the manifest: what every column is, every piece, where it hangs and which roles it paints
  const manifest = {
    v: 1, palette: { cols: N, w: PAL_W, h: PAL_H },
    joints: jointNames,
    columns: cols.map(c => ({ name: c.name, role: c.role, family: c.family })),
    models, pieces,
  };
  fs.writeFileSync(path.join(OUT, 'chars', 'equip.json'), JSON.stringify(manifest));
  console.log(`chars/equip.json  ${N} palette columns, ${Object.keys(pieces).length} pieces`);
  return size;
}

// each source pack's licence travels with the built files
const LICENCES = BLEND_ONLY ? {} : {
  'kaykit-adventurers.txt': 'kaykit-adventurers/addons/kaykit_character_pack_adventures/LICENSE.txt',
  'kaykit-skeletons.txt': 'kaykit-skeletons/addons/kaykit_character_pack_skeletons/LICENSE.txt',
  'kaykit-dungeon-remastered.txt': 'kaykit-dungeon/addons/kaykit_dungeon_remastered/Assets/LICENSE.txt',
  'quaternius-stylized-nature-megakit.txt': 'quaternius-nature/License_Standard.txt',
  'quaternius-farm-animals.txt': 'quaternius-farm/Farm Animals by @Quaternius/License.txt',
  'kaykit-medieval-hexagon.txt': 'kaykit-hexagon/addons/kaykit_medieval_hexagon_pack/LICENSE.txt',
  'kaykit-furniture-bits.txt': 'kaykit-furniture/addons/kaykit_furniture_bits/Assets/LICENSE.txt',
  'kaykit-halloween-bits.txt': 'kaykit-halloween/addons/kaykit_halloween_bits/Assets/LICENSE.txt',
  'quaternius-animated-monster-pack.txt': 'quaternius-monsters/Animated Monster Pack by @Quaternius/License.txt',
};
// the Blender models: every .json sidecar blender/out holds (build them with blender/run.sh first)
if (fs.existsSync(BLEND)) {
  for (const f of fs.readdirSync(BLEND).filter(f => f.endsWith('.json')).sort()) {
    const side = JSON.parse(fs.readFileSync(path.join(BLEND, f), 'utf8'));
    if (fs.existsSync(path.join(BLEND, `${side.name}.glb`))) JOBS.push({ kind: 'blend', side, out: `bodies/${side.name}.glb` });
  }
}
fs.mkdirSync(path.join(OUT, 'licenses'), { recursive: true });
for (const [dst, src] of Object.entries(LICENCES)) {
  if (fs.existsSync(path.join(CACHE, src))) fs.copyFileSync(path.join(CACHE, src), path.join(OUT, 'licenses', dst));
  else if (!process.argv[3]) throw new Error(`missing licence ${src}`);
}

// ---- animated creatures from FBX ----
const FBX2GLTF = path.resolve(path.dirname(new URL(import.meta.url).pathname),
  'node_modules/fbx2gltf/bin', process.platform === 'darwin' ? 'Darwin' : process.platform === 'win32' ? 'Windows_NT' : 'Linux',
  process.platform === 'win32' ? 'FBX2glTF.exe' : 'FBX2glTF');

async function buildMob(job) {
  const tmp = path.join(os.tmpdir(), `mob_${job.name}_${process.pid}`);
  const r = spawnSync(FBX2GLTF, ['--binary', '--input', path.join(CACHE, job.fbx), '--output', tmp], { encoding: 'utf8' });
  if (r.status !== 0) throw new Error(`FBX2glTF failed on ${job.fbx}: ${r.stderr || r.stdout}`);
  const doc = await io.read(tmp + '.glb');
  fs.rmSync(tmp + '.glb', { force: true });
  const root = doc.getRoot();
  // lights exported from the source scene are not ours
  for (const ext of root.listExtensionsUsed()) if (ext.extensionName === 'KHR_lights_punctual') ext.dispose();
  // the cute monsters keep their colours in one atlas texture beside the FBX files
  if (job.tex && fs.existsSync(path.join(CACHE, job.tex))) {
    const tex = doc.createTexture(job.name).setImage(fs.readFileSync(path.join(CACHE, job.tex))).setMimeType('image/png');
    for (const m of root.listMaterials()) m.setBaseColorTexture(tex).setBaseColorFactor([1, 1, 1, 1]);
  }
  for (const m of root.listMaterials()) m.setMetallicFactor(0).setRoughnessFactor(0.85);
  if (job.gamma) {
    for (const m of root.listMaterials()) {
      const [r, g, b, a] = m.getBaseColorFactor();
      m.setBaseColorFactor([r ** (1 / 2.2), g ** (1 / 2.2), b ** (1 / 2.2), a]);
    }
  }
  for (const a of root.listAnimations()) a.setName(a.getName().replace(/^.*\|/, '').replace(/\.\d+$/, (x) => x));
  // a job's renames; with renames, the clips it doesn't name are dropped (sitting down, carrying...)
  if (job.rename) {
    for (const a of root.listAnimations()) {
      const to = job.rename[a.getName()];
      if (to) a.setName(to); else dropAnimation(a);
    }
  }
  // face +Z, feet on the ground, 1 m tall
  const scene = root.getDefaultScene() || root.listScenes()[0];
  const holder = doc.createNode(job.name);
  for (const c of scene.listChildren()) { scene.removeChild(c); holder.addChild(c); }
  scene.addChild(holder);
  const yaw = MOB_YAW[job.name] ?? job.yaw ?? 0;
  holder.setRotation([0, Math.sin(yaw / 2), 0, Math.cos(yaw / 2)]);
  const b = getBounds(scene);
  const h = Math.max(1e-3, b.max[1] - b.min[1]);
  const s = 1 / h;
  holder.setScale([s, s, s]);
  const b2 = getBounds(scene);
  holder.setTranslation([-(b2.min[0] + b2.max[0]) / 2, -b2.min[1], -(b2.min[2] + b2.max[2]) / 2]);
  await doc.transform(resample(), weld());
  MOB_INDEX[job.name] = { anims: root.listAnimations().map(a => a.getName()) };
  return finish(doc, job);
}
const MOB_INDEX = {};

async function buildBlend(job) {
  const doc = await io.read(path.join(BLEND, `${job.side.name}.glb`));
  const root = doc.getRoot();
  for (const m of root.listMaterials()) m.setMetallicFactor(0).setRoughnessFactor(0.85);
  await doc.transform(resample(), weld());
  BODY_INDEX[job.side.name] = { kind: job.side.kind, anims: root.listAnimations().map(a => a.getName()),
    tris: job.side.tris, height: job.side.height, ...(job.side.for ? { for: job.side.for } : {}),
    ...(job.side.look ? { look: job.side.look } : {}), ...(job.side.ref ? { ref: job.side.ref } : {}) };   // ref: the size the game's h means          // how it's drawn: { opacity, glow }
  return finish(doc, job);
}
const BODY_INDEX = {};

const only = process.argv[3];
for (const job of JOBS) {
  if (only && !job.out.includes(only)) continue;
  if (BLEND_ONLY && job.kind !== 'blend') continue;
  const size = job.kind === 'char' ? await buildChar(job) : job.kind === 'anims' ? await buildAnims(job)
    : job.kind === 'mob' ? await buildMob(job) : job.kind === 'equip' ? await buildEquip(job)
    : job.kind === 'blend' ? await buildBlend(job) : await buildKit(job);
  console.log(`${job.out}  ${(size / 1024).toFixed(0)} KB`);
}
// the client's creature registry reads each model's clip names from here
if (Object.keys(MOB_INDEX).length) {
  const file = path.join(OUT, 'mobs', 'index.json');
  const prev = fs.existsSync(file) ? JSON.parse(fs.readFileSync(file, 'utf8')) : {};
  fs.writeFileSync(file, JSON.stringify({ ...prev, ...MOB_INDEX }, null, 1));
}
// the client reads which Blender bodies exist, and their clips, from here
if (Object.keys(BODY_INDEX).length) {
  const file = path.join(OUT, 'bodies', 'index.json');
  const prev = fs.existsSync(file) ? JSON.parse(fs.readFileSync(file, 'utf8')) : {};
  fs.writeFileSync(file, JSON.stringify({ ...prev, ...BODY_INDEX }, null, 1));
}
// packs that ship without a licence file: record the licence stated on their OpenGameArt page
const NOTE = (name, url) => `${name} by Quaternius (quaternius.com)\nLicence: CC0 1.0 Universal (public domain dedication), as stated at ${url}\n`;
for (const [f, n, u] of [
  ['quaternius-cute-animated-monsters.txt', 'Cute Animated Monsters (Aug 2020)', 'https://opengameart.org/content/textured-cute-monster-pack'],
  ['quaternius-animal-pack-vol2.txt', 'Animal Pack Vol.2', 'https://opengameart.org/content/animated-animales-low-poly'],
  ['quaternius-animals-pack.txt', 'Animals Pack', 'https://opengameart.org/content/5-low-poly-animals'],
  ['quaternius-ultimate-animated-character-pack.txt', 'Ultimate Animated Character Pack (Nov 2019)', 'https://opengameart.org/content/animated-characters-pack'],
]) fs.writeFileSync(path.join(OUT, 'licenses', f), NOTE(n, u));
