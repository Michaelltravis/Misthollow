// Legend (G): your prestige specialisation (at level 50, choose one: `specialize <class>`) and
// the server's leaderboards, with your own place. For a warrior, also the war doctrine and the
// evolution of their abilities by use (`swear <doctrine>`, `evolve <ability>`). Data: /legend,
// /doctrine.
import { netNote } from './netfail.js';

const esc = s => String(s == null ? '' : s).replace(/[&<>"]/g, c => ({ '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;' }[c]));
const cap = s => s ? s[0].toUpperCase() + s.slice(1) : s;

// each warrior ability: its uses, its evolution now, and the next one under the sworn doctrine
export function evolutionRows(doc) {
  if (!doc || !doc.doctrine) return [];
  return (doc.abilities || []).map(a => {
    const ths = Object.keys(a.thresholds || {}).map(Number).sort((x, y) => x - y);
    const taken = ths.filter(t => {
      const pair = (a.thresholds[String(t)] || {})[doc.doctrine];
      return pair && a.evolved && pair[0] === a.evolved;
    });
    const doneUpTo = taken.length ? Math.max(...taken) : 0;
    const at = ths.find(t => t > doneUpTo);
    const pair = at != null ? (a.thresholds[String(at)] || {})[doc.doctrine] : null;
    return { ability: a.ability, usage: a.usage || 0, current: a.evolved || null,
      next: pair ? { at, name: pair[0], description: pair[1] } : null,
      ready: !!(pair && (a.usage || 0) >= at) };
  });
}

export function createLegend(root, { fetchLegend, fetchDoctrine, send, isWarrior }) {
  const body = root.querySelector('.lg-body');
  let open = false, tab = 'prestige', data = null, doc = null;
  root.querySelector('.lg-close').addEventListener('click', () => toggle(false));
  root.querySelectorAll('.lg-tab').forEach(b => b.addEventListener('click', () => { tab = b.dataset.tab; render(); }));
  const act = cmd => { send(cmd); setTimeout(refresh, 600); };
  function render() {
    if (!open) return;
    root.querySelectorAll('.lg-tab').forEach(b => { b.classList.toggle('on', b.dataset.tab === tab); if (b.dataset.tab === 'doctrine') b.hidden = !isWarrior(); });
    if (!data) { body.innerHTML = '<span class="ch-none">Reading the chronicles…</span>'; return; }
    if (tab === 'prestige') {
      const p = data.prestige || { options: [] };
      body.innerHTML = p.current
        ? `<div class="tr-purse">You are a ${esc(p.current_name || p.current)}</div>`
        : `<div class="tr-purse">${p.eligible ? 'Choose your path: it is for good (a respec costs 50,000 gold)' : `At level 50 you choose a path (you are ${p.level})`}</div>`;
      body.innerHTML += (p.options || []).map(o => `<div class="al-ach ${p.current === o.key ? 'done' : ''}"><div class="sb-main">
          <div class="sb-name">${esc(o.name)} <span class="al-pts">${esc(o.theme)}</span></div>
          <div class="sb-cost">${esc(o.description)}</div>
          ${(o.abilities || []).map(a => `<div class="sb-cost">• <b>${esc(a.name)}</b> — ${esc(a.description)}</div>`).join('')}</div>
          ${p.eligible ? `<button class="tr-buy" data-cmd="specialize ${esc(o.key)}">Choose</button>` : ''}</div>`).join('');
    } else if (tab === 'boards') {
      const b = data.leaderboards || {};
      body.innerHTML = Object.entries(b).map(([cat, x]) => `<div class="tk-head">${esc(cap(cat))}${x.my_rank ? ` — you are #${x.my_rank} of ${x.total}` : ''}</div>
        ${(x.top || []).map((r, i) => `<div class="wh-row"><span class="wh-lvl">${i + 1}</span><span class="wh-name">${esc(r.name)}</span><span class="wh-what">${Number(r.value).toLocaleString()}</span></div>`).join('')}`).join('');
    } else {
      if (!doc) { body.innerHTML = '<span class="ch-none">…</span>'; return; }
      if (!doc.doctrine) {
        body.innerHTML = '<div class="tr-purse">Swear to a war doctrine: it shapes what Momentum gives you and how your abilities evolve</div>'
          + Object.entries(doc.doctrines || {}).map(([k, d]) => `<div class="al-ach"><div class="sb-main"><div class="sb-name">${esc(d.name)}</div>
            <div class="sb-cost">${esc(d.description)}</div><div class="sb-cost"><i>${esc(d.bonus)}</i></div></div>
            <button class="tr-buy" data-cmd="swear ${esc(k)}">Swear</button></div>`).join('');
      } else {
        const d = (doc.doctrines || {})[doc.doctrine] || {};
        body.innerHTML = `<div class="tr-purse">${esc(d.name || doc.doctrine)} · Momentum ${doc.momentum}/10</div>`
          + evolutionRows(doc).map(r => `<div class="al-ach ${r.next ? '' : 'done'}"><div class="sb-main">
            <div class="sb-name">${esc(cap(r.ability))}${r.current ? ` <span class="al-pts">${esc(r.current.replace(/_/g, ' '))}</span>` : ''}</div>
            ${r.next ? `<div class="sb-cost">Next: <b>${esc(r.next.name.replace(/_/g, ' '))}</b> — ${esc(r.next.description)}</div>
              <div class="al-bar"><i style="width:${Math.min(100, Math.round(100 * r.usage / r.next.at))}%"></i><span>${r.usage}/${r.next.at} uses</span></div>`
              : '<div class="sb-cost">Fully evolved</div>'}</div>
            ${r.ready ? `<button class="tr-buy" data-cmd="evolve ${esc(r.ability)}">Evolve</button>` : ''}</div>`).join('');
      }
    }
    body.querySelectorAll('[data-cmd]').forEach(btn => btn.addEventListener('click', () => act(btn.dataset.cmd)));
  }
  async function refresh() {
    let failed = false;
    try { data = await fetchLegend(); } catch (_) { data = {}; failed = true; }
    if (isWarrior()) { try { doc = await fetchDoctrine(); } catch (_) { doc = null; } }
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
