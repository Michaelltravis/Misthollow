// The room you stand in, under the minimap: a compass of its ways out (a door shut, a lock — gold
// if you hold the key — a seal, a deathtrap in red, a zone's border, up and down), what kind of
// place it is (forest, city, deep water) and what holds here (peaceful, dark, indoors, no magic,
// no recall). A MUD tells these in "[ Exits: west ]" and in refusals ("A peaceful feeling
// overwhelms you"); the room's data has them all (map_system current_room). Also the place's
// bite: heat, cold and being under water tint the screen's edge, a held breath counts down in
// bubbles, shadow corruption fills a violet bar (web_hud.py vitals). No imports: the pure parts
// are tested in Node.

export const SPOKES = ['north', 'northeast', 'east', 'southeast', 'south', 'southwest', 'west', 'northwest'];
const SHORT = { north: 'N', northeast: 'NE', east: 'E', southeast: 'SE', south: 'S', southwest: 'SW', west: 'W', northwest: 'NW', up: 'Up', down: 'Down' };

// each way out of the room and how it stands; hidden ways stay unshown (they are found, not told)
export function compassSpokes(exits) {
  const out = {};
  for (const [dir, e] of Object.entries(exits || {})) {
    if (!e || e.hidden) continue;
    const d = e.door;
    let state = 'open';
    if (e.deathtrap) state = 'death';
    else if (d && (d.sealed || d.barricaded)) state = 'sealed';
    else if (d && d.locked && d.state !== 'open') state = 'locked';
    else if (d && d.state && d.state !== 'open' && !d.broken) state = 'door';
    else if (e.to_zone) state = 'zone';
    out[dir] = { state, key: !!(d && d.locked && d.has_key), door: d ? d.label || d.name : null, zone: e.to_zone || null };
  }
  return out;
}

// the compass in words, for its tooltip
export function exitsText(spokes) {
  const say = (dir, s) => {
    const what = { open: 'open', door: `${s.door || 'a door'}, shut`, locked: `${s.door || 'a door'}, locked${s.key ? ' (you have the key)' : ''}`,
      sealed: `${s.door || 'the way'}, barred`, death: 'DEATH lies that way', zone: `into ${s.zone}` }[s.state];
    return `${SHORT[dir] || dir}: ${what}`;
  };
  const order = [...SPOKES, 'up', 'down'];
  const dirs = Object.keys(spokes).sort((a, b) => order.indexOf(a) - order.indexOf(b));
  return dirs.length ? dirs.map(d => say(d, spokes[d])).join('\n') : 'No way out that you can see';
}

// what kind of place: the sector's icon and words
export function sectorOf(sector) {
  return {
    inside: { icon: 'house', label: 'Indoors' }, city: { icon: 'banner', label: 'City streets' },
    field: { icon: 'leaf', label: 'Open field' }, forest: { icon: 'leaf', label: 'Forest' },
    hills: { icon: 'rock', label: 'Hills' }, mountain: { icon: 'rock', label: 'Mountains' },
    water_swim: { icon: 'wave', label: 'Shallow water' }, water_noswim: { icon: 'boat', label: 'Deep water — a boat is needed' },
    underwater: { icon: 'bubble', label: 'Under water' }, flying: { icon: 'feather', label: 'Open air' },
    desert: { icon: 'sun', label: 'Desert' }, swamp: { icon: 'drop', label: 'Swamp' }, dungeon: { icon: 'crack', label: 'Dungeon' },
  }[sector] || null;
}

// what holds in this room, as small badges: {icon, label, off} (off: struck through, a thing you can't do)
export function roomBadges(room) {
  if (!room) return [];
  const f = new Set(room.flags || []);
  const out = [];
  if (f.has('peaceful') || f.has('safe')) out.push({ icon: 'dove', label: 'Peaceful — no fighting here' });
  if (f.has('dark')) out.push({ icon: 'eye', label: 'Dark — bring a light', off: true });
  if (f.has('no_magic')) out.push({ icon: 'rune', label: 'No magic works here', off: true });
  if (f.has('no_recall')) out.push({ icon: 'scroll', label: 'Recall does not work here', off: true });
  if (f.has('indoors') && room.sector !== 'inside') out.push({ icon: 'house', label: 'Under a roof' });
  return out;
}

// the place's bite: what tints the screen's edge
export function envOf(room, weather) {
  const env = (room && room.env) || {};
  const sector = room && room.sector;
  const flags = new Set((room && room.flags) || []);
  const outdoors = !flags.has('indoors') && sector !== 'inside';
  const t = weather && weather.temperature != null ? Number(weather.temperature) : null;
  const snowing = weather && (weather.sky === 'snowy' || weather.precipitation === 'snow');
  return {
    under: sector === 'underwater',
    hot: !!(env.burning || env.fire) || (outdoors && t != null && t >= 95),
    cold: !!env.frozen || (outdoors && ((t != null && t <= 25) || !!snowing)),
  };
}

// the bubbles of a held breath: [{full}] (null when breathing freely)
export function breathBubbles(b) {
  if (!b || !b.max) return null;
  return Array.from({ length: b.max }, (_, i) => ({ full: i < b.left }));
}

const RAD = 15, CX = 18, CY = 18;
const AT = dir => { const i = SPOKES.indexOf(dir); const a = i * Math.PI / 4; return { x: CX + Math.sin(a) * RAD, y: CY - Math.cos(a) * RAD, a }; };

// the card under the minimap (el: .mm-card); icon(name, opts) gives an image URL (icons.js uiIcon)
export function createRoomCard(el, { icon } = {}) {
  if (!el) return { update() {}, ping() {} };
  const spokes = SPOKES.map(d => {
    const p = AT(d);
    return `<g class="cp-spoke" data-dir="${d}"><line x1="${CX}" y1="${CY}" x2="${p.x.toFixed(1)}" y2="${p.y.toFixed(1)}"/><circle cx="${p.x.toFixed(1)}" cy="${p.y.toFixed(1)}" r="2.6"/></g>`;
  }).join('');
  el.insertAdjacentHTML('afterbegin', `<svg class="mm-compass" viewBox="0 0 36 36" width="36" height="36">
      <circle class="cp-ring" cx="${CX}" cy="${CY}" r="${RAD + 1.5}"/>${spokes}
      <g class="cp-spoke cp-vert" data-dir="up"><path d="M33,4 l3,4 h-6z"/></g>
      <g class="cp-spoke cp-vert" data-dir="down"><path d="M33,32 l3,-4 h-6z"/></g>
      <circle class="cp-hub" cx="${CX}" cy="${CY}" r="2.4"/><text class="cp-n" x="${CX}" y="5.2">N</text>
      <g class="cp-locks"></g>
    </svg>`);
  const svg = el.querySelector('.mm-compass');
  const badges = el.querySelector('.mm-badges');
  const locks = svg.querySelector('.cp-locks');
  let lastSig = '';
  return {
    update(room) {
      if (!room) return;
      const sp = compassSpokes(room.exits);
      const sig = JSON.stringify([room.vnum, sp, room.flags, room.sector]);
      if (sig === lastSig) return;
      lastSig = sig;
      for (const g of svg.querySelectorAll('.cp-spoke')) {
        const s = sp[g.dataset.dir];
        g.dataset.state = s ? s.state : 'none';
        g.classList.toggle('key', !!(s && s.key));
      }
      locks.innerHTML = '';
      if (icon) {
        for (const [dir, s] of Object.entries(sp)) {
          if (s.state !== 'locked' || !SPOKES.includes(dir)) continue;
          const p = AT(dir);
          locks.insertAdjacentHTML('beforeend', `<image href="${icon('padlock', { size: 32, color: s.key ? '#ffd36a' : '#ff8a6a', glow: 'rgba(0,0,0,.8)' })}" x="${(p.x - 4).toFixed(1)}" y="${(p.y - 4).toFixed(1)}" width="8" height="8"/>`);
        }
      }
      svg.dataset.tipTitle = 'Ways out';
      svg.dataset.tipSub = exitsText(sp);
      if (badges) {
        const sec = sectorOf(room.sector);
        const all = [...(sec ? [{ ...sec, sector: true }] : []), ...roomBadges(room)];
        badges.innerHTML = all.map(b => `<span class="mm-badge${b.off ? ' off' : ''}${b.sector ? ' sector' : ''}" data-tip-title="${b.label.replace(/"/g, '&quot;')}">`
          + `${icon ? `<img alt="" src="${icon(b.icon, { size: 32 })}">` : ''}</span>`).join('');
      }
    },
    // something heard that way (ambient.js presence): its spoke flares red for a moment
    ping(dir) {
      const g = svg.querySelector(`.cp-spoke[data-dir="${dir}"]`);
      if (!g) return;
      g.classList.remove('ping');
      void g.getBoundingClientRect();
      g.classList.add('ping');
      setTimeout(() => g.classList.remove('ping'), 2600);
    },
  };
}

// the place's bite on the screen: the edge tint, the held breath, the corruption
export function createEnvLayer({ html = document.documentElement, breath, corruption } = {}) {
  let lastBreath = '';
  return {
    update(room, weather) {
      const e = envOf(room, weather);
      html.classList.toggle('env-hot', e.hot && !e.under);
      html.classList.toggle('env-cold', e.cold && !e.under);
      html.classList.toggle('env-under', e.under);
    },
    body(p) {
      if (!p) return;
      const bub = breathBubbles(p.breath);
      if (breath) {
        const sig = JSON.stringify(bub);
        if (sig !== lastBreath) {
          lastBreath = sig;
          breath.classList.toggle('hidden', !bub);
          breath.innerHTML = bub ? bub.map(b => `<i class="${b.full ? 'full' : ''}"></i>`).join('') : '';
          breath.classList.toggle('low', !!(bub && p.breath.left <= 3));
          breath.dataset.tipTitle = 'Breath';
          breath.dataset.tipSub = bub ? `${p.breath.left} of ${p.breath.max} breaths left — find air` : '';
        }
      }
      if (corruption) {
        const c = Math.max(0, Math.min(100, Number(p.corruption) || 0));
        corruption.classList.toggle('hidden', !c);
        corruption.style.setProperty('--c', `${c}%`);
        corruption.dataset.tipTitle = 'Shadow corruption';
        corruption.dataset.tipSub = `${c}% — the light thins it`;
      }
    },
  };
}
