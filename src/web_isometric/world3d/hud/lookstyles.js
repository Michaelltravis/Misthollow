// The looks a class may choose beyond its own (player.py LOOK_STYLES, gear_look.py `style`): the
// class's own ('classic') and the other, each with a line that says it. The creation wizard
// (login.js) and the Character window (character.js) both offer them. Pure.
export const STYLES = {
  mage: [['classic', 'The young mage in a travelling coat.'], ['archmage', 'A tall hat, a long white beard, a robe to the ankles and a moon staff.']],
  warrior: [['classic', 'The fighter as their armour makes them.'], ['warden', 'A fur mantle, a great pauldron on the shield arm, bracers, and a crimson tabard at a broad belt.']],
  paladin: [['classic', 'The knight in the plate of their order.'], ['templar', 'A halo behind the head, winged pauldrons, a white tabard with the sun.']],
  cleric: [['classic', 'The priest in plain vestments.'], ['hierophant', 'A gold-ended stole, a sunburst behind the head, a censer at the belt.']],
  thief: [['classic', 'The rogue in travelling leathers.'], ['footpad', 'A red scarf, a bandolier of knives, pouches at the belt.']],
  assassin: [['classic', 'The hooded killer.'], ['nightblade', 'A pointed black mantle, crossed blades on the back, a red sash.']],
  ranger: [['classic', 'The hooded hunter.'], ['wayfinder', 'A mantle of leaves, feathers at the shoulder, a bedroll on the back.']],
  bard: [['classic', 'The player in road clothes.'], ['troubadour', 'A white ruff, a half-cape, a lute across the back.']],
  necromancer: [['classic', 'The dark scholar in a robe.'], ['gravecaller', 'A collar of bone spikes, a skull on the shoulder, a ragged shroud.']],
};

// the class whose look is being asked, by the name of the other look the server offers
export const classOfStyle = other => Object.keys(STYLES).find(c => STYLES[c].some(([id]) => id === other)) || null;

// what the Character window shows: the class's looks with the one worn marked ([]: it has no choice)
export function lookChoices(cls, style) {
  const list = STYLES[String(cls || '').toLowerCase()];
  if (!list) return [];
  const now = list.some(([id]) => id === style) ? style : 'classic';
  return list.map(([id, words]) => ({ id, words, on: id === now }));
}
