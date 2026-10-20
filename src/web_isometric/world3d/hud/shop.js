// A shopkeeper's window (right-click a shopkeeper → Shop): what they sell, and what they would
// give for what you carry, priced by the server (/shop). Buying and selling go out as the MUD's
// own commands: `buy <n>` (the item's place in the shop's list, which /shop keeps) and
// `sell <keyword>`; the window asks the server again after each.

const esc = s => String(s == null ? '' : s).replace(/[&<>"]/g, c => ({ '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;' }[c]));

// an item's kind as a player says it, not the world file's (`drinkcon` is a bottle or a skin)
const TYPE_NAMES = { drinkcon: 'drink', armor: 'armour', treasure: 'valuable', money: 'coin', fountain: 'fountain', other: 'goods', trash: 'junk', note: 'letter' };
export const typeName = t => (t ? TYPE_NAMES[t] || String(t).replace(/_/g, ' ') : '');

// the word the MUD finds a carried item by, numbered when several share it ("2.sword")
export function keywordFor(item, list) {
  const kw = String(item.name || item.short || 'item').toLowerCase().split(/\s+/).find(w => w.length > 1) || 'item';
  let n = 0;
  for (const it of list) {
    if (String(it.name || it.short || '').toLowerCase().split(/\s+/).includes(kw)) n++;
    if (it === item) break;
  }
  return n > 1 ? `${n}.${kw}` : kw;
}

// one tab's rows from a /shop answer: {item, price, ok, why, cmd}
export function shopRows(data, tab) {
  if (!data || !data.found) return [];
  const gold = data.gold || 0;
  if (tab === 'sell') {
    const list = data.sell || [];
    return list.map(it => ({
      item: it, price: it.price || 0, ok: !!it.will_buy,
      why: it.will_buy ? '' : `${data.keeper || 'The shopkeeper'} doesn't deal in that`,
      cmd: `sell ${keywordFor(it, list)}`,
    }));
  }
  return (data.buy || []).map((it, i) => ({
    item: it, price: it.price || 0, ok: gold >= (it.price || 0),
    why: gold >= (it.price || 0) ? '' : 'Not enough gold',
    cmd: `buy ${i + 1}`,
  }));
}

export function createShop(root, { fetchShop, send, icon, sound }) {
  const body = root.querySelector('.sh-body');
  let open = false, keeper = '', tab = 'buy', data = null, busy = false;
  root.querySelector('.sh-close').addEventListener('click', () => toggle(false));
  root.querySelectorAll('.sh-tab').forEach(b => b.addEventListener('click', () => { tab = b.dataset.tab; render(); }));

  function render() {
    if (!open) return;
    root.querySelectorAll('.sh-tab').forEach(b => b.classList.toggle('on', b.dataset.tab === tab));
    root.querySelector('.sh-who').textContent = data && data.found ? data.keeper : (keeper || 'Shop');
    if (!data) { body.innerHTML = '<span class="ch-none">Asking for prices…</span>'; return; }
    if (!data.found) { body.innerHTML = '<span class="ch-none">There is no shopkeeper here to trade with.</span>'; return; }
    const rows = shopRows(data, tab);
    const verb = tab === 'buy' ? 'Buy' : 'Sell';
    body.innerHTML = `<div class="tr-purse">${(data.gold || 0).toLocaleString()} gold</div>
      <div class="sb-list sh-list">${rows.map((r, i) => `<div class="sh-row ${r.ok ? '' : 'no'}" data-i="${i}">
        <div class="sh-ic"></div>
        <div class="sb-main"><div class="sb-name">${esc(r.item.short || r.item.name)}</div>
          <div class="sb-cost">${r.item.level ? `level ${r.item.level} · ` : ''}${esc(typeName(r.item.type))}${r.why ? ` · ${esc(r.why)}` : ''}</div></div>
        <div class="sh-price">${r.price.toLocaleString()}</div>
        <button class="tr-buy" data-i="${i}" ${r.ok ? '' : 'disabled'}>${verb}</button>
      </div>`).join('') || `<span class="ch-none">${tab === 'buy' ? 'Nothing for sale right now' : 'You carry nothing to sell'}</span>`}</div>`;
    body.querySelectorAll('.sh-row').forEach(el => {
      const r = rows[+el.dataset.i];
      el.querySelector('.sh-ic').appendChild(icon(r.item));
    });
    body.querySelectorAll('.tr-buy:not([disabled])').forEach(b => b.addEventListener('click', () => {
      if (busy) return;
      const r = rows[+b.dataset.i];
      busy = true;
      send(r.cmd);
      if (sound) sound.play('coins');
      setTimeout(() => { busy = false; refresh(); }, 450);
    }));
  }
  async function refresh() {
    try { data = await fetchShop(keeper); } catch (_) { data = { found: false }; }
    render();
  }
  function toggle(on = !open, name) {
    open = on;
    if (name !== undefined) keeper = name;
    root.classList.toggle('hidden', !open);
    if (open) { data = null; tab = 'buy'; render(); refresh(); }
  }
  return { toggle, refresh, get open() { return open; } };
}
