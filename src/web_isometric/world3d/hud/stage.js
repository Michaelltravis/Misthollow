// A small second renderer: a character turning on a plinth (the class preview at creation
// and the portrait on the character sheet).
import * as THREE from 'three';
import { spawnDressed } from '../equip.js';

export function makeStage() {
  let renderer = null, canvas = null, actor = null, raf = 0, token = 0;
  const scene = new THREE.Scene();
  const cam = new THREE.PerspectiveCamera(30, 520 / 600, 0.1, 50);
  cam.position.set(0, 1.6, 6.2); cam.lookAt(0, 1.05, 0);
  scene.add(new THREE.HemisphereLight(0xdde6ff, 0x2a2018, 1.4));
  const key = new THREE.DirectionalLight(0xffe2b0, 2.6); key.position.set(2.5, 4, 3); scene.add(key);
  const rim = new THREE.DirectionalLight(0x8ab0ff, 1.6); rim.position.set(-3, 2.5, -3); scene.add(rim);
  const plinth = new THREE.Mesh(new THREE.CylinderGeometry(1.1, 1.25, 0.25, 40),
    new THREE.MeshStandardMaterial({ color: 0x3a3442, roughness: 0.6, metalness: 0.2 }));
  plinth.position.y = -0.125; scene.add(plinth);
  const clock = new THREE.Timer();
  const sinceLast = () => { clock.update(); return clock.getDelta(); };
  const loop = () => {
    raf = requestAnimationFrame(loop);
    const dt = Math.min(sinceLast(), 0.05);
    if (actor) { actor.update(dt); actor.root.rotation.y += dt * 0.5; }
    if (renderer) renderer.render(scene, cam);
  };
  return {
    attach(cv) {
      if (canvas !== cv) {
        if (renderer) renderer.dispose();
        canvas = cv;
        renderer = new THREE.WebGLRenderer({ canvas: cv, antialias: true, alpha: true });
        renderer.outputColorSpace = THREE.SRGBColorSpace;
        renderer.toneMapping = THREE.ACESFilmicToneMapping;
      }
      if (!raf) { sinceLast(); loop(); }
    },
    // look: what they wear (gear_look.py); none: the class's starting gear
    async show(cls, { flourish = true, look = null } = {}) {
      const my = ++token;
      const a = await spawnDressed(look, cls);
      if (my !== token) return;
      if (actor) scene.remove(actor.root);
      actor = a;
      scene.add(actor.root);
      actor.play('Idle', 0);
      if (flourish) actor.once(/mage|necro|cleric|bard/.test(cls) ? 'Spellcast_Shoot' : /ranger/.test(cls) ? '1H_Ranged_Shoot' : '1H_Melee_Attack_Chop', 0.1, 1);
    },
    // pause drawing; the renderer (and its WebGL context) is kept for the same canvas
    stop() { cancelAnimationFrame(raf); raf = 0; },
  };
}
