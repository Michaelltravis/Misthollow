// Help (H): the controls of /play, and a search over the game's help topics (/help: the same
// topics as the MUD's `help` command).

import { formatLines } from './frames.js';

const esc = s => String(s == null ? '' : s).replace(/[&<>"]/g, c => ({ '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;' }[c]));

// a topic's text, its rules and boxes in /play's dress (frames.js); the rest as written
export function helpHtml(text) {
  return formatLines(String(text || '').replace(/\r/g, '').split('\n').map(t => ({ text: t, html: esc(t) || ' ' })))
    .map(o => (o.box ? o.html : `<div class="hp-line">${o.html}</div>`)).join('');
}

export const CONTROLS = [
  ['Move', 'W A S D, or click the ground'],
  ['Turn the camera', 'right-drag; the wheel zooms'],
  ['Target', 'click a creature, or Tab to cycle (after a fight, corpses too: F loots one)'],
  ['Attack', 'F or Space'],
  ['Abilities', '1 – 8 and Shift+1 – 8 (your bar); right-click a slot to change it'],
  ['More bars', 'Alt+1 – 8, Alt+Shift+1 – 8; how many in Settings (O); drag a bar by its grip, ⟲ turns it, 🔒 locks it'],
  ['Ride / dismount', 'R'],
  ['A marked blow coming', 'Q brace · E sidestep · X interrupt'],
  ['Doors', 'E by a door, or walk into it'],
  ['Menu on anything', 'right-click it'],
  ['Inventory · Character · Spellbook', 'I · C · K'],
  ['Journal · Map · Who · Help', 'L · M · P · H'],
  ['Settings', 'O'],
  ['Chat or a command', 'Enter, then type ("say hello", "help bash")'],
  ['Close windows', 'Esc'],
];

// the topics that match a search, best first: a name that starts with it, then one that has it,
// then a summary that mentions it
export function rankTopics(topics, q) {
  const s = String(q || '').trim().toLowerCase();
  if (!s) return [];
  const score = t => {
    const n = String(t.name || '').toLowerCase();
    if (n === s) return 0;
    if (n.startsWith(s)) return 1;
    if (n.includes(s)) return 2;
    return String(t.summary || '').toLowerCase().includes(s) ? 3 : 9;
  };
  return (topics || []).map(t => [score(t), t]).filter(([sc]) => sc < 9)
    .sort((a, b) => a[0] - b[0] || String(a[1].name).localeCompare(String(b[1].name))).map(([, t]) => t);
}

export function createHelp(root, { fetchTopics, fetchTopic }) {
  const body = root.querySelector('.hp-body');
  const input = root.querySelector('.hp-search');
  let open = false, topics = null, reading = null, timer = 0;
  root.querySelector('.hp-close').addEventListener('click', () => toggle(false));
  input.addEventListener('input', () => { clearTimeout(timer); timer = setTimeout(() => { reading = null; render(); }, 120); });
  input.addEventListener('keydown', e => {
    e.stopPropagation();          // typing here is not a key press for the game
    if (e.key === 'Escape') toggle(false);
    if (e.key === 'Enter') { const first = rankTopics(topics, input.value)[0]; if (first) read(first.name); }
  });
  async function read(name) {
    reading = { name, text: '…' }; render();
    try { reading = await fetchTopic(name); } catch (_) { reading = { name, text: 'No help on that.' }; }
    render();
  }
  function render() {
    if (!open) return;
    if (reading) {
      body.innerHTML = `<button class="hp-back">‹ Back</button><div class="hp-title">${esc(reading.name)}</div>
        <div class="hp-text">${helpHtml(reading.text)}</div>`;
      body.querySelector('.hp-back').addEventListener('click', () => { reading = null; render(); });
      return;
    }
    const q = input.value.trim();
    if (!q) {
      body.innerHTML = `<div class="hp-head">Controls</div><div class="hp-keys">${CONTROLS.map(([what, keys]) =>
        `<div class="hp-key"><span>${esc(what)}</span><kbd>${esc(keys)}</kbd></div>`).join('')}</div>
        <div class="hp-tip">Search above for any command, spell, class or place.</div>`;
      return;
    }
    if (!topics) { body.innerHTML = '<span class="ch-none">Loading the topics…</span>'; return; }
    const found = rankTopics(topics, q).slice(0, 40);
    body.innerHTML = found.length ? found.map(t => `<button class="hp-topic" data-name="${esc(t.name)}">
        <b>${esc(t.name)}</b><span>${esc(t.category || '')}</span><i>${esc(t.summary || '')}</i></button>`).join('')
      : `<span class="ch-none">Nothing on "${esc(q)}".</span>`;
    body.querySelectorAll('.hp-topic').forEach(b => b.addEventListener('click', () => read(b.dataset.name)));
  }
  async function load() {
    if (topics) return;
    try { topics = (await fetchTopics()).topics || []; } catch (_) { topics = []; }
    render();
  }
  function toggle(on = !open) {
    open = on;
    root.classList.toggle('hidden', !open);
    if (open) { reading = null; render(); load(); setTimeout(() => input.focus(), 30); }
  }
  // `help` typed in the chat box: the window, open at the topic asked for (or its search)
  function show(topic) {
    toggle(true);
    if (topic) { input.value = topic; read(topic); }
  }
  return { toggle, show, get open() { return open; } };
}
