// The stable (U): your mounts (Mount / Dismount), the ones a stable sells (Buy, at a stable),
// and your pets and companions with their health (Dismiss). Data: /stable.

const esc = s => String(s == null ? '' : s).replace(/[&<>"]/g, c => ({ '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;' }[c]));
const bar = (hp, max) => `<div class="al-bar"><i style="width:${max ? Math.round(100 * Math.max(0, hp) / max) : 0}%"></i><span>${hp}/${max}</span></div>`;

// a mount for sale: its description, and its speed and flight where the description doesn't say
// them already ("... +35% speed." twice over)
export function forSale(x) {
  const d = String(x.description || '').trim();
  const more = [];
  if (!/%\s*speed/i.test(d)) more.push(`+${x.travel ?? 0}% speed`);
  if (x.can_fly && !/\bfl(?:y|ies)\b/i.test(d)) more.push('flies');
  return [d, ...more].filter(Boolean).join(' · ');
}

export function createStable(root, { fetchStable, send }) {
  const body = root.querySelector('.st-body');
  let open = false, data = null;
  root.querySelector('.st-close').addEventListener('click', () => toggle(false));
  const act = cmd => { send(cmd); setTimeout(refresh, 600); };
  function render() {
    if (!open) return;
    if (!data) { body.innerHTML = '<span class="ch-none">Calling your animals…</span>'; return; }
    const m = data.mounts || { owned: [], purchasable: [] };
    const owned = (m.owned || []).map(x => `<div class="sh-row">
        <div class="sb-main"><div class="sb-name">${esc(x.name)}${x.active ? ' <span class="al-pts">riding</span>' : ''}</div>
          <div class="sb-cost">+${x.travel ?? 0}% speed${x.can_fly ? ' · flies' : ''}${x.combat_ok ? ' · fights' : ''} · loyalty ${x.loyalty}</div></div>
        ${x.active ? '<button class="tr-buy" data-cmd="dismount">Dismount</button>' : `<button class="tr-buy" data-cmd="mount ${esc(x.key)}">Mount</button>`}</div>`).join('');
    const buy = (m.purchasable || []).map(x => `<div class="sh-row ${x.afford && m.at_stable ? '' : 'no'}">
        <div class="sb-main"><div class="sb-name">${esc(x.name)}</div><div class="sb-cost">${esc(forSale(x))}</div></div>
        <div class="sh-price">${(x.cost || 0).toLocaleString()}</div>
        <button class="tr-buy" data-cmd="stable buy ${esc(x.key)}" ${x.afford && m.at_stable ? '' : 'disabled'}>Buy</button></div>`).join('');
    const pets = [...(data.pets || []).map(p => ({ ...p, kind: p.type })), ...(data.companions || []).map(c => ({ ...c, kind: c.role }))]
      .map(p => `<div class="sh-row"><div class="sb-main"><div class="sb-name">${esc(p.name)} <span class="al-pts">level ${p.level} ${esc(p.kind || '')}</span></div>
        ${bar(p.hp, p.maxHp)}</div><button class="tr-buy" data-cmd="dismiss ${esc(String(p.name).split(/\s+/).pop())}">Dismiss</button></div>`).join('');
    body.innerHTML = `<div class="tk-head">Your mounts</div>${owned || '<span class="ch-none">None yet.</span>'}
      <div class="tk-head">For sale${m.at_stable ? '' : ' — visit a stable to buy'}</div>${buy || '<span class="ch-none">Nothing for sale.</span>'}
      <div class="tk-head">Pets and companions</div>${pets || '<span class="ch-none">No one follows you.</span>'}`;
    body.querySelectorAll('[data-cmd]:not([disabled])').forEach(b => b.addEventListener('click', () => act(b.dataset.cmd)));
  }
  async function refresh() {
    try { data = await fetchStable(); } catch (_) { data = {}; }
    render();
  }
  function toggle(on = !open) {
    open = on;
    root.classList.toggle('hidden', !open);
    if (open) { data = null; render(); refresh(); }
  }
  return { toggle, get open() { return open; } };
}
