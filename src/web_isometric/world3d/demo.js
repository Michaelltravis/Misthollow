// The look-and-feel scene from milestone M0: four real room layouts from the MUD's room
// generator (a glade, a brook, a crypt, a hall) stitched into one world, a knight and the
// crypt's skeletons. It is the backdrop behind the login screen (the camera drifts over
// it) and, at /play?demo, a playable page for checking art, camera and performance
// (/play?demo&gallery=dungeon|nature lays out a whole kit).
import * as THREE from 'three';
import { spawnCharacter } from './assets.js';
import { World } from './world.js';
import { Controller } from './controller.js';
import { cutout } from './cutout.js';

const ROOMS = [
  { cx: 0, cy: 0, vnum: 990001, sector: 'forest', name: 'Whispering Glade',
    description: 'Tall oaks ring a mossy clearing. A small pond glitters among the ferns.',
    exits: { east: { to_room: 990002 }, south: { to_room: 990003 } } },
  { cx: 1, cy: 0, vnum: 990002, sector: 'forest', name: 'Brookside Trail',
    description: 'A brook babbles across the old trail between the pines.',
    exits: { west: { to_room: 990001 }, south: { to_room: 990004 } } },
  { cx: 0, cy: 1, vnum: 990003, sector: 'inside', name: 'Crypt Antechamber',
    description: 'Cold stone and guttering torches. Something shuffles in the dark.',
    exits: { north: { to_room: 990001 }, east: { to_room: 990004 } } },
  { cx: 1, cy: 1, vnum: 990004, sector: 'inside', name: 'Hall of Bones',
    description: 'The dead keep their vigil here.',
    exits: { north: { to_room: 990002 }, west: { to_room: 990003 } } },
];

export async function buildDemo(engine, kits, { interactive = false, banner = null } = {}) {
  const world = new World(engine, kits);
  const groups = [];
  for (const r of ROOMS) groups.push(world.addRoom(r, r.cx, r.cy).group);

  const hero = await spawnCharacter('knight');
  engine.scene.add(hero.root);
  const start = world.centre(world.byVnum.get(990001));
  hero.root.position.copy(start);
  const ctl = new Controller(engine, hero, (x, z) => world.blocked(x, z));
  ctl.enabled = interactive;
  engine.rig.target.copy(start);
  engine.placeCamera(true);

  const slot = (vnum, i) => {
    const r = world.byVnum.get(vnum), s = r.layout.spawnSlots[i % r.layout.spawnSlots.length];
    return new THREE.Vector3(r.ox + s.x / 16, 0, r.oz + s.y / 16);
  };
  const cast = [
    { model: 'skeleton_warrior', at: slot(990004, 0), anim: 'Idle_Combat' },
    { model: 'skeleton_mage', at: slot(990004, 3), anim: 'Spellcasting' },
    { model: 'skeleton_minion', at: slot(990003, 1), anim: 'Walking_D_Skeletons', patrol: true },
    { model: 'skeleton_rogue', at: slot(990003, 4), anim: 'Idle_B' },
  ];
  const actors = [hero];
  for (const c of cast) {
    const a = await spawnCharacter(c.model);
    a.root.position.copy(c.at);
    a.root.rotation.y = Math.random() * Math.PI * 2;
    a.play(c.anim, 0, 0.9 + Math.random() * 0.2);
    a.patrol = c.patrol ? { home: c.at.clone(), t: Math.random() * 6 } : null;
    engine.scene.add(a.root);
    actors.push(a);
  }

  const onKey = e => { if ((e.key === ' ' || e.key === 'f') && !e.repeat) { ctl.swing(); e.preventDefault(); } };
  const onDown = e => {
    if (e.button !== 0) return;
    const g = ctl.groundAt(e.clientX, e.clientY);
    if (g) ctl.walkTo(g.x, g.z);
  };
  if (interactive) {
    window.addEventListener('keydown', onKey);
    engine.renderer.domElement.addEventListener('pointerdown', onDown);
  }

  let here = null;
  const enter = room => {
    here = room;
    engine.setMood(room.indoor ? 'crypt' : 'forest', !banner);
    if (banner) banner(room.name);
  };
  let orbit = 0;
  function update(dt, t) {
    if (interactive) ctl.update(dt);
    else {
      // behind the login card: drift slowly over the glade and the crypt
      orbit += dt * 0.06;
      engine.rig.target.set(24 + Math.sin(orbit) * 12, 0, 15 + Math.sin(orbit * 0.7) * 6);
    }
    const p = hero.root.position;
    if (interactive) engine.rig.target.set(p.x, 0, p.z);
    cutout.update(engine.camera, interactive ? p : engine.rig.target);
    world.update(dt, t, interactive ? p : engine.rig.target);
    const room = world.roomAt(interactive ? p.x : engine.rig.target.x, interactive ? p.z : engine.rig.target.z);
    if (room && room !== here) enter(room);
    for (const a of actors) {
      if (a.patrol) {
        a.patrol.t += dt * 0.35;
        const k = a.patrol.t;
        const nx = a.patrol.home.x + Math.sin(k) * 2.2, nz = a.patrol.home.z + Math.sin(k * 2) * 1.1;
        a.root.rotation.y = Math.atan2(nx - a.root.position.x, nz - a.root.position.z);
        a.root.position.set(nx, 0, nz);
      }
      a.update(dt);
    }
  }
  function dispose() {
    window.removeEventListener('keydown', onKey);
    engine.renderer.domElement.removeEventListener('pointerdown', onDown);
    for (const g of groups) engine.scene.remove(g);
    for (const a of actors) engine.scene.remove(a.root);
    for (const l of world.lights) engine.scene.remove(l);
  }
  return { world, hero, ctl, update, dispose };
}

// /play?demo&gallery=rooms: one room of every look (room_looks.py), side by side, joined up.
// MH3D_gallery.rooms lists each look's room centre (screenshots: tests/web/probe and the
// owner's checks).
export const LOOK_SAMPLES = [
  { look: 'cave', sector: 'inside', name: 'The Dripping Cavern', description: 'Water drips from the stalactites into still pools. The cave walls glitter.' },
  { look: 'ice_cave', sector: 'inside', name: 'The Freezer', description: 'The walls are sheathed in ice and icicles hang from the roof; the floor is a frozen sheet.' },
  { look: 'lava_cave', sector: 'inside', name: 'The Tunnel To Hell', description: 'Molten rock seeps through cracks in the floor of this sweltering tunnel.' },
  { look: 'mine', sector: 'inside', name: 'The Old Mine Shaft', description: 'Timber props hold up the shaft. Ore glints in the rock where the miners left off.' },
  { look: 'crypt', sector: 'inside', name: 'The Forgotten Crypt', description: 'Coffins line the walls of the crypt, and the dead lie unquiet.' },
  { look: 'sewer', sector: 'inside', name: 'The Muddy Sewer', description: 'A channel of foul water runs down the middle of the sewer.' },
  { look: 'dungeon', sector: 'inside', name: 'The Dungeon Cells', description: 'Broken walls and rubble; the cells stand empty.' },
  { look: 'desert', sector: 'field', name: 'A Sea of Dunes', description: 'The sands roll away in dunes under a merciless sun.' },
  { look: 'snow', sector: 'field', name: 'The Frozen Waste', description: 'Snow lies deep over the tundra, and ice glazes the rocks.' },
  { look: 'shore', sector: 'field', name: 'The Pebbled Shore', description: 'Waves lap at a beach of sand and pebbles strewn with driftwood.' },
  { look: 'volcanic', sector: 'field', name: 'The Ashfields', description: 'Lava glows in the cracks of the ashen ground.' },
  { look: 'swamp', sector: 'swamp', name: 'The Sucking Mire', description: 'Dead trees stand in the black water of the swamp.' },
  { look: 'forest', sector: 'forest', name: 'A Forest Path', description: 'Tall oaks shade the path.' },
  { look: 'inside', sector: 'inside', name: 'The Great Hall', description: 'A plain stone hall.' },
  { look: 'mountain', sector: 'mountain', name: 'A High Mountain Pass', description: 'Cliffs rise on every side of the pass, and scree slides underfoot.' },
  { look: 'water_swim', sector: 'water_swim', name: 'On Mira Retrum', description: 'The river runs wide and slow between grassy banks.' },
  { look: 'water_noswim', sector: 'water_noswim', name: 'On Mira Retrum', description: 'Deep water, too deep to wade.' },
  { look: 'web', sector: 'field', name: 'Webbed Entrance', description: 'Sticky webs coat the limbs of the trees; webbed remains of crickets, rats and men hang in cocoons.' },
  { look: 'necropolis', sector: 'city', name: 'In The Streets Of Morkai', description: 'A crooked street of black stone houses; orc bones lie where they fell, and green ghost-fire burns in the braziers.' },
  // the drow city (terrain-drow.js): its streets, Narbondel, Lolth's temple, a bridge over the abyss,
  // the fungus forest, a noble house
  { look: 'drow', sector: 'city', zone: 51, name: 'The City Street', description: 'A street between the spire houses of the drow, faerie fire glowing on every carved edge.' },
  { look: 'drow', sector: 'inside', zone: 51, key: 'drowcenter', name: 'The Center Of The Drow City', description: 'The heart of the city; the great pillar rises into the dark.' },
  { look: 'drow', sector: 'inside', zone: 51, key: 'drowtemple', name: 'Entrance To The Temple Of Lloth', description: 'The spider-shaped temple of Lolth crouches over the way.' },
  { look: 'drow', sector: 'inside', zone: 51, key: 'drowbridge', name: 'A Thin Underground Bridge', description: 'A narrow bridge over the abyss; the city glows far below.' },
  { look: 'drow', sector: 'inside', zone: 51, key: 'drowfungus', name: 'The Fungus Forest', description: 'Giant mushrooms glow in the dark.' },
  { look: 'drow', sector: 'inside', zone: 51, key: 'drowhouse', name: 'The Main Chamber In The Fourth House', description: 'A hall of the noble house, its walls carved with spiders.' },
  // interiors in their zone's style (world/looks.json 'interiors', terrain-interiors.js)
  { look: 'inside', sector: 'inside', key: 'icastle', tone: { interior: 'castle' }, name: 'The Main Hall', description: 'A long hall of the castle; banners hang on the walls.' },
  { look: 'inside', sector: 'inside', key: 'ithrone', tone: { interior: 'castle' }, name: 'The Throne Room', description: 'The lord sits his throne at the end of the hall.' },
  { look: 'inside', sector: 'inside', key: 'ibedroom', tone: { interior: 'castle' }, name: 'Guest Room', description: 'A guest room of the castle.' },
  { look: 'inside', sector: 'inside', key: 'iarcane', tone: { interior: 'arcane' }, name: 'A Hallway In The Tower', description: 'Arcane sigils glow on the stones of the tower.' },
  { look: 'inside', sector: 'inside', key: 'iholy', tone: { interior: 'holy' }, name: 'The Halls Of Eternity', description: 'White marble halls shine with a holy light.' },
  { look: 'inside', sector: 'inside', key: 'iinfernal', tone: { interior: 'infernal' }, name: 'The Inner Sanctum', description: 'Blood-red stone and the stink of sulphur; the demon prince is worshipped here.' },
  { look: 'inside', sector: 'inside', key: 'ihaunted', tone: { interior: 'haunted' }, name: 'The Parlour', description: 'Dust and cobwebs cover the furniture; something moves in the dark.' },
  { look: 'inside', sector: 'inside', key: 'idwarven', tone: { interior: 'dwarven' }, name: 'The Great Hall Of The King', description: 'Carved pillars of granite hold up the hall of the dwarf king.' },
  { look: 'inside', sector: 'inside', key: 'ielven', tone: { interior: 'elven' }, name: 'A Hall Of Living Wood', description: 'Trees grow through the hall of the elves.' },
  { look: 'underwater', sector: 'underwater', key: 'underwater', name: 'Kelp Forest Chamber', description: 'Kelp sways in the green water and fish dart among the coral.' },
  { look: 'foundry', sector: 'inside', key: 'foundry', name: 'Assembly Line Alpha', description: 'Conveyor belts carry parts past clanking machines.' },
  { look: 'foundry', sector: 'inside', key: 'foundry2', name: 'The Furnace Core', description: 'The great furnace roars; the heat is terrible.' },
  { look: 'castle', sector: 'city', name: 'The Castle Yard', description: 'High walls ring the yard; banners hang from the battlements.' },
  { look: 'castle', sector: 'field', key: 'blackcastle', name: 'Before The Dark Castle', description: 'A grim castle of black stone rises before you.' },
  // a way into another region (key gate*): a named gateway on the far side
  { look: 'field', key: 'gate', name: 'The Road North', description: 'The road runs on between the fields.', zoneExit: { side: 'north', zoneName: 'Elvandar' } },
  { look: 'city', key: 'gatecity', name: 'The North Gate', description: 'The street meets the town gate.', zoneExit: { side: 'north', zoneName: 'The Trade Road' } },
  { look: 'cave', sector: 'inside', key: 'gatecave', name: 'A Narrow Tunnel', description: 'The tunnel runs on through the rock.', zoneExit: { side: 'north', zoneName: 'Orc Tunnels' } },
  { look: 'field', key: 'gateup', name: 'At The Foot Of The Long Stair', description: 'Worn steps climb the cliff toward the keep above.', zoneExit: { side: 'up', zoneName: 'Mahn-Tor Keep' } },
  { look: 'inside', key: 'webroom', name: 'The Den Of The Queen Spider', description: 'Webs coat every wall; cocoons hang from the ceiling and egg sacs crowd the corners of the webbed chamber.' },
  // what the words say stands in a room (room_features.py): real rooms, their features as the game reads them
  { look: 'stones', sector: 'city', key: 'stones', name: 'A Sharp Bend In The Stone Circle', description: 'The circle makes a sharp turn at a stone wrapped in a collar of red-dyed wool. The ground is pocked with the holes of old stakes.',
    features: [{ k: 'standing_stone', n: 2, main: true, c: 'red' }, { k: 'stake_holes', n: 1 }] },
  { look: 'stones', sector: 'city', key: 'slaughter', name: 'At The Slaughter Stone', description: 'A broad black stone lies flat as an altar, chains bolted to its sides.',
    features: [{ k: 'altar', n: 2, main: true, c: 'black' }, { k: 'chains', n: 1 }] },
  { look: 'city', sector: 'city', key: 'gathering', name: 'The Gathering Place', description: 'A wide trampled square rimmed by log benches. A tall pole bears a ring of sun-whitened skulls; old bloodstains darken the packed earth.',
    features: [{ k: 'brazier', n: 1 }, { k: 'pole', n: 1 }, { k: 'skull', n: 2 }, { k: 'bench', n: 2 }, { k: 'blood', n: 1 }, { k: 'ash', n: 1 }] },
  { look: 'inside', sector: 'inside', key: 'temple', name: 'The Temple', description: 'A great altar of slab stone; braziers smoulder at every corner, skull-lamps hang from chains.',
    features: [{ k: 'altar', n: 1, c: 'black' }, { k: 'brazier', n: 2 }, { k: 'skull', n: 1 }, { k: 'lantern', n: 1 }, { k: 'ash', n: 1, c: 'black' }, { k: 'chains', n: 1 }] },
  // the art audit's bare rooms: the named thing made big enough to see, and the scenery a look alone
  // does not draw
  { look: 'inside', sector: 'inside', key: 'fthrone', name: "Upon Zeus's Mighty Throne", description: 'A great throne of white marble stands upon a dais.',
    features: [{ k: 'throne', n: 1, main: true, c: 'white' }, { k: 'candle', n: 2 }] },
  { look: 'dungeon', sector: 'inside', key: 'fstore', name: 'A Store Room', description: 'Crates, sacks and barrels are piled to the ceiling; chains hang from a beam.',
    features: [{ k: 'crate', n: 2 }, { k: 'barrel', n: 2 }, { k: 'chains', n: 1 }] },
  { look: 'cave', sector: 'inside', key: 'fcrystal', name: 'The Crystal Cave', description: 'Crystals of violet and blue jut from every wall; giant mushrooms glow in the corners; bones lie heaped.',
    features: [{ k: 'crystal', n: 3, main: true, c: 'purple' }, { k: 'mushroom', n: 2 }, { k: 'bones', n: 1 }] },
  { look: 'inside', sector: 'inside', key: 'fhall', name: 'The Hall Of Mirrors', description: 'Tall mirrors line the walls; a great bell hangs in its frame; a fireplace roars at the north end.',
    features: [{ k: 'mirror', n: 3, main: true }, { k: 'bell', n: 1 }, { k: 'brazier', n: 1 }] },
  { look: 'shore', sector: 'field', key: 'fshore', name: 'The Boathouse Shore', description: 'A rowboat is drawn up among the reeds by an old willow; mist lies on the water, and a waterfall spills down the cliff.',
    features: [{ k: 'boat', n: 1 }, { k: 'reeds', n: 2 }, { k: 'tree', n: 1 }, { k: 'mist', n: 1 }, { k: 'waterfall', n: 1 }] },
  { look: 'cave', sector: 'inside', key: 'fgate', name: 'Before The Gates', description: 'The gate of Burzuk rises before you; fires burn in pits; icicles hang from the roof; roots crawl down the wall.',
    features: [{ k: 'gate', n: 1, main: true }, { k: 'flames', n: 2 }, { k: 'ice', n: 2 }, { k: 'roots', n: 1 }] },
  // places an old import typed 'city' that are no town (room_looks.py TOWNLESS): real rooms
  { look: "village", sector: 'city', key: "village", name: "The Palm Covered Path", description: "The sand is smooth here, swept clean by broom and by wind, and the palms stand in a tidy row on each side. Flags of bright cloth snap from poles, and a ring of whitewashed stones marks the approach to a large hut.",
    features: [{k: "pole", n: 2}, {k: "banner", n: 2}] },
  { look: "camp", sector: 'city', key: "camp", name: "The Firepit Before the Lodge", description: "A huge firepit smoulders in the middle of the clearing, ringed by blackened boulders and heaped with charred bones. Spits of green wood stand over the embers, still dripping fat.",
    features: [{k: "brazier", n: 2, main: true}, {k: "bones", n: 2}, {k: "ash", n: 2}] },
  { look: "garden", sector: 'city', key: "garden", name: "The Flower Garden", description: "Beds of roses, lilies and anemones spill across this corner in banks of crimson and gold. Petals carpet the paths, and the scent is almost too rich to breathe.",
    features: [{k: "flowers", n: 2, main: true}] },
  { look: "ruins", sector: 'city', key: "ruins", name: "Main Street", description: "This was once a magnificent street, but now is in total ruin. The streets are barren and windswept and the silence is unending.",
    features: [{k: "rubble", n: 1}] },
  { look: "terrace", sector: 'city', key: "olympus", name: "Crossing The Gods' Table", description: "The Gods' Table narrows here to a stately ribbon of marble, wide enough for six to walk abreast. Its surface is scored with the long-dried stains of spilled wine.",
    features: [{k: "throne", n: 1}, {k: "table", n: 2, main: true}] },
  // a set piece (world/setpieces.json): the Throne of Shadows as laid out by hand
  { look: 'inside', sector: 'inside', key: 'throneshadows', name: 'The Throne of Shadows', description: 'A black throne.', exits: { south: { to_room: 0 } },
    setpiece: { light: '#8a5cff' }, features: [{k: "throne", x: 12, y: 2, main: true, c: "black"}, {k: "pillar", x: 8, y: 3}, {k: "pillar", x: 16, y: 3}, {k: "pillar", x: 8, y: 9}, {k: "pillar", x: 16, y: 9}, {k: "crystal", x: 5, y: 5, c: "purple"}, {k: "crystal", x: 19, y: 5, c: "purple"}, {k: "crystal", x: 6, y: 11, c: "purple"}, {k: "crystal", x: 18, y: 11, c: "purple"}, {k: "banner", x: 9, y: 1}, {k: "banner", x: 15, y: 1}] },
  { look: 'hills', key: 'gatesouth', name: 'The Border Hills', description: 'The hills fall away to the south.', zoneExit: { side: 'south', zoneName: 'The Eastern Highlands' } },
];
export function buildLooksGallery(engine, kits) {
  const world = new World(engine, kits);
  // &only=web,cave: just those looks
  const only = typeof location !== 'undefined' && new URLSearchParams(location.search).get('only');
  const LOOK_SAMPLES = only ? ALL_LOOK_SAMPLES.filter(r => only.split(',').includes(r.key || r.look)) : ALL_LOOK_SAMPLES;
  const COLS = 4;
  const vnumAt = (cx, cy) => 991000 + cy * COLS + cx;
  const rooms = [];
  // every room's cell, known up front, so each fills the empty country beyond its edges; and
  // its neighbours opened onto as the game's open exits are (outdoor neighbours share a side)
  const cells = new Map(LOOK_SAMPLES.map((r, i) => [`${i % COLS},${Math.floor(i / COLS)}`, { ...r, data: { sector: r.look, name: r.name } }]));
  const look = (cx, cy) => (cells.get(`${cx},${cy}`) || {}).look;
  LOOK_SAMPLES.forEach((r, i) => {
    const cx = i % COLS, cy = Math.floor(i / COLS);
    const exits = {};
    const open = (tx, ty) => ({ to_room: vnumAt(tx, ty), kind: 'open', nlook: look(tx, ty) });
    if (cx > 0) exits.west = open(cx - 1, cy);
    if (cx < COLS - 1 && i + 1 < LOOK_SAMPLES.length) exits.east = open(cx + 1, cy);
    if (cy > 0) exits.north = open(cx, cy - 1);
    if (i + COLS < LOOK_SAMPLES.length) exits.south = open(cx, cy + 1);
    if (r.zoneExit) exits[r.zoneExit.side] = { to_room: 0, kind: 'zone', zoneName: r.zoneExit.zoneName, toName: r.zoneExit.zoneName };
    const built = world.addRoom({ ...r, vnum: vnumAt(cx, cy), exits }, cx, cy, cells);
    const c = world.centre(world.byVnum.get(vnumAt(cx, cy)));
    rooms.push({ look: r.look, theme: built.theme, x: c.x, z: c.z, name: r.name });
  });
  window.MH3D_gallery = { rooms, world };
  return new THREE.Vector3(rooms[0].x, 0, rooms[0].z);
}

const ALL_LOOK_SAMPLES = LOOK_SAMPLES;

// /play?demo&gallery=steeds: a knight on each kind of mount (steed.js), walking on the spot
export const STEED_SAMPLES = ['horse', 'warhorse', 'nightmare', 'griffin', 'clockwork_steed', 'moonstag', 'stoneboar', 'merchant_camel', 'shadowpanther', 'dire_warg'];
export async function buildSteedGallery(engine, kits) {
  const { mountRider } = await import('./steed.js');
  const world = new World(engine, kits);
  world.addRoom({ vnum: 992000, sector: 'field', name: 'The Paddock', description: 'Open grass.', exits: {} }, 0, 0);
  world.addRoom({ vnum: 992001, sector: 'field', name: 'The Paddock', description: 'Open grass.', exits: {} }, 1, 0);
  const riders = [];
  for (let i = 0; i < STEED_SAMPLES.length; i++) {
    const a = await spawnCharacter('knight');
    a.root.position.set(4 + (i % 5) * 4.4, 0, 4 + Math.floor(i / 5) * 6);
    a.root.rotation.y = 0.5;
    const riding = mountRider(a, STEED_SAMPLES[i], null);
    engine.scene.add(a.root);
    riders.push({ a, riding, key: STEED_SAMPLES[i] });
  }
  window.MH3D_gallery = { riders: riders.map(r => ({ key: r.key, x: r.a.root.position.x, z: r.a.root.position.z })), world };
  let tt = 0;
  engine.onTick(dt => { tt += dt; for (const r of riders) { r.a.play('Idle', 0.2); r.a.update(dt); r.riding.steed.update(dt, true, 1.4); r.riding.pose(tt, true); } world.update(dt, 0, engine.rig.target); });
  return new THREE.Vector3(12.8, 0, 7);
}
