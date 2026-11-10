// How a character is lit, on top of the room's own light: the hero, other players and every
// creature are what the player looks at, and under the world's one sun and a few torches they
// were the darkest things on the screen (a helmet from behind in a torch-lit hall: a silhouette).
//
//   rim   an edge light on the side turned away from the camera, in the colour of the place's
//         sky: the body stands off the floor behind it
//   fill  a floor of light of the body's own colour, more of it the darker the place: nobody is
//         ever a black shape
//   blob  a soft shadow at the feet, so a body stands on the ground where the sun casts none
//         (interiors, caves, night)
//
// charLook(root) dresses a body's materials once (safe to call again: gear changes add meshes).
// The engine sets CHAR's values each frame from the mood (setCharLight).
import * as THREE from 'three';
import { charLightFor } from './charlight.js';

// shared by every character material: one write a frame lights them all
export const CHAR = {
  rim: { value: new THREE.Vector4(0.8, 0.9, 1.0, 0.5) },      // rgb, strength
  fill: { value: new THREE.Vector3(0.06, 0.06, 0.06) },
};

export { charLightFor };

const _c = new THREE.Color(), _warm = new THREE.Color(1.0, 0.86, 0.66);
// sky: the mood's sky colour (a THREE.Color, linear). The rim leans a little warm so it reads as
// light, not as fog; the fill is neutral so a body keeps its own colours.
export function setCharLight(sky, mood) {
  const want = charLightFor(mood);
  _c.copy(sky).lerp(_warm, 0.25);
  const m = Math.max(_c.r, _c.g, _c.b, 1e-3);
  CHAR.rim.value.set(_c.r / m, _c.g / m, _c.b / m, want.rim);
  CHAR.fill.value.setScalar(want.fill);
  return want;
}

function dress(mat) {
  if (!mat || mat.userData.charLook || !(mat.isMeshStandardMaterial || mat.isMeshPhongMaterial || mat.isMeshLambertMaterial)) return;
  mat.userData.charLook = true;
  const before = mat.onBeforeCompile;
  mat.onBeforeCompile = (shader, renderer) => {
    if (before) before.call(mat, shader, renderer);
    shader.uniforms.uCharRim = CHAR.rim;
    shader.uniforms.uCharFill = CHAR.fill;
    shader.fragmentShader = shader.fragmentShader
      .replace('#include <common>', '#include <common>\nuniform vec4 uCharRim;\nuniform vec3 uCharFill;')
      .replace('#include <opaque_fragment>', `
        {
          vec3 cN = normalize( normal );
          vec3 cV = normalize( vViewPosition );
          float cFacing = clamp( dot( cN, cV ), 0.0, 1.0 );
          float cUp = 0.5 + 0.5 * cN.y;                         // lit from above, in the view's frame
          float cRim = pow( 1.0 - cFacing, 2.4 ) * ( 0.3 + 0.7 * cUp );
          outgoingLight += uCharRim.rgb * uCharRim.a * cRim * ( 0.35 + 0.65 * diffuseColor.rgb );
          outgoingLight += diffuseColor.rgb * uCharFill * ( 0.55 + 0.45 * cUp );
        }
        #include <opaque_fragment>`);
  };
  // three caches programs by the material's settings: this one differs from an undressed twin
  const key = mat.customProgramCacheKey ? mat.customProgramCacheKey.bind(mat) : null;
  mat.customProgramCacheKey = () => `${key ? key() : ''}|charlook`;
  mat.needsUpdate = true;
}

// the soft shadow at a body's feet: one small texture, shared
let blobTex = null;
function blobTexture() {
  if (blobTex) return blobTex;
  const S = 64, cv = document.createElement('canvas');
  cv.width = cv.height = S;
  const g = cv.getContext('2d'), grad = g.createRadialGradient(S / 2, S / 2, 0, S / 2, S / 2, S / 2);
  grad.addColorStop(0, 'rgba(0,0,0,0.62)'); grad.addColorStop(0.55, 'rgba(0,0,0,0.3)'); grad.addColorStop(1, 'rgba(0,0,0,0)');
  g.fillStyle = grad; g.fillRect(0, 0, S, S);
  blobTex = new THREE.CanvasTexture(cv);
  return blobTex;
}
const blobGeo = new THREE.PlaneGeometry(1, 1).rotateX(-Math.PI / 2);

// radius: the body's footprint in its own units (a biped about 0.55)
export function addBlob(root, radius = 0.55) {
  if (!root || root.userData.blob || typeof document === 'undefined') return null;
  const m = new THREE.Mesh(blobGeo, new THREE.MeshBasicMaterial({ map: blobTexture(), transparent: true, depthWrite: false, fog: true, toneMapped: false,
    polygonOffset: true, polygonOffsetFactor: -2, polygonOffsetUnits: -2 }));
  m.name = 'char-blob';
  m.scale.setScalar(radius * 2.3);
  m.position.y = 0.03;
  m.renderOrder = 1;
  m.raycast = () => {};                  // never what a click lands on
  m.userData.keep = true;                // not part of the body (fades, tints, gear passes skip it)
  root.add(m);
  root.userData.blob = m;
  return m;
}

// dress every material of a body; `blob`: its footprint radius (0 or null: no shadow at its feet)
export function charLook(root, { blob = 0.55 } = {}) {
  if (!root) return;
  root.traverse(o => {
    if (!o.isMesh || o.name === 'char-blob') return;
    const m = o.material;
    if (Array.isArray(m)) m.forEach(dress); else dress(m);
  });
  if (blob) addBlob(root, blob);
}
