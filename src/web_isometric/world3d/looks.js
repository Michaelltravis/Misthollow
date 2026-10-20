// Which 3D body a creature or NPC gets. Pure (no THREE): tests/web run it over every creature
// in the world (tools/qc_bestiary.mjs).
//
// The server sends a creature's keywords (`name`, often one word: "green"), what it is
// (`short`: "the green gelatinous blob"), the start of its room line (`long`: "A massive
// rat-man standing here."), its flags, its role (shopkeeper, trainer) and its type number
// (`pv`). What the short description ends with decides:
//   - a two-word creature ("the fire elemental", "the giant lizard", "a lizard man");
//   - a trade or role word: a person ("the goat herder", "the vampire hunter"), unless a race
//     stands beside it ("a goblin mushroom farmer", "King of the Goblins") or a creature
//     rules ("the spider queen", "the rat king");
//   - the creature it names ("the giant hornet" is a hornet, not a giant);
// then undead, then any creature word, then a person dressed for the role. A person whose room
// line says otherwise takes that ("the Sewer King" is "a massive rat-man"). Adjectives in front
// size and colour the body; the type number picks a stable variation.
//
// A look is one of:
//   {beast: {mob|proc|prop, h, tint, fly}, why}          a creature model, procedural body or kit prop
//   {model, tint, scale, loadout, still, flat, fly, why}  a KayKit adventurer or skeleton (flat: one
//                                                         colour all over, stone or metal)
// `why` says which rule chose it (for tools/qc_bestiary.mjs).
import { kinRecipe } from './kinrecipe.js';
import { BESTIARY } from './bestiary.js';

// words that only ever name people
const PEOPLE = new Set(('man men woman women boy girl child children kid kids baby lad lass maiden maid wife husband '
  + 'mother father son daughter widow bride uncle aunt grandmother grandfather sister brother monk nun '
  + 'herder shepherd farmer farmhand keeper innkeeper shopkeeper storekeeper merchant trader vendor peddler clerk baker '
  + 'butcher smith blacksmith weaponsmith armorer armourer tailor jeweler grocer brewer bartender barkeep barmaid '
  + 'waiter waitress cook chef servant butler steward squire page herald crier scribe librarian teacher student scholar '
  + 'apprentice fisherman trapper woodsman lumberjack miner pilgrim hermit beggar vagrant drunk drunkard mayor sheriff '
  + 'judge adjudicator jester bard minstrel dancer gladiator adventurer explorer citizen townsman townswoman villager '
  + 'peasant serf orphan urchin elf elves dwarf dwarves gnome gnomes halfling hobbit human humans drow duergar maker '
  + 'receptionist secretary nobleman noblewoman noble duke duchess baron baroness count countess emperor empress '
  + 'prince princess cartographer navigator alchemist apothecary herbalist healer stablehand groom ferryman jailer '
  + 'executioner torturer gatekeeper doorman courier messenger tourist sailor pirate tomb robber thief rogue '
  + 'assassin cutpurse pickpocket bandit brigand thug ruffian raider mercenary nomad hunter huntress ranger henchman '
  + 'slayer killer catcher tamer handler rider breeder charmer whisperer wrangler poacher slaver trainer instructor '
  + 'worshipper worshiper follower disciple').split(/\s+/));
// a trade whose word in front is what it works on, not what it is ("the vampire hunter")
const AGENTS = new Set(('herder shepherd keeper hunter huntress slayer killer catcher trapper tamer handler rider breeder '
  + 'charmer whisperer wrangler maker poacher slaver trainer worshipper worshiper follower').split(/\s+/));
// role words a creature race can carry ("the goblin shaman", "the orc chief")
const TITLES = new Set(('king queen lord lady chief chieftain leader master mistress matron elder shaman priest priestess '
  + 'warrior guard guardian champion scout captain general commander soldier mage wizard witch warlock sorcerer '
  + 'sorceress cultist slave prisoner servant hunter knight paladin cleric monk acolyte druid sage spy agent warden '
  + 'sentry watchman lieutenant sergeant recruit veteran novice initiate zealot templar inquisitor herald').split(/\s+/));
// the race words a role word defers to
const RACES = /\b(goblins?|hobgoblins?|kobolds?|orcs?|half-orcs?|gnolls?|bugbears?|trolls?|ogres?|giants?|skeleton|skeletal|zombies?|ghouls?|undead|vampires?|spectral|ghostly|ghosts?|demons?|imps?|minotaurs?|sahuagin|myconoids?|myconids?)\b/;
const UNDEAD = /\b(skeleton|skeletons|skeletal|zombie|zombies|ghoul|ghouls|ghast|undead|lich|wight|bone|bones|corpse|mummy|mummies|revenant|vampire|vampires|deathknight|death knight|drowned|risen|ossuary|ribcage|charnel|draugr|undying|dead performers?)\b/;
// "bone" alone is no proof of the dead when the words name a living kind: Grushka the
// Bone-Caller is an ogre shaman, Bone Gnasher a troll, a bone-hung shaman an orc
const LIVING = /\b(ogres?|trolls?|orcs?|goblins?|hobgoblins?|gnolls?|kobolds?|humans?|dwarf|dwarves|elf|elves|barbarians?)\b/;
function deadWords(text) {
  const hits = String(text).match(new RegExp(UNDEAD.source, 'g'));
  if (!hits) return false;
  return !(hits.every(w => /^bones?$/.test(w)) && LIVING.test(text));
}
// an undead creature that is not a person keeps its body, rotten or bare to the bone
const ROTTEN = /\b(undead|zombie|zombies|zombified|rotting|rotten|drowned|ghoul|plague)\b/;
const BONY = /\b(skeleton|skeletal|bone|bones)\b/;
const ORCISH = /\b(orc|orcs|half-orc|hobgoblin|bugbear|gnoll|gnolls|ogrillon)\b/;
// people of other kinds: their skin, whatever their trade
const RACE_TINT = [[/\b(drow|dark elf|dark elves)\b/, 0x9a90b8], [/\bduergar\b/, 0x9a9aa0], [/\bsahuagin\b/, 0x6aa8a0],
  [/\bdragon-kin\b/, 0xc89070], [/\b(svirfneblin|deep gnome)\b/, 0xa0a0a8]];
const MATERIAL = [[/diamond|crystal/, 0xcde8ff], [/obsidian/, 0x3a3440], [/glass/, 0x5a5a78], [/adamantite|adamant/, 0x6a7a9a],
  [/bronze|brass|copper/, 0xb08850], [/iron|steel|steam|clockwork|metal|armou?r/, 0x8a909a], [/wood|wooden|oak/, 0x8a6a44],
  [/clay|mud/, 0xb08060], [/flesh/, 0xc89a8a], [/cloth|straw|rag/, 0xc8b89a], [/granite/, 0x8a8a8a], [/marble/, 0xe8e4dc],
  [/bone/, 0xe0d8c0], [/ice|frost/, 0x9fd8ff], [/furnace|forge|magma|ember|cinder/, 0xc86a3a],
  [/\bblack\b/, 0x45454d], [/\bwhite\b/, 0xf2f2f2]];
// colour words in front of a creature: "the red dragon", "a black bear", "the gray ooze"
const COLOUR = [[/\b(black|ebony)\b/, 0x3a3a42], [/\b(white|snowy|ivory|albino)\b/, 0xf4f4f4], [/\b(grey|gray|ashen)\b/, 0x9a9aa0],
  [/\b(brown|tawny)\b/, 0x8a6040], [/\b(red|crimson|scarlet)\b/, 0xc84030], [/\b(green|emerald|jade)\b/, 0x5aa04a],
  [/\b(blue|azure|sapphire)\b/, 0x4a70c8], [/\b(gold|golden|yellow)\b/, 0xe8c040], [/\b(silver|silvery)\b/, 0xc8ccd8],
  [/\b(bronze|brass|copper)\b/, 0xb08850], [/\b(purple|violet)\b/, 0x8a5ab0],
  [/\b(fire|fiery|flame|flaming|magma|lava|volcanic|ember|cinder|slag|molten|burning|blazing)\b/, 0xe0603a],
  [/\b(frost|ice|icy|frozen|snow)\b/, 0x9fd8ff]];
const SMALL = /\b(tiny|little|small|young|baby|juvenile|lesser|petite|miniature|wee|hatchling)\b/;
const BIG = /\b(large|big|huge|great|giant|greater|grown|elder|dire|towering|hulking|ancient)\b/;
const HUGE = /\b(massive|enormous|gigantic|colossal|monstrous|titanic|immense|mighty)\b/;
const RULER = /\b(king|queen|matriarch|patriarch|broodmother|alpha|chieftain|lord)\b/;

export function hashStr(s) { let h = 2166136261; for (const ch of String(s)) h = Math.imul(h ^ ch.charCodeAt(0), 16777619); return h >>> 0; }

const ARTICLES = new Set(['a', 'an', 'the', 'some', 'two', 'three', 'pair']);
const clean = s => String(s || '').toLowerCase().replace(/[‐-―]/g, '-');
const wordsOf = s => s.replace(/[^a-z\- ']/g, ' ').split(/\s+/).map(w => w.replace(/^'+|'+$/g, '')).filter(w => w && !ARTICLES.has(w));

// what to read: the short description, unless it is a whole sentence ("A giant spider lurks in
// the shadows.") — then the keywords, which are its short name there. "Scarface, the bandit
// leader" is read from the part after the comma.
export function describe(m) {
  const short = String(m.short || '').trim();
  const name = String(m.kw || m.name || '').trim();     // kw: the keywords, when the server names it by description
  const sentence = /[.!]$/.test(short) || short.split(/\s+/).length > 7;
  let text = clean(sentence || !short ? name : short);
  const appos = text.match(/^[^,]+,\s+(?:the|a|an)\s+(.+)$/);
  if (appos) text = appos[1];
  const phrase = text.split(/\s+(?:of|with|who|that|from|in|on|wearing|carrying|holding|riding)\s+|\(/)[0];
  const words = wordsOf(phrase);
  return { head: words[words.length - 1] || '', words, all: `${text} ${name.toLowerCase()}${sentence ? '' : ` ${short.toLowerCase()}`}` };
}

// the subject of a room line: "A massive rat-man standing here." -> massive rat-man
const VERB = /^(is|are|was|stands?|standing|sits?|sitting|lies|lying|here|there|lurks?|lurking|waits?|waiting|watches|watching|hovers?|glides?|crawls?|walks?|wanders?|prowls?|stalks?|slithers?|floats?|scurries|skitters|rises?|bars|guards?|has|looks?|moves?|roams?|flutters?|dances?|grazes?|towers?|drifts?|circles?|shambles?|clatters?|sings?|chants?|slides?|tends?|snarls?|hisses?|growls?|lumbers?|sleeps?|rests?|works?|sweeps?|stares?|peers?|patrols?|paces?|leans?|kneels?|hides?|lounges?|appears?|seems?|smiles?|grins?|eyes|eyeing|screams?|attacks?|roars?|shrieks?|howls?|flickers?|buzzes|buzzing|sniffs?|gnaws?|writhes?|squats?|bares?|blocks?|ignores?|notices?|studies|scans?|glares?|glowers?|mutters?|muttering|whispers?|laughs?|cackles?|wails?|weeps?|cries|begs?|offers?|sells?|polishes?|sharpens?|counts?|reads?|writes?|cleans?|cooks?|serves?|waves?|nods?|bows?|flies|swims?|hops?|crouches?|coils?|squeaks?|barks?|purrs?|chirps?|croaks?|bleats?|moos?|clucks?|neighs?|splashes?|burrows?|digs?|gathers?|collects?|carries?|holds?|wields?|brandishes?|shuffles?|scuttles?|scuttling|darts?|swoops?|perches?|perched)$/;
export function subjectOf(long) {
  const t = clean(long).split(/[,.!;:(]|\s+(?:of|with|who|that|from|in|on|wearing|carrying|holding|riding|and)\s+/)[0];
  const out = [];
  for (const w of wordsOf(t)) {
    if (VERB.test(w)) break;
    out.push(w);
    if (out.length >= 4) break;
  }
  return out;
}

function beast(text) {
  if (!text) return null;
  for (const [re, look] of BESTIARY) if (re.test(text)) return look;
  return null;
}

// adjectives in front of the creature word: "the giant hornet", "a tiny spider", "the baby
// dragon". Small creatures grow more and big ones less: a giant rat is dog-sized, a massive
// minotaur still fits through a door, a baby dragon is not a full dragon.
export function sizeOf(mods, h = 1) {
  let k = HUGE.test(mods) ? 1.7 : BIG.test(mods) || RULER.test(mods) ? 1.3 : 1;
  if (k > 1) k = h < 0.75 ? 1 + (k - 1) * 2 : h >= 2 ? 1 + (k - 1) * 0.5 : k;
  if (SMALL.test(mods)) k *= h >= 2 && /\b(baby|young|hatchling|juvenile)\b/.test(mods) ? 0.45 : 0.72;
  return k;
}

// a bestiary look with size, colour and boss adjustments applied
function creature(look, mods, all, boss, why) {
  if (look.person) {
    const tint = look.material ? (MATERIAL.find(([re]) => re.test(all)) || [0, 0x9a9590])[1] : look.tint;
    const scale = (look.scale || 1) * sizeOf(mods) * (boss ? 1.25 : 1);
    return { model: look.person, loadout: look.loadout || [], tint, scale: scale !== 1 ? +scale.toFixed(2) : undefined,
      still: !!look.still, flat: !!look.flat, fly: look.fly || 0, why: 'bestiary' };
  }
  const b = { ...look, h: +(look.h * sizeOf(mods, look.h) * (boss ? 1.35 : 1)).toFixed(2) };
  const colour = COLOUR.find(([re]) => re.test(mods));
  if (colour) b.tint = colour[1];
  if (BONY.test(mods)) b.tint = 0xe0d8c0;
  else if (ROTTEN.test(mods)) b.tint = 0x9ab08a;
  return { beast: b, why };
}

// people: a KayKit adventurer dressed for the role, stable per creature type
function person(m, all, why = 'person') {
  const h = hashStr(m.pv != null ? `pv${m.pv}` : all);
  const pick = list => list[h % list.length];
  const has = re => re.test(all);
  const warm = [0xe8e0d0, 0xd0c8b8, 0xc8d0d8, 0xe0d0c0, 0xd8c8b0];
  let scale = has(/\b(child|children|kid|baby|urchin|orphan|boy|girl)\b/) ? 0.62
    : has(/\b(gnome|gnomes|halfling|hobbit|brownie|svirfneblin)\b/) ? 0.66
      : has(/\b(dwarf|dwarves|dwarven|duergar)\b/) ? 0.82 : 1;
  if (m.boss || (m.flags || []).includes('boss')) scale *= 1.25;
  const orc = ORCISH.test(all);
  const skin = orc ? pick([0x8fb07a, 0x9aa070, 0x7a9a6a]) : (RACE_TINT.find(([re]) => re.test(all)) || [])[1];
  const out = (model, loadout, tint) => ({ model, loadout, tint: skin || tint, scale: scale !== 1 ? +scale.toFixed(2) : undefined, why });
  // a priestess who keeps a door (Lloth's temple warden) is robed, not a knight
  if (has(/\b(priests?|priestess|clerics?|monk|nun|acolyte|bishop|abbot|vicar|druids?|shaman|sage|hermit|healer|oracle|seer|prophet|cantor|confessor|astrologer)\b/))
    return out('mage', ['Spellbook', 'Mage_Cape'], pick([0xf4ecd8, 0xe8e0f0, 0xd8e8d0]));
  if (has(/\b(guards?|guardsman|bodyguard|lifeguard|guildguard|gateguard|soldiers?|sentry|watchman|watch|warden|cityguard|captain|sergeant|lieutenant|militia|patrol|peacekeeper|marshal|bailiff|jailor|jailer)\b/))
    return out('knight', ['1H_Sword', 'Round_Shield', 'Knight_Helmet'], 0xc8d0e0);
  if (has(/\b(knights?|paladins?|templars?|crusaders?|champion)\b/)) return out('knight', ['1H_Sword', 'Badge_Shield', 'Knight_Helmet', 'Knight_Cape'], 0xe0e4f0);
  if (has(/\b(chief|chieftain|warlord|warchief)\b/)) return out('barbarian', ['2H_Axe', 'Barbarian_Hat', 'Barbarian_Cape'], pick(warm));
  if (has(/\b(king|queen|prince|princess|lord|lady|duke|duchess|baron|baroness|count|countess|noble|nobleman|noblewoman|emperor|empress|mayor|matron|sovereign|regent|monarch|tyrant|overlord|sultan|pharaoh|pharoah|senator|governor)\b/))
    return out(pick(['knight', 'mage']), ['Knight_Cape', 'Mage_Cape'], pick([0xf0d890, 0xd8b8e8, 0xf0e0c0]));
  if (has(/\b(mages?|wizards?|witch|warlocks?|sorcerers?|sorceress|necromancers?|conjurer|enchanter|enchantress|illusionist|magus|summoner|spellbinder|arcanist|magic user)\b/))
    return out('mage', ['2H_Staff', 'Mage_Hat', 'Mage_Cape'], pick([0xffffff, 0xd8c8f0, 0xc8e0d0]));
  if (has(/\b(librarian|scribe|scholar|teacher|student|apprentice|cartographer|navigator|alchemist|apothecary|herbalist|secretary|clerk|curator)\b/))
    return out('mage', ['Spellbook_open'], pick(warm));
  if (has(/\b(innkeeper|bartender|barkeep|barmaid|waiter|waitress|brewer|tavern)\b/)) return out('barbarian', ['Mug'], pick(warm));
  if (has(/\b(smith|blacksmith|weaponsmith|armorer|armourer|miner|mineworker|lumberjack|woodsman|foreman|dockworker|shipwright|carpenter)\b/)) return out('barbarian', ['1H_Axe'], pick(warm));
  if (has(/\b(thief|thieves|rogues?|assassins?|cutpurse|pickpocket|spy|agent|robber|smuggler)\b/)) return out('rogue_hooded', ['Knife', 'Knife_Offhand'], pick([0x9a9aa8, 0x8a8a9a, 0xa8a0a0]));
  if (has(/\b(rangers?|hunter|huntress|trapper|scout|archer|bowman|poacher)\b/)) return out('rogue_hooded', ['1H_Crossbow', 'Rogue_Cape'], pick([0xb8d8a8, 0xc8c8a0]));
  if (has(/\b(bandit|brigand|thug|ruffian|raider|marauder|pirate|mercenary|cultist|zealot|henchman|slaver|murderer)\b/))
    return out(pick(['rogue', 'barbarian']), pick([['Knife', 'Rogue_Cape'], ['1H_Axe']]), pick([0xb89a8a, 0x9a8a7a, 0x8a7a9a]));
  if (has(/\b(warriors?|fighters?|gladiator|barbarian|berserker|veteran|recruit|weaponsmaster|swordsman|slayer|mauler)\b/)) return out('barbarian', ['2H_Axe', 'Barbarian_Cape'], pick(warm));
  if (has(/\b(jester|bards?|minstrel|dancer|performer|juggler)\b/)) return out('rogue', ['Rogue_Cape'], pick([0xe0b8e0, 0xb8d8f0, 0xf0d8a0]));
  if (m.shopkeeper || has(/\b(shopkeeper|storekeeper|merchant|trader|vendor|peddler|grocer|baker|butcher|tailor|jeweler|cook|chef)\b/))
    return out(pick(['rogue', 'mage']), [], pick(warm));
  if (m.trainer || has(/\bguildmaster|guild master|trainer|instructor\b/)) return out('knight', ['1H_Sword', 'Knight_Cape'], 0xf8f0e0);
  // anyone else: orcs and hostile strangers carry a weapon, townsfolk do not
  if (orc) return out(pick(['barbarian', 'barbarian', 'rogue_hooded']), ['1H_Axe', 'Barbarian_Round_Shield', 'Knife'], 0);
  if (m.hostile || (m.flags || []).includes('aggressive')) return out(pick(['rogue_hooded', 'barbarian', 'rogue']), pick([['Knife'], ['1H_Axe'], ['Knife', 'Knife_Offhand']]), pick(warm));
  return out(pick(['rogue', 'rogue', 'mage', 'barbarian']), [], pick(warm));
}

// the walking dead: a skeleton dressed by what it was
function undead(m, all) {
  const h = hashStr(m.pv != null ? `pv${m.pv}` : all);
  const big = /\b(giant|juggernaut|harvester|behemoth|colossus|colossi)\b/.test(all) ? 1.6 : 1;
  const scale = ((m.boss || (m.flags || []).includes('boss')) ? 1.25 : 1) * big;
  const s = scale !== 1 ? scale : undefined, why = 'undead';
  if (/\b(vampire|vampires)\b/.test(all)) return { model: 'rogue_hooded', loadout: ['Knife'], tint: 0x8a6a8a, scale: s, why };
  // the walking dead in their own flesh (the Quaternius zombies), ghouls with them; a woman's
  // body for a woman
  if (/\b(zombies?|zombified|ghouls?|ghasts?|restless dead|risen)\b/.test(all) && !/\b(skeleton|skeletal|bones?)\b/.test(all)) {
    const she = m.sex === 'female' || /\b(woman|women|girl|maiden|bride|widow|she)\b/.test(all);
    return { beast: { mob: she ? 'zombie_f' : 'zombie_m', h: +(2.1 * scale).toFixed(2), prefer: true }, why };
  }
  const tint = /\bdrowned\b/.test(all) ? 0x8ab0a8 : /\b(mummy|mummies)\b/.test(all) ? 0xd8c8a0
    : /\b(zombies?|ghouls?|ghast|revenant|corpse|rotting)\b/.test(all) ? 0x9ab08a : /\blich\b/.test(all) ? 0xc8b8e8 : undefined;
  const model = /\b(lich|necromancer|mage|priests?|priestess|vicar|cantor|choir|sorcerer|wizard|shaman|witch|warlock|cleric|acolyte|sovereign|king|queen|herald|sanctifier)\b/.test(all) ? 'skeleton_mage'
    : /\b(warrior|guard|guardian|knight|soldier|champion|sentinel|juggernaut|harvester|colossus|captain|mummy|mummies)\b/.test(all) ? 'skeleton_warrior'
      : /\b(archer|rogue|thief|scout|assassin|hunter|collector|thrall)\b/.test(all) ? 'skeleton_rogue'
        : /\b(zombies?|ghouls?|ghast|revenant|corpse)\b/.test(all) ? 'skeleton_minion'
          : ['skeleton_warrior', 'skeleton_rogue', 'skeleton_minion'][h % 3];
  return { model, tint, scale: s, why };
}

// "a ghostly mermaid" is a ghost; "the spectral wolf" a pale wolf
const GHOSTLY = /\b(ghostly|spectral|phantom|phantasmal)\b/;

export function creatureLook(m) {
  let look = lookOf(m);
  // a female of a kind with its own female model (goblins)
  const b = look.beast;
  if (b && b.alt && (m.sex === 'female' || /\b(woman|women|girl|wife|mother|maiden|queen|matron|crone|she)\b/.test(`${m.short || ''} ${m.kw || m.name || ''}`.toLowerCase())))
    look = { ...look, beast: { ...b, mob: b.alt } };
  // a colour the model can't wear: the body that can
  const c = look.beast;
  const said = `${m.short || ''} ${m.kw || m.name || ''}`.toLowerCase();
  if (c && c.orTinted && c.tint != null) {
    if (c.own && new RegExp(`\\b${c.own}\\b`).test(said)) look = { ...look, beast: { ...c, tint: undefined } };   // already that colour
    else {
      const { mob, prefer, orTinted, own, ...rest } = c;
      look = { ...look, beast: { ...rest, ...orTinted } };
    }
  }
  return withKin(look, m);
}

// a creature body the kit builds gets its own recipe (kinrecipe.js): from all its words, and
// seeded by its prototype so every kind of creature keeps one body of its own
function withKin(look, m) {
  const b = look.beast;
  if (!b || b.prop) return look;
  const body = b.mob || (b.proc ? `proc:${b.proc}` : null);
  const d = describe(m);
  const all = `${d.all} ${String(m.long || '').toLowerCase()}`;
  const kin = body ? kinRecipe(body, all, m.pv != null ? +m.pv : hashStr(d.all), b.tint != null ? b.tint : null) : null;
  return kin ? { ...look, beast: { ...b, kin } } : look;
}

// creatures whose words no safe rule reads right, by prototype: what they are
const BY_PROTO = {
  2500: 'ghost',     // the shadow guardian: a shade that screams a challenge
  9712: 'ghost',     // the Echo of the Archmage, pacing out her last spell
  9775: 'ghost',     // a silent echo, the shape of a sound
  23802: 'ghost',    // a wailing monk drifting through the refectory
  48204: 'ghost',    // the weeping maid (her keywords say ghost)
  642905: 'ghost',   // Elder Verun, Keeper of Trials (his keywords say ghost)
  648002: 'zombie',  // a hollow-eyed farmhand shambling between the rows (a ghoul)
  650106: 'troll',   // Karrak, the stone troll of the deep shaft
  47904: 'beetle',   // the undead riding beetle: a dead beetle, not a skeleton
};

function lookOf(m) {
  const d = describe(m);
  const by = m.pv != null ? BY_PROTO[+m.pv] : null;
  if (by === 'zombie') return undead(m, `zombie ${d.all}`);
  if (by === 'ghost') return creature(beast('ghost'), '', d.all, !!m.boss, 'by prototype');
  if (by) return creature(beast(by), '', d.all, !!m.boss, 'by prototype');
  let look = choose(m, d);
  // a person by default or by trade whose room line names a creature, a construct or the dead
  if (!look.beast && (look.why === 'person' || look.why === 'role') && m.long) {
    const sub = subjectOf(m.long);
    const alt = sub.length ? choose(m, { head: sub[sub.length - 1], words: sub, all: sub.join(' ') }) : null;
    if (alt && (alt.beast || alt.why === 'bestiary' || alt.why === 'undead')) look = { ...alt, why: `room line: ${alt.why}` };
  }
  if (!GHOSTLY.test(d.words.slice(0, -1).join(' '))) return look;
  if (look.beast) return look.beast.mob === 'ghost' ? look : { ...look, beast: { ...look.beast, tint: 0xb8c8f0 } };
  if (/^skeleton/.test(look.model)) return look;
  return creature(beast('ghost'), '', d.all, !!m.boss, 'ghostly');
}

function choose(m, { head, words, all }) {
  const boss = !!m.boss || (m.flags || []).includes('boss');
  const mods = words.slice(0, -1).join(' ');
  if (/-kin\b/.test(all)) return person(m, all, 'race');                    // "a dragon-kin warrior"
  // a creature named by two words: "the fire elemental", "the giant lizard", "a lizard man"
  const before = words[words.length - 2] || '';
  const pb = before ? beast(`${before} ${head}`) : null;
  if (pb && pb !== beast(before) && pb !== beast(head)) return creature(pb, words.slice(0, -2).join(' '), all, boss, 'pair');
  if (PEOPLE.has(head) || TITLES.has(head)) {
    // "the vampire hunter" hunts vampires; "a goblin mushroom farmer" is a goblin
    const agent = AGENTS.has(head);
    const race = words.slice(0, agent ? -2 : -1).join(' ');
    // ("a death knight": the dead by their whole name, not only their race)
    if (deadWords(race) || /\bdeath ?knights?\b/.test(words.join(' '))) return undead(m, all);
    const rm = race.match(RACES) || (TITLES.has(head) && !agent ? all.match(RACES) : null);   // "King of the Goblins"
    if (rm) {
      if (deadWords(rm[0])) return undead(m, all);
      const rb = beast(rm[0]);
      return rb ? creature(rb, '', all, boss, 'race') : person(m, all, 'race');
    }
    // "the spider queen", "the rat king" (but "the shadow priest" is a person)
    const cb = TITLES.has(head) && !PEOPLE.has(head) ? beast(before) : null;
    if (cb && cb.mob !== 'ghost') return creature(cb, head, all, boss, 'ruler');
    return person(m, all, 'role');
  }
  const hb = beast(head);                                                    // "the giant hornet"
  if (hb) return creature(hb, mods, all, boss, 'head');
  if (deadWords(all)) return undead(m, all);
  const fb = beast(all);                                                     // any creature word
  if (fb) return creature(fb, mods, all, boss, 'word');
  return person(m, all);
}

// ---- people the world dressed: drawn in their gear, like players ----
// A person whose zone gave them gear by name (the server's look, gear_look.py) wears it: the
// body their trade gave them above, their race from their words, a human's skin varying from
// one kind of person to the next. Creatures, skeletons and the like keep the bodies above.
const PEOPLE_RACES = [[/\b(drow|dark elf|dark elves)\b/, 'dark_elf'], [ORCISH, 'half_orc'],
  [/\b(dwarf|dwarves|dwarven|duergar)\b/, 'dwarf'], [/\b(gnome|gnomes|svirfneblin|deep gnome)\b/, 'gnome'],
  [/\b(halfling|halflings|hobbit|hobbits|brownie)\b/, 'halfling'], [/\b(elf|elves|elven|sylvan)\b/, 'elf']];
// the class whose colours their trade wears, and the body its model stands for
const TRADE_CLASS = [[/\bnecromancers?\b/, 'necromancer'],
  [/\b(guards?|guardsman|soldiers?|sentry|watchman|warden|cityguard|captain|sergeant|lieutenant|militia|knights?|paladins?|templars?|crusaders?)\b/, 'paladin'],
  [/\b(priests?|priestess|clerics?|monk|nun|acolyte|bishop|abbot|vicar|healer|oracle|druids?|shaman)\b/, 'cleric'],
  [/\b(mages?|wizards?|witch|warlocks?|sorcerers?|sorceress|conjurer|enchanter|enchantress|illusionist|magus|summoner|arcanist)\b/, 'mage'],
  [/\b(rangers?|hunter|huntress|trapper|scout|archer|bowman|poacher)\b/, 'ranger'],
  [/\b(thief|thieves|rogues?|assassins?|cutpurse|pickpocket|spy|smuggler)\b/, 'assassin'],
  [/\b(jester|bards?|minstrel|dancer|performer|juggler)\b/, 'bard']];
const MODEL_CLASS = { knight: 'paladin', barbarian: 'warrior', mage: 'mage', rogue: 'thief', rogue_hooded: 'assassin' };
const MODEL_BASE = { knight: { model: 'knight', w: 3 }, barbarian: { model: 'barbarian', w: 2 }, mage: { model: 'mage', w: 0 },
  rogue: { model: 'rogue', w: 1, hood: false }, rogue_hooded: { model: 'rogue', w: 1, hood: true } };

export function personRace(all) {
  return (PEOPLE_RACES.find(([re]) => re.test(all)) || [null, 'human'])[1];
}

// how a dressed person is drawn: { look, cls, scale }, or null when they keep their body above
export function npcDress(m, look) {
  if (!m || !m.look || !look || look.beast || !MODEL_BASE[look.model]) return null;
  const all = describe(m).all;
  const race = personRace(all);
  const dressed = { ...m.look, rn: 0, race, base: MODEL_BASE[look.model] };
  if (race === 'human') dressed.tone = hashStr(m.pv != null ? `pv${m.pv}` : all) % 4;
  dressed.sig = `${m.look.sig}:${look.model}:${race}:${dressed.tone ?? ''}`;
  const cls = (TRADE_CLASS.find(([re]) => re.test(all)) || [null, MODEL_CLASS[look.model]])[1];
  // a child is small, a boss large; a race's own build comes with its look (gearlook.js RACE)
  const scale = (/\b(child|children|kid|baby|urchin|orphan|boy|girl)\b/.test(all) ? 0.62 : 1) * (m.boss || (m.flags || []).includes('boss') ? 1.25 : 1);
  return { look: dressed, cls, scale };
}
