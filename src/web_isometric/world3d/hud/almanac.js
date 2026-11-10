// The almanac (Y): your daily streak (the reward comes as you log in each day), achievements
// with their progress, the titles you have earned (Wear one: `title <name>`), collections and
// gear sets. Data: /almanac.
import { netNote } from './netfail.js';

const esc = s => String(s == null ? '' : s).replace(/[&<>"]/g, c => ({ '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;' }[c]));
const cap = s => s ? s[0].toUpperCase() + s.slice(1) : s;

// achievements by category, the nearest to done first (done ones last), each with its bar
export function achievementGroups(list, { done = true } = {}) {
  const groups = new Map();
  for (const a of list || []) {
    if (!done && a.unlocked) continue;
    const pct = a.unlocked ? 1 : a.target ? Math.min(1, (a.progress || 0) / a.target) : 0;
    const g = groups.get(a.category || 'other') || [];
    g.push({ ...a, pct });
    groups.set(a.category || 'other', g);
  }
  return [...groups.entries()].sort((x, y) => x[0].localeCompare(y[0]))
    .map(([category, rows]) => ({ category, rows: rows.sort((a, b) => (a.unlocked - b.unlocked) || b.pct - a.pct || a.name.localeCompare(b.name)) }));
}

const rewardText = r => !r ? '' : typeof r === 'string' ? r
  : [r.gold && `${r.gold} gold`, r.exp && `${r.exp} xp`, r.item_name, r.title && `title “${r.title}”`].filter(Boolean).join(', ');

export function createAlmanac(root, { fetchAlmanac, send, prefill }) {
  const body = root.querySelector('.al-body');
  let open = false, tab = 'daily', data = null, showDone = true;
  root.querySelector('.al-close').addEventListener('click', () => toggle(false));
  root.querySelectorAll('.al-tab').forEach(b => b.addEventListener('click', () => { tab = b.dataset.tab; render(); }));
  function render() {
    if (!open) return;
    root.querySelectorAll('.al-tab').forEach(b => b.classList.toggle('on', b.dataset.tab === tab));
    if (!data) { body.innerHTML = '<span class="ch-none">Opening the almanac…</span>'; return; }
    if (tab === 'daily') {
      const d = data.daily || {};
      body.innerHTML = `<div class="al-streak">${d.streak || 0}-day streak · ${d.total_days || 0} days in all</div>
        <div class="al-week">${[1, 2, 3, 4, 5, 6, 7].map(n => `<span class="al-day ${n < d.streak_day || (n === d.streak_day && d.claimed_today) ? 'got' : ''} ${n === d.streak_day ? 'today' : ''}">${n}</span>`).join('')}</div>
        <div class="al-line"><b>Today</b> ${esc(rewardText(d.today))} ${d.claimed_today ? '<i>(received)</i>' : '<i>(comes as you log in)</i>'}</div>
        <div class="al-line"><b>Tomorrow</b> ${esc(rewardText(d.next))}</div>
        ${d.next_milestone ? `<div class="al-line"><b>Day ${d.next_milestone.day}</b> ${esc(d.next_milestone.name)}</div>` : ''}`;
    } else if (tab === 'achievements') {
      const a = data.achievements || {};
      const groups = achievementGroups(a.list, { done: showDone });
      body.innerHTML = `<div class="al-streak">${a.unlocked || 0} of ${a.total || 0} · ${a.points || 0} of ${a.max_points || 0} points
          <label class="al-toggle"><input type="checkbox" ${showDone ? 'checked' : ''}> show the ones you have</label></div>
        ${groups.map(g => `<div class="tk-head">${esc(cap(g.category))}</div>${g.rows.map(r => `
          <div class="al-ach ${r.unlocked ? 'done' : ''}">
            <div class="sb-main"><div class="sb-name">${esc(r.name)} <span class="al-pts">${r.points}</span></div>
              <div class="sb-cost">${esc(r.description)}${r.reward_title ? ` · title “${esc(r.reward_title)}”` : ''}</div>
              ${r.target && !r.unlocked ? `<div class="al-bar"><i style="width:${Math.round(r.pct * 100)}%"></i><span>${r.progress}/${r.target}</span></div>` : ''}
            </div></div>`).join('')}`).join('') || '<span class="ch-none">Nothing left to earn here.</span>'}`;
      const cb = body.querySelector('.al-toggle input');
      if (cb) cb.addEventListener('change', () => { showDone = cb.checked; render(); });
    } else if (tab === 'titles') {
      const t = data.titles || {};
      body.innerHTML = `<div class="al-streak">You are known as <b>${esc(t.current || '')}</b></div>
        ${(t.available || []).map(x => `<div class="al-title"><span>${esc(x)}</span><button class="tr-buy" data-title="${esc(x)}">Wear</button></div>`).join('')
          || '<span class="ch-none">Achievements earn titles; none yet.</span>'}
        <div class="al-title"><span><i>Your own words</i></span><button class="tr-buy" data-own="1">Write one</button></div>`;
      body.querySelectorAll('[data-title]').forEach(b => b.addEventListener('click', () => { send(`title ${b.dataset.title}`); setTimeout(refresh, 500); }));
      const own = body.querySelector('[data-own]');
      if (own) own.addEventListener('click', () => { toggle(false); prefill('title '); });     // type it on the command line
    } else {
      const colls = data.collections || [], sets = data.gear_sets || [];
      body.innerHTML = `${colls.map(c => `<div class="al-ach ${c.have >= c.total ? 'done' : ''}"><div class="sb-main">
          <div class="sb-name">${esc(c.name)}</div><div class="sb-cost">${esc(c.description)}${c.reward ? ` · ${esc(rewardText(c.reward))}` : ''}</div>
          <div class="al-bar"><i style="width:${c.total ? Math.round(100 * c.have / c.total) : 0}%"></i><span>${c.have}/${c.total}</span></div></div></div>`).join('')}
        ${sets.length ? `<div class="tk-head">Gear sets</div>${sets.map(s => `<div class="al-ach"><div class="sb-main">
          <div class="sb-name">${esc(s.name)} <span class="al-pts">${s.worn}/${s.total} worn</span></div>
          ${s.tiers.map(x => `<div class="sb-cost ${x.active ? 'on' : ''}">${x.need} pieces: ${esc(x.text)}</div>`).join('')}</div></div>`).join('')}` : ''}`
        || '<span class="ch-none">No collections yet.</span>';
    }
  }
  async function refresh() {
    let failed = false;
    try { data = await fetchAlmanac(); } catch (_) { data = {}; failed = true; }
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
