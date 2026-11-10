// The marquee quest on screen (marquee.py): the offer (a card with the trainer's words, what it
// teaches, how long it takes alone, Accept / Not now), the embark popup for the group members
// beside the one who accepts (Join / Decline, 30 s: those who join fix how hard it is), a
// tracker under the minimap (the stage, its objectives, where to go, who embarked) and a
// banner when a stage begins or the quest is done. Data: the quest_offer / quest_embark /
// quest_stage / quest_done events and the map payload's `quest` block.
const esc = s => String(s == null ? '' : s).replace(/[&<>"]/g, c => ({ '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;' }[c]));

export function createQuest({ card, embark, tracker, toast, onMark }) {
  let block = null, sig = '', embarkTimer = 0;

  // ---- the offer ----
  function offer(q) {
    if (!q) return;
    const r = q.reward || {};
    card.innerHTML = `<div class="qc-kicker">${esc(q.giver || 'Your trainer')} · a marquee quest</div>
      <div class="qc-title">${esc(q.name)}</div>
      <div class="qc-text">${esc(q.text)}</div>
      <div class="qc-reward"><span class="qc-lab">Teaches</span> <b>${esc(r.name || '')}</b><div class="qc-desc">${esc(r.desc || '')}</div></div>
      <div class="qc-meta">${esc(q.length || 'About two hours alone')} · ${q.party && q.party.length > 1
        ? `your group here (${q.party.length}) will be asked to join; it grows harder with each who does`
        : 'a group may join you when you accept; it grows harder with each who does'}</div>
      <div class="iv-b"><button class="accept">Accept</button><button class="decline">Not now</button></div>`;
    card.classList.remove('hidden');
    card.querySelector('.accept').addEventListener('click', () => { MH.sendCommand('marquee accept'); card.classList.add('hidden'); });
    card.querySelector('.decline').addEventListener('click', () => { card.classList.add('hidden'); });
  }

  // ---- a group member's quest: join it? ----
  function showEmbark(e) {
    embark.innerHTML = `<div class="iv-t">${esc(e.quest || 'A marquee quest')}</div>
      <div class="iv-who"><b>${esc(e.from)}</b> embarks on their ${esc(e.cls || '')} trial. Join them? Every member who joins makes it harder — and shares the glory.</div>
      <div class="iv-b"><button class="join">Join</button><button class="decline">Decline</button></div>
      <div class="lr-bar" style="--lr-ms:${(e.expires || 30) * 1000}ms"></div>`;
    embark.classList.remove('hidden');
    const close = () => { embark.classList.add('hidden'); clearTimeout(embarkTimer); };
    embark.querySelector('.join').addEventListener('click', () => { MH.sendCommand('marquee join'); close(); });
    embark.querySelector('.decline').addEventListener('click', () => { MH.sendCommand('marquee decline'); close(); });
    clearTimeout(embarkTimer);
    embarkTimer = setTimeout(close, (e.expires || 30) * 1000);
  }

  // ---- the tracker ----
  function render() {
    const b = block;
    tracker.classList.toggle('hidden', !b);
    if (onMark) onMark(b && b.where ? b.where.vnum : null);
    if (!b) { sig = ''; return; }
    const nsig = JSON.stringify(b);
    if (nsig === sig) return;
    sig = nsig;
    // the step in hand is one of the objectives: said once, in bold, where it stands in the list
    const same = (b.objectives || []).find(o => !o.done && o.text === b.title);
    const objs = (b.objectives || []).map(o => `<li class="${o.done ? 'done' : o === same ? 'now' : ''}">${esc(o.text)}${o.need > 1 ? ` <span>${o.have || 0}/${o.need}</span>
      <i class="qt-bar"><i style="width:${Math.min(100, Math.round(100 * (o.have || 0) / o.need))}%"></i></i>` : ''}</li>`).join('');
    const trial = b.trial && b.trial.state ? `<div class="qt-trial">${b.trial.state === 'ready' ? 'The way into the trial is open here'
      : b.trial.state === 'inside' ? (b.trial.boss ? 'The last foe waits' : `Wave ${b.trial.wave || 1} of ${b.trial.of || 3}`) : esc(b.trial.state)}</div>` : '';
    // holding the ritual: a draining bar for the seconds left
    const hold = b.ritual ? `<div class="qt-hold"><span>Hold!</span><i class="qt-bar"><i style="animation-duration:${b.ritual.left}s;width:${Math.round(100 * b.ritual.left / b.ritual.seconds)}%"></i></i></div>` : '';
    const act = b.action ? `<button class="btn qt-act" data-cmd="${esc(b.action.cmd)}">${esc(b.action.label)}</button>` : '';
    tracker.innerHTML = `<div class="qt-head"><span class="qt-star">★</span><span class="qt-name">${esc(b.name)}</span>
        <span class="qt-step">${b.stage || 0}/${b.of || 0}</span>${b.kind === 'quest' ? '<button class="qt-hide" title="Hide it from the tracker (your Journal, L, can show it again)">✕</button>' : ''}</div>
      ${same ? '' : `<div class="qt-title">${esc(b.title || '')}</div>`}
      ${b.text ? `<div class="qt-text">${esc(b.text)}</div>` : ''}
      ${objs ? `<ul class="qt-obj">${objs}</ul>` : ''}${trial}${hold}${act}
      <div class="qt-foot">${b.where && b.where.name ? `<span title="Marked on your minimap; the gold arrow by your feet points the way">◆ ${esc(b.where.name)}${b.where.steps ? ` · ${b.where.steps} room${b.where.steps > 1 ? 's' : ''}${b.where.dir ? ` ${esc(b.where.dir)}` : ''}` : b.where.steps === 0 ? ' · here' : ''}</span>` : ''}
        ${b.kind === 'quest' ? '' : b.party && b.party.length > 1 ? `<span title="It was made harder for each who embarked">⚔ ${b.party.length} embarked</span>` : '<span>alone</span>'}
        ${b.role === 'helper' ? `<span>helping ${esc(b.owner)}</span>` : ''}</div>`;
    // hide this quest from the tracker (the server picks the next one to follow: quest_guide.tracked)
    const hide = tracker.querySelector('.qt-hide');
    if (hide) hide.addEventListener('click', () => { MH.sendCommand(`webtrack hide ${b.id}`, false); block = null; render(); });
    const btn = tracker.querySelector('.qt-act');
    if (btn) btn.addEventListener('click', () => { MH.sendCommand(btn.dataset.cmd); btn.disabled = true; });
  }

  return {
    offer,
    showEmbark,
    update(b) { block = b && b.id ? b : null; render(); },
    stage(e) {
      if (e && e.title) toast(`${e.done ? '✔ ' : '★ '}${e.title}${e.text ? ` — ${e.text}` : ''}`);
    },
    done(e) {
      if (e && e.reward) toast(`★ ${e.quest || 'Quest'} complete — you learned ${e.reward}!`);
      else if (e && e.helper) toast(`★ ${e.quest || 'The trial'} — you stood with ${e.owner || 'them'} to the end`);
    },
    get active() { return block; },
  };
}
