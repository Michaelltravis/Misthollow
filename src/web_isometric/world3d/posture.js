// How a body shows the server's posture (player.position: standing, sitting, resting, sleeping,
// fighting, dead). Pure (no THREE), so it runs in Node tests; controller.js poses the hero and
// entities.js the other players. The clips are the rig's own (art3d/chars/rig_anims.glb).

const SIT = { loop: 'Sit_Floor_Idle', down: 'Sit_Floor_Down', up: 'Sit_Floor_StandUp' };
const LIE = { loop: 'Lie_Idle', down: 'Lie_Down', up: 'Lie_StandUp' };

// the pose a posture is drawn in, or null for one drawn on its feet
export function poseFor(position) {
  if (position === 'resting' || position === 'sitting') return SIT;
  if (position === 'sleeping') return LIE;
  return null;
}

// the posture a body in the payload is drawn in: a player's as the server says; a creature's only
// when a spell holds it asleep (its other positions, fighting or standing, are all on its feet)
export function bodyPosition(kind, data) {
  const pos = (data && data.position) || 'standing';
  return kind === 'player' ? pos : pos === 'sleeping' ? 'sleeping' : 'standing';
}

// what to play when the posture changes from `was` to `now`: a clip once (getting down, getting
// up) and the loop to hold after it (null: back to the body's own idle)
export function postureChange(was, now) {
  const a = poseFor(was), b = poseFor(now);
  if (a === b) return null;
  if (b) return { once: a ? null : b.down, loop: b.loop };      // (from sitting to lying: straight down)
  return { once: a.up, loop: null };
}
