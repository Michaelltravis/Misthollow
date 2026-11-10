// Who is about (O): everyone online (/who) and who is here, in the hero's room (the map
// payload's `nearby` entry for it). A name opens the same menu a right-click on them would.
import { netNote } from './netfail.js';

const esc = s => String(s == null ? '' : s).replace(/[&<>"]/g, c => ({ '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;' }[c]));
const cap = s => s ? s[0].toUpperCase() + s.slice(1) : s;

// the online list, sorted: your group first, then by level
export function onlineRows(list, me) {
  const lower = String(me || '').toLowerCase();
  return (list || []).map(p => ({ ...p, self: String(p.name || '').toLowerCase() === lower }))
    .sort((a, b) => (b.self - a.self) || ((b.group ? 1 : 0) - (a.group ? 1 : 0)) || (b.level || 0) - (a.level || 0)
      || String(a.name).localeCompare(String(b.name)));
}

// who is in the hero's room, from a map payload: players, then creatures (hostile ones marked)
export function hereRows(payload, vnum, me) {
  const room = ((payload && payload.nearby) || []).find(r => r.vnum === vnum);
  if (!room) return [];
  const lower = String(me || '').toLowerCase();
  const players = (room.players || []).filter(p => String(p.name || '').toLowerCase() !== lower)
    .map(p => ({ kind: 'player', name: p.name, level: p.level, what: cap(p.char_class || '') }));
  const mobs = (room.mobs || []).map(m => {
    const hostile = !!(m.hostile || m.fighting || (Array.isArray(m.flags) && m.flags.includes('aggressive')));
    return {
      kind: 'mob', id: m.id, name: cap(m.name || 'someone'), level: m.level, hostile,
      what: m.shopkeeper ? 'shopkeeper' : m.trainer ? 'trainer' : m.quest ? 'has a quest' : hostile ? 'hostile' : '',
    };
  });
  return [...players, ...mobs];
}

export function createWho(root, { fetchWho, here, onPick }) {
  const body = root.querySelector('.wh-body');
  let open = false, tab = 'online', online = null, me = '';
  root.querySelector('.wh-close').addEventListener('click', () => toggle(false));
  root.querySelectorAll('.wh-tab').forEach(b => b.addEventListener('click', () => { tab = b.dataset.tab; render(); }));
  function render() {
    if (!open) return;
    root.querySelectorAll('.wh-tab').forEach(b => b.classList.toggle('on', b.dataset.tab === tab));
    if (tab === 'online') {
      if (!online) { body.innerHTML = '<span class="ch-none">Asking who is about…</span>'; return; }
      const rows = onlineRows(online.players, me);
      body.innerHTML = `<div class="wh-count">${rows.length} adventurer${rows.length === 1 ? '' : 's'} online</div>` + rows.map(p => `
        <div class="wh-row ${p.self ? 'self' : ''}" data-name="${esc(p.name)}">
          <span class="wh-lvl">${p.level || '?'}</span>
          <span class="wh-name">${esc(p.name)}${p.title ? ` <i>${esc(p.title)}</i>` : ''}</span>
          <span class="wh-what">${esc(cap(p.cls || ''))}${p.guild ? ` · &lt;${esc(p.guild)}&gt;` : ''}${p.group ? ' · your group' : ''}</span>
          <span class="wh-where">${esc(p.zone || '')}${p.idle_min ? ` · idle ${p.idle_min}m` : ''}</span>
        </div>`).join('');
    } else {
      const rows = here();
      body.innerHTML = rows.length ? rows.map((r, i) => `
        <div class="wh-row ${r.hostile ? 'hostile' : ''}" data-i="${i}">
          <span class="wh-lvl">${r.level || ''}</span>
          <span class="wh-name">${esc(r.name)}</span>
          <span class="wh-what">${esc(r.what)}</span>
        </div>`).join('') : '<span class="ch-none">No one else is here.</span>';
      body.querySelectorAll('.wh-row').forEach(el => el.addEventListener('click', e => onPick(rows[+el.dataset.i], e)));
    }
  }
  async function refresh() {
    let failed = false;
    try { online = await fetchWho(); } catch (_) { online = { players: [] }; failed = true; }
    render();
    netNote(root, failed, refresh);
  }
  function toggle(on = !open, name) {
    open = on;
    if (name) me = name;
    root.classList.toggle('hidden', !open);
    if (open) { online = null; render(); refresh(); }
  }
  return { toggle, render, get open() { return open; } };
}
