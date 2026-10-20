// Hero movement: WASD / arrows (relative to the camera: W is away from it), click-to-move
// with pathfinding, travel along a list of waypoints (minimap clicks), attack. Velocity
// eases toward the wanted speed, the body is a circle that slides along walls, and the
// world is a flat plane, so all of this is 2D (x, z). `blocked(x, z)` answers for the hero's current room (crossing into another
// room is legal only through an open exit — the zone decides).
import * as THREE from 'three';
import { toWorld } from './orbit.js';
import { postureChange } from './posture.js';

const RADIUS = 0.36;
const RUN = 5.2, WALK = 2.4;            // m/s
const ACCEL = 32, DECEL = 26;           // m/s^2

export class Controller {
  constructor(engine, actor, blocked) {
    this.engine = engine;
    this.actor = actor;
    this.blocked = blocked;
    this.pos = actor.root.position;
    this.vel = new THREE.Vector2();
    this.yaw = 0;
    this.keys = new Set();
    this.path = null;                    // [{x, z}] waypoints
    this.goal = null;                    // the passage a click path was sent to: {room, dir}
    this.avoidDefault = null;            // (tx, tz) => true for tiles paths go around (stairs)
    this.lock = 0;                       // seconds of attack wind-down
    this.enabled = true;
    this.onArrive = null;
    this.speedMul = 1;                   // how much faster than on foot (a mount, haste: the payload's speed)
    this.mounted = false;                // riding: the body sits; the steed walks (steed.js)
    this.position = 'standing';          // the server's posture (payload.player.position)
    this.pose = null;                    // the loop it is held in: sat down resting, lying asleep (posture.js)
    const down = e => {
      if (e.target && /INPUT|TEXTAREA|SELECT/.test(e.target.tagName)) return;
      const k = e.key.toLowerCase();
      if (['w', 'a', 's', 'd', 'arrowup', 'arrowdown', 'arrowleft', 'arrowright', 'shift'].includes(k)) {
        this.keys.add(k);
        if (k !== 'shift') { this.path = null; this.goal = null; }
        e.preventDefault();
      }
    };
    const up = e => this.keys.delete(e.key.toLowerCase());
    window.addEventListener('keydown', down);
    window.addEventListener('keyup', up);
    window.addEventListener('blur', () => this.keys.clear());
  }

  // ground point under a page position
  groundAt(clientX, clientY) {
    const r = this.engine.renderer.domElement.getBoundingClientRect();
    const ndc = new THREE.Vector2(((clientX - r.left) / r.width) * 2 - 1, -((clientY - r.top) / r.height) * 2 + 1);
    const ray = new THREE.Raycaster();
    ray.setFromCamera(ndc, this.engine.camera);
    const hit = new THREE.Vector3();
    return ray.ray.intersectPlane(new THREE.Plane(new THREE.Vector3(0, 1, 0), 0), hit) ? hit : null;
  }

  // walk there along a path; `avoid(tx, tz)` marks tiles to go around (stairs you did not
  // click), `goal` names the passage the path is meant to take
  walkTo(x, z, onArrive, { avoid = this.avoidDefault, goal = null } = {}) {
    const gx = Math.floor(x), gz = Math.floor(z);
    const step = (ax, az, bx, bz) => this.step(ax, az, bx, bz) && !(avoid && !(bx === gx && bz === gz) && avoid(bx, bz));
    const path = findPath(this.pos.x, this.pos.z, x, z, step);
    this.path = path && path.length ? path : [{ x, z }];
    this.onArrive = onArrive || null;
    this.goal = goal;
  }
  follow(waypoints, onArrive, { goal = null } = {}) { this.path = waypoints.slice(); this.onArrive = onArrive || null; this.goal = goal; }
  stop() { this.path = null; this.onArrive = null; this.goal = null; }
  // stop dead (a hop, a teleport): no glide, no running in place
  halt() {
    this.stop();
    this.vel.set(0, 0);
    this.dashing = null;
    this.actor.play(this.actor.idle || 'Idle', 0.15);
  }

  // rest, sit, sleep, wake: get down (or up) once, then hold the pose; moving cuts it short
  setPosture(position) {
    const ch = postureChange(this.position, position || 'standing');
    this.position = position || 'standing';
    if (!ch) return;
    this.pose = ch.loop;
    if (ch.once && !this.mounted) {
      const d = this.actor.once(ch.once, 0.2);
      if (d) { this.lock = d * 0.9; this.soft = true; }
    }
  }

  // can the body move from tile (ax, az) to the next tile (bx, bz)? (for path search)
  step(ax, az, bx, bz) { return !this.blockedFrom(bx + 0.5, bz + 0.5, ax + 0.5, az + 0.5); }
  blockedFrom(x, z, fx, fz) { return this.blocked(x, z, fx, fz); }

  wish() {
    const k = this.keys;
    let x = 0, z = 0;
    if (k.has('a') || k.has('arrowleft')) x -= 1;
    if (k.has('d') || k.has('arrowright')) x += 1;
    if (k.has('w') || k.has('arrowup')) z -= 1;
    if (k.has('s') || k.has('arrowdown')) z += 1;
    // W is always away from the camera, whichever way it has been turned
    if (x || z) { const l = Math.hypot(x, z); const w = toWorld(x / l, z / l, this.engine.rig.yaw || 0); return new THREE.Vector2(w.x, w.z); }
    while (this.path && this.path.length) {
      const g = this.path[0];
      const dx = g.x - this.pos.x, dz = g.z - this.pos.z, l = Math.hypot(dx, dz);
      const last = this.path.length === 1;
      if (l < (last ? 0.25 : 0.6)) {
        this.path.shift();
        if (!this.path.length) {
          this.path = null;
          this.goal = null;
          const cb = this.onArrive; this.onArrive = null;
          if (cb) cb();
          return new THREE.Vector2();
        }
        continue;
      }
      return new THREE.Vector2(dx / l, dz / l).multiplyScalar(last ? Math.min(1, l / 0.8) : 1);
    }
    return new THREE.Vector2();
  }

  free(x, z) {
    // the circle's four extreme points, its diagonals and its centre must be open ground
    const b = (px, pz) => this.blocked(px, pz, this.pos.x, this.pos.z);
    const d = RADIUS * 0.7;
    return !b(x, z) && !b(x + RADIUS, z) && !b(x - RADIUS, z) && !b(x, z + RADIUS) && !b(x, z - RADIUS)
      && !b(x + d, z + d) && !b(x - d, z + d) && !b(x + d, z - d) && !b(x - d, z - d);
  }

  // a short rush to a point (charge, lunges): eased, stops at the last open spot; `height`
  // makes it a leap, `face: false` keeps the way the hero looks (a step back, a sidestep)
  dash(x, z, time = 0.25, { height = 0, face = true } = {}) {
    this.dashing = { fx: this.pos.x, fz: this.pos.z, tx: x, tz: z, t: 0, time, height };
    this.path = null;
    if (face) this.yaw = Math.atan2(x - this.pos.x, z - this.pos.z);
  }
  // laid over whatever the body is doing (abilities, fxdirector.js): a turn on the spot, a
  // rise off the ground (`slam`: up slowly, down hard), a blink to a nearby open spot
  spin(turns = 1, time = 0.5) { this.spinning = { turns, time, t: 0 }; }
  lift(height = 0.6, time = 1, slam = false) { this.lifting = { height, time, t: 0, slam }; }
  blink(x, z) {
    if (this.free(x, z)) { this.pos.x = x; this.pos.z = z; }
    this.vel.set(0, 0); this.path = null; this.dashing = null;
  }
  // the turn and height of the moment
  overlay(dt) {
    let turn = 0, y = 0;
    if (this.spinning) {
      const s = this.spinning;
      s.t += dt;
      const k = Math.min(1, s.t / s.time);
      turn = (1 - Math.pow(1 - k, 2)) * s.turns * Math.PI * 2;
      if (k >= 1) this.spinning = null;
    }
    if (this.lifting) {
      const l = this.lifting;
      l.t += dt;
      const k = Math.min(1, l.t / l.time);
      y = l.height * (l.slam ? (k < 0.75 ? Math.sin(k / 0.75 * Math.PI / 2) : Math.max(0, 1 - (k - 0.75) / 0.25))
        : k < 0.25 ? Math.sin(k / 0.25 * Math.PI / 2) : k > 0.8 ? Math.max(0, (1 - k) / 0.2) : 1);
      if (k >= 1) this.lifting = null;
    }
    const d = this.dashing;
    if (d && d.height) y += d.height * 4 * d.t * (1 - d.t);
    this.actor.root.rotation.y = this.yaw + turn;
    this.pos.y = y;
  }

  update(dt) {
    if (this.dashing) {
      const d = this.dashing;
      d.t = Math.min(1, d.t + dt / d.time);
      const k = d.height ? d.t : 1 - Math.pow(1 - d.t, 3);
      const nx = d.fx + (d.tx - d.fx) * k, nz = d.fz + (d.tz - d.fz) * k;
      if (this.free(nx, nz)) { this.pos.x = nx; this.pos.z = nz; } else if (!d.height) d.t = 1;
      this.overlay(dt);
      if (d.t >= 1) { this.dashing = null; this.pos.y = 0; }
      this.vel.set(0, 0);
      return 0;
    }
    this.lock = Math.max(0, this.lock - dt);
    // a soft swing (an auto-attack, a flinch) never roots you: moving cuts it short
    if (this.lock > 0 && this.soft && this.enabled && !MH.state.uiFrozen && this.wish().lengthSq() > 0) {
      this.lock = 0;
      this.actor.stopOnce(0.1);
    }
    const w = this.enabled && !MH.state.uiFrozen && this.lock === 0 ? this.wish() : new THREE.Vector2();
    const top = (this.keys.has('shift') ? WALK : RUN) * (this.speedMul || 1);
    const want = w.clone().multiplyScalar(top);
    const dv = want.clone().sub(this.vel);
    const rate = (want.lengthSq() > this.vel.lengthSq() ? ACCEL : DECEL) * dt;
    if (dv.length() > rate) dv.setLength(rate);
    this.vel.add(dv);

    // move each axis on its own: blocked on one, still slide along the other
    const nx = this.pos.x + this.vel.x * dt;
    if (this.free(nx, this.pos.z)) this.pos.x = nx; else this.vel.x = 0;
    const nz = this.pos.z + this.vel.y * dt;
    if (this.free(this.pos.x, nz)) this.pos.z = nz; else this.vel.y = 0;

    const speed = this.vel.length();
    if (speed > 0.15) {
      const target = Math.atan2(this.vel.x, this.vel.y);
      let d = target - this.yaw;
      d = Math.atan2(Math.sin(d), Math.cos(d));
      this.yaw += d * Math.min(1, dt * 14);
    }
    this.overlay(dt);
    if (this.lock === 0 && this.mounted) this.actor.play('Idle', 0.2);         // the legs: steed.js ridePose
    else if (this.lock === 0) {
      if (speed > 3.2) this.actor.play('Running_A', 0.15, speed / (RUN * (this.speedMul || 1)) * 1.05 * Math.sqrt(this.speedMul || 1));
      else if (speed > 0.25) this.actor.play('Walking_A', 0.15, Math.max(0.6, speed / WALK));
      else if (this.pose) this.actor.play(this.pose, 0.35);
      else this.actor.play(this.actor.idle || 'Idle', 0.25);
    }
    return speed;
  }

  // soft: drawn from a server event (a round's blow, being hit) — skipped while you run,
  // cancelled when you start moving; a key press (soft = false) commits you for a moment
  // `force`: an ability's second clip (aim, then loose) follows its first
  swing(anim = '1H_Melee_Attack_Chop', soft = false, { speed = 1.25, force = false } = {}) {
    if (this.lock > 0 && !this.soft && !force) return;      // nothing cuts into a committed move
    if (soft && (this.keys.size || this.path || this.dashing || this.vel.lengthSq() > 1)) return;
    const d = this.actor.once(anim, 0.06, speed);
    this.lock = Math.min(0.55, d * 0.7);
    this.soft = soft;
  }
  face(x, z) { this.yaw = Math.atan2(x - this.pos.x, z - this.pos.z); }
}

// A* over 1 m tiles, 8 directions (no corner cutting), with a node budget so a far click
// can never stall a frame; then string-pulled to a few straight segments.
export function findPath(sx, sz, gx, gz, canStep, budget = 6000) {
  const ax = Math.floor(sx), az = Math.floor(sz), bx = Math.floor(gx), bz = Math.floor(gz);
  if (ax === bx && az === bz) return [{ x: gx, z: gz }];
  const key = (x, z) => x * 100003 + z;
  const open = [[0, ax, az]], g = new Map([[key(ax, az), 0]]), from = new Map();
  const h = (x, z) => Math.hypot(x - bx, z - bz);
  let found = false, best = null, bestH = Infinity, n = 0;
  while (open.length && n++ < budget) {
    let bi = 0;
    for (let i = 1; i < open.length; i++) if (open[i][0] < open[bi][0]) bi = i;
    const [, x, z] = open.splice(bi, 1)[0];
    const hx = h(x, z);
    if (hx < bestH) { bestH = hx; best = [x, z]; }
    if (x === bx && z === bz) { found = true; best = [x, z]; break; }
    const gc = g.get(key(x, z));
    for (const [dx, dz] of [[1, 0], [-1, 0], [0, 1], [0, -1], [1, 1], [1, -1], [-1, 1], [-1, -1]]) {
      const nx = x + dx, nz = z + dz;
      if (!canStep(x, z, nx, nz)) continue;
      if (dx && dz && (!canStep(x, z, x + dx, z) || !canStep(x, z, x, z + dz))) continue;
      const ng = gc + (dx && dz ? 1.4142 : 1);
      const k = key(nx, nz);
      if (g.has(k) && g.get(k) <= ng) continue;
      g.set(k, ng);
      from.set(k, [x, z]);
      open.push([ng + h(nx, nz), nx, nz]);
    }
  }
  if (!best) return null;
  const cells = [];
  for (let c = best; c; c = from.get(key(c[0], c[1]))) cells.unshift(c);
  const pts = cells.map(([x, z]) => ({ x: x + 0.5, z: z + 0.5 }));
  if (found) pts[pts.length - 1] = { x: gx, z: gz };
  // string pulling: drop points while the straight line stays walkable
  const clear = (p, q) => {
    const steps = Math.ceil(Math.hypot(q.x - p.x, q.z - p.z) * 3);
    let px = Math.floor(p.x), pz = Math.floor(p.z);
    for (let i = 1; i <= steps; i++) {
      const x = Math.floor(p.x + (q.x - p.x) * i / steps), z = Math.floor(p.z + (q.z - p.z) * i / steps);
      if (x !== px || z !== pz) { if (!canStep(px, pz, x, z)) return false; px = x; pz = z; }
    }
    return true;
  };
  const out = [];
  let i = 0;
  while (i < pts.length - 1) {
    let j = pts.length - 1;
    while (j > i + 1 && !clear(pts[i], pts[j])) j--;
    out.push(pts[j]);
    i = j;
  }
  return out.length ? out : pts.slice(1);
}
