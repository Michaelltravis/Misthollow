// Talking to someone (right-click → Talk): a window with what they say, their dialogue's
// responses as buttons (`talk <npc> <n>`), the quests they offer (Accept: `quest accept <id>`)
// and the finished quests you can hand in (Turn in: `quest complete <id>`). The words are the
// server's own reply to `talk`; the offers and the finished quests come from /quests.

import { formatLines, noteKind, PROMPT_AT } from './frames.js';

const esc = s => String(s == null ? '' : s).replace(/[&<>"]/g, c => ({ '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;' }[c]));

// the instructions a telnet player needs and a window replaces with buttons; a quest's progress
// (the tracker shows it) and a tip that happens to come while they speak
const HINTS = [/^Use 'talk <npc> <number>' to respond\.?$/i, /^Use 'quest accept <quest_id>' to accept a quest\.?$/i,
  /^\(quest accept [\w-]+\)$/i, /^Responses:$/i, /^\[Hint\]/i, /^Quest Progress:/i, /^Tip:/i, /^💡/];

// what they say, drawn: their words as lines of the book, what happened to you (a reward, a quest
// step, the journal) as notes, the server's boxes as banners (frames.js)
export function talkHtml(says) {
  const parts = formatLines(says.map(t => ({ text: t, html: esc(t) })));
  const html = parts.map(o => {
    if (o.box) return o.html;
    const k = noteKind(o.text);
    return k ? `<p class="tx-note ${k}">${o.html}</p>` : `<p>${o.html}</p>`;
  }).join('');
  // (no word from them and nothing done, only a journal note: say so first)
  const spoke = parts.some(o => o.box || noteKind(o.text) !== 'journal');
  return spoke ? html : `<p class="tk-quiet">They have nothing to say.</p>${html}`;
}

// what a reply to `talk` says: {says: [lines], choices: [{n, text}], offers: [quest ids]}. Only
// what follows "You greet ..." is theirs (before it: your command's echo, the world going on);
// the prompt, the echo of a command and the offers' own lines (the window lists the offers) go.
export function readTalk(text) {
  // (a line's leading prompt goes, the rest stays: what they say can follow it on the same line)
  let lines = String(text || '').replace(/\r/g, '').split('\n').map(l => l.replace(PROMPT_AT, '').trim()).filter(Boolean);
  const greet = lines.findIndex(l => /^You greet /.test(l));
  if (greet >= 0) lines = lines.slice(greet + 1);
  const says = [], choices = [], offers = [];
  let inChoices = false;
  for (let i = 0; i < lines.length; i++) {
    const line = lines[i];
    const acc = line.match(/^\(quest accept ([\w-]+)\)$/i);
    if (acc) {
      offers.push(acc[1]);
      if (says.length && /\s[\u2014-]\s/.test(says[says.length - 1])) says.pop();     // "Name — what it is"
      continue;
    }
    if (/^Responses:$/i.test(line)) { inChoices = true; continue; }
    const ch = inChoices && line.match(/^(\d+)\.\s+(.+)$/);
    if (ch) { choices.push({ n: +ch[1], text: ch[2] }); continue; }
    if (HINTS.some(re => re.test(line)) || /^> /.test(line) || /^\d+\/\d+hp\b/.test(line) || /has quests for you:$/.test(line)) continue;
    inChoices = false;
    says.push(line);
  }
  return { says, choices, offers };
}

// the quests to show for this person, from a /quests answer: what they offer, and what you
// have finished (handed in to whoever gave it; the server says if it is the wrong person)
export function talkQuests(q, name) {
  const lower = String(name || '').toLowerCase();
  const giver = ((q && q.givers) || []).find(g => String(g.name || '').toLowerCase() === lower) || null;
  const done = ((q && q.active) || []).filter(a => a.complete && a.id && !String(a.id).startsWith('marquee'));
  return { offers: giver ? giver.offers : [], done };
}

export function createTalk(root, { send, listen, fetchQuests, sound }) {
  const body = root.querySelector('.tk-body');
  let open = false, who = '', kw = '', reply = { says: [], choices: [], offers: [] }, quests = { offers: [], done: [] };
  let waiting = false;
  root.querySelector('.tk-close').addEventListener('click', () => toggle(false));

  // send a line and gather what the server says back for a moment
  function ask(line, ms = 1100) {
    waiting = true; render();
    let text = '';
    const off = listen(t => { text += t + '\n'; });
    send(line);
    setTimeout(async () => {
      off();
      waiting = false;
      const r = readTalk(text);
      if (r.says.length || r.choices.length) reply = r;
      render();
      await refreshQuests();
    }, ms);
  }
  async function refreshQuests() {
    try { quests = talkQuests(await fetchQuests(), who); } catch (_) { quests = { offers: [], done: [] }; }
    render();
  }
  function render() {
    if (!open) return;
    root.querySelector('.tk-who').textContent = who || 'Conversation';
    const words = reply.says.length ? talkHtml(reply.says) : `<p class="tk-quiet">${waiting ? '…' : 'They have nothing to say.'}</p>`;
    const choices = reply.choices.map(c => `<button class="tk-choice" data-n="${c.n}">${esc(c.text)}</button>`).join('');
    const offers = quests.offers.map(o => `<div class="tk-quest">
        <div class="sb-main"><div class="sb-name">${esc(o.name)}</div><div class="sb-cost">${esc(o.description || '')}</div></div>
        <button class="tr-buy" data-accept="${esc(o.id)}">Accept</button></div>`).join('');
    const done = quests.done.map(d => `<div class="tk-quest done">
        <div class="sb-main"><div class="sb-name">${esc(d.name)}</div><div class="sb-cost">Finished — hand it in</div></div>
        <button class="tr-buy" data-turnin="${esc(d.id)}">Turn in</button></div>`).join('');
    body.innerHTML = `<div class="tk-words">${words}</div>
      ${choices ? `<div class="tk-choices">${choices}</div>` : ''}
      ${offers ? `<div class="tk-head">Quests offered</div>${offers}` : ''}
      ${done ? `<div class="tk-head">Ready to hand in</div>${done}` : ''}`;
    body.querySelectorAll('.tk-choice').forEach(b => b.addEventListener('click', () => ask(`talk ${kw} ${b.dataset.n}`)));
    body.querySelectorAll('[data-accept]').forEach(b => b.addEventListener('click', () => {
      send(`quest accept ${b.dataset.accept}`);
      if (sound) sound.play('quest_stage');
      setTimeout(refreshQuests, 500);
    }));
    body.querySelectorAll('[data-turnin]').forEach(b => b.addEventListener('click', () => {
      send(`quest complete ${b.dataset.turnin}`);
      if (sound) sound.play('quest_done');
      setTimeout(refreshQuests, 500);
    }));
  }
  function toggle(on = !open, name, keyword) {
    open = on;
    root.classList.toggle('hidden', !open);
    if (!open) return;
    who = name || who; kw = keyword || kw;
    reply = { says: [], choices: [], offers: [] }; quests = { offers: [], done: [] };
    ask(`talk ${kw}`);
  }
  return { toggle, get open() { return open; } };
}
