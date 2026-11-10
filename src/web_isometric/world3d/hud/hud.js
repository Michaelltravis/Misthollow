// The 3D client's HUD: player frame, orbs and action bar, target frame, room/zone banner,
// toasts, chat log with command line, menu and settings. DOM over the WebGL canvas,
// driven by the shared net.js state (`map` payloads, `combat.update`, server text).
// Actions go out as bus events ('hud.attack', 'hud.ability', 'hud.flee') for main.js,
// which knows the target and plays the hero's animation.
import { splitByKind } from './logkinds.js';
import { framed as inBox, renderBox, renderLine, renderCols, classify, meters, inList, unprompt, isTitle } from './frames.js';
import { SCHOOL_CSS } from '../sctlogic.js';
import { createInventory, tooltip as itemTooltip } from './inventory.js';
import { createCharacter } from './character.js';
import { createSpellbook } from './spellbook.js';
import { createTrainer } from './trainer.js';
import { createParty } from './party.js';
import { createQuest } from './quest.js';
import { createJournal } from './journal.js';
import { createShop } from './shop.js';
import { createLootWindow } from './lootwin.js';
import { createTalk } from './talk.js';
import { createWho, hereRows } from './who.js';
import { createHelp } from './help.js';
import { createTalents } from './talents.js';
import { createAlmanac } from './almanac.js';
import { createTravel } from './travel.js';
import { createStable } from './stable.js';
import { createServices } from './services.js';
import { createLegend } from './legend.js';
import { abilityIcon, uiIcon } from './icons.js';
import { buffList, auraBase } from './buffs.js';
import { lookPortrait, creaturePortrait } from './portrait.js';
import { SLOTS, cleanBar, defaultBar, placeNew, putOnBar, takeOffBar, keepUnseen, diffAbilities, usable, costLine, rankOf, MAIN, keyOf, slotForKey } from '../abilities.js';
import { createBars } from './bars.js';
import { conOf, shownName } from '../targeting.js';
import { recipeFor } from '../abilityfx.js';
import { RECIPES } from '../abilityfx-table.js';
import { sound } from '../audio.js';
const $ = s => document.querySelector(s);
const ls = { get(k) { try { return localStorage.getItem(k); } catch (_) { return null; } },
  set(k, v) { try { localStorage.setItem(k, v); } catch (_) {} } };

// class kits in the order they unlock (same order as the 2D client's action bar)
export const KIT = {
  warrior: ['bash', 'cleave', 'kick', 'execute', 'rally', 'rescue', 'charge', 'heroic_throw'],
  paladin: ['censure', 'order_verdict', 'holy_smite', 'absolution', 'halo_of_reckoning', 'turn_undead', 'rescue', 'bash'],
  ranger: ['truesight_shot', 'wildbond_strike', 'loosing_storm', 'quarry_mark', 'call_lightning'],
  thief: ['backstab', 'circle', 'trip', 'low_blow', 'pocket_sand', 'jackpot', 'knife_toss'],
  assassin: ['backstab', 'mark', 'expose', 'vital', 'feint', 'execute_contract', 'fade'],
  mage: ['magic_missile', 'fireball', 'lightning_bolt', 'chill_touch', 'sleep', 'towerbolt'],
  necromancer: ['soul_bolt', 'chill_touch', 'soul_siphon', 'animate_dead', 'soul_reap'],
  cleric: ['holy_smite', 'cure_light', 'heal', 'turn_undead', 'bless', 'flamestrike'],
  bard: ['mockery', 'fascinate', 'crescendo', 'discordant_note', 'sleep'],
};
const SELF = new Set(['rally', 'cure_light', 'heal', 'bless', 'fade', 'absolution', 'halo_of_reckoning', 'animate_dead', 'crescendo']);
// an ability's painted icon (hud/icons.js) as an <img>, in the hero's class's colours
let iconClass = '';
const iconTypes = new Map();
export const ICON = id => `<img class="ic" alt="" draggable="false" src="${abilityIcon(id, iconClass, { type: iconTypes.get(id) || 'skill' })}">`;
// classes that spend mana on their spells: their orb stays mana (setPlayer)
const CASTERS = new Set(['mage', 'necromancer', 'cleric', 'paladin', 'bard']);
// a big number made short for an orb: 200000 -> 200k, 12500 -> 12.5k
const compact = n => { n = Number(n) || 0; const a = Math.abs(n);
  return a >= 1e6 ? `${(n / 1e6).toFixed(a >= 1e7 ? 0 : 1)}m` : a >= 1e5 ? `${Math.round(n / 1e3)}k` : a >= 1e4 ? `${(n / 1e3).toFixed(1)}k` : String(n); };
const esc = s => String(s == null ? '' : s).replace(/[&<>"]/g, c => ({ '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;' }[c]));

export function createHud() {
  const els = {
    pf: $('#player-frame'), tf: $('#target-frame'), banner: $('#banner'), toasts: $('#toasts'),
    mm: $('#minimap'), ab: $('#actionbar'), chat: $('#chat'), log: $('#log'), input: $('#chat-input'),
    menu: $('#menu'), settings: $('#settings'), slots: $('#slots'), xbars: $('#xbars'),
  };
  const st = { player: null, abilities: null, byId: new Map(), bar: new Array(SLOTS).fill(null), custom: false, barEdited: 0,
    arranged: null, serverSig: '', barSig: '', glow: new Set(), cooldowns: {}, cdAt: 0, target: null, history: [], hi: -1, barsFor: '' };
  // the extra bars (bars.js): floating, movable; their slots behave as the main bar's
  const mainLock = document.createElement('button');
  mainLock.className = 'barlock';
  $('#bar-mid').appendChild(mainLock);
  const bars = createBars(els.xbars, { mainLock, onChange: () => { st.barSig = ''; renderBar(); try { syncSettings(); } catch (_) {} } });
  const locked = i => bars.lockedSlot(i);
  const lockedToast = () => toast('That bar is locked: click its 🔒 to change what is on it');
  // a slot anywhere on the bars (main and extra)
  const slotQ = sel => els.slots.querySelector(sel) || els.xbars.querySelector(sel);
  const slotQA = sel => [...els.slots.querySelectorAll(sel), ...els.xbars.querySelectorAll(sel)];
  const keyTip = i => (keyOf(i, true) ? ` (${keyOf(i, true)})` : ' (bar 5)');
  const inventory = createInventory();
  const character = createCharacter();
  const spellbook = createSpellbook($('#spellbook'), {
    icon: id => ICON(id),
    onUse: id => use(id),
    onAdd: id => {
      // the first free slot on a bar that shows (the main bar first)
      const i = st.bar.findIndex((x, k) => x === null && !locked(k) && (k < MAIN || k - MAIN < 8 * bars.count));
      if (i < 0) toast('Your bars are full (or locked): drag the ability onto a slot (more bars: Settings, O)');
      else if (st.bar.includes(id) && locked(st.bar.indexOf(id))) lockedToast();
      else editBar(putOnBar(st.bar, id, i, locked));
    },
    onDragStart: () => { els.ab.classList.add('dragging'); if (els.xbars) els.xbars.classList.add('dragging'); },
    onDragEnd: () => { els.ab.classList.remove('dragging'); if (els.xbars) els.xbars.classList.remove('dragging'); },
  });
  const trainer = createTrainer($('#trainer'), { icon: id => ICON(id), onTrain: id => MH.sendCommand(`practice ${id}`) });
  // the everyday windows: a shopkeeper's wares, a conversation, who is about, help
  const me = () => MH.state.playerName || '';
  const getJSON = async url => { const r = await fetch(url); if (!r.ok) throw new Error(r.status); return r.json(); };
  const itemCanvas = item => { const c = document.createElement('canvas'); c.width = c.height = 84; try { if (MH.itemIcons) MH.itemIcons.intoCanvas(c, item); } catch (_) {} return c; };
  const shop = createShop($('#shop'), {
    fetchShop: kw => getJSON(`/shop?player=${encodeURIComponent(me())}&keeper=${encodeURIComponent(kw || '')}`),
    send: c => MH.sendCommand(c), icon: itemCanvas, sound,
    tooltip: itemTooltip, player: () => MH.state && MH.state.player,     // a row's hover card, against what you wear
  });
  // a corpse's loot window (lootwin.js): main.js opens it when the hero reaches a corpse
  const lootwin = createLootWindow($('#lootwin'), { send: c => { MH.sendCommand(c); setTimeout(() => MH.refreshState && MH.refreshState(), 400); }, icon: itemCanvas, sound, toast: t => toast(t) });
  const talk = createTalk($('#talk'), {
    send: c => MH.sendCommand(c), sound,
    listen: fn => { const h = ({ text }) => fn(text || ''); MH.bus.on('terminal.output', h); return () => MH.bus.off('terminal.output', h); },
    fetchQuests: () => getJSON(`/quests?player=${encodeURIComponent(me())}`),
  });
  const who = createWho($('#who'), {
    fetchWho: () => getJSON(`/who?player=${encodeURIComponent(me())}`),
    here: () => hereRows(MH.state.lastPayload, (MH.state.player || {}).vnum, me()),
    onPick: (row, e) => MH.bus.emit('hud.pickWho', { row, x: e.clientX, y: e.clientY }),
  });
  // progression and travel: talents, the almanac, travel, the stable, bank and mail, legend
  const q = path => getJSON(`/${path}?player=${encodeURIComponent(me())}`);
  const send = c => MH.sendCommand(c);
  const talents = createTalents($('#talents'), { fetchTalents: () => q('talents'), send });
  const almanac = createAlmanac($('#almanac'), { fetchAlmanac: () => q('almanac'), send, prefill: t => prefill(t) });
  const travel = createTravel($('#travel'), { fetchTravel: () => q('travel'), send });
  const stable = createStable($('#stable'), { fetchStable: () => q('stable'), send });
  const services = createServices($('#services'), { fetchServices: () => q('services'), send, prefill: t => prefill(t) });
  const legend = createLegend($('#legend'), { fetchLegend: () => q('legend'), fetchDoctrine: () => q('doctrine'), send,
    isWarrior: () => String((MH.state.player || {}).char_class || '').toLowerCase() === 'warrior' });
  const PROGRESS = { talents, almanac, travel, stable, services, legend };
  const help = createHelp($('#help'), {
    fetchTopics: () => getJSON('/help'),
    fetchTopic: name => getJSON(`/help?topic=${encodeURIComponent(name)}`),
  });
  const party = createParty({
    frames: $('#party'), invite: $('#group-invite'), loot: $('#loot-roll'),
    onTarget: name => MH.bus.emit('hud.targetPlayer', name),
    onMenu: (name, x, y, leader) => MH.bus.emit('hud.partyMenu', { name, x, y, leader }),
    toast: msg => toast(msg),
  });
  // the marquee quest: the offer card, the embark popup, the tracker under the minimap
  const quest = createQuest({
    card: $('#quest-card'), embark: $('#quest-embark'), tracker: $('#quest-tracker'),
    toast: msg => toast(msg), onMark: vnum => MH.bus.emit('quest.mark', vnum),
  });

  const journal = createJournal($('#journal'), { toast: msg => toast(msg) });

  // ---- scale ----
  function applyScale() {
    const pref = ls.get('mh3d_ui') || 'auto';
    const w = window.innerWidth;
    const v = pref === 'auto' ? (w >= 1800 ? 1.05 : w >= 1400 ? 0.95 : w >= 1000 ? 0.85 : 0.72) : Number(pref) || 1;
    document.documentElement.style.setProperty('--ui', v);
  }
  window.addEventListener('resize', applyScale);
  applyScale();

  function showGame(on) {
    for (const k of ['pf', 'mm', 'ab', 'chat', 'menu']) els[k].classList.toggle('hidden', !on);
    bars.show(on);
    fitChat();
    els.log.scrollTop = els.log.scrollHeight;
  }
  // the chat sits left of the action bar and never runs under it
  function fitChat() {
    if (els.ab.classList.contains('hidden')) return;
    const left = els.ab.getBoundingClientRect().left;
    const ui = parseFloat(getComputedStyle(document.documentElement).getPropertyValue('--ui')) || 1;
    els.chat.style.width = window.innerWidth <= 900 ? '' : `${Math.max(240, Math.min(430 * ui, left - 14 - 12))}px`;
  }
  window.addEventListener('resize', () => requestAnimationFrame(fitChat));

  // ---- player ----
  const pct = (a, b) => `${Math.max(0, Math.min(100, (b ? a / b : 0) * 100))}%`;
  // a vitals bar: the fill, a pale ghost that drains behind it after a wound, the numbers
  function vbar(el, cur, max, label = '') {
    const w = pct(cur, max);
    el.querySelector('b').style.width = w;
    const ghost = el.querySelector('i');
    if (ghost) ghost.style.width = w;
    el.querySelector('span').textContent = max ? `${label}${Number(cur || 0).toLocaleString()} / ${Number(max).toLocaleString()}` : '';
    el.classList.toggle('low', !!max && cur / max <= 0.3);
  }
  let portraitFor = '', lastLevel = 0;
  // a moment: a title over light rays (a level gained, a fall)
  let momentTimer = 0;
  function moment({ kicker = '', title = '', sub = '', tone = '' }) {
    const m = $('#moment');
    m.querySelector('.mo-kicker').textContent = kicker;
    m.querySelector('.mo-title').textContent = title;
    m.querySelector('.mo-sub').textContent = sub;
    m.className = tone;
    void m.offsetWidth;
    m.classList.add('in');
    clearTimeout(momentTimer);
    momentTimer = setTimeout(() => m.classList.add('hidden'), 4300);
  }
  // the death card: who did it, what it cost, where you wake (player.py sends a 'fallen' event
  // with them; the death event alone shows the card at once, the details fill it in)
  let fallenAt = 0;
  function fallen(d) {
    const now = performance.now();
    if (!d && now - fallenAt < 3000) return;
    fallenAt = now;
    document.documentElement.classList.add('fallen');
    const cost = d ? [d.exp ? `−${d.exp.toLocaleString()} experience` : '', d.gold ? `−${d.gold.toLocaleString()} gold` : ''].filter(Boolean).join(' · ') : '';
    const sub = d ? `${d.killer ? `Slain by ${d.killer}. ` : ''}${cost ? `${cost}. ` : ''}You wake at ${d.wake || 'your shelter'}, weakened.`
      : 'You wake where your journey last found shelter…';
    if (d && $('#moment').classList.contains('in') && !$('#moment').classList.contains('hidden')) $('#moment .mo-sub').textContent = sub;
    else moment({ kicker: 'the mist takes you', title: 'You have fallen', sub, tone: 'fall' });
    setTimeout(() => document.documentElement.classList.remove('fallen'), 4200);
  }
  function setPlayer(p) {
    if (!p) return;
    st.player = p;
    // a level gained: the moment, and the world answers with light (main.js)
    if (lastLevel && p.level > lastLevel) {
      moment({ kicker: `${String(p.char_class || '').toLowerCase()} · level ${p.level}`, title: 'Level Up!', sub: 'Your strength grows. New paths open before you.' });
      MH.bus.emit('hud.levelup', p.level);
    }
    lastLevel = p.level || lastLevel;
    const cls = String(p.char_class || '').toLowerCase();
    if (cls && cls !== iconClass) { iconClass = cls; st.barSig = ''; }
    els.pf.querySelector('.name').textContent = p.name || '';
    els.pf.querySelector('.cls').textContent = `${(p.race || '').replace(/_/g, ' ')} ${p.char_class || ''}`.trim();
    els.pf.querySelector('.ini').textContent = (p.name || '?')[0].toUpperCase();
    els.pf.querySelector('.lvl').textContent = p.level || 1;
    els.pf.dataset.cls = cls;
    // the portrait shows what you wear: taken again when your look changes
    const pkey = `${cls}:${(p.look && p.look.sig) || ''}`;
    if (cls && portraitFor !== pkey) {
      portraitFor = pkey;
      lookPortrait(p.look, cls).then(url => { if (url && portraitFor === pkey) { const img = els.pf.querySelector('.face'); img.src = url; img.classList.add('on'); } });
    }
    vbar(els.pf.querySelector('.vbar.hp'), p.hp, p.max_hp);
    // a caster's orb is its mana, and its class's own resource (Faith, Holy Power, Soul Shards,
    // Inspiration) the pips under the bars; a fighter's orb is its resource (Momentum, Focus...)
    const caster = CASTERS.has(cls);
    const classRes = p.resource && p.resource.max ? p.resource : null;
    const res = classRes && !caster ? { cur: classRes.value, max: classRes.max, name: classRes.name }
      : { cur: p.mana, max: p.max_mana, name: 'Mana' };
    vbar(els.pf.querySelector('.vbar.mp'), res.cur, res.max);
    els.pf.querySelector('.vbar.mp').dataset.res = String(res.name || 'mana').toLowerCase();
    document.documentElement.classList.toggle('hp-low', !!p.max_hp && p.hp / p.max_hp <= 0.3 && p.hp > 0);
    const hpOrb = els.ab.querySelector('.orb.hp'), mpOrb = els.ab.querySelector('.orb.mp');
    hpOrb.querySelector('.fill').style.height = pct(p.hp, p.max_hp);
    hpOrb.querySelector('.val').textContent = `${compact(p.hp)}/${compact(p.max_hp)}`;
    mpOrb.querySelector('.fill').style.height = pct(res.cur, res.max);
    mpOrb.querySelector('.val').textContent = `${compact(res.cur)}/${compact(res.max)}`;
    mpOrb.querySelector('.lab').textContent = res.name;
    mpOrb.classList.toggle('full', !!(classRes && !caster) && res.cur >= res.max);
    mpOrb.dataset.res = String(res.name || 'mana').toLowerCase();
    const floor = p.exp_floor || 0, next = p.exp_to_level || 0;
    const capped = !next || next - floor > 1e9;
    $('#xpbar b').style.width = capped ? '100%' : next > floor ? pct((p.exp || 0) - floor, next - floor) : '0%';
    $('#xpbar').title = capped ? 'Max level' : `Experience: ${p.exp || 0} / ${next}`;
    // buffs and debuffs: an icon each, a ring that empties as it wears off
    renderBuffs(Array.isArray(p.affects) ? p.affects : []);
    paintPips(p.charges || (caster && classRes ? { name: String(classRes.name).toLowerCase().replace(/\s+/g, '_'), label: classRes.name, value: classRes.value, max: classRes.max } : null));
    inventory.update(p);
    character.update(p);
    paintRiding(p);
    st.cooldowns = p.cooldowns || {};
    st.cdAt = performance.now();
    buildBar(p);
    paintCooldowns();
  }

  // ---- buffs ----
  const TICK_S = 6;          // an affect tick (config.AFFECT_TICK_SECONDS)
  const BAD = /poison|curse|blind|slow|weak|stun|bleed|burn|fear|snare|root|shatter|mark|expose|sunder|disease|plague|silence|entangle|sleep/;
  let buffSig = '';
  function renderBuffs(aff) {
    const list = buffList(aff);
    const nsig = JSON.stringify(list.map(a => [a.name, a.remaining, a.duration]));
    if (nsig === buffSig) return;
    buffSig = nsig;
    $('#buffs').innerHTML = list.map(a => {
      const id = String(a.name || a.spell).toLowerCase();
      const base = auraBase(id);
      const bad = BAD.test(id);
      const left = a.remaining != null ? a.remaining : a.duration;
      const frac = a.duration ? Math.max(0, Math.min(1, (left || 0) / a.duration)) : 1;
      const secs = left != null ? Math.max(0, Math.round(left * TICK_S)) : null;
      const label = base.replace(/_/g, ' ');
      return `<div class="buff${bad ? ' bad' : ''}" style="--left:${frac}" data-tip-title="${esc(label)}" data-tip-sub="${bad ? 'Harmful' : 'Helpful'}${secs != null ? ` · about ${secs >= 60 ? `${Math.round(secs / 60)} min` : `${secs} s`} left` : ''}">
        <img alt="" src="${abilityIcon(base, iconClass, { type: 'spell' })}"><span>${secs != null && secs < 60 ? secs : ''}</span></div>`;
    }).join('');
  }

  // ---- the tooltip card: abilities, buffs, menu buttons ----
  const tip = $('#tipcard');
  function showTip(html, x, y) {
    tip.innerHTML = html;
    tip.classList.remove('hidden');
    const r = tip.getBoundingClientRect();
    const left = Math.min(window.innerWidth - r.width - 8, Math.max(8, x - r.width / 2));
    const top = y - r.height - 14 < 8 ? y + 22 : y - r.height - 14;
    tip.style.left = `${left}px`; tip.style.top = `${top}px`;
  }
  function hideTip() { tip.classList.add('hidden'); }
  function abilityTip(a, key) {
    const book = a.pct > 0 ? `<div class="tc-bar"><b style="width:${Math.min(100, a.pct)}%"></b></div>` : '';
    const rank = a.known ? `${rankOf(a.pct)} · ${a.pct}%` : a.quest ? `Earned through ${a.quest}` : `Unlocks at level ${a.level}`;
    return `<div class="tc-head"><img class="tc-ic" src="${abilityIcon(a.id, iconClass, { type: a.type })}">
        <div><div class="tc-name">${esc(a.name)}</div><div class="tc-sub">${a.type === 'spell' ? 'Spell' : 'Skill'}${a.marquee ? ' · ★ marquee' : ''} · ${esc(rank)}</div></div></div>
      ${book}<div class="tc-desc">${esc(a.desc || '')}</div>
      <div class="tc-meta">${esc(costLine(a))}${key ? ` · key <b>${esc(key)}</b>` : ''}</div>`;
  }
  // anything with data-tip-title shows a small card
  document.addEventListener('mouseover', e => {
    const el = e.target.closest && e.target.closest('[data-tip-title]');
    if (!el) return;
    const r = el.getBoundingClientRect();
    showTip(`<div class="tc-name">${esc(el.dataset.tipTitle)}</div>${el.dataset.tipSub ? `<div class="tc-sub">${esc(el.dataset.tipSub)}</div>` : ''}`, r.left + r.width / 2, r.top);
  });
  document.addEventListener('mouseout', e => { if (e.target.closest && e.target.closest('[data-tip-title], .slot')) hideTip(); });

  // ---- action bar: Attack (F), your own 16 slots (1-8, Shift+1-8), Flee ----
  // Abilities come from the payload (`abilities`, `bar`: see abilities.js). A character who
  // never arranged the bar gets the class's usual order; once you drag something, the bar is
  // yours and is kept with the character (`webbar`). New abilities glow into free slots.
  // the class's ability book (what each ability is, costs and unlocks at) comes once per class
  // from /abilitybook; the payload only carries how well you know each one (skills, spells)
  const books = new Map();
  function bookFor(cls) {
    if (!books.has(cls)) {
      books.set(cls, null);
      fetch(`/abilitybook?cls=${encodeURIComponent(cls)}`).then(r => (r.ok ? r.json() : null)).catch(() => null).then(b => {
        if (!b || !Array.isArray(b.abilities)) return;
        books.set(cls, b.abilities);
        if (st.player && String(st.player.char_class || '').toLowerCase() === cls) buildBar(st.player);
      });
    }
    return books.get(cls);
  }
  function abilityList(p) {
    const cls = String(p.char_class || '').toLowerCase();
    const learned = { ...(p.skills || {}), ...(p.spells || {}) };
    const book = bookFor(cls);
    if (book) return book.map(a => ({ ...a, pct: learned[a.id] || 0, known: (learned[a.id] || 0) > 0 }));
    // until the book arrives: what the class kit and the learned lists say
    const spells = new Set(Object.keys(p.spells || {}));
    return (KIT[cls] || []).map((id, i) => ({ id, name: id.replace(/_/g, ' '), type: spells.has(id) ? 'spell' : 'skill',
      pct: learned[id] || 0, known: !!learned[id], level: i + 1, target: SELF.has(id) ? 'self' : 'enemy' }));
  }
  function buildBar(p) {
    if (p.name && p.name !== st.barsFor) { st.barsFor = p.name; st.serverSig = ''; st.barEdited = 0; bars.load(p.name); }
    const cls = String(p.char_class || '').toLowerCase();
    const list = abilityList(p);
    const prev = st.abilities && st.abilities.fromBook === !!books.get(cls) ? st.abilities : null, before = st.bar;
    list.fromBook = !!books.get(cls);
    st.abilities = list;
    st.byId = new Map(list.map(a => [a.id, a]));
    for (const a of list) iconTypes.set(a.id, a.type || 'skill');
    // the server's bar is taken up when it CHANGES. Between map payloads the same player object
    // comes again with every vitals tick and combat round, carrying the bar as it was then:
    // taking that up each time undid what you had arranged since (and the next edit sent the
    // old bar back to the server). Nor is it taken up while a change of yours is on its way.
    const sig = JSON.stringify(Array.isArray(p.bar) ? p.bar : null);
    if (sig !== st.serverSig) {
      st.serverSig = sig;
      if (performance.now() - st.barEdited > 4000) {
        st.custom = Array.isArray(p.bar) && p.bar.some(Boolean);
        st.arranged = st.custom ? p.bar.slice(0, SLOTS) : null;
      }
    }
    st.bar = st.custom ? cleanBar(st.arranged, list) : defaultBar(list, KIT[cls] || []);
    if (prev) {
      const { learned, improved } = diffAbilities(prev, list);
      if (learned.length) {
        // into free slots, without moving what is already on your keys
        const r = placeNew(st.custom ? st.bar : cleanBar(before, list), learned.filter(id => usable(st.byId.get(id))), MAIN + 8 * bars.count, locked);
        if (r.placed.length || !st.custom) editBar(r.bar, true);
        for (const id of learned) {
          const a = st.byId.get(id), i = st.bar.indexOf(id);
          toast(`You learned ${a ? a.name : id}${a && a.passive ? ' (passive)' : i >= 0 ? ` — on your bar${keyTip(i)}` : ' — open your spellbook (K)'}`);
          st.glow.add(id);
          setTimeout(() => { st.glow.delete(id); renderBar(); }, 9000);
        }
      }
      for (const imp of improved) tick(imp.id, imp.to - imp.from);
    }
    renderBar();
    spellbook.update(list, st.bar, p.level);
    trainer.update({ ...p, abilities: list });
  }
  // send the bar to the server (kept with the character)
  function editBar(bar, quiet) {
    // (what the bar held that this client can't show yet stays on it: keepUnseen)
    st.arranged = st.custom ? keepUnseen(bar, st.arranged, st.bar) : bar.slice();
    st.bar = bar;
    st.custom = true;
    st.barEdited = performance.now();
    MH.sendCommand(`webbar ${st.arranged.map(x => x || '-').join(' ')}`, false);
    renderBar();
    spellbook.update(st.abilities, st.bar, st.player && st.player.level);
    if (!quiet) requestAnimationFrame(fitChat);
  }
  function slotHtml(i) {
    const id = st.bar[i], a = id && st.byId.get(id), key = keyOf(i);
    if (!a) return `<div class="slot empty" data-i="${i}" data-tip-title="An empty slot${keyTip(i)}" data-tip-sub="Drag an ability here from your spellbook (K)"><span class="key">${key}</span></div>`;
    return `<div class="slot${st.glow.has(id) ? ' glow' : ''}${a.marquee ? ' marquee' : ''}${locked(i) ? ' pinned' : ''}" data-i="${i}" data-id="${a.id}" draggable="${!locked(i)}">`
      + `${ICON(a.id)}<span class="key">${key}</span><div class="cd"><i></i><span></span></div></div>`;
  }
  function renderBar() {
    const sig = JSON.stringify([st.bar, [...st.glow], st.bar.map(id => id && st.byId.has(id)), bars.count, st.bar.map((_, i) => locked(i))]);
    if (sig === st.barSig) return;
    st.barSig = sig;
    const row = (from, to) => Array.from({ length: to - from }, (_, k) => slotHtml(from + k)).join('');
    els.slots.innerHTML = `<div class="bar-row shift${st.bar.slice(8).some(Boolean) ? '' : ' unused'}">${row(8, 16)}</div>`
      + `<div class="bar-row main"><div class="slot fixed attack" data-act="attack" data-tip-title="Attack" data-tip-sub="Swing at your target — or press F (or Space)"><img class="ic" alt="" src="${uiIcon('sword', { size: 96 })}"><span class="key">F</span><i class="swing"></i></div>`
      + `${row(0, 8)}<div class="slot fixed flee" data-act="flee" data-tip-title="Flee" data-tip-sub="Break off the fight and run"><img class="ic" alt="" src="${uiIcon('flee', { size: 96, color: '#d8e6f0', glow: 'rgba(160,200,240,.6)' })}"></div></div>`;
    for (const r of bars.rows()) {
      r.el.innerHTML = r.on ? row(r.from, r.to) : '';
      // nothing on it yet: faded back, out of the way, until hovered or something is dragged
      r.el.parentElement.classList.toggle('unused', !st.bar.slice(r.from, r.to).some(Boolean));
    }
    slotQA('.slot').forEach(el => {
      const i = el.dataset.i != null ? +el.dataset.i : -1;
      el.addEventListener('click', () => use(el.dataset.act || st.bar[i]));
      if (el.dataset.id) {
        el.addEventListener('mouseenter', () => {
          const a = st.byId.get(el.dataset.id);
          if (!a) return;
          const r = el.getBoundingClientRect();
          showTip(abilityTip(a, keyOf(i, true)), r.left + r.width / 2, r.top);
          MH.bus.emit('hud.abilityHover', { id: a.id });
        });
        el.addEventListener('mouseleave', () => { hideTip(); MH.bus.emit('hud.abilityHover', null); });
      }
      if (i < 0) return;
      el.addEventListener('contextmenu', e => {
        e.preventDefault();
        if (st.bar[i]) MH.bus.emit('hud.slotMenu', { x: e.clientX, y: e.clientY, slot: i, id: st.bar[i], name: (st.byId.get(st.bar[i]) || {}).name });
      });
      el.addEventListener('dragstart', e => {
        if (locked(i)) { e.preventDefault(); return; }
        e.dataTransfer.setData('text/x-ability', st.bar[i]);
        e.dataTransfer.setData('text/x-slot', String(i));
        e.dataTransfer.effectAllowed = 'move';
        els.ab.classList.add('dragging');
        els.xbars.classList.add('dragging');
      });
      // (let go off the bars, it comes off: the document's drop, below)
      el.addEventListener('dragend', () => {
        els.ab.classList.remove('dragging');
        els.xbars.classList.remove('dragging');
      });
      // a locked slot takes the drop too, and keeps what it has: one turned away would read as
      // let go off the bars, and the ability dragged would come off
      el.addEventListener('dragover', e => { if (e.dataTransfer.types.includes('text/x-ability')) { e.preventDefault(); if (!locked(i)) el.classList.add('over'); } });
      el.addEventListener('dragleave', () => el.classList.remove('over'));
      el.addEventListener('drop', e => {
        e.preventDefault();
        el.classList.remove('over');
        els.ab.classList.remove('dragging');
        els.xbars.classList.remove('dragging');
        const id = e.dataTransfer.getData('text/x-ability');
        if (!id || !st.byId.has(id)) return;
        const next = putOnBar(st.bar, id, i, locked);
        if (next.every((x, k) => x === st.bar[k])) { if (st.bar[i] !== id) lockedToast(); return; }
        editBar(next);
      });
    });
    requestAnimationFrame(fitChat);
  }
  // an ability dragged from a slot and let go off the bars comes off them. Only a drop does it:
  // a drag called off (Esc), let go outside the window, or on a bar's frame between slots keeps it
  document.addEventListener('dragover', e => { if (e.dataTransfer.types.includes('text/x-slot')) e.preventDefault(); });
  document.addEventListener('drop', e => {
    if (!e.dataTransfer.types.includes('text/x-slot')) return;
    e.preventDefault();
    els.ab.classList.remove('dragging');
    els.xbars.classList.remove('dragging');
    if (e.target.closest && e.target.closest('#actionbar, #xbars')) return;
    const i = +e.dataTransfer.getData('text/x-slot'), id = e.dataTransfer.getData('text/x-ability');
    if (!id || st.bar[i] !== id || locked(i)) return;
    const a = st.byId.get(id);
    editBar(takeOffBar(st.bar, i));
    toast(`${a ? a.name : 'That'} is off your bar (it stays in your spellbook, K)`);
  });
  // "+2%": an ability on the bar grew
  function tick(id, by) {
    const el = slotQ(`.slot[data-id="${id}"]`);
    if (!el || !(by > 0)) return;
    const t = document.createElement('div');
    t.className = 'tick';
    t.textContent = `+${by}%`;
    el.appendChild(t);
    setTimeout(() => t.remove(), 1600);
  }
  // use an ability by id (bar, spellbook, right-click menu) or the fixed Attack/Flee
  function use(id) {
    if (!id) return;
    const el = slotQ(id === 'attack' || id === 'flee' ? `.slot[data-act="${id}"]` : `.slot[data-id="${id}"]`);
    if (el) { el.classList.add('flash'); setTimeout(() => el.classList.remove('flash'), 180); }
    if (id === 'attack') { MH.bus.emit('hud.attack'); return; }
    if (id === 'flee') { MH.bus.emit('hud.flee'); return; }
    const a = st.byId.get(id);
    if (a && !a.known) { toast(`${a.name} unlocks at level ${a.level}`); return; }
    // aimed at a foe (the target), at a friend (a targeted player, else you), or at nothing
    // (yourself, the room, an object you name): sent without a target
    const aim = a ? a.target || 'enemy' : SELF.has(id) ? 'self' : 'enemy';
    MH.bus.emit('hud.ability', { id, name: a && a.name, spell: a ? a.type === 'spell' : false, self: aim !== 'enemy' && aim !== 'ally', ally: aim === 'ally',
      door: aim === 'door',      // Block Door, Break Door: at the nearest closed door (main.js)
      // an area spell /play aims (spells.py AIM_RADIUS): its circle and how far it may land
      radius: a && a.radius, range: a && a.radius ? a.range : undefined });
  }
  // a staggered foe: the bar's heaviest ready attacks glow for a moment (combatcues.js)
  function suggestStrike() {
    const now = (performance.now() - st.cdAt) / 1000;
    const weight = id => {
      const r = recipeFor(RECIPES, id, iconClass, {});
      return (r.flags.has('heavy') ? 2 : 0) + (r.flags.has('shake+') ? 2 : r.flags.has('shake') ? 1 : 0) + (r.flags.has('stop') ? 1 : 0) + (r.land && r.land.big ? 1 : 0);
    };
    const ready = st.bar.filter(Boolean).map(id => st.byId.get(id))
      .filter(a => a && a.known && !a.passive && (a.target || 'enemy') === 'enemy' && (st.cooldowns[a.id] || 0) - now <= 0.05)
      .sort((x, y) => weight(y.id) - weight(x.id));
    for (const a of ready.slice(0, 2)) {
      const el = slotQ(`.slot[data-id="${a.id}"]`);
      if (el) { el.classList.add('suggest'); setTimeout(() => el.classList.remove('suggest'), 2400); }
    }
  }
  // the server says an ability grew (mastery.py): tick it now, before the next payload
  MH.bus.on('ability.improve', ({ id, pct }) => {
    const a = st.byId.get(id);
    if (!a || !(pct > (a.pct || 0))) return;
    const by = pct - (a.pct || 0);
    a.pct = pct;
    const p = st.player;
    if (p) for (const k of ['skills', 'spells']) if (p[k] && id in p[k]) p[k][id] = pct;
    tick(id, by);
    spellbook.update(st.abilities, st.bar, p && p.level);
    if (p) trainer.update({ ...p, abilities: st.abilities });
  });
  const cdTotal = new Map();             // how long each running cooldown was when it started
  const NO_GCD = new Set(['brace', 'sidestep', 'interrupt', 'flee', 'escape', 'evade']);
  function paintCooldowns() {
    const elapsed = (performance.now() - st.cdAt) / 1000;
    const p = st.player;
    // real-time combat: the global cooldown sweeps every skill on the bar (action_combat.py)
    const clock = MH.actionClock;
    const gcd = clock && MH.combatMode === 'action' && MH.state.inCombat ? clock.gcdLeft(performance.now()) / 1000 : 0;
    slotQA('.slot[data-id]').forEach(slot => {
      const id = slot.dataset.id;
      const own = (st.cooldowns[id] || 0) - elapsed;
      const g = NO_GCD.has(id) ? 0 : gcd;
      const left = Math.max(own, g);
      if (g > own && g > 0.05) { cdTotal.set(id, clock.gcd / 1000); slot.dataset.gcd = '1'; }
      else if (own > 0.05) delete slot.dataset.gcd;
      const cd = slot.querySelector('.cd');
      if (!cd) return;
      if (left > 0.05) {
        if (!cdTotal.has(id) || cdTotal.get(id) < left) cdTotal.set(id, Math.max(left, (st.byId.get(id) || {}).cd || left));
        slot.classList.add('cooling');
        cd.style.setProperty('--cd', Math.min(1, left / (cdTotal.get(id) || left)));
        cd.querySelector('span').textContent = left >= 10 ? Math.ceil(left) : left.toFixed(1);
      } else if (slot.classList.contains('cooling')) {
        slot.classList.remove('cooling');
        cdTotal.delete(id);
        // the end of the global cooldown is not news: only a skill's own cooldown flashes ready
        if (slot.dataset.gcd) delete slot.dataset.gcd;
        else {
          slot.classList.add('ready');
          setTimeout(() => slot.classList.remove('ready'), 700);
        }
      }
      // a spell you haven't the mana for
      const a = st.byId.get(id);
      const usesMana = !(p && p.resource && p.resource.max) || CASTERS.has(String((p && p.char_class) || '').toLowerCase());
      const short = !!(a && a.type === 'spell' && a.cost && p && usesMana && (p.mana || 0) < a.cost);
      slot.classList.toggle('nores', short);
    });
  }
  setInterval(paintCooldowns, 100);

  // ---- ranges: the target frame shows the distance; slots out of reach turn red ----
  let ranges = null, lastDist = null;
  function setRanges(d) { ranges = d; }
  function abilityRange(id) {
    if (!ranges) return null;
    if (id === 'attack') {
      // the weapon in hand decides the reach (a bow shoots), else the class
      const look = st.player && st.player.look, k = look && look.main && look.main.k;
      const a = (ranges.weapons && ranges.weapons[k]) || ranges.auto[String(st.player && st.player.char_class || '').toLowerCase()];
      return a ? a.range : ranges.melee;
    }
    const ab = ranges.abilities[id], info = st.byId.get(id);
    if (ab) return /^(self|nova)/.test(ab.shape) ? null : ab.range;
    if (info && info.target === 'self') return null;
    return info && info.type === 'spell' ? ranges.spellDefault : ranges.melee;
  }
  // what can strike from where the hero stands: anything in the same room; across an open way
  // into the next room (opt.across), only what strikes from afar (a bow, a bolt, a ranged or aimed
  // ability: reach.py pulls the creature in)
  function strikesFrom(id, sameRoom, opt) {
    if (sameRoom) return true;
    if (!opt) return false;
    const ab = ranges && ranges.abilities[id];
    if (ab && ab.shape === 'dash') return !!opt.leap;          // a leap or a charge carries the hero over
    if (!opt.across) return false;
    if (id === 'attack') return !!opt.ranged;
    const info = st.byId.get(id) || {};
    if (info.target && info.target !== 'enemy') return false;   // a heal, a blessing, on oneself: never
    return ab ? /^(ranged|blast)/.test(ab.shape) : (st.byId.get(id) || {}).type === 'spell';
  }
  function setDistance(d, sameRoom, opt = {}) {
    const sub = els.tf.querySelector('.tdist') || (() => { const x = document.createElement('div'); x.className = 'tdist'; els.tf.appendChild(x); return x; })();
    if (d == null || els.tf.classList.contains('hidden')) { sub.textContent = ''; lastDist = null; return; }
    const r = Math.round(d * 2) / 2, sig = `${r}|${sameRoom}|${!!opt.across}|${!!opt.leap}`;
    if (sig === lastDist) return;
    lastDist = sig;
    const reach = abilityRange('attack');
    const near = reach != null && d <= reach + 0.3 && strikesFrom('attack', sameRoom, opt);
    const hostile = st.target && st.target.hostile;
    const where = sameRoom ? '' : opt.across || opt.leap ? ' · next room' : ' · another room';
    sub.textContent = `${r.toFixed(r < 10 ? 1 : 0)} m${where}${reach != null ? (near ? (hostile && !MH.state.inCombat ? ' · in reach — press F to attack' : ' · in reach') : ` · reach ${reach} m`) : ''}`;
    sub.className = 'tdist' + (near ? ' ok' : '');
    slotQA('.slot[data-id], .slot[data-act="attack"]').forEach(el => {
      const id = el.dataset.id || 'attack', rng = abilityRange(id);
      el.classList.toggle('far', rng != null && (d > rng + 0.3 || !strikesFrom(id, sameRoom, opt)));
    });
  }

  // ---- target ----
  let targetKey = '';
  // ---- charges a class builds beside its mana (a mage's arcane charges): pips under the bars.
  // A charge gained pops in; spending them flares the row as they go into the spell ----
  let pipsShown = -1;
  function paintPips(ch, spent) {
    const el = els.pf.querySelector('.pips');
    if (!ch || !ch.max) { el.classList.add('hidden'); pipsShown = -1; return; }
    el.classList.remove('hidden');
    el.dataset.res = ch.name || 'arcane';
    el.title = `${ch.label || 'Charges'}: ${ch.value} / ${ch.max}`;
    if (el.childElementCount !== ch.max) el.innerHTML = '<i></i>'.repeat(ch.max);
    [...el.children].forEach((pip, i) => {
      const on = i < ch.value;
      if (on && !pip.classList.contains('on') && pipsShown >= 0 && i >= pipsShown) { pip.classList.remove('pop'); void pip.offsetWidth; pip.classList.add('pop'); }
      pip.classList.toggle('on', on);
    });
    if (spent) { el.classList.remove('spent'); void el.offsetWidth; el.classList.add('spent'); }
    pipsShown = ch.value;
  }
  // a 'res' event (combat_hooks._watch_charges): the pips change at once, before any refresh
  function setCharges(e) {
    const p = st.player;
    const ch = { name: e.name, label: (p && p.charges && p.charges.label) || 'Arcane Charges', value: e.v, max: e.max };
    if (p) p.charges = ch;
    paintPips(ch, e.spent);
  }
  // ---- what lingers on the target (a burn, a poison, a slow): chips under its health bar, from
  // the zone map (map_system._ailments) and from the ticks seen since (combat.js tick) ----
  function noteAilment(ent, name, school) {
    if (!ent || !ent.data || !name) return;
    const seen = ent.data.ailSeen || (ent.data.ailSeen = {});
    seen[name] = { s: school, until: performance.now() + 7000 };
    if (st.target && st.target.id != null && st.target.id === ent.data.id) setTarget({ ...st.target, ailSeen: seen });
  }
  function paintAilments(t) {
    const el = els.tf.querySelector('.tails');
    const now = performance.now(), list = new Map();
    for (const a of (t && t.ails) || []) list.set(a.n, { n: a.n, s: a.s, r: a.r });
    for (const [n, v] of Object.entries((t && t.ailSeen) || {})) if (v.until > now && !list.has(n)) list.set(n, { n, s: v.s });
    const html = [...list.values()].slice(0, 6).map(a => `<span class="ail s-${esc(a.s || 'none')}" title="${esc(a.n)}${a.r ? ` · ${a.r} more ticks` : ''}">${esc((a.n || '?').trim().charAt(0).toUpperCase())}</span>`).join('');
    if (el.innerHTML !== html) el.innerHTML = html;
  }
  // ---- a kill's reward, drawn (combat.js reward): the XP bar fills as its gain rises over it,
  // with the bonuses as chips; coins fly from the fallen creature to the pack; a change in
  // standing with a faction is a small card. The log keeps the words in its Combat tab ----
  const rewardsEl = $('#rewards');
  function floatOver(anchor, cls, html, life = 2200) {
    const r = anchor.getBoundingClientRect();
    const d = document.createElement('div');
    d.className = `rw-float ${cls}`;
    d.innerHTML = html;
    d.style.left = `${r.left + r.width / 2}px`; d.style.top = `${r.top}px`;
    document.body.appendChild(d);
    setTimeout(() => d.remove(), life);
  }
  function reward(e, from) {
    if (e.k === 'xp') {
      const bar = $('#xpbar');
      if (e.next > e.floor) bar.querySelector('b').style.width = pct((e.exp || 0) - e.floor, e.next - e.floor);
      bar.classList.remove('gain'); void bar.offsetWidth; bar.classList.add('gain');
      // (the amount and its bonuses rise in the middle of the screen: combat.js reward)
      if (st.player) st.player.exp = e.exp;
    } else if (e.k === 'gold') {
      const bag = els.menu.querySelector('[data-act="inventory"]');
      const to = bag.getBoundingClientRect();
      const start = from || { x: innerWidth / 2, y: innerHeight / 2 };
      const n = Math.min(10, 3 + Math.floor(e.amt / 60));
      for (let i = 0; i < n; i++) {
        const c = document.createElement('div');
        c.className = 'rw-coin';
        document.body.appendChild(c);
        const sx = start.x + (Math.random() - 0.5) * 40, sy = start.y + (Math.random() - 0.5) * 30;
        const mx = (sx + to.left + to.width / 2) / 2 + (Math.random() - 0.5) * 160, my = Math.min(sy, to.top) - 80 - Math.random() * 80;
        const a = c.animate([
          { transform: `translate(${sx}px, ${sy}px) scale(.6)`, opacity: 0 },
          { transform: `translate(${sx}px, ${sy - 30}px) scale(1)`, opacity: 1, offset: 0.15 },
          { transform: `translate(${mx}px, ${my}px) scale(1.1)`, opacity: 1, offset: 0.55 },
          { transform: `translate(${to.left + to.width / 2}px, ${to.top + to.height / 2}px) scale(.5)`, opacity: 0.9 },
        ], { duration: 900 + i * 40, delay: i * 70, easing: 'cubic-bezier(.4,.1,.5,1)', fill: 'forwards' });
        a.onfinish = () => c.remove();
      }
      setTimeout(() => { bag.classList.remove('rw-pop'); void bag.offsetWidth; bag.classList.add('rw-pop'); }, 900 + n * 70);
      if (st.player && e.total != null) st.player.gold = e.total;
    } else if (e.k === 'rep') {
      const d = document.createElement('div');
      d.className = `rw-rep${e.amt < 0 ? ' down' : ''}${e.changed ? ' changed' : ''}`;
      d.innerHTML = `<b>${esc(e.faction)}</b> <em>${e.amt > 0 ? '+' : ''}${e.amt}</em><span>${e.changed ? 'now ' : ''}${esc(e.standing)}</span>`;
      rewardsEl.appendChild(d);
      while (rewardsEl.childElementCount > 4) rewardsEl.firstChild.remove();
      setTimeout(() => d.remove(), e.changed ? 5200 : 3400);
    }
  }
  function setTarget(t) {
    st.target = t;
    els.tf.classList.toggle('hidden', !t);
    if (!t) { targetKey = ''; targetCast(null); return; }
    // a corpse Tab aimed at after a fight (main.js): F loots it
    if (t.kind === 'corpse') {
      els.tf.className = 'hud panel ornate neutral corpse';
      els.tf.querySelector('.tname').textContent = t.name;
      els.tf.querySelector('.lvl').textContent = '';
      els.tf.querySelector('.tsub').textContent = 'Corpse · F to loot';
      vbar(els.tf.querySelector('.vbar.hp'), 0, 1);
      els.tf.querySelector('.vbar.hp span').textContent = '';
      const key = `c:${t.key}`;
      if (key !== targetKey) {
        targetKey = key;
        targetCast(null);
        const img = els.tf.querySelector('.face');
        img.classList.remove('on');
        creaturePortrait({ name: t.victim, short: t.victim }).then(url => { if (url && targetKey === key) { img.src = url; img.classList.add('on'); } });
      }
      return;
    }
    const me = st.player ? st.player.level || 1 : 1;
    const con = t.kind === 'player' ? { key: 'ally', label: 'Player' } : conOf(t.level || 1, me);
    const kind = t.kind === 'player' ? 'ally' : t.hostile ? 'hostile' : (t.shopkeeper || t.trainer) ? 'npc' : 'neutral';
    els.tf.className = `hud panel ornate ${kind} con-${con.key}${t.boss ? ' boss' : ''}`;
    els.tf.querySelector('.tname').textContent = shownName(t, t.kind);
    els.tf.querySelector('.lvl').textContent = t.kind === 'player' ? (t.level || '') : (t.level || '?');
    const role = t.shopkeeper ? ' · shopkeeper' : t.trainer ? ' · trainer' : t.boss ? ' · boss' : t.rank === 'sub-boss' ? ' · sub-boss' : t.rank === 'elite' ? ' · elite' : '';
    els.tf.querySelector('.tsub').textContent = `${t.kind === 'player' ? `Level ${t.level || '?'} ${t.char_class || ''}` : `Level ${t.level || '?'} · ${con.label}`}${role}`;
    vbar(els.tf.querySelector('.vbar.hp'), t.maxHp ? t.hp : 1, t.maxHp || 1);
    // whom it is fighting (target of target): you, a friend, or someone else
    const tot = els.tf.querySelector('.ttot');
    if (tot) {
      const who = t.kind !== 'player' && t.fighting_name;
      const me = String(MH.state.playerName || '').toLowerCase();
      tot.classList.toggle('hidden', !who);
      if (who) { tot.textContent = `⟶ ${String(who).toLowerCase() === me ? 'you' : who}`; tot.classList.toggle('you', String(who).toLowerCase() === me); }
    }
    if (!t.maxHp) els.tf.querySelector('.vbar.hp span').textContent = '';
    paintAilments(t);
    // its portrait, once per target
    const key = t.kind === 'player' ? `p:${t.name}` : `m:${t.id}`;
    if (key !== targetKey) {
      targetKey = key;
      const img = els.tf.querySelector('.face');
      img.classList.remove('on');
      targetCast(null);
      const shot = t.kind === 'player' ? lookPortrait(t.look, t.char_class) : creaturePortrait(t);
      shot.then(url => { if (url && targetKey === key) { img.src = url; img.classList.add('on'); } });
    }
  }
  els.tf.querySelector('.tclose').addEventListener('click', () => MH.bus.emit('hud.untarget'));
  // the target gathers itself for a big blow: its wind-up as a cast bar ("Crushing Blow")
  let castTimer = 0;
  function targetCast(c) {
    const el = els.tf.querySelector('.tcast');
    clearTimeout(castTimer);
    if (!c) { el.classList.add('hidden'); return; }
    if (c.end) {
      el.classList.add(c.end === 'broken' ? 'broken' : 'landed');
      el.querySelector('em').textContent = c.end === 'broken' ? 'Interrupted!' : '';
      castTimer = setTimeout(() => el.classList.add('hidden'), 650);
      return;
    }
    el.className = 'tcast';
    el.querySelector('span').textContent = c.label || 'Winding up';
    el.querySelector('em').textContent = '';
    const b = el.querySelector('b');
    b.style.transition = 'none'; b.style.width = '0%';
    requestAnimationFrame(() => requestAnimationFrame(() => { b.style.transition = `width ${Math.max(0.3, (c.ms || 1500) / 1000)}s linear`; b.style.width = '100%'; }));
    castTimer = setTimeout(() => el.classList.add('hidden'), (c.ms || 1500) + 1200);
  }

  // ---- banner + toasts ----
  let bannerTimer = 0;
  function banner(room, zone) {
    // mid-fight a room's name would sit on the fight; a new region still announces itself
    if (MH.state.inCombat && !zone) return;
    els.banner.querySelector('.zone').textContent = zone || '';
    els.banner.querySelector('.room').textContent = room || '';
    els.banner.style.opacity = 1;
    clearTimeout(bannerTimer);
    bannerTimer = setTimeout(() => { els.banner.style.opacity = 0; }, zone ? 3200 : 1800);
  }
  // the world's news, large and gilded for a few seconds: an achievement, a rare creature sighted
  let heraldTimer = 0;
  function herald({ kicker = '', title = '', sub = '', tone = '' } = {}) {
    const el = document.getElementById('herald');
    if (!el) return toast(`${kicker} ${title}`);
    el.className = `hud on ${tone}`;
    el.querySelector('.hd-k').textContent = kicker;
    el.querySelector('.hd-t').textContent = title;
    el.querySelector('.hd-s').textContent = sub;
    clearTimeout(heraldTimer);
    heraldTimer = setTimeout(() => { el.className = `hud ${tone}`; }, 5200);
  }
  function toast(msg, ms = 2900) {
    if (!msg) return;
    sound.play('toast');
    const d = document.createElement('div');
    d.className = 'toast';
    d.textContent = msg;
    els.toasts.appendChild(d);
    while (els.toasts.children.length > 3) els.toasts.firstChild.remove();
    setTimeout(() => d.remove(), ms);
  }

  // ---- chat log + command line ----
  const PROMPT = /^\s*<?\s*\d+\/\d+\s*hp\b[^\n]*>\s*$/i;
  let stick = true;
  els.log.addEventListener('scroll', () => { stick = els.log.scrollTop + els.log.clientHeight >= els.log.scrollHeight - 30; });
  // what kind of line it is, for the chat tabs (All / Group / Say / Tells)
  let tellFrom = '';
  function lineKind(text) {
    if (/^You tell the group,|^\w+ tells the group,/.test(text)) return 'group';
    const t = text.match(/^(\w+) tells you,/);
    if (t) { tellFrom = t[1]; return 'tell'; }
    if (/^You tell \w+,/.test(text)) return 'tell';
    if (/^You say,|^\w+ says,|^You say '|^\w+ says '/.test(text)) return 'say';
    return '';
  }
  function log(html, cls, sort) {
    const atBottom = stick;
    const d = document.createElement('div');
    if (cls) { d.className = cls; d.textContent = html; } else d.innerHTML = html;
    if (sort) d.classList.add(`k-${sort}`);      // msgkind.py: combat, reward
    const kind = lineKind(d.textContent.trim());
    if (kind) {
      d.classList.add(`l-${kind}`);
      const tab = document.querySelector(`#chat .chat-tabs [data-tab="${kind}"]`);
      if (tab && els.log.dataset.tab !== kind) tab.classList.add('new');
    }
    els.log.appendChild(d);
    while (els.log.childElementCount > 400) els.log.firstChild.remove();
    if (atBottom) els.log.scrollTop = els.log.scrollHeight;
  }
  // a telnet box (frames.js) coming in a line or a few at a time: gathered in one block of the
  // log, drawn again as each line comes, until a line that is not part of it
  let box = null;
  function boxLine(html, text, sort) {
    const atBottom = stick;
    if (!box || !box.el.isConnected) {
      const d = document.createElement('div');
      d.className = 'tx-block';
      if (sort) d.classList.add(`k-${sort}`);
      // a rule, a short line, a rule: a heading ("═══\n Your Worth \n═══"); the rule that
      // closes it draws nothing more unless a box goes on from it
      const title = els.log.lastElementChild, above = title && title.previousElementSibling;
      const closes = title && !title.className && isTitle(title.textContent) && above && above._lines
        && above._lines.length === 1 && classify(text).t === 'rule';
      if (closes) {
        above.innerHTML = `<div class="tx-head">${escHtml(title.textContent.trim())}</div>`;
        above._lines = null;
        title.remove();
      }
      els.log.appendChild(d);
      box = { el: d, lines: [], closer: !!closes };
      d._lines = box.lines;
    }
    box.lines.push({ html, text });
    const shown = box.closer ? box.lines.slice(1) : box.lines;
    box.el.innerHTML = shown.length ? renderBox(shown) : '';
    if (atBottom) els.log.scrollTop = els.log.scrollHeight;
  }
  const escHtml = s => String(s).replace(/[&<>"]/g, c => ({ '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;' }[c]));
  MH.bus.on('terminal.output', ({ html }) => {
    if (!html || !MH.state.isLoggedIn) return;
    const plain = l => l.replace(/<[^>]+>/g, '').replace(/&gt;/g, '>').replace(/&lt;/g, '<').replace(/&amp;/g, '&');
    // (a prompt a line begins with goes: the HUD shows those numbers; frames.js unprompt)
    const lines = String(html).split(/\r?\n/).filter(l => !PROMPT.test(plain(l))).map(unprompt).filter(l => plain(l).trim());
    for (const g of splitByKind(lines)) {
      for (const line of g.html.split('\n')) {
        const text = plain(line);
        if (inBox(text)) { cols = null; boxLine(line, text, g.kind); continue; }
        box = null;
        // a list set in columns, gathered the same way (frames.js renderCols), an indented line
        // amid it one of its rows
        const k = classify(text).t;
        if (k === 'cols' || (k === 'text' && inList(text) && cols && cols.el.isConnected)) { colsLine(line, text, g.kind); continue; }
        cols = null;
        const one = renderLine({ html: line, text });
        if (one) { log(one, null, g.kind); continue; }
        log(meters(line), null, g.kind);
      }
    }
  });
  let cols = null;
  function colsLine(html, text, sort) {
    const atBottom = stick;
    if (!cols || !cols.el.isConnected) {
      const d = document.createElement('div');
      d.className = 'tx-block';
      if (sort) d.classList.add(`k-${sort}`);
      els.log.appendChild(d);
      cols = { el: d, lines: [] };
    }
    cols.lines.push({ html, text });
    cols.el.innerHTML = renderCols(cols.lines);
    if (atBottom) els.log.scrollTop = els.log.scrollHeight;
  }
  MH.bus.on('terminal.echo', () => { box = null; cols = null; });
  // a command typed shows as typed; one the bar sent for a fight goes with the fight ({ text, kind })
  MH.bus.on('terminal.echo', cmd => (typeof cmd === 'object' ? log(`> ${cmd.text}`, 'cmd', cmd.kind) : log(`> ${cmd}`, 'cmd')));
  // tabs filter the log; the mode chip decides what Enter does with plain text
  document.querySelectorAll('#chat .chat-tabs button').forEach(b => b.addEventListener('click', () => {
    els.log.dataset.tab = b.dataset.tab;
    document.querySelectorAll('#chat .chat-tabs button').forEach(x => x.classList.toggle('on', x === b));
    b.classList.remove('new');
    els.log.scrollTop = els.log.scrollHeight;
  }));
  const MODES = ['cmd', 'say', 'group', 'tell'];
  let mode = 'cmd';
  const modeBtn = $('#chat-mode');
  function setMode(m) {
    mode = m;
    modeBtn.textContent = { cmd: 'Cmd', say: 'Say', group: 'Group', tell: tellFrom ? `→ ${tellFrom}` : 'Tell' }[m];
    els.input.placeholder = m === 'cmd' ? 'Press Enter to talk or type a command…' : m === 'tell' && !tellFrom ? 'Tell whom? Start with their name…'
      : `${m === 'say' ? 'Say' : m === 'group' ? 'Tell the group' : `Tell ${tellFrom}`} — or start with / for a command`;
  }
  modeBtn.addEventListener('click', () => setMode(MODES[(MODES.indexOf(mode) + 1) % MODES.length]));
  function framed(v) {
    if (mode === 'cmd' || v.startsWith('/')) return v.replace(/^\//, '');
    if (mode === 'say') return `say ${v}`;
    if (mode === 'group') return `gtell ${v}`;
    return tellFrom ? `tell ${tellFrom} ${v}` : `tell ${v}`;
  }
  els.input.addEventListener('keydown', e => {
    if (e.key === 'Enter') {
      const raw = els.input.value.trim(), v = raw && framed(raw);
      // `help` and `help <topic>`: the Help window (H), not the telnet's paged index in the log
      const asked = v && v.match(/^help(?:\s+(.+))?$/i);
      if (asked) { help.show(asked[1] || ''); st.history.unshift(raw); }
      // `map` and `minimap`: the Map window (M), not the telnet's map drawn in letters
      else if (v && /^(?:mini)?map$/i.test(v)) { MH.bus.emit('hud.map'); st.history.unshift(raw); }
      // `clear` / `cls`: the log emptied (a terminal's clear-screen code means nothing here)
      else if (v && /^(?:clear|cls)$/i.test(v)) { els.log.innerHTML = ''; box = null; cols = null; st.history.unshift(raw); }
      else if (v) { MH.sendCommand(v); if (!MH.secretLine(raw)) { st.history.unshift(raw); st.history.length = Math.min(st.history.length, 50); } }
      st.hi = -1;
      els.input.value = '';
      els.input.blur();
      e.preventDefault();
    } else if (e.key === 'Escape') { els.input.value = ''; els.input.blur(); }
    else if (e.key === 'ArrowUp' && st.history.length) { st.hi = Math.min(st.hi + 1, st.history.length - 1); els.input.value = st.history[st.hi]; e.preventDefault(); }
    else if (e.key === 'ArrowDown') { st.hi = Math.max(st.hi - 1, -1); els.input.value = st.hi >= 0 ? st.history[st.hi] : ''; e.preventDefault(); }
    e.stopPropagation();
  });

  // ---- menu + settings ----
  els.menu.querySelectorAll('button[data-icon]').forEach(b => {
    b.innerHTML = `<img alt="" src="${uiIcon(b.dataset.icon, { size: 72 })}"><kbd>${esc(b.dataset.key || '')}</kbd>`;
    b.dataset.tipTitle = b.dataset.tip; b.dataset.tipSub = b.dataset.key ? `Key: ${b.dataset.key}` : '';
  });
  els.menu.querySelector('[data-act="settings"]').addEventListener('click', () => els.settings.classList.toggle('hidden'));
  // a window opened tells the server (`uiseen`): the tutorial's "type score" steps count it
  for (const [w, name] of [[inventory, 'inventory'], [character, 'character'], [spellbook, 'spellbook'], [journal, 'journal'], [who, 'who'], [shop, 'shop']]) {
    const toggle = w.toggle.bind(w);
    w.toggle = (...a) => { const was = w.open; const r = toggle(...a); if (w.open && !was) MH.sendCommand(`uiseen ${name}`, false); return r; };
  }
  els.menu.querySelector('[data-act="inventory"]').addEventListener('click', () => inventory.toggle());
  els.menu.querySelector('[data-act="character"]').addEventListener('click', () => character.toggle());
  els.menu.querySelector('[data-act="abilities"]').addEventListener('click', () => spellbook.toggle());
  els.menu.querySelector('[data-act="journal"]').addEventListener('click', () => journal.toggle());
  els.menu.querySelector('[data-act="map"]').addEventListener('click', () => MH.bus.emit('hud.map'));
  els.menu.querySelector('[data-act="who"]').addEventListener('click', () => who.toggle(undefined, me()));
  els.menu.querySelector('[data-act="help"]').addEventListener('click', () => help.toggle());
  els.menu.querySelector('[data-act="ride"]').addEventListener('click', () => rideToggle());
  for (const [name, win] of Object.entries(PROGRESS)) els.menu.querySelector(`[data-act="${name}"]`).addEventListener('click', () => win.toggle());
  const syncSettings = () => {
    const q = ls.get('mh3d_quality') || 'high', u = ls.get('mh3d_ui') || 'auto';
    els.settings.querySelectorAll('[data-set="quality"] button').forEach(b => b.classList.toggle('on', b.dataset.v === q));
    els.settings.querySelectorAll('[data-set="ui"] button').forEach(b => b.classList.toggle('on', b.dataset.v === u));
    const kb = ls.get('mh3d_bodies') === 'classic' ? 'classic' : 'kin';
    els.settings.querySelectorAll('[data-set="bodies"] button').forEach(b => b.classList.toggle('on', b.dataset.v === kb));
    els.settings.querySelectorAll('[data-set="xbars"] button').forEach(b => b.classList.toggle('on', +b.dataset.v === bars.count));
    // combat numbers (fx.js opts): where they show, how big, whether the view shakes
    const sct = ls.get('mh3d_sct') || 'all', ssz = ls.get('mh3d_sctsize') || '1', shk = ls.get('mh3d_shake') === 'off' ? 'off' : 'on';
    const slf = ls.get('mh3d_sctlife') || '1';
    els.settings.querySelectorAll('[data-set="sctlife"] button').forEach(b => b.classList.toggle('on', b.dataset.v === slf));
    els.settings.querySelectorAll('[data-set="sct"] button').forEach(b => b.classList.toggle('on', b.dataset.v === sct));
    els.settings.querySelectorAll('[data-set="sctsize"] button').forEach(b => b.classList.toggle('on', b.dataset.v === ssz));
    els.settings.querySelectorAll('[data-set="shake"] button').forEach(b => b.classList.toggle('on', b.dataset.v === shk));
    MH.bus.emit('settings.sct', { sct, size: +ssz || 1, shake: shk === 'on', life: +slf || 1 });
    const br = ls.get('mh3d_bright') || '1';
    els.settings.querySelectorAll('[data-set="bright"] button').forEach(b => b.classList.toggle('on', b.dataset.v === br));
    MH.bus.emit('settings.brightness', +br || 1);
    const ct = ls.get('mh3d_combattext') === 'on' ? 'on' : 'off';
    els.settings.querySelectorAll('[data-set="combattext"] button').forEach(b => b.classList.toggle('on', b.dataset.v === ct));
    els.log.classList.toggle('with-combat', ct === 'on');
    const cap = ls.get('mh3d_ambcap') === 'on' ? 'on' : 'off';
    els.settings.querySelectorAll('[data-set="ambcap"] button').forEach(b => b.classList.toggle('on', b.dataset.v === cap));
  };
  for (const [key, store] of [['sct', 'mh3d_sct'], ['sctsize', 'mh3d_sctsize'], ['sctlife', 'mh3d_sctlife'], ['shake', 'mh3d_shake'], ['bright', 'mh3d_bright']]) {
    els.settings.querySelectorAll(`[data-set="${key}"] button`).forEach(b => b.addEventListener('click', () => { ls.set(store, b.dataset.v); syncSettings(); }));
  }
  // what each colour of number means
  $('#sct-key').innerHTML = Object.entries(SCHOOL_CSS).map(([k, c]) => `<i style="background:${c}" title="${k[0].toUpperCase() + k.slice(1)}"></i>`).join('');
  // the blow-by-blow in the All tab too (it is drawn; the Combat tab always has it)
  els.settings.querySelectorAll('[data-set="combattext"] button').forEach(b => b.addEventListener('click', () => {
    ls.set('mh3d_combattext', b.dataset.v); syncSettings(); els.log.scrollTop = els.log.scrollHeight;
  }));
  // the world's murmurs as a line of text too (hud/ambient.js)
  els.settings.querySelectorAll('[data-set="ambcap"] button').forEach(b => b.addEventListener('click', () => {
    ls.set('mh3d_ambcap', b.dataset.v); syncSettings();
  }));
  // how many extra bars show (bars.js; kept per character on this device)
  els.settings.querySelectorAll('[data-set="xbars"] button').forEach(b => b.addEventListener('click', () => {
    bars.setCount(+b.dataset.v); syncSettings();
  }));
  els.settings.querySelectorAll('[data-set="bodies"] button').forEach(b => b.addEventListener('click', () => {
    ls.set('mh3d_bodies', b.dataset.v); syncSettings();
  }));
  els.settings.querySelectorAll('[data-set="quality"] button').forEach(b => b.addEventListener('click', () => {
    ls.set('mh3d_quality', b.dataset.v); syncSettings();
    MH.bus.emit('hud.quality', b.dataset.v);
  }));
  els.settings.querySelectorAll('[data-set="ui"] button').forEach(b => b.addEventListener('click', () => {
    ls.set('mh3d_ui', b.dataset.v); applyScale(); syncSettings();
  }));
  els.settings.querySelector('[data-act="perf"]').addEventListener('click', () => window.dispatchEvent(new KeyboardEvent('keydown', { key: 'F3' })));
  els.settings.querySelector('[data-act="camreset"]').addEventListener('click', () => MH.bus.emit('hud.cameraReset'));
  // sound: a master switch and a slider per bus (audio.js keeps them in localStorage)
  const muteBtn = els.settings.querySelector('[data-act="mute"]');
  const syncSound = () => {
    muteBtn.textContent = sound.muted ? 'Off' : 'On';
    muteBtn.classList.toggle('on', !sound.muted);
    els.settings.querySelectorAll('[data-vol]').forEach(r => { r.value = Math.round(sound.vol[r.dataset.vol] * 100); });
  };
  muteBtn.addEventListener('click', () => { sound.setMuted(!sound.muted); syncSound(); sound.play('ui_toggle'); });
  els.settings.querySelectorAll('[data-vol]').forEach(r => {
    r.addEventListener('input', () => sound.setVolume(r.dataset.vol, r.value / 100));
    // let go of a slider: hear what it sets
    r.addEventListener('change', () => sound.play({ sfx: 'hit', master: 'ui_confirm' }[r.dataset.vol] || 'ui_click'));
    r.addEventListener('keydown', e => e.stopPropagation());
  });
  syncSound();
  els.settings.querySelector('[data-act="logout"]').addEventListener('click', () => {
    if (!MH.logout()) toast('Finish the fight before you log out.');
  });
  syncSettings();
  // auto-loot (a kill's things) and loot gold (its gold), each the server's own setting
  const LOOTS = [['autoloot', 'autoloot', 'autoloot'], ['autolootgold', 'autoloot_gold', 'autoloot gold']];
  const syncLoot = () => LOOTS.forEach(([set, field]) => {
    const seg = els.settings.querySelector(`[data-set="${set}"]`);
    if (seg) seg.querySelectorAll('button').forEach(b => b.classList.toggle('on', (b.dataset.v === 'on') === !!(MH.state.player && MH.state.player[field])));
  });
  LOOTS.forEach(([set, field, cmd]) => {
    const seg = els.settings.querySelector(`[data-set="${set}"]`);
    if (seg) seg.querySelectorAll('button').forEach(b => b.addEventListener('click', () => {
      MH.sendCommand(`${cmd} ${b.dataset.v}`);
      if (MH.state.player) MH.state.player[field] = b.dataset.v === 'on';
      syncLoot();
    }));
  });
  MH.bus.on('map', syncLoot);

  // ---- real-time combat: the swing ring on the attack button, a press refused mid-cooldown ----
  (function ring() {
    requestAnimationFrame(ring);
    const clock = MH.actionClock;
    // (the bar is rebuilt as it changes: find the button's ring each frame)
    const swingEl = els.slots.querySelector('.slot[data-act="attack"] .swing');
    const on = !!(clock && MH.combatMode === 'action' && MH.state.inCombat && swingEl);
    if (swingEl) swingEl.parentElement.classList.toggle('rt', on);
    if (!on) return;
    const now = performance.now();
    swingEl.style.setProperty('--sw', clock.progress(now).toFixed(3));
    swingEl.parentElement.classList.toggle('perfect', clock.inPerfect(now));
    swingEl.parentElement.classList.toggle('queued', clock.queued && !clock.ready(now));
  })();
  function flashSlot(id, kind = 'busy') {
    const el = slotQ(`.slot[data-id="${id}"]`);
    if (!el) return;
    el.classList.add(kind);
    setTimeout(() => el.classList.remove(kind), 320);
  }
  // Settings: real time (on by default) or the 3-s round
  const rtSeg = els.settings.querySelector('[data-set="combat"]');
  const syncRt = () => rtSeg && rtSeg.querySelectorAll('button').forEach(b => b.classList.toggle('on', (b.dataset.v === 'action') === (MH.combatMode === 'action')));
  if (rtSeg) rtSeg.querySelectorAll('button').forEach(b => b.addEventListener('click', () => {
    MH.combatMode = b.dataset.v === 'action' ? 'action' : null;
    ls.set('mh3d_combat', b.dataset.v === 'action' ? 'action' : 'rounds');
    if (MH.resubscribe) MH.resubscribe();
    syncRt();
    toast(MH.combatMode ? 'Real-time combat: your blows land as you strike' : 'Combat in rounds: a blow every 3 seconds');
  }));
  syncRt();

  // ---- sounds for windows and buttons (audio.js) ----
  // a window sounds as it opens and closes, however it was opened (a key, a button, a link)
  const WINDOW_SOUNDS = { inventory: ['bag_open', 'ui_close'], character: ['cloth', 'ui_close'], spellbook: ['book_open', 'book_close'],
    journal: ['book_open', 'book_close'], trainer: ['book_flip', 'ui_close'], settings: ['ui_open', 'ui_close'], bigmap: ['ui_open', 'ui_close'],
    shop: ['coins', 'ui_close'], lootwin: ['leather', 'ui_close'], talk: ['ui_offer', 'ui_close'], who: ['ui_open', 'ui_close'], help: ['book_open', 'book_close'],
    talents: ['book_open', 'book_close'], almanac: ['book_open', 'book_close'], travel: ['ui_open', 'ui_close'], stable: ['leather', 'ui_close'],
    services: ['coins', 'ui_close'], legend: ['book_open', 'book_close'] };
  for (const [id, [on, off]] of Object.entries(WINDOW_SOUNDS)) {
    const el = document.getElementById(id);
    if (!el) continue;
    let was = !el.classList.contains('hidden');
    new MutationObserver(() => {
      const now = !el.classList.contains('hidden');
      if (now !== was) { was = now; sound.play(now ? on : off); }
    }).observe(el, { attributes: true, attributeFilter: ['class'] });
  }
  // a click on a window's buttons (not the action bar: abilities make their own sounds)
  document.addEventListener('click', e => {
    const b = e.target && e.target.closest && e.target.closest('.panel button, #create .pick, #login .btn');
    if (b && !b.closest('#actionbar') && !b.matches('[data-act="mute"]')) sound.play('ui_click');
  }, true);
  // gold changes hands: coins
  MH.bus.on('terminal.output', ({ text }) => {
    if (MH.state.isLoggedIn && /\b(?:you (?:get|receive|take|loot|sell|buy)|there (?:was|were))\b[^\n]*\b(?:gold|coins?)\b/i.test(text || '')) sound.play('coins');
  });

  // ---- riding: R (or the menu's horseshoe, or the chip by your portrait) gets you up or down ----
  // The server decides which (`mount toggle`): this page's copy of whether you ride can be a
  // payload behind, and asking for the wrong one did nothing.
  function rideToggle() {
    const p = MH.state.player || {};
    if (!p.mount && !(p.mounts || []).length) { toast('You own no mount: visit a stable (U)'); return; }
    send('mount toggle');
    setTimeout(() => MH.refreshState && MH.refreshState(), 400);
  }
  $('#riding').addEventListener('click', rideToggle);
  function paintRiding(p) {
    const ridingEl = $('#riding'), m = p && p.mount;
    ridingEl.classList.toggle('hidden', !m);
    if (!m) return;
    const html = `<img alt="" src="${uiIcon('horseshoe', { size: 32 })}"><span>Riding <b>${esc(m.name)}</b> · R to dismount</span>`;
    if (ridingEl.innerHTML !== html) ridingEl.innerHTML = html;
  }

  // ---- keys (when not typing) ----
  window.addEventListener('keydown', e => {
    if (e.target && /INPUT|TEXTAREA|SELECT/.test(e.target.tagName)) return;
    if (!MH.state.isLoggedIn) return;
    const k = e.key;
    if (k === 'Enter') { els.input.focus(); e.preventDefault(); return; }
    // (a key held a moment too long repeats: one press is one use)
    if (e.repeat && (k === 'f' || k === 'F' || k === ' ' || /^Digit[1-8]$/.test(e.code || ''))) { e.preventDefault(); return; }
    if (k === 'f' || k === 'F' || k === ' ') { use('attack'); e.preventDefault(); return; }
    // 1-8 and Shift+1-8: the main bar; Alt+1-8 and Alt+Shift+1-8: the extra bars 3 and 4
    const digit = /^Digit([1-8])$/.exec(e.code || '');
    if (digit && !e.ctrlKey && !e.metaKey) {
      const i = slotForKey(+digit[1], { shift: e.shiftKey, alt: e.altKey });
      if (i < MAIN || i - MAIN < 8 * bars.count) use(st.bar[i]);
      e.preventDefault(); return;
    }
    if (k === 'Escape') {
      const mapOpen = !$('#bigmap').classList.contains('hidden');
      const progOpen = Object.values(PROGRESS).some(w => w.open);
      if (inventory.open || character.open || spellbook.open || trainer.open || journal.open || mapOpen || shop.open || lootwin.open || talk.open || who.open || help.open || progOpen) {
        for (const w of Object.values(PROGRESS)) w.toggle(false);
        inventory.toggle(false); character.toggle(false); spellbook.toggle(false); trainer.toggle(false); journal.toggle(false);
        shop.toggle(false); lootwin.toggle(false); talk.toggle(false); who.toggle(false); help.toggle(false);
        MH.bus.emit('hud.map', false); return;
      }
      MH.bus.emit('hud.untarget'); els.settings.classList.add('hidden'); return;
    }
    if ((k === 'i' || k === 'I') && !e.ctrlKey && !e.metaKey) { inventory.toggle(); e.preventDefault(); return; }
    if ((k === 'c' || k === 'C') && !e.ctrlKey && !e.metaKey) { character.toggle(); e.preventDefault(); return; }
    if ((k === 'k' || k === 'K') && !e.ctrlKey && !e.metaKey) { spellbook.toggle(); e.preventDefault(); return; }
    if (k === 'Tab') { MH.bus.emit('hud.cycleTarget'); e.preventDefault(); return; }
    if (e.ctrlKey || e.metaKey || e.altKey) return;
    if (k === 'l' || k === 'L') { journal.toggle(); e.preventDefault(); return; }
    if (k === 'm' || k === 'M') { MH.bus.emit('hud.map'); e.preventDefault(); return; }
    if (k === 'o' || k === 'O') { els.settings.classList.toggle('hidden'); e.preventDefault(); return; }
    if (k === 'p' || k === 'P') { who.toggle(undefined, me()); e.preventDefault(); return; }
    if (k === 'h' || k === 'H') { help.toggle(); e.preventDefault(); return; }
    if (k === 'r' || k === 'R') { rideToggle(); e.preventDefault(); return; }
    const PKEYS = { n: 'talents', y: 'almanac', t: 'travel', u: 'stable', b: 'services', g: 'legend' };
    if (PKEYS[k.toLowerCase()]) { PROGRESS[PKEYS[k.toLowerCase()]].toggle(); e.preventDefault(); }
  });

  // ---- for the right-click menu ----
  // the bar's abilities that aim at someone (not heals on yourself, not shouts)
  function targetSkills() {
    return st.bar.map(id => id && st.byId.get(id)).filter(a => a && a.known && (a.target || 'enemy') === 'enemy')
      .map(a => ({ id: a.id, label: a.name, spell: a.type === 'spell' }));
  }
  function useAbility(id) { use(id); }
  function unslot(i) { if (!st.bar[i]) return; if (locked(i)) lockedToast(); else editBar(takeOffBar(st.bar, i)); }
  function prefill(text) { els.input.value = text; els.input.focus(); }
  function openPanel(name) { if (name === 'inventory') inventory.toggle(true); else if (name === 'character') character.toggle(true); else if (name === 'mail') services.show('mail'); }
  function openTrainer(name) { trainer.toggle(true, name || ''); if (MH.refreshState) MH.refreshState(); }
  function openShop(kw) { shop.toggle(true, kw || ''); }
  // give someone something: a short list of what you carry, by the word the MUD knows it by
  function giveTo(name, x, y) {
    const bag = ((MH.state.player || {}).inventory || []);
    const el = $('#give-pick');
    if (!bag.length) { toast('You carry nothing to give.'); return; }
    const word = (it, list) => { const kw = String(it.name || it.short || 'item').toLowerCase().split(/\s+/).find(w => w.length > 1) || 'item';
      let n = 0; for (const o of list) { if (String(o.name || o.short || '').toLowerCase().split(/\s+/).includes(kw)) n++; if (o === it) break; } return n > 1 ? `${n}.${kw}` : kw; };
    el.innerHTML = `<div class="gp-title">Give ${esc(name)}…</div>` + bag.slice(0, 24).map((it, i) => `<button data-i="${i}">${esc(it.short || it.name)}</button>`).join('')
      + '<button data-i="gold">Some gold…</button>';
    el.style.left = `${Math.min(x, innerWidth - 240)}px`; el.style.top = `${Math.min(y, innerHeight - 320)}px`;
    el.classList.remove('hidden');
    el.querySelectorAll('button').forEach(b => b.addEventListener('click', () => {
      el.classList.add('hidden');
      if (b.dataset.i === 'gold') { prefill(`give  coins ${name}`); return; }
      MH.sendCommand(`give ${word(bag[+b.dataset.i], bag)} ${name}`);
    }));
    setTimeout(() => document.addEventListener('pointerdown', function off(e) { if (!el.contains(e.target)) { el.classList.add('hidden'); document.removeEventListener('pointerdown', off); } }), 0);
  }
  function openTalk(name, kw) { talk.toggle(true, name, kw); }
  // a conversation stays in its room: leave (or be ferried off) and it closes
  function closeTalk() { if (talk.open) talk.toggle(false); }
  // whisper someone: the chat input set to tell them
  function whisper(name) { tellFrom = name; setMode('tell'); els.input.focus(); }

  return { showGame, setPlayer, setTarget, setCharges, noteAilment, reward, targetCast, moment, fallen, suggestStrike, setRanges, setDistance, banner, herald, toast, log, targetSkills, useAbility, prefill, openPanel, openTrainer, openShop, openTalk, closeTalk, lootwin, giveTo, flashSlot,
    spellbook, unslot, party, quest, whisper, get player() { return st.player; }, get bar() { return st.bar.slice(); } };
}
