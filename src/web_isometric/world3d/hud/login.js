// Login and character creation for the 3D client. The protocol is the server's own
// prompts, driven through net.js (MH.connect). One account holds all of a player's heroes. Sign
// in: the account's email (or name) and password, then its heroes (the account's menu, sent as
// an 'account' message) to play one or forge one. No account by what was typed: the card turns
// into Create your account (email, account name, password twice), which makes an empty account
// and goes straight on to its first hero.
// A new hero is its name, then the race, male or female, class and stat-roll prompts,
// answered from these screens. The class step shows the class's 3D model turning on a small stage.
import { makeStage } from './stage.js';
import { starterLook } from '../gearlook.js';
import { uiIcon } from './icons.js';
import { THEMES } from '../abilityfx.js';

const $ = s => document.querySelector(s);
const NAME_KEY = 'misthollow_name';   // shared with the 2D client; no password is kept (MH.auth)
const ls = { get(k) { try { return localStorage.getItem(k); } catch (_) { return null; } },
  set(k, v) { try { localStorage.setItem(k, v); } catch (_) {} } };

const RACES = [
  ['human', 'Versatile and balanced — at home anywhere.'],
  ['elf', 'Graceful and magical, keen of mind and eye.'],
  ['dwarf', 'Sturdy and tough, hewn from living stone.'],
  ['halfling', 'Nimble and lucky — small, quick, hard to hit.'],
  ['half_orc', 'Fierce and mighty, a born brawler.'],
  ['gnome', 'Clever and arcane, a tinkering mind.'],
  ['dark_elf', 'Deadly shadow-kin, swift and merciless.'],
];
const CLASSES = [
  ['warrior', 'Tank', 'Master of melee and defence — sturdy and relentless.', 'STR'],
  ['cleric', 'Healer', 'Divine healer who mends allies and smites the undead.', 'WIS'],
  ['ranger', 'Ranged', 'Wilderness warrior blending bow and nature magic.', 'DEX'],
  ['mage', 'Caster', 'Commands devastating arcane spells from afar.', 'INT'],
  ['thief', 'Stealth', 'Cunning rogue who strikes from the shadows.', 'DEX'],
  ['paladin', 'Tank · Healer', 'Holy warrior — martial skill fused with divine power.', 'STR'],
  ['necromancer', 'Summoner', 'Dark mage who commands death and the undead.', 'INT'],
  ['bard', 'Support', 'Charismatic performer who inspires with magical songs.', 'CHA'],
  ['assassin', 'Burst', 'Deadly killer who eliminates targets with precision.', 'DEX'],
];
const SEXES = [['male', 'He, his, him.'], ['female', 'She, her, hers.']];
const STYLES = [['classic', 'The young mage in a travelling coat.'], ['archmage', 'A tall hat, a long white beard, a robe to the ankles and a moon staff.']];
const FIRST = new Set(['warrior', 'cleric', 'ranger']);
// what the hollow's folk say, turning slowly under the login
const LORE = [
  'Lanterns burn blue where the dead have walked.',
  'The hollow was a lake once. On still nights, it remembers.',
  'Garathorm\u2019s temple bells ring at dusk to call the lost home.',
  'Every blade remembers its first battle, say the guildmasters.',
  'Beyond the Ashlands, the dragons count the years in embers.',
  'Not every voice in the mist belongs to the living.',
  'A hero is only a traveller who did not turn back.',
  'Keep your lantern lit, and your name close.',
];

export function setupLogin() {
  const name = $('#login-name'), pass = $('#login-pass'), status = $('#login-status');
  const nEmail = $('#new-email'), nName = $('#new-name'), nPass = $('#new-pass'), nPass2 = $('#new-pass2');
  const create = $('#create');
  let creating = false, prime = '', madeNow = false;
  const saved = ls.get(NAME_KEY);
  if (saved) name.value = saved;
  const say = (msg, err) => { status.textContent = msg || ''; status.className = err ? 'error' : ''; };
  // this browser signed in before: one click continues (the stored token, not a password)
  const resumeBox = $('#login-resume'), form = $('#login-form'), signup = $('#signup-form'), chars = $('#login-chars');
  const codeForm = $('#code-form'), codeIn = $('#code-input');
  const only = el => [resumeBox, form, signup, codeForm, chars].forEach(x => x.classList.toggle('hidden', x !== el));
  const showForm = () => only(form);
  // no account yet: the account first (email, name, password), then its heroes; what was typed
  // at the sign-in carries over
  function showSignup(why, carry) {
    only(signup);
    const typed = carry ? name.value.trim() : '';
    if (typed.includes('@')) { if (!nEmail.value) nEmail.value = typed; }
    else if (typed && !nName.value) nName.value = typed;
    if (carry && pass.value && !nPass.value) nPass.value = pass.value;
    $('#signup-why').textContent = why || 'One account holds all your heroes.';
    say('');
    [nEmail, nName, nPass, nPass2].find(x => !x.value)?.focus();
  }
  $('#to-create').addEventListener('click', () => showSignup());
  $('#to-login').addEventListener('click', () => { showForm(); say(''); (name.value ? pass : name).focus(); });
  MH.bus.on('login.noaccount', who => showSignup(`There's no account for ${who} yet. Create one to start playing.`, true));
  // the email's code: nothing is made until it comes back (server.py handle_verify_code)
  MH.bus.on('signup.code', ({ email, error }) => {
    only(codeForm);
    $('#code-why').textContent = `We sent a 6-digit code to ${email}. It works for 15 minutes.`;
    codeIn.value = '';
    say(error || '', !!error);
    codeIn.focus();
  });
  MH.bus.on('signup.stopped', why => showSignup(why));
  const sendCode = () => {
    const v = codeIn.value.replace(/\s/g, '');
    if (!/^\d{6}$/.test(v)) return say('The code is 6 digits.', true);
    say('Checking the code…');
    send(v);
  };
  $('#code-btn').addEventListener('click', sendCode);
  codeIn.addEventListener('keydown', e => { if (e.key === 'Enter') sendCode(); e.stopPropagation(); });
  $('#code-resend').addEventListener('click', () => { say('Sending a new code…'); send('resend'); });
  // (nothing sent: the server drops the sign-up, and its reply brings the form back)
  $('#code-back').addEventListener('click', () => send(''));
  const rec = MH.auth.get();
  if (rec) {
    resumeBox.querySelector('b').textContent = rec.name;
    resumeBox.classList.remove('hidden');
    form.classList.add('hidden');
  } else {
    // a password an older version of this page kept: offered once, then forgotten
    const old = MH.auth.takeOldPassword();
    if (old) pass.value = old;
  }
  $('#resume-btn').addEventListener('click', () => {
    const r = MH.auth.get();
    if (!r) return showForm();
    name.value = r.name;
    MH.connect(r.name, '', false, r.token);
  });
  // back after the server went away mid-play (net.js MH.awaitServer): straight back in
  let again = false;
  try { again = sessionStorage.getItem(MH.RESUME_FLAG) === '1'; sessionStorage.removeItem(MH.RESUME_FLAG); } catch (_) {}
  // (once the title is up: the world listens for the first map only from then on, main.js)
  if (again && rec) {
    const go = () => ($('#loading').classList.contains('done') ? $('#resume-btn').click() : setTimeout(go, 250));
    go();
  }
  $('#switch-btn').addEventListener('click', () => { showForm(); name.value = ''; pass.value = ''; name.focus(); say(''); });
  MH.bus.on('login.expired', who => { showForm(); if (who) name.value = who; pass.focus(); });
  // a line of lore, changing every few seconds while the title screen stands
  const lore = $('#login .lore-line');
  let li = Math.floor(Math.random() * LORE.length);
  if (lore) {
    lore.textContent = LORE[li];
    const turn = setInterval(() => {
      if ($('#login').classList.contains('hidden')) { clearInterval(turn); return; }
      lore.style.opacity = 0;
      setTimeout(() => { li = (li + 1) % LORE.length; lore.textContent = LORE[li]; lore.style.opacity = 1; }, 1200);
    }, 8000);
  }

  const EMAIL = /^[^@\s]+@[^@\s]+\.[^@\s.]+$/;
  function signIn() {
    const n = name.value.trim(), p = pass.value;
    if (!n || !p) return say('Enter your email (or account name) and your password.', true);
    if (n.includes('@') ? !EMAIL.test(n) : !/^[a-zA-Z]{3,12}$/.test(n)) return say("That isn't an email or an account name.", true);
    ls.set(NAME_KEY, n);
    madeNow = false;
    MH.connect(n, p, false);
  }
  function signUp() {
    const e = nEmail.value.trim(), n = nName.value.trim(), p = nPass.value;
    if (!EMAIL.test(e)) return say("That isn't an email address.", true);
    if (!/^[a-zA-Z]{3,12}$/.test(n)) return say('An account name is 3–12 letters (no spaces, numbers or symbols).', true);
    if (p.length < 8) return say('Passwords must be at least 8 characters.', true);
    if (nPass2.value !== p) return say("The two passwords don't match.", true);
    ls.set(NAME_KEY, e);
    madeNow = true;
    MH.connect(n, p, true, undefined, e);
  }
  $('#login-btn').addEventListener('click', signIn);
  $('#signup-btn').addEventListener('click', signUp);
  // Enter moves to the next box, and on the last one sends
  const chain = (fields, go) => fields.forEach((f, i) => f.addEventListener('keydown', e => {
    if (e.key === 'Enter') (i < fields.length - 1 ? fields[i + 1].focus() : go());
    e.stopPropagation();
  }));
  chain([name, pass], signIn);
  chain([nEmail, nName, nPass, nPass2], signUp);

  // ---- the account's heroes ----
  const send = v => { const s = MH.state.mudSocket; if (s && s.readyState === WebSocket.OPEN) s.send(v); };
  const esc = s => String(s).replace(/[&<>"']/g, ch => `&#${ch.charCodeAt(0)};`);
  const tint = cls => '#' + (THEMES[cls] || THEMES.creature).core.toString(16).padStart(6, '0');
  function heroes(menu) {
    only(chars);
    // an account with no email yet (made before emails): offered here, and its code asked for
    pendingEmail = menu.pending || '';
    const box = chars.querySelector('.lc-email'), field = $('#acct-email');
    box.classList.toggle('hidden', !!menu.email && !pendingEmail);
    box.querySelector('.login-note').textContent = pendingEmail
      ? `Enter the 6-digit code we sent to ${pendingEmail}.`
      : 'Add an email to sign in with it (and to get a reset if you forget your password).';
    field.value = '';
    field.type = pendingEmail ? 'text' : 'email';
    field.placeholder = pendingEmail ? '6-digit code' : 'Email';
    field.autocomplete = pendingEmail ? 'one-time-code' : 'email';
    $('#acct-email-btn').textContent = pendingEmail ? 'Confirm' : 'Save';
    chars.querySelector('.lc-head b').textContent = menu.account;
    const list = chars.querySelector('.lc-list');
    list.innerHTML = menu.chars.length ? menu.chars.map(c => {
      const cc = tint(c.class);
      return `<button class="hero" data-name="${esc(c.name)}" style="--cc:${cc}" aria-label="Play ${esc(c.name)}, level ${esc(c.level)} ${esc(String(c.race).replace('_', ' '))} ${esc(c.class)}">`
        + `<img alt="" src="${uiIcon((THEMES[c.class] || THEMES.creature).glyph, { size: 64, color: cc, glow: 'rgba(0,0,0,.6)' })}">`
        + `<span><b>${esc(c.name)}</b><small>${esc(String(c.race).replace('_', ' '))} ${esc(c.class)}</small></span>`
        + `<span class="lv" title="Level">${esc(c.level)}</span></button>`;
    }).join('') : '<div class="lc-empty">No heroes yet. Forge your first.</div>';
    list.querySelectorAll('.hero').forEach(el => el.addEventListener('click', () => {
      say(`Entering as ${el.dataset.name}…`);
      MH.playHero(el.dataset.name);
    }));
    const full = menu.chars.length >= (menu.max || 8);
    $('#forge-btn').disabled = full;
    $('#forge-btn').title = full ? `This account holds its most heroes (${menu.max})` : '';
    const first = list.querySelector('.hero');
    (first || $('#forge-btn')).focus();
  }
  MH.bus.on('account.menu', menu => {
    // back from a hero half made (the name was taken meanwhile, or Back): the list again
    if (creating) { creating = false; create.classList.add('hidden'); if (stage) stage.stop(); }
    // what the menu's last command did (its email), or what the hero wizard learned
    if (menu.note) say(menu.note, menu.bad); else say(heroNote);
    heroNote = '';
    heroes(menu);
    // an account just made: straight on to its first hero
    if (madeNow && !menu.chars.length) { madeNow = false; $('#forge-btn').click(); }
  });
  // an email for the account; when the server mails codes, the code then (the menu's verify)
  let pendingEmail = '';
  const saveEmail = () => {
    const e = $('#acct-email').value.trim();
    heroNote = '';
    if (pendingEmail) {
      if (!/^\d{6}$/.test(e)) return say('The code is 6 digits.', true);
      return send(`verify ${e}`);
    }
    if (!EMAIL.test(e)) return say("That isn't an email address.", true);
    send(`email ${e}`);
  };
  $('#acct-email-btn').addEventListener('click', saveEmail);
  $('#acct-email').addEventListener('keydown', e => { if (e.key === 'Enter') saveEmail(); e.stopPropagation(); });
  let heroNote = '', phase = '';
  $('#forge-btn').addEventListener('click', () => {
    creating = true;
    phase = 'name';
    say('');
    wizard('', 'FORGE YOUR HERO', 'Summoning the loom of fate…', '');
    send('create');
  });
  // signing out of the account: the connection closes and the page starts again
  $('#leave-btn').addEventListener('click', () => { try { MH.state.mudSocket.close(); } catch (_) {} location.reload(); });

  // ---- creation wizard ----
  function wizard(step, title, hint, body) {
    create.classList.remove('hidden');
    create.querySelector('.step').textContent = step;
    create.querySelector('h2').textContent = title;
    create.querySelector('.hint').textContent = hint;
    create.querySelector('.body').innerHTML = body;
  }
  // the hero's name (the account menu's create asks it); nothing sent goes back to the list
  function naming(err) {
    wizard('NEW HERO', 'NAME YOUR HERO', 'The name the mist will remember: 3–12 letters.',
      `<div class="name-row"><input id="hero-name" maxlength="12" autocomplete="off" spellcheck="false" placeholder="Hero name">`
      + `<button class="btn" id="hero-go">Continue</button></div><div class="name-err"></div>`
      + `<button class="btn alt" id="hero-back">Back</button>`);
    create.querySelector('.name-err').textContent = err || '';
    const input = $('#hero-name');
    const go = () => {
      const v = input.value.trim();
      if (!/^[a-zA-Z]{3,12}$/.test(v)) { create.querySelector('.name-err').textContent = 'A name is 3–12 letters (no spaces, numbers or symbols).'; return; }
      send(v);
      wizard('', 'FORGE YOUR HERO', 'Weighing the name…', '');
    };
    $('#hero-go').addEventListener('click', go);
    input.addEventListener('keydown', e => { if (e.key === 'Enter') go(); e.stopPropagation(); });
    $('#hero-back').addEventListener('click', () => send(''));
    input.focus();
  }
  function races() {
    wizard('STEP 1 OF 4', 'CHOOSE YOUR LINEAGE', 'Your bloodline shapes your gifts and your fate.',
      `<div class="grid">${RACES.map(([id, de]) => `<div class="pick" data-v="${id}"><b>${id.replace('_', ' ')}</b><small>${de}</small></div>`).join('')}</div>`);
    create.querySelectorAll('.pick').forEach(el => el.addEventListener('click', () => { lineage = el.dataset.v; send(el.dataset.v); wizard('', 'FORGE YOUR HERO', 'Weaving your lineage…', ''); }));
  }
  function sexes() {
    wizard('STEP 2 OF 4', 'CHOOSE YOUR FORM', 'How the world will know you: your words, your face and your build.',
      `<div class="grid">${SEXES.map(([id, de]) => `<div class="pick" data-v="${id}"><b>${id}</b><small>${de}</small></div>`).join('')}</div>`);
    create.querySelectorAll('.pick').forEach(el => el.addEventListener('click', () => { chosenSex = el.dataset.v; send(el.dataset.v); wizard('', 'FORGE YOUR HERO', 'Shaping your form…', ''); }));
  }
  let stage = null, lineage = null, chosenSex = null;
  // the class's starting gear on the race and form just chosen (skin, face and build)
  const preview = (id, style = '') => (lineage ? { ...starterLook(id), race: lineage, ...(chosenSex ? { sex: chosenSex } : {}), ...(style ? { style } : {}),
    sig: `starter:${id}:${lineage}:${chosenSex || ''}:${style}` } : null);
  function classes() {
    wizard('STEP 3 OF 4', 'CHOOSE YOUR CALLING', 'Pick a class to see it up close. Three are marked as good first picks.',
      `<div class="split"><div class="grid">${CLASSES.map(([id, role]) =>
        `<div class="pick cls" data-v="${id}" style="--cc:#${(THEMES[id] || THEMES.creature).core.toString(16).padStart(6, '0')}"><img class="pk-ic" alt="" src="${uiIcon((THEMES[id] || THEMES.creature).glyph, { size: 72, color: '#' + (THEMES[id] || THEMES.creature).core.toString(16).padStart(6, '0'), glow: 'rgba(0,0,0,.6)' })}"><b>${id}</b><small>${role}</small>${FIRST.has(id) ? '<div class="first">★ first pick</div>' : ''}</div>`).join('')}</div>`
      + `<div class="focus"><canvas width="520" height="600"></canvas><div class="fn"></div><p class="fd"></p><p class="fs"></p>`
      + `<button class="btn" id="choose-class" disabled>Choose</button></div></div>`);
    stage = stage || makeStage();
    stage.attach(create.querySelector('canvas'));
    let pick = null;
    const focus = id => {
      pick = id;
      create.querySelectorAll('.pick').forEach(el => el.classList.toggle('on', el.dataset.v === id));
      const c = CLASSES.find(x => x[0] === id);
      prime = c[3];
      create.querySelector('.fn').textContent = id;
      create.querySelector('.fd').textContent = c[2];
      create.querySelector('.fs').textContent = `Role: ${c[1]} · Prime stat: ${c[3]}`;
      const b = $('#choose-class'); b.disabled = false; b.textContent = `Choose ${id}`;
      stage.show(id, { look: preview(id) });
    };
    create.querySelectorAll('.pick').forEach(el => el.addEventListener('click', () => focus(el.dataset.v)));
    $('#choose-class').addEventListener('click', () => { if (pick) { send(pick); stage.stop(); wizard('', 'FORGE YOUR HERO', 'Rolling the dice of fate…', ''); } });
    focus('warrior');
  }
  // a mage's look (server.py show_style_menu): the classic mage or the archmage, each shown
  function looks() {
    wizard('A MAGE’S LOOK', 'CHOOSE YOUR LOOK', 'How your mage appears in the world. The appearance command changes it later.',
      `<div class="split"><div class="grid">${STYLES.map(([id, de]) => `<div class="pick" data-v="${id}"><b>${id}</b><small>${de}</small></div>`).join('')}</div>`
      + `<div class="focus"><canvas width="520" height="600"></canvas><div class="fn"></div>`
      + `<button class="btn" id="choose-look" disabled>Choose</button></div></div>`);
    stage = stage || makeStage();
    stage.attach(create.querySelector('canvas'));
    let pick = null;
    const focus = id => {
      pick = id;
      create.querySelectorAll('.pick').forEach(el => el.classList.toggle('on', el.dataset.v === id));
      create.querySelector('.fn').textContent = id;
      const b = $('#choose-look'); b.disabled = false; b.textContent = `Choose ${id}`;
      stage.show('mage', { look: preview('mage', id === 'archmage' ? 'archmage' : '') });
    };
    create.querySelectorAll('.pick').forEach(el => el.addEventListener('click', () => focus(el.dataset.v)));
    $('#choose-look').addEventListener('click', () => { if (pick) { send(pick); stage.stop(); wizard('', 'FORGE YOUR HERO', 'Rolling the dice of fate…', ''); } });
    focus('archmage');
  }
  // the six rolled stats: drawn once, then each reroll changes only the numbers in place (the
  // server's lines can arrive in pieces; a half roll is held until all six are in, so the panel
  // never redraws smaller and jumps)
  const STAT_KEYS = { Strength: 'STR', Intelligence: 'INT', Wisdom: 'WIS', Dexterity: 'DEX', Constitution: 'CON', Charisma: 'CHA' };
  let rolled = {}, rollText = '';
  function stats(text) {
    rollText = (rollText + '\n' + text).slice(-2000);
    const re = /(Strength|Intelligence|Wisdom|Dexterity|Constitution|Charisma):\s*(\d+)/g;
    const got = {};
    let m;
    while ((m = re.exec(rollText))) got[STAT_KEYS[m[1]]] = m[2];
    if (Object.keys(got).length < 6) return;
    rollText = '';
    rolled = got;
    const panel = create.querySelector('.stats');
    if (panel && $('#reroll')) {
      panel.classList.remove('rolling');
      panel.querySelectorAll('[data-k]').forEach(el => { el.querySelector('.v').textContent = rolled[el.dataset.k]; });
      return;
    }
    const cells = Object.values(STAT_KEYS).map(k =>
      `<div data-k="${k}" class="${k === prime ? 'prime' : ''}"><div class="v">${rolled[k]}</div><div class="k">${k}</div></div>`).join('');
    wizard('STEP 4 OF 4', 'ROLL YOUR FATE', 'The dice favour the bold — keep them, or tempt fate again.',
      `<div class="stats">${cells}</div><div class="row2"><button class="btn" id="keep">Keep these</button><button class="btn alt" id="reroll">Reroll</button></div>`);
    $('#keep').addEventListener('click', () => { send('y'); wizard('', 'FORGE YOUR HERO', 'Your story begins…', ''); });
    $('#reroll').addEventListener('click', () => { create.querySelector('.stats').classList.add('rolling'); rollText = ''; send('n'); });
  }
  MH.bus.on('terminal.output', ({ text }) => {
    if (MH.state.isLoggedIn || !text) return;
    // what the account's menu says about the last thing asked of it (shown over the list)
    const full = /maximum number of characters/i.test(text);
    const lost = /([^\n]*already taken\.?)\s*your character was not made/i.exec(text);
    if (full) heroNote = 'This account holds its most heroes.';
    if (lost) heroNote = `${lost[1].trim()} Your hero was not made.`;
    if (/error loading character/i.test(text)) say('That hero could not be loaded.', true);
    if (!creating || full || lost) return;
    if (phase === 'name') {
      if (/enter name for new character/i.test(text) || /choose another/i.test(text)) {
        const err = text.split('\n').map(l => l.trim()).find(l => /taken|must|only letters/i.test(l));
        return naming(err && !/enter name/i.test(err) ? err.replace(/\s*choose another:?\s*$/i, '') : '');
      }
      if (!/choose your race|race name or number/i.test(text)) return;
      phase = 'build';
    }
    if (/choose your race|race name or number/i.test(text)) return races();
    if (/male or female/i.test(text)) return sexes();
    if (/choose your class|class name or number/i.test(text)) return classes();
    if (/classic or archmage/i.test(text)) return looks();
    if (/accept these stats|to reroll/i.test(text) || /Strength:\s*\d+/.test(text)) return stats(text);
    const note = text.split('\n').map(l => l.trim()).filter(Boolean).slice(-1)[0];
    if (note && /invalid|already|taken|try again|not a valid|must (?:be|contain)|in use/i.test(note)) {
      wizard('', 'FORGE YOUR HERO', note.slice(0, 140), '<button class="btn alt" id="restart">Start over</button>');
      $('#restart').addEventListener('click', () => location.reload());
    }
  });
  MH.bus.on('login.status', msg => say(msg));
  MH.bus.on('login.error', msg => say(msg, true));
  MH.bus.on('login.success', () => {
    creating = false;
    create.classList.add('hidden');
    $('#login').classList.add('hidden');
    if (stage) stage.stop();
  });
}
