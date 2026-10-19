// Which body each creature gets (world3d/looks.js), case by case and over every creature in
// the world (tools/qc_bestiary.mjs).   node --test tests/web/*.test.mjs
import { test } from 'node:test';
import assert from 'node:assert/strict';
import fs from 'node:fs';
import path from 'node:path';
import { fileURLToPath } from 'node:url';
import { creatureLook, subjectOf } from '../../src/web_isometric/world3d/looks.js';
import { loadMobs, suspects, lookLabel, drawnAs } from '../../tools/qc_bestiary.mjs';

const ART = path.join(path.dirname(fileURLToPath(import.meta.url)), '../../src/web_isometric/art3d');
const look = (short, o = {}) => creatureLook({ short, name: o.name || short.split(' ').pop(), ...o });
const body = l => l.beast ? (l.beast.mob || l.beast.proc || l.beast.prop[1]) : l.model;

test('the head noun decides: a blob is a slime, a giant hornet a hornet, a goat herder a person', () => {
  assert.equal(body(look('the green gelatinous blob', { name: 'green' })), 'slime');
  assert.equal(body(look('the giant hornet')), 'bee');
  assert.ok(look('the giant hornet').beast.h > 0.6, 'a giant hornet is bigger than a hornet');
  assert.ok(!look('the goat herder').beast, 'the goat herder is a person');
  assert.ok(!look('the vampire hunter').beast && !/skeleton/.test(look('the vampire hunter').model), 'hunts vampires, is not one');
  assert.equal(body(look('a goblin mushroom farmer')), 'goblin_m');
  assert.equal(body(look('King of the Goblins', { name: 'king' })), 'goblin_m');
  assert.equal(body(look('a goblin woman')), 'goblin_f', 'a goblin woman has her own body');
  assert.equal(body(look('a goblin scout', { sex: 'female' })), 'goblin_f');
  assert.ok(look('a goblin scout').beast.prefer, 'the pack goblin, not one built in code');
  assert.equal(body(look('a green slime')), 'q_slime');
  assert.equal(body(look('a grey ooze')), 'slime', 'a colour the pack slime cannot wear: the slime built in code');
  assert.equal(body(look('the Spider Queen')), 'spider');
  assert.equal(body(look('the fire elemental')), 'ghost');
  assert.equal(body(look('the giant lizard')), 'lizard');
  assert.ok(look('the giant lizard').beast.h > 1, 'the giant lizard entry, not a garden lizard');
});

test('things that are not animals: props, constructs, statues', () => {
  assert.deepEqual(look('the mimic').beast.prop, ['dungeon', 'chest']);
  assert.ok(look('the dancing sword').beast.prop && look('the dancing sword').beast.fly > 0);
  const golem = look('the bronze golem');
  assert.equal(golem.model, 'knight');
  assert.ok(!golem.loadout.some(i => /Sword|Axe|Staff|Knife|Crossbow/.test(i)), 'golems carry no weapons');
  assert.equal(golem.tint, 0xb08850, 'bronze');
  assert.equal(golem.flat, true, 'bronze all over, not a tinted costume');
  assert.equal(look('the statue of Indra', { name: 'statue' }).still, true);
  assert.equal(look('the Black Rook', { name: 'black' }).tint, 0x45454d);
  assert.equal(look('a possessed suit of armor', { name: 'armor' }).model, 'knight');
});

test('people are dressed for their trade, the same way every time', () => {
  assert.deepEqual(look('the baker', { shopkeeper: true }).loadout, [], 'no baker with an axe');
  assert.ok(look('the cityguard').loadout.includes('1H_Sword'));
  assert.equal(look("the mages' guildmaster", { trainer: true }).model, 'mage');
  assert.equal(look('an orc shaman').model, 'mage');
  assert.ok(look('an orc shaman').tint !== undefined, 'green skin');
  const a = creatureLook({ short: 'a villager', name: 'villager', pv: 3040 });
  const b = creatureLook({ short: 'a villager', name: 'villager', pv: 3040, id: 99 });
  assert.deepEqual(a, b, 'stable per creature type, whatever its id');
});

test('the dead: dressed by what they were', () => {
  assert.equal(look('a skeletal warrior').model, 'skeleton_warrior');
  assert.equal(look('an ancient lich').model, 'skeleton_mage');
  assert.equal(body(look('a rotting zombie')), 'zombie_m', 'a zombie in its own rotting flesh');
  assert.equal(body(look('a zombie bride')), 'zombie_f');
  assert.ok(look('a rotting zombie').beast.prefer);
  assert.equal(look('a skeletal zombie').model, 'skeleton_minion', 'bones are bones');
  assert.equal(look('a vampire spawn').model, 'rogue_hooded');
  assert.equal(look('the undead giant').beast.tint, 0x9ab08a, 'an undead giant is a rotten giant');
});

test('adjectives size and colour the body', () => {
  assert.ok(look('the baby dragon').beast.h < look('the red dragon').beast.h * 0.6);
  assert.equal(look('the red dragon').beast.tint, 0xc84030);
  assert.ok(look('the massive Minotaur').beast.h < 4, 'a massive minotaur still fits through a door');
  assert.equal(look('the large, grey wolf', { name: 'wolf' }).beast.tint, 0x9a9aa0);
  assert.ok(look('the large, grey wolf', { name: 'wolf' }).beast.h > 1, 'large');
});

test('a person whose room line names a creature takes that body', () => {
  assert.deepEqual(subjectOf('A massive rat-man standing here.'), ['massive', 'rat-man']);
  assert.deepEqual(subjectOf('A shifty-looking smuggler eyes you suspiciously.'), ['shifty-looking', 'smuggler']);
  assert.equal(body(look('the Sewer King', { name: 'sewer king', long: 'A massive rat-man standing here.' })), 'rat');
  assert.equal(look('the Ancient Guardian', { name: 'guardian', long: 'A towering stone golem stands watch, runes glowing.' }).model, 'knight');
  assert.ok(!look('a shifty smuggler', { long: 'A shifty-looking smuggler eyes you suspiciously.' }).beast);
});

// every model, weapon and prop a look names must exist in the art
function glbJson(file) {
  const b = fs.readFileSync(file);
  return JSON.parse(b.slice(20, 20 + b.readUInt32LE(12)).toString());
}

test('every creature in the world gets a body that exists, and no creature is drawn as a person', { skip: !fs.existsSync(path.join(ART, 'mobs/index.json')) }, () => {
  const mobs = loadMobs();
  assert.ok(mobs.length > 800, `${mobs.length} creatures`);
  const bad = suspects(mobs);
  assert.deepEqual(bad.map(({ m, look }) => `${m.pv} ${m.short} -> ${lookLabel(look)}`), []);
  const mobModels = new Set(Object.keys(JSON.parse(fs.readFileSync(path.join(ART, 'mobs/index.json'), 'utf8'))));
  const bodyFile = path.join(ART, 'bodies/index.json');
  const bodies = new Set(fs.existsSync(bodyFile) ? Object.keys(JSON.parse(fs.readFileSync(bodyFile, 'utf8'))) : []);
  const accessories = {}, kitModels = {};
  const accOf = model => accessories[model] || (accessories[model] = new Set(glbJson(path.join(ART, `chars/${model}.glb`)).nodes
    .filter(n => n.mesh != null && n.skin == null).map(n => n.name)));
  const kitOf = kit => kitModels[kit] || (kitModels[kit] = new Set((j => j.scenes[0].nodes.map(i => j.nodes[i].name))(glbJson(path.join(ART, `kits/${kit}.glb`)))));
  const procs = new Set(['rat', 'spider', 'snake', 'lizard', 'rabbit', 'slime']);
  for (const m of mobs) {
    const l = creatureLook(m), where = `${m.pv} ${m.short}`;
    if (l.beast) {
      const b = l.beast;
      assert.ok(b.h > 0.1 && b.h < 6, `${where}: height ${b.h}`);
      if (b.body) assert.ok(bodies.has(b.body), `${where}: no Blender body ${b.body} (art3d/bodies)`);
      if (b.mob) assert.ok(mobModels.has(b.mob), `${where}: no creature model ${b.mob}`);
      else if (b.proc) assert.ok(procs.has(b.proc), `${where}: no body ${b.proc}`);
      else assert.ok(kitOf(b.prop[0]).has(b.prop[1]), `${where}: no prop ${b.prop}`);
    } else {
      assert.ok(fs.existsSync(path.join(ART, `chars/${l.model}.glb`)), `${where}: no character ${l.model}`);
      for (const item of l.loadout || []) {
        // a list may name the gear of several models ("Knight_Cape" or "Mage_Cape"): one must fit
        if (!accOf(l.model).has(item)) assert.ok(['Knight_Cape', 'Mage_Cape', 'Knife', '1H_Axe', 'Barbarian_Round_Shield'].includes(item), `${where}: ${l.model} has no ${item}`);
      }
      assert.ok(!l.scale || (l.scale > 0.3 && l.scale < 3), `${where}: scale ${l.scale}`);
    }
  }
});

test('the build-out creatures get fitting bodies: seals, clams, gnolls, badgers', () => {
  assert.equal(body(look('a grey seal')), 'whale');
  assert.ok(look('a grey seal').beast.h < 2, 'a seal is a small whale, not a leviathan');
  assert.ok(!look('a seal hunter').beast, 'the seal hunter is a person');
  assert.equal(body(look('a giant clam')), 'slime', 'a giant clam is a shell, not a giant');
  assert.equal(body(look('a grizzled badger')), 'farm_pig');
  const g = look('a gnoll raider', { name: 'gnoll raider' });
  assert.ok(!g.beast && g.tint === 0xb0905a, 'a gnoll is hyena-hued folk');
});

test('the creature kit gives every kind of creature in the world a body of its own', async () => {
  const { kinSignature } = await import('../../src/web_isometric/world3d/kinrecipe.js');
  const seen = new Map(), dups = [];
  let kin = 0;
  for (const m of loadMobs()) {
    const l = creatureLook(m);
    if (!l.beast || !l.beast.kin) continue;
    kin++;
    const s = kinSignature(l.beast.kin);
    if (seen.has(s) && seen.get(s) !== m.short) dups.push(`${seen.get(s)} = ${m.short}`);
    else seen.set(s, m.short);
    assert.ok(['quad', 'bird', 'fish'].includes(l.beast.kin.plan) || l.beast.kin.plan, `${m.short} has a plan`);
  }
  assert.ok(kin >= 380, `nearly every non-person creature is on a kit body (${kin})`);
  assert.deepEqual(dups, [], 'no two kinds of creature share a body');
});

test('a creature keeps its words: colour, antlers, tusks, a seal on flippers', async () => {
  const k = s => creatureLook({ short: s, name: s.split(' ').pop(), pv: 7 }).beast.kin;
  assert.equal(k('a white stag').horns, 'antlers');
  assert.equal(k('a bristly wild boar').horns, 'tusks');
  assert.equal(k('a black dire wolf').c.main >> 16 < 0x50, true, 'black is dark');
  assert.equal(k('a grey seal').tail, 'flippers');
  assert.equal(k('a giant raven').plan, 'bird');
  assert.ok(k('a giant raven').c.main >> 16 < 0x40, 'a raven is black without saying so');
});

test('the newer skeletons follow the words too: ogres, minotaurs, scorpions, cobras, hydras, wyverns, elementals, frogs', () => {
  const k = s => creatureLook({ short: s, name: s.split(' ').pop(), pv: 11 }).beast.kin;
  assert.equal(k('a wandering ogre').eyes, 2);
  assert.equal(k('a cyclops').eyes, 1);
  assert.equal(k('the minotaur').head, 'bull');
  assert.equal(k('a black scorpion').kind, 'scorpion');
  assert.equal(k('a spitting cobra').head, 'hood');
  assert.equal(k('a swamp hydra').heads, 3);
  assert.equal(k('a rock wyvern').legs, 2);
  assert.equal(k('a fire elemental').form, 'flame');
  assert.equal(k('a giant river frog').form, 'frog');
});

// what JEV caught (docs/JEV_REVIEW_CREATURES.md): each a creature drawn as something its words are not
test('the JEV review: orcs of the Skull Clan, ghouls, the Rat King and the rest drawn as they are', () => {
  const drawn = (short, name = short, long = '') => drawnAs(creatureLook({ short, name, long }));
  assert.match(drawn('a Skull Clan orc', 'orc grunt warrior skull clan'), /^person:/, 'the Skull Clan are orcs, not floating skulls');
  assert.equal(drawn('a flameskull'), 'skull', 'a flameskull is still a skull');
  assert.match(drawn('the mutant orc', 'orc'), /^person:/, 'a mutant orc is an orc');
  assert.match(drawn('a Banner-Reaver war-chief'), /^person:/, 'a reaver is a raider');
  assert.equal(drawn('a spine reaver'), 'spider', 'but a spine reaver skitters');
  assert.equal(drawn('a hungry ghoul', 'ghoul'), 'zombie_m', 'ghouls are the walking dead in their flesh');
  assert.equal(drawn('the Rat King', 'rat king'), 'rat_king');
  assert.equal(drawn('a cliff roc'), 'roc');
  assert.equal(drawn('the baby dragon', 'dragon'), 'q_dragon');
  assert.equal(drawn('a lizard hatchling'), 'lizard');
  assert.equal(drawn('Grushka the Bone-Caller', 'grushka shaman ogre bone caller'), 'ogre', 'bone alone does not make an ogre undead');
  assert.match(drawn('a bone colossus', 'colossus bone giant'), /^undead:/, 'a giant built of skeletons is still the dead');
  assert.match(drawn('a sworn blade'), /^person:/, 'a sworn blade is a warrior');
});

