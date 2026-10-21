// The body under the player frame: hunger, thirst and stamina as thin meters that pulse when they
// run low, and how you are sitting, resting or asleep (click it to get up). A MUD says these in
// lines ("You are extremely hungry!", "You rest and begin to recuperate."); the server now sends
// the numbers too (web_hud.py vitals, and every map payload) and the lines come dimmed. No
// imports: the pure parts are tested in Node.

// when a need is low and when it is critical (Player.hunger_thirst_tick's warnings: hunger is
// counted in game hours of food, thirst in hours of water; stamina is the movement pool)
export const NEED = {
  hunger: { low: 48, crit: 24, label: 'Hunger', icon: 'bread', fed: 'Fed' },
  thirst: { low: 24, crit: 12, label: 'Thirst', icon: 'mug', fed: 'Quenched' },
  move: { lowPct: 0.25, critPct: 0.10, label: 'Stamina', icon: 'boot' },
};

export function needLevel(cur, max, kind) {
  const n = NEED[kind];
  const c = Number(cur) || 0, m = Math.max(1, Number(max) || 1);
  if (!n) return 'ok';
  if (n.lowPct != null) return c / m < n.critPct ? 'crit' : c / m < n.lowPct ? 'low' : 'ok';
  return c <= n.crit ? 'crit' : c <= n.low ? 'low' : 'ok';
}

// what getting up from a posture takes
export function postureAction(pos) {
  return pos === 'sleeping' ? 'wake' : pos === 'sitting' || pos === 'resting' ? 'stand' : null;
}

// a posture's icon and words; standing shows nothing
export function postureOf(pos) {
  return {
    sitting: { icon: 'seat', label: 'Sitting', sub: 'Click to stand up' },
    resting: { icon: 'fountain', label: 'Resting', sub: 'Recovering faster · click to stand up' },
    sleeping: { icon: 'zzz', label: 'Asleep', sub: 'Recovering fastest · click to wake' },
  }[pos] || null;
}

// the meters' fill (0..1) for each need, from the player block
export function meters(p) {
  if (!p) return [];
  return [
    { kind: 'hunger', cur: p.hunger, max: p.max_hunger, state: p.hunger_state },
    { kind: 'thirst', cur: p.thirst, max: p.max_thirst, state: p.thirst_state },
    { kind: 'move', cur: p.move, max: p.max_move },
  ].filter(m => m.cur != null && m.max != null)
    .map(m => ({ ...m, fill: Math.max(0, Math.min(1, m.cur / Math.max(1, m.max))), level: needLevel(m.cur, m.max, m.kind) }));
}

// the row itself, in `root` (#body-meters): icon(name) gives an image URL, send(cmd) a command
export function createBody(root, { icon, send } = {}) {
  if (!root) return { update() {} };
  root.innerHTML = '';
  const els = {};
  for (const kind of ['hunger', 'thirst', 'move']) {
    const n = NEED[kind];
    const el = document.createElement('div');
    el.className = `need need-${kind}`;
    el.innerHTML = `<img alt=""><span class="need-bar"><i></i></span>`;
    if (icon) el.querySelector('img').src = icon(n.icon);
    el.dataset.tipTitle = n.label;
    root.appendChild(el);
    els[kind] = el;
  }
  const post = document.createElement('button');
  post.className = 'posture hidden';
  post.innerHTML = '<img alt="">';
  root.appendChild(post);
  let pos = 'standing';
  post.addEventListener('click', () => { const a = postureAction(pos); if (a && send) send(a); });
  return {
    update(p) {
      if (!p) return;
      for (const m of meters(p)) {
        const el = els[m.kind];
        el.querySelector('i').style.width = `${(m.fill * 100).toFixed(1)}%`;
        el.dataset.level = m.level;
        const n = NEED[m.kind];
        el.dataset.tipSub = m.kind === 'move'
          ? `${m.cur} / ${m.max} — every step and swing draws on it`
          : `${m.state || (m.level === 'ok' ? n.fed : m.level === 'low' ? 'Low' : 'Critical')} · ${m.cur} of ${m.max} hours`;
      }
      pos = p.position || 'standing';
      const look = postureOf(pos);
      post.classList.toggle('hidden', !look);
      if (look) {
        if (icon && post.dataset.icon !== look.icon) { post.querySelector('img').src = icon(look.icon); post.dataset.icon = look.icon; }
        post.dataset.tipTitle = look.label;
        post.dataset.tipSub = look.sub;
        post.dataset.pos = pos;
      }
    },
  };
}
