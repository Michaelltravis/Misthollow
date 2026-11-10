// How much of their own light characters get, by how bright the place is (charlook.js draws it).
// Pure: no three.js here, so the tests can ask it.

// what the mood asks of the character light. `light` is how bright the place is (0 a dark crypt,
// 1 open day): the darker, the more fill and the stronger the rim. Pure, for the tests.
export function charLightFor({ hemi = 1, sunI = 1, darkness = 0, gloom = 0 } = {}) {
  const light = Math.max(0, Math.min(1, (hemi * 0.35 + sunI * 0.3) * (1 - 0.6 * darkness) * (1 - 0.5 * gloom)));
  return {
    light,
    rim: 0.5 + 0.65 * (1 - light),          // 0.5 by day, up to 1.15 in the dark
    fill: 0.03 + 0.15 * (1 - light),        // 0.03 by day, up to 0.18 in the dark
  };
}
