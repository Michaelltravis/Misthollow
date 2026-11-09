// What the banner says of a region (the world's nine: docs/world/WORLD_SPINE.md). Pure.
// A room's own banner (no zone named) says nothing of the region. A zone's banner names its
// region over the zone; the region's line is said only on crossing into it: from another region,
// or on first arriving. `last` is the id of the region last announced (null: none yet).
export function bannerSays(zone, region, last = null) {
  if (!zone || !region || !region.name) return { region: '', line: '' };
  const id = region.id || region.name;
  return { region: region.name, line: id !== last ? region.line || '' : '' };
}

// a region's levels as the map says them: "levels 8-20" ('' when it has none)
export function levelsText(region) {
  const l = region && region.levels;
  return l && l.length === 2 ? `levels ${l[0]}\u2013${l[1]}` : '';
}
