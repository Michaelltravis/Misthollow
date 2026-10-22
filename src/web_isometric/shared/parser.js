// Misthollow web client (/play): MUD text -> typed game events.
// Regex tables first written for the retired 2D clients; the single source of truth for
// which lines of telnet prose drive which animations and UI updates.
(() => {
  const MH = window.MH = window.MH || {};

  const HIT_TARGET = /^You (?:hit|slash|pierce|smite|blast|attack|pound|crush|whip|claw|sting|bite|kick|bash|cleave|backstab) (?:at )?([A-Za-z' -]+?)(?:\.|!| for| with| very| extremely| hard|$)/i;
  // full format: "Your <damage word> <verb>s <target>! [23 damage]" - damage
  // words can be multi-word ("barely scratch"), so anchor on the verb list
  const VERBS = 'hits|stings|whips|slashes|bites|bludgeons|crushes|pounds|claws|mauls|thrashes|pierces|blasts|punches|stabs|slices|cleaves|smashes';
  const HIT_DMG_FULL = new RegExp(`^Your .+? (?:${VERBS}) (.+?)! \\[(\\d+) damage\\]`, 'i');
  const HIT_DMG_COMPACT = /^You \w+ (.+?)\. \[(\d+)\]/i;
  // spell damage: "Your spell does 21 damage to quasit!" (dmg, then target)
  const SPELL_DMG_OUT = /^Your .*?\bdoes (\d+) damage to (.+?)!/i;
  const SPELL_DMG_IN = /\bdoes (\d+) damage to you!/i;
  // incoming: "a janitor's scratch hits you! [3 damage]"  compact: "a janitor hits you. [3]"
  const TAKEN_DMG_FULL = new RegExp(`^(.+?)'s .+? (?:${VERBS}) you! \\[(\\d+) damage\\]`, 'i');
  const TAKEN_DMG_COMPACT = /^(.+?) \w+s? you\. \[(\d+)\]/i;
  const EXP_GAIN = /You receive (\d+) experience/i;
  const MISS_TARGET = /^You miss ([A-Za-z' -]+?)(?:\.|!|$)/i;
  const TAKEN = /(?:hits?|slashes|pierces|smites|blasts|attacks|pounds|crushes|whips|claws|stings|bites|kicks|bashes|cleaves|backstabs) you\b/i;
  const MISSED_ME = /(?:misses) you\b/i;
  const MOB_DEATH = /^(.+?) is dead!|^You receive .* experience/i;
  // what the game says to you starts the line; the same words inside someone's speech or emote
  // ("Bob says, 'you are dead'") must not kill or stand anyone up
  const PLAYER_DEATH = /^(?:you are dead|you have been slain)/i;
  const LEVEL_UP = /^(?:you gain a level|you have gained a level|you are now level)/i;
  const MOVE_BLOCKED = /alas, you cannot go that way|the .* (?:is|seems to be) closed|seems to be locked|it'?s locked|you are too exhausted|no exit in that direction|you can'?t go that way|^only .+ may enter\.?$/i;
  const POSTURE_BLOCK = /^(?:you need to stand up first|you can'?t do that while (?:resting|sitting|sleeping)|you are asleep)/i;
  const DOOR_OPENED = /^(?:You open|.* opens) (?:the )?(.+?)\.?$/i;
  const FLEE = /^You flee(?: (\w+))?|panic and (?:try to )?flee/i;
  const CHAT = /^(You say|You tell|You shout|You gossip|You chat|\w+ says?|\w+ tells you|\w+ tells the group|\w+ shouts?|\w+ gossips?|\[\w+\])/i;
  const COMBAT_LINE = /you hit|you slash|you pierce|you smite|you blast|you miss|is dead!|you are fighting|hits you|slashes you|attacks you|misses you|parry|dodge|block/i;
  const HEAL = /you feel (?:better|much better|healthier)|heals you|your wounds/i;
  const CAST_START = /^You (?:begin casting|start to cast|utter the words)/i;
  const NOT_HERE = /they aren'?t here|you do not see that here|kill who/i;
  const SLEEP_LINE = /^You go to sleep|^You wake|^You stand up|^You sit down|^You rest/i;
  const GOLD_LINE = /you (?:get|receive|find) (\d+) (?:gold )?coins?/i;
  // loot pickups: "You get <item> from <corpse>." or "You get <item>." (gold is
  // matched by GOLD_LINE first, so this only catches real items)
  const LOOT_LINE = /^You get (.+?)(?: from (.+?))?\.?$/i;
  // a shop trade (shops.py): "You sell <item> for 9 gold." / "You buy <item> for 40 gold."
  const TRADE_LINE = /^You (sell|buy) (.+?) for ([\d,]+) gold\.?$/i;
  // skill / spell proficiency growth, and warrior ability evolution
  const SKILL_IMPROVE = /^You feel more skilled at (.+?)!\s*\((\d+)%\s*->\s*(\d+)%\)/i;
  const SPELL_IMPROVE = /^Your knowledge of (.+?) deepens!\s*\((\d+)%\s*->\s*(\d+)%\)/i;
  const ABILITY_EVOLVED_HDR = /ABILITY EVOLVED/i;
  const EVOLVE_ARROW = /^\s*([A-Za-z][A-Za-z ]*?)\s*(?:→|->)\s*(.+?)\s*$/;
  // consumables & gear feedback (no UI cue today)
  const EAT_LINE = /^You eat (.+?)\.?$/i;
  const STILL_HUNGRY = /^You eat but are still hungry/i;
  const DRINK_FROM = /^You drink (?:(.+?) )?from (.+?)\.?$/i;
  const WEAR_LINE = /^You (?:wear|hold|grip|light) (.+?)\.?$/i;
  const WIELD_LINE = /^You (?:wield|off-hand|sling) (.+?)\.?$/i;
  const UNEQUIP_LINE = /^You (?:remove|stop using|unwield) (.+?)\.?$/i;
  const LIGHT_KW = /torch|lantern|lamp|candle|brazier|glow|light|lume|flame|ember|fire(?:fly|brand)|crystal|star|beacon/i;

  MH.parseLine = function parseLine(msg) {
    let line = typeof msg === 'string' ? msg : msg.line;
    const chunkLen = typeof msg === 'object' ? (msg.chunkLen || 99) : 99;
    // the MUD prompt has no trailing newline, so it glues to the next
    // message - strip it before matching
    line = line.replace(/^\s*\d+\/\d+hp.*?>\s*/i, '');
    if (!line.trim()) return;
    const bus = MH.bus;
    let m;
    // speech first: nothing a player says may drive the client
    if (CHAT.test(line)) { bus.emit('chat', { line }); return; }

    if (PLAYER_DEATH.test(line)) { MH.setCombat(false); bus.emit('player.death', { line }); return; }
    if ((m = line.match(EXP_GAIN))) { bus.emit('player.exp', { amount: Number(m[1]), line }); /* fall through to MOB_DEATH below */ }
    if ((m = line.match(SPELL_DMG_IN))) {   // check incoming before outgoing
      MH.setCombat(true);
      bus.emit('combat.taken', { dmg: Number(m[1]), line });
      return;
    }
    if ((m = line.match(SPELL_DMG_OUT))) {
      MH.setCombat(true);
      bus.emit('combat.hit', { target: m[2].trim(), dmg: Number(m[1]), line });
      return;
    }
    if ((m = line.match(HIT_DMG_FULL)) || (m = line.match(HIT_DMG_COMPACT))) {
      MH.setCombat(true);
      bus.emit('combat.hit', { target: m[1].trim(), dmg: Number(m[2]), line });
      return;
    }
    if ((m = line.match(TAKEN_DMG_FULL)) || (m = line.match(TAKEN_DMG_COMPACT))) {
      MH.setCombat(true);
      bus.emit('combat.taken', { from: m[1].trim(), dmg: Number(m[2]), line });
      return;
    }
    if ((m = line.match(MOB_DEATH))) {
      bus.emit('mob.death', { name: (m[1] || '').trim(), line });
      MH.setCombat(false);
      MH.refreshState();
      return;
    }
    if (/^(Quest accepted:|Objective complete!|Quest Completed:|.*QUEST COMPLETE:)/.test(line)) { bus.emit('quest.update', { line }); }   // falls through: the line still reaches the feed
    if (LEVEL_UP.test(line)) { bus.emit('level.up', { line }); MH.refreshState(); return; }
    if (MOVE_BLOCKED.test(line)) { bus.emit('move.blocked', { line }); return; }
    if (POSTURE_BLOCK.test(line)) {
      // movement is the most common cause: stand and retry transparently
      bus.emit('move.blocked', { line, posture: true });
      MH.sendCommand('stand', false);
      return;
    }
    if ((m = line.match(HIT_TARGET))) { MH.setCombat(true); bus.emit('combat.hit', { target: m[1].trim(), line }); return; }
    if ((m = line.match(MISS_TARGET))) { MH.setCombat(true); bus.emit('combat.miss', { target: m[1].trim(), line }); return; }
    // defensive skills: yours and theirs, each with its own event
    if ((m = line.match(/^You parry (.+?)'s attack/i))) { MH.setCombat(true); bus.emit('defense.parry', { from: m[1], line }); return; }
    if ((m = line.match(/^You dodge (?:(.+?)'s attack|the attack)/i))) { MH.setCombat(true); bus.emit('defense.dodge', { from: m[1] || '', line }); return; }
    if (/^You block the attack/i.test(line)) { MH.setCombat(true); bus.emit('defense.block', { line }); return; }
    if ((m = line.match(/^(.+?) parries your attack/i))) { MH.setCombat(true); bus.emit('attack.parried', { target: m[1], line }); return; }
    if ((m = line.match(/^(.+?) dodges (?:your attack|like a ghost|from the shadows)/i))) { MH.setCombat(true); bus.emit('attack.dodged', { target: m[1], line }); return; }
    if ((m = line.match(/^(.+?) blocks (?:your attack|the attack with)/i))) { MH.setCombat(true); bus.emit('attack.blocked', { target: m[1], line }); return; }
    // rhythm combat: perfect strikes, stagger, guard, evade
    if (/your next strike will land PERFECTLY/i.test(line)) { MH.setCombat(true); bus.emit('reaction.swing.ready', { line }); return; }
    if (/^Your timing is off/i.test(line)) { MH.setCombat(true); bus.emit('reaction.swing.miss', { line }); return; }
    if (/PERFECT STRIKE!/.test(line)) { MH.setCombat(true); bus.emit('reaction.swing.perfect', { line }); return; }
    if ((m = line.match(/(?:💥 )?(.+?) reels — STAGGERED/))) { MH.setCombat(true); bus.emit('mob.staggered', { name: m[1].trim(), line }); return; }
    if ((m = line.match(/heavy blow SHATTERS (.+?)'s guard/i))) { MH.setCombat(true); bus.emit('mob.guardbreak', { name: m[1].trim(), line }); return; }
    if ((m = line.match(/(?:🛡 )?(.+?) (?:locks into a defensive guard|reads your rhythm and snaps into a guard)/i))) { MH.setCombat(true); bus.emit('mob.guardup', { name: m[1].trim(), line }); return; }
    if (/^You dart clear of the danger zone/i.test(line)) { MH.setCombat(true); bus.emit('reaction.evade', { line }); return; }
    // timed door work: begin lines carry their duration "(~Ns"; interruption
    // and completion lines end the progress bar
    if ((m = line.match(/\(~(\d+)s/)) && /barricad|sigils|picks whispering|tumblers shut/i.test(line)) {
      const label = /barricad/i.test(line) ? 'Barricading' : /sigil/i.test(line) ? 'Sealing' : 'Lockpicking';
      bus.emit('env.channel', { secs: Number(m[1]), label, line });
      return;
    }
    if (/is interrupted — the pile|rite is broken|picks slip|abandon the work|wedge the last piece|last sigil flares|tumblers seat|tumblers refuse|successfully pick the lock|fail to pick the lock|beyond any pick/i.test(line)) {
      bus.emit('env.channel.end', { line });
      // fall through: these also read well in the feed
    }
    // environmental drama (traps, shoves, elemental terrain, door tactics):
    // surface these lines in the message feed so nobody misses the world
    // fighting back. (Stagger/guard lines matched above keep their own events.)
    if (/^(?:⚠|💦|🔥|❄|⚡|🐺|🗡|💥 CRACK)/.test(line) || /barricades the|seals it\.$|disarms a hidden trap|SLAMS the \w+ shut|fiddles with something low to the ground/i.test(line)) {
      bus.emit('env.event', { line }); return;
    }
    // declared-intent reactions (brace / sidestep / interrupt)
    if (/^You plant your feet and BRACE/i.test(line)) { MH.setCombat(true); bus.emit('reaction.brace', { line }); return; }
    if (/^You brace against the impact/i.test(line)) { MH.setCombat(true); bus.emit('reaction.brace.success', { line }); return; }
    if ((m = line.match(/^(.+?) sidesteps at the last instant/i))) { MH.setCombat(true); bus.emit('reaction.sidestep.success', { who: m[1], line }); return; }
    if ((m = line.match(/^You slam into (.+?) and BREAK its (.+?)!/i))) { MH.setCombat(true); bus.emit('reaction.interrupt.success', { target: m[1], label: m[2], line }); return; }
    if (MISSED_ME.test(line)) { MH.setCombat(true); bus.emit('combat.dodged', { line }); return; }
    if (TAKEN.test(line)) { MH.setCombat(true); bus.emit('combat.taken', { line }); return; }
    if (NOT_HERE.test(line)) { bus.emit('combat.notarget', { line }); return; }
    if ((m = line.match(/^You flee (\w+)!/i))) {
      MH.setCombat(false);
      bus.emit('combat.flee', { dir: m[1].toLowerCase(), line });
      return;
    }
    if (FLEE.test(line)) { MH.setCombat(false); bus.emit('combat.flee', { line }); return; }
    if (CAST_START.test(line)) { bus.emit('combat.cast', { line }); return; }
    if (HEAL.test(line)) { bus.emit('player.heal', { line }); return; }
    if ((m = line.match(GOLD_LINE))) { bus.emit('player.gold', { amount: Number(m[1]), line }); return; }
    if ((m = line.match(LOOT_LINE))) { bus.emit('item.loot', { item: m[1].trim(), from: (m[2] || '').trim(), line }); MH.refreshState(); return; }
    // the pack and purse change with a trade, and the map socket only pushes on a move
    if ((m = line.match(TRADE_LINE))) { bus.emit('item.trade', { kind: m[1].toLowerCase(), item: m[2].trim(), price: Number(m[3].replace(/,/g, '')), line }); MH.refreshState(); return; }
    if ((m = line.match(SKILL_IMPROVE))) { bus.emit('skill.improve', { kind: 'skill', skill: m[1].trim(), from: +m[2], to: +m[3], line }); return; }
    if ((m = line.match(SPELL_IMPROVE))) { bus.emit('skill.improve', { kind: 'spell', skill: m[1].trim(), from: +m[2], to: +m[3], line }); return; }
    if (ABILITY_EVOLVED_HDR.test(line)) { MH._pendingEvolve = true; return; }
    if (MH._pendingEvolve && (m = line.match(EVOLVE_ARROW))) { MH._pendingEvolve = false; bus.emit('skill.evolve', { ability: m[1].trim(), evolution: m[2].trim(), line }); MH.refreshState(); return; }
    if (STILL_HUNGRY.test(line)) { bus.emit('item.consume', { kind: 'eat', sated: false, line }); return; }
    if ((m = line.match(EAT_LINE))) { bus.emit('item.consume', { kind: 'eat', item: m[1].trim(), line }); MH.refreshState(); return; }
    if ((m = line.match(DRINK_FROM))) { bus.emit('item.consume', { kind: 'drink', liquid: (m[1] || '').trim(), item: m[2].trim(), line }); MH.refreshState(); return; }
    if ((m = line.match(WIELD_LINE))) { bus.emit('item.equip', { slot: 'wield', item: m[1].trim(), line }); MH.refreshState(); return; }
    if ((m = line.match(WEAR_LINE))) {
      const item = m[1].trim();
      bus.emit('item.equip', { slot: LIGHT_KW.test(item) ? 'light' : 'wear', item, line });
      MH.refreshState();
      return;
    }
    if ((m = line.match(UNEQUIP_LINE))) { bus.emit('item.unequip', { item: m[1].trim(), line }); MH.refreshState(); return; }
    if ((m = line.match(DOOR_OPENED))) { bus.emit('door.opened', { name: m[1], line }); MH.refreshState(); return; }
    if (SLEEP_LINE.test(line)) { bus.emit('player.posture', { line }); MH.refreshState(); return; }
    if (CHAT.test(line)) { bus.emit('chat', { line }); return; }
    if (COMBAT_LINE.test(line)) { bus.emit('combat.misc', { line }); return; }
    // nothing matched: short standalone chunks are ambient narrative
    if (MH.state && MH.state.isLoggedIn && chunkLen <= 2) bus.emit('ambient.candidate', { line });
  };

  // wire the bus
  MH.bus.on('mud.line', MH.parseLine);
})();
