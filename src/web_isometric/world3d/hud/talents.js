// Talents (N): your class's trees, tier by tier. A talent you can take now is lit; a click
// spends a point on it (`talents learn <id>`); the server keeps the rules (talents.py): a tier
// opens at five points spent in its tree for each tier below it, some talents need another
// first, and each has a top rank. Data: /talents. Warriors grow by doctrine instead.

const esc = s => String(s == null ? '' : s).replace(/[&<>"]/g, c => ({ '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;' }[c]));

// what each talent is to you now: 'max', 'learned' (has ranks, more to take), 'open' (you can
// take a rank), 'locked' (with why)
export function talentStates(data) {
  const free = (data && data.points_available) || 0;
  return ((data && data.trees) || []).map(tree => {
    const byId = new Map(tree.talents.map(t => [t.id, t]));
    const talents = tree.talents.map(t => {
      const need = (t.tier - 1) * 5;
      const missing = (t.requires || []).map(id => byId.get(id)).find(p => p && !p.rank);
      let state, why = '';
      if (t.rank >= t.max_rank) state = 'max';
      else if ((tree.points || 0) < need) { state = 'locked'; why = `${need} points in ${tree.name} first`; }
      else if (missing) { state = 'locked'; why = `needs ${missing.name} first`; }
      else if (free < 1) { state = t.rank ? 'learned' : 'locked'; why = 'no points to spend'; }
      else state = 'open';
      return { ...t, state, why };
    });
    const tiers = [...new Set(talents.map(t => t.tier))].sort((a, b) => a - b)
      .map(tier => ({ tier, talents: talents.filter(t => t.tier === tier) }));
    return { name: tree.name, description: tree.description, points: tree.points || 0, tiers };
  });
}

export function createTalents(root, { fetchTalents, send }) {
  const body = root.querySelector('.tl-body');
  let open = false, data = null, busy = false;
  root.querySelector('.tl-close').addEventListener('click', () => toggle(false));
  function render() {
    if (!open) return;
    if (!data) { body.innerHTML = '<span class="ch-none">Opening your talents…</span>'; return; }
    if (!data.has_trees) {
      body.innerHTML = `<span class="ch-none">${data.class === 'warrior'
        ? 'Warriors grow by their martial doctrine and by using their abilities: see the <b>Doctrine</b> page of your Legend (G).'
        : 'Your class has no talent trees.'}</span>`;
      return;
    }
    const trees = talentStates(data);
    body.innerHTML = `<div class="tl-purse">${data.points_available} point${data.points_available === 1 ? '' : 's'} to spend · ${data.points_total} earned</div>
      <div class="tl-trees">${trees.map(t => `<div class="tl-tree">
        <div class="tl-name">${esc(t.name)} <span>${t.points}</span></div>
        <div class="tl-desc">${esc(t.description)}</div>
        ${t.tiers.map(tier => `<div class="tl-tier"><span class="tl-tn">${tier.tier}</span>${tier.talents.map(x => `
          <button class="tl-talent ${x.state}" data-id="${esc(x.id)}" ${x.state === 'open' ? '' : 'disabled'}
            data-tip-title="${esc(x.name)} (${x.rank}/${x.max_rank})" data-tip-sub="${esc(x.description)}${x.why ? ' — ' + esc(x.why) : ''}">
            <b>${esc(x.name)}</b><i>${x.rank}/${x.max_rank}</i></button>`).join('')}</div>`).join('')}
      </div>`).join('')}</div>`;
    body.querySelectorAll('.tl-talent.open').forEach(b => b.addEventListener('click', () => {
      if (busy) return;
      busy = true;
      send(`talents learn ${b.dataset.id}`);
      setTimeout(async () => { busy = false; await refresh(); }, 500);
    }));
  }
  async function refresh() {
    try { data = await fetchTalents(); } catch (_) { data = { has_trees: false }; }
    render();
  }
  function toggle(on = !open) {
    open = on;
    root.classList.toggle('hidden', !open);
    if (open) { data = null; render(); refresh(); }
  }
  return { toggle, get open() { return open; } };
}
