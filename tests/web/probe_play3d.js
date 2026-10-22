// Browser probe for /play against a local server (./run.sh), with the gauntlet admin account.
//   NODE_PATH=/opt/node22/lib/node_modules node tests/web/probe_play3d.js stairs|doors|camera|menu|autotarget|creatures|spellbook|trainer|party|gear|abilityfx [outdir]
// CommonJS on purpose (the global Playwright only resolves through NODE_PATH with require).
// WebGL may render at ~1 fps in a container, so the probe places the hero directly and waits
// on frames instead of walking in real time.
//   stairs: the zone map download is delayed 3 s (the race that sent every zone hop twice);
//           taking the temple's ▲ stairs must send exactly one move, show no "can't go", land
//           beside the destination's ▼ stairs, and a key held into them must not hop back.
//   doors:  the diamond gate at 2512 north: the prompt says what E does, E opens it (one webdoor),
//           and a locked door without the key says which key it needs.
//   camera: a right-drag turns the view (no menu), W follows the camera, drag up tilts, Home
//           snaps back north.
//   menu:   a right-click on a creature offers Attack/Consider (naming it exactly), on the
//           hero "You".
//   autotarget: a creature that hits you becomes your target; a foe you picked stays.
//   spellbook: K opens the spellbook; an ability dragged onto slot 2 lands there and the bar is
//           saved (one `webbar`); key 2 uses it; dragging it off the bar removes it; a newly
//           learned ability glows into a free slot.
//   trainer: the minimap knows your guild; right-click your class's trainer → Master your
//           abilities opens the trainer window; Train takes a mastered ability 85 → 90.
//   party: two browsers (Gauntlet, Gauntletb) in the temple each draw the other; one walks and
//           the other sees it; invite -> the popup -> Join -> party frames on both.
//   creatures: a blob, a mimic, a statue, a chess rook, a stone golem, a goblin farmer, a brownie,
//           a living book and the Sewer King each get the right body (looks.js, from the payload's
//           short description and room line).
//   gear: two browsers (Gauntlet, Gauntletb) in the temple: each hero wears its own look; when
//           Gauntlet wields a greatblade, Gauntletb sees it re-dressed within seconds.
//   mount: buy a horse and mount it: the hero sits a steed and runs faster; dismount: on foot.
//   looks: a cave, a sewer, a desert and a crawlway under Moria draw as what they are (room_looks.py).
//   aim:    in the crypt: an area spell's key starts the aim (a circle under the mouse, the
//           reach round the hero); the circle follows the mouse; a click sends "cast ... @x,z"
//           in the room's own metres; Escape lets it go; an aimed spell's event lands its
//           blast on the point (aim.js, combat.js).
//   abilityfx: in the crypt with a spectre, a few of the character's own abilities each start
//           their own recipe on the key press (abilityfx.js) and the server's event plays the
//           rest (what flies, lands, lingers), with no page errors.
const fs = require('fs');
const path = require('path');
const { chromium } = require('playwright');

const MODE = process.argv[2] || 'stairs';
const OUT = process.argv[3] || '/tmp';
const CFG = JSON.parse(fs.readFileSync(path.join(__dirname, '../../tools/gauntlet/config.json'), 'utf8'));
const sleep = ms => new Promise(r => setTimeout(r, ms));
const results = [];
const check = (ok, what) => { results.push([ok, what]); console.log(`${ok ? 'ok  ' : 'FAIL'} ${what}`); };

async function waitFor(page, fn, arg, secs = 60) {
  for (let i = 0; i < secs * 4; i++) {
    if (await page.evaluate(fn, arg).catch(() => false)) return true;
    await sleep(250);
  }
  return false;
}

(async () => {
  const browser = await chromium.launch({ args: ['--use-gl=swiftshader', '--enable-webgl', '--ignore-gpu-blocklist', '--enable-unsafe-swiftshader'] });
  const page = await (await browser.newContext({ viewport: { width: 960, height: 540 } })).newPage();
  page.setDefaultTimeout(120000);
  const errors = [];
  page.on('pageerror', e => errors.push(String(e).slice(0, 300)));
  if (MODE === 'stairs') {
    await page.route('**/zonemap*', async route => { await sleep(3000); await route.continue(); });
  }
  await page.goto(`http://${CFG.mud.host}:${CFG.mud.mapPort}/play?q=low`, { waitUntil: 'load' });
  await waitFor(page, () => document.getElementById('loading').classList.contains('done'));
  await page.fill('#login-name', CFG.character.name);
  await page.fill('#login-pass', CFG.character.password);
  await page.click('#login-btn');
  check(await waitFor(page, () => !!(window.MH3D && MH3D.hero), null, 120), 'logged in, hero in the world');
  await page.evaluate(() => {
    window.__sent = [];
    const real = MH.sendCommand;
    MH.sendCommand = (cmd, echo) => { window.__sent.push(String(cmd)); return real(cmd, echo); };
    window.__toasts = [];
    new MutationObserver(m => { for (const r of m) for (const n of r.addedNodes) window.__toasts.push(n.textContent); })
      .observe(document.getElementById('toasts'), { childList: true });
  });
  const goto = async v => {
    await page.evaluate(v => MH.sendCommand(`goto ${v}`, false), v);
    return waitFor(page, v => MH3D.heroRoom() && MH3D.heroRoom().vnum === v && !MH3D.hop(), v, 90);
  };

  if (MODE === 'stairs') {
    check(await goto(3001), 'in the Temple of Garathorm (3001)');
    await sleep(1500);
    // stand 1.3 m west of the ▲ stairs and walk onto them on purpose
    const info = await page.evaluate(() => {
      const z = MH3D.zone(), r = MH3D.heroRoom(), sp = z.passageWorld(r, 'up');
      MH3D.hero.root.position.set(sp.x - 1.3, 0, sp.z);
      window.__sent.length = 0; window.__toasts.length = 0;
      MH3D.walkToPassage('up');
      return { to: r.data.exits.up && r.data.exits.up.to, kind: r.data.exits.up && r.data.exits.up.kind };
    });
    check(!!info.to, `the temple has stairs up (to ${info.to}, ${info.kind})`);
    // the bounce case: a key held through the hop, toward the stairs you arrive beside
    await waitFor(page, () => !!MH3D.hop(), null, 60);
    await page.evaluate(() => MH3D.ctl.keys.add('a'));
    const landed = await waitFor(page, to => MH3D.heroRoom() && MH3D.heroRoom().vnum === to && !MH3D.hop(), info.to, 120);
    check(landed, `took the stairs to ${info.to}`);
    const dist = await page.evaluate(() => {
      const z = MH3D.zone(), r = MH3D.heroRoom(), p = MH3D.hero.root.position;
      const sp = r.data.exits.down ? z.passageWorld(r, 'down') : null;
      return sp ? Math.hypot(p.x - sp.x, p.z - sp.z) : null;
    });
    check(dist != null && dist < 2.4, `landed beside the stairs back down (${dist && dist.toFixed(2)} m)`);
    await sleep(8000);                                  // still holding the key toward them
    await page.evaluate(() => MH3D.ctl.keys.delete('a'));
    const moves = await page.evaluate(() => window.__sent.filter(c => c.startsWith('webmove')));
    check(moves.length === 1 && / up$/.test(moves[0]), `exactly one move sent, no bounce back: ${JSON.stringify(moves)}`);
    const toasts = await page.evaluate(() => window.__toasts.join(' | '));
    check(!/can't go/i.test(toasts), `no "can't go that way" (${toasts || 'no toasts'})`);
    await page.screenshot({ path: path.join(OUT, 'stairs-landed.png') });
    // a deliberate return: stand still a moment, then walk onto them
    await sleep(1500);
    await page.evaluate(() => { window.__sent.length = 0; MH3D.walkToPassage('down'); });
    const back = await waitFor(page, () => window.__sent.some(c => / down$/.test(c)), null, 60);
    check(back, 'walking onto them on purpose takes them back down');
  }

  if (MODE === 'doors') {
    check(await goto(2512), 'at the diamond gate (2512)');
    await page.evaluate(() => { MH.sendCommand('open north', false); });
    await sleep(800);
    await page.evaluate(() => MH.sendCommand('close north', false));
    await waitFor(page, () => MH3D.heroRoom().doors.north && MH3D.heroRoom().doors.north.closed, null, 20);
    const at = await page.evaluate(() => {
      const r = MH3D.heroRoom();
      const p = MH3D.hero.root.position;
      p.set(r.ox + 12, 0, r.oz + 1.6);
      return [p.x, p.z];
    });
    await sleep(2500);
    const text = await page.evaluate(() => !document.getElementById('prompt').classList.contains('hidden') && document.querySelector('#prompt span').textContent);
    check(/open the diamond gate/i.test(text || ''), `prompt: "${text}"`);
    await page.screenshot({ path: path.join(OUT, 'door-prompt.png') });
    await page.evaluate(() => { window.__sent.length = 0; });
    await page.keyboard.press('e');
    const opened = await waitFor(page, () => MH3D.heroRoom().doors.north && !MH3D.heroRoom().doors.north.closed, null, 20);
    const sent = await page.evaluate(() => window.__sent.filter(c => c.startsWith('webdoor')));
    check(opened && sent.length === 1 && sent[0] === 'webdoor 2512 north open', `E opened it with one webdoor: ${JSON.stringify(sent)}`);
    const meshOpen = await page.evaluate(() => {
      const r = MH3D.heroRoom();
      const m = r.built && r.built.doors && r.built.doors.north;
      return m ? m.userData.open : 'no mesh';
    });
    check(meshOpen === true, `the door mesh swung open (${meshOpen})`);
    // lock it without the key: the prompt names the key
    await page.evaluate(() => { for (const c of ['oload 2500', 'close north', 'lock north', 'drop key', 'drop key', 'drop key', 'purge']) MH.sendCommand(c, false); });
    await sleep(2500);
    await page.evaluate(() => MH.refreshState && MH.refreshState());   // keys are per viewer: ask again
    await waitFor(page, () => MH3D.heroRoom().doors.north && MH3D.heroRoom().doors.north.locked, null, 20);
    await sleep(2500);
    const locked = await page.evaluate(() => document.querySelector('#prompt span').textContent);
    check(/needs a diamond key/i.test(locked || ''), `locked prompt: "${locked}"`);
    await page.screenshot({ path: path.join(OUT, 'door-locked.png') });
    // leave it as the zone keeps it
    await page.evaluate(() => { for (const c of ['oload 2500', 'unlock north', 'open north', 'drop key', 'drop key', 'drop key', 'purge']) MH.sendCommand(c, false); });
    await sleep(2000);
  }

  if (MODE === 'guardian') {
    // two gate guardians of one name at the castle door: one dies, it goes (and leaves a corpse)
    check(await goto(22001), 'on the Pathway To The Lost Castle (22001)');
    await page.evaluate(() => MH.sendCommand('mpeace', false));
    const ents = () => page.evaluate(() => [...MH3D.ents.list.values()].filter(e => e.kind === 'mob')
      .map(e => ({ key: e.key, name: e.data.name, hp: e.data.hp, maxHp: e.data.maxHp, vnum: e.vnum })));
    console.log('before', JSON.stringify(await ents()));
    await page.evaluate(() => MH.sendCommand('slay guardian', false));
    await sleep(4000);
    const after = await ents();
    console.log('after', JSON.stringify(after));
    check(after.filter(e => /guardian/.test(e.name)).length === 1, 'one guardian left');
    const items = await page.evaluate(() => (MH.state && MH.state.nearby || []).flatMap(r => (r.items || []).map(i => i.name)));
    console.log('items', JSON.stringify(items));
    await page.screenshot({ path: path.join(OUT, 'guardian.png') });
  }

  if (MODE === 'guardfight') {
    // a real fight with the gate guardians (worn down first): each one that dies leaves the view
    check(await goto(22001), 'on the Pathway To The Lost Castle (22001)');
    const me = CFG.character.name.toLowerCase();
    await page.evaluate(me => { for (const c of [`set ${me} maxhp 200000`, `set ${me} hp 200000`, 'set 1.guardian hp 400', 'set 2.guardian hp 400']) MH.sendCommand(c, false); }, me);
    await sleep(1500);
    const mobs = () => page.evaluate(() => [...MH3D.ents.list.values()].filter(e => e.kind === 'mob' && e.vnum === 22001)
      .map(e => ({ key: e.key, name: e.data.name, hp: e.data.hp, maxHp: e.data.maxHp })));
    console.log('start', JSON.stringify(await mobs()));
    await page.evaluate(() => MH.sendCommand('kill guardian', false));
    for (let i = 0; i < 40; i++) {
      await page.keyboard.press('f');
      await sleep(1000);
      const left = await mobs();
      if (i % 5 === 0) console.log(i, JSON.stringify(left));
      if (!left.some(m => /gate guardian/.test(m.name))) break;
    }
    await sleep(3000);
    const end = await mobs();
    console.log('end', JSON.stringify(end));
    const tgt = await page.evaluate(() => { const f = document.getElementById('target-frame') || document.querySelector('.target-frame'); return f && !f.classList.contains('hidden') ? f.textContent.replace(/\s+/g, ' ') : null; });
    console.log('target frame', tgt);
    check(!end.some(m => /gate guardian/.test(m.name)), 'both guardians gone from view once dead');
    await page.screenshot({ path: path.join(OUT, 'guardfight.png') });
    await page.evaluate(me => MH.sendCommand(`restore ${me}`, false), me);
  }

  if (MODE === 'sunken') {
    // the Sunken Ruins of Atal'narath: drowned streets and temples under the sea, and who lives there
    for (const [v, name] of [[13010, 'plaza'], [13011, 'temple'], [13005, 'kelp'], [13015, 'throne']]) {
      check(await goto(v), `in ${name} (${v})`);
      await sleep(3500);
      const info = await page.evaluate(() => { const r = MH3D.heroRoom(); return { look: r.data.look, sector: r.data.sector,
        mobs: [...MH3D.ents.list.values()].filter(e => e.kind === 'mob' && e.vnum === r.vnum).map(e => e.data.name) }; });
      console.log(v, JSON.stringify(info));
      await page.screenshot({ path: path.join(OUT, `sunken-${name}.png`) });
    }
  }

  if (MODE === 'garathorm') {
    // Garathorm and its districts: the watch in the streets, the wall, the cathedral and its bishop, Fameland
    for (const [v, name] of [[3014, 'market'], [2913, 'wall'], [4408, 'churchyard'], [4422, 'greathall'], [4472, 'ossuary'],
                             [4430, 'altar'], [4452, 'belfry'], [15222, 'firsthero'], [2815, 'fencing']]) {
      check(await goto(v), `in ${name} (${v})`);
      await sleep(3500);
      const info = await page.evaluate(() => { const r = MH3D.heroRoom(); return { look: r.data.look, sector: r.data.sector,
        mobs: [...MH3D.ents.list.values()].filter(e => e.kind === 'mob' && e.vnum === r.vnum).map(e => e.data.name) }; });
      console.log(v, JSON.stringify(info));
      await page.screenshot({ path: path.join(OUT, `garathorm-${name}.png`) });
    }
  }

  if (MODE === 'rooms') {
    // any rooms, from PROBE_ROOMS=vnum,vnum,...: its look, the creatures there and their plates
    for (const v of (process.env.PROBE_ROOMS || '').split(',').filter(Boolean).map(Number)) {
      check(await goto(v), `in ${v}`);
      await sleep(3500);
      const info = await page.evaluate(() => { const r = MH3D.heroRoom(); return { look: r.data.look,
        mobs: [...MH3D.ents.list.values()].filter(e => e.kind === 'mob' && e.vnum === r.vnum).map(e => e.data.name),
        plates: [...document.querySelectorAll('.plate')].map(p => p.className).filter(c => /boss|elite/.test(c)) }; });
      console.log(v, JSON.stringify(info));
      await page.screenshot({ path: path.join(OUT, `room-${v}.png`) });
    }
  }

  if (MODE === 'gates') {
    // just outside the gates: the Rat King, Black Jory, the Barrow King, the dracolich, the Alpha Wolf, Redferne
    for (const [v, name] of [[7320, 'ratking'], [19742, 'jory'], [8690, 'barrowking'], [5011, 'dracolich'], [20009, 'alphawolf'], [7911, 'redferne'],
                             [2590, 'summoner'], [5406, 'thalos'], [4044, 'grondar'], [3519, 'grukthar'], [12204, 'highpriest'], [8892, 'carcosa'],
                             [5141, 'lloth'], [3605, 'blackking'], [15017, 'welmar'], [14027, 'morthul'], [14030, 'verdraxx'], [4652, 'hrimgar'],
                             [16252, 'lordofchaos'], [16258, 'island'], [9901, 'ghenna'], [9937, 'deepdragon'],
                             [6411, 'rand'], [3375, 'aglandiir'], [6259, 'elstar'], [5332, 'ramses'], [11000, 'elves'],
                             [8003, 'scorathax'], [7352, 'mindflayer'], [8742, 'barrowwight'], [8357, 'blackpriest'], [18629, 'minotaur']]) {
      check(await goto(v), `in ${name} (${v})`);
      await sleep(3500);
      const info = await page.evaluate(() => { const r = MH3D.heroRoom(); return { look: r.data.look,
        mobs: [...MH3D.ents.list.values()].filter(e => e.kind === 'mob' && e.vnum === r.vnum).map(e => e.data.name),
        plates: [...document.querySelectorAll('.plate')].map(p => p.className) }; });
      console.log(v, JSON.stringify(info));
      await page.screenshot({ path: path.join(OUT, `gates-${name}.png`) });
    }
  }

  if (MODE === 'castlelife') {
    // the castle is alive: the Bone Marshal (a sub-boss) at the junction, sentries in the halls
    check(await goto(14139), 'at the Junction of the Inner Halls (14139)');
    await sleep(3000);
    const plates = await page.evaluate(() => [...document.querySelectorAll('.plate')].map(p => [p.className, p.querySelector('.nm').textContent]));
    console.log(JSON.stringify(plates));
    check(plates.some(([c, n]) => /subboss/.test(c) && /Bone Marshal/i.test(n)), 'the Bone Marshal wears a sub-boss plate');
    await page.screenshot({ path: path.join(OUT, 'castle-marshal.png') });
    check(await goto(14104), 'in the halls along the inner wall');
    await sleep(3000);
    await page.screenshot({ path: path.join(OUT, 'castle-halls.png') });
  }

  if (MODE === 'horsemen') {
    // the castle's bosses fight with their rooms: Pestilence's plague pools on the ground, Death's gloom
    const me = CFG.character.name.toLowerCase();
    await page.evaluate(() => { window.__ev = []; MH.bus.on('combat.events', p => { for (const e of p.events || []) window.__ev.push(e.k); }); });
    check(await goto(14151), 'in the first Guardian Chamber (14151)');
    await page.evaluate(me => { for (const c of [`set ${me} maxhp 200000`, `set ${me} hp 200000`, 'kill pestilence']) MH.sendCommand(c, false); }, me);
    const pool = await waitFor(page, () => window.__ev.includes('hazard'), null, 40);
    check(pool, 'Pestilence spits a plague pool (a hazard event)');
    await sleep(800);
    await page.screenshot({ path: path.join(OUT, 'horsemen-pool.png') });
    await page.evaluate(() => MH.sendCommand('flee', false));
    await sleep(1500);
    check(await goto(14153), 'at The Gates To Hell (14153)');
    await page.evaluate(me => { for (const c of [`restore ${me}`, `set ${me} maxhp 200000`, `set ${me} hp 200000`, 'set death hp 12000', 'kill death']) MH.sendCommand(c, false); }, me);
    const dark = await waitFor(page, () => (MH3D.engine.gloom || 0) > 0.5, null, 40);
    check(dark, `the room darkens around Death (gloom ${await page.evaluate(() => MH3D.engine.gloom)})`);
    await sleep(2500);
    await page.screenshot({ path: path.join(OUT, 'horsemen-gloom.png') });
    await page.evaluate(me => { for (const c of ['flee', `restore ${me}`]) MH.sendCommand(c, false); }, me);
    await sleep(800);
  }

  if (MODE === 'seam') {
    // a stretch of the Trade Road's woods (the owner's screenshot): rooms that lead to each other
    // sit side by side, so the way on is walked, not hopped
    check(await goto(1828), 'at the edge of the woods (1828)');
    await sleep(3000);
    const kinds = await page.evaluate(() => Object.values(MH3D.heroRoom().data.exits).map(e => e.kind));
    console.log('exits here:', JSON.stringify(kinds));
    check(kinds.filter(k => k === 'open').length >= kinds.filter(k => k === 'passage').length, `most ways on are walked across (${kinds})`);
    await page.screenshot({ path: path.join(OUT, 'seam-woods.png') });
    // stand by the passage that remains and look at it
    await page.evaluate(() => {
      const r = MH3D.heroRoom(), z = MH3D.zone();
      const d = Object.entries(r.data.exits).find(([k, e]) => e.kind === 'passage' && ['north', 'south', 'east', 'west'].includes(k));
      if (!d) return;
      const p = z.passageWorld(r, d[0]);
      const c = z.centre(r);
      MH3D.hero.root.position.set((p.x + c.x) / 2, 0, (p.z + c.z) / 2);
    });
    await sleep(2000);
    await page.screenshot({ path: path.join(OUT, 'seam-passage.png') });
  }

  if (MODE === 'dnd') {
    // drag and drop gear: two rings onto both fingers, a helm off onto the pack, rings lit only
    // on the fingers while dragged
    check(await goto(3001), 'in the Temple of Garathorm (3001)');
    await page.evaluate(() => { for (const c of ['remove all', 'oload 904', 'oload 904', 'oload 2570', 'wear cowl']) MH.sendCommand(c, false); });
    await sleep(1500);
    await page.evaluate(() => MH.refreshState && MH.refreshState());
    await sleep(1200);
    await page.keyboard.press('i');
    await waitFor(page, () => !document.getElementById('inventory').classList.contains('hidden'), null, 10);
    const RING = '#inventory .inv-bag .inv-cell[data-name="a platinum ring"]';
    console.log('pack:', JSON.stringify(await page.evaluate(() => [...document.querySelectorAll('#inventory .inv-bag .inv-cell[data-name]')].map(e => e.dataset.name))),
      'state:', JSON.stringify(await page.evaluate(() => (MH.state.player.inventory || []).map(i => i.short))));
    check(await waitFor(page, s => document.querySelectorAll(s).length >= 2, RING, 15), 'platinum rings in the pack');
    const src = await page.$(RING);
    const sb = await src.boundingBox();
    const f1 = await (await page.$('#inventory .inv-slot[data-slot="finger1"]')).boundingBox();
    await page.mouse.move(sb.x + sb.width / 2, sb.y + sb.height / 2);
    await page.mouse.down();
    await page.mouse.move(sb.x + sb.width / 2 + 30, sb.y + sb.height / 2 + 10, { steps: 4 });
    await sleep(200);
    const lit = await page.evaluate(() => [...document.querySelectorAll('#inventory .inv-slot.can-drop')].map(e => e.dataset.slot));
    check(JSON.stringify(lit) === JSON.stringify(['finger1', 'finger2']), `dragging a ring lights both fingers, and only them (${lit})`);
    await page.mouse.move(f1.x + f1.width / 2, f1.y + f1.height / 2, { steps: 8 });
    await page.mouse.up();
    await sleep(1500);
    await sleep(500);
    await page.dragAndDrop(RING, '#inventory .inv-slot[data-slot="finger2"]');
    await sleep(1500);
    const eq = await page.evaluate(() => { const e = MH.state.player.equipment || {}; return [e.finger1 && e.finger1.name, e.finger2 && e.finger2.name, e.head && e.head.name]; });
    check(/ring/.test(eq[0] || '') && /ring/.test(eq[1] || ''), `a platinum ring on each finger (${eq[0]} / ${eq[1]})`);
    await page.screenshot({ path: path.join(OUT, 'gear-rings.png') });
    if (eq[2]) {
      await page.dragAndDrop('#inventory .inv-slot[data-slot="head"] .inv-cell', '#inventory .inv-bag');
      await sleep(1500);
      const head = await page.evaluate(() => (MH.state.player.equipment || {}).head);
      check(!head, 'the cowl dragged onto the pack comes off');
    }
    await page.evaluate(() => { for (const c of ['remove all', ...Array(16).fill('drop ring'), 'drop cowl']) MH.sendCommand(c, false); });
    await sleep(800);
  }

  if (MODE === 'ambient') {
    // the world's murmurs as sound and cue, never chat: beside the weaponsmith the hammer rings;
    // in the castle's Entrance Chambers no town sound, and the gate guardians north are heard
    await page.evaluate(() => {
      window.__snd = [];
      const real = MH3D.sound.play.bind(MH3D.sound);
      MH3D.sound.play = (n, o) => { window.__snd.push([n, o && o.at ? [Math.round(o.at.x), Math.round(o.at.z)] : null]); return real(n, o); };
    });
    const logText = () => page.evaluate(() => document.getElementById('log').textContent);
    check(await goto(3011), 'in the Weapon Shop (3011)');
    const before = await logText();
    for (let i = 0; i < 14; i++) { await page.evaluate(() => MH.sendCommand('ambient now', false)); await sleep(350); }
    const snd = await page.evaluate(() => window.__snd.map(s => s[0]));
    console.log('sounds at the smithy:', JSON.stringify(snd));
    check(snd.some(n => n === 'amb_anvil'), 'the hammer rings beside the smith');
    check(snd.every(n => !/^amb_/.test(n) || ['amb_anvil', 'amb_crowd', 'amb_coins', 'amb_creak'].includes(n)), 'only the sounds of a smithy and a shop');
    const after = await logText();
    check(!/hammer|haggle|anvil|forge/i.test(after.slice(before.length)), 'and nothing of it in the chat');
    check(await goto(14102), 'in the castle Entrance Chambers (14102)');
    await page.evaluate(() => { window.__snd.length = 0; });
    let cue = false;
    for (let i = 0; i < 16 && !cue; i++) {
      await page.evaluate(() => MH.sendCommand('ambient now', false));
      await sleep(400);
      cue = await page.evaluate(() => !document.getElementById('amb-cue').classList.contains('hidden'));
    }
    const castle = await page.evaluate(() => window.__snd.map(s => s[0]));
    console.log('sounds in the castle:', JSON.stringify(castle));
    check(!castle.some(n => ['amb_anvil', 'amb_crowd', 'amb_coins', 'amb_cart', 'amb_bell'].includes(n)), 'no town sounds in the castle');
    const label = await page.evaluate(() => document.querySelector('#amb-cue .lab').textContent + ' · ' + document.querySelector('#amb-cue .sub').textContent);
    check(cue && /guardian/i.test(label), `the gate guardians north are heard: a cue "${label}"`);
    await page.screenshot({ path: path.join(OUT, 'ambient-cue.png') });
  }

  if (MODE === 'bars') {
    // extra action bars: one shows at first; an ability dragged onto it is kept (a 40-slot
    // webbar); Alt+1 uses it; the grip moves it and the place is remembered; it turns; Settings
    // shows three
    check(await goto(3001), 'in the Temple of Garathorm (3001)');
    const orig = await page.evaluate(() => (MH.state.player && MH.state.player.bar) || []);
    check(await waitFor(page, () => [...document.querySelectorAll('#xbars .xbar')].filter(e => getComputedStyle(e).display !== 'none').length === 1, null, 20),
      'one extra bar shows at first (the others are not drawn)');
    const id = await page.evaluate(() => { const el = document.querySelector('#slots .bar-row.main .slot[data-id]'); return el && el.dataset.id; });
    await page.evaluate(() => { window.__ab = []; MH.bus.on('hud.ability', a => window.__ab.push(a.id)); window.__sent.length = 0; });
    await page.dragAndDrop('#slots .bar-row.main .slot[data-id]', '#xbars .xbar[data-bar="0"] .slot[data-i="16"]');
    await sleep(600);
    const sent = await page.evaluate(() => window.__sent.filter(c => c.startsWith('webbar ')).pop() || '');
    const words = sent.split(' ').slice(1);
    check(words.length === 40 && words[16] === id, `dragged onto bar 3: kept with the character (${words.length} slots, slot 17 = ${words[16]}, want ${id})`);
    await page.keyboard.press('Alt+Digit1');
    await sleep(300);
    check(await page.evaluate(id => window.__ab.includes(id), id), `Alt+1 uses it (${id})`);
    const grip = await page.$('#xbars .xbar[data-bar="0"] .xgrip .dots');
    const gb = await grip.boundingBox();
    const before = await page.evaluate(() => { const e = document.querySelector('#xbars .xbar[data-bar="0"]'); return [e.offsetLeft, e.offsetTop]; });
    await page.mouse.move(gb.x + gb.width / 2, gb.y + gb.height / 2);
    await page.mouse.down();
    await page.mouse.move(gb.x - 150, gb.y - 120, { steps: 8 });
    await page.mouse.up();
    const after = await page.evaluate(() => { const e = document.querySelector('#xbars .xbar[data-bar="0"]'); return [e.offsetLeft, e.offsetTop]; });
    check(Math.abs(after[0] - before[0]) > 100 && Math.abs(after[1] - before[1]) > 80, `the grip moves it (${before} -> ${after})`);
    const saved = await page.evaluate(n => localStorage.getItem(`mh3d_bars:${n}`), CFG.character.name.toLowerCase());
    check(saved && JSON.parse(saved).bars[0] && Math.abs(JSON.parse(saved).bars[0].x - after[0]) < 2, 'and its place is remembered');
    await page.click('#xbars .xbar[data-bar="0"] .xturn');
    check(await page.evaluate(() => document.querySelector('#xbars .xbar[data-bar="0"]').classList.contains('vertical')), 'the turn button stands it on end');
    await page.keyboard.press('o');
    await page.click('#settings [data-set="xbars"] button[data-v="3"]');
    await sleep(300);
    check(await page.evaluate(() => document.querySelectorAll('#xbars .xbar:not(.off)').length) === 3, 'Settings: three extra bars');
    await page.keyboard.press('o');
    await page.screenshot({ path: path.join(OUT, 'bars.png') });
    // leave the character's bar as it was
    await page.evaluate(b => MH.sendCommand(`webbar ${b.length ? b.map(x => x || '-').join(' ') : ''}`.trim(), false), orig);
    await page.evaluate(n => localStorage.removeItem(`mh3d_bars:${n}`), CFG.character.name.toLowerCase());
  }

  if (MODE === 'deathtrap') {
    // the castle's inner hall: south of 22179 lies a death trap (22205, the Iron Maiden). It is
    // drawn as a ledge round a burning abyss; walking at it stops at the edge with a prompt; E dares it
    check(await goto(22179), 'in the Hall Along The Inner Wall (22179)');
    await sleep(2500);
    await page.screenshot({ path: path.join(OUT, 'deathtrap-from-outside.png') });
    console.log(JSON.stringify(await page.evaluate(() => { const z = MH3D.zone(), r = z.rooms.get(22205), h = MH3D.heroRoom();
      return { flags: r && r.data.flags, deadly: z.deadly ? z.deadly(r) : 'no fn', exits: h.data.exits, hasDared: !!z.dared }; })));
    const built = await page.evaluate(() => { const r = MH3D.zone().rooms.get(22205); return !!(r && r.built); });
    check(built, 'the death trap next door is built (seen from here)');
    await page.evaluate(() => { const r = MH3D.heroRoom(), g = MH3D.zone().layoutOf(r).gaps.south;
      MH3D.hero.root.position.set(r.ox + (g.x0 + g.x1 + 1) / 2, 0, r.oz + 15 - 2.2); });
    await page.keyboard.down('s');
    await sleep(2000);
    await page.keyboard.up('s');
    await sleep(500);
    const at = await page.evaluate(() => MH3D.heroRoom().vnum);
    const text = await page.evaluate(() => !document.getElementById('prompt').classList.contains('hidden') && document.querySelector('#prompt span').textContent);
    check(at === 22179, `walking at it stops at the edge (still in ${at})`);
    check(/certain death/i.test(text || ''), `the prompt warns: "${text}"`);
    await page.screenshot({ path: path.join(OUT, 'deathtrap-edge.png') });
    await page.keyboard.press('e');
    const dared = await page.evaluate(() => MH3D.zone().dared.has(22205));
    check(dared, 'E dares it');
    // inside (an immortal's goto skips the trap): the abyss
    await page.evaluate(() => MH.sendCommand('goto 22205', false));
    await waitFor(page, () => MH3D.heroRoom() && MH3D.heroRoom().vnum === 22205, null, 30);
    await sleep(2500);
    await page.screenshot({ path: path.join(OUT, 'deathtrap-inside.png') });
    await page.evaluate(() => MH.sendCommand('goto 22179', false));
  }

  if (MODE === 'castle') {
    // the Castle of the Apocalypse's front door (22001 south, closed) from the Tunnel of Sticks
    check(await goto(22001), 'on the Pathway To The Lost Castle (22001)');
    await page.evaluate(() => MH.sendCommand('close south', false));
    await waitFor(page, () => MH3D.heroRoom().doors.south && MH3D.heroRoom().doors.south.closed, null, 20);
    const info = await page.evaluate(() => {
      const r = MH3D.heroRoom();
      return { exits: r.data.exits, door: r.doors.south, built: !!(r.built && r.built.doors && r.built.doors.south) };
    });
    console.log(JSON.stringify(info));
    await page.screenshot({ path: path.join(OUT, 'castle-door.png') });
    // stand at the door
    const spot = await page.evaluate(() => {
      const r = MH3D.heroRoom(), L = MH3D.zone().layoutOf(r);
      const g = L.gaps && L.gaps.south;
      const p = MH3D.hero.root.position;
      p.set(r.ox + (g ? (g.x0 + g.x1 + 1) / 2 : 12), 0, r.oz + 15 - 1.6);
      return { gap: g, at: [p.x - r.ox, p.z - r.oz], passages: MH3D.zone().passageSpots(r) };
    });
    console.log('spot', JSON.stringify(spot));
    await sleep(2500);
    const text = await page.evaluate(() => !document.getElementById('prompt').classList.contains('hidden') && document.querySelector('#prompt span').textContent);
    check(/open/i.test(text || ''), `walking at it prompts: "${text}"`);
    await page.screenshot({ path: path.join(OUT, 'castle-prompt.png') });
    await page.keyboard.press('e');
    const opened = await waitFor(page, () => MH3D.heroRoom().doors.south && !MH3D.heroRoom().doors.south.closed, null, 20);
    check(opened, 'E opens it');
    await page.keyboard.down('s');
    const inside = await waitFor(page, () => MH3D.heroRoom().vnum === 14102, null, 15);
    await page.keyboard.up('s');
    check(inside, `walking on goes in (${await page.evaluate(() => MH3D.heroRoom().vnum)})`);
    await page.screenshot({ path: path.join(OUT, 'castle-in.png') });
  }

  if (MODE === 'camera') {
    check(await goto(3001), 'in the Temple of Garathorm (3001)');
    await sleep(1500);
    const box = await page.evaluate(() => { const r = MH3D.engine.renderer.domElement.getBoundingClientRect(); return { x: r.left + r.width / 2, y: r.top + r.height / 2 }; });
    // right-drag 120 px to the right: the view turns right, and no menu opens
    await page.mouse.move(box.x, box.y);
    await page.mouse.down({ button: 'right' });
    await page.mouse.move(box.x + 120, box.y, { steps: 8 });
    await page.mouse.up({ button: 'right' });
    await sleep(500);
    const yaw = await page.evaluate(() => MH3D.engine.rig.yaw);
    check(Math.abs(yaw - -0.78) < 0.06, `right-drag 120 px turned the view (yaw ${yaw.toFixed(3)})`);
    check(await page.evaluate(() => document.getElementById('ctx-menu').classList.contains('hidden')), 'a drag opens no menu');
    const w = await page.evaluate(() => { MH3D.ctl.keys.add('w'); const v = MH3D.ctl.wish(); MH3D.ctl.keys.delete('w'); return [v.x, v.y]; });
    check(Math.abs(w[0] - Math.sin(-yaw)) < 0.02 && Math.abs(w[1] + Math.cos(yaw)) < 0.02, `W walks away from the turned camera (${w.map(n => n.toFixed(2))})`);
    // drag up: a higher view (tilt), kept within limits
    await page.mouse.move(box.x, box.y);
    await page.mouse.down({ button: 'right' });
    await page.mouse.move(box.x, box.y - 400, { steps: 8 });
    await page.mouse.up({ button: 'right' });
    const tilt = await page.evaluate(() => MH3D.engine.rig.tilt);
    check(tilt > 9.9 && tilt <= 10, `dragging up tilts the view, to its limit (${tilt.toFixed(1)}°)`);
    await page.screenshot({ path: path.join(OUT, 'camera-turned.png') });
    await page.keyboard.press('Home');
    await waitFor(page, () => !MH3D.engine.rig.snap, null, 30);
    const back = await page.evaluate(() => [MH3D.engine.rig.yaw, MH3D.engine.rig.tilt]);
    check(back[0] === 0 && back[1] === 0, `Home: north up again (${back})`);
  }

  if (MODE === 'menu' || MODE === 'autotarget') {
    check(await goto(18620), 'in the crypt (18620)');
    await page.evaluate(() => { for (const c of ['purge', 'mload 18610', 'mload 18610']) MH.sendCommand(c, false); });
    await sleep(1500);
    await page.evaluate(() => MH.state.mapSocket.send(JSON.stringify({ type: 'subscribe', player: MH.state.playerName, token: MH.state.mapToken, mode: 'near' })));
    const two = await waitFor(page, () => [...MH3D.ents.list.values()].filter(e => e.kind === 'mob' && e.vnum === 18620 && e.root).length >= 2, null, 60);
    check(two, 'two spectres drawn');
    const ids = await page.evaluate(() => [...MH3D.ents.list.values()].filter(e => e.kind === 'mob' && e.vnum === 18620).map(e => e.data.id));
    if (MODE === 'menu') {
      await sleep(1500);
      const at = await page.evaluate(id => {
        const e = MH3D.ents.list.get(`m${id}`), cv = MH3D.engine.renderer.domElement, r = cv.getBoundingClientRect();
        const v = e.root.position.clone().setY(e.root.position.y + 1.1).project(MH3D.engine.camera);
        return { x: r.left + (v.x + 1) / 2 * r.width, y: r.top + (1 - v.y) / 2 * r.height };
      }, ids[1]);
      await page.mouse.click(at.x, at.y, { button: 'right' });
      await sleep(400);
      const items = await page.evaluate(() => [...document.querySelectorAll('#ctx-menu button')].map(b => b.textContent));
      check(items.includes('Attack') && items.includes('Consider'), `right-click on a spectre: ${JSON.stringify(items)}`);
      await page.screenshot({ path: path.join(OUT, 'menu-mob.png') });
      await page.evaluate(() => { window.__sent.length = 0; });
      await page.evaluate(() => [...document.querySelectorAll('#ctx-menu button')].find(b => b.textContent === 'Consider').click());
      await sleep(300);
      const sent = await page.evaluate(() => window.__sent.slice());
      check(sent.includes(`consider #${ids[1]}`), `Consider names that exact spectre: ${JSON.stringify(sent)}`);
      // the hero
      const me = await page.evaluate(() => {
        const cv = MH3D.engine.renderer.domElement, r = cv.getBoundingClientRect(), p = MH3D.hero.root.position;
        const v = p.clone().setY(p.y + 1.1).project(MH3D.engine.camera);
        return { x: r.left + (v.x + 1) / 2 * r.width, y: r.top + (1 - v.y) / 2 * r.height };
      });
      await page.mouse.click(me.x, me.y, { button: 'right' });
      await sleep(400);
      const title = await page.evaluate(() => (document.querySelector('#ctx-menu .ctx-title') || {}).textContent);
      check(title === 'You', `right-click on yourself: "${title}"`);
      await page.keyboard.press('Escape');
    } else {
      const name = await page.evaluate(() => MH.state.playerName);
      await page.evaluate(() => MH3D.ents.setTarget(null));
      await page.evaluate(({ id, name }) => MH.bus.emit('combat.events', { events: [{ k: 'attack', src: { m: id }, dst: { p: name }, res: 'hit' }] }), { id: ids[0], name });
      await sleep(300);
      check(await page.evaluate(id => MH3D.ents.target === `m${id}`, ids[0]), 'a creature that hits you becomes your target');
      // you pick the other one by hand and it fights you: the first one's blows don't steal it
      await page.evaluate(id => { const e = MH3D.ents.list.get(`m${id}`); e.data.fighting = true; MH3D.ents.setTarget(e.key, { byHand: true }); }, ids[1]);
      await page.evaluate(({ id, name }) => MH.bus.emit('combat.events', { events: [{ k: 'attack', src: { m: id }, dst: { p: name }, res: 'hit' }] }), { id: ids[0], name });
      await sleep(300);
      check(await page.evaluate(id => MH3D.ents.target === `m${id}`, ids[1]), 'your chosen foe stays targeted');
    }
    await page.evaluate(() => MH.sendCommand('purge', false));
    await sleep(800);
  }

  if (MODE === 'spellbook') {
    check(await goto(3001), 'in the Temple of Garathorm (3001)');
    await page.evaluate(() => MH.sendCommand('webbar', false));          // no arguments: forget the arranged bar
    await sleep(1500);
    await page.evaluate(() => MH.refreshState && MH.refreshState());
    await sleep(1500);
    await page.keyboard.press('k');
    const cards = await waitFor(page, () => document.querySelectorAll('#spellbook:not(.hidden) .sb-card').length > 0, null, 20);
    check(cards, 'K opens the spellbook with ability cards');
    const info = await page.evaluate(() => {
      const all = [...document.querySelectorAll('#spellbook .sb-card')];
      const known = all.filter(c => c.getAttribute('draggable') === 'true');
      return { all: all.length, known: known.length, locked: all.filter(c => c.classList.contains('locked')).length,
        ids: known.map(c => c.dataset.id), text: (all[0] || {}).textContent };
    });
    check(info.known > 0, `known abilities can be dragged (${info.known} of ${info.all}; ${info.locked} still to come)`);
    await page.screenshot({ path: path.join(OUT, 'spellbook.png') });
    // drag the last known ability onto slot 2
    const id = info.ids[info.ids.length - 1];
    await page.evaluate(() => { window.__sent.length = 0; });
    await page.dragAndDrop(`#spellbook .sb-card[data-id="${id}"]`, '#slots .bar-row.main .slot[data-i="1"]');
    await sleep(600);
    const placed = await page.evaluate(() => (document.querySelector('#slots .slot[data-i="1"]') || {}).dataset);
    check(placed && placed.id === id, `dragged ${id} onto slot 2 (${placed && placed.id})`);
    const sent = await page.evaluate(() => window.__sent.filter(c => c.startsWith('webbar')));
    check(sent.length === 1 && sent[0].split(' ')[2] === id, `the bar was saved once: ${JSON.stringify(sent)}`);
    // the server keeps it: a fresh payload still has it there
    await sleep(4500);
    await page.evaluate(() => MH.refreshState && MH.refreshState());
    await sleep(2000);
    const kept = await page.evaluate(() => (document.querySelector('#slots .slot[data-i="1"]') || {}).dataset);
    check(kept && kept.id === id, `the server kept it in slot 2 (${kept && kept.id})`);
    // key 2 uses it
    const used = await page.evaluate(() => new Promise(res => {
      const off = MH.bus.on('hud.ability', ab => res(ab.id));
      window.dispatchEvent(new KeyboardEvent('keydown', { key: '2', code: 'Digit2' }));
      setTimeout(() => res(null), 800);
    }));
    check(used === id, `key 2 uses it (${used})`);
    await page.keyboard.press('k');
    await page.screenshot({ path: path.join(OUT, 'bar.png') });
    // right-click the slot: Take off the bar
    const box = await page.evaluate(() => { const r = document.querySelector('#slots .slot[data-i="1"]').getBoundingClientRect(); return { x: r.left + r.width / 2, y: r.top + r.height / 2 }; });
    await page.mouse.click(box.x, box.y, { button: 'right' });
    await sleep(300);
    const items = await page.evaluate(() => [...document.querySelectorAll('#ctx-menu button')].map(b => b.textContent));
    check(items.includes('Take off the bar'), `right-click a slot: ${JSON.stringify(items)}`);
    await page.evaluate(() => [...document.querySelectorAll('#ctx-menu button')].find(b => b.textContent === 'Take off the bar').click());
    await sleep(400);
    check(await page.evaluate(() => document.querySelector('#slots .slot[data-i="1"]').classList.contains('empty')), 'slot 2 is empty again');
    // a newly learned ability is announced and glows into the free slot
    const learnt = await page.evaluate(id => {
      const p = JSON.parse(JSON.stringify(MH.state.player));
      const before = JSON.parse(JSON.stringify(p));
      delete before.skills[id];
      MH.bus.emit('map', { ...window.MH3D.lastPayload(), player: before });
      MH.bus.emit('map', { ...window.MH3D.lastPayload(), player: p });
      const slot = document.querySelector(`#slots .slot[data-id="${id}"]`);
      return { glow: !!slot && slot.classList.contains('glow'), key: slot && slot.dataset.i,
        toast: [...document.querySelectorAll('#toasts div')].map(d => d.textContent).join(' | ') };
    }, id);
    check(learnt.glow && learnt.key === '1' && /You learned/.test(learnt.toast), `a new ability glows into the free slot: ${JSON.stringify(learnt)}`);
    await page.evaluate(() => MH.sendCommand('webbar', false));
  }

  if (MODE === 'trainer') {
    check(await goto(3001), 'in the Temple of Garathorm (3001)');
    const guild = await page.evaluate(() => MH.state.player && MH.state.player.guild);
    check(guild && guild.vnum, `the payload names your guild's trainer (${guild && guild.trainer}, ${guild && guild.room})`);
    await page.evaluate(n => MH.sendCommand(`set ${n} skill bash 85`, false), CFG.character.name.toLowerCase());
    check(await goto(guild.vnum), `at the guild (${guild.vnum})`);
    await sleep(2500);
    const at = await page.evaluate(() => {
      const e = [...MH3D.ents.list.values()].find(x => x.kind === 'mob' && x.data.trainer && x.root);
      if (!e) return null;
      const cv = MH3D.engine.renderer.domElement, r = cv.getBoundingClientRect();
      const v = e.root.position.clone().setY(e.root.position.y + 1.1).project(MH3D.engine.camera);
      return { x: r.left + (v.x + 1) / 2 * r.width, y: r.top + (1 - v.y) / 2 * r.height, name: e.data.name };
    });
    check(!!at, `the trainer stands here (${at && at.name})`);
    if (at) {
      await page.mouse.click(at.x, at.y, { button: 'right' });
      await sleep(400);
      const items = await page.evaluate(() => [...document.querySelectorAll('#ctx-menu button')].map(b => b.textContent));
      check(items.includes('Master your abilities'), `right-click the trainer: ${JSON.stringify(items)}`);
      await page.evaluate(() => [...document.querySelectorAll('#ctx-menu button')].find(b => b.textContent === 'Master your abilities').click());
      const rows = await waitFor(page, () => document.querySelectorAll('#trainer:not(.hidden) .tr-row').length > 0, null, 20);
      check(rows, 'the trainer window lists your abilities');
      const bashRow = await page.evaluate(() => {
        const b = document.querySelector('#trainer .tr-buy[data-id="bash"]');
        return b ? { text: b.closest('.tr-row').textContent, enabled: !b.disabled } : null;
      });
      check(bashRow && bashRow.enabled && /85% → 90%/.test(bashRow.text), `bash can be trained: ${bashRow && bashRow.text.trim()}`);
      await page.screenshot({ path: path.join(OUT, 'trainer.png') });
      await page.evaluate(() => { window.__sent.length = 0; document.querySelector('#trainer .tr-buy[data-id="bash"]').click(); });
      const done = await waitFor(page, () => [...document.querySelectorAll('#log div')].some(d => /bash: 85% → 90%/.test(d.textContent)), null, 20);
      check(done, 'Train: "drills you in bash: 85% → 90%"');
      const sent = await page.evaluate(() => window.__sent.slice());
      check(sent.includes('practice bash'), `it sent "practice bash" (${JSON.stringify(sent)})`);
    }
    await page.evaluate(n => MH.sendCommand(`set ${n} skill bash 50`, false), CFG.character.name.toLowerCase());
    await sleep(600);
  }

  if (MODE === 'party') {
    // a second player in a second browser
    const page2 = await (await browser.newContext({ viewport: { width: 960, height: 540 } })).newPage();
    page2.on('pageerror', e => errors.push('B: ' + String(e).slice(0, 300)));
    await page2.goto(`http://${CFG.mud.host}:${CFG.mud.mapPort}/play?q=low`, { waitUntil: 'load' });
    await waitFor(page2, () => document.getElementById('loading').classList.contains('done'));
    await page2.fill('#login-name', 'Gauntletb');
    await page2.fill('#login-pass', 'gauntlet1');
    await page2.click('#login-btn');
    check(await waitFor(page2, () => !!(window.MH3D && MH3D.hero), null, 120), 'second player logged in');
    for (const pg of [page, page2]) {
      await pg.evaluate(() => { MH.sendCommand('group leave', false); MH.sendCommand('goto 3001', false); });
    }
    const seesB = await waitFor(page, () => { const e = MH3D.ents.list.get('pGauntletb'); return !!(e && e.root); }, null, 60);
    const seesA = await waitFor(page2, () => { const e = MH3D.ents.list.get('pGauntlet'); return !!(e && e.root); }, null, 60);
    check(seesB && seesA, `each draws the other (${seesB}, ${seesA})`);
    // B walks: A's picture of B follows
    const dest = await page2.evaluate(() => {
      const r = MH3D.heroRoom(); const p = MH3D.hero.root.position;
      p.set(r.ox + 5, 0, r.oz + 4);
      return { x: r.ox + 5, z: r.oz + 4 };
    });
    const followed = await waitFor(page, d => {
      const e = MH3D.ents.list.get('pGauntletb');
      return e && e.root && Math.hypot(e.root.position.x - d.x, e.root.position.z - d.z) < 0.8;
    }, dest, 30);
    check(followed, 'when Gauntletb walks, Gauntlet sees it');
    // invite, accept from the popup, party frames on both
    await page.evaluate(() => MH.sendCommand('group invite gauntletb', false));
    const popup = await waitFor(page2, () => !document.getElementById('group-invite').classList.contains('hidden'), null, 20);
    check(popup, 'the invite pops up for Gauntletb');
    await page2.screenshot({ path: path.join(OUT, 'party-invite.png') });
    if (popup) await page2.click('#group-invite .join');
    const framesA = await waitFor(page, () => [...document.querySelectorAll('#party .pt')].some(f => f.dataset.name === 'Gauntletb'), null, 20);
    const framesB = await waitFor(page2, () => [...document.querySelectorAll('#party .pt')].some(f => f.dataset.name === 'Gauntlet'), null, 20);
    check(framesA && framesB, `party frames on both (${framesA}, ${framesB})`);
    const crown = await page2.evaluate(() => !!document.querySelector('#party .pt[data-name="Gauntlet"] .crown'));
    check(crown, "Gauntletb's frame for Gauntlet wears the leader's crown");
    await page.screenshot({ path: path.join(OUT, 'party-frames.png') });
    await page2.evaluate(() => MH.sendCommand('group leave', false));
    const cleared = await waitFor(page, () => document.getElementById('party').classList.contains('hidden'), null, 20);
    check(cleared, "when Gauntletb leaves, Gauntlet's frames clear");
    await page2.close();
  }

  if (MODE === 'creatures') {
    check(await goto(3001), 'in the Temple of Garathorm (3001)');
    const want = { 3068: 'slime', 5202: 'chest', 5423: 'knight still', 3602: 'knight', 3016: 'knight', 23506: 'greendemon', 6115: 'mage', 6402: 'book_single', 3014: 'rat' };
    await page.evaluate(vs => { for (const c of ['purge', ...vs.map(v => `mload ${v}`)]) MH.sendCommand(c, false); }, Object.keys(want));
    await sleep(1500);
    await page.evaluate(() => MH.state.mapSocket.send(JSON.stringify({ type: 'subscribe', player: MH.state.playerName, token: MH.state.mapToken, mode: 'near' })));
    const n = Object.keys(want).length;
    check(await waitFor(page, n => [...MH3D.ents.list.values()].filter(e => e.kind === 'mob' && e.vnum === 3001 && e.root).length >= n, n, 90), `all ${n} drawn`);
    const got = await page.evaluate(() => [...MH3D.ents.list.values()].filter(e => e.kind === 'mob' && e.vnum === 3001).map(e => {
      const l = e.look || {}, b = l.beast;
      return { pv: e.data.pv, short: e.data.short, long: e.data.long, body: b ? (b.mob || b.proc || b.prop[1]) : l.model + (l.still ? ' still' : ''), fly: e.fly, y: +e.root.position.y.toFixed(2) };
    }));
    for (const [pv, body] of Object.entries(want)) {
      const g = got.find(x => String(x.pv) === pv);
      check(g && g.body === body, `${pv} ${g ? g.short : '?'}: ${g ? g.body : 'missing'} (want ${body})`);
    }
    const book = got.find(x => x.pv === 6402);
    check(book && book.fly > 0 && book.y > 0.5, `the living book flies (${book && book.y} m)`);
    check(got.some(x => x.pv === 3014 && /rat-man/.test(x.long || '')), 'the payload carries the room line');
    // stand back from them for a picture
    await page.evaluate(() => {
      const ms = [...MH3D.ents.list.values()].filter(e => e.kind === 'mob' && e.vnum === 3001 && e.root);
      const c = ms.reduce((a, e) => a.add(e.root.position), new MH3D.THREE.Vector3()).multiplyScalar(1 / ms.length);
      MH3D.hero.root.position.set(c.x, 0, c.z + 7);
    });
    await sleep(4000);
    await page.screenshot({ path: path.join(OUT, 'creatures.png') });
    await page.evaluate(() => MH.sendCommand('purge', false));
    await sleep(800);
  }

  if (MODE === 'abilityfx') {
    check(await goto(18620), 'in the crypt (18620)');
    const spectre = () => [...MH3D.ents.list.values()].find(e => e.kind === 'mob' && e.vnum === 18620 && e.root && e.alive && !(e.data.maxHp && e.data.hp <= 0));
    const fresh = async () => {
      const alive = src => !!eval(`(${src})`)();
      if (await page.evaluate(alive, String(spectre))) return true;
      await page.evaluate(() => { MH.sendCommand('mload 18610', false); });
      await sleep(1200);
      await page.evaluate(() => MH.state.mapSocket.send(JSON.stringify({ type: 'subscribe', player: MH.state.playerName, token: MH.state.mapToken, mode: 'near' })));
      return waitFor(page, alive, String(spectre), 60);
    };
    await page.evaluate(() => { for (const c of ['purge', 'restore']) MH.sendCommand(c, false); });
    await sleep(800);
    check(await fresh(), 'a spectre to practise on');
    // record what the effects director is asked to do: the key press, then the server's event
    const info = await page.evaluate(async () => {
      window.__fx = [];
      const d = MH3D.combat.director, pre = d.prelude.bind(d), play = d.play.bind(d);
      d.prelude = (r, o) => { window.__fx.push(['pre', r.id, r.known]); return pre(r, o); };
      d.play = (r, c) => { window.__fx.push(['play', r.id, r.known, !!(c.src && c.src.hero)]); return play(r, c); };
      // what the character knows: the class's book and the payload's proficiencies
      const p = MH.state.player || {}, cls = String(p.char_class || '').toLowerCase();
      const book = (await (await fetch(`/abilitybook?cls=${cls}`)).json()).abilities || [];
      const pct = id => Math.max((p.skills || {})[id] || 0, (p.spells || {})[id] || 0);
      const abs = book.filter(a => !a.passive && pct(a.id) > 0);
      return { cls, known: abs.map(a => ({ id: a.id, type: a.type, target: a.target || 'enemy' })) };
    });
    const pick = [...info.known.filter(a => a.target === 'enemy').slice(0, 3), ...info.known.filter(a => a.target === 'self').slice(0, 1)];
    check(pick.length >= 2, `${info.cls}: trying ${pick.map(a => a.id).join(', ')}`);
    let played = 0;
    for (const a of pick) {
      await fresh();
      await page.evaluate(spectre => {
        const m = eval(`(${spectre})`)();
        if (m) { MH3D.ents.setTarget(m.key, { byHand: true }); MH3D.hero.root.position.copy(m.root.position).add(new MH3D.THREE.Vector3(-1.8, 0, 0)); }
        MH.sendCommand('restore', false);
        window.__fx.length = 0;
      }, String(spectre));
      await sleep(600);
      await page.evaluate(a => MH.bus.emit('hud.ability', { id: a.id, spell: a.type === 'spell', self: a.target !== 'enemy' && a.target !== 'ally', ally: a.target === 'ally' }), a);
      const started = await waitFor(page, id => window.__fx.some(f => f[0] === 'pre' && f[1] === id && f[2]), a.id, 6);
      const landed = await waitFor(page, id => window.__fx.some(f => f[0] === 'play' && f[1] === id && f[3]), a.id, 8);
      await sleep(450);
      await page.screenshot({ path: path.join(OUT, `abilityfx-${a.id}.png`) });
      if (started && landed) played++;
      console.log(`     ${a.id}: key press ${started ? 'played its own recipe' : 'NOT played'}, server event ${landed ? 'played' : 'did not come (refused, cooldown?)'}`);
      await sleep(2200);
    }
    check(played >= 2, `${played} of ${pick.length} abilities played their own look from the key press and the server's event`);
    await page.evaluate(() => MH.sendCommand('purge', false));
    await sleep(800);
  }

  if (MODE === 'atlas') {
    // the world re-laid on the Bedlam atlas: the city, the long trade road, the forest and the
    // Newbie Zone through its hookup each load and draw without page errors
    check(await goto(3001), 'in the Temple of Garathorm (3001)');
    const city = await page.evaluate(() => ({ name: MH3D.zone().name, n: MH3D.zone().rooms.size, room: MH3D.heroRoom().name }));
    check(/Garathorm/.test(city.name) && city.n > 150, `the city is the atlas's Garathorm (${city.name}, ${city.n} rooms)`);
    check(/Temple Of Garathorm/i.test(city.room), `the temple has its atlas name (${city.room})`);
    await page.screenshot({ path: path.join(OUT, 'atlas-temple.png') });
    for (const [v, label] of [[3061, 'the Great Field, on the Trade Road'], [6001, 'the Light Forest trail, on the Plains'], [18600, 'the Newbie Zone']]) {
      const t = Date.now();
      const ok = await goto(v);
      const info = await page.evaluate(() => ({ name: MH3D.zone().name, n: MH3D.zone().rooms.size }));
      check(ok, `${label}: arrived, zone ${info.name} (${info.n} rooms) in ${((Date.now() - t) / 1000).toFixed(1)} s`);
      await sleep(1500);
    }
    // walk the hookup as a player would: from the Great Field east into the Newbie Zone
    await goto(3061);
    await sleep(1000);
    await page.evaluate(() => MH.sendCommand('east', false));
    check(await waitFor(page, () => MH3D.heroRoom() && MH3D.heroRoom().vnum === 18600 && !MH3D.hop(), null, 90),
      'east from the Great Field walks into the Newbie Zone');
    await page.screenshot({ path: path.join(OUT, 'atlas-newbie.png') });
    check(errors.length === 0, `no page errors (${errors.slice(0, 2).join(' | ')})`);
  }

  if (MODE === 'mount') {
    // riding (steed.js): bought and mounted, the hero sits a steed and runs faster; dismounted,
    // back on foot at walking pace
    check(await goto(3014), 'in a street of Garathorm (3014)');
    await page.evaluate(() => { MH.sendCommand('dismount', false); MH.sendCommand('stable buy horse', false); });
    await sleep(1500);
    await page.evaluate(() => MH.sendCommand('mount horse', false));
    check(await waitFor(page, () => MH3D.ctl.mounted && MH3D.ctl.speedMul > 1.2, null, 30), 'mounted: the hero sits a horse');
    const riding = await page.evaluate(() => ({ steed: !!MH3D.hero.root.children.find(c => /^steed_/.test(c.name)), mul: MH3D.ctl.speedMul }));
    check(riding.steed && Math.abs(riding.mul - 1.35) < 0.08, `a steed is drawn under the hero, and the run is ${riding.mul}x`);
    await page.screenshot({ path: path.join(OUT, 'mount-riding.png') });
    // run east for a moment, mounted, and see how far it gets
    const runFor = async () => page.evaluate(async () => {
      const p0 = MH3D.hero.root.position.clone();
      MH3D.ctl.keys.add('d');
      await new Promise(r => setTimeout(r, 1200));
      MH3D.ctl.keys.delete('d');
      return Math.hypot(MH3D.hero.root.position.x - p0.x, MH3D.hero.root.position.z - p0.z) / Math.max(0.2, MH3D.ctl.vel.length() || 1);
    });
    const topRiding = await page.evaluate(() => MH3D.ctl.speedMul * 5.2);
    await runFor();
    await page.evaluate(() => MH.sendCommand('dismount', false));
    check(await waitFor(page, () => !MH3D.ctl.mounted && MH3D.ctl.speedMul === 1, null, 30), 'dismounted: on foot again');
    const onFoot = await page.evaluate(() => ({ steed: !!MH3D.hero.root.children.find(c => /^steed_/.test(c.name)), top: MH3D.ctl.speedMul * 5.2 }));
    check(!onFoot.steed && topRiding > onFoot.top * 1.2, `riding runs faster than on foot (${topRiding.toFixed(1)} m/s against ${onFoot.top.toFixed(1)})`);
    check(errors.length === 0, `no page errors (${errors.slice(0, 2).join(' | ')})`);
  }

  if (MODE === 'looks') {
    // rooms look like what they say (room_looks.py): a cave typed 'inside' draws as a cave, a
    // sewer typed 'mountain' as a sewer, a desert typed 'field' as desert
    for (const [v, want] of [[4469, 'cave'], [7001, 'sewer'], [5300, 'desert'], [20508, 'cave']]) {
      const ok = await goto(v);
      await sleep(2500);
      const got = await page.evaluate(() => { const r = MH3D.heroRoom(); const L = MH3D.zone().layoutOf(r); return { name: r.name, look: r.data.look, theme: L.theme }; });
      check(ok && got.look === want && got.theme === want, `${got.name} (${v}) draws as ${want} (look ${got.look}, theme ${got.theme})`);
      await page.screenshot({ path: path.join(OUT, `looks-${v}.png`) });
    }
    check(errors.length === 0, `no page errors (${errors.slice(0, 2).join(' | ')})`);
  }

  if (MODE === 'gear') {
    // two browsers in the temple: Gauntlet changes gear, Gauntletb sees it re-dressed (equip.js,
    // the server's 'look' relay); each hero wears its own look
    const page2 = await (await browser.newContext({ viewport: { width: 960, height: 540 } })).newPage();
    page2.on('pageerror', e => errors.push('B: ' + String(e).slice(0, 300)));
    await page2.goto(`http://${CFG.mud.host}:${CFG.mud.mapPort}/play?q=low`, { waitUntil: 'load' });
    await waitFor(page2, () => document.getElementById('loading').classList.contains('done'));
    await page2.fill('#login-name', 'Gauntletb');
    await page2.fill('#login-pass', 'gauntlet1');
    await page2.click('#login-btn');
    check(await waitFor(page2, () => !!(window.MH3D && MH3D.hero), null, 120), 'second player logged in');
    for (const pg of [page, page2]) await pg.evaluate(() => { MH.sendCommand('group leave', false); MH.sendCommand('goto 3001', false); });
    const seen = await waitFor(page2, () => { const e = MH3D.ents.list.get('pGauntlet'); return !!(e && e.actor && e.actor.gear); }, null, 60);
    check(seen, 'Gauntletb draws Gauntlet dressed');
    const mine = await page.evaluate(() => ({ hero: MH3D.hero.gear && MH3D.hero.gear.sig, look: MH.state.player.look && MH.state.player.look.sig,
      pieces: MH3D.hero.gear ? MH3D.hero.gear.plan.props.map(p => p.name) : [] }));
    check(mine.hero && mine.hero === mine.look, `Gauntlet wears its own look (${mine.hero}: ${mine.pieces.join(', ')})`);
    // renown shows: a cloak and its emblem from level 20, motes round the hero from level 45 (adorn.js)
    await sleep(1500);
    const fame = await page.evaluate(() => { const g = MH3D.hero.gear; return { rn: MH.state.player.look.rn || 0, addons: g.plan.addons.map(a => a.kind),
      adorned: MH3D.adorn.on.has(MH3D.hero), motes: !!g.plan.adorn.motes, glow: g.glow.value }; });
    check(fame.rn < 2 || fame.addons.includes('emblem'), `renown ${fame.rn}: ${fame.addons.join(', ') || 'no add-ons'}`);
    check(!fame.motes || fame.adorned, `adorned as its standing asks (motes ${fame.motes}, adorned ${fame.adorned}, glow ${fame.glow})`);
    const before = await page2.evaluate(() => MH3D.ents.list.get('pGauntlet').actor.gear.sig);
    await page2.screenshot({ path: path.join(OUT, 'gear-before.png') });
    // a two-handed greatblade instead of whatever was in hand
    await page.evaluate(() => { MH.sendCommand('remove all', false); MH.sendCommand('load obj 15023', false); MH.sendCommand('wield greatblade', false); });
    const redressed = await waitFor(page2, sig => { const e = MH3D.ents.list.get('pGauntlet'); return e && e.actor.gear.sig !== sig; }, before, 15);
    const theirs = await page2.evaluate(() => { const g = MH3D.ents.list.get('pGauntlet').actor.gear; return { sig: g.sig, pieces: g.plan.props.map(p => p.name) }; });
    check(redressed && theirs.pieces.some(n => /2H_Sword|sword_2handed/.test(n)), `Gauntletb sees the greatblade in Gauntlet's hands within seconds (${theirs.pieces.join(', ')})`);
    await page.evaluate(() => MH.refreshState && MH.refreshState());
    const own = await waitFor(page, () => MH3D.hero.gear.plan.props.some(p => /2H_Sword|sword_2handed/.test(p.name)), null, 15);
    check(own, 'and Gauntlet sees it in its own hands');
    await sleep(1500);
    await page2.screenshot({ path: path.join(OUT, 'gear-after-other.png') });
    await page.screenshot({ path: path.join(OUT, 'gear-after-own.png') });
    // put things back as they were
    await page.evaluate(() => { MH.sendCommand('remove all', false); MH.sendCommand('junk greatblade', false); MH.sendCommand('wear all', false); });
    await sleep(1500);
    // people their zone armed wear it: the guards by the temple (a knight, a cityguard)
    await page.evaluate(() => MH.sendCommand('goto 3004', false));
    await waitFor(page, () => [...MH3D.ents.list.values()].some(e => e.kind === 'mob' && e.actor && e.actor.gear), null, 20);
    const npcs = await page.evaluate(() => [...MH3D.ents.list.values()].filter(e => e.kind === 'mob' && e.actor && e.actor.gear)
      .map(e => `${e.data.name}: ${e.actor.gear.plan.props.filter(p => !/-(Head|HeadHooded|Body|Arm|Leg)/.test(p.name)).map(p => p.name).join('+')} (${e.actor.gear.cls}, ${e.actor.gear.plan.build.h})`));
    check(npcs.some(n => /1H_Sword/.test(n)), `armed people wear their gear: ${npcs.join('; ') || 'none dressed'}`);
    await sleep(1500);
    await page.screenshot({ path: path.join(OUT, 'gear-npcs.png') });
    await page.evaluate(() => MH.sendCommand('goto 3001', false));
    await sleep(800);
  }

  if (MODE === 'aim') {
    check(await goto(18620), 'in the crypt (18620)');
    await sleep(1500);
    const box = await page.evaluate(() => { const r = MH3D.engine.renderer.domElement.getBoundingClientRect(); return { x: r.left, y: r.top, w: r.width, h: r.height }; });
    await page.mouse.move(box.x + box.w * 0.5, box.y + box.h * 0.5);
    // Meteor Storm's key (the circle 7 m, the reach 16 m: spells.py AIM_RADIUS, AIM_RANGE)
    await page.evaluate(() => MH.bus.emit('hud.ability', { id: 'meteor_storm', name: 'Meteor Storm', spell: true, self: true, radius: 7, range: 16 }));
    await sleep(800);
    const a1 = await page.evaluate(() => MH3D.aim());
    check(a1 && a1.id === 'meteor_storm' && a1.radius === 7, `the key starts the aim (${JSON.stringify(a1)})`);
    await page.mouse.move(box.x + box.w * 0.72, box.y + box.h * 0.62, { steps: 8 });
    await sleep(1500);
    const a2 = await page.evaluate(() => MH3D.aim());
    check(a2 && a1 && Math.hypot(a2.at.x - a1.at.x, a2.at.z - a1.at.z) > 0.5, 'the circle follows the mouse');
    await page.screenshot({ path: path.join(OUT, 'aim-circle.png') });
    await page.evaluate(() => { window.__sent.length = 0; });
    await page.mouse.click(box.x + box.w * 0.72, box.y + box.h * 0.62);
    await sleep(800);
    const sent = await page.evaluate(() => window.__sent.slice());
    check(sent.some(c => /^cast 'meteor storm' @\d+(\.\d)?,\d+(\.\d)?$/.test(c)) && !(await page.evaluate(() => MH3D.aim())),
      `a click casts it there and the aim ends (${sent.join(' | ')})`);
    await page.evaluate(() => MH.bus.emit('hud.ability', { id: 'meteor_storm', name: 'Meteor Storm', spell: true, self: true, radius: 7, range: 16 }));
    await sleep(500);
    await page.keyboard.press('Escape');
    await sleep(500);
    check(!(await page.evaluate(() => MH3D.aim())), 'Escape lets the aim go');
    // an aimed spell's event: the blast lands on the point (another player's view of it)
    const landed = await page.evaluate(async () => {
      const room = MH3D.heroRoom(), at = [6, 7];
      const d = MH3D.combat.director, seen = [];
      const land = d.land.bind(d);
      d.land = (r, who, ...rest) => { seen.push([who.root.position.x - room.ox, who.root.position.z - room.oz]); return land(r, who, ...rest); };
      MH3D.combat.handle([{ k: 'spell', src: { p: MH.state.playerName }, spell: 'meteor_storm', school: 'fire', shape: 'blast:7', at }], room.vnum);
      for (let i = 0; i < 40 && !seen.length; i++) await new Promise(r => setTimeout(r, 100));
      d.land = land;
      return seen;
    });
    check(landed.length && Math.hypot(landed[0][0] - 6, landed[0][1] - 7) < 0.1, `the aimed blast lands on its point (${JSON.stringify(landed)})`);
    await sleep(600);
    await page.screenshot({ path: path.join(OUT, 'aim-landed.png') });
  }

  check(errors.length === 0, `no page errors${errors.length ? ': ' + errors.join(' / ') : ''}`);
  await browser.close();
  const bad = results.filter(r => !r[0]).length;
  console.log(bad ? `${bad} FAILED` : 'ALL OK');
  process.exit(bad ? 1 : 0);
})();
