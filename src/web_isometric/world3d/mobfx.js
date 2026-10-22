// A creature's spells and specials, as the 3D client draws them: which family's marks they leave
// (abilityfx.js FAMILIES), how big its rank lets them be, and the line for each (mobfx-hand.js,
// then mobfx-table.js). Pure: no three.js, so the Node tests can read it.
import { creatureRecipe, rankOf } from './abilityfx.js';
import { MOB_RECIPES } from './mobfx-hand.js';
import { MOB_TABLE } from './mobfx-table.js';

export const TABLES = [MOB_RECIPES, MOB_TABLE];

// the body a creature was given (looks.js creatureLook: look.beast.body / .mob, a person's
// model, the dead's), then the words of its name
const BODY_FAMILY = {
  elemental: 'elemental', demon: 'demon', fiend: 'demon', imp: 'demon', horror: 'demon', mindflayer: 'demon',
  overmind: 'demon', beholder: 'demon', dragon: 'dragon', frost_wyrm: 'dragon', spider: 'insect', spider_queen: 'insect',
  scorpion: 'insect', wasp: 'insect', beetle: 'insect', stick_mother: 'insect', ghost: 'undead', treant: 'elemental',
  myconid: 'elemental',
};
const WORDS = [
  [/\b(skeletons?|zombies?|ghouls?|ghasts?|lich|liches|wraiths?|spectres?|specters?|ghosts?|shades?|wights?|mummy|mummies|revenants?|banshees?|vampires?|undead)\b/, 'undead'],
  [/\b(demons?|devils?|fiends?|imps?|succubus|balors?|hellhounds?|abyssal)\b/, 'demon'],
  [/\b(dragons?|drakes?|wyrms?|wyverns?|dracolich)\b/, 'dragon'],
  [/\b(elementals?|golems?|gargoyles?|treants?)\b/, 'elemental'],
  [/\b(spiders?|scorpions?|wasps?|hornets?|beetles?|ants?|mantis|centipedes?|locusts?)\b/, 'insect'],
  [/\b(mages?|wizards?|witch|witches|warlocks?|sorcer\w*|shamans?|priests?|priestess|clerics?|necromancers?|acolytes?|cultists?|conjurers?|enchant\w*|druids?|oracles?|seers?)\b/, 'caster'],
];

export function familyOf(look = {}, data = {}) {
  const name = `${data.short || ''} ${data.name || ''} ${data.kw || ''}`.toLowerCase();
  const b = look.beast;
  // (its body first: an elemental is drawn on the ghost's model)
  if (b && b.body && BODY_FAMILY[b.body]) return BODY_FAMILY[b.body];
  if (/undead/.test(look.why || '') || /^skeleton/.test(look.model || '') || (b && /^zombie|^ghost$/.test(b.mob || ''))) return 'undead';
  if (b && BODY_FAMILY[b.mob]) return BODY_FAMILY[b.mob];
  // a golem, an animated armour, a statue: a person's model in one flat colour
  if (look.flat || (b && b.flat)) return 'construct';
  for (const [re, fam] of WORDS) if (re.test(name)) return fam;
  return b ? 'beast' : 'creature';
}

// the recipe for creature `src` (combat.js resolve(): its ent's look and data) using ability `id`
export function mobRecipe(id, src, ev = {}) {
  const ent = src && src.ent;
  const data = (ent && ent.data) || {};
  if (ent && !ent.family) ent.family = familyOf(ent.look || {}, data);
  return creatureRecipe(TABLES, id, ent ? ent.family : 'creature', ev, rankOf(data));
}
