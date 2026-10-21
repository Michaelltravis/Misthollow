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

// what to play when the posture changes from `was` to `now`: a clip once (getting down, getting
// up) and the loop to hold after it (null: back to the body's own idle)
export function postureChange(was, now) {
  const a = poseFor(was), b = poseFor(now);
  if (a === b) return null;
  if (b) return { once: a ? null : b.down, loop: b.loop };      // (from sitting to lying: straight down)
  return { once: a.up, loop: null };
}
