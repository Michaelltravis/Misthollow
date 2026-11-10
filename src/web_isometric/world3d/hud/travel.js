// Travel (T): the waypoints you have found, what each costs, and Travel (`travel <waypoint>`).
// Data: /travel. A journey has a cooldown; the window says how long.
import { netNote } from './netfail.js';

const esc = s => String(s == null ? '' : s).replace(/[&<>"]/g, c => ({ '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;' }[c]));

// each waypoint: can you go there now, and if not why
export function travelRows(data) {
  if (!data) return [];
  const gold = data.gold || 0, cd = data.cooldown || 0;
  return (data.waypoints || []).map(w => ({
    ...w,
    ok: !w.here && cd <= 0 && gold >= (w.cost || 0),
    why: w.here ? 'you are here' : cd > 0 ? `ready in ${cd}s` : gold < (w.cost || 0) ? 'not enough gold' : '',
  }));
}

export function createTravel(root, { fetchTravel, send }) {
  const body = root.querySelector('.tv-body');
  let open = false, data = null;
  root.querySelector('.tv-close').addEventListener('click', () => toggle(false));
  function render() {
    if (!open) return;
    if (!data) { body.innerHTML = '<span class="ch-none">Reading the waystones…</span>'; return; }
    const rows = travelRows(data);
    body.innerHTML = `<div class="tr-purse">${(data.gold || 0).toLocaleString()} gold · ${data.discovered || 0} of ${data.total || 0} waypoints found</div>
      ${rows.map(r => `<div class="sh-row ${r.ok ? '' : 'no'}">
        <div class="sb-main"><div class="sb-name">${esc(r.name)}</div><div class="sb-cost">${r.why ? esc(r.why) : 'ready'}</div></div>
        <div class="sh-price">${(r.cost || 0).toLocaleString()}</div>
        <button class="tr-buy" data-key="${esc(r.key)}" ${r.ok ? '' : 'disabled'}>Travel</button></div>`).join('')
        || '<span class="ch-none">You have found no waypoints yet: touch a waystone as you pass one.</span>'}`;
    body.querySelectorAll('.tr-buy:not([disabled])').forEach(b => b.addEventListener('click', () => { send(`travel ${b.dataset.key}`); toggle(false); }));
  }
  async function refresh() {
    let failed = false;
    try { data = await fetchTravel(); } catch (_) { data = { waypoints: [] }; failed = true; }
    render();
    netNote(root, failed, refresh);
  }
  function toggle(on = !open) {
    open = on;
    root.classList.toggle('hidden', !open);
    if (open) { data = null; render(); refresh(); }
  }
  return { toggle, get open() { return open; } };
}
