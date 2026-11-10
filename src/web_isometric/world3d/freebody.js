// What a made body holds on the graphics card, and giving it back.
// A creature built from a recipe (kin.js makeKin) has geometries and materials that are its alone
// (its parts merged into its own buffers, its materials its own copies so a hit flash lights it and
// no other). When it is cleared from the scene those must be disposed of, or a long walk through a
// busy zone leaves every creature ever seen in memory. A body loaded from a file shares its buffers
// with every other of its kind and is never marked: freeBody leaves it alone. Pure (no three.js).

// mark `root` as owning every geometry and material under it now (what is added to it later, a ring
// or a nameplate, is not its own); returns how many
export function ownBody(root) {
  const owned = new Set();
  root.traverse(o => {
    if (o.geometry && o.geometry.dispose) owned.add(o.geometry);
    for (const m of Array.isArray(o.material) ? o.material : o.material ? [o.material] : []) if (m.dispose) owned.add(m);
  });
  root.userData.owned = owned;
  return owned.size;
}

// dispose of what `root` owns (once: a second call frees nothing); returns how many were freed
export function freeBody(root) {
  const owned = root && root.userData && root.userData.owned;
  if (!owned) return 0;
  root.userData.owned = null;
  for (const x of owned) x.dispose();
  return owned.size;
}
