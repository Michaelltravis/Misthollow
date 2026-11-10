// What the banner says of a region (the world's nine: docs/world/WORLD_SPINE.md). Pure.
// A room's own banner (no zone named) says nothing of the region. A zone's banner names its
// region over the zone; the region's line is said only on crossing into it: from another region,
// or on first arriving. `last` is the id of the region last announced (null: none yet).
// `levels` ({zone: about what level the zone's creatures are, hero: the hero's}): a zone eight or more
// levels beyond the hero says so instead, in the place of the region's line (the world's danger does
// not always follow its distance: a level-31 necropolis opens two zones from the Temple).
export const BEYOND_BY = 8;
export function bannerSays(zone, region, last = null, levels = null) {
  if (!zone) return { region: '', line: '', danger: false };
  const beyond = levels && levels.zone && levels.hero && levels.zone - levels.hero >= BEYOND_BY;
  const warn = beyond ? `This place is beyond you: what lives here is about level ${levels.zone}.` : '';
  if (!region || !region.name) return { region: '', line: warn, danger: !!beyond };
  const id = region.id || region.name;
  return { region: region.name, line: warn || (id !== last ? region.line || '' : ''), danger: !!beyond };
}

// what the map says beside a zone's name: its region, the region's levels, and about what level this
// zone's own creatures are when that lies outside them ("The Marches \u00b7 levels 8\u201320 \u00b7 here about 25")
export function mapSays(region, zoneLevel = null) {
  const parts = [];
  if (region && region.name) parts.push(region.name);
  const band = levelsText(region);
  if (band) parts.push(band);
  const l = region && region.levels;
  if (zoneLevel && (!band || zoneLevel < l[0] || zoneLevel > l[1])) parts.push(`${band ? 'here ' : ''}about level ${zoneLevel}`);
  return parts.join(' \u00b7 ');
}

// a region's levels as the map says them: "levels 8-20" ('' when it has none)
export function levelsText(region) {
  const l = region && region.levels;
  return l && l.length === 2 ? `levels ${l[0]}\u2013${l[1]}` : '';
}
