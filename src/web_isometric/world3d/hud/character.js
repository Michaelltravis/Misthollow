// Character sheet (C): the hero turning in a portrait, vitals, the six attributes, combat
// numbers, experience and active effects; a second tab lists skills and spells with their
// proficiency (the class's whole roster, unlearned ones dimmed); a third works out a fight: what
// your blows and guard come to and how a bout with a creature would go (combatcalc.js). Everything
// comes from the map payload's player block; nothing here changes the character.
import { makeStage } from './stage.js';
import { fight, typicalFoe } from './combatcalc.js';

const $ = s => document.querySelector(s);
const esc = s => String(s == null ? '' : s).replace(/[&<>"]/g, c => ({ '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;' }[c]));
const ATTRS = [['str', 'Strength'], ['int', 'Intelligence'], ['wis', 'Wisdom'], ['dex', 'Dexterity'], ['con', 'Constitution'], ['cha', 'Charisma']];
const PRIME = { warrior: 'str', paladin: 'str', mage: 'int', necromancer: 'int', cleric: 'wis', thief: 'dex', ranger: 'dex', assassin: 'dex', bard: 'cha' };
const title = s => String(s || '').replace(/_/g, ' ').replace(/\b\w/g, c => c.toUpperCase());

// what worn gear adds to a maximum (counted in it already), as a note beside its label
const fromGear = (p, k) => { const g = (p.gear_stats || {})[k] || 0; return g ? ` <small class="gear">${g > 0 ? '+' : ''}${g} from gear</small>` : ''; };

export function createCharacter() {
  const root = $('#character');
  const body = root.querySelector('.ch-body');
  let player = null, open = false, tab = 'overview', stage = null, shownClass = '', shownSig = '', sig = '';
  // the calculator's creature (kept while the sheet is open; a fight you start fills it in once)
  let foe = null, seenFoe = '';

  root.querySelectorAll('.ch-tabs button').forEach(b => b.addEventListener('click', () => {
    tab = b.dataset.tab; sig = '';
    root.querySelectorAll('.ch-tabs button').forEach(x => x.classList.toggle('on', x === b));
    render();
  }));
  root.querySelector('.ch-close').addEventListener('click', () => toggle(false));

  const bar = (cur, max, cls) => `<div class="ch-bar ${cls}"><b style="width:${max ? Math.max(0, Math.min(100, cur / max * 100)) : 0}%"></b><span>${cur ?? 0} / ${max ?? 0}</span></div>`;

  function overview(p) {
    const cls = String(p.char_class || '').toLowerCase();
    const prime = PRIME[cls];
    const floor = p.exp_floor || 0, next = p.exp_to_level || 0;
    const res = p.resource && p.resource.max ? [p.resource.value, p.resource.max, p.resource.name] : [p.mana, p.max_mana, 'Mana'];
    const aff = Array.isArray(p.affects) ? p.affects : [];
    return `<div class="ch-top">
      <div class="ch-id">
        <div class="ch-name">${esc(p.name)}</div>
        <div class="ch-title">${esc(p.title || '')}</div>
        <div class="ch-line">Level ${p.level || 1} ${esc(title(p.race))} ${esc(title(p.char_class))}</div>
        <div class="ch-lab">Health${fromGear(p, 'max_hp')}</div>${bar(p.hp, p.max_hp, 'hp')}
        <div class="ch-lab">${esc(res[2])}${res[2] === 'Mana' ? fromGear(p, 'max_mana') : ''}</div>${bar(res[0], res[1], 'mp')}
        <div class="ch-lab">Movement${fromGear(p, 'max_move')}</div>${bar(p.move, p.max_move, 'mv')}
        <div class="ch-lab">Experience</div>${next - floor > 1e9 || !next
          ? `<div class="ch-bar xp"><b style="width:100%"></b><span>Max level · ${(p.exp || 0).toLocaleString()} xp</span></div>`
          : bar(Math.max(0, (p.exp || 0) - floor), Math.max(1, next - floor), 'xp')}
        <div class="ch-gold">${(p.gold || 0).toLocaleString()} gold</div>
      </div>
    </div>
    <div class="ch-attrs">${ATTRS.map(([k, n]) => {
      // what worn gear adds counts already; shown beside it
      const g = (p.gear_stats || {})[k] || 0;
      const tip = `${n}${k === prime ? ' — your prime stat' : ''}${g ? ` (${p[k] - g} your own, ${g > 0 ? '+' : ''}${g} from gear)` : ''}`;
      return `<div class="${k === prime ? 'prime' : ''}" title="${tip}"><div class="v">${p[k] ?? '–'}${g ? `<small class="gear">${g > 0 ? '+' : ''}${g}</small>` : ''}</div><div class="k">${k.toUpperCase()}</div></div>`;
    }).join('')}</div>
    <div class="ch-combat">
      <div><span>Hit</span><b>${p.hitroll >= 0 ? '+' : ''}${p.hitroll ?? 0}</b></div>
      <div><span>Damage</span><b>${p.damroll >= 0 ? '+' : ''}${p.damroll ?? 0}</b></div>
      <div><span>Armour</span><b>${p.armor_class ?? p.armor ?? '–'}</b></div>
      <div><span>Stance</span><b>${esc(title(p.position || 'standing'))}</b></div>
    </div>
    ${(p.gear_wards || []).length ? `<div class="ch-lab">From your gear</div><div class="ch-wards">${p.gear_wards.map(w => `<span>${esc(w)}</span>`).join('')}</div>` : ''}
    <div class="ch-lab">Active effects</div>
    <div class="ch-affects">${aff.length ? aff.map(a => {
      const n = title(a.name || a.type || a.spell || 'effect');
      const left = a.duration != null ? ` <small>${a.duration}${typeof a.duration === 'number' ? 't' : ''}</small>` : '';
      return `<i>${esc(n)}${left}</i>`;
    }).join('') : '<span class="ch-none">None</span>'}</div>`;
  }

  function abilities(p) {
    const learnedSk = p.skills || {}, learnedSp = p.spells || {};
    const roster = (list, learned) => {
      const names = new Set([...(list || []).map(x => typeof x === 'string' ? x : x && x.name).filter(Boolean), ...Object.keys(learned)]);
      return [...names].sort((a, b) => (learned[b] || 0) - (learned[a] || 0) || a.localeCompare(b)).map(n => {
        const v = learned[n];
        return `<div class="ab-row ${v ? '' : 'dim'}"><span>${esc(title(n))}</span>${v ? `<div class="ab-bar"><b style="width:${Math.min(100, v)}%"></b></div><em>${v}%</em>` : '<em>not learned</em>'}</div>`;
      }).join('') || '<span class="ch-none">None</span>';
    };
    const talents = Object.entries(p.talents || {});
    return `<div class="ab-cols">
      <div><div class="ch-lab">Skills</div>${roster(p.class_skills, learnedSk)}</div>
      <div><div class="ch-lab">Spells</div>${roster(p.class_spells, learnedSp)}</div>
    </div>
    ${talents.length ? `<div class="ch-lab">Talents</div><div class="ch-affects">${talents.map(([k, v]) => `<i>${esc(title(k))}${typeof v === 'number' ? ` <small>${v}</small>` : ''}</i>`).join('')}</div>` : ''}`;
  }

  const fmt = x => !Number.isFinite(x) ? '–' : x >= 10 ? String(Math.round(x)) : x.toFixed(1);
  const pct = x => `${Math.round(x * 100)}%`;
  const sgn = n => `${n >= 0 ? '+' : ''}${n}`;
  const rounds = (n, me) => !Number.isFinite(n) ? 'never' : `${n} round${n === 1 ? '' : 's'} <small>~${Math.round(n * (me.round_secs || 3))}s</small>`;
  const FIELDS = [['level', 'Level'], ['ac', 'Armour'], ['hit', 'To hit'], ['min', 'Damage from'], ['max', 'to'], ['hp', 'Health'], ['pb', 'Absorb %']];
  const fromFoe = f => ({ level: f.level, ac: f.ac, hit: f.hit, min: f.min, max: f.max, hp: f.hp, maxHp: f.max_hp, pb: f.pb, boss: !!f.boss, kind: 'physical', src: f.name });

  // what you bring to a swing and what turns blows aside (map_system._combat_sheet)
  function sheet(me) {
    const a = me.avoid || {};
    const extra = (me.extra || []).map(e => `${esc(e.name)} ${e.chance}%`).join(' · ');
    const wards = Object.entries(me.resist || {});
    return `<div class="ch-lab">Your swing</div>
    <div class="ch-combat">
      <div title="${esc(me.weapon || 'Bare hands')} (${esc(me.dice || '1d3')})"><span>Weapon</span><b>${esc(me.dice || '1d3')}</b></div>
      <div title="A swing lands when a d20 plus this reaches the target's 10 − armour/10"><span>To hit</span><b>${sgn(me.hit)}</b></div>
      <div title="Weapon dice scaled to your level, ${sgn(me.damroll)} damage"><span>Damage</span><b>${me.min}–${me.max}</b></div>
      <div title="Criticals deal ×${me.crit_mult}"><span>Critical</span><b>${me.crit}%</b></div>
    </div>
    <div class="cc-note">${extra ? `Extra swings a round: ${extra}` : 'No extra swings a round'}</div>
    <div class="ch-lab">Your guard</div>
    <div class="ch-combat">
      <div title="Lower is better"><span>Armour</span><b>${me.ac}</b></div>
      <div title="A blow at you lands when a d20 plus its to-hit reaches this"><span>Blows need</span><b>${me.defense}</b></div>
      <div title="Taken off every creature's blow; grows with level"><span>Tough</span><b>${fmt(me.toughness)}%</b></div>
      <div title="Taken off every blow that lands: parry and shield skill, stance, armour weight"><span>Absorb</span><b>${me.pb}%</b></div>
      <div><span>Dodge</span><b>${a.dodge || 0}%</b></div>
      <div title="Needs a weapon in hand"><span>Parry</span><b>${a.parry || 0}%</b></div>
      <div title="Needs a shield"><span>Block</span><b>${a.block || 0}%</b></div>
      <div><span>Evasion</span><b>${a.evasion || 0}%</b></div>
    </div>
    <div class="ch-lab">Wards <small class="gear">${me.spell_resist ? `spells ${me.spell_resist}% · ` : ''}saves ${sgn(me.saves || 0)}</small></div>
    <div class="cc-wards">${wards.map(([k, v]) => `<div class="${v ? '' : 'dim'}" title="${esc(title(k))}: ${v}% of the harm turned aside (75% at most)"><span>${esc(title(k))}</span><i><b style="width:${Math.min(100, v / 75 * 100)}%"></b></i><em>${v}%</em></div>`).join('')}</div>`;
  }

  function calcForm(me) {
    const kinds = ['physical', ...Object.keys(me.resist || {})];
    return `<div class="ch-lab cc-head">Against a creature
      <span class="cc-pre"><button data-pre="foe" ${me.foe ? '' : 'disabled'} title="${me.foe ? esc(me.foe.name) : 'You are not fighting'}">Your foe</button><button data-pre="typical">Typical</button></span></div>
    <div class="cc-form">${FIELDS.map(([k, n]) => `<label><span>${n}</span><input type="number" data-k="${k}" value="${foe[k]}"></label>`).join('')}
      <label><span>Its blows</span><select data-k="kind">${kinds.map(k => `<option value="${k}" ${k === foe.kind ? 'selected' : ''}>${esc(title(k))}</option>`).join('')}</select></label>
      <label class="cc-boss"><input type="checkbox" data-k="boss" ${foe.boss ? 'checked' : ''}><span>Boss</span></label>
    </div>
    <div class="cc-src">${foe.src ? `${esc(foe.src)}, as you face it` : `A typical level ${foe.level} creature · changing its level fills in the rest`}</div>
    <div class="cc-out"></div>`;
  }

  function calcOut(me, p) {
    const r = fight(me, foe, p.hp || 0);
    const extra = r.extras.map(e => `${e.name} ${e.chance}%, lands ${pct(e.land)}, ~${fmt(e.avg)}`).join('; ');
    return `<div class="cc-side">
        <h4>Your blows</h4>
        <div><span>Land</span><b>${pct(r.land)}</b><small>${r.need} needed</small></div>
        <div><span>A hit</span><b>~${fmt(r.perHit)}</b><small>${r.crit}% critical</small></div>
        <div title="${esc(extra)}"><span>A round</span><b>~${fmt(r.perRound)}</b>${extra ? '<small>with extra swings</small>' : ''}</div>
        <div><span>Kills it in</span><b>${rounds(r.toKill, me)}</b></div>
      </div><div class="cc-side">
        <h4>Its blows</h4>
        <div><span>Land</span><b>${pct(r.theirLand)}</b><small>${pct(r.avoid)} turned aside</small></div>
        <div><span>A hit</span><b>~${fmt(r.takenPerHit)}</b><small>of ~${fmt(r.rawPerHit)} struck</small></div>
        <div><span>A round</span><b>~${fmt(r.takenPerRound)}</b></div>
        <div><span>You last</span><b>${rounds(r.toFall, me)}</b></div>
      </div>
      <div class="cc-verdict ${r.win ? 'win' : 'lose'}">${!Number.isFinite(r.toKill)
        ? 'Your blows would never land.'
        : r.win ? `You'd win in about ${r.toKill} round${r.toKill === 1 ? '' : 's'}, with about ${r.hpLeft} of your ${p.hp || 0} health left.`
          : `It would outlast you: you fall in about ${r.toFall} round${r.toFall === 1 ? '' : 's'}, it needs ${r.toKill}.`}</div>`;
  }

  function combat(p) {
    const me = p.combat;
    if (!me) { body.innerHTML = '<span class="ch-none">Nothing to work out yet.</span>'; return; }
    const fname = me.foe ? me.foe.name : '';
    if (fname && fname !== seenFoe) { foe = fromFoe(me.foe); body.innerHTML = ''; }   // a new fight fills it in once
    seenFoe = fname;
    if (!foe) foe = typicalFoe(p.level || 1);
    if (!body.querySelector('.cc')) body.innerHTML = `<div class="cc"><div class="cc-sheet"></div>${calcForm(me)}</div>`;
    body.querySelector('.cc-sheet').innerHTML = sheet(me);
    const pre = body.querySelector('[data-pre="foe"]');
    pre.disabled = !me.foe; pre.title = me.foe ? me.foe.name : 'You are not fighting';
    body.querySelector('.cc-out').innerHTML = calcOut(me, p);
  }
  // the calculator's own inputs: the form stays put while the numbers around it refresh
  const refill = () => { body.innerHTML = ''; sig = ''; render(); };
  body.addEventListener('input', e => {
    const k = e.target.dataset && e.target.dataset.k;
    if (!k || !foe || !player || !player.combat) return;
    if (k === 'kind') foe.kind = e.target.value;
    else if (k === 'boss') foe.boss = e.target.checked;
    else {
      const v = Number(e.target.value);
      if (e.target.value === '' || !Number.isFinite(v)) return;
      if (k === 'level') {       // the rest of a typical creature of that level, the field kept in focus
        foe = { ...typicalFoe(v), boss: foe.boss, kind: foe.kind };
        body.querySelectorAll('.cc-form input[type=number]').forEach(i => { if (i !== e.target) i.value = foe[i.dataset.k]; });
        body.querySelector('.cc-src').textContent = `A typical level ${foe.level} creature · changing its level fills in the rest`;
      }
      else {
        foe[k] = v; foe.src = '';
        if (k === 'hp') foe.maxHp = Math.max(foe.maxHp || 0, v);
        body.querySelector('.cc-src').textContent = 'Your own creature';
      }
    }
    body.querySelector('.cc-out').innerHTML = calcOut(player.combat, player);
  });
  body.addEventListener('click', e => {
    const b = e.target.closest && e.target.closest('[data-pre]');
    if (!b || !player || !player.combat) return;
    foe = b.dataset.pre === 'foe' && player.combat.foe ? fromFoe(player.combat.foe) : typicalFoe(player.level || 1);
    refill();
  });

  function render() {
    if (!player || !open) return;
    const nsig = JSON.stringify([tab, player.level, player.hp, player.mana, player.move, player.exp, player.gold,
      player.affects, player.skills, player.spells, player.hitroll, player.damroll, player.armor_class, player.position,
      tab === 'combat' ? player.combat : null]);
    if (nsig === sig) return;
    sig = nsig;
    if (tab === 'combat') combat(player);
    else body.innerHTML = tab === 'overview' ? overview(player) : abilities(player);
    // the portrait canvas lives outside the re-rendered text (one WebGL context, kept)
    const portrait = root.querySelector('.ch-portrait');
    portrait.classList.toggle('hidden', tab !== 'overview');
    if (tab === 'overview') {
      stage = stage || makeStage();
      stage.attach(portrait.querySelector('canvas'));
      const lsig = (player.look && player.look.sig) || '';
      if (shownClass !== player.char_class || shownSig !== lsig || !stage._shown) {
        shownClass = player.char_class; shownSig = lsig; stage._shown = true;
        stage.show(player.char_class, { flourish: false, look: player.look });
      }
    } else if (stage) { stage.stop(); stage._shown = false; }
  }
  function toggle(on = !open) {
    open = on;
    root.classList.toggle('hidden', !open);
    if (open) { sig = ''; if (stage) stage._shown = false; if (MH.refreshState) MH.refreshState(); render(); }
    else if (stage) { stage.stop(); stage._shown = false; }
  }
  return { toggle, get open() { return open; }, update(p) { player = p; render(); } };
}
