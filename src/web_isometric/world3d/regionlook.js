// How each region of the world is tinted (docs/world/WORLD_SPINE.md section 4: "its light and
// look"): a slight cast over the whole picture, applied in the engine's grade, so the Lantern Vale
// is warm, the Frostmarch cold, the Sundered Reach ash-red. Slight on purpose: a room's own mood
// (crypt, forest, cave) still decides its light; the region only leans it. Pure.
//
// [red, green, blue] multipliers in linear light; 1 is no change.
export const REGION_TINT = {
  vale: [1.035, 1.0, 0.95],          // lantern gold
  marches: [0.985, 0.99, 1.02],      // grey evening
  greenreach: [0.96, 1.035, 0.95],   // under leaves
  stonemarch: [0.965, 0.99, 1.04],   // cold rock
  frostmarch: [0.92, 0.99, 1.085],   // white and steel
  sundersea: [0.97, 1.02, 1.03],     // sea green
  deeproad: [0.94, 1.04, 0.975],     // ghost-green
  reach: [1.07, 0.96, 0.92],         // ash red
  beyond: [1.03, 0.94, 1.06],        // wrong: violet
};
export const NO_TINT = [1, 1, 1];

// the tint for a zone's region ({id} from the zone map, or null: none)
export function tintFor(region) {
  return (region && REGION_TINT[region.id]) || NO_TINT;
}

// A region's own stone, for a zone whose words name none (zone_tone.py reads a zone's stone from its
// rooms; most say nothing): the Frostmarch builds in white stone, the Deep Road is black, the Sundered
// Reach red. The other regions keep the kit's grey. Returns a tone as zone_tone.py sends one, or null.
export const REGION_STONE = { frostmarch: 'white', deeproad: 'black', reach: 'red' };
export function stoneFor(region) {
  const stone = region && REGION_STONE[region.id];
  return stone ? { stone } : null;
}
