// Misthollow web client (/play): networking layer.
// Dual sockets: MUD command/output bridge (:4003/ws) + structured map stream (:4001).
// Born in the retired 2D clients, with the same proxy-aware host detection.
(() => {
  const protocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:';
  const host = window.location.hostname || 'localhost';
  const isBehindProxy = !window.location.port || window.location.port == 80 || window.location.port == 443;
  const mudHost = isBehindProxy ? host.replace('map.', 'mud.') : host;

  const MH = window.MH = window.MH || {};
  MH.urls = {
    mudWs: isBehindProxy ? `${protocol}//${mudHost}/ws` : `${protocol}//${host}:4003/ws`,
    mapWs: isBehindProxy ? `${protocol}//${host}` : `${protocol}//${host}:4001`,
    art: isBehindProxy ? `${window.location.protocol}//${mudHost}/art/` : `${window.location.protocol}//${host}:4003/art/`,
    // MH.mapMode is read per call: the 3D client sets 'near' after this file loads
    state: name => (isBehindProxy ? `/state?player=${encodeURIComponent(name)}`
                                  : `${window.location.protocol}//${host}:4001/state?player=${encodeURIComponent(name)}`)
      + (MH.mapMode ? `&mode=${MH.mapMode}` : ''),
  };

  // every per-player request to the map server carries this session's token (handed over in
  // MAPSYNC by the player's own game connection): the server answers nothing to a name alone
  const realFetch = window.fetch.bind(window);
  window.fetch = (input, init) => {
    const tok = MH.state && MH.state.mapToken;
    if (tok && typeof input === 'string' && /[?&]player=/.test(input) && !/[?&]t=/.test(input)) {
      input += `&t=${encodeURIComponent(tok)}`;
    }
    return realFetch(input, init);
  };

  // --- tiny event bus ---
  const listeners = {};
  MH.bus = {
    on(event, fn) { (listeners[event] = listeners[event] || []).push(fn); },
    off(event, fn) {
      const a = listeners[event];
      if (!a) return;
      const i = a.indexOf(fn);
      if (i >= 0) a.splice(i, 1);
    },
    emit(event, payload) {
      for (const fn of (listeners[event] || []).slice()) {
        try { fn(payload); } catch (err) { console.error(`[bus:${event}]`, err); }
      }
    },
  };

  // --- graphics quality + reduced motion ---
  // central source of truth the scene reads to scale its FX. Persisted, with
  // first-load auto-detection (lighter on mobile/low-RAM, respects the OS
  // "reduce motion" preference). Changing it emits 'gfx.changed'.
  MH.gfx = (function () {
    const QKEY = 'misthollow_gfx_quality', MKEY = 'misthollow_gfx_motion';
    const TIERS = {
      low:    { bloom: false, particleScale: 0.3, parallax: false, caustics: false, rim: false, weatherLayers: 1, lightPools: 0 },
      medium: { bloom: true,  particleScale: 0.6, parallax: true,  caustics: true,  rim: true,  weatherLayers: 2, lightPools: 1 },
      high:   { bloom: true,  particleScale: 1.0, parallax: true,  caustics: true,  rim: true,  weatherLayers: 3, lightPools: 2 },
    };
    const ls = (k) => { try { return localStorage.getItem(k); } catch (_) { return null; } };
    const save = (k, v) => { try { localStorage.setItem(k, v); } catch (_) {} };
    function detectQuality() {
      try {
        const mobile = /Mobi|Android|iPhone|iPad|iPod/i.test(navigator.userAgent || '');
        const mem = navigator.deviceMemory || 4;
        if (mobile || mem <= 2) return 'medium';
        return 'high';
      } catch (_) { return 'high'; }
    }
    function detectMotion() {
      try { return !!(window.matchMedia && window.matchMedia('(prefers-reduced-motion: reduce)').matches); }
      catch (_) { return false; }
    }
    let quality = TIERS[ls(QKEY)] ? ls(QKEY) : detectQuality();
    const ms = ls(MKEY);
    let reduced = ms != null ? ms === '1' : detectMotion();
    const t = () => TIERS[quality] || TIERS.high;
    return {
      get quality() { return quality; },
      get reducedMotion() { return reduced; },
      get motion() { return !reduced; },
      get bloom() { return t().bloom; },
      get particleScale() { return t().particleScale; },
      get parallax() { return t().parallax; },
      get caustics() { return t().caustics; },
      get rim() { return t().rim; },
      get weatherLayers() { return t().weatherLayers; },
      get lightPools() { return t().lightPools; },
      setQuality(q) { if (!TIERS[q] || q === quality) return; quality = q; save(QKEY, q); MH.bus.emit('gfx.changed', { quality, reduced }); },
      setReducedMotion(v) { v = !!v; if (v === reduced) return; reduced = v; save(MKEY, v ? '1' : '0'); MH.bus.emit('gfx.changed', { quality, reduced }); },
    };
  })();

  // --- sign-in tokens (security.py) ---
  // After a password login the page asks the server to `remember` this browser; the server
  // answers with a token (the RESUME signal) that stands in for the password next time and
  // is swapped for a fresh one on every use. No password is kept in the browser.
  const AUTH_KEY = 'misthollow_resume', OLD_PW_KEY = 'misthollow_pw';
  MH.auth = {
    get() {
      try {
        const v = JSON.parse(localStorage.getItem(AUTH_KEY) || 'null');
        return v && v.name && v.token ? v : null;
      } catch (_) { return null; }
    },
    set(name, token) { try { localStorage.setItem(AUTH_KEY, JSON.stringify({ name, token })); } catch (_) {} },
    clear() { try { localStorage.removeItem(AUTH_KEY); } catch (_) {} },
    // a password an older version of these pages kept: handed back once, then gone
    takeOldPassword() {
      let pw = null;
      try {
        const v = localStorage.getItem(OLD_PW_KEY);
        if (v) pw = atob(v);
        localStorage.removeItem(OLD_PW_KEY);
      } catch (_) {}
      return pw;
    },
  };

  // --- shared state ---
  MH.state = {
    playerName: '',
    mapToken: '',              // this session's secret for the map server (MAPSYNC)
    playerPassword: '',
    resumeToken: '',           // signing in with a stored token instead of a password
    newAccount: false,         // Create account: `newaccount <name> <email>`, then its password twice
    newEmail: '',
    account: null,             // the account signed in to: {account, max, chars} (its menu, server.py)
    isLoggedIn: false,
    loginSequenceStarted: false,
    mudSocket: null,
    mapSocket: null,
    mapResubscribeInterval: null,
    mapRetryTimers: [],
    lastMapDataAt: 0,
    lastPayload: null,
    currentRoom: null,       // current_room block from payload
    player: null,            // player block from payload
    inCombat: false,
    combatPollTimer: null,
    pendingMove: null,       // {dir, sentAt} while a movement command is in flight
  };

  const sleep = ms => new Promise(r => setTimeout(r, ms));

  function decodeHtmlEntities(text) {
    const el = document.createElement('textarea');
    el.innerHTML = String(text || '');
    return el.value;
  }
  MH.stripServerMarkup = function stripServerMarkup(text) {
    return decodeHtmlEntities(
      String(text || '')
        .replace(/<br\s*\/?>/gi, '\n')
        .replace(/<\/p>/gi, '\n')
        .replace(/<[^>]+>/g, '')
    ).replace(/\r\n/g, '\n').replace(/\r/g, '\n');
  };

  // --- command sending ---
  // a line carrying a password: what to show for it ('' when it carries none)
  MH.secretLine = function secretLine(command) {
    const m = /^\s*account\s+(password|recover|reset|claim)\b/i.exec(String(command || ''));
    return m ? `account ${m[1].toLowerCase()} ****` : '';
  };
  MH.sendCommand = function sendCommand(command, echo = true) {
    const trimmed = String(command || '').trim();
    const sock = MH.state.mudSocket;
    if (!trimmed || !sock || sock.readyState !== WebSocket.OPEN) return false;
    sock.send(trimmed);
    // echo: true shows it as typed; a kind ('combat') files it with that kind's lines (hud/logkinds.js)
    if (echo) MH.bus.emit('terminal.echo', typeof echo === 'string' ? { text: MH.secretLine(trimmed) || trimmed, kind: echo } : MH.secretLine(trimmed) || trimmed);
    return true;
  };

  // --- scripted login (same dance as client2d) ---
  async function runLoginSequence() {
    const st = MH.state;
    if (st.loginSequenceStarted || !st.mudSocket || st.mudSocket.readyState !== WebSocket.OPEN) return;
    st.loginSequenceStarted = true;
    MH.bus.emit('login.status', st.newAccount ? 'Opening a new account…' : 'Opening the gate…');
    await sleep(500);
    if (st.resumeToken) {
      st._loginNameSent = true;
      MH.sendCommand(`resume ${st.playerName} ${st.resumeToken}`, false);
      return;
    }
    if (st.newAccount) {
      // its password prompts are answered as they arrive (answerLoginPrompts)
      MH.sendCommand(`newaccount ${st.playerName} ${st.newEmail}`.trim(), false);
      st._loginNameSent = true;
      return;
    }
    // an account's email or name (or a hero's): its password, then the account's heroes (an
    // 'account' message)
    // (the password goes only when its prompt comes: an unknown name gets none, and a
    // password sent anyway would be read as the next name)
    MH.sendCommand(st.playerName, false);
    st._loginNameSent = true;   // a name re-prompt after this means it was rejected
  }
  // the account's heroes: play one, or make one (the menu's own commands; server.py)
  MH.playHero = name => MH.sendCommand(`play ${name}`, false);

  const ROOM_LOGIN_PATTERNS = [/^\[[0-9]+\]\s+/m, /\bExits?:\b/i, /You are in/i, /Obvious exits:/i];

  // pre-game prompts the scripted login should answer on the player's behalf
  const LOGIN_PROMPT_RESPONDERS = [
    { test: /press (?:enter|return) to continue/i, send: '' },
    { test: /\[\s*press (?:enter|return)\s*\]/i, send: '' },
  ];
  function answerLoginPrompts(text) {
    const st = MH.state;
    if (st.isLoggedIn) return;
    // a stored sign-in the server no longer knows: forget it and ask for the password
    if (st.resumeToken && /sign-in has expired/i.test(text)) {
      st.resumeToken = '';
      MH.auth.clear();
      MH.bus.emit('login.expired', st.playerName);
      MH.bus.emit('login.error', 'Your sign-in has expired — enter your password.');
      return;
    }
    const sendDelayed = (key, val) => {
      if (st._lastPromptKey === key) return;   // dedupe a prompt repeated across chunks
      st._lastPromptKey = key;
      setTimeout(() => {
        const sock = st.mudSocket;
        if (sock && sock.readyState === WebSocket.OPEN) sock.send(val);
      }, 250);
    };
    // Create account: the password twice, then the new account's (empty) list of heroes
    if (st.newAccount) {
      if (/choose a password/i.test(text)) { sendDelayed('new-pw', st.playerPassword); return; }
      if (/confirm password/i.test(text)) { sendDelayed('new-pw2', st.playerPassword); return; }
      if (!st._loginNameSent) return;
      // the email's code (when the server can send mail): the page asks for it (login.js)
      if (/enter the 6-digit code|type 'resend' for a new one/i.test(text)) {
        const why = /that code isn't right|that code has expired/i.exec(text);
        MH.bus.emit('signup.code', { email: st.newEmail, error: why ? `${why[0]}.` : '' });
        return;
      }
      const gone = /(too many codes have been sent just now[^.]*\.|a code couldn't be sent to [^.]+\.[^.]*\.|too many wrong codes|sign-up stopped)/i.exec(text);
      if (gone) { MH.bus.emit('signup.stopped', gone[1]); return; }
      if (/name is already taken/i.test(text)) { MH.bus.emit('login.error', 'That account name is taken — choose another.'); return; }
      const why = /(names must[^.]*\.|passwords must[^.]*\.|that isn't an email address\.|that email already belongs to an account\.)/i.exec(text);
      if (why) { MH.bus.emit('login.error', why[1]); return; }
      return;
    }
    if (st._loginNameSent && st.playerPassword && /account password:/i.test(text)) { sendDelayed('login-pw', st.playerPassword); return; }
    // no account by that email or name: the page asks for a new one (login.js)
    if (st._loginNameSent && /no account uses the email|is a new name|create account\?/i.test(text)) {
      MH.bus.emit('login.noaccount', st.playerName);
      return;
    }
    // login failures: give clear feedback instead of a silent hang
    if (st._loginNameSent && /invalid password|wrong password/i.test(text)) {
      MH.bus.emit('login.error', 'Wrong password — try again.');
      return;
    }
    if (st._loginNameSent && /can't be logged into/i.test(text)) {
      MH.bus.emit('login.error', `${st.playerName} has no account: ask an immortal for help.`);
      return;
    }
    for (const { test, send } of LOGIN_PROMPT_RESPONDERS) {
      if (test.test(text)) { sendDelayed('static:' + test.source, send); return; }
    }
  }
  function inferLoginSuccess(text) {
    const st = MH.state;
    if (st.isLoggedIn) return;
    // mapsync is the authoritative signal; room-looking output is the fallback.
    // (a bare /welcome/i match would false-positive on the splash banner)
    if (ROOM_LOGIN_PATTERNS.some(p => p.test(text))) {
      st.isLoggedIn = true;
      MH.bus.emit('login.success', st.playerName);
    }
  }

  // --- map socket ---
  function stopResubscribe() {
    if (MH.state.mapResubscribeInterval) {
      clearInterval(MH.state.mapResubscribeInterval);
      MH.state.mapResubscribeInterval = null;
    }
  }
  function clearRetryTimers() {
    MH.state.mapRetryTimers.forEach(t => clearTimeout(t));
    MH.state.mapRetryTimers = [];
  }
  function sendMapSubscribe() {
    const st = MH.state;
    if (!st.playerName || !st.mapSocket || st.mapSocket.readyState !== WebSocket.OPEN) return;
    st.mapSocket.send(JSON.stringify({ type: 'subscribe', player: st.playerName, token: st.mapToken || '', mode: MH.mapMode || 'full',
      combat: MH.combatMode || undefined }));
  }
  MH.resubscribe = sendMapSubscribe;
  function startResubscribe() {
    stopResubscribe();
    MH.state.mapResubscribeInterval = setInterval(() => {
      const st = MH.state;
      if (!st.mapSocket || st.mapSocket.readyState !== WebSocket.OPEN) return;
      if (st.lastPayload && (Date.now() - st.lastMapDataAt) < 5000) return;
      sendMapSubscribe();
    }, 2000);
  }

  function handleMapData(payload) {
    const st = MH.state;
    clearRetryTimers();
    st.lastMapDataAt = Date.now();
    st.lastPayload = payload;
    if (payload.player) st.player = payload.player;
    if (payload.current_room) st.currentRoom = payload.current_room;
    // authoritative combat state rides every payload - no more stuck chips
    if (payload.player && payload.player.in_combat != null) MH.setCombat(!!payload.player.in_combat);
    if (st.player && st.lastPayload) stopResubscribe();
    MH.bus.emit('map', payload);
  }

  // server pushes these every combat round: vitals + current-room entities
  function handleCombatUpdate(payload) {
    const st = MH.state;
    if (st.player && payload.player) Object.assign(st.player, payload.player);
    if (payload.in_combat != null) MH.setCombat(!!payload.in_combat);
    MH.bus.emit('combat.update', payload);
  }

  function ensureMapSocket() {
    const st = MH.state;
    if (!st.playerName) return;
    if (st.mapSocket && (st.mapSocket.readyState === WebSocket.OPEN || st.mapSocket.readyState === WebSocket.CONNECTING)) return;
    st.mapSocket = new WebSocket(MH.urls.mapWs);
    st.mapSocket.addEventListener('open', () => {
      sendMapSubscribe();
      clearRetryTimers();
      [500, 1500, 3000].forEach(delay => {
        st.mapRetryTimers.push(setTimeout(() => {
          if (!st.lastPayload || (Date.now() - st.lastMapDataAt) > 2000) sendMapSubscribe();
        }, delay));
      });
      startResubscribe();
    });
    st.mapSocket.addEventListener('message', event => {
      try {
        const payload = JSON.parse(event.data);
        if (payload.type === 'map_data') handleMapData(payload);
        else if (payload.type === 'combat_update') handleCombatUpdate(payload);
        // the hero's body out of a fight too (web_hud.py): pools, posture, hunger, a breath, mail
        else if (payload.type === 'vitals') { if (MH.state.player) Object.assign(MH.state.player, payload.player); MH.bus.emit('vitals', payload); }
        else if (payload.type === 'mob_move') MH.bus.emit('mob.move', payload);
        else if (payload.type === 'player_move') { MH.bus.emit('player.move', payload); if (payload.name && payload.name !== MH.state.playerName && payload.action !== 'move') MH.bus.emit('ambient.echo', `${payload.name} ${payload.action === 'leave' ? 'leaves' : 'arrives'}.`); }
        else if (payload.type === 'ambient') MH.bus.emit('ambient.murmur', payload);   // a sound and a cue (world3d/hud/ambient.js)
        else if (payload.type === 'loot_roll') MH.bus.emit('loot.roll', payload);
        else if (payload.type === 'loot_result') MH.bus.emit('loot.result', payload);
        else if (payload.type === 'move_result') MH.bus.emit('move.result', payload);
        else if (payload.type === 'combat_events') MH.bus.emit('combat.events', payload);
        else if (payload.type === 'door') MH.bus.emit('door.update', payload);
        else if (payload.type === 'door_result') MH.bus.emit('door.result', payload);
        else if (payload.type === 'improve') MH.bus.emit('ability.improve', payload);
        // other players: where they stand, and group changes (party frames, invites)
        else if (payload.type === 'presence') MH.bus.emit('player.presence', payload);
        else if (payload.type === 'look') MH.bus.emit('player.look', payload);
        else if (payload.type === 'group') MH.bus.emit('group.update', payload);
        else if (payload.type === 'group_invite') MH.bus.emit('group.invite', payload);
        // the server wants this session's token (subscribe) / another login took the character
        else if (payload.type === 'auth' && !payload.ok) MH.bus.emit('session.denied', payload);
        else if (payload.type === 'revoked') { MH.state.leaving = true; MH.bus.emit('session.revoked', payload); }
        // the marquee quest (marquee.py): quest_offer / quest_embark / quest_stage / quest_done
        else if (typeof payload.type === 'string' && payload.type.startsWith('quest_')) MH.bus.emit(`quest.${payload.type.slice(6)}`, payload);
        // the world's news for this player (docs/GAMEPLAY_POLISH.md): world_rare (elites.py), world_achievement
        else if (typeof payload.type === 'string' && payload.type.startsWith('world_')) MH.bus.emit(`world.${payload.type.slice(6)}`, payload);
      } catch (err) {
        console.warn('map socket parse error', err);
      }
    });
    const onDown = () => { clearRetryTimers(); stopResubscribe(); setTimeout(ensureMapSocket, 2000); };
    st.mapSocket.addEventListener('close', onDown);
    st.mapSocket.addEventListener('error', () => {});
  }

  // --- combat HP polling: map pushes only fire on movement, so poll /state mid-fight ---
  MH.setCombat = function setCombat(on) {
    const st = MH.state;
    if (st.inCombat === on) return;
    st.inCombat = on;
    MH.bus.emit('combat.state', on);
    // fallback only: the server now pushes combat_update every round,
    // so this just guards against missed frames
    if (on && !st.combatPollTimer) {
      st.combatPollTimer = setInterval(async () => {
        if (!st.playerName) return;
        try {
          const res = await fetch(MH.urls.state(st.playerName));
          if (res.ok) handleMapData(await res.json());
        } catch (_) { /* server hiccup; next tick retries */ }
      }, 4000);
    } else if (!on && st.combatPollTimer) {
      clearInterval(st.combatPollTimer);
      st.combatPollTimer = null;
    }
  };
  // One-shot refresh (used after deaths, purchases, etc.)
  MH.refreshState = async function refreshState() {
    const st = MH.state;
    if (!st.playerName) return;
    try {
      const res = await fetch(MH.urls.state(st.playerName));
      if (res.ok) handleMapData(await res.json());
    } catch (_) {}
  };

  // --- MUD socket ---
  function handleMudMessage(raw) {
    let payload;
    try { payload = JSON.parse(raw); } catch (_) { payload = { type: 'output', data: raw }; }
    if (payload.type === 'output') {
      const text = MH.stripServerMarkup(payload.data || '');
      MH.bus.emit('terminal.output', { html: payload.data, text });
      const lines = text.split('\n').filter(l => l.trim());
      // chunkLen lets the parser treat short standalone chunks as ambient
      // narrative while ignoring look/score dumps
      for (const line of lines) MH.bus.emit('mud.line', { line, chunkLen: lines.length });
      answerLoginPrompts(text);
      inferLoginSuccess(text);
    } else if (payload.type === 'account') {
      // signed in to an account (or one just made): its heroes, for the page to list
      MH.state.newAccount = false;
      MH.state.account = payload;
      MH.bus.emit('account.menu', payload);
    } else if (payload.type === 'resume') {
      // this browser's sign-in token, fresh from the server
      if (payload.token) { MH.state.resumeToken = payload.token; MH.auth.set(MH.state.playerName, payload.token); }
    } else if (payload.type === 'mapsync') {
      if (payload.player) MH.state.playerName = payload.player;
      if (payload.token != null) MH.state.mapToken = payload.token;
      if (!MH.state.isLoggedIn) {
        MH.state.isLoggedIn = true;
        // signed in with the password: ask the server to remember this browser
        if (MH.state.playerPassword && !MH.state.resumeToken) MH.sendCommand('remember', false);
        MH.state.playerPassword = '';
        MH.bus.emit('login.success', MH.state.playerName);
      }
      ensureMapSocket();
      sendMapSubscribe();
      startResubscribe();
    }
  }

  // log in to an account (its email or name) with its password, make a new account (newAccount:
  // `name` signing in by `email` too), or (token given) come back as a hero with this browser's
  // stored sign-in
  MH.connect = function connect(name, password, newAccount, token, email) {
    const st = MH.state;
    st.playerName = name;
    st.playerPassword = token ? '' : password;
    st.resumeToken = token || '';
    st.newAccount = !!newAccount && !token;
    st.newEmail = st.newAccount ? (email || '') : '';
    st.account = null;
    st.loginSequenceStarted = false;
    st.isLoggedIn = false;
    st._loginNameSent = false;
    st._lastPromptKey = null;
    if (st.mudSocket) { try { st.mudSocket.close(); } catch (_) {} }
    MH.bus.emit('login.status', `Connecting to ${MH.urls.mudWs}…`);
    const sock = st.mudSocket = new WebSocket(MH.urls.mudWs);
    st.mudSocket.addEventListener('open', () => runLoginSequence());
    st.mudSocket.addEventListener('message', e => handleMudMessage(e.data));
    st.mudSocket.addEventListener('close', () => {
      MH.bus.emit('login.status', 'World socket closed.');
      // dropped mid-play (the server restarted, the network blinked), not a quit or a takeover:
      // the page waits for the server and signs back in (world3d/main.js)
      if (sock === st.mudSocket && st.isLoggedIn && !st.leaving) MH.bus.emit('connection.lost');
    });
    st.mudSocket.addEventListener('error', () => MH.bus.emit('login.error', 'Could not reach the gate. Is the server up?'));
  };

  // the server went away mid-play: try its socket every few seconds (backing off to 10 s); once
  // it answers, reload and sign straight back in with this browser's stored sign-in (login.js
  // reads the flag). A fresh page rebuilds the world rather than patching a stale one.
  MH.RESUME_FLAG = 'misthollow_autoresume';
  MH.awaitServer = function awaitServer(onTry) {
    let wait = 1500, tries = 0;
    const attempt = () => {
      tries++;
      if (onTry) onTry(tries);
      let ws;
      try { ws = new WebSocket(MH.urls.mudWs); } catch (_) { return later(); }
      ws.addEventListener('open', () => {
        try { ws.close(); } catch (_) {}
        try { sessionStorage.setItem(MH.RESUME_FLAG, '1'); } catch (_) {}
        location.reload();
      });
      ws.addEventListener('error', () => later());
    };
    let pending = false;
    const later = () => { if (pending) return; pending = true; setTimeout(() => { pending = false; attempt(); }, wait); wait = Math.min(10000, wait * 1.5); };
    later();
  };

  // sign out: the server forgets this browser's token, the character leaves the world
  MH.logout = function logout() {
    const st = MH.state;
    if (st.inCombat) return false;           // the caller says why (quit is refused mid-fight)
    const rec = MH.auth.get();
    if (rec && rec.token) MH.sendCommand(`forget ${rec.token}`, false);
    MH.auth.clear();
    st.resumeToken = '';
    st.leaving = true;
    MH.sendCommand('quit', false);
    setTimeout(() => location.reload(), 700);
    return true;
  };
})();
