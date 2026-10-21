// /play's everyday windows: the shop, talking to someone, who is about, help, and the keys that
// answer a marked blow.   node --test tests/web/*.test.mjs
import { test } from 'node:test';
import assert from 'node:assert/strict';
import { shopRows, keywordFor, shopTip } from '../../src/web_isometric/world3d/hud/shop.js';
import { readTalk, talkQuests } from '../../src/web_isometric/world3d/hud/talk.js';
import { onlineRows, hereRows } from '../../src/web_isometric/world3d/hud/who.js';
import { rankTopics, CONTROLS } from '../../src/web_isometric/world3d/hud/help.js';
import { reactionKeys, threatens, ReactionPrompt } from '../../src/web_isometric/world3d/reactions.js';

test('the shop buys by the number in its list and sells by the word the MUD knows', () => {
  const data = { found: true, keeper: 'the armourer', gold: 100,
    buy: [{ name: 'iron helm', price: 40 }, { name: 'steel breastplate', price: 400 }],
    sell: [{ name: 'rusty sword', price: 3, will_buy: true }, { name: 'short sword', price: 9, will_buy: true },
      { name: 'bread loaf', price: 1, will_buy: false }] };
  const buy = shopRows(data, 'buy');
  assert.deepEqual(buy.map(r => [r.cmd, r.ok]), [['buy 1', true], ['buy 2', false]]);
  assert.equal(buy[1].why, 'Not enough gold');
  const sell = shopRows(data, 'sell');
  assert.deepEqual(sell.map(r => [r.cmd, r.ok]), [['sell rusty', true], ['sell short', true], ['sell bread', false]]);
  assert.match(sell[2].why, /doesn't deal in that/);
  assert.deepEqual(shopRows({ found: false }, 'buy'), []);
  const two = [{ name: 'long sword' }, { name: 'long bow' }];
  assert.equal(keywordFor(two[1], two), '2.long');
});

test("hovering a shop row shows the item's stats, and this shop's price, not its worth", async () => {
  globalThis.window = globalThis.window || globalThis;
  if (typeof globalThis.addEventListener !== 'function') globalThis.addEventListener = () => {};
  globalThis.localStorage = globalThis.localStorage || { getItem: () => null, setItem: () => {} };
  globalThis.document = globalThis.document || { querySelector: () => null, addEventListener: () => {}, createElement: () => ({ getContext: () => null }) };
  const sword = { name: 'long sword', short: 'a long sword', type: 'weapon', slot: 'wield', damage_dice: '2d6',
    weapon_type: 'slash', affects: [{ type: 'hitroll', value: 2 }], weight: 6, cost: 120, level: 12 };
  const data = { found: true, keeper: 'the weaponsmith', gold: 50, buy: [{ ...sword, price: 180 }],
    sell: [{ ...sword, price: 60, will_buy: true }, { name: 'bread', short: 'a loaf of bread', type: 'food', price: 0, will_buy: false }] };
  const { tooltip } = await import('../../src/web_isometric/world3d/hud/inventory.js');
  const buy = shopTip(shopRows(data, 'buy')[0], 'buy', null, tooltip);
  assert.match(buy, /a long sword/);
  assert.match(buy, /Damage 2d6 \(slash\)/);
  assert.match(buy, /\+2 hitroll/);
  assert.match(buy, /Costs 180 gold · Not enough gold/);
  assert.doesNotMatch(buy, /120 gold/);
  const [sold, bread] = shopRows(data, 'sell');
  assert.match(shopTip(sold, 'sell', null, tooltip), /They pay 60 gold/);
  assert.match(shopTip(bread, 'sell', null, tooltip), /doesn't deal in that/);
  const player = { char_class: 'warrior', equipment: { wield: { name: 'dagger', short: 'a dagger', type: 'weapon', slot: 'wield', damage_dice: '1d4' } } };
  assert.match(shopTip(shopRows(data, 'buy')[0], 'buy', player, tooltip), /Against a dagger/);
});

test('a reply to talk: their words, the responses as buttons, the offers; the telnet hints go', () => {
  const r = readTalk([
    'Night falls across the land.',
    '> talk keeper',
    'You greet the morose grave keeper.',
    'The grave keeper sighs. "The dead do not rest here."',
    'Responses:',
    '  1. Why not?',
    '  2. Goodbye.',
    "Use 'talk <npc> <number>' to respond.",
    'The grave keeper has quests for you:',
    '  Bones of the Crypt — Gather five bones',
    '    (quest accept crypt_bones)',
    "Use 'quest accept <quest_id>' to accept a quest.",
    '531/531hp 199/199mp 306/306mv>',
  ].join('\n'));
  assert.deepEqual(r.choices, [{ n: 1, text: 'Why not?' }, { n: 2, text: 'Goodbye.' }]);
  assert.deepEqual(r.offers, ['crypt_bones']);
  assert.ok(r.says[0].startsWith('The grave keeper sighs'));
  assert.ok(!r.says.some(l => /^Use '|You greet/.test(l)));
  // only their words: not the world going on before the greeting, the echo, the prompt, or the offer's own line
  assert.deepEqual(r.says, ['The grave keeper sighs. "The dead do not rest here."']);
  const q = talkQuests({ givers: [{ name: 'the morose grave keeper', offers: [{ id: 'crypt_bones', name: 'Bones' }] }],
    active: [{ id: 'rats', name: 'Rats', complete: true }, { id: 'wolves', complete: false }, { id: 'marquee', complete: true }] },
  'The morose grave keeper');
  assert.deepEqual(q.offers.map(o => o.id), ['crypt_bones']);
  assert.deepEqual(q.done.map(d => d.id), ['rats']);
});

test('who: you first, then your group, then by level; who is here comes from the map payload', () => {
  const rows = onlineRows([{ name: 'Zed', level: 9 }, { name: 'Ann', level: 30 }, { name: 'Me', level: 5 }, { name: 'Bo', level: 2, group: true }], 'me');
  assert.deepEqual(rows.map(r => r.name), ['Me', 'Bo', 'Ann', 'Zed']);
  const payload = { nearby: [{ vnum: 3001, players: [{ name: 'Me' }, { name: 'Ann', level: 30, char_class: 'mage' }],
    mobs: [{ id: 7, name: 'the baker', shopkeeper: true }, { id: 8, name: 'a rat', flags: ['aggressive'] }] }] };
  const here = hereRows(payload, 3001, 'Me');
  assert.deepEqual(here.map(r => [r.name, r.what]), [['Ann', 'Mage'], ['The baker', 'shopkeeper'], ['A rat', 'hostile']]);
  assert.deepEqual(hereRows(payload, 9999, 'Me'), []);
});

test('help: the controls, and topics ranked by how well they match', () => {
  assert.ok(CONTROLS.some(([what, keys]) => /marked blow/.test(what) && /Q brace/.test(keys)));
  const topics = [{ name: 'bash', summary: 'knock a foe down' }, { name: 'backstab' }, { name: 'abash' }, { name: 'kick', summary: 'like bash, but a kick' }];
  assert.deepEqual(rankTopics(topics, 'bash').map(t => t.name), ['bash', 'abash', 'kick']);
  assert.deepEqual(rankTopics(topics, '  '), []);
});

test('a marked blow: Q braces, E sidesteps, X interrupts a cast; one answer each, until it lands', () => {
  assert.deepEqual(reactionKeys({ kind: 'heavy' }), ['q', 'e']);
  assert.deepEqual(reactionKeys({ kind: 'aoe', interruptible: true }), ['q', 'e', 'x']);
  assert.deepEqual(reactionKeys({ kind: 'cast', interruptible: true }), ['x', 'q']);
  assert.deepEqual(reactionKeys({ kind: 'cast' }), ['q']);           // the server sends interruptible only when true
  assert.deepEqual(reactionKeys({ kind: 'debuff', interruptible: true }), ['q', 'e', 'x']);
  const me = s => s && s.p === 'Me';
  assert.ok(threatens({ k: 'windup', dst: { p: 'Me' } }, me));
  assert.ok(!threatens({ k: 'windup', dst: { p: 'Ann' } }, me));
  assert.ok(threatens({ k: 'windup', dst: { p: 'Ann' } }, me, () => true));
  assert.ok(!threatens({ k: 'attack', dst: { p: 'Me' } }, me));
  const p = new ReactionPrompt();
  p.windup({ k: 'windup', src: { m: 4 }, kind: 'heavy', ms: 2000 }, 0);
  assert.equal(p.press('x', 100), null);                // not an answer to a heavy blow
  assert.equal(p.press('Q', 100), 'brace');
  assert.equal(p.press('e', 200), null);                // already answered
  p.windup({ k: 'windup', src: { m: 4 }, kind: 'heavy', ms: 2000 }, 0);
  assert.equal(p.press('e', 5000), null);               // too late: it landed
  assert.equal(p.active(5000), null);
  p.windup({ k: 'windup', src: { m: 5 }, kind: 'cast', ms: 2000 }, 0);
  p.end(5);
  assert.equal(p.active(10), null);
});

test('what lies on the ground: corpses and items, each with the word `get` finds it by', async () => {
  const { groundItems, groundKeyword, isCorpse } = await import('../../src/web_isometric/world3d/lootlogic.js');
  assert.ok(isCorpse({ name: 'corpse of a fido' }) && isCorpse({ short: 'the corpse of a rat' }) && !isCorpse({ name: 'corpse-flower seed' }));
  const items = [{ name: 'corpse of a rat' }, { name: 'iron dagger' }, { name: 'corpse of a fido' }, { name: 'iron shield' }];
  assert.deepEqual(items.map(it => groundKeyword(it, items)), ['corpse', 'iron', '2.corpse', '2.iron']);
  const g = groundItems({ nearby: [{ vnum: 3001, items }, { vnum: 3002, items: [{ name: 'iron dagger' }, { name: 'iron dagger' }] }] });
  assert.equal(g.length, 6);
  assert.deepEqual(g.filter(x => x.corpse).map(x => x.kw), ['corpse', '2.corpse']);
  // two of the same in a room keep separate places
  assert.notEqual(g[4].key, g[5].key);
  assert.deepEqual(groundItems({}), []);
  // fixtures (a fountain, a board: the server marks them) are part of the room, not loot
  assert.deepEqual(groundItems({ nearby: [{ vnum: 1, items: [{ name: 'fountain', fixed: true }, { name: 'iron dagger' }] }] }).map(x => x.kw), ['iron']);
});

test("a corpse's loot window: its gold, then each thing, each taken by the MUD's own `get`", async () => {
  const { lootRows } = await import('../../src/web_isometric/world3d/lootlogic.js');
  const corpse = { name: 'corpse of an orc', gold: 12, contents: [{ name: 'iron sword' }, { name: 'iron helm' }, { name: 'brass key' }] };
  const rows = lootRows(corpse, '2.corpse');
  assert.deepEqual(rows.map(r => r.cmd), ['get gold from 2.corpse', 'get iron from 2.corpse', 'get 2.iron from 2.corpse', 'get brass from 2.corpse']);
  assert.equal(rows[0].gold, 12);
  assert.deepEqual(lootRows({ name: 'corpse of a rat', gold: 0, contents: [] }, 'corpse'), []);
  assert.deepEqual(lootRows(null, 'corpse'), []);
});
