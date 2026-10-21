// Bank, mail and storage (B): your gold in the bank (Deposit / Withdraw, at a bank), your mail
// (Delete; Write puts `mail send` on the command line), and what you keep at an inn (Retrieve
// there; drop things in with `store`). Data: /services.

const esc = s => String(s == null ? '' : s).replace(/[&<>"]/g, c => ({ '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;' }[c]));

// a typed amount of gold, made sane: a whole number from 1 up to what there is, or 'all'
export function goldAmount(text, max) {
  const t = String(text || '').trim().toLowerCase();
  if (t === 'all') return max > 0 ? 'all' : null;
  const n = Math.floor(Number(t.replace(/[,\s]/g, '')));
  return Number.isFinite(n) && n >= 1 && n <= max ? n : null;
}

export function createServices(root, { fetchServices, send, prefill }) {
  const body = root.querySelector('.sv-body');
  let open = false, tab = 'bank', data = null;
  root.querySelector('.sv-close').addEventListener('click', () => toggle(false));
  root.querySelectorAll('.sv-tab').forEach(b => b.addEventListener('click', () => { tab = b.dataset.tab; render(); }));
  const act = cmd => { send(cmd); setTimeout(refresh, 600); };
  function render() {
    if (!open) return;
    root.querySelectorAll('.sv-tab').forEach(b => b.classList.toggle('on', b.dataset.tab === tab));
    if (!data) { body.innerHTML = '<span class="ch-none">Opening the ledger…</span>'; return; }
    if (tab === 'bank') {
      const b = data.bank || {};
      body.innerHTML = `<div class="tr-purse">${(b.balance || 0).toLocaleString()} gold in the bank · ${(b.on_hand || 0).toLocaleString()} on hand</div>
        ${b.at_bank ? `<div class="sv-row"><input class="sv-amt" placeholder="how much, or all" aria-label="Amount">
          <button class="tr-buy" data-op="deposit">Deposit</button><button class="tr-buy" data-op="withdraw">Withdraw</button></div>
          <div class="sv-why"></div>` : '<span class="ch-none">Deposits and withdrawals are made at a bank.</span>'}`;
      body.querySelectorAll('[data-op]').forEach(btn => btn.addEventListener('click', () => {
        const max = btn.dataset.op === 'deposit' ? (b.on_hand || 0) : (b.balance || 0);
        const amt = goldAmount(body.querySelector('.sv-amt').value, max);
        if (amt == null) { body.querySelector('.sv-why').textContent = `Between 1 and ${max.toLocaleString()}, or "all".`; return; }
        act(`${btn.dataset.op} ${amt}`);
      }));
      const inp = body.querySelector('.sv-amt');
      if (inp) inp.addEventListener('keydown', e => e.stopPropagation());
    } else if (tab === 'mail') {
      const m = data.mail || { messages: [] };
      body.innerHTML = `<div class="tr-purse">${m.unread || 0} unread · <button class="tr-buy" data-write="1">Write</button></div>
        ${(m.messages || []).map(x => `<div class="al-ach ${x.read ? 'done' : ''}"><div class="sb-main">
          <div class="sb-name">${esc(x.sender)} <span class="al-pts">${esc(x.ts)}</span></div>
          <div class="sb-cost sv-body-text">${esc(x.body)}</div></div>
          <button class="tr-buy" data-del="${esc(x.id)}">Delete</button></div>`).join('') || '<span class="ch-none">No mail.</span>'}`;
      body.querySelectorAll('[data-del]').forEach(btn => btn.addEventListener('click', () => act(`mail delete ${btn.dataset.del}`)));
      const w = body.querySelector('[data-write]');
      if (w) w.addEventListener('click', () => { toggle(false); prefill('mail send '); });
    } else {
      const s = data.storage || { items: [] };
      body.innerHTML = `<div class="tr-purse">${s.items.length} item${s.items.length === 1 ? '' : 's'} kept${s.location ? ` at ${esc(s.location)}` : ''}</div>
        ${s.items.map(it => `<div class="sh-row"><div class="sb-main"><div class="sb-name">${esc(it.name)}</div></div>
          ${s.at_inn ? `<button class="tr-buy" data-get="${esc(String(it.name).split(/\s+/).pop())}">Retrieve</button>` : ''}</div>`).join('')
          || '<span class="ch-none">Nothing kept. At an inn, `store <item>` puts something away.</span>'}
        ${s.at_inn ? '' : '<div class="sv-why">Retrieve things at an inn.</div>'}`;
      body.querySelectorAll('[data-get]').forEach(btn => btn.addEventListener('click', () => act(`retrieve ${btn.dataset.get}`)));
    }
  }
  async function refresh() {
    try { data = await fetchServices(); } catch (_) { data = {}; }
    render();
  }
  function toggle(on = !open) {
    open = on;
    root.classList.toggle('hidden', !open);
    if (open) { data = null; render(); refresh(); }
  }
  // open on one tab (the minimap's envelope: the mail)
  function show(t) { if (t) tab = t; if (open) render(); else toggle(true); }
  return { toggle, show, get open() { return open; } };
}
