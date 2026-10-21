// What waits for you and what is going on, at the foot of the minimap: an envelope with your
// unread mail (click: the Mail tab), and a chip for each world event — an invasion with its wave,
// double experience, a world boss, wild weather — counting down. A MUD shouts these once in the
// stream ("You have 2 unread mail messages!", "⚔️ INVASION!"); the server sends them as data now
// (web_hud.py: the body's mail count, world_event) and the lines come dimmed. No imports: the
// pure parts are tested in Node.

// seconds left, short: 1h 5m, 12m, 45s
export function fmtLeft(s) {
  const n = Math.max(0, Math.floor(Number(s) || 0));
  if (n >= 3600) return `${Math.floor(n / 3600)}h ${Math.floor((n % 3600) / 60)}m`;
  if (n >= 60) return `${Math.floor(n / 60)}m`;
  return `${n}s`;
}

// a world event's chip: its icon, words and what is left, `since` seconds after it was told
export function chipOf(e, since = 0) {
  const icon = { invasion: 'banner', world_boss: 'skull', treasure_hunt: 'map', double_xp: 'star', weather: 'bolt' }[e.kind] || 'banner';
  const left = Math.max(0, (Number(e.left) || 0) - since);
  const wave = e.waves ? ` · wave ${e.wave || 0}/${e.waves}` : '';
  return { icon, left, text: fmtLeft(left), title: e.label || e.kind, sub: `${e.where ? `${e.where}${wave} · ` : wave ? `${wave.slice(3)} · ` : ''}${fmtLeft(left)} left` };
}

// a quest step as a toast: "Rats slain 3/5", "Rats slain — done!"
export function progressText(e) {
  if (!e) return '';
  const what = e.objective || e.quest || 'Quest';
  return e.done ? `${what} — done!` : `${what} ${e.current}/${e.required}`;
}

// the row, in `root` (.mm-alerts): icon(name) gives an image URL; openMail() shows the mailbox
export function createAlerts(root, { icon, openMail } = {}) {
  if (!root) return { setMail() {}, setEvents() {} };
  root.innerHTML = '<button class="al-mail hidden"><img alt=""><b></b></button><span class="al-events"></span>';
  const mail = root.querySelector('.al-mail'), evs = root.querySelector('.al-events');
  if (icon) mail.querySelector('img').src = icon('envelope');
  mail.addEventListener('click', () => openMail && openMail());
  let events = [], at = 0, timer = 0;
  function draw() {
    const since = (performance.now() - at) / 1000;
    const chips = events.map(e => chipOf(e, since)).filter(c => c.left > 0);
    evs.innerHTML = chips.map(c => `<span class="al-chip" data-tip-title="${esc(c.title)}" data-tip-sub="${esc(c.sub)}">`
      + `${icon ? `<img alt="" src="${icon(c.icon)}">` : ''}<em>${c.text}</em></span>`).join('');
    sync();
  }
  function sync() {
    const any = !mail.classList.contains('hidden') || evs.childElementCount > 0;
    root.classList.toggle('hidden', !any);
    if (events.length && !timer) timer = setInterval(draw, 1000);
    if (!events.length && timer) { clearInterval(timer); timer = 0; }
  }
  return {
    setMail(n) {
      const k = Math.max(0, Number(n) || 0);
      mail.classList.toggle('hidden', !k);
      mail.querySelector('b').textContent = k > 9 ? '9+' : String(k);
      mail.dataset.tipTitle = 'Mail';
      mail.dataset.tipSub = `${k} unread — click to open your mailbox`;
      sync();
    },
    setEvents(list) {
      events = Array.isArray(list) ? list : [];
      at = performance.now();
      draw();
    },
  };
}

const esc = s => String(s == null ? '' : s).replace(/[&<>"]/g, c => ({ '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;' }[c]));
