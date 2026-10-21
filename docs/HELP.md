# Misthollow Help Reference

This file is generated from in-game help topics to preserve documentation.

## Class

### Assassin

The Assassin class.

SKILL TREE / PROGRESSION:
- Skills/spells unlock in the order listed for your class.
- Unlock tiers at levels: 2, 3, 5, 7, 10, 15, 20, 25, 30.

### Bard

The Bard class.

SKILL TREE / PROGRESSION:
- Skills/spells unlock in the order listed for your class.
- Unlock tiers at levels: 2, 3, 5, 7, 10, 15, 20, 25, 30.

### Cleric

The Cleric class.

SKILL TREE / PROGRESSION:
- Skills/spells unlock in the order listed for your class.
- Unlock tiers at levels: 2, 3, 5, 7, 10, 15, 20, 25, 30.

### Mage

The Mage class.

SKILL TREE / PROGRESSION:
- Skills/spells unlock in the order listed for your class.
- Unlock tiers at levels: 2, 3, 5, 7, 10, 15, 20, 25, 30.

### Necromancer

Necromancers wield death magic, draining life and commanding the dead. They
excel at sustained pressure, debuffs, and undead minions, but are fragile
in direct melee.

PLAYSTYLE:
- Open with debuffs (blindness, poison) and drain effects
- Use undead minions for frontline pressure
- Sustain with life drain and mana management

RESOURCE LOOP:
- Mana fuels most damage; conserve with efficient drains
- Soul fragments extend undead duration (if available)

PETS / MINIONS:
- Animate Dead creates temporary undead
- Undead minions persist for their duration and assist in combat

DEFENSES:
- Armor/Shield spells improve survivability
- Keep distance; rely on control and minions

SKILL TREE / PROGRESSION:
- Skills/spells unlock in the order listed for your class.
- Unlock tiers at levels: 2, 3, 5, 7, 10, 15, 20, 25, 30.

SPELL ORDER:
- 1. Chill Touch
- 2. Animate Dead
- 3. Vampiric Touch
- 4. Enervation
- 5. Death Grip
- 6. Finger Of Death
- 7. Energy Drain
- 8. Poison
- 9. Weaken
- 10. Blindness
- 11. Fear
- 12. Armor
- 13. Shield
- 14. Protection From Good

TRAINING:
- Use PRACTICE at your class trainer.

### Paladin

The Paladin class.

SKILL TREE / PROGRESSION:
- Skills/spells unlock in the order listed for your class.
- Unlock tiers at levels: 2, 3, 5, 7, 10, 15, 20, 25, 30.

### Ranger

The Ranger class.

SKILL TREE / PROGRESSION:
- Skills/spells unlock in the order listed for your class.
- Unlock tiers at levels: 2, 3, 5, 7, 10, 15, 20, 25, 30.

### Thief

The Thief class.

SKILL TREE / PROGRESSION:
- Skills/spells unlock in the order listed for your class.
- Unlock tiers at levels: 2, 3, 5, 7, 10, 15, 20, 25, 30.

### Warrior

The Warrior class.

SKILL TREE / PROGRESSION:
- Skills/spells unlock in the order listed for your class.
- Unlock tiers at levels: 2, 3, 5, 7, 10, 15, 20, 25, 30.

## Command

### Account
**Syntax:** `account [chars|info|claim|password|email|forgot|recover]`

View and manage your account: every character is on one, and its password is the only way in. Log in with the account (or any of its characters) to make, play or delete characters. `account claim <name> <password>` brings in a character from another account of yours (the password of the account it is on now).

### Achievements
**Syntax:** `achievements [all|progress]`

List earned achievements and progress. Usage: achievements [all|progress]

### Adrenaline Rush
**Syntax:** `adrenaline_rush`

Burst of speed.

### Advance
**Syntax:** `advance <player> <level>`

Set a player's level (immortal only).

Usage: advance <player> <level>

### Ai
**Syntax:** `ai on|off`

Toggle AI chat on/off. Usage: ai on|off

### Aimed Shot
**Syntax:** `aimed_shot`

Powerful ranged shot.

### Aistatus
**Syntax:** `aistatus`

Check AI service status (admin command).

### Alias
**Syntax:** `alias              - List all your aliases`

Create, view, or remove personal command aliases.

Usage:
    alias              - List all your aliases
    alias <word>       - Show what <word> is aliased to
    alias <word> <cmd> - Create alias <word> for <cmd>
    unalias <word>     - Remove an alias

### Animate
**Syntax:** `animate <corpse>`

Animate a corpse as undead. Usage: animate <corpse>

### Answer
**Syntax:** `answer`

Answer a riddle puzzle in the room.

### Apologize
**Syntax:** `apologize`

Apologize.

### Ascii
**Syntax:** `ascii [on|off]`

Toggle ASCII-only UI (no box-drawing characters). Usage: ascii [on|off]

### Ask
**Syntax:** `ask`

Ask an NPC a question using LLM-powered conversation.

### Assist
**Syntax:** `assist <player>`

Help someone in combat. Usage: assist <player>

### Protect
**Syntax:** `protect <ally>|protect off`

Protect an ally by intercepting attacks. Warriors and paladins only.

MECHANICS:
- Intercept chance scales with rescue/shield skill and STR/CON
- Defensive stance improves intercepts
- Short intercept cooldown prevents chaining

### At
**Syntax:** `at <location> <command>`

Execute a command at another location (immortal only).

Usage: at <location> <command>

Examples:
    at 3001 look
    at 3001 mload 3000

### Attack
**Syntax:** `attack`

Alias for kill.

### Auction
**Syntax:** `auction <message>`

Auction channel for selling items. Usage: auction <message>

### Aura
**Syntax:** `aura`

Activate or view paladin auras.

### Autoattack
**Syntax:** `autoattack          - Toggle autoattack on/off`

Toggle automatic basic attacks.

Usage:
    autoattack          - Toggle autoattack on/off
    autoattack on       - Turn autoattack on
    autoattack off      - Turn autoattack off

### Autocombat
**Syntax:** `autocombat          - Toggle autocombat on/off`

Toggle automatic combat skills/spells.

Usage:
    autocombat          - Toggle autocombat on/off
    autocombat on       - Turn autocombat on
    autocombat off      - Turn autocombat off

### Autoexit
**Syntax:** `autoexit`

Toggle automatic exit display on room entry.

### Autogold
**Syntax:** `autogold          - Toggle autogold on/off`

Toggle automatic pickup of ground gold.

Usage:
    autogold          - Toggle autogold on/off
    autogold on       - Turn autogold on
    autogold off      - Turn autogold off

### Autoloot
**Syntax:** `autoloot          - Toggle autoloot on/off`

Toggle automatic looting of items from corpses.

Usage:
    autoloot          - Toggle autoloot on/off
    autoloot on       - Turn autoloot on
    autoloot off      - Turn autoloot off
    autoloot gold     - Toggle gold autoloot on/off
    autoloot gold on  - Turn gold autoloot on
    autoloot gold off - Turn gold autoloot off

### Autorecall
**Syntax:** `autorecall             - Show current autorecall settings`

Set automatic recall when HP drops below a threshold.

Usage:
    autorecall             - Show current autorecall settings
    autorecall <hp>        - Set HP threshold (number or percentage)
    autorecall 50          - Recall when HP drops below 50
    autorecall 25%         - Recall when HP drops below 25%
    autorecall off         - Disable autorecall

### Avatar Of War
**Syntax:** `avatar_of_war`

Massive offensive burst.

### Backup
**Syntax:** `backup [players|world|full]`

Create a backup of game data (immortal only).

Usage: backup [players|world|full]
       backup list
       backup restore <filename>

### Balance
**Syntax:** `balance`

Check your bank balance.

### Bestial Wrath
**Syntax:** `bestial_wrath`

Enrage your pet.

### Bind
**Syntax:** `bind`

Set your recall point to the current location.

### Black Arrow
**Syntax:** `black_arrow`

Poisoned arrow dealing damage over time.

### Blade Dance
**Syntax:** `blade_dance`

Spin striking nearby enemies.

### Bladestorm
**Syntax:** `bladestorm`

Spin and strike all enemies.

### Blush
**Syntax:** `blush`

Blush.

### Bow
**Syntax:** `bow`

Bow.

### Brief
**Syntax:** `brief          - Toggle brief mode on/off`

Toggle brief room descriptions.

Usage:
    brief          - Toggle brief mode on/off
    brief on       - Turn brief mode on
    brief off      - Turn brief mode off

### Bug
**Syntax:** `bug <description>`

Report a bug. Usage: bug <description>

### Buy
**Syntax:** `buy <item>`

Buy an item from a shop. Usage: buy <item>

### Cackle
**Syntax:** `cackle`

Cackle.

### Cast
**Syntax:** `cast`

Cast a spell.

### Changelog
**Syntax:** `changelog`

Alias for updates command.

### Chat
**Syntax:** `chat <npc> <message>`

Have a dynamic AI conversation with an NPC. Usage: chat <npc> <message>

### Chathistory
**Syntax:** `chathistory <npc>`

Show recent AI chat history with an NPC. Usage: chathistory <npc>

### Cheer
**Syntax:** `cheer`

Cheer.

### Clear
**Syntax:** `clear`

Clear the screen.

Usage: clear

### Cloak Of Shadows
**Syntax:** `cloak_of_shadows`

Remove harmful magic effects.

### Close
**Syntax:** `close <door/container>`

Close a door or container. Usage: close <door/container>

### Cold Blood
**Syntax:** `cold_blood`

Guarantee your next attack crits.

### Collections
**Syntax:** `collections`

View collection progress.

### Color
**Syntax:** `color [off|sparse|normal|complete]`

Set color level. Usage: color [off|sparse|normal|complete]

### Combat
**Syntax:** `combat settings`

Combat settings for auto-combat.

Usage:
    combat settings
    combat settings heal <percent>
    combat settings skills on|off
    combat settings spells on|off
    combat settings skillpriority <skill1,skill2,...>
    combat settings spellpriority <spell1,spell2,...>
    combat settings reset

### Combo
**Syntax:** `combo`

View current combo points.

### Comfort
**Syntax:** `comfort`

Comfort someone.

### Commands
**Syntax:** `commands`

List all available commands.

### Compact
**Syntax:** `compact          - Toggle compact mode on/off`

Toggle compact combat messages.

Usage:
    compact          - Toggle compact mode on/off
    compact on       - Turn compact mode on
    compact off      - Turn compact mode off

### Companion
**Syntax:** `companion`

Show your companion's stats. Usage: companion

### Companions
**Syntax:** `companions`

List your current companions. Usage: companions

### Compare
**Syntax:** `compare <item>`

Compare a shop item to your equipped item. Usage: compare <item>

### Consider
**Syntax:** `consider`

Consider how tough a mob is and learn about its capabilities.

### Cover
**Syntax:** `cover light`

Cover your light source. Usage: cover light

### Craft
**Syntax:** `craft`

Craft an item from a recipe.

### Cringe
**Syntax:** `cringe`

Cringe.

### Crippling Poison
**Syntax:** `crippling_poison`

Apply crippling poison to your weapon.

### Crusader Strike
**Syntax:** `crusader_strike`

Instant weapon strike.

### Cry
**Syntax:** `cry`

Cry.

### Daily
**Syntax:** `daily`

View your daily login bonus status.

Usage: daily

Log in each day to build your streak and earn better rewards!

### Dance
**Syntax:** `dance`

Dance.

### Dc
**Syntax:** `dc <player>`

Disconnect a player (immortal only).

Usage: dc <player>

### Deadly Poison
**Syntax:** `deadly_poison`

Apply deadly poison to your weapon.

### Death From Above
**Syntax:** `death_from_above`

Leap attack for massive damage.

### Deposit
**Syntax:** `deposit <amount>`

Deposit gold in the bank. Usage: deposit <amount>

### Diagnose
**Syntax:** `diagnose [target]`

Check detailed health status. Usage: diagnose [target]

### Dismiss
**Syntax:** `dismiss <pet name>`

Dismiss a pet or companion. Usage: dismiss <pet name>

### Dismount
**Syntax:** `dismount`

Dismount your current mount.

### Display
**Syntax:** `display`

Set display options. Alias for prompt.

### Divine Storm
**Syntax:** `divine_storm`

Holy whirlwind attack.

### Divinefavor
**Syntax:** `divinefavor`

View current divine favor.

### Donate
**Syntax:** `donate <item>`

Donate an item to help newbies. Usage: donate <item>

### Down
**Syntax:** `down`

No additional details available yet.

### Drink
**Syntax:** `drink`

Drink from a container or fountain.

### Drink Alt
**Syntax:** `drink [from] <source>`

Drink from a fountain or container. Usage: drink [from] <source>

### Drop
**Syntax:** `drop`

Drop an item or gold.

### Dungeon
**Syntax:** `dungeon list`

Procedural dungeon commands.

Usage:
    dungeon list
    dungeon enter <type> [difficulty] [permadeath]
    dungeon enter daily [difficulty] [permadeath]
    dungeon leave

### East
**Syntax:** `east`

No additional details available yet.

### Eat
**Syntax:** `eat`

Eat food.

### Echo
**Syntax:** `echo <message>`

Send a message to the current room (immortal only).

Usage: echo <message>

### Emote
**Syntax:** `emote`

Emote an action.

### Encore
**Syntax:** `encore`

Boost your current song's effects temporarily.

### Enter
**Syntax:** `enter [portal/building name]`

Enter a building or portal. Usage: enter [portal/building name]

### Equipment
**Syntax:** `equipment`

Show equipped items.

### Eviscerate
**Syntax:** `eviscerate`

Powerful finisher that consumes all combo points.

### Examine
**Syntax:** `examine <item>`

Examine an item in your inventory or equipment. Usage: examine <item>

### Execute
**Syntax:** `execute`

Devastating finisher that deals more damage at low target HP.

### Exits
**Syntax:** `exits`

Show available exits from the current room with descriptions.

### Explosive Trap
**Syntax:** `explosive_trap`

Set an explosive trap in the room.

### Faction
**Syntax:** `faction`

Show detailed reputation for a specific faction.

### Fill
**Syntax:** `fill <container> [fountain]`

Fill a container from a fountain. Usage: fill <container> [fountain]

### Find
**Syntax:** `find mob <name>    - Find all mobs matching name`

Find a mob or object anywhere in the world (immortal only).

Usage:
    find mob <name>    - Find all mobs matching name
    find obj <name>    - Find all objects matching name

### Flee
**Syntax:** `flee`

Panic flee from combat in a random direction.

MECHANICS:
- Chance scales with DEX and stance
- Costs move and has a short cooldown
- On success: random exit, small XP loss

### Escape
**Syntax:** `escape <direction>`

Attempt a controlled escape in a chosen direction.

MECHANICS:
- Chance scales with escape skill (or DEX)
- Costs move and has a short cooldown

### Disengage
**Syntax:** `disengage`

Break off combat if enemies aren't focused on you.

MECHANICS:
- Requires you not be the current focus
- Costs move and has a short cooldown

### Follow
**Syntax:** `follow <player> or follow self`

Follow another player. Usage: follow <player> or follow self

### Force
**Syntax:** `force <player> <command>`

Force a player to execute a command (immortal only).

Usage: force <player> <command>

### Freeze
**Syntax:** `freeze <player>`

Freeze a player so they can't do anything (immortal only).

Usage: freeze <player>

### Gather
**Syntax:** `gather`

Gather resources based on environment.

### Gecho
**Syntax:** `gecho <message>`

Send a message to all players (immortal only).

Usage: gecho <message>

### Get
**Syntax:** `get <item>              - Get item from room`

Pick up an item.

Usage:
    get <item>              - Get item from room
    get all                 - Get all items from room
    get <item> <container>  - Get item from container
    get all <container>     - Get all items from container
    get <item> from <container> - Alternative syntax
    get all from <container>    - Alternative syntax

### Giggle
**Syntax:** `giggle`

Giggle.

### Give
**Syntax:** `give`

Give an item to someone.

### Glare
**Syntax:** `glare`

Glare at someone.

### Gossip
**Syntax:** `gossip <message>`

Global chat channel. Usage: gossip <message>

### Goto
**Syntax:** `goto <vnum>     - Go to room vnum (e.g. goto 3001)`

Teleport to a room or zone (testing command).

Usage:
    goto <vnum>     - Go to room vnum (e.g. goto 3001)
    goto <zone>     - Go to zone entrance (e.g. goto 30)

### Grats
**Syntax:** `grats <message>`

Congratulations channel. Usage: grats <message>

### Greet
**Syntax:** `greet`

Greet someone.

### Grin
**Syntax:** `grin`

Grin.

### Group
**Syntax:** `group           - Show group status`

Manage your group. CircleMUD-style group commands.

Usage:
    group           - Show group status
    group all       - Group all players following you
    group <player>  - Add a player following you to your group
    group leave     - Leave your current group
    group disband   - Disband the group (leader only)
    group kick <n>  - Remove player from group (leader only)

### Grumble
**Syntax:** `grumble`

Grumble.

### Gtell
**Syntax:** `gtell <message>`

Send a message to your group. Usage: gtell <message>

### Help
**Syntax:** `help`

Show help information for commands, skills, and spells.

### Hint
**Syntax:** `hint`

Request a hint for the current room puzzle.

### Hire
**Syntax:** `hire <npc>`

Hire a companion from a tavern or guild. Usage: hire <npc>

### Holler
**Syntax:** `holler <message>`

Shout to everyone (costs 20 movement). Usage: holler <message>

### Holylight
**Syntax:** `holylight`

Toggle ability to see everything (dark rooms, invisible, etc) (immortal only).

Usage: holylight

### Holysmite
**Syntax:** `holysmite`

Spend divine favor for a powerful holy attack.

### House
**Syntax:** `house [buy|info]`

Manage housing. Usage: house [buy|info]

### Hug
**Syntax:** `hug`

Hug someone.

### Hunters Mark
**Syntax:** `hunters_mark`

Mark a target for increased damage from your attacks.

### Idea
**Syntax:** `idea <your suggestion>`

Suggest an idea. Usage: idea <your suggestion>

### Ignorepain
**Syntax:** `ignorepain`

Absorb incoming damage with pure willpower.

### Imbue
**Syntax:** `imbue [corpse]`

Imbue a corpse with soulstone power. Usage: imbue [corpse]

### Immlist
**Syntax:** `immlist`

List all immortals (admin accounts).

Usage: immlist

### Info
**Syntax:** `info`

Display game information for new players.

### Interrupt
**Syntax:** `interrupt`

Attempt to interrupt a boss cast with bash or kick.

### Inventory
**Syntax:** `inventory`

Show inventory.

### Invis
**Syntax:** `invis`

List all invisible players/mobs in room (immortal only).

Usage: invis

### Journal
**Syntax:** `journal              - Show journal overview and recent entries`

Review your discovery journal.

Usage:
    journal              - Show journal overview and recent entries
    journal stats        - Show discovery statistics
    journal lore         - Show lore entries
    journal secrets      - Show discovered secrets
    journal npcs         - Show NPCs you've met
    journal areas        - Show discovered areas
    journal read <num>   - Read a specific entry
    journal all          - Show all entries

### Judgment
**Syntax:** `judgment`

Ranged holy strike.

### Junk
**Syntax:** `junk <item>`

Destroy an item. Usage: junk <item>

### Kidneyshot
**Syntax:** `kidneyshot`

Stun finisher that uses 4+ combo points.

### Kill
**Syntax:** `kill`

Attack a target.

### Killing Spree
**Syntax:** `killing_spree`

Rapidly strike multiple enemies.

### Knock
**Syntax:** `knock <direction>`

Knock on a door. Usage: knock <direction>

### Label
**Syntax:** `label                    - Show all current labels`

Label a target for quick targeting in combat.

Usage:
    label                    - Show all current labels
    label <target> <name>    - Label a target (e.g., label warrior DEAD)
    label clear              - Clear all labels
    label clear <name>       - Clear specific label

Then use the label in commands: kill DEAD, cast fireball DEAD
Labels are case-insensitive and session-only (not saved).

### Laugh
**Syntax:** `laugh`

Laugh.

### Layhands
**Syntax:** `layhands`

Use lay on hands to heal yourself or an ally.

### Leaderboard
**Syntax:** `leaderboard [category]`

View the server leaderboards.

Usage: leaderboard [category]
Categories: level, kills, gold, deaths, achievements, quests

### Leave
**Syntax:** `leave`

Leave a building to go outside. Usage: leave

### Levels
**Syntax:** `levels`

Show experience required for each level.

### List
**Syntax:** `list`

List items for sale in a shop. Usage: list

### Load
**Syntax:** `load mob <vnum>       - Load a mob`

Load a mob or object (immortal only).

Usage:
    load mob <vnum>       - Load a mob
    load obj <vnum>       - Load an object to inventory
    load obj <vnum> room  - Load an object to room

### Lock
**Syntax:** `lock <door/container>`

Lock a door or container. Usage: lock <door/container>

### Look
**Syntax:** `look`

Look at the room or something.

### Loot
**Syntax:** `loot`

Loot items from a corpse. Supports numbered targeting (e.g., loot 2.corpse)

### Map
**Syntax:** `map        - Show local explored map`

Display ASCII map.

Usage:
    map        - Show local explored map
    map full   - Show entire explored area
    map zone   - Show explored rooms in current zone

### Mapurl
**Syntax:** `mapurl`

Show the web map URL for this player.

### Mark
**Syntax:** `mark`

Mark a target for death, increasing damage against them.

### Marked For Death
**Syntax:** `marked_for_death`

Mark a target for lethal focus.

### Marked Shot
**Syntax:** `marked_shot`

Fire a powerful shot at a marked target for bonus damage.

### Medit
**Syntax:** `medit`

Online mob editor (immortal only).

### Minimap
**Syntax:** `minimap`

Display a compact ASCII minimap centered on the player.

### Minions
**Syntax:** `minions`

List your summoned minions (undead, summons). Usage: minions

### Mlist
**Syntax:** `mlist           - List mobs in current zone`

List all mobs in a zone (immortal only).

Usage:
    mlist           - List mobs in current zone
    mlist <zone>    - List mobs in specified zone

### Mload
**Syntax:** `mload <vnum>`

Load a mob into the current room (immortal only).

Usage: mload <vnum>

### Mock
**Syntax:** `mock`

Taunt an enemy with vicious mockery, debuffing them.

### Mortal Strike
**Syntax:** `mortal_strike`

Heavy strike that wounds the target.

### Motd
**Syntax:** `motd`

Display the Message of the Day.

### Mount
**Syntax:** `mount [name]`

Mount a owned/tamed mount. Usage: mount [name]

### Mounts
**Syntax:** `mounts`

List your owned mounts.

### Move
**Syntax:** `move`

Move in a direction.

### Mute
**Syntax:** `mute <player>`

Mute a player so they can't talk (immortal only).

Usage: mute <player>

### Mutilate
**Syntax:** `mutilate`

Dual strike that builds combo points.

### Newgameplus
**Syntax:** `newgameplus`

Start a New Game+ cycle after completing the main story.

### News
**Syntax:** `news`

Alias for updates command.

### Nod
**Syntax:** `nod`

Nod.

### Nohassle
**Syntax:** `nohassle`

Toggle immunity to mob attacks (immortal only).

Usage: nohassle

### Norepeat
**Syntax:** `norepeat`

Toggle echoing of your own communication.

### North
**Syntax:** `north`

No additional details available yet.

### Noshout
**Syntax:** `noshout`

Toggle blocking of shouts and hollers.

### Notell
**Syntax:** `notell`

Toggle blocking of tells from other players.

### Notick
**Syntax:** `notick`

Alias for tick - toggle tick notifications.

### Oedit
**Syntax:** `oedit`

Online object editor (immortal only).

### Olist
**Syntax:** `olist           - List objects in current zone`

List all objects in a zone (immortal only).

Usage:
    olist           - List objects in current zone
    olist <zone>    - List objects in specified zone

### Oload
**Syntax:** `oload <vnum> [room]`

Load an object into the room or your inventory (immortal only).

Usage: oload <vnum> [room]

### Open
**Syntax:** `open <door/container>`

Open a door or container. Usage: open <door/container>

### Order
**Syntax:** `order <action> [target] OR order <pet> <action> [target]`

Order your companion or pet. Usage: order <action> [target] OR order <pet> <action> [target]

### Overpower
**Syntax:** `overpower`

Quick counterattack.

### Pat
**Syntax:** `pat`

Pat someone.

### Peace
**Syntax:** `peace`

Stop all combat in the current room (immortal only).

Usage: peace

### Perform
**Syntax:** `perform`


Begin a bard performance.

MECHANICS:
- Ongoing song with mana drain
- Moving cancels performance


### Pet
**Syntax:** `pet`

Show your pets and companions.

### Pets
**Syntax:** `pets [list|report|assist|recall|dismiss all]`

Manage all your pets. Usage: pets [list|report|assist|recall|dismiss all]

### Pick
**Syntax:** `pick <door/container>`

Pick a lock (Thief skill). Usage: pick <door/container>

### Poke
**Syntax:** `poke`

Poke someone.

### Policy
**Syntax:** `policy`

Display server policies and rules.

### Ponder
**Syntax:** `ponder`

Ponder.

### Pour
**Syntax:** `pour <from> <to> OR pour <from> out`

Pour liquid between containers. Usage: pour <from> <to> OR pour <from> out

### Practice
**Syntax:** `practice`

Practice skills/spells - must be at a guild master for your class.

### Predators Mark
**Syntax:** `predators_mark`

Mark a target for increased damage and tracking.

### Preparation
**Syntax:** `preparation`

Reset major cooldowns.

### Prompt
**Syntax:** `prompt <format> or prompt default`

Set custom prompt. Usage: prompt <format> or prompt default

### Pull
**Syntax:** `pull`

Pull a lever for lever puzzles.

### Purge
**Syntax:** `purge           - Remove all mobs/objects in room`

Remove all mobs and objects from the room, or a specific target (immortal only).

Usage: 
    purge           - Remove all mobs/objects in room
    purge <target>  - Remove specific mob/object

### Push
**Syntax:** `push`

Push a symbol or object for puzzle interactions.

### Put
**Syntax:** `put <item> <container> or put all <container>`

Put an item into a container. Usage: put <item> <container> or put all <container>

### Qsay
**Syntax:** `qsay <message>`

Say something on the quest channel. Usage: qsay <message>

### Quaff
**Syntax:** `quaff <potion>`

Drink a potion. Usage: quaff <potion>

### Quest
**Syntax:** `quest`

Manage quests.

### Questlog
**Syntax:** `questlog`

Show quest log (alias for quest log).

### Quit
**Syntax:** `quit`

Quit the game.

### Rage
**Syntax:** `rage`

Display current rage level.

### Rent
**Syntax:** `rent`

Rent a room at an inn to safely store your inventory and equipment when you log out.
You must be at an innkeeper to use this command. The innkeeper will calculate your
daily rental cost based on the items you're carrying:

  Common items:    10 gold/day
  Uncommon items:  50 gold/day
  Rare items:      200 gold/day
  Epic items:      1,000 gold/day
  Legendary items: 5,000 gold/day

Your total rent is the sum of all item costs plus a small base fee. The gold is
deducted and you are safely disconnected. When you reconnect, your gear is restored.
If you quit without renting (using `quit`), you keep your gear but miss the flavor
of a proper inn stay.

See also: QUIT, SAVE, INN

### Raise
**Syntax:** `raise <knight|wraith|lich|stalker>`

Raise a necromancer servant. Usage: raise <knight|wraith|lich|stalker>

### Rampage
**Syntax:** `rampage`

Attack all enemies in the room.

### Rapid Shot
**Syntax:** `rapid_shot`

Fire multiple arrows in quick succession.

### Read
**Syntax:** `read`

Read a book, scroll, or readable item.

### Recall
**Syntax:** `recall     - Teleport to your recall point`

Recall to your recall point (temple).

Usage:
    recall     - Teleport to your recall point
    recall set - Set current location as recall point

### Recite
**Syntax:** `recite <scroll> [target]`

Read a scroll. Usage: recite <scroll> [target]

### Redit
**Syntax:** `redit`

Online room editor (immortal only).

### Relight
**Syntax:** `relight light`

Relight your light source. Usage: relight light

### Remove
**Syntax:** `remove`

Remove worn equipment or 'remove all' to remove everything.

### Rend
**Syntax:** `rend`

Apply a bleeding wound.

### Rent
**Syntax:** `rent`

Rent a room at the Inn to save your character and quit safely.

### Report
**Syntax:** `report`

Report your status to the group.

### Reputation
**Syntax:** `reputation`

Show reputation standings with all factions.

### Rest
**Syntax:** `rest`

Rest to regenerate faster.

### Restore
**Syntax:** `restore         - Restore yourself`

Fully restore HP/mana/move for self or a target (immortal only).

Usage:
    restore         - Restore yourself
    restore <name>  - Restore a player

### Retrieve
**Syntax:** `retrieve <item>`

Retrieve an item from your house. Usage: retrieve <item>

### Ritual
**Syntax:** `ritual`

Perform dark ritual to empower all undead pets (Necromancer only).

### Rlist
**Syntax:** `rlist           - List rooms in current zone`

List all rooms in a zone (immortal only).

Usage:
    rlist           - List rooms in current zone
    rlist <zone>    - List rooms in specified zone

### Sacred Shield
**Syntax:** `sacred_shield`

Apply a holy shield.

### Sacrifice
**Syntax:** `sacrifice`

Sacrifice a corpse to the gods for gold.

### Salute
**Syntax:** `salute`

Salute.

### Save
**Syntax:** `save`

Save your character.

### Say
**Syntax:** `say`

Say something to the room.

### Score
**Syntax:** `score`

Show player stats.

### Seal Of Command
**Syntax:** `seal_of_command`

Empower attacks with holy damage.

### Search
**Syntax:** `search`

Search the room for hidden exits or items.

### Second Wind
**Syntax:** `secondwind`

Convert stamina or mana into a burst of movement recovery.

### Sell
**Syntax:** `sell <item>`

Sell an item to a shop. Usage: sell <item>

### Set
**Syntax:** `set <target> <field> <value>`

Set a field on a player or mob (immortal only).

Usage: set <target> <field> <value>

Fields for characters:
    level, hp, maxhp, mana, maxmana, move, maxmove
    str, int, wis, dex, con, cha
    gold, exp, alignment, hitroll, damroll, ac

### Sets
**Syntax:** `sets`

Show active zone set bonuses.

### Settings
**Syntax:** `settings`

Show toggleable settings.

### Shadow Blade
**Syntax:** `shadow_blade`

Empower attacks from stealth.

### Shadow Blink
**Syntax:** `shadow_blink`

Blink behind target and stealth briefly.

### Shadow Dance
**Syntax:** `shadow_dance`

Use stealth abilities in combat for a short time.

### Shadowstep
**Syntax:** `shadowstep`

Step through shadows behind target.

### Shield Bash
**Syntax:** `shield_bash`


Bash with a shield to stun/knock down.

REQUIREMENTS:
- Shield equipped

MECHANICS:
- Higher success with STR
- Stuns briefly on success


### Shield Wall
**Syntax:** `shield_wall`

Reduce incoming damage for a short time.

### Shout
**Syntax:** `shout`

Shout to everyone in the zone.

### Show
**Syntax:** `show zones    - List all zones`

Show various game statistics (immortal only).

Usage:
    show zones    - List all zones
    show players  - List all online players with details
    show stats    - Show server statistics

### Shrug
**Syntax:** `shrug`

Shrug.

### Shutdown
**Syntax:** `shutdown [now|reboot]`

Shutdown the MUD server (immortal only).

Usage: shutdown [now|reboot]

### Sigh
**Syntax:** `sigh`

Sigh.

### Silence Strike
**Syntax:** `silence_strike`

Strike and silence spellcasting.

### Sit
**Syntax:** `sit`

Sit down.

### Skill
**Syntax:** `skill`

Alias for skills command.

### Skills
**Syntax:** `skills`

Show all skills and spells available to your class, or pet abilities.

### Slap
**Syntax:** `slap`

Slap someone.

### Slay
**Syntax:** `slay <target>`

Instantly kill a target (immortal only).

Usage: slay <target>

### Slicedice
**Syntax:** `slicedice`

DoT finisher that uses 3+ combo points.

### Slip Away
**Syntax:** `slip_away`

Enter stealth after a dodge.

### Smile
**Syntax:** `smile`

Smile at someone.

### Snicker
**Syntax:** `snicker`

Snicker.

### Snoop
**Syntax:** `snoop <player>  - Start snooping on a player`

Watch what another player sees (immortal only).

Usage:
    snoop <player>  - Start snooping on a player
    snoop           - Stop snooping

### Snuff
**Syntax:** `snuff light`

Snuff your light source. Usage: snuff light

### Social
**Syntax:** `social`

Process a social command.

### Socials
**Syntax:** `socials`

List all available social commands.

### Songs
**Syntax:** `songs`


List available bard songs and performance status.

MECHANICS:
- Songs are ongoing buffs/debuffs
- Mana drains each tick while active


### Soulstone
**Syntax:** `soulstone [create]`

Create a necromancer soulstone. Usage: soulstone [create]

### South
**Syntax:** `south`

No additional details available yet.

### Spells
**Syntax:** `spells`

Show known spells.

### Split
**Syntax:** `split <amount>`

Split gold with your group. Usage: split <amount>

### Stable
**Syntax:** `stable [list|buy <mount>]`

Stable services. Usage: stable [list|buy <mount>]

### Stampede
**Syntax:** `stampede`

Command all pets to attack.

### Stance
**Syntax:** `stance [aggressive|normal|defensive]`

Set your combat stance (offense vs defense tradeoff).

### Stand
**Syntax:** `stand`

Stand up.

### Stat
**Syntax:** `stat <target>`

View detailed stats on a player, mob, or object (immortal only).

Usage: stat <target>

### Stop
**Syntax:** `stop`

Stop the current bard performance.

### Storage
**Syntax:** `storage`

View items in your storage locker.

### Store
**Syntax:** `store <item>`

Store an item in your house. Usage: store <item>

### Story
**Syntax:** `story`

Show main story quest progress.

### Sunder Armor
**Syntax:** `sunder_armor`

Reduce target armor temporarily.

### Tactical
**Syntax:** `tactical`

Show a concise combat stat line (OB/DB/PB, shield evasion, stance, wimpy, flee/escape risk, disengage, protect).

### Take
**Syntax:** `take`

Alias for get.

### Talents
**Syntax:** `talents           - Show all talent trees`

View and spend talent points.

Usage:
    talents           - Show all talent trees
    talents <tree>    - Show specific tree (e.g., 'talents fury')
    talents learn <id> - Learn/rank up a talent
    talents reset     - Reset all talents (costs gold)

### Talk
**Syntax:** `talk`

Talk to an NPC.

### Target
**Syntax:** `target`

Set your combat target.

### Taste
**Syntax:** `taste <item>`

Taste food or drink. Usage: taste <item>

### Tell
**Syntax:** `tell`

Send a private message.

### Thank
**Syntax:** `thank`

Thank someone.

### Tick
**Syntax:** `tick         - Toggle tick notifications`

Toggle tick timer notifications.

Shows when game ticks happen (regen, combat, etc.)

Usage:
    tick         - Toggle tick notifications
    tick on      - Turn on
    tick off     - Turn off

### Tickle
**Syntax:** `tickle`

Tickle someone.

### Time
**Syntax:** `time`

Display the current game time.

### Time Old
**Syntax:** `time_old`

Show the current in-game time (old version).

### Title
**Syntax:** `title <new title>`

Set your title. Usage: title <new title>

### Toggle
**Syntax:** `toggle`

Show all toggle settings.

### Transfer
**Syntax:** `transfer <player>`

Teleport a player to your location (immortal only).

Usage: transfer <player>

### Travel
**Syntax:** `travel <waypoint>`

Travel to a discovered waypoint.

Usage:
    travel <waypoint>

### Turnundead
**Syntax:** `turnundead`

Turn undead creatures, causing fear or destroying weak ones.

### Typo
**Syntax:** `typo <description>`

Report a typo. Usage: typo <description>

### Unalias
**Syntax:** `unalias`

Remove a personal alias.

### Uncover
**Syntax:** `uncover light`

Uncover your light source. Usage: uncover light

### Ungroup
**Syntax:** `ungroup         - Leave your current group`

Leave your group or remove someone from it.

Usage:
    ungroup         - Leave your current group
    ungroup <name>  - Remove player from group (leader only)

### Unlabel
**Syntax:** `unlabel`

Remove a target label.

### Unlock
**Syntax:** `unlock <door/container>`

Unlock a door or container. Usage: unlock <door/container>

### Up
**Syntax:** `up`

No additional details available yet.

### Updates
**Syntax:** `updates [number of days]`

Show recent game updates and changes. Usage: updates [number of days]

### Value
**Syntax:** `value <item>`

Check how much a shop will pay for an item. Usage: value <item>

### Vanish
**Syntax:** `vanish`

Instant stealth and drop threat.

### Vendetta
**Syntax:** `vendetta`

Mark target to take extra damage from you.

### Visible
**Syntax:** `visible`

Come out of hiding or stop sneaking.

### Volley
**Syntax:** `volley`

Rain arrows on all enemies in the room.

### Wake
**Syntax:** `wake`

Wake up.

### Warcry
**Syntax:** `warcry`

Terrifying shout that fears enemies and buffs allies.

### Wave
**Syntax:** `wave`

Wave.

### Waypoints
**Syntax:** `waypoints`

List discovered waypoints.

### Wear
**Syntax:** `wear`

Wear an item or 'wear all' to wear everything you can.

### Weather
**Syntax:** `weather`

Check the current weather.

### West
**Syntax:** `west`

No additional details available yet.

### Where
**Syntax:** `where`

Show where players/mobs are.

### Who
**Syntax:** `who`

Show online players.

### Wield
**Syntax:** `wield`

Wield a weapon.

### Wimpy
**Syntax:** `wimpy [hp amount]`

Set auto-flee HP threshold for combat. Usage: wimpy [hp amount]

### Wink
**Syntax:** `wink`

Wink.

### Withdraw
**Syntax:** `withdraw <amount>`

Withdraw gold from the bank. Usage: withdraw <amount>

### Wizhelp
**Syntax:** `wizhelp`

List all immortal commands.

Usage: wizhelp

### Wizinvis
**Syntax:** `wizinvis [level]`

Toggle invisibility to mortals (immortal only).

Usage: wizinvis [level]

### Worth
**Syntax:** `worth`

Show your total wealth breakdown.

Usage: worth

### Wyvern Sting
**Syntax:** `wyvern_sting`

Put target to sleep briefly.

### Xp
**Syntax:** `xp`

Show XP breakdown and progress.

### Yawn
**Syntax:** `yawn`

Yawn.

### Zreset
**Syntax:** `zreset          - Reset current zone`

Reset (repopulate) a zone (immortal only).

Usage: 
    zreset          - Reset current zone
    zreset <number> - Reset specific zone

## Skill

### Ambush
**Syntax:** `ambush`
**Classes:** ranger

Launch a devastating attack from hiding.

TRAINING:
- Use PRACTICE at your class trainer.
- Max 85% skill cap.

### Assassinate
**Syntax:** `assassinate`
**Classes:** assassin


A high‑risk, high‑damage stealth finisher.

REQUIREMENTS:
- Must not be in combat
- Piercing weapon required
- Best while hidden/sneaking

MECHANICS:
- Uses your stealth vs target awareness
- Higher success on lower‑level targets
- Fails if target is too alert


### Backstab
**Syntax:** `backstab`
**Classes:** assassin, thief


Backstab is a stealth opener that delivers a massive strike. It uses your
Sneak/Hide + environment to boost success and damage.

REQUIREMENTS:
- Must not be in combat
- Requires a piercing weapon (dagger/knife/stiletto)
- Best from hidden/sneaking

MECHANICS:
- Wind‑up 1–4s with spinner (can be interrupted)
- Success roll scales with DEX + stealth + level gap
- Damage multiplier scales with hidden/sneak/darkness
- Rare execution proc vs non‑boss targets
- 6s cooldown

TIPS:
- Cover/snuff light to improve stealth
- Use hide + sneak before backstab


### Bash
**Syntax:** `bash`
**Classes:** paladin, warrior


Bash to knock a target down.

REQUIREMENTS:
- In combat

MECHANICS:
- STR/DEX vs target
- On success: target knocked down (sitting)


### Battleshout
**Syntax:** `battleshout`
**Classes:** warrior

Shout to buff party's strength and constitution.

TRAINING:
- Use PRACTICE at your class trainer.
- Max 85% skill cap.

### Blur
**Syntax:** `blur`
**Classes:** assassin

A class skill. Use it to gain tactical advantages in combat or utility.

TRAINING:
- Use PRACTICE at your class trainer.
- Max 85% skill cap.

### Camouflage
**Syntax:** `camouflage`
**Classes:** ranger


Blend into terrain to reduce detection.

MECHANICS:
- Bonus in forests/swamps
- Penalized by active light


### Circle
**Syntax:** `circle`
**Classes:** thief

Strike a distracted target for a bonus attack.

### Cleave
**Syntax:** `cleave`
**Classes:** warrior

Hit multiple nearby enemies with a wide swing.

### Countersong
**Syntax:** `countersong`
**Classes:** bard


Dispel magical effects using song.

MECHANICS:
- Removes buffs/debuffs from targets


### Detect Traps
**Syntax:** `detect_traps`
**Classes:** thief


Scan for hidden traps and dangers in the room.

MECHANICS:
- Skill roll vs trap difficulty
- Higher skill improves detection


### Disarm
**Syntax:** `disarm`
**Classes:** warrior


Disarm a target’s weapon.

MECHANICS:
- DEX/STR vs target DEX
- Requires weapon in target’s hands


### Dodge
**Syntax:** `dodge`
**Classes:** assassin, ranger, thief

Passive chance to avoid hits entirely. Higher skill = higher chance.

### Dual Wield
**Syntax:** `dual_wield`
**Classes:** assassin, ranger


Use an off‑hand weapon.

REQUIREMENTS:
- Must know dual_wield
- Off‑hand must be a dagger/knife/short sword

MECHANICS:
- Off‑hand attacks have reduced hit/damage
- Scales with dual_wield skill


### Envenom
**Syntax:** `envenom`
**Classes:** assassin


Coat your blade with poison for extra damage.

MECHANICS:
- Adds poison damage on hits for a short duration
- Stronger with higher skill


### Evasion
**Syntax:** `evasion`
**Classes:** assassin, thief

Passive chance to evade attacks entirely (best for rogues).

### Fascinate
**Syntax:** `fascinate`
**Classes:** bard


Charm and pacify a target.

MECHANICS:
- Target must be out of combat
- Breaks if target is attacked


### Feint
**Syntax:** `feint`
**Classes:** assassin

Briefly lowers target defenses; improves your next hit.

### Garrote
**Syntax:** `garrote`
**Classes:** assassin


Ambush that constricts a target, disrupting them.

REQUIREMENTS:
- Must not be in combat
- Target in room

MECHANICS:
- Uses stealth roll vs target detection
- On success: bonus damage + short control window


### Hide
**Syntax:** `hide`
**Classes:** assassin, ranger, thief


Blend into shadows to avoid detection.

MECHANICS:
- Hide roll uses skill + environment
- Dark/forest/swamp boost; active light penalizes
- Successful hide can break tracking

TIPS:
- Hide before backstab for a big damage bonus


### Holy Smite
**Syntax:** `holy_smite`
**Classes:** cleric


Spend divine favor to smite a target.

MECHANICS:
- Bonus damage vs undead/evil
- Scales with favor


### Intimidate
**Syntax:** `intimidate`
**Classes:** warrior

A class skill. Use it to gain tactical advantages in combat or utility.

TRAINING:
- Use PRACTICE at your class trainer.
- Max 85% skill cap.

### Kick
**Syntax:** `kick`
**Classes:** warrior

Kick a target for extra damage.

MECHANICS:
- Usable in combat
- Scales with STR


### Lore
**Syntax:** `lore`
**Classes:** bard

Review discovered lore.

TRAINING:
- Use PRACTICE at your class trainer.
- Max 85% skill cap.

### Mark Target
**Syntax:** `mark_target`
**Classes:** assassin


Mark a target to improve accuracy and track them.

EFFECTS:
- Improves hit chance vs marked target
- Used for coordinated burst


### Mockery
**Syntax:** `mockery`
**Classes:** bard


Psychic taunt that damages and debuffs.

MECHANICS:
- Deals psychic damage
- Reduces hitroll briefly


### Parry
**Syntax:** `parry`
**Classes:** warrior

Passive chance to deflect attacks when wielding a weapon.

### Pick Lock
**Syntax:** `pick_lock`
**Classes:** bard, thief


Pick locks on doors/containers.

REQUIREMENTS:
- Lockpick skill

MECHANICS:
- Skill roll vs difficulty
- Failure leaves lock intact


### Rescue
**Syntax:** `rescue`
**Classes:** paladin, warrior


Rescue an ally by pulling aggro.

MECHANICS:
- Success scales with rescue skill, STR/DEX, and stance
- On success: attacker switches to you
- Short cooldown between attempts


### Scan
**Syntax:** `scan`
**Classes:** ranger

Scan for creatures in adjacent rooms.

TRAINING:
- Use PRACTICE at your class trainer.
- Max 85% skill cap.

### Scribe
**Syntax:** `scribe`
**Classes:** mage

A class skill. Use it to gain tactical advantages in combat or utility.

TRAINING:
- Use PRACTICE at your class trainer.
- Max 85% skill cap.

### Second Attack
**Syntax:** `second_attack`
**Classes:** assassin, paladin, ranger, thief, warrior

A class skill. Use it to gain tactical advantages in combat or utility.

TRAINING:
- Use PRACTICE at your class trainer.
- Max 85% skill cap.

### Shadow Step
**Syntax:** `shadow_step`
**Classes:** assassin


Step through shadows to reposition for a strike.

REQUIREMENTS:
- Must see the target

MECHANICS:
- Teleports behind target (flavor)
- Improves next attack accuracy


### Shield Block
**Syntax:** `shield_block`
**Classes:** warrior

Passive chance to block attacks with a shield.

### Smite
**Syntax:** `smite`
**Classes:** paladin


Paladin holy strike.

MECHANICS:
- Bonus damage vs undead/evil
- Uses holy_smite bonus where available


### Sneak
**Syntax:** `sneak`
**Classes:** assassin, bard, ranger, thief


Move silently and avoid detection.

MECHANICS:
- Persists until a failed movement check
- Detection vs mobs uses your stealth vs mob detect + environment
- Light penalizes stealth; dark/forest/swamp boosts it

TIPS:
- Pair with Hide for best results
- Cover/snuff light to reduce penalties


### Steal
**Syntax:** `steal`
**Classes:** thief


Attempt to steal gold from a target.

REQUIREMENTS:
- Must be out of combat

MECHANICS:
- DEX vs target DEX check
- Failure may anger the target


### Tame
**Syntax:** `tame`
**Classes:** ranger

Tame a wild creature. Usage: tame <creature>

TRAINING:
- Use PRACTICE at your class trainer.
- Max 85% skill cap.

### Third Attack
**Syntax:** `third_attack`
**Classes:** warrior

A class skill. Use it to gain tactical advantages in combat or utility.

TRAINING:
- Use PRACTICE at your class trainer.
- Max 85% skill cap.

### Track
**Syntax:** `track`
**Classes:** ranger


Track a target through the wilderness.

MECHANICS:
- WIS/DEX vs target stealth
- Best outdoors


### Trip
**Syntax:** `trip`
**Classes:** thief

Knock a target down with a leg sweep.

### Tumble
**Syntax:** `tumble`
**Classes:** thief

Short evasive window reducing incoming damage.

### Turn Undead
**Syntax:** `turn_undead`
**Classes:** cleric, paladin


Turn or repel undead creatures.

MECHANICS:
- WIS + skill roll vs undead level
- On success: undead flee


## Spell

### Aegis
**Syntax:** `cast 'aegis'`
**Classes:** cleric
**Level/Mana:** 1 / 65

Aegis
TARGET: defensive

CASTING:
- Use `cast 'aegis'`.
- Mana cost applies per cast.

### Animate Dead
**Syntax:** `cast 'animate dead'`
**Classes:** necromancer
**Level/Mana:** 1 / 50


Raise a corpse as undead.

MECHANICS:
- Summons a temporary undead servant
- Duration scales with level


### Armor
**Syntax:** `cast 'armor'`
**Classes:** bard, cleric, mage, necromancer, ranger
**Level/Mana:** 1 / 15

Armor
TARGET: defensive

CASTING:
- Use `cast 'armor'`.
- Mana cost applies per cast.

MECHANICS:
- Boosts armor class and grants a small absorb ward.
- Absorb scales with caster level and proficiency.
- Heavy armor reduces the ward's effectiveness.

### Barkskin
**Syntax:** `cast 'barkskin'`
**Classes:** cleric, ranger
**Level/Mana:** 1 / 40

Barkskin
TARGET: defensive

CASTING:
- Use `cast 'barkskin'`.
- Mana cost applies per cast.

### Briskness
**Syntax:** `cast 'briskness'`
**Classes:** ranger
**Level/Mana:** 1 / 30

Briskness
TARGET: defensive

CASTING:
- Use `cast 'briskness'`.
- Mana cost applies per cast.

MECHANICS:
- Restores a burst of movement immediately.
- Grants a short-term move regen surge.
- Wilderness terrain boosts the instant recovery for rangers.

### Bless
**Syntax:** `cast 'bless'`
**Classes:** bard, cleric, paladin
**Level/Mana:** 1 / 15

Bless
TARGET: defensive

CASTING:
- Use `cast 'bless'`.
- Mana cost applies per cast.

### Blindness
**Syntax:** `cast 'blindness' <target>`
**Classes:** necromancer
**Level/Mana:** 1 / 25

Blindness
TARGET: offensive

CASTING:
- Use `cast 'blindness'`.
- Mana cost applies per cast.

### Blink
**Syntax:** `cast 'blink'`
**Classes:** mage
**Level/Mana:** 1 / 30

Blink
TARGET: self

CASTING:
- Use `cast 'blink'`.
- Mana cost applies per cast.

### Burning Hands
**Syntax:** `cast 'burning hands' <target>`
**Classes:** mage
**Level/Mana:** 1 / 15

Burning Hands
TARGET: offensive
DAMAGE: 1d6+2 + 2/level

CASTING:
- Use `cast 'burning hands'`.
- Mana cost applies per cast.

### Call Lightning
**Syntax:** `cast 'call lightning' <target>`
**Classes:** ranger
**Level/Mana:** 1 / 45

Call Lightning
TARGET: offensive
DAMAGE: 4d6+5 + 2/level

CASTING:
- Use `cast 'call lightning'`.
- Mana cost applies per cast.

### Chain Lightning
**Syntax:** `cast 'chain lightning' <target>`
**Classes:** mage
**Level/Mana:** 1 / 70

Chain Lightning
TARGET: offensive
DAMAGE: 6d6+8 + 3/level

CASTING:
- Use `cast 'chain lightning'`.
- Mana cost applies per cast.

### Charm Person
**Syntax:** `cast 'charm person' <target>`
**Classes:** bard
**Level/Mana:** 1 / 30

Charm Person
TARGET: offensive

CASTING:
- Use `cast 'charm person'`.
- Mana cost applies per cast.

### Chill Touch
**Syntax:** `cast 'chill touch' <target>`
**Classes:** mage, necromancer
**Level/Mana:** 1 / 15

Chill Touch
TARGET: offensive
DAMAGE: 1d8 + 2/level

CASTING:
- Use `cast 'chill touch'`.
- Mana cost applies per cast.

### Color Spray
**Syntax:** `cast 'color spray' <target>`
**Classes:** mage
**Level/Mana:** 1 / 25

Color Spray
TARGET: offensive
DAMAGE: 2d6 + 2/level

CASTING:
- Use `cast 'color spray'`.
- Mana cost applies per cast.

### Create Food
**Syntax:** `cast 'create food'`
**Classes:** cleric
**Level/Mana:** 1 / 10

Create Food
TARGET: self

CASTING:
- Use `cast 'create food'`.
- Mana cost applies per cast.

### Create Water
**Syntax:** `cast 'create water'`
**Classes:** cleric
**Level/Mana:** 1 / 10

Create Water
TARGET: self

CASTING:
- Use `cast 'create water'`.
- Mana cost applies per cast.

### Cure Critical
**Syntax:** `cast 'cure critical'`
**Classes:** cleric
**Level/Mana:** 1 / 35


Heal grievous wounds.

MECHANICS:
- Strong single‑target heal


### Cure Light
**Syntax:** `cast 'cure light'`
**Classes:** bard, cleric, paladin, ranger
**Level/Mana:** 1 / 10

Cure Light Wounds
TARGET: defensive

CASTING:
- Use `cast 'cure light'`.
- Mana cost applies per cast.

### Cure Serious
**Syntax:** `cast 'cure serious'`
**Classes:** cleric, paladin
**Level/Mana:** 1 / 20

Cure Serious Wounds
TARGET: defensive

CASTING:
- Use `cast 'cure serious'`.
- Mana cost applies per cast.

### Death Grip
**Syntax:** `cast 'death grip' <target>`
**Classes:** necromancer
**Level/Mana:** 1 / 45


Crush a target with necrotic force.

MECHANICS:
- Strong single‑target damage


### Detect Evil
**Syntax:** `cast 'detect evil'`
**Classes:** paladin
**Level/Mana:** 1 / 10

Detect Evil
TARGET: self

CASTING:
- Use `cast 'detect evil'`.
- Mana cost applies per cast.

### Detect Magic
**Syntax:** `cast 'detect magic'`
**Classes:** bard, mage, ranger
**Level/Mana:** 1 / 10

Detect Magic
TARGET: self

CASTING:
- Use `cast 'detect magic'`.
- Mana cost applies per cast.

### Dispel Evil
**Syntax:** `cast 'dispel evil' <target>`
**Classes:** cleric
**Level/Mana:** 1 / 40

Dispel Evil
TARGET: offensive
DAMAGE: 4d8 + 3/level

CASTING:
- Use `cast 'dispel evil'`.
- Mana cost applies per cast.

### Displacement
**Syntax:** `cast 'displacement'`
**Classes:** mage
**Level/Mana:** 1 / 35

Displacement
TARGET: self

CASTING:
- Use `cast 'displacement'`.
- Mana cost applies per cast.

### Divine Protection
**Syntax:** `cast 'divine protection'`
**Classes:** cleric
**Level/Mana:** 1 / 100

Divine Protection
TARGET: self

CASTING:
- Use `cast 'divine protection'`.
- Mana cost applies per cast.

### Divine Shield
**Syntax:** `cast 'divine shield'`
**Classes:** cleric, paladin
**Level/Mana:** 1 / 75


Creates a divine barrier that absorbs damage.

MECHANICS:
- Absorbs a fixed amount of damage
- Scales with level


### Earthquake
**Syntax:** `cast 'earthquake'`
**Classes:** cleric
**Level/Mana:** 1 / 90

Earthquake
TARGET: room
DAMAGE: 5d8 + 2/level

CASTING:
- Use `cast 'earthquake'`.
- Mana cost applies per cast.

### Enchant Weapon
**Syntax:** `cast 'enchant weapon'`
**Classes:** mage
**Level/Mana:** 1 / 100

Enchant Weapon
TARGET: object

CASTING:
- Use `cast 'enchant weapon'`.
- Mana cost applies per cast.

### Energy Drain
**Syntax:** `cast 'energy drain' <target>`
**Classes:** necromancer
**Level/Mana:** 1 / 60

Energy Drain
TARGET: offensive
DAMAGE: 3d8 + 2/level

CASTING:
- Use `cast 'energy drain'`.
- Mana cost applies per cast.

### Enervation
**Syntax:** `cast 'enervation' <target>`
**Classes:** necromancer
**Level/Mana:** 1 / 35


Drain life force, weakening a target.

MECHANICS:
- Damage + debuff


### Entangle
**Syntax:** `cast 'entangle' <target>`
**Classes:** ranger
**Level/Mana:** 1 / 25

Entangle
TARGET: offensive

CASTING:
- Use `cast 'entangle'`.
- Mana cost applies per cast.

### Faerie Fire
**Syntax:** `cast 'faerie fire' <target>`
**Classes:** ranger
**Level/Mana:** 1 / 20

Faerie Fire
TARGET: offensive

CASTING:
- Use `cast 'faerie fire'`.
- Mana cost applies per cast.

### Fear
**Syntax:** `cast 'fear' <target>`
**Classes:** bard, necromancer
**Level/Mana:** 1 / 30

Fear
TARGET: offensive

CASTING:
- Use `cast 'fear'`.
- Mana cost applies per cast.

### Finger Of Death
**Syntax:** `cast 'finger of death' <target>`
**Classes:** necromancer
**Level/Mana:** 1 / 150


Deadly necrotic spell.

MECHANICS:
- Heavy damage
- Can execute targets below 25% HP
- Bosses immune


### Fire Shield
**Syntax:** `cast 'fire shield'`
**Classes:** mage
**Level/Mana:** 1 / 50

Fire Shield
TARGET: self

CASTING:
- Use `cast 'fire shield'`.
- Mana cost applies per cast.

### Fireball
**Syntax:** `cast 'fireball' <target>`
**Classes:** mage
**Level/Mana:** 1 / 40


Hurl a fireball at a target.

MECHANICS:
- Damage scales with level
- Single‑target burst


### Flamestrike
**Syntax:** `cast 'flamestrike' <target>`
**Classes:** cleric
**Level/Mana:** 1 / 60

Flamestrike
TARGET: offensive
DAMAGE: 4d8+10 + 2/level

CASTING:
- Use `cast 'flamestrike'`.
- Mana cost applies per cast.

### Fly
**Syntax:** `cast 'fly'`
**Classes:** mage
**Level/Mana:** 1 / 30

Fly
TARGET: defensive

CASTING:
- Use `cast 'fly'`.
- Mana cost applies per cast.

### Group Heal
**Syntax:** `cast 'group heal'`
**Classes:** cleric
**Level/Mana:** 1 / 80

Group Heal
TARGET: group

CASTING:
- Use `cast 'group heal'`.
- Mana cost applies per cast.

### Harm
**Syntax:** `cast 'harm' <target>`
**Classes:** cleric
**Level/Mana:** 1 / 50

Harm
TARGET: offensive
DAMAGE: 5d8

CASTING:
- Use `cast 'harm'`.
- Mana cost applies per cast.

### Haste
**Syntax:** `cast 'haste'`
**Classes:** bard
**Level/Mana:** 1 / 50


Magically hasten allies.

MECHANICS:
- Extra attacks / move speed
- Short duration


### Heal
**Syntax:** `cast 'heal'`
**Classes:** cleric
**Level/Mana:** 1 / 50


Restore major HP to a target.

MECHANICS:
- Scaling with level and heal power
- Higher mana cost, strong single target


### Heroism
**Syntax:** `cast 'heroism'`
**Classes:** bard
**Level/Mana:** 1 / 40

Heroism
TARGET: defensive

CASTING:
- Use `cast 'heroism'`.
- Mana cost applies per cast.

### Holy Aura
**Syntax:** `cast 'holy aura'`
**Classes:** cleric
**Level/Mana:** 1 / 80

Holy Aura
TARGET: defensive

CASTING:
- Use `cast 'holy aura'`.
- Mana cost applies per cast.

### Ice Armor
**Syntax:** `cast 'ice armor'`
**Classes:** mage
**Level/Mana:** 1 / 45

Ice Armor
TARGET: defensive

CASTING:
- Use `cast 'ice armor'`.
- Mana cost applies per cast.

### Identify
**Syntax:** `cast 'identify'`
**Classes:** mage
**Level/Mana:** 1 / 20

Identify
TARGET: object

CASTING:
- Use `cast 'identify'`.
- Mana cost applies per cast.

### Invisibility
**Syntax:** `cast 'invisibility'`
**Classes:** bard, mage
**Level/Mana:** 1 / 35


Become invisible to enemies.

MECHANICS:
- Breaks on attack
- Improves stealth rolls


### Lightning Bolt
**Syntax:** `cast 'lightning bolt' <target>`
**Classes:** mage
**Level/Mana:** 1 / 35


Strike a target with lightning.

MECHANICS:
- Damage scales with level
- Offensive spell


### Magic Missile
**Syntax:** `cast 'magic missile' <target>`
**Classes:** mage
**Level/Mana:** 1 / 10

Magic Missile
TARGET: offensive
DAMAGE: 1d4+1 + 1/level

CASTING:
- Use `cast 'magic missile'`.
- Mana cost applies per cast.

### Mana Shield
**Syntax:** `cast 'mana shield'`
**Classes:** mage
**Level/Mana:** 1 / 50

Mana Shield
TARGET: self

CASTING:
- Use `cast 'mana shield'`.
- Mana cost applies per cast.

### Mass Charm
**Syntax:** `cast 'mass charm'`
**Classes:** bard
**Level/Mana:** 1 / 100

Mass Charm
TARGET: room

CASTING:
- Use `cast 'mass charm'`.
- Mana cost applies per cast.

### Meteor Swarm
**Syntax:** `cast 'meteor swarm' <target>`
**Classes:** mage
**Level/Mana:** 1 / 80


Call down a swarm of meteors.

MECHANICS:
- Heavy AoE damage
- High mana cost


### Mirror Image
**Syntax:** `cast 'mirror image'`
**Classes:** mage
**Level/Mana:** 1 / 40

Mirror Image
TARGET: self

CASTING:
- Use `cast 'mirror image'`.
- Mana cost applies per cast.

### Poison
**Syntax:** `cast 'poison' <target>`
**Classes:** necromancer
**Level/Mana:** 1 / 25

Poison
TARGET: offensive

CASTING:
- Use `cast 'poison'`.
- Mana cost applies per cast.

### Protection From Evil
**Syntax:** `cast 'protection from evil'`
**Classes:** cleric, mage, paladin
**Level/Mana:** 1 / 30

Protection from Evil
TARGET: defensive

CASTING:
- Use `cast 'protection from evil'`.
- Mana cost applies per cast.

### Protection From Good
**Syntax:** `cast 'protection from good'`
**Classes:** mage, necromancer
**Level/Mana:** 1 / 30

Protection from Good
TARGET: defensive

CASTING:
- Use `cast 'protection from good'`.
- Mana cost applies per cast.

### Remove Curse
**Syntax:** `cast 'remove curse'`
**Classes:** cleric
**Level/Mana:** 1 / 35

Remove Curse
TARGET: defensive

CASTING:
- Use `cast 'remove curse'`.
- Mana cost applies per cast.

### Remove Poison
**Syntax:** `cast 'remove poison'`
**Classes:** cleric
**Level/Mana:** 1 / 30

Remove Poison
TARGET: defensive

CASTING:
- Use `cast 'remove poison'`.
- Mana cost applies per cast.

### Resurrect
**Syntax:** `cast 'resurrect'`
**Classes:** cleric
**Level/Mana:** 1 / 150

Resurrect
TARGET: special

CASTING:
- Use `cast 'resurrect'`.
- Mana cost applies per cast.

### Righteous Fury
**Syntax:** `cast 'righteous fury'`
**Classes:** cleric
**Level/Mana:** 1 / 55

Righteous Fury
TARGET: self

CASTING:
- Use `cast 'righteous fury'`.
- Mana cost applies per cast.

### Sanctuary
**Syntax:** `cast 'sanctuary'`
**Classes:** cleric
**Level/Mana:** 1 / 75


Holy aura that reduces incoming damage.

MECHANICS:
- Percentage damage reduction
- Strong defensive buff


### Shield
**Syntax:** `cast 'shield'`
**Classes:** mage, necromancer
**Level/Mana:** 1 / 25

Shield
TARGET: defensive

CASTING:
- Use `cast 'shield'`.
- Mana cost applies per cast.

MECHANICS:
- Improves armor class and grants a minor evasion boost.

### Shield Of Faith
**Syntax:** `cast 'shield of faith'`
**Classes:** cleric, paladin
**Level/Mana:** 1 / 35

Shield of Faith
TARGET: defensive

CASTING:
- Use `cast 'shield of faith'`.
- Mana cost applies per cast.

MECHANICS:
- Improves armor class and grants a minor evasion boost.

### Sleep
**Syntax:** `cast 'sleep' <target>`
**Classes:** bard, mage
**Level/Mana:** 1 / 20

Sleep
TARGET: offensive

CASTING:
- Use `cast 'sleep'`.
- Mana cost applies per cast.

### Slow
**Syntax:** `cast 'slow' <target>`
**Classes:** bard
**Level/Mana:** 1 / 35

Slow
TARGET: offensive

CASTING:
- Use `cast 'slow'`.
- Mana cost applies per cast.

### Spell Reflection
**Syntax:** `cast 'spell reflection'`
**Classes:** mage
**Level/Mana:** 1 / 70

Spell Reflection
TARGET: self

CASTING:
- Use `cast 'spell reflection'`.
- Mana cost applies per cast.

### Stoneskin
**Syntax:** `cast 'stoneskin'`
**Classes:** mage
**Level/Mana:** 1 / 60

Stoneskin
TARGET: defensive

CASTING:
- Use `cast 'stoneskin'`.
- Mana cost applies per cast.

### Stats
**Syntax:** `stats`

Stats & Influences

STR: melee damage, shield block, bash/kick/cleave/charge.
DEX: accuracy, dodge/evasion/parry, stealth skills, move regen.
CON: max HP, HP regeneration, resilience.
INT: spell damage/crit, mana pool/regen (casters).
WIS: healing potency, spell resilience, tracking/taming.
CHA: bard inspiration, social checks, vendor reactions.

Many skills add a small bonus from their primary stat.

### Summon
**Syntax:** `cast 'summon'`
**Classes:** cleric
**Level/Mana:** 1 / 75

Summon
TARGET: special

CASTING:
- Use `cast 'summon'`.
- Mana cost applies per cast.

### Teleport
**Syntax:** `cast 'teleport'`
**Classes:** mage
**Level/Mana:** 1 / 50


Teleport to a random safe location.

MECHANICS:
- Random destination
- Cannot use in no‑teleport rooms


### Vampiric Touch
**Syntax:** `cast 'vampiric touch' <target>`
**Classes:** necromancer
**Level/Mana:** 1 / 30


Drain life from a target.

MECHANICS:
- Deals damage and heals you


### Weaken
**Syntax:** `cast 'weaken' <target>`
**Classes:** necromancer
**Level/Mana:** 1 / 20

Weaken
TARGET: offensive

CASTING:
- Use `cast 'weaken'`.
- Mana cost applies per cast.

### Word Of Recall
**Syntax:** `cast 'word of recall'`
**Classes:** cleric
**Level/Mana:** 1 / 15

Word of Recall
TARGET: self

CASTING:
- Use `cast 'word of recall'`.
- Mana cost applies per cast.
