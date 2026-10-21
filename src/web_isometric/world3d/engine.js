// Renderer, scene, lights, camera rig, post-processing and the frame loop.
// One continuous world: nothing here knows about rooms. Callers add objects and
// register per-frame callbacks with engine.onTick(fn(dt, t)).
import * as THREE from 'three';
import { EffectComposer } from 'three/addons/postprocessing/EffectComposer.js';
import { RenderPass } from 'three/addons/postprocessing/RenderPass.js';
import { UnrealBloomPass } from 'three/addons/postprocessing/UnrealBloomPass.js';
import { OutputPass } from 'three/addons/postprocessing/OutputPass.js';
import { ShaderPass } from 'three/addons/postprocessing/ShaderPass.js';
import { orbitOffset, pitchFor, dragOrbit, nearestTurn } from './orbit.js';

// ?q=low|med|high, default high (the Mac mini and any recent laptop handle it)
export const QUALITY = {
  low: { name: 'low', dpr: 1, shadows: false, shadowSize: 1024, bloom: false, antialias: false },
  med: { name: 'med', dpr: 1.25, shadows: true, shadowSize: 1024, bloom: true, antialias: true },
  high: { name: 'high', dpr: 2, shadows: true, shadowSize: 2048, bloom: true, antialias: true },
};

// Lighting moods (bg: how much of the fog colour the far background is: 1 outdoors, a haze; dark
// enclosed). The world is one scene with one sun, so "indoors" is a mood the
// rig blends to when the hero's room is enclosed (a crypt under an open sky).
export const MOODS = {
  day: { sky: 0xcfe2ff, ground: 0x5a4a32, hemi: 1.15, sun: 0xfff1d6, sunI: 2.6, fog: 0xa9bfd0, near: 34, far: 90, exposure: 1.0, bg: 1.0 },
  // open water by day: a blue-grey haze the far sea fades into (far.js fills the sea to it)
  sea: { sky: 0xc8dcef, ground: 0x2a4a5a, hemi: 1.1, sun: 0xfff1d6, sunI: 2.5, fog: 0x7194ad, near: 40, far: 110, exposure: 1.0, bg: 1.0 },
  forest: { sky: 0xbfe0c8, ground: 0x3a3424, hemi: 1.0, sun: 0xffe6b8, sunI: 2.3, fog: 0x8fae9a, near: 30, far: 80, exposure: 1.0, bg: 1.0 },
  crypt: { sky: 0x6a7a9a, ground: 0x2a221a, hemi: 0.65, sun: 0x8c9cc8, sunI: 0.5, fog: 0x12141c, near: 20, far: 56, exposure: 1.25, bg: 0.35 },
  // a lit interior (temple, shop, inn): warm and readable, no strong sun
  interior: { sky: 0xffe6c4, ground: 0x4a3a28, hemi: 1.0, sun: 0xffe2b8, sunI: 1.05, fog: 0x1c1712, near: 28, far: 72, exposure: 1.1, bg: 0.35 },
  dusk: { sky: 0xf0b890, ground: 0x3a2a24, hemi: 0.85, sun: 0xff9a5a, sunI: 1.6, fog: 0x6a5060, near: 30, far: 80, exposure: 1.05, bg: 0.9 },
  night: { sky: 0x6a7aaa, ground: 0x22222c, hemi: 0.8, sun: 0xa8bcff, sunI: 0.95, fog: 0x141c30, near: 28, far: 72, exposure: 1.3, bg: 0.85 },
  // the room looks (room_looks.py): rock close and cold, sand hot and hazy, snow bright, ash red
  ice_cave: { sky: 0xb4cce6, ground: 0x4a5a6c, hemi: 1.2, sun: 0xcfe4ff, sunI: 0.6, fog: 0x1a2634, near: 20, far: 58, exposure: 1.15, bg: 0.4 },
  lava_cave: { sky: 0xc87458, ground: 0x5a2410, hemi: 1.35, sun: 0xff8a50, sunI: 1.2, fog: 0x2a120a, near: 18, far: 54, exposure: 1.3, bg: 0.6 },
  cave: { sky: 0xa8b4cc, ground: 0x5a4a3c, hemi: 1.45, sun: 0xb8c4e0, sunI: 0.85, fog: 0x161a22, near: 20, far: 60, exposure: 1.35, bg: 0.35 },
  desert: { sky: 0xfff0d0, ground: 0x8a6a40, hemi: 1.2, sun: 0xffe8b8, sunI: 2.9, fog: 0xe8d4b0, near: 30, far: 85, exposure: 1.0, bg: 1.0 },
  snow: { sky: 0xe4eeff, ground: 0x8a96a8, hemi: 1.15, sun: 0xf4f8ff, sunI: 2.2, fog: 0xd8e4f0, near: 26, far: 75, exposure: 0.95, bg: 1.0 },
  // under the sea: green-blue light from above, the far distance lost in deep water
  // (deep and blue: the fog close, the light from above cold; the old haze read as a dry field)
  underwater: { sky: 0x7ad0e8, ground: 0x1a4a5a, hemi: 1.4, sun: 0xa8e8ff, sunI: 1.3, fog: 0x1a6a86, near: 7, far: 34, exposure: 1.15, bg: 0.75 },
  // a spider's lair: grey-green gloom under a webbed canopy
  web: { sky: 0xa8b8a4, ground: 0x3a3a2c, hemi: 1.35, sun: 0xd8e4c8, sunI: 1.15, fog: 0x3a4236, near: 18, far: 56, exposure: 1.3, bg: 0.6 },
  // a dead city (Morkai): grave-green ghost-light in a cavern, dark but readable
  // the drow city's cavern: black overhead, a violet gloom lit by faerie fire (terrain-drow.js)
  // the Clockwork Foundry: soot overhead, the glow of furnaces and the haze of steam (terrain-interiors.js)
  foundry: { sky: 0x8a6a4a, ground: 0x2a2018, hemi: 1.0, sun: 0xffb070, sunI: 0.8, fog: 0x1e1610, near: 20, far: 58, exposure: 1.35, bg: 0.3 },
  drow: { sky: 0x6a5a9a, ground: 0x1c1428, hemi: 1.05, sun: 0x9a8ad8, sunI: 0.7, fog: 0x0e0a18, near: 22, far: 62, exposure: 1.45, bg: 0.25 },
  necropolis: { sky: 0x8a9c98, ground: 0x262a24, hemi: 1.15, sun: 0xb4d4c0, sunI: 0.95, fog: 0x1a2622, near: 20, far: 60, exposure: 1.4, bg: 0.4 },
  // a sewer: sickly green-brown gloom off the water, close and dank, the lamps the only warmth
  sewer: { sky: 0x8a9a7a, ground: 0x2a2c1e, hemi: 0.95, sun: 0x9aa880, sunI: 0.65, fog: 0x12160e, near: 18, far: 52, exposure: 1.3, bg: 0.3 },
  volcanic: { sky: 0x9a5a48, ground: 0x3a160a, hemi: 0.85, sun: 0xff8a50, sunI: 1.4, fog: 0x3a1a12, near: 22, far: 64, exposure: 1.1, bg: 0.75 },
};

export function createEngine(container, opts = {}) {
  const q = QUALITY[opts.quality] || QUALITY.high;
  const renderer = new THREE.WebGLRenderer({ antialias: q.antialias, powerPreference: 'high-performance' });
  renderer.setPixelRatio(Math.min(window.devicePixelRatio || 1, q.dpr));
  renderer.outputColorSpace = THREE.SRGBColorSpace;
  renderer.toneMapping = THREE.ACESFilmicToneMapping;
  renderer.shadowMap.enabled = q.shadows;
  renderer.shadowMap.type = THREE.PCFSoftShadowMap;
  // count draw calls over the whole frame (shadow + scene + bloom passes), not the last pass
  renderer.info.autoReset = false;
  container.appendChild(renderer.domElement);

  const scene = new THREE.Scene();
  scene.background = new THREE.Color(0x07080b);
  scene.fog = new THREE.Fog(0x0d0f16, 30, 80);

  const hemi = new THREE.HemisphereLight(0xffffff, 0x444444, 1);
  const sun = new THREE.DirectionalLight(0xffffff, 2);
  sun.castShadow = q.shadows;
  sun.shadow.mapSize.set(q.shadowSize, q.shadowSize);
  Object.assign(sun.shadow.camera, { left: -24, right: 24, top: 24, bottom: -24, near: 1, far: 90 });
  sun.shadow.bias = -0.0004;
  sun.shadow.normalBias = 0.04;
  scene.add(hemi, sun, sun.target);

  // ---- camera rig: orbits the hero (right-drag, orbit.js), smooth follow ----
  const camera = new THREE.PerspectiveCamera(36, 1, 0.5, 220);
  // The pitch follows the zoom (owner: "see more of the character's face"): pulled back
  // it looks down on the room like a map (58°); zoomed in it drops toward the hero's
  // face (34°). The default sits in between. A right-drag turns the view around the hero
  // (yaw; 0 = north up) and tilts it (added to the zoom's pitch); it stays where it is left
  // until snapNorth() (Home, or the minimap's compass).
  const rig = {
    target: new THREE.Vector3(),     // what we look at (the hero)
    focus: new THREE.Vector3(),      // smoothed target
    pitch: THREE.MathUtils.degToRad(46),
    lowPitch: 34, highPitch: 58,
    dist: 19, minDist: 10, maxDist: 34, wantDist: 19,
    yaw: 0, tilt: 0, snap: null,
  };
  function placeCamera(snap) {
    if (snap) rig.focus.copy(rig.target);
    const k = THREE.MathUtils.clamp((rig.dist - rig.minDist) / (rig.maxDist - rig.minDist), 0, 1);
    rig.pitch = pitchFor(THREE.MathUtils.lerp(rig.lowPitch, rig.highPitch, Math.pow(k, 0.8)), rig.tilt);
    const off = orbitOffset(rig.yaw, rig.pitch, rig.dist);
    camera.position.set(rig.focus.x + off.x, rig.focus.y + off.y, rig.focus.z + off.z);
    camera.lookAt(rig.focus.x, rig.focus.y + 1.1, rig.focus.z);
    // impact shake (fx.js): a small offset for a few frames on heavy blows
    const sh = rig.shake && rig.shake();
    if (sh) camera.position.add(sh);
  }
  // turn and tilt by a drag of (dx, dy) pixels
  function orbit(dx, dy) {
    rig.snap = null;
    const o = dragOrbit(rig.yaw, rig.tilt, dx, dy);
    rig.yaw = o.yaw; rig.tilt = o.tilt;
  }
  // ease back to north up and the zoom's own pitch (on the wall clock: a hit-stop can't slow it)
  function snapNorth() {
    rig.snap = { t0: performance.now(), yaw0: rig.yaw, tilt0: rig.tilt, yaw1: nearestTurn(rig.yaw) };
  }
  function easeSnap() {
    const s = rig.snap;
    if (!s) return;
    const k = Math.min(1, (performance.now() - s.t0) / 350), e = 1 - Math.pow(1 - k, 3);
    rig.yaw = s.yaw0 + (s.yaw1 - s.yaw0) * e;
    rig.tilt = s.tilt0 * (1 - e);
    if (k >= 1) { rig.yaw = 0; rig.tilt = 0; rig.snap = null; }
  }
  // zoom: proportional to the wheel (a trackpad glides, a notch steps ~15%); a sideways-only
  // scroll (deltaY 0) does nothing
  renderer.domElement.addEventListener('wheel', e => {
    e.preventDefault();
    if (!e.deltaY) return;
    const px = THREE.MathUtils.clamp(e.deltaY * (e.deltaMode ? 33 : 1), -100, 100);
    rig.wantDist = THREE.MathUtils.clamp(rig.wantDist * Math.exp(px * 0.0015), rig.minDist, rig.maxDist);
  }, { passive: false });

  // ---- post: bloom only on what is really bright (torches, sparks), then tone map ----
  // A pixel the GPU worked out as not-a-number (or infinite) would be smeared by the bloom's blur
  // over most of the screen as black: the scene is clamped to finite light before the bloom.
  const SCRUB = {
    uniforms: { tDiffuse: { value: null } },
    vertexShader: 'varying vec2 vUv; void main() { vUv = uv; gl_Position = projectionMatrix * modelViewMatrix * vec4(position, 1.0); }',
    fragmentShader: `uniform sampler2D tDiffuse; varying vec2 vUv;
      void main() { vec4 c = texture2D(tDiffuse, vUv);
        bvec4 bad = bvec4(isnan(c.r) || isinf(c.r), isnan(c.g) || isinf(c.g), isnan(c.b) || isinf(c.b), isnan(c.a) || isinf(c.a));
        c = vec4(bad.x ? 0.0 : c.r, bad.y ? 0.0 : c.g, bad.z ? 0.0 : c.b, bad.w ? 1.0 : c.a);
        gl_FragColor = min(max(c, vec4(0.0)), vec4(64.0)); }`,
  };
  function makeComposer() {
    const c = new EffectComposer(renderer);
    c.addPass(new RenderPass(scene, camera));
    c.addPass(new ShaderPass(SCRUB));
    c.addPass(new UnrealBloomPass(new THREE.Vector2(256, 256), 0.32, 0.45, 0.88));
    c.addPass(new OutputPass());
    return c;
  }
  let composer = q.bloom ? makeComposer() : null;

  function resize() {
    const w = container.clientWidth || window.innerWidth, h = container.clientHeight || window.innerHeight;
    renderer.setSize(w, h, false);
    camera.aspect = w / h;
    camera.updateProjectionMatrix();
    if (composer) { composer.setPixelRatio(renderer.getPixelRatio()); composer.setSize(w, h); }
  }
  window.addEventListener('resize', resize);
  resize();

  // the GPU dropped the 3D view (a driver reset, a stall): three.js asks the browser for it back;
  // when it comes back the bloom's buffers are made afresh. If it never does, say so and offer a
  // reload rather than leave the world black under a working HUD.
  let lostNote = null, lostTimer = 0;
  renderer.domElement.addEventListener('webglcontextlost', () => {
    console.warn('3D view lost (WebGL context lost)');
    clearTimeout(lostTimer);
    lostTimer = setTimeout(() => {
      if (lostNote || typeof document === 'undefined') return;
      lostNote = document.createElement('div');
      lostNote.className = 'gl-lost';
      lostNote.style.cssText = 'position:fixed;left:50%;top:38%;transform:translate(-50%,-50%);z-index:50;padding:14px 18px;'
        + 'background:rgba(12,10,16,0.92);border:1px solid #8a6a3a;border-radius:8px;color:#f0e2c0;font:15px/1.4 serif;text-align:center';
      lostNote.innerHTML = 'The graphics card dropped the 3D view.<br><button style="margin-top:8px;padding:4px 14px;cursor:pointer">Reload the view</button>';
      lostNote.querySelector('button').onclick = () => location.reload();
      document.body.appendChild(lostNote);
    }, 3000);
  });
  renderer.domElement.addEventListener('webglcontextrestored', () => {
    console.warn('3D view restored');
    clearTimeout(lostTimer);
    if (lostNote) { lostNote.remove(); lostNote = null; }
    if (composer) { if (composer.dispose) composer.dispose(); composer = makeComposer(); }
    resize();
  });

  // ---- mood blending ----
  const cur = { ...MOODS.day }, want = { ...MOODS.day };
  const colors = { sky: new THREE.Color(), ground: new THREE.Color(), sun: new THREE.Color(), fog: new THREE.Color() };
  let gloomNow = 0, darkNow = 0, flashNow = 0;
  const wNow = { dim: 0, fog: 0, grey: 0 }, GREY = new THREE.Color(0x9aa2ac);
  function setMood(m, instant) {
    Object.assign(want, typeof m === 'string' ? MOODS[m] : m);
    if (instant) Object.assign(cur, want);
  }
  function blendMood(dt) {
    const k = 1 - Math.exp(-dt * 2.2);
    for (const key of ['hemi', 'sunI', 'near', 'far', 'exposure', 'bg']) cur[key] += (want[key] - cur[key]) * k;
    for (const key of ['sky', 'ground', 'sun', 'fog']) {
      colors[key].set(cur[key]).lerp(new THREE.Color(want[key]), k);
      cur[key] = colors[key].getHex();
    }
    // a boss's gloom (combat.js gloom): the light dies as it weakens
    gloomNow += ((api.gloom || 0) - gloomNow) * (1 - Math.exp(-dt * 1.5));
    // a dark room (main.js sight): the light of the world goes, the hero's own light stays
    darkNow += ((api.darkness || 0) - darkNow) * (1 - Math.exp(-dt * 2.5));
    // the weather under open sky (weather.js): cloud dims the sun, rain and fog draw the haze in
    // and grey it; a storm's lightning lights everything for an instant
    const wt = api.weather || {}, open = (cur.bg ?? 0) >= 0.75 ? 1 : 0;
    for (const k of ['dim', 'fog', 'grey']) wNow[k] += ((wt[k] || 0) * open - wNow[k]) * (1 - Math.exp(-dt * 0.8));
    flashNow = Math.max(0, flashNow - dt * 5);
    const dim = (1 - 0.85 * gloomNow) * (1 - 0.75 * darkNow);
    hemi.color.set(cur.sky); hemi.groundColor.set(cur.ground); hemi.intensity = cur.hemi * dim * (1 - 0.35 * wNow.dim) + flashNow * 2.5;
    sun.color.set(cur.sun); sun.intensity = cur.sunI * dim * (1 - 0.7 * wNow.dim);
    scene.fog.color.set(cur.fog).lerp(GREY, wNow.grey * 0.6).multiplyScalar(1 - 0.85 * darkNow);
    // under open sky the haze lies further off (far.js draws what is out there; by quality)
    const sight = (cur.bg ?? 0) >= 0.75 ? (api.farSight || 1) : 1;
    scene.fog.near = cur.near * (1 + (sight - 1) * 0.5) * (1 - 0.4 * gloomNow) * (1 - 0.5 * darkNow) * (1 - 0.75 * wNow.fog);
    scene.fog.far = cur.far * sight * (1 - 0.5 * gloomNow) * (1 - 0.45 * darkNow) * (1 - 0.6 * wNow.fog);
    // under open sky the distance fades into the haze itself; enclosed, into the dark
    scene.background.set(cur.fog).multiplyScalar(cur.bg ?? 0.35);
    if (darkNow > 0.01) scene.background.multiplyScalar(1 - 0.9 * darkNow);
    // (the player's own Brightness setting on top: Settings, main.js)
    renderer.toneMappingExposure = cur.exposure * (1 - 0.45 * gloomNow) * (1 - 0.15 * darkNow) * (api.brightness || 1);
  }

  // ---- loop ----
  // ticks move the world; late ticks run once the camera is placed for this frame (screen
  // overlays: nameplates, floating text, the see-through circle, prompts, the minimap)
  const ticks = [], lateTicks = [];
  const clock = new THREE.Clock();
  let frames = 0, stopUntil = 0, elapsed = 0;
  // `fixed`: a step of exactly that long (engine.step: screenshots of effects mid-flight)
  function frame(fixed) {
    // hit-stop: a big blow freezes the world for a few frames (time crawls, it never stops)
    const raw = fixed != null ? fixed : Math.min(clock.getDelta(), 0.05) * api.timeScale;
    const dt = performance.now() < stopUntil ? raw * 0.06 : raw;
    const t = (elapsed += dt);
    for (const fn of ticks) fn(dt, t);
    rig.dist += (rig.wantDist - rig.dist) * (1 - Math.exp(-dt * 10));
    rig.focus.lerp(rig.target, 1 - Math.exp(-dt * 9));
    easeSnap();
    placeCamera(false);
    camera.updateMatrixWorld();
    for (const fn of lateTicks) fn(dt, t);
    // the sun's shadow box follows the hero so shadows stay sharp everywhere
    sun.position.set(rig.focus.x - 14, 30, rig.focus.z + 10);
    sun.target.position.copy(rig.focus);
    blendMood(dt);
    renderer.info.reset();
    if (composer) composer.render(dt); else renderer.render(scene, camera);
    frames++;
  }
  // the picture's sharpness follows the machine: when frames come slower than ~42 a second the
  // pixel density steps down (never below 1: the screen's own pixels), and back up after a steady
  // stretch at ~55+ a second, never above the chosen quality's (Settings -> Graphics)
  const fit = { ema: 16.7, last: 0, at: 0, good: 0, pr: renderer.getPixelRatio() };
  function fitResolution() {
    const now = performance.now(), gap = now - fit.last;
    fit.last = now;
    if (gap <= 0 || gap > 250) return;               // a hidden tab, a hitch, a reload: not a trend
    fit.ema += (gap - fit.ema) * 0.05;
    if (now - fit.at < 2000) return;
    fit.at = now;
    const cap = Math.min(window.devicePixelRatio || 1, api.quality.dpr);
    if (fit.ema > 24 && fit.pr > 1) { fit.pr = Math.max(1, fit.pr - 0.25); fit.good = 0; }
    else if (fit.ema < 18 && fit.pr < cap) { if (++fit.good >= 4) { fit.pr = Math.min(cap, fit.pr + 0.25); fit.good = 0; } }
    else { fit.good = 0; return; }
    if (Math.abs(renderer.getPixelRatio() - fit.pr) > 0.01) { renderer.setPixelRatio(fit.pr); resize(); }
  }
  renderer.setAnimationLoop(() => { frame(); fitResolution(); });

  // a graphics quality chosen in Settings, at once: the pixel ratio, shadows and bloom change
  // now; smoothed edges (antialias) are fixed when the page starts. Returns whether a reload
  // would still change something.
  function setQuality(name) {
    const nq = QUALITY[name] || QUALITY.high;
    if (nq === api.quality) return false;
    renderer.setPixelRatio(fit.pr = Math.min(window.devicePixelRatio || 1, nq.dpr));
    if (renderer.shadowMap.enabled !== nq.shadows) {
      renderer.shadowMap.enabled = nq.shadows;
      sun.castShadow = nq.shadows;
      // materials compile with or without shadows: have them rebuilt
      scene.traverse(o => { const m = o.material; if (m) (Array.isArray(m) ? m : [m]).forEach(x => { x.needsUpdate = true; }); });
    }
    if (sun.shadow.mapSize.x !== nq.shadowSize) {
      sun.shadow.mapSize.set(nq.shadowSize, nq.shadowSize);
      if (sun.shadow.map) { sun.shadow.map.dispose(); sun.shadow.map = null; }
    }
    if (nq.bloom && !composer) composer = makeComposer();
    else if (!nq.bloom && composer) { if (composer.dispose) composer.dispose(); composer = null; }
    api.quality = nq;
    resize();
    return nq.antialias !== q.antialias;
  }

  // the light the hero carries in the dark: a torch's warm circle, or (none) a faint glimmer to
  // feel by (main.js sets its strength and keeps it with the hero)
  const heroLight = new THREE.PointLight(0xffb36a, 0, 10, 1.6);
  scene.add(heroLight);
  const api = {
    THREE, renderer, scene, camera, rig, sun, hemi, quality: q,
    timeScale: 1,                      // slow motion for the effects gallery
    darkness: 0,                       // 0..1: a dark room (main.js sight)
    brightness: 1,                     // the player's Brightness setting (exposure × this)
    heroLight,                         // the light the hero carries (main.js moves it)
    onTick: fn => ticks.push(fn),
    onLateTick: fn => lateTicks.push(fn),
    orbit, snapNorth, setQuality,
    hitStop: ms => { stopUntil = Math.max(stopUntil, performance.now() + ms); },
    // a crit lands: the view darts in a little and eases back (the rig's own easing)
    punch: m => { rig.dist = Math.max(rig.minDist * 0.8, rig.dist - m); },
    // a storm's lightning (weather.js): the whole scene lit for an instant
    lightning: () => { flashNow = 1; },
    weather: null,                     // {dim, fog, grey}: the sky's mood under open sky (weather.js)
    setMood, placeCamera, MOODS,
    // stop the loop and advance by hand, `n` frames of `dt` each (a slow machine still shows
    // every moment of an effect); setManual(false) starts the loop again
    setManual(on) { renderer.setAnimationLoop(on ? null : () => { frame(); fitResolution(); }); clock.getDelta(); },
    get pixelRatio() { return renderer.getPixelRatio(); },
    step(dt = 1 / 30, n = 1) { for (let i = 0; i < n; i++) frame(dt); },
    get frames() { return frames; },
  };
  return api;
}
