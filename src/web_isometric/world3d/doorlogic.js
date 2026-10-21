// What a door offers the hero right now: the one-key prompt over it, and the full menu for a
// right-click. Pure (no THREE, no DOM) so it can be tested in Node.
//
// `info` is the zone's record for one side of a doorway, kept current by the server's map
// payloads and 'door' pushes: {label, closed, locked, broken, sealed, barricaded, has_key,
// can_pick, keyless, key_name, material, arcane, can_block, can_break}.
const cap = s => s ? s[0].toUpperCase() + s.slice(1) : s;

export function doorPrompt(info) {
  if (!info || info.broken) return null;
  const name = info.label || 'door';
  if (!info.closed) return { key: 'E', text: `Close the ${name}`, action: 'close', tone: 'dim' };
  if (info.sealed) return { key: null, text: `The ${name} is sealed by magic`, action: null, tone: 'locked' };
  if (info.barricaded) return { key: null, text: `The ${name} is barricaded`, action: null, tone: 'locked' };
  if (!info.locked) return { key: 'E', text: `Open the ${name}`, action: 'open', tone: 'open' };
  if (info.has_key || info.keyless) return { key: 'E', text: `Unlock the ${name}`, action: 'unlockopen', tone: 'key' };
  if (info.can_pick) return { key: 'E', text: 'Pick the lock', action: 'pick', tone: 'pick' };
  return { key: null, text: info.key_name ? `Locked — needs ${info.key_name}` : 'Locked — needs a key', action: null, tone: 'locked' };
}

// every door action that makes sense now, for the right-click menu
export function doorVerbs(info) {
  if (!info) return [];
  if (info.broken) return [{ label: `The ${info.label || 'door'} is broken`, action: null }];
  const out = [];
  const key = info.has_key || info.keyless;
  if (!info.closed) {
    out.push({ label: 'Close', action: 'close' });
  } else if (!info.locked) {
    out.push({ label: 'Open', action: 'open' });
    if (key) out.push({ label: 'Lock', action: 'lock' });
  } else {
    if (key) out.push({ label: 'Unlock and open', action: 'unlockopen' }, { label: 'Unlock', action: 'unlock' });
    if (info.can_pick) out.push({ label: 'Pick the lock', action: 'pick' });
    if (!key && !info.can_pick) out.push({ label: info.key_name ? `Needs ${info.key_name}` : 'Locked — needs a key', action: null });
  }
  if (info.closed) {
    out.push({ label: 'Knock', action: 'knock' });
    // what force can do against it (doors.py: an arcane door holds against any)
    if (info.arcane) out.push({ label: 'Bound by old magic: nothing breaks it', action: null });
    else {
      out.push({ label: info.material && info.material !== 'wood' ? `Bash it down (${info.material})` : 'Bash it down', action: 'bash' });
      if (info.can_break) out.push({ label: 'Break Door (spell)', action: 'break' });
    }
    if (info.can_block && !info.sealed) out.push({ label: 'Block Door (spell)', action: 'block' });
  }
  return out;
}

// where the prompt floats, room-local metres: the middle of the doorway on the room's edge,
// or the stairs for a trapdoor up or down
export function doorAnchor(L, dir, W, H) {
  const g = L.gaps && L.gaps[dir];
  if (g && (dir === 'north' || dir === 'south')) return { x: (g.x0 + g.x1 + 1) / 2, z: dir === 'north' ? 0.15 : H - 0.15 };
  if (g && (dir === 'east' || dir === 'west')) return { x: dir === 'west' ? 0.15 : W - 0.15, z: (g.y0 + g.y1 + 1) / 2 };
  if (dir === 'up' && L.stairsUp) return { x: L.stairsUp.x + 0.5, z: L.stairsUp.y + 0.5 };
  if (dir === 'down' && L.stairsDown) return { x: L.stairsDown.x + 0.5, z: L.stairsDown.y + 0.5 };
  return null;
}

export { cap };
