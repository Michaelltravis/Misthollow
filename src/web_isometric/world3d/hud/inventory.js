// Inventory panel (I): worn gear in slots around the hero, the bag as a grid, item
// tooltips (stats, damage, armour, effects) and actions that go out as the MUD's own
// commands (wear, wield, remove, quaff, eat, drink, recite, drop, examine). Item art comes
// from the shared icon painter (shared/items.js).
// Drag and drop: from the pack onto a slot wears it there (what was there comes back to the
// pack), from a slot onto the pack takes it off, a ring from one finger to the other moves it.
// The slots an item fits light up as you drag it (a ring: both fingers; equip.py on the server).
// A search box above the bag shows only what matches every word typed (name, type, slot, rarity).
import { compare } from '../gearcompare.js';
import { sound } from '../audio.js';

const $ = s => document.querySelector(s);

const SLOTS = [
  ['head', 'Head'], ['neck1', 'Neck'], ['neck2', 'Neck'], ['about', 'Cloak'], ['body', 'Body'], ['arms', 'Arms'],
  ['wrist1', 'Wrist'], ['wrist2', 'Wrist'], ['hands', 'Hands'], ['waist', 'Waist'], ['legs', 'Legs'], ['feet', 'Feet'],
  ['finger1', 'Ring'], ['finger2', 'Ring'], ['light', 'Light'], ['wield', 'Weapon'], ['shield', 'Shield'],
  ['hold', 'Held'], ['dual_wield', 'Off-hand'],
];
const RARITY = { common: '#b8b0a0', uncommon: '#6fd06f', rare: '#5aa8ff', epic: '#c07aff', legendary: '#ffa640', set: '#5fe0c8' };
const esc = s => String(s == null ? '' : s).replace(/[&<>"]/g, c => ({ '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;' }[c]));

// does an item match the search? every word typed must be found in its name, type, slot or
// rarity ("ring", "rare sword", "potion of heal"); an empty search matches everything
export function matchesSearch(item, query) {
  const words = String(query || '').toLowerCase().split(/\s+/).filter(Boolean);
  if (!words.length) return true;
  if (!item) return false;
  const hay = [item.name, item.short, item.type, item.slot, item.rarity, item.set_key].filter(Boolean).join(' ').toLowerCase();
  return words.every(w => hay.includes(w));
}

// the word the MUD finds an item by, numbered when several share it ("2.sword")
export function keywordFor(item, list) {
  const kw = String(item.name || item.short || 'item').toLowerCase().split(/\s+/).find(w => w.length > 1) || 'item';
  let n = 0;
  for (const it of list) {
    const k = String(it.name || it.short || '').toLowerCase().split(/\s+/);
    if (k.includes(kw)) n++;
    if (it === item) break;
  }
  return n > 1 ? `${n}.${kw}` : kw;
}

// ---- what the class may use (class_gear.py sends the rules as player.gear_rules, and each
// item's gk: 'w:sword:2' a weapon's kind and hands, 's' a shield, 'a:3' armour by weight) ----
const ARMOUR = ['cloth', 'leather', 'mail', 'plate'];
let RULES = null;
export const setGearRules = r => { RULES = r || null; };
// why the class can't use it (a short phrase), or null
export function barredBy(item, rules = RULES) {
  if (!item || !item.gk || !rules) return null;
  const [k, a, b] = String(item.gk).split(':');
  if (k === 'w') {
    const ws = rules.weapons || [];
    if (ws.includes(a) || (a === 'sword' && b === '1' && ws.includes('sword1'))) return null;
    return a === 'sword' && b === '2' ? 'two-handed swords' : `${a}s`;
  }
  if (k === 's') return rules.shield ? null : 'shields';
  if (k === 'a') return +a > rules.armour ? `${ARMOUR[+a] || 'heavy'} armour` : null;
  return null;
}

// ---- drag and drop (pure: tests/web) ----
export const PAIRS = { finger: ['finger1', 'finger2'], neck: ['neck1', 'neck2'], wrist: ['wrist1', 'wrist2'] };
// the slots an item may go in (the server says yes or no: a weapon's off hand needs dual wield);
// none for what the class isn't trained in
export function slotsFor(item, rules = RULES) {
  if (!item) return [];
  if (barredBy(item, rules)) return [];
  const t = item.type;
  if (t === 'weapon') return ['wield', 'dual_wield'];
  const s = String(item.slot || '');
  if (t === 'light' && (!s || s === 'light' || s === 'hold')) return ['light'];   // a glowing ring is still a ring
  if ((t === 'wand' || t === 'staff') && !s) return ['hold'];
  if (!s) return [];
  const kind = s.replace(/[12]$/, '');
  return PAIRS[kind] ? PAIRS[kind].slice() : [s];
}
export const partnerOf = slot => { for (const p of Object.values(PAIRS)) { const i = p.indexOf(slot); if (i >= 0) return p[1 - i]; } return null; };
const verbFor = (item, slot) => (item.type === 'weapon' ? 'wield' : slot === 'light' || slot === 'hold' ? 'hold' : 'wear');
// the command that puts a carried item in a slot
export function dropCommand(item, slot, list) { return `${verbFor(item, slot)} ${keywordFor(item, list)} ${slot}`; }
export const removeCommand = slot => `remove ${slot}`;
// moving worn gear from one slot of a pair to the other (and what is there to the first): the
// commands in order, the carried list followed as each lands in the pack
export function moveCommands(eq, inv, from, to) {
  const a = eq[from], b = eq[to];
  if (!a) return [];
  const pack = inv.slice(), out = [removeCommand(from)];
  pack.push(a);
  if (b) { out.push(removeCommand(to)); pack.push(b); }
  out.push(dropCommand(a, to, pack));
  pack.splice(pack.indexOf(a), 1);
  if (b) out.push(dropCommand(b, from, pack));
  return out;
}

function actionsFor(item, worn) {
  if (worn) return [['Remove', 'remove'], ['Examine', 'examine']];
  const t = item.type;
  const a = [];
  if (t === 'weapon') a.push(['Wield', 'wield']);
  else if (t === 'armor' || t === 'worn' || item.slot) a.push(['Wear', 'wear']);
  else if (t === 'light') a.push(['Hold', 'hold']);
  if (t === 'potion') a.push(['Quaff', 'quaff']);
  if (t === 'food') a.push(['Eat', 'eat']);
  if (t === 'drink') a.push(['Drink', 'drink']);
  if (t === 'scroll') a.push(['Recite', 'recite']);
  if (t === 'wand') a.push(['Zap', 'zap']);
  if (t === 'staff') a.push(['Brandish', 'brandish']);
  if (t === 'note') a.push(['Read', 'read']);
  if (t === 'container') a.push(['Look inside', 'look in']);
  a.push(['Examine', 'examine'], ['Drop', 'drop']);
  return a;
}

// what a piece in the pack (or on a corpse) would change against what you wear: each stat up or
// down, and a verdict (gearcompare.js weighs them for your class)
const STAT_NAME = { damage: 'damage', armour: 'armour', hp: 'health', mana: 'mana', move: 'moves', str: 'strength', dex: 'dexterity',
  con: 'constitution', int: 'intelligence', wis: 'wisdom', cha: 'charisma', damroll: 'damage bonus', hitroll: 'to hit' };
export function upgradeOf(item, player) {
  if (!player || !item || !(item.slot || item.type === 'weapon') || barredBy(item)) return null;
  return compare(item, player.equipment || {}, String(player.char_class || '').toLowerCase());
}
function comparison(item, player) {
  const c = upgradeOf(item, player);
  if (!c) return '';
  const head = c.worn ? `Against ${esc(c.worn.short || c.worn.name)}` : 'Fills an empty slot';
  const verdict = c.better ? '<b class="up">Upgrade</b>' : c.worn && c.diff < -0.5 ? '<b class="down">Worse</b>' : '';
  const rows = c.rows.slice(0, 6).map(r => `<div class="${r.delta > 0 ? 'up' : 'down'}">${r.delta > 0 ? '▲ +' : '▼ '}${esc(r.delta)} ${esc(STAT_NAME[r.k] || String(r.k).replace(/_/g, ' '))}</div>`).join('');
  return `<div class="tt-cmp"><div class="tt-cmp-h">${head} ${verdict}</div>${rows}</div>`;
}

export function tooltip(item, player) {
  const r = item.set_id ? 'set' : (item.rarity || 'common');
  const rows = [];
  rows.push(`<div class="tt-name" style="color:${RARITY[r] || RARITY.common}">${esc(item.short || item.name)}</div>`);
  rows.push(`<div class="tt-sub">${esc(r)} ${esc(item.type || '')}${item.slot ? ` · ${esc(String(item.slot).replace(/\d$/, ''))}` : ''}${item.level ? ` · level ${item.level}` : ''}</div>`);
  if (item.damage_dice) rows.push(`<div>Damage ${esc(item.damage_dice)}${item.weapon_type ? ` (${esc(item.weapon_type)})` : ''}</div>`);
  if (item.armor) rows.push(`<div>Armour ${esc(item.armor)}</div>`);
  for (const a of item.affects || []) {
    const loc = a.location || a.stat || a.type || a.name, mod = a.modifier ?? a.value ?? a.amount;
    if (loc && mod != null) rows.push(`<div class="tt-aff">${mod > 0 ? '+' : ''}${esc(mod)} ${esc(String(loc).replace(/_/g, ' '))}</div>`);
  }
  for (const p of item.procs || []) rows.push(`<div class="tt-proc">${esc(p)}</div>`);
  const bar = barredBy(item);
  if (bar) rows.push(`<div class="tt-bar">Not for your class: no ${esc(bar)}</div>`);
  if (player) rows.push(comparison(item, player));
  const foot = [item.weight ? `${item.weight} lb` : '', item.cost ? `${item.cost} gold` : ''].filter(Boolean).join(' · ');
  if (foot) rows.push(`<div class="tt-foot">${esc(foot)}</div>`);
  return rows.join('');
}

export function createInventory() {
  const root = $('#inventory');
  const doll = root.querySelector('.inv-doll'), bag = root.querySelector('.inv-bag');
  const tip = $('#item-tip'), menu = $('#item-menu');
  let player = null, open = false, sig = '';
  const search = root.querySelector('.inv-search');
  search.addEventListener('input', () => { sig = ''; render(); });
  search.addEventListener('keydown', e => {
    if (e.key === 'Escape') { search.value = ''; sig = ''; render(); search.blur(); }
    e.stopPropagation();          // typing here is not the game's keys
  });

  const icon = (item, size = 88) => {
    const c = document.createElement('canvas');
    c.width = c.height = size;
    try { if (MH.itemIcons) MH.itemIcons.intoCanvas(c, item); } catch (_) {}
    return c;
  };
  const run = (verb, item, list, slot = null) => {
    MH.sendCommand(verb === 'remove' && slot ? removeCommand(slot) : `${verb} ${keywordFor(item, list)}`);
    sound.play({ wear: 'equip', wield: 'draw', hold: 'equip', remove: 'cloth', drop: 'ui_drop' }[verb] || 'ui_click');
    // wearing and dropping do not move you, so no map push follows: ask for one
    setTimeout(() => MH.refreshState && MH.refreshState(), 450);
  };
  function showMenu(e, item, worn, list) {
    menu.innerHTML = actionsFor(item, worn).map(([label, verb]) => `<button data-v="${verb}">${label}</button>`).join('');
    menu.classList.remove('hidden');
    // (kept on the screen by its own size, whatever the HUD's scale and however many lines it has)
    const mr = menu.getBoundingClientRect();
    menu.style.left = `${Math.max(6, Math.min(e.clientX, innerWidth - mr.width - 6))}px`;
    menu.style.top = `${Math.max(6, Math.min(e.clientY, innerHeight - mr.height - 6))}px`;
    menu.querySelectorAll('button').forEach(b => b.addEventListener('click', () => { menu.classList.add('hidden'); run(b.dataset.v, item, list, worn); }));
  }
  // a drag under way: {from: 'bag'|'worn', item, slot, list}
  let drag = null;
  const send = (cmds, snd) => {
    for (const c of cmds) MH.sendCommand(c);
    sound.play(snd);
    setTimeout(() => MH.refreshState && MH.refreshState(), 450);
  };
  function lightSlots(on) {
    const fits = !on ? [] : drag.from === 'bag' ? slotsFor(drag.item) : [partnerOf(drag.slot)].filter(Boolean);
    doll.querySelectorAll('.inv-slot').forEach(w => {
      w.classList.toggle('can-drop', on && fits.includes(w.dataset.slot));
      w.classList.toggle('no-drop', on && !fits.includes(w.dataset.slot));
      w.classList.remove('over');
    });
    bag.classList.toggle('bag-drop', !!on && drag.from === 'worn');
  }
  function cell(item, worn, list, label) {
    const d = document.createElement('div');
    d.className = 'inv-cell' + (item ? '' : ' empty') + (item && barredBy(item) ? ' barred' : '');
    if (!item) { d.innerHTML = `<span>${label || ''}</span>`; return d; }
    d.dataset.name = item.short || item.name || '';
    const r = item.set_id ? 'set' : (item.rarity || 'common');
    d.style.borderColor = RARITY[r] || RARITY.common;
    d.appendChild(icon(item));
    // a piece in the pack better than what you wear: a green arrow on it
    if (!worn) { const up = upgradeOf(item, player); if (up && up.better) { const b = document.createElement('b'); b.className = 'up-badge'; b.title = 'Better than what you wear'; b.textContent = '▲'; d.appendChild(b); } }
    d.addEventListener('mouseenter', e => { tip.innerHTML = tooltip(item, worn ? null : player); tip.classList.remove('hidden'); place(e); });
    d.addEventListener('mousemove', place);
    d.addEventListener('mouseleave', () => tip.classList.add('hidden'));
    d.addEventListener('click', e => { e.stopPropagation(); showMenu(e, item, worn, list); });
    d.addEventListener('dblclick', e => { e.stopPropagation(); menu.classList.add('hidden'); run(actionsFor(item, worn)[0][1], item, list, worn); });
    // drag it: from the pack onto a slot, or off a slot (worn: the slot's name)
    d.draggable = true;
    d.addEventListener('dragstart', e => {
      drag = { from: worn ? 'worn' : 'bag', item, slot: worn || null, list };
      e.dataTransfer.setData('text/x-gear', worn || 'bag');
      e.dataTransfer.effectAllowed = 'move';
      tip.classList.add('hidden'); menu.classList.add('hidden');
      requestAnimationFrame(() => lightSlots(true));
    });
    d.addEventListener('dragend', () => { lightSlots(false); drag = null; });
    return d;
  }
  function place(e) {
    // (by its own size: a comparing tooltip is wider than a plain one; flipped to the cursor's left at the edge)
    const tr = tip.getBoundingClientRect();
    const x = e.clientX + 16 + tr.width > innerWidth - 6 ? e.clientX - 16 - tr.width : e.clientX + 16;
    tip.style.left = `${Math.max(6, x)}px`;
    tip.style.top = `${Math.max(6, Math.min(e.clientY + 12, innerHeight - tr.height - 10))}px`;
  }
  function render() {
    if (!player || !open) return;
    const eq = player.equipment || {}, inv = player.inventory || [];
    setGearRules(player.gear_rules);
    const query = search.value.trim();
    const nsig = JSON.stringify([eq, inv.map(i => i.name + i.rarity), player.gold, query]);
    if (nsig === sig) return;
    sig = nsig;
    doll.innerHTML = '';
    const wornList = Object.values(eq);
    for (const [slot, label] of SLOTS) {
      const w = document.createElement('div');
      w.className = 'inv-slot';
      w.dataset.slot = slot;
      w.appendChild(cell(eq[slot], eq[slot] ? slot : false, wornList, label));
      const fits = () => drag && (drag.from === 'bag' ? slotsFor(drag.item).includes(slot) : partnerOf(drag.slot) === slot);
      w.addEventListener('dragover', e => { if (fits()) { e.preventDefault(); w.classList.add('over'); } });
      w.addEventListener('dragleave', () => w.classList.remove('over'));
      w.addEventListener('drop', e => {
        e.preventDefault();
        if (!fits()) return;
        const dr = drag;
        if (dr.from === 'bag') send([dropCommand(dr.item, slot, inv)], dr.item.type === 'weapon' ? 'draw' : 'equip');
        else send(moveCommands(eq, inv, dr.slot, slot), 'equip');
      });
      doll.appendChild(w);
    }
    bag.innerHTML = '';
    if (!bag.dataset.dnd) {
      // worn gear dropped on the pack comes off
      bag.dataset.dnd = '1';
      bag.addEventListener('dragover', e => { if (drag && drag.from === 'worn') e.preventDefault(); });
      bag.addEventListener('drop', e => {
        e.preventDefault();
        if (drag && drag.from === 'worn') send([removeCommand(drag.slot)], 'cloth');
      });
    }
    // what the search lets through (its commands still number the item in the whole pack)
    const shown = query ? inv.filter(i => matchesSearch(i, query)) : inv;
    const cells = query ? Math.max(6, Math.ceil(shown.length / 6) * 6) : Math.max(30, Math.ceil(inv.length / 6) * 6);
    for (let i = 0; i < cells; i++) bag.appendChild(cell(shown[i], false, inv));
    root.querySelector('.inv-gold').textContent = `${(player.gold || 0).toLocaleString()} gold`;
    root.querySelector('.inv-count').textContent = query ? `${shown.length} of ${inv.length} item${inv.length === 1 ? '' : 's'}`
      : `${inv.length} item${inv.length === 1 ? '' : 's'}`;
  }
  document.addEventListener('click', () => menu.classList.add('hidden'));
  root.querySelector('.inv-close').addEventListener('click', () => toggle(false));
  function toggle(on = !open) {
    open = on;
    root.classList.toggle('hidden', !open);
    tip.classList.add('hidden'); menu.classList.add('hidden');
    if (open) { sig = ''; if (MH.refreshState) MH.refreshState(); render(); }
  }
  return {
    toggle,
    get open() { return open; },
    update(p) { player = p; setGearRules(p && p.gear_rules); render(); },
  };
}
