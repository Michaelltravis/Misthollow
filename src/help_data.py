"""
Help system data for Misthollow.
Contains detailed information about commands, skills, spells, and game mechanics.
"""

HELP_TOPICS = {'auction': {'category': 'command',
             'description': 'The Auction House — player-to-player trading system.\n\n'
                            'Visit Guildmaster Harlan at Market Square (room 3014) to trade.\n\n'
                            'COMMANDS:\n'
                            '  auction list [category]        — Browse listings\n'
                            '  auction sell <item> <price>     — List item for fixed price (5% fee)\n'
                            '  auction sell <item> <price> auction — List as auction with bidding\n'
                            '  auction buy <id>               — Buy a listed item\n'
                            '  auction bid <id> <amount>      — Bid on an auction listing\n'
                            '  auction cancel <id>            — Cancel your listing\n'
                            '  auction search <keyword>       — Search listings by name\n'
                            '  auction history                — View your recent transactions\n'
                            '  auction collect                — Collect pending gold/items\n\n'
                            'CATEGORIES: weapons, armor, materials, consumables, misc\n\n'
                            'RULES:\n'
                            '  - 5% listing fee (non-refundable)\n'
                            '  - 10% transaction tax on sales (gold sink)\n'
                            '  - Max 10 active listings per player\n'
                            '  - Listings expire after 48 hours (items returned via mail)\n'
                            '  - Cannot auction soulbound or quest items\n'
                            '  - Auction bids: min bid is 50% of buyout price\n\n'
                            'Aliases: auc, ah\n\n'
                            'See also: HELP MAIL, HELP SHOP',
             'syntax': 'auction <subcommand> [args]'},
             'auction house': {'category': 'general',
             'description': 'See HELP AUCTION for auction house commands.',
             'syntax': 'auction'},
             'arena': {'category': 'command',
             'description': 'The PvP Arena System — opt-in player vs player combat.\n\n'
                            'Travel to The Blood Pit Arena (zone 250) to compete.\n\n'
                            'COMMANDS:\n'
                            '  challenge <player> — Challenge someone to a duel (both in lobby)\n'
                            '  accept / decline   — Respond to a challenge\n'
                            '  arena join         — Queue for random matchmaking\n'
                            '  arena leave        — Leave the queue\n'
                            '  arena stats        — View your PvP record (wins/losses/rating)\n'
                            '  arena top          — Leaderboard (top 10 by rating)\n\n'
                            'RULES:\n'
                            '  - ELO-style rating system (start at 1000)\n'
                            '  - No death on loss — loser teleported to lobby at 1 HP\n'
                            '  - No XP loss, no item loss\n'
                            '  - Winner earns arena points + gold reward\n'
                            '  - Spectators can watch from the gallery above the lobby\n'
                            '  - PvP is opt-in only — no combat outside the arena',
             'syntax': 'arena [join|leave|stats|top]',
             'title': 'Arena (PvP)'},
 'challenge': {'category': 'command',
               'description': 'Challenge another player to an arena duel.\n'
                              'Both players must be in the Arena Lobby.\n\n'
                              'Usage: challenge <player>',
               'syntax': 'challenge <player>',
               'title': 'Challenge'},
 'account': {'category': 'command',
             'description': 'View and manage your account: every character is on one, and its password is the '
                            'only way in. Log in with the account (or any of its characters) to make, play or '
                            'delete characters.

'
                            '  account                      - this account and its characters
'
                            '  account chars                - its characters, with levels and classes
'
                            '  account claim <name> <pass>  - bring in a character from another account of yours '
                            '(the password of the account it is on now)
'
                            '  account password <old> <new> - change the account password
'
                            '  account email <address>      - an address for password resets
'
                            '  account forgot / recover <token> <new> - reset a forgotten password',
             'syntax': 'account [chars|info|claim|password|email|forgot|recover]',
             'title': 'Account'},
 'achievements': {'category': 'command',
                  'description': 'View your achievements and progress toward earning them.\n\n'
                                 'Achievements are earned by completing goals across several categories:\n'
                                 '  Combat      - Kill enemies, defeat bosses, survive without dying\n'
                                 '  Exploration - Visit rooms, complete zones, travel the world\n'
                                 '  Progression - Reach level milestones\n'
                                 '  Class       - Master your class at level 50, max talent trees\n'
                                 '  Social      - Join groups, complete quests\n'
                                 '  Wealth      - Earn gold milestones (1k, 10k, 100k)\n'
                                 '  Collection  - Read lore items, collect equipment sets\n\n'
                                 'Earning achievements grants points, titles, gold, XP, and permanent stat bonuses.\n'
                                 'Use "title" to equip a title earned from achievements.\n'
                                 'Progress bars show how close you are to each achievement.',
                  'syntax': 'achievements [category]\n  achievements combat\n  achievements exploration',
                  'title': 'Achievements'},
 'title': {'category': 'command',
           'description': 'View or set your display title from earned achievements.\n\n'
                          'Titles are unlocked by earning achievements. Your title appears after\n'
                          'your name (e.g. "Gandalf the Slayer").\n\n'
                          'With no arguments, shows all available titles.\n'
                          'Use "title <name>" or "title <number>" to set your title.\n'
                          'Use "title none" to reset to the default title.',
           'syntax': 'title [name|number|none]',
           'title': 'Title'},
 'quests': {'category': 'command',
            'description': 'The Quest Journal shows all your active and completed quests,\n'
                           'organized by category: Main Story, Side Quests, Daily, Faction, and Dungeon.\n\n'
                           'COMMANDS:\n'
                           '  quests               - Show active quests grouped by category\n'
                           '  quests <area>         - Filter quests by area\n'
                           '  quests <name>         - Look up a quest by name or ID\n'
                           '  quests completed      - Show completed quests\n'
                           '  quests daily          - Show available daily quests and status\n'
                           '  quests main           - Filter to main story quests\n'
                           '  quests side           - Filter to side quests\n'
                           '  quests faction        - Filter to faction quests\n'
                           '  quests dungeon        - Filter to dungeon quests\n'
                           '  quests track <name>   - Track a quest (progress shown in prompt)\n'
                           '  quests untrack        - Stop tracking a quest\n\n'
                           'QUEST TYPES:\n'
                           '  Main Story  - Multi-part storyline quests\n'
                           '  Side Quests - Optional adventures and quest chains\n'
                           '  Daily       - Repeatable quests that reset at midnight\n'
                           '  Faction     - Quests tied to faction reputation\n'
                           '  Dungeon     - Dungeon exploration quest chains\n\n'
                           'QUEST GIVERS:\n'
                           '  NPCs with [!] have quests available for you.\n'
                           '  NPCs with [?] are ready to accept a completed quest turn-in.\n\n'
                           'See also: quest, journal, track',
            'syntax': 'quests [<area>|<name>|completed|daily|main|side|faction|dungeon|track|untrack]',
            'title': 'Quest Journal'},
 'adrenaline_rush': {'category': 'command',
                     'description': 'Burst of speed.',
                     'syntax': 'adrenaline_rush',
                     'title': 'Adrenaline Rush'},
 'advance': {'category': 'command',
             'description': "Set a player's level (immortal only).\n\nUsage: advance <player> <level>",
             'syntax': 'advance <player> <level>',
             'title': 'Advance'},
 'aegis': {'category': 'spell',
           'classes': ['cleric'],
           'description': "Aegis\nTARGET: defensive\n\nCASTING:\n- Use `cast 'aegis'`.\n- Mana cost applies per cast.",
           'level': 1,
           'mana': 65,
           'syntax': "cast 'aegis'",
           'title': 'Aegis'},
 'ai': {'category': 'command',
        'description': 'Toggle AI chat on/off. Usage: ai on|off',
        'syntax': 'ai on|off',
        'title': 'Ai'},
 'aimed_shot': {'category': 'skill',
                'classes': ['ranger'],
                'description': 'Aimed Shot — A precisely aimed ranged strike.\n\n'
                               'MECHANICS:\n'
                               '- Deals 2.5x weapon damage, guaranteed hit\n'
                               '- +10% bonus damage on Hunter\'s Marked targets\n'
                               '- Cost: 30 Focus (15 at 100 Focus)\n'
                               '- Cooldown: 12 seconds\n\n'
                               'TALENT SYNERGIES:\n'
                               '- Careful Aim: +3% damage per rank\n\n'
                               'STRATEGY:\n'
                               '- Your bread-and-butter damage ability\n'
                               '- Mark target first for the 10% bonus\n'
                               '- At max Focus, costs only 15 — use it!\n\n'
                               'See also: HELP FOCUS, HELP HUNTERS_MARK, HELP RANGER',
                'syntax': 'aimed_shot [target]',
                'title': 'Aimed Shot'},
 'aistatus': {'category': 'command',
              'description': 'Check AI service status (admin command).',
              'syntax': 'aistatus',
              'title': 'Aistatus'},
 'alias': {'category': 'command',
           'description': 'Create, view, or remove personal command aliases.\n'
                          '\n'
                          'Usage:\n'
                          '    alias              - List all your aliases\n'
                          '    alias <word>       - Show what <word> is aliased to\n'
                          '    alias <word> <cmd> - Create alias <word> for <cmd>\n'
                          '    unalias <word>     - Remove an alias',
           'syntax': 'alias              - List all your aliases',
           'title': 'Alias'},
 'ambush': {'category': 'skill',
            'classes': ['ranger'],
            'description': 'Launch a devastating attack from hiding.\n'
                           '\n'
                           'TRAINING:\n'
                           '- Grows as you use it, up to 85%.\n'
                           '- Your guild\'s trainer teaches the rest.',
            'syntax': 'ambush',
            'title': 'Ambush'},
 'animate': {'category': 'command',
             'description': 'Animate a corpse as undead. Usage: animate <corpse>',
             'syntax': 'animate <corpse>',
             'title': 'Animate'},
 'animate_dead': {'category': 'spell',
                  'classes': ['necromancer'],
                  'description': '\n'
                                 'Raise a corpse as undead.\n'
                                 '\n'
                                 'MECHANICS:\n'
                                 '- Summons a temporary undead servant\n'
                                 '- Duration scales with level\n',
                  'level': 1,
                  'mana': 50,
                  'syntax': "cast 'animate dead'",
                  'title': 'Animate Dead'},
 'answer': {'category': 'command',
            'description': 'Answer a riddle puzzle in the room.',
            'syntax': 'answer',
            'title': 'Answer'},
 'apologize': {'category': 'command', 'description': 'Apologize.', 'syntax': 'apologize', 'title': 'Apologize'},
 'armor': {'category': 'spell',
           'classes': ['bard', 'cleric', 'mage', 'necromancer', 'ranger'],
           'description': "Armor\nTARGET: defensive\n\nCASTING:\n- Use `cast 'armor'`.\n- Mana cost applies per cast.\n\nMECHANICS:\n- Boosts armor class and grants a small absorb ward.\n- Absorb scales with caster level and proficiency.\n- Heavy armor reduces the ward's effectiveness.",
           'level': 1,
           'mana': 15,
           'syntax': "cast 'armor'",
           'title': 'Armor'},
 'ascii': {'category': 'command',
           'description': 'Toggle ASCII-only UI (no box-drawing characters). Usage: ascii [on|off]',
           'syntax': 'ascii [on|off]',
           'title': 'Ascii'},
 'ask': {'category': 'command',
         'description': 'Ask an NPC a question using LLM-powered conversation.',
         'syntax': 'ask',
         'title': 'Ask'},
 'assassin': {'category': 'class',
              'description': 'The Assassin class.\n'
                             '\n'
                             'Assassins are patient killers who study their prey before\n'
                             'striking with lethal precision. Unlike rogues, assassins\n'
                             'grow MORE dangerous the longer a fight lasts.\n'
                             '\n'
                             'CORE MECHANIC - INTEL SYSTEM:\n'
                             '  Use "mark <target>" to begin studying an enemy.\n'
                             '  Each successful attack on a marked target builds Intel (0-10).\n'
                             '  Backstab from stealth grants bonus Intel.\n'
                             '  At Intel thresholds, powerful abilities unlock:\n'
                             '    Intel 3: Expose Weakness - target takes 15% more damage\n'
                             '    Intel 6: Vital Strike   - guaranteed crit, 3x weapon damage\n'
                             '    Intel 10: Execute Contract - instant kill below 20% HP\n'
                             '\n'
                             'COMBAT FLOW:\n'
                             '  Stealth -> Mark -> Backstab (opener) -> Build Intel ->\n'
                             '  Expose/Vital/Execute -> Vanish to re-engage if needed\n'
                             '  Intel is preserved through Vanish!\n'
                             '\n'
                             'DEFENSIVE TOOLS:\n'
                             '  Feint    - reduce incoming damage 30% for 3 rounds\n'
                             '  Evasion  - 100% dodge for 10 seconds (3 min cooldown)\n'
                             '  Vanish   - drop combat, re-stealth, keep Intel\n'
                             '  Shadow Step - teleport, dodge next attack, +1 Intel\n'
                             '\n'
                             'TALENT TREES:\n'
                             '  Lethality - Burst damage, crit scaling, backstab power\n'
                             '  Poison    - DoTs, debuffs, sustain through Leech Venom\n'
                             '  Shadow    - Evasion, stealth, survivability passives\n'
                             '\n'
                             'CORE SKILLS:\n'
                             '  backstab, mark, expose, vital, execute_contract,\n'
                             '  feint, evasion, vanish, shadow_step, sneak, hide,\n'
                             '  dual_wield, second_attack, dodge, poison\n'
                             '\n'
                             'See also: HELP INTEL, HELP MARK, HELP EXPOSE,\n'
                             '          HELP VITAL, HELP EXECUTE_CONTRACT',
              'title': 'Assassin'},
 'intel': {'category': 'guide',
           'description': 'The Intel System (Assassin class)\n'
                          '\n'
                          'Intel is the assassin\'s core combat mechanic. It represents\n'
                          'your knowledge of a target\'s weaknesses, gathered through\n'
                          'observation and combat.\n'
                          '\n'
                          'HOW TO BUILD INTEL:\n'
                          '  1. Use "mark <target>" to designate your prey\n'
                          '  2. Each successful melee hit grants +1 Intel\n'
                          '  3. Backstab from stealth grants +3 Intel\n'
                          '     (with Intel Backstab talent)\n'
                          '  4. Shadow Step grants +1 Intel on marked target\n'
                          '  5. Poison ticks can grant Intel (with talent)\n'
                          '\n'
                          'INTEL THRESHOLDS:\n'
                          '  Intel 3  - "expose"   : Target takes 15% more damage (30s)\n'
                          '  Intel 6  - "vital"    : 3x weapon damage, guaranteed crit\n'
                          '  Intel 10 - "execute_contract" : Instant kill below 20% HP\n'
                          '\n'
                          'INTEL RESETS WHEN:\n'
                          '  - Target dies\n'
                          '  - You mark a new target\n'
                          '  - You die\n'
                          '\n'
                          'INTEL PERSISTS THROUGH:\n'
                          '  - Vanish (key for re-engage cycle!)\n'
                          '  - Fleeing\n'
                          '\n'
                          'TALENT SYNERGIES:\n'
                          '  Kill or Be Killed - each Intel point = +1% dodge\n'
                          '  Deadly Patience   - Intel >= 6 = 15% damage reduction\n'
                          '  Intel from Poison  - poison ticks build Intel\n'
                          '  Intel Backstab    - backstab grants +3 instead of +1\n'
                          '\n'
                          'See also: HELP MARK, HELP ASSASSIN',
           'title': 'Intel System'},
 'assassinate': {'category': 'skill',
                 'classes': ['assassin'],
                 'description': 'Legacy ability - replaced by the Intel system.\n'
                                'Use "mark" to study targets and build Intel,\n'
                                'then "execute_contract" at Intel 10 for the kill.\n'
                                '\n'
                                'See HELP ASSASSIN, HELP INTEL, HELP EXECUTE_CONTRACT',
                 'syntax': 'assassinate',
                 'title': 'Assassinate (Legacy)'},
 'assist': {'category': 'command',
            'description': 'Help someone in combat. Usage: assist <player>',
            'syntax': 'assist <player>',
            'title': 'Assist'},
 'protect': {'category': 'command',
             'description': 'Protect an ally by intercepting attacks. Warriors and paladins only.\n'
                            '\n'
                            'Usage:\n'
                            '  protect <ally>   - Guard an ally\n'
                            '  protect off      - Stop protecting\n'
                            '\n'
                            'MECHANICS:\n'
                            '- Intercept chance scales with rescue/shield skill and STR/CON\n'
                            '- Defensive stance improves intercepts\n'
                            '- Successful intercepts can improve rescue/shield block\n'
                            '- Short intercept cooldown prevents chaining',
             'syntax': 'protect <ally>|protect off',
             'title': 'Protect'},
 'at': {'category': 'command',
        'description': 'Execute a command at another location (immortal only).\n'
                       '\n'
                       'Usage: at <location> <command>\n'
                       '\n'
                       'Examples:\n'
                       '    at 3001 look\n'
                       '    at 3001 mload 3000',
        'syntax': 'at <location> <command>',
        'title': 'At'},
 'attack': {'category': 'command', 'description': 'Alias for kill.', 'syntax': 'attack', 'title': 'Attack'},
 'auction': {'category': 'command',
             'description': 'Auction channel for selling items. Usage: auction <message>',
             'syntax': 'auction <message>',
             'title': 'Auction'},
 'aura': {'category': 'command', 'description': 'Activate or view paladin auras.', 'syntax': 'aura', 'title': 'Aura'},
 'autoattack': {'category': 'command',
                'description': 'Toggle automatic basic attacks.\n'
                               '\n'
                               'Usage:\n'
                               '    autoattack          - Toggle autoattack on/off\n'
                               '    autoattack on       - Turn autoattack on\n'
                               '    autoattack off      - Turn autoattack off',
                'syntax': 'autoattack          - Toggle autoattack on/off',
                'title': 'Autoattack'},
 'autocombat': {'category': 'command',
                'description': 'Toggle automatic combat skills/spells.\n'
                               '\n'
                               'Usage:\n'
                               '    autocombat          - Toggle autocombat on/off\n'
                               '    autocombat on       - Turn autocombat on\n'
                               '    autocombat off      - Turn autocombat off',
                'syntax': 'autocombat          - Toggle autocombat on/off',
                'title': 'Autocombat'},
 'autoexit': {'category': 'command',
              'description': 'Toggle automatic exit display on room entry.',
              'syntax': 'autoexit',
              'title': 'Autoexit'},
 'autogold': {'category': 'command',
              'description': 'Toggle automatic pickup of ground gold.\n'
                             '\n'
                             'Usage:\n'
                             '    autogold          - Toggle autogold on/off\n'
                             '    autogold on       - Turn autogold on\n'
                             '    autogold off      - Turn autogold off',
              'syntax': 'autogold          - Toggle autogold on/off',
              'title': 'Autogold'},
 'autoloot': {'category': 'command',
              'description': 'Toggle automatic looting of items from corpses.\n'
                             '\n'
                             'Usage:\n'
                             '    autoloot          - Toggle autoloot on/off\n'
                             '    autoloot on       - Turn autoloot on\n'
                             '    autoloot off      - Turn autoloot off\n'
                             '    autoloot gold     - Toggle gold autoloot on/off\n'
                             '    autoloot gold on  - Turn gold autoloot on\n'
                             '    autoloot gold off - Turn gold autoloot off',
              'syntax': 'autoloot          - Toggle autoloot on/off',
              'title': 'Autoloot'},
 'autorecall': {'category': 'command',
                'description': 'Set automatic recall when HP drops below a threshold.\n'
                               '\n'
                               'Usage:\n'
                               '    autorecall             - Show current autorecall settings\n'
                               '    autorecall <hp>        - Set HP threshold (number or percentage)\n'
                               '    autorecall 50          - Recall when HP drops below 50\n'
                               '    autorecall 25%         - Recall when HP drops below 25%\n'
                               '    autorecall off         - Disable autorecall',
                'syntax': 'autorecall             - Show current autorecall settings',
                'title': 'Autorecall'},
 'avatar_of_war': {'category': 'command',
                   'description': 'Massive offensive burst.',
                   'syntax': 'avatar_of_war',
                   'title': 'Avatar Of War'},
 'backstab': {'category': 'skill',
              'classes': ['assassin', 'thief'],
              'description': '\n'
                             'Backstab is a stealth opener that delivers a massive strike.\n'
                             '\n'
                             'REQUIREMENTS:\n'
                             '- Must not be in combat\n'
                             '- Requires a piercing weapon (dagger/knife/stiletto)\n'
                             '- Best from hidden/sneaking\n'
                             '\n'
                             'MECHANICS:\n'
                             '- Wind-up 1-4s with spinner (can be interrupted)\n'
                             '- Success roll scales with DEX + stealth + level gap\n'
                             '- Damage multiplier scales with hidden/sneak/darkness\n'
                             '- 6s cooldown\n'
                             '\n'
                             'ASSASSIN INTEL BONUS:\n'
                             '- Backstab from stealth on a marked target grants +3 Intel\n'
                             '  (or +1 without the Intel Backstab talent)\n'
                             '- This is your primary Intel builder\n'
                             '- Vanish -> Backstab cycle is core assassin gameplay\n'
                             '\n'
                             'TALENT SYNERGIES:\n'
                             '- Intel Backstab: +3 Intel from stealth backstab\n'
                             '- Shadow Mend: stealth backstab heals 10% of damage dealt\n'
                             '- Improved Backstab: +5% backstab damage per rank\n'
                             '\n'
                             'TIPS:\n'
                             '- Mark target BEFORE backstabbing for Intel\n'
                             '- Use hide + sneak before backstab\n'
                             '- Vanish preserves Intel, so backstab again after vanishing\n',
              'syntax': 'backstab <target>',
              'title': 'Backstab'},
 'backup': {'category': 'command',
            'description': 'Create a backup of game data (immortal only).\n'
                           '\n'
                           'Usage: backup [players|world|full]\n'
                           '       backup list\n'
                           '       backup restore <filename>',
            'syntax': 'backup [players|world|full]',
            'title': 'Backup'},
 'balance': {'category': 'command', 'description': 'Check your bank balance.', 'syntax': 'balance', 'title': 'Balance'},
 'bard': {'category': 'class',
          'description': 'The Bard class - master of songs, lore, and trickery.\n'
                         '\n'
                         'CORE MECHANIC - INSPIRATION:\n'
                         '  Build Inspiration through songs and combat (max 10).\n'
                         '  Each point boosts all song buffs by +1%.\n'
                         '  Spend Inspiration on powerful abilities:\n'
                         '    Crescendo (5): Massive sonic damage\n'
                         '    Encore (3): Double-strength song reapply\n'
                         '    Discordant Note (4): Silence + damage\n'
                         '    Magnum Opus (10): Party +20% everything\n'
                         '\n'
                         'TALENT TREES:\n'
                         '  Performance - Song power, duration, and Inspiration gen\n'
                         '  Lore - Knowledge, utility, XP, and item identification\n'
                         '  Trickster - Crowd control, illusions, and debuffs\n'
                         '\n'
                         'See also: HELP INSPIRATION_GUIDE, HELP CRESCENDO',
          'title': 'Bard'},
 'barkskin': {'category': 'spell',
              'classes': ['cleric', 'ranger'],
              'description': 'Barkskin\n'
                             'TARGET: defensive\n'
                             '\n'
                             'CASTING:\n'
                             "- Use `cast 'barkskin'`.\n"
                             '- Mana cost applies per cast.',
              'level': 1,
              'mana': 40,
              'syntax': "cast 'barkskin'",
              'title': 'Barkskin'},
 'briskness': {'category': 'spell',
               'classes': ['ranger'],
               'description': 'Briskness\n'
                              'TARGET: defensive\n'
                              '\n'
                              'CASTING:\n'
                              "- Use `cast 'briskness'`.\n"
                              '- Mana cost applies per cast.\n'
                              '\n'
                              'MECHANICS:\n'
                              '- Restores a burst of movement immediately.\n'
                              '- Grants a short-term move regen surge.\n'
                              '- Wilderness terrain boosts the instant recovery for rangers.',
               'level': 1,
               'mana': 30,
               'syntax': "cast 'briskness'",
               'title': 'Briskness'},
 'bash': {'category': 'skill',
          'classes': ['paladin', 'warrior'],
          'description': 'Bash — Shield bash. 8s cooldown. Deals 1x damage + stun 1 round.\n\n'
                         'Evolutions (at 50/150/300 uses):\n'
                         '  Iron Wall: fortress_bash → bastion_bash → unbreakable_bash\n'
                         '  Berserker: skull_crack → cranial_devastation → execution_bash\n'
                         '  Warlord: concussive_bash → shockwave_bash → domination_bash',
          'syntax': 'bash [target]',
          'title': 'Bash'},
 'battleshout': {'category': 'skill',
                 'classes': ['warrior'],
                 'description': "Shout to buff party's strength and constitution.\n"
                                '\n'
                                'TRAINING:\n'
                                '- Grows as you use it, up to 85%.\n'
                                '- Your guild\'s trainer teaches the rest.',
                 'syntax': 'battleshout',
                 'title': 'Battleshout'},
 'bestial_wrath': {'category': 'command',
                   'description': 'Enrage your pet.',
                   'syntax': 'bestial_wrath',
                   'title': 'Bestial Wrath'},
 'bind': {'category': 'command',
          'description': 'Set your recall point to the current location.',
          'syntax': 'bind',
          'title': 'Bind'},
 'black_arrow': {'category': 'command',
                 'description': 'Poisoned arrow dealing damage over time.',
                 'syntax': 'black_arrow',
                 'title': 'Black Arrow'},
 'blade_dance': {'category': 'command',
                 'description': 'Spin striking nearby enemies.',
                 'syntax': 'blade_dance',
                 'title': 'Blade Dance'},
 'bladestorm': {'category': 'skill',
                'classes': ['warrior'],
                'description': 'Bladestorm — Finisher (🔴) for Warriors.\n'
                               'AoE: Hit all enemies for weapon damage × chain count.\n'
                               'Cooldown: 60s. Resets chain after use.\n\n'
                               'CHAIN TYPE: Finisher — consumes chain for massive damage.\n'
                               'NAMED COMBO: Charge → Cleave → Rend → Cleave → Bladestorm = Whirlwind of Steel',
                'syntax': 'bladestorm',
                'title': 'Bladestorm'},
 'bless': {'category': 'spell',
           'classes': ['bard', 'cleric', 'paladin'],
           'description': "Bless\nTARGET: defensive\n\nCASTING:\n- Use `cast 'bless'`.\n- Mana cost applies per cast.",
           'level': 1,
           'mana': 15,
           'syntax': "cast 'bless'",
           'title': 'Bless'},
 'blindness': {'category': 'spell',
               'classes': ['necromancer'],
               'description': 'Blindness\n'
                              'TARGET: offensive\n'
                              '\n'
                              'CASTING:\n'
                              "- Use `cast 'blindness'`.\n"
                              '- Mana cost applies per cast.',
               'level': 1,
               'mana': 25,
               'syntax': "cast 'blindness' <target>",
               'title': 'Blindness'},
 'blink': {'category': 'spell',
           'classes': ['mage'],
           'description': "Blink\nTARGET: self\n\nCASTING:\n- Use `cast 'blink'`.\n- Mana cost applies per cast.",
           'level': 1,
           'mana': 30,
           'syntax': "cast 'blink'",
           'title': 'Blink'},
 'blur': {'category': 'skill',
          'classes': ['assassin'],
          'description': 'Legacy ability - removed from assassin core skills.\n'
                         'Replaced by Evasion and Feint. See HELP EVASION, HELP FEINT.',
          'syntax': 'blur',
          'title': 'Blur (Legacy)'},
 'blush': {'category': 'command', 'description': 'Blush.', 'syntax': 'blush', 'title': 'Blush'},
 'bow': {'category': 'command', 'description': 'Bow.', 'syntax': 'bow', 'title': 'Bow'},
 'brief': {'category': 'command',
           'description': 'Toggle brief room descriptions.\n'
                          '\n'
                          'Usage:\n'
                          '    brief          - Toggle brief mode on/off\n'
                          '    brief on       - Turn brief mode on\n'
                          '    brief off      - Turn brief mode off',
           'syntax': 'brief          - Toggle brief mode on/off',
           'title': 'Brief'},
 'bug': {'category': 'command',
         'description': 'Report a bug. Usage: bug <description>',
         'syntax': 'bug <description>',
         'title': 'Bug'},
 'burning_hands': {'category': 'spell',
                   'classes': ['mage'],
                   'description': 'Burning Hands\n'
                                  'TARGET: offensive\n'
                                  'DAMAGE: 1d6+2 + 2/level\n'
                                  '\n'
                                  'CASTING:\n'
                                  "- Use `cast 'burning hands'`.\n"
                                  '- Mana cost applies per cast.',
                   'level': 1,
                   'mana': 15,
                   'syntax': "cast 'burning hands' <target>",
                   'title': 'Burning Hands'},
 'buy': {'category': 'command',
         'description': 'Buy an item from a shop. Usage: buy <item>',
         'syntax': 'buy <item>',
         'title': 'Buy'},
 'cackle': {'category': 'command', 'description': 'Cackle.', 'syntax': 'cackle', 'title': 'Cackle'},
 'call_lightning': {'category': 'spell',
                    'classes': ['ranger'],
                    'description': 'Call Lightning\n'
                                   'TARGET: offensive\n'
                                   'DAMAGE: 4d6+5 + 2/level\n'
                                   '\n'
                                   'CASTING:\n'
                                   "- Use `cast 'call lightning'`.\n"
                                   '- Mana cost applies per cast.',
                    'level': 1,
                    'mana': 45,
                    'syntax': "cast 'call lightning' <target>",
                    'title': 'Call Lightning'},
 'camouflage': {'category': 'skill',
                'classes': ['ranger'],
                'description': '\n'
                               'Blend into terrain to reduce detection.\n'
                               '\n'
                               'MECHANICS:\n'
                               '- Bonus in forests/swamps\n'
                               '- Penalized by active light\n',
                'syntax': 'camouflage',
                'title': 'Camouflage'},
 'cast': {'category': 'command',
          'description': "Cast a spell: cast '<spell>' [target]. A spell for the room's foes (Meteor Storm, "
                         "Earthquake, Hallowed Ground, Requiem...) strikes every foe here. In /play you aim it "
                         "instead: its key puts a circle under the mouse, a click casts it there and it strikes "
                         "only the foes inside (right-click or Esc lets it go). Typed, an aimed cast is "
                         "cast '<spell>' @x,z, where in the room in metres.",
          'syntax': "cast '<spell>' [target | @x,z]", 'title': 'Cast'},
 'chain_lightning': {'category': 'spell',
                     'classes': ['mage'],
                     'description': 'Chain Lightning\n'
                                    'TARGET: offensive\n'
                                    'DAMAGE: 6d6+8 + 3/level\n'
                                    '\n'
                                    'CASTING:\n'
                                    "- Use `cast 'chain lightning'`.\n"
                                    '- Mana cost applies per cast.',
                     'level': 1,
                     'mana': 70,
                     'syntax': "cast 'chain lightning' <target>",
                     'title': 'Chain Lightning'},
 'changelog': {'category': 'command',
               'description': 'Alias for updates command.',
               'syntax': 'changelog',
               'title': 'Changelog'},
 'charm_person': {'category': 'spell',
                  'classes': ['bard'],
                  'description': 'Charm Person\n'
                                 'TARGET: offensive\n'
                                 '\n'
                                 'CASTING:\n'
                                 "- Use `cast 'charm person'`.\n"
                                 '- Mana cost applies per cast.',
                  'level': 1,
                  'mana': 30,
                  'syntax': "cast 'charm person' <target>",
                  'title': 'Charm Person'},
 'chat': {'category': 'command',
          'description': 'Have a dynamic AI conversation with an NPC. Usage: chat <npc> <message>',
          'syntax': 'chat <npc> <message>',
          'title': 'Chat'},
 'chathistory': {'category': 'command',
                 'description': 'Show recent AI chat history with an NPC. Usage: chathistory <npc>',
                 'syntax': 'chathistory <npc>',
                 'title': 'Chathistory'},
 'cheer': {'category': 'command', 'description': 'Cheer.', 'syntax': 'cheer', 'title': 'Cheer'},
 'chill_touch': {'category': 'spell',
                 'classes': ['mage', 'necromancer'],
                 'description': 'Chill Touch\n'
                                'TARGET: offensive\n'
                                'DAMAGE: 1d8 + 2/level\n'
                                '\n'
                                'CASTING:\n'
                                "- Use `cast 'chill touch'`.\n"
                                '- Mana cost applies per cast.',
                 'level': 1,
                 'mana': 15,
                 'syntax': "cast 'chill touch' <target>",
                 'title': 'Chill Touch'},
 'circle': {'category': 'skill',
            'classes': ['thief'],
            'description': 'Circle — Dart behind a distracted enemy for a quick strike.\n\n'
                           'REQUIREMENTS:\n'
                           '- Target must be fighting someone else (not you)\n'
                           '- Target must be in the room\n\n'
                           'MECHANICS:\n'
                           '- Delivers a bonus attack against the distracted target\n'
                           '- Great for group fights where the tank holds aggro\n\n'
                           'STRATEGY:\n'
                           '- Let your group\'s tank engage first\n'
                           '- Circle for free bonus damage while they\'re distracted\n'
                           '- Combines well with backstab opener → circle followup\n\n'
                           'See also: HELP BACKSTAB, HELP THIEF',
            'syntax': 'circle [target]',
            'title': 'Circle'},
 'clear': {'category': 'command',
           'description': 'Clear the screen.\n\nUsage: clear',
           'syntax': 'clear',
           'title': 'Clear'},
 'cleave': {'category': 'skill',
            'classes': ['warrior'],
            'description': 'Cleave — Hit all enemies in room. 10s cooldown. 0.8x damage each.\n\n'
                           'Evolutions (at 50/150/300 uses):\n'
                           '  Iron Wall: bulwark_sweep → iron_tempest → aegis_storm\n'
                           '  Berserker: bloodwhirl → blood_cyclone → deathstorm\n'
                           '  Warlord: surgical_cleave → anatomical_rend → grand_strategy',
            'syntax': 'cleave',
            'title': 'Cleave'},
 'charge': {'category': 'skill',
            'classes': ['warrior'],
            'description': 'Charge — Rush to target. 12s cooldown. 1.5x damage + 1 round stun.\n'
                           'Must not already be fighting target.\n\n'
                           'Evolutions (at 50/150/300 uses):\n'
                           '  Iron Wall: ironclad_advance → juggernaut → unstoppable_force\n'
                           '  Berserker: reckless_charge → death_from_above → extinction_event\n'
                           '  Warlord: flanking_rush → tactical_insertion → checkmate',
            'syntax': 'charge <target>',
            'title': 'Charge'},
 'rally': {'category': 'skill',
           'classes': ['warrior'],
           'description': 'Rally — Self-buff/recovery. 15s cooldown. Heal 15% max HP.\n\n'
                          'Evolutions (at 50/150/300 uses):\n'
                          '  Iron Wall: stand_your_ground → immovable_object → eternal_guardian\n'
                          '  Berserker: blood_frenzy → berserker_rage → war_incarnate\n'
                          '  Warlord: battle_orders → inspiring_command → supreme_command',
           'syntax': 'rally',
           'title': 'Rally'},
 'execute': {'category': 'skill',
             'classes': ['warrior'],
             'description': 'Execute — Finisher. Only usable on targets below 25% HP.\n'
                            'Deals 3x weapon damage. 15s cooldown.\n\n'
                            'Evolutions (at 50/150/300 uses):\n'
                            '  Iron Wall: merciful_end → righteous_execution → divine_judgment\n'
                            '  Berserker: overkill → massacre → annihilation\n'
                            '  Warlord: subjugate → total_domination → absolute_authority',
             'syntax': 'execute [target]',
             'title': 'Execute'},
 'cleric': {'category': 'class',
            'description': 'The Cleric class.\n'
                           '\n'
                           'CORE MECHANIC - FAITH SYSTEM:\n'
                           '  Clerics build Faith through healing and holy damage.\n'
                           '  Shadow-spec clerics build Faith through damage instead.\n'
                           '  Taking damage below 30% HP grants +1 Faith (divine desperation).\n'
                           '  Faith (0-10) fuels powerful abilities.\n'
                           '\n'
                           'FAITH ABILITIES:\n'
                           '  divine_word  (3 Faith) - AoE group heal, 15% max HP. 20s CD.\n'
                           '  holy_fire    (5 Faith) - Massive holy damage + DoT. 25s CD.\n'
                           '  divine_intervention (10 Faith) - Invulnerable for 8s. 5min CD.\n'
                           '  shadowform   - Toggle shadow form (+25% shadow, -30% heal)\n'
                           '\n'
                           'TALENT TREES:\n'
                           '  Holy       - Healing, support, HoTs\n'
                           '  Discipline - Shields, prevention, atonement\n'
                           '  Shadow     - Shadow damage, DoTs, self-healing\n'
                           '\n'
                           'See also: HELP FAITH, HELP DIVINE_WORD, HELP HOLY_FIRE',
            'title': 'Cleric'},
 'cloak_of_shadows': {'category': 'command',
                      'description': 'Remove harmful magic effects.',
                      'syntax': 'cloak_of_shadows',
                      'title': 'Cloak Of Shadows'},
 'close': {'category': 'command',
           'description': 'Close a door or container. Usage: close <door/container>',
           'syntax': 'close <door/container>',
           'title': 'Close'},
 'cold_blood': {'category': 'command',
                'description': 'Guarantee your next attack crits.',
                'syntax': 'cold_blood',
                'title': 'Cold Blood'},
 'collections': {'category': 'command',
                 'description': 'View collection progress.',
                 'syntax': 'collections',
                 'title': 'Collections'},
 'color': {'category': 'command',
           'description': 'Set color level. Usage: color [off|sparse|normal|complete]',
           'syntax': 'color [off|sparse|normal|complete]',
           'title': 'Color'},
 'color_spray': {'category': 'spell',
                 'classes': ['mage'],
                 'description': 'Color Spray\n'
                                'TARGET: offensive\n'
                                'DAMAGE: 2d6 + 2/level\n'
                                '\n'
                                'CASTING:\n'
                                "- Use `cast 'color spray'`.\n"
                                '- Mana cost applies per cast.',
                 'level': 1,
                 'mana': 25,
                 'syntax': "cast 'color spray' <target>",
                 'title': 'Color Spray'},
 'combat': {'category': 'command',
            'description': 'Combat settings for auto-combat.\n'
                           '\n'
                           'Usage:\n'
                           '    combat settings\n'
                           '    combat settings heal <percent>\n'
                           '    combat settings skills on|off\n'
                           '    combat settings spells on|off\n'
                           '    combat settings skillpriority <skill1,skill2,...>\n'
                           '    combat settings spellpriority <spell1,spell2,...>\n'
                           '    combat settings reset',
            'syntax': 'combat settings',
            'title': 'Combat'},
 'combo': {'category': 'command', 'description': 'View current combo points.', 'syntax': 'combo', 'title': 'Combo'},
 'comfort': {'category': 'command', 'description': 'Comfort someone.', 'syntax': 'comfort', 'title': 'Comfort'},
 'commands': {'category': 'command',
              'description': 'List all available commands.',
              'syntax': 'commands',
              'title': 'Commands'},
 'compact': {'category': 'command',
             'description': 'Toggle compact combat messages.\n'
                            '\n'
                            'Usage:\n'
                            '    compact          - Toggle compact mode on/off\n'
                            '    compact on       - Turn compact mode on\n'
                            '    compact off      - Turn compact mode off',
             'syntax': 'compact          - Toggle compact mode on/off',
             'title': 'Compact'},
 'companion': {'category': 'command',
               'description': 'Manage your combat companion.\n\n'
                              'Combat companions unlock at level 20. Each class gets a thematic companion:\n'
                              '  Warrior: War Hound      Assassin: Shadow Cat     Mage: Arcane Familiar\n'
                              '  Ranger: Timber Wolf      Cleric: Guardian Spirit  Thief: Street Urchin\n'
                              '  Paladin: Celestial Stag  Necro: Shade Wraith      Bard: Dancing Sprite\n\n'
                              'COMMANDS:\n'
                              '  companion           - Show companion status\n'
                              '  companion summon     - Summon your companion\n'
                              '  companion dismiss    - Dismiss your companion\n'
                              '  companion attack     - Set to attack mode (deals ~30% of your DPS)\n'
                              '  companion defend     - Set to defend mode (guards you, reduced damage)\n'
                              '  companion passive    - Set to passive mode (no attacks)\n\n'
                              'Your companion levels with you, has its own HP, and can be knocked out\n'
                              '(but not killed). It revives after resting.\n\n'
                              'See also: mount, stable',
               'syntax': 'companion [summon|dismiss|attack|defend|passive|status]',
               'title': 'Companion'},
 'companions': {'category': 'command',
                'description': 'List your current companions. Usage: companions',
                'syntax': 'companions',
                'title': 'Companions'},
 'compare': {'category': 'command',
             'description': 'Compare a shop item to your equipped item. Usage: compare <item>',
             'syntax': 'compare <item>',
             'title': 'Compare'},
 'consider': {'category': 'command',
              'description': 'Consider how tough a mob is and learn about its capabilities.\n'
                             'Shows a threat estimate plus quick combat stats.',
              'syntax': 'consider <mob>',
              'title': 'Consider'},
 'countersong': {'category': 'skill',
                 'classes': ['bard'],
                 'description': '\n'
                                'Dispel magical effects using song.\n'
                                '\n'
                                'MECHANICS:\n'
                                '- Removes buffs/debuffs from targets\n',
                 'syntax': 'countersong',
                 'title': 'Countersong'},
 'cover': {'category': 'command',
           'description': 'Cover your light source. Usage: cover light',
           'syntax': 'cover light',
           'title': 'Cover'},
 'craft': {'category': 'command', 'description': 'Craft an item from a recipe.', 'syntax': 'craft', 'title': 'Craft'},
 'create_food': {'category': 'spell',
                 'classes': ['cleric'],
                 'description': 'Create Food\n'
                                'TARGET: self\n'
                                '\n'
                                'CASTING:\n'
                                "- Use `cast 'create food'`.\n"
                                '- Mana cost applies per cast.',
                 'level': 1,
                 'mana': 10,
                 'syntax': "cast 'create food'",
                 'title': 'Create Food'},
 'create_water': {'category': 'spell',
                  'classes': ['cleric'],
                  'description': 'Create Water\n'
                                 'TARGET: self\n'
                                 '\n'
                                 'CASTING:\n'
                                 "- Use `cast 'create water'`.\n"
                                 '- Mana cost applies per cast.',
                  'level': 1,
                  'mana': 10,
                  'syntax': "cast 'create water'",
                  'title': 'Create Water'},
 'cringe': {'category': 'command', 'description': 'Cringe.', 'syntax': 'cringe', 'title': 'Cringe'},
 'crippling_poison': {'category': 'command',
                      'description': 'Apply crippling poison to your weapon.',
                      'syntax': 'crippling_poison',
                      'title': 'Crippling Poison'},
 'crusader_strike': {'category': 'command',
                     'description': 'Instant weapon strike.',
                     'syntax': 'crusader_strike',
                     'title': 'Crusader Strike'},
 'cry': {'category': 'command', 'description': 'Cry.', 'syntax': 'cry', 'title': 'Cry'},
 'cure_critical': {'category': 'spell',
                   'classes': ['cleric'],
                   'description': 'Cure Critical Wounds — Channel divine power to mend grievous injuries.\n\n'
                                  'MECHANICS:\n'
                                  '- Strong single-target heal\n'
                                  '- Heals more than Cure Serious, less than Heal\n'
                                  '- Mana: 35\n'
                                  '- Builds +1 Faith on cast\n\n'
                                  'STRATEGY:\n'
                                  '- Your mid-tier healing spell\n'
                                  '- Use for moderate damage; save Heal for emergencies\n'
                                  '- Each cast builds Faith toward Divine Word or Holy Fire\n\n'
                                  'See also: HELP FAITH, HELP HEAL, HELP CURE_SERIOUS',
                   'level': 1,
                   'mana': 35,
                   'syntax': "cast 'cure critical' [target]",
                   'title': 'Cure Critical'},
 'cure_light': {'category': 'spell',
                'classes': ['bard', 'cleric', 'paladin', 'ranger'],
                'description': 'Cure Light Wounds\n'
                               'TARGET: defensive\n'
                               '\n'
                               'CASTING:\n'
                               "- Use `cast 'cure light'`.\n"
                               '- Mana cost applies per cast.',
                'level': 1,
                'mana': 10,
                'syntax': "cast 'cure light'",
                'title': 'Cure Light'},
 'cure_serious': {'category': 'spell',
                  'classes': ['cleric', 'paladin'],
                  'description': 'Cure Serious Wounds\n'
                                 'TARGET: defensive\n'
                                 '\n'
                                 'CASTING:\n'
                                 "- Use `cast 'cure serious'`.\n"
                                 '- Mana cost applies per cast.',
                  'level': 1,
                  'mana': 20,
                  'syntax': "cast 'cure serious'",
                  'title': 'Cure Serious'},
 'daily': {'category': 'command',
           'description': 'View your daily login bonus status.\n'
                          '\n'
                          'Usage: daily\n'
                          '\n'
                          'Log in each day to build your streak and earn better rewards!',
           'syntax': 'daily',
           'title': 'Daily'},
 'dance': {'category': 'command', 'description': 'Dance.', 'syntax': 'dance', 'title': 'Dance'},
 'dc': {'category': 'command',
        'description': 'Disconnect a player (immortal only).\n\nUsage: dc <player>',
        'syntax': 'dc <player>',
        'title': 'Dc'},
 'deadly_poison': {'category': 'command',
                   'description': 'Apply deadly poison to your weapon.',
                   'syntax': 'deadly_poison',
                   'title': 'Deadly Poison'},
 'death_from_above': {'category': 'command',
                      'description': 'Leap attack for massive damage.',
                      'syntax': 'death_from_above',
                      'title': 'Death From Above'},
 'death_grip': {'category': 'spell',
                'classes': ['necromancer'],
                'description': 'Death Grip — Crush a target with tendrils of necrotic energy.\n\n'
                               'MECHANICS:\n'
                               '- Strong single-target necrotic damage\n'
                               '- Mana: 45\n'
                               '- One of the necromancer\'s hardest-hitting spells\n'
                               '- Generates +1 Soul Shard on kill\n\n'
                               'STRATEGY:\n'
                               '- Your heavy damage spell for tough targets\n'
                               '- Use after debuffs (Enervation, Blindness) are applied\n'
                               '- Save Soul Shards for Soul Bolt/Soul Reap for burst\n\n'
                               'See also: HELP SOUL_SHARDS, HELP FINGER_OF_DEATH, HELP NECROMANCER',
                'level': 1,
                'mana': 45,
                'syntax': "cast 'death grip' <target>",
                'title': 'Death Grip'},
 'deposit': {'category': 'command',
             'description': 'Deposit gold in the bank. Usage: deposit <amount>',
             'syntax': 'deposit <amount>',
             'title': 'Deposit'},
 'detect_evil': {'category': 'spell',
                 'classes': ['paladin'],
                 'description': 'Detect Evil\n'
                                'TARGET: self\n'
                                '\n'
                                'CASTING:\n'
                                "- Use `cast 'detect evil'`.\n"
                                '- Mana cost applies per cast.',
                 'level': 1,
                 'mana': 10,
                 'syntax': "cast 'detect evil'",
                 'title': 'Detect Evil'},
 'detect_magic': {'category': 'spell',
                  'classes': ['bard', 'mage', 'ranger'],
                  'description': 'Detect Magic\n'
                                 'TARGET: self\n'
                                 '\n'
                                 'CASTING:\n'
                                 "- Use `cast 'detect magic'`.\n"
                                 '- Mana cost applies per cast.',
                  'level': 1,
                  'mana': 10,
                  'syntax': "cast 'detect magic'",
                  'title': 'Detect Magic'},
 'detect_traps': {'category': 'skill',
                  'classes': ['thief'],
                  'description': '\n'
                                 'Scan for hidden traps and dangers in the room.\n'
                                 '\n'
                                 'MECHANICS:\n'
                                 '- Skill roll vs trap difficulty\n'
                                 '- Higher skill improves detection\n',
                  'syntax': 'detect_traps',
                  'title': 'Detect Traps'},
 'diagnose': {'category': 'command',
              'description': 'Check detailed health status. Usage: diagnose [target]',
              'syntax': 'diagnose [target]',
              'title': 'Diagnose'},
 'disarm': {'category': 'skill',
            'classes': ['warrior'],
            'description': 'Disarm — Chain ability (🟡) for Warriors.\n'
                           'Disarm target for 2 rounds. Extends chain.\n'
                           'Cooldown: 15s. No resource cost.\n\n'
                           'CHAIN TYPE: Chain — extends combo by 1.',
            'syntax': 'disarm [target]',
            'title': 'Disarm'},
 'dismiss': {'category': 'command',
             'description': 'Dismiss a pet or companion. Usage: dismiss <pet name>',
             'syntax': 'dismiss <pet name>',
             'title': 'Dismiss'},
 'ride': {'category': 'command',
          'description': 'Ride several rooms in one go while mounted: ride n n 3e, or ride nnee. '
                         'Up to 10 steps; you rein in at a closed door, water you cannot cross, '
                         'a fight, or a hostile creature in your way. A mount also makes you '
                         'travel faster in 3D (+15% to +60% by mount, more with haste) and '
                         'halves what moving costs you.',
          'syntax': 'ride <directions>',
          'title': 'Ride'},
 'dismount': {'category': 'command',
              'description': 'Dismount your current mount.',
              'syntax': 'dismount',
              'title': 'Dismount'},
 'disengage': {'category': 'command',
              'description': "Break off combat if enemies aren't focused on you.\n"
                             "\n"
                             "MECHANICS:\n"
                             "- Requires you not be the current focus\n"
                             "- Costs move and has a short cooldown",
              'syntax': 'disengage',
              'title': 'Disengage'},
 'dispel_evil': {'category': 'spell',
                 'classes': ['cleric'],
                 'description': 'Dispel Evil\n'
                                'TARGET: offensive\n'
                                'DAMAGE: 4d8 + 3/level\n'
                                '\n'
                                'CASTING:\n'
                                "- Use `cast 'dispel evil'`.\n"
                                '- Mana cost applies per cast.',
                 'level': 1,
                 'mana': 40,
                 'syntax': "cast 'dispel evil' <target>",
                 'title': 'Dispel Evil'},
 'displacement': {'category': 'spell',
                  'classes': ['mage'],
                  'description': 'Displacement\n'
                                 'TARGET: self\n'
                                 '\n'
                                 'CASTING:\n'
                                 "- Use `cast 'displacement'`.\n"
                                 '- Mana cost applies per cast.',
                  'level': 1,
                  'mana': 35,
                  'syntax': "cast 'displacement'",
                  'title': 'Displacement'},
 'display': {'category': 'command',
             'description': 'Set display options. Alias for prompt.',
             'syntax': 'display',
             'title': 'Display'},
 'divine_protection': {'category': 'spell',
                       'classes': ['cleric'],
                       'description': 'Divine Protection\n'
                                      'TARGET: self\n'
                                      '\n'
                                      'CASTING:\n'
                                      "- Use `cast 'divine protection'`.\n"
                                      '- Mana cost applies per cast.',
                       'level': 1,
                       'mana': 100,
                       'syntax': "cast 'divine protection'",
                       'title': 'Divine Protection'},
 'divine_shield': {'category': 'spell',
                   'classes': ['cleric', 'paladin'],
                   'description': '\n'
                                  'Creates a divine barrier that absorbs damage.\n'
                                  '\n'
                                  'MECHANICS:\n'
                                  '- Absorbs a fixed amount of damage\n'
                                  '- Scales with level\n',
                   'level': 1,
                   'mana': 75,
                   'syntax': "cast 'divine shield'",
                   'title': 'Divine Shield'},
 'divine_storm': {'category': 'skill',
                  'classes': ['paladin'],
                  'description': 'Divine Storm — Unleash a burst of holy energy hitting all enemies.\n\n'
                                 'MECHANICS:\n'
                                 '- AoE holy damage to all enemies in the room\n'
                                 '- Deals 1.5x weapon damage + damroll to each target\n'
                                 '- Cost: 5 Holy Power (consumes all)\n'
                                 '- Cooldown: 30 seconds\n\n'
                                 'STRATEGY:\n'
                                 '- Save for multi-mob pulls\n'
                                 '- Build Holy Power with Smite/Bash, then Storm\n'
                                 '- Use Templar\'s Verdict for single target instead\n\n'
                                 'See also: HELP HOLY_POWER, HELP TEMPLARS_VERDICT, HELP PALADIN',
                  'syntax': 'divine_storm',
                  'title': 'Divine Storm'},
 'divinefavor': {'category': 'command',
                 'description': 'View current divine favor.',
                 'syntax': 'divinefavor',
                 'title': 'Divinefavor'},
 'dodge': {'category': 'skill',
           'classes': ['assassin', 'ranger', 'thief'],
           'description': 'Passive chance to avoid hits entirely. Higher skill = higher chance.',
           'syntax': 'dodge',
           'title': 'Dodge'},
 'donate': {'category': 'command',
            'description': 'Donate an item to help newbies. Usage: donate <item>',
            'syntax': 'donate <item>',
            'title': 'Donate'},
 'down': {'category': 'command',
          'description': 'No additional details available yet.',
          'syntax': 'down',
          'title': 'Down'},
 'drink': {'category': 'command',
           'description': 'Drink from a container or fountain.',
           'syntax': 'drink',
           'title': 'Drink'},
 'drink_alt': {'category': 'command',
               'description': 'Drink from a fountain or container. Usage: drink [from] <source>',
               'syntax': 'drink [from] <source>',
               'title': 'Drink Alt'},
 'drop': {'category': 'command', 'description': 'Drop an item or gold.', 'syntax': 'drop', 'title': 'Drop'},
 'dual_wield': {'category': 'skill',
                'classes': ['assassin', 'ranger'],
                'description': '\n'
                               'Use an off-hand weapon.\n'
                               '\n'
                               'REQUIREMENTS:\n'
                               '- Must know dual_wield\n'
                               '- Off-hand must be a dagger/knife/short sword\n'
                               '\n'
                               'MECHANICS:\n'
                               '- Off-hand attacks have reduced hit/damage\n'
                               '- Scales with dual_wield skill\n',
                'syntax': 'dual_wield',
                'title': 'Dual Wield'},
 'dungeon': {'category': 'command',
             'description': 'Procedural dungeon commands.\n'
                            '\n'
                            'Usage:\n'
                            '    dungeon list\n'
                            '    dungeon enter <type> [difficulty] [permadeath]\n'
                            '    dungeon enter daily [difficulty] [permadeath]\n'
                            '    dungeon leave',
             'syntax': 'dungeon list',
             'title': 'Dungeon'},
 'earthquake': {'category': 'spell',
                'classes': ['cleric'],
                'description': 'Earthquake\n'
                               'TARGET: room\n'
                               'DAMAGE: 5d8 + 2/level\n'
                               '\n'
                               'CASTING:\n'
                               "- Use `cast 'earthquake'`.\n"
                               '- Mana cost applies per cast.',
                'level': 1,
                'mana': 90,
                'syntax': "cast 'earthquake'",
                'title': 'Earthquake'},
 'east': {'category': 'command',
          'description': 'No additional details available yet.',
          'syntax': 'east',
          'title': 'East'},
 'eat': {'category': 'command', 'description': 'Eat food.', 'syntax': 'eat', 'title': 'Eat'},
 'echo': {'category': 'command',
          'description': 'Send a message to the current room (immortal only).\n\nUsage: echo <message>',
          'syntax': 'echo <message>',
          'title': 'Echo'},
 'emote': {'category': 'command', 'description': 'Emote an action.', 'syntax': 'emote', 'title': 'Emote'},
 'enchant_weapon': {'category': 'spell',
                    'classes': ['mage'],
                    'description': 'Enchant Weapon\n'
                                   'TARGET: object\n'
                                   '\n'
                                   'CASTING:\n'
                                   "- Use `cast 'enchant weapon'`.\n"
                                   '- Mana cost applies per cast.',
                    'level': 1,
                    'mana': 100,
                    'syntax': "cast 'enchant weapon'",
                    'title': 'Enchant Weapon'},
 'encore': {'category': 'skill',
            'classes': ['bard'],
            'description': 'Encore — Reapply your active song at double strength.\n\n'
                           'MECHANICS:\n'
                           '- Your current song buff is doubled for 2 ticks\n'
                           '- Must be actively performing a song\n'
                           '- Cost: 3 Inspiration (2 with Encore Mastery talent)\n'
                           '- Cooldown: 30 seconds\n\n'
                           'STRATEGY:\n'
                           '- Use during boss fights to double your song buffs\n'
                           '- Pairs well with Song of Valor or Song of Healing\n'
                           '- Build Inspiration through performance, then Encore\n\n'
                           'See also: HELP INSPIRATION, HELP SONGS, HELP BARD',
            'syntax': 'encore',
            'title': 'Encore'},
 'energy_drain': {'category': 'spell',
                  'classes': ['necromancer'],
                  'description': 'Energy Drain\n'
                                 'TARGET: offensive\n'
                                 'DAMAGE: 3d8 + 2/level\n'
                                 '\n'
                                 'CASTING:\n'
                                 "- Use `cast 'energy drain'`.\n"
                                 '- Mana cost applies per cast.',
                  'level': 1,
                  'mana': 60,
                  'syntax': "cast 'energy drain' <target>",
                  'title': 'Energy Drain'},
 'enervation': {'category': 'spell',
                'classes': ['necromancer'],
                'description': 'Enervation — Sap a target\'s vitality, weakening them.\n\n'
                               'MECHANICS:\n'
                               '- Deals necrotic damage\n'
                               '- Applies a debuff reducing target\'s combat effectiveness\n'
                               '- Mana: 35\n'
                               '- Generates +1 Soul Shard on kill\n\n'
                               'STRATEGY:\n'
                               '- Open with Enervation to weaken tough enemies\n'
                               '- Follow up with damage spells while they\'re debuffed\n'
                               '- Stack with Blindness and Weaken for maximum control\n\n'
                               'See also: HELP SOUL_SHARDS, HELP WEAKEN, HELP NECROMANCER',
                'level': 1,
                'mana': 35,
                'syntax': "cast 'enervation' <target>",
                'title': 'Enervation'},
 'entangle': {'category': 'spell',
              'classes': ['ranger'],
              'description': 'Entangle\n'
                             'TARGET: offensive\n'
                             '\n'
                             'CASTING:\n'
                             "- Use `cast 'entangle'`.\n"
                             '- Mana cost applies per cast.',
              'level': 1,
              'mana': 25,
              'syntax': "cast 'entangle' <target>",
              'title': 'Entangle'},
 'enter': {'category': 'command',
           'description': 'Enter a building or portal. Usage: enter [portal/building name]',
           'syntax': 'enter [portal/building name]',
           'title': 'Enter'},
 'envenom': {'category': 'skill',
             'classes': ['assassin'],
             'description': '\n'
                            'Coat your blade with poison for extra damage.\n'
                            '\n'
                            'MECHANICS:\n'
                            '- Adds poison damage on hits for a short duration\n'
                            '- Stronger with higher skill\n',
             'syntax': 'envenom',
             'title': 'Envenom'},
 'equipment': {'category': 'command',
               'description': 'Show equipped items.',
               'syntax': 'equipment',
               'title': 'Equipment'},
 'evasion': {'category': 'skill',
             'classes': ['assassin', 'thief'],
             'description': 'Activate Evasion to dodge all attacks.\n'
                            '\n'
                            'ASSASSIN VERSION:\n'
                            '- 100% dodge chance for 10 seconds\n'
                            '- Cooldown: 180 seconds (3 minutes)\n'
                            '- Your main "oh shit" button for boss fights\n'
                            '- Use to survive burst damage phases\n'
                            '- Combine with Intel building - dodge attacks while\n'
                            '  your poisons tick and build Intel\n'
                            '\n'
                            'THIEF VERSION:\n'
                            '- Passive chance to evade attacks\n'
                            '\n'
                            'See also: HELP FEINT, HELP VANISH',
             'syntax': 'evasion',
             'title': 'Evasion'},
 'eviscerate': {'category': 'command',
                'description': 'Powerful finisher that consumes all combo points.',
                'syntax': 'eviscerate',
                'title': 'Eviscerate'},
 'examine': {'category': 'command',
             'description': 'Examine an item in your inventory or equipment. Usage: examine <item>',
             'syntax': 'examine <item>',
             'title': 'Examine'},
 'execute': {'category': 'skill',
             'classes': ['warrior'],
             'description': 'Execute — Finisher (🔴) for Warriors.\n'
                            'Massive damage finisher. Target must be below 30% HP\n'
                            '(chain 5 removes this restriction). Resets chain.\n'
                            'Cooldown: 10s.\n\n'
                            'CHAIN TYPE: Finisher — consumes chain for massive damage.\n'
                            'NAMED COMBOS: Bash → Rend → Execute = Butcher\'s Sequence\n'
                            '              Hamstring → Rend → Hamstring → Execute = Death by a Thousand Cuts\n'
                            '              Charge → Rend → Cleave → Execute = Berserker Rush\n\n'
                            'Assassin: See HELP EXECUTE_CONTRACT for Intel finisher.',
             'syntax': 'execute [target]',
             'title': 'Execute'},
 'execute_contract': {'category': 'skill',
                      'classes': ['assassin'],
                      'description': 'Execute Contract - the ultimate assassin finisher.\n'
                                     '\n'
                                     'Usage: execute_contract\n'
                                     '\n'
                                     'REQUIREMENTS:\n'
                                     '- Must be an assassin\n'
                                     '- Must be fighting your marked target\n'
                                     '- Requires 10 Intel (maximum)\n'
                                     '\n'
                                     'EFFECTS:\n'
                                     '- Target below 20% HP: INSTANT KILL\n'
                                     '  (bosses take 5x weapon damage instead)\n'
                                     '- Target above 20% HP: 5x weapon damage + 2x damroll\n'
                                     '- Consumes all Intel (resets to 0)\n'
                                     '\n'
                                     'STRATEGY:\n'
                                     '- This is your fight-ending move\n'
                                     '- Build to Intel 10, whittle boss below 20%,\n'
                                     '  then Execute for the kill\n'
                                     '- Against non-bosses below 20%, it is a guaranteed kill\n'
                                     '- Against bosses, still deals massive damage\n'
                                     '\n'
                                     'See also: HELP INTEL, HELP EXPOSE, HELP VITAL',
                      'syntax': 'execute_contract',
                      'title': 'Execute Contract'},
 'expose': {'category': 'skill',
            'classes': ['assassin'],
            'description': 'Expose Weakness - Intel 3 threshold ability.\n'
                           '\n'
                           'Usage: expose\n'
                           '\n'
                           'REQUIREMENTS:\n'
                           '- Must be an assassin\n'
                           '- Marked target must be in the room\n'
                           '- Requires at least 3 Intel\n'
                           '\n'
                           'EFFECTS:\n'
                           '- Target takes 15% more damage from you for 30 seconds\n'
                           '- Consumes 3 Intel\n'
                           '\n'
                           'STRATEGY:\n'
                           '- Use early in a boss fight to amplify all damage\n'
                           '- Can be reapplied once you build Intel back to 3\n'
                           '- Stacks with other damage modifiers\n'
                           '\n'
                           'See also: HELP INTEL, HELP VITAL, HELP EXECUTE_CONTRACT',
            'syntax': 'expose',
            'title': 'Expose Weakness'},
 'escape': {'category': 'command',
            'description': 'Attempt a controlled escape in a chosen direction.\n'
                           '\n'
                           'MECHANICS:\n'
                           '- Chance scales with escape skill (or DEX)\n'
                           '- Costs move and has a short cooldown',
            'syntax': 'escape <direction>',
            'title': 'Escape'},
 'exits': {'category': 'command',
           'description': 'Show available exits from the current room with descriptions.',
           'syntax': 'exits',
           'title': 'Exits'},
 'explosive_trap': {'category': 'command',
                    'description': 'Set an explosive trap in the room.',
                    'syntax': 'explosive_trap',
                    'title': 'Explosive Trap'},
 'faction': {'category': 'command',
             'description': 'Show detailed reputation for a specific faction.',
             'syntax': 'faction',
             'title': 'Faction'},
 'faerie_fire': {'category': 'spell',
                 'classes': ['ranger'],
                 'description': 'Faerie Fire\n'
                                'TARGET: offensive\n'
                                '\n'
                                'CASTING:\n'
                                "- Use `cast 'faerie fire'`.\n"
                                '- Mana cost applies per cast.',
                 'level': 1,
                 'mana': 20,
                 'syntax': "cast 'faerie fire' <target>",
                 'title': 'Faerie Fire'},
 'fascinate': {'category': 'skill',
               'classes': ['bard'],
               'description': '\n'
                              'Charm and pacify a target.\n'
                              '\n'
                              'MECHANICS:\n'
                              '- Target must be out of combat\n'
                              '- Breaks if target is attacked\n',
               'syntax': 'fascinate',
               'title': 'Fascinate'},
 'fear': {'category': 'spell',
          'classes': ['bard', 'necromancer'],
          'description': "Fear\nTARGET: offensive\n\nCASTING:\n- Use `cast 'fear'`.\n- Mana cost applies per cast.",
          'level': 1,
          'mana': 30,
          'syntax': "cast 'fear' <target>",
          'title': 'Fear'},
 'feint': {'category': 'skill',
           'classes': ['assassin'],
           'description': 'Feint - your bread-and-butter damage mitigation.\n'
                          '\n'
                          'Usage: feint\n'
                          '\n'
                          'REQUIREMENTS:\n'
                          '- Must be in combat\n'
                          '- Must be an assassin\n'
                          '- Cooldown: 20 seconds\n'
                          '\n'
                          'EFFECTS:\n'
                          '- Your current target deals 30% less damage to you\n'
                          '- Lasts 3 combat rounds (~12 seconds)\n'
                          '\n'
                          'STRATEGY:\n'
                          '- Use on cooldown during boss fights\n'
                          '- Combine with Evasion for near-invulnerability\n'
                          '- With Numbing Toxin talent, poisoned targets deal\n'
                          '  even less damage on top of Feint\n'
                          '\n'
                          'See also: HELP EVASION, HELP VANISH',
           'syntax': 'feint',
           'title': 'Feint'},
 'fill': {'category': 'command',
          'description': 'Fill a container from a fountain. Usage: fill <container> [fountain]',
          'syntax': 'fill <container> [fountain]',
          'title': 'Fill'},
 'find': {'category': 'command',
          'description': 'Find a mob or object anywhere in the world (immortal only).\n'
                         '\n'
                         'Usage:\n'
                         '    find mob <name>    - Find all mobs matching name\n'
                         '    find obj <name>    - Find all objects matching name',
          'syntax': 'find mob <name>    - Find all mobs matching name',
          'title': 'Find'},
 'finger_of_death': {'category': 'spell',
                     'classes': ['necromancer'],
                     'description': '\n'
                                    'Deadly necrotic spell.\n'
                                    '\n'
                                    'MECHANICS:\n'
                                    '- Heavy damage\n'
                                    '- Can execute targets below 25% HP\n'
                                    '- Bosses immune\n',
                     'level': 1,
                     'mana': 150,
                     'syntax': "cast 'finger of death' <target>",
                     'title': 'Finger Of Death'},
 'fire_shield': {'category': 'spell',
                 'classes': ['mage'],
                 'description': 'Fire Shield\n'
                                'TARGET: self\n'
                                '\n'
                                'CASTING:\n'
                                "- Use `cast 'fire shield'`.\n"
                                '- Mana cost applies per cast.',
                 'level': 1,
                 'mana': 50,
                 'syntax': "cast 'fire shield'",
                 'title': 'Fire Shield'},
 'fireball': {'category': 'spell',
              'classes': ['mage'],
              'description': '\n'
                             'Hurl a fireball at a target.\n'
                             '\n'
                             'MECHANICS:\n'
                             '- Damage scales with level\n'
                             '- Single-target burst\n',
              'level': 1,
              'mana': 40,
              'syntax': "cast 'fireball' <target>",
              'title': 'Fireball'},
 'flamestrike': {'category': 'spell',
                 'classes': ['cleric'],
                 'description': 'Flamestrike\n'
                                'TARGET: offensive\n'
                                'DAMAGE: 4d8+10 + 2/level\n'
                                '\n'
                                'CASTING:\n'
                                "- Use `cast 'flamestrike'`.\n"
                                '- Mana cost applies per cast.',
                 'level': 1,
                 'mana': 60,
                 'syntax': "cast 'flamestrike' <target>",
                 'title': 'Flamestrike'},
 'flee': {'category': 'command',
          'description': 'Panic flee from combat in a random direction.\n'
                         '\n'
                         'MECHANICS:\n'
                         '- Chance scales with DEX and stance\n'
                         '- Costs move and has a short cooldown\n'
                         '- On success: random exit, small XP loss',
          'syntax': 'flee',
          'title': 'Flee'},
 'fly': {'category': 'spell',
         'classes': ['mage'],
         'description': "Fly\nTARGET: defensive\n\nCASTING:\n- Use `cast 'fly'`.\n- Mana cost applies per cast.",
         'level': 1,
         'mana': 30,
         'syntax': "cast 'fly'",
         'title': 'Fly'},
 'follow': {'category': 'command',
            'description': 'Follow another player. Usage: follow <player> or follow self',
            'syntax': 'follow <player> or follow self',
            'title': 'Follow'},
 'force': {'category': 'command',
           'description': 'Force a player to execute a command (immortal only).\n\nUsage: force <player> <command>',
           'syntax': 'force <player> <command>',
           'title': 'Force'},
 'freeze': {'category': 'command',
            'description': "Freeze a player so they can't do anything (immortal only).\n\nUsage: freeze <player>",
            'syntax': 'freeze <player>',
            'title': 'Freeze'},
 'garrote': {'category': 'skill',
             'classes': ['assassin'],
             'description': 'Legacy ability - removed from assassin core skills.\n'
                            'Replaced by the Intel system. See HELP ASSASSIN.',
             'syntax': 'garrote',
             'title': 'Garrote (Legacy)'},
 'gather': {'category': 'command',
            'description': 'Gather resources based on environment.',
            'syntax': 'gather',
            'title': 'Gather'},
 'gecho': {'category': 'command',
           'description': 'Send a message to all players (immortal only).\n\nUsage: gecho <message>',
           'syntax': 'gecho <message>',
           'title': 'Gecho'},
 'get': {'category': 'command',
         'description': 'Pick up an item.\n'
                        '\n'
                        'Usage:\n'
                        '    get <item>              - Get item from room\n'
                        '    get all                 - Get all items from room\n'
                        '    get <item> <container>  - Get item from container\n'
                        '    get all <container>     - Get all items from container\n'
                        '    get <item> from <container> - Alternative syntax\n'
                        '    get all from <container>    - Alternative syntax',
         'syntax': 'get <item>              - Get item from room',
         'title': 'Get'},
 'giggle': {'category': 'command', 'description': 'Giggle.', 'syntax': 'giggle', 'title': 'Giggle'},
 'give': {'category': 'command', 'description': 'Give an item to someone.', 'syntax': 'give', 'title': 'Give'},
 'glare': {'category': 'command', 'description': 'Glare at someone.', 'syntax': 'glare', 'title': 'Glare'},
 'gossip': {'category': 'command',
            'description': 'Global chat channel. Usage: gossip <message>',
            'syntax': 'gossip <message>',
            'title': 'Gossip'},
 'goto': {'category': 'command',
          'description': 'Teleport to a room or zone (testing command).\n'
                         '\n'
                         'Usage:\n'
                         '    goto <vnum>     - Go to room vnum (e.g. goto 3001)\n'
                         '    goto <zone>     - Go to zone entrance (e.g. goto 30)',
          'syntax': 'goto <vnum>     - Go to room vnum (e.g. goto 3001)',
          'title': 'Goto'},
 'grats': {'category': 'command',
           'description': 'Congratulations channel. Usage: grats <message>',
           'syntax': 'grats <message>',
           'title': 'Grats'},
 'greet': {'category': 'command', 'description': 'Greet someone.', 'syntax': 'greet', 'title': 'Greet'},
 'grin': {'category': 'command', 'description': 'Grin.', 'syntax': 'grin', 'title': 'Grin'},
 'group': {'category': 'command',
           'description': 'Manage your group/party for multiplayer dungeon runs.\n'
                          'Max group size: 6 players.\n'
                          '\n'
                          'Usage:\n'
                          '    group               - Show group status\n'
                          '    group <player>      - Invite a player to your group\n'
                          '    group accept        - Accept a pending invitation\n'
                          '    group decline       - Decline a pending invitation\n'
                          '    group leave         - Leave your current group\n'
                          '    group list          - Show group status\n'
                          '    group kick <player> - Remove player (leader only)\n'
                          '    group leader <player> - Transfer leadership (leader only)\n'
                          '    group loot <mode>   - Set loot: freeforall or roundrobin\n'
                          '    group follow        - Toggle auto-follow on/off\n'
                          '    group disband       - Disband the group (leader only)\n'
                          '    group all           - Group all followers\n'
                          '\n'
                          'XP Sharing: When a grouped player kills a mob, XP splits\n'
                          'among group members in the same room with a +10% bonus per\n'
                          'extra member to incentivize grouping.\n'
                          '\n'
                          'Loot Modes:\n'
                          '  freeforall - Anyone can loot (default)\n'
                          '  roundrobin - Loot rotates among members\n'
                          '\n'
                          'Group Effects: Bard songs and Paladin auras affect group\n'
                          'members in the same room.\n'
                          '\n'
                          'See also: GTELL, FOLLOW, SPLIT',
           'syntax': 'group <player>      - Invite a player',
           'title': 'Group'},
 'group_heal': {'category': 'spell',
                'classes': ['cleric'],
                'description': 'Group Heal\n'
                               'TARGET: group\n'
                               '\n'
                               'CASTING:\n'
                               "- Use `cast 'group heal'`.\n"
                               '- Mana cost applies per cast.',
                'level': 1,
                'mana': 80,
                'syntax': "cast 'group heal'",
                'title': 'Group Heal'},
 'grumble': {'category': 'command', 'description': 'Grumble.', 'syntax': 'grumble', 'title': 'Grumble'},
 'gtell': {'category': 'command',
           'description': 'Send a message to all group members regardless of location.\n'
                          'Aliases: gt, grouptell\n'
                          '\n'
                          'Usage: gtell <message>\n'
                          '\n'
                          'You must be in a group to use this command.\n'
                          'See also: GROUP',
           'syntax': 'gtell <message>',
           'title': 'Gtell'},
 'harm': {'category': 'spell',
          'classes': ['cleric'],
          'description': 'Harm\n'
                         'TARGET: offensive\n'
                         'DAMAGE: 5d8\n'
                         '\n'
                         'CASTING:\n'
                         "- Use `cast 'harm'`.\n"
                         '- Mana cost applies per cast.',
          'level': 1,
          'mana': 50,
          'syntax': "cast 'harm' <target>",
          'title': 'Harm'},
 'haste': {'category': 'spell',
           'classes': ['bard'],
           'description': '\nMagically hasten allies.\n\nMECHANICS:\n- Extra attacks / move speed\n- Short duration\n',
           'level': 1,
           'mana': 50,
           'syntax': "cast 'haste'",
           'title': 'Haste'},
 'heal': {'category': 'spell',
          'classes': ['cleric'],
          'description': '\n'
                         'Restore major HP to a target.\n'
                         '\n'
                         'MECHANICS:\n'
                         '- Scaling with level and heal power\n'
                         '- Higher mana cost, strong single target\n',
          'level': 1,
          'mana': 50,
          'syntax': "cast 'heal'",
          'title': 'Heal'},
 'help': {'category': 'command',
          'description': 'Show help information for commands, skills, and spells.',
          'syntax': 'help',
          'title': 'Help'},
 'heroism': {'category': 'spell',
             'classes': ['bard'],
             'description': 'Heroism\n'
                            'TARGET: defensive\n'
                            '\n'
                            'CASTING:\n'
                            "- Use `cast 'heroism'`.\n"
                            '- Mana cost applies per cast.',
             'level': 1,
             'mana': 40,
             'syntax': "cast 'heroism'",
             'title': 'Heroism'},
 'hide': {'category': 'skill',
          'classes': ['assassin', 'ranger', 'thief'],
          'description': '\n'
                         'Blend into shadows to avoid detection.\n'
                         '\n'
                         'MECHANICS:\n'
                         '- Hide roll uses skill + environment\n'
                         '- Dark/forest/swamp boost; active light penalizes\n'
                         '- Successful hide can break tracking\n'
                         '\n'
                         'TIPS:\n'
                         '- Hide before backstab for a big damage bonus\n',
          'syntax': 'hide',
          'title': 'Hide'},
 'hint': {'category': 'command',
          'description': 'Request a hint for the current room puzzle.',
          'syntax': 'hint',
          'title': 'Hint'},
 'hire': {'category': 'command',
          'description': 'Hire a companion from a tavern or guild. Usage: hire <npc>',
          'syntax': 'hire <npc>',
          'title': 'Hire'},
 'holler': {'category': 'command',
            'description': 'Shout to everyone (costs 20 movement). Usage: holler <message>',
            'syntax': 'holler <message>',
            'title': 'Holler'},
 'holy_aura': {'category': 'spell',
               'classes': ['cleric'],
               'description': 'Holy Aura\n'
                              'TARGET: defensive\n'
                              '\n'
                              'CASTING:\n'
                              "- Use `cast 'holy aura'`.\n"
                              '- Mana cost applies per cast.',
               'level': 1,
               'mana': 80,
               'syntax': "cast 'holy aura'",
               'title': 'Holy Aura'},
 'holy_smite': {'category': 'skill',
                'classes': ['cleric'],
                'description': '\n'
                               'Spend divine favor to smite a target.\n'
                               '\n'
                               'MECHANICS:\n'
                               '- Bonus damage vs undead/evil\n'
                               '- Scales with favor\n',
                'syntax': 'holy_smite',
                'title': 'Holy Smite'},
 'holylight': {'category': 'command',
               'description': 'Toggle ability to see everything (dark rooms, invisible, etc) (immortal only).\n'
                              '\n'
                              'Usage: holylight',
               'syntax': 'holylight',
               'title': 'Holylight'},
 'holysmite': {'category': 'command',
               'description': 'Spend divine favor for a powerful holy attack.',
               'syntax': 'holysmite',
               'title': 'Holysmite'},
 'house': {'category': 'command',
           'description': 'Player Housing System — own a home in the Garathorm Housing District!\n\n'
                          'COMMANDS:\n'
                          '  house list              — View all plots (available and owned)\n'
                          '  house buy               — Purchase the plot you\'re standing on\n'
                          '  house sell              — Sell your house (50% refund, chest must be empty)\n'
                          '  house info              — View your house details\n'
                          '  house enter / home      — Teleport to your house (30 min cooldown)\n'
                          '  house lock / unlock     — Control who can enter\n'
                          '  house invite <player>   — Add a player to your guest list\n'
                          '  house name <name>       — Name your house\n'
                          '  house decorate <desc>   — Set a custom room description\n'
                          '  house furnish [item]    — View or install furniture\n'
                          '  house storage           — View chest contents\n'
                          '  store <item>            — Store an item in your chest (max 50)\n'
                          '  retrieve <item>         — Take an item from your chest\n\n'
                          'PRICES:\n'
                          '  Small Cottage:    5,000 gold  (Plots 1-4, 11-14)\n'
                          '  Medium Townhouse: 15,000 gold (Plots 5-7, 15-17)\n'
                          '  Grand Estate:     50,000 gold (Plots 8-10, 18-20)\n\n'
                          'FURNITURE (buy from Hearth & Home Furnishings in the district):\n'
                          '  Bed          — 2,000g — +50% HP regen when resting at home\n'
                          '  Table        — 1,500g — Decorative\n'
                          '  Trophy Case  — 5,000g — Displays achievements to visitors\n'
                          '  Weapon Rack  — 3,000g — Display your finest weapons\n'
                          '  Bookshelf    — 2,500g — Stores and displays lore\n\n'
                          'NOTES:\n'
                          '  - One house per player\n'
                          '  - Storage persists across sessions (max 50 items)\n'
                          '  - Locked houses only allow owner and invited guests',
           'syntax': 'house [buy|sell|list|info|enter|lock|unlock|invite|name|decorate|furnish|storage]',
           'title': 'Housing'},
 'home': {'category': 'command',
          'description': 'Teleport to your house from anywhere. 30 minute cooldown.\n'
                         'Alias for \'house enter\'. Stops combat before teleporting.',
          'syntax': 'home',
          'title': 'Home (Teleport)'},
 'housing': {'category': 'guide',
             'description': 'See HELP HOUSE for full housing system documentation.',
             'syntax': 'help house',
             'title': 'Housing'},
 'events': {'category': 'command',
            'description': 'View active world events.\n\n'
                           'World events occur periodically and include:\n'
                           '  - Invasions: Defend zones from monster attacks\n'
                           '  - World Bosses: Powerful foes requiring group effort\n'
                           '  - Treasure Hunts: Follow clues to hidden treasure\n'
                           '  - Double XP: Temporary XP boost for all players\n'
                           '  - Weather Events: Dense fog affecting visibility/combat',
            'syntax': 'events',
            'title': 'World Events'},
 'furnish': {'category': 'command',
             'description': 'View or install furniture in your house.\n'
                            'Alias for \'house furnish\'. Must be inside your house.',
             'syntax': 'house furnish [item]',
             'title': 'Furnish'},
 'hug': {'category': 'command', 'description': 'Hug someone.', 'syntax': 'hug', 'title': 'Hug'},
 'hunters_mark': {'category': 'skill',
                  'classes': ['ranger'],
                  'description': "Hunter's Mark — Mark a target as prey.\n\n"
                                 'MECHANICS:\n'
                                 '- +10% damage to marked target from all your attacks\n'
                                 '- +5 bonus Focus per hit on marked target\n'
                                 '- Free (no Focus cost)\n'
                                 '- Toggle: use again on same target to remove\n'
                                 '- Only one mark active at a time\n\n'
                                 'TALENT SYNERGIES:\n'
                                 "- Predator's Mark: also reduces target's armor\n\n"
                                 'STRATEGY:\n'
                                 '- Always mark before engaging — it\'s free!\n'
                                 '- The +5 Focus/hit helps fuel Aimed Shot and Rapid Fire\n\n'
                                 'See also: HELP FOCUS, HELP AIMED_SHOT, HELP RANGER',
                  'syntax': 'hunters_mark [target]',
                  'title': "Hunter's Mark"},
 'ice_armor': {'category': 'spell',
               'classes': ['mage'],
               'description': 'Ice Armor\n'
                              'TARGET: defensive\n'
                              '\n'
                              'CASTING:\n'
                              "- Use `cast 'ice armor'`.\n"
                              '- Mana cost applies per cast.',
               'level': 1,
               'mana': 45,
               'syntax': "cast 'ice armor'",
               'title': 'Ice Armor'},
 'idea': {'category': 'command',
          'description': 'Suggest an idea. Usage: idea <your suggestion>',
          'syntax': 'idea <your suggestion>',
          'title': 'Idea'},
 'identify': {'category': 'spell',
              'classes': ['mage'],
              'description': 'Identify\n'
                             'TARGET: object\n'
                             '\n'
                             'CASTING:\n'
                             "- Use `cast 'identify'`.\n"
                             '- Mana cost applies per cast.',
              'level': 1,
              'mana': 20,
              'syntax': "cast 'identify'",
              'title': 'Identify'},
 'ignorepain': {'category': 'command',
                'description': 'Absorb incoming damage with pure willpower.',
                'syntax': 'ignorepain',
                'title': 'Ignorepain'},
 'imbue': {'category': 'command',
           'description': 'Imbue a corpse with soulstone power. Usage: imbue [corpse]',
           'syntax': 'imbue [corpse]',
           'title': 'Imbue'},
 'immlist': {'category': 'command',
             'description': 'List all immortals (admin accounts).\n\nUsage: immlist',
             'syntax': 'immlist',
             'title': 'Immlist'},
 'info': {'category': 'command',
          'description': 'Display game information for new players.',
          'syntax': 'info',
          'title': 'Info'},
 'interrupt': {'category': 'command',
               'description': 'Break an enemy wind-up before it lands.\n'
                              '\n'
                              'When a foe begins an interruptible cast or hex (watch for the\n'
                              '⚠ telegraph line), INTERRUPT slams into them to stop it cold.\n'
                              '\n'
                              'MECHANICS:\n'
                              '- Works on any declared cast/hex marked interruptible\n'
                              '- Chance scales with your kick skill\n'
                              '- Cooldown: 20s on success, 8s on a miss\n'
                              '- Also works on boss telegraphed casts\n'
                              '\n'
                              'See also: BRACE, SIDESTEP',
               'syntax': 'interrupt',
               'title': 'Interrupt'},
 'barricade': {'category': 'command',
               'description': 'Brace a closed door so nothing opens it for a while.\n'
                              '\n'
                              'The classic escape: slam the door on your pursuers and pile\n'
                              'everything you can find against it (~90s hold, costs 15 move).\n'
                              'A mighty BASH can still break through.\n'
                              '\n'
                              'See also: SEAL, BASH <direction>',
               'syntax': 'barricade <direction>',
               'title': 'Barricade'},
 'seal': {'category': 'command',
          'description': 'Seal a closed door with arcane sigils (casters, 20 mana).\n'
                         '\n'
                         'Holds ~2 minutes against anything short of a mighty bash.\n'
                         'Mages, necromancers, clerics and paladins know the rites.\n'
                         '\n'
                         'See also: BARRICADE, BASH <direction>',
          'syntax': 'seal <direction>',
          'title': 'Seal'},
 'caltrops': {'category': 'command',
              'description': 'Thief: scatter caltrops across the ground.\n'
                             '\n'
                             'The next hostile through here is hobbled and hurt. Lasts ~5\n'
                             'minutes or until sprung. Prepare a fight, or cover an escape.\n'
                             '\n'
                             'See also: SNARE, SEARCH, DISARM',
              'syntax': 'caltrops',
              'title': 'Caltrops'},
 'snare': {'category': 'command',
           'description': 'Ranger: rig a spring-snare across the approach.\n'
                          '\n'
                          'The next hostile through here is yanked off its feet and held\n'
                          'for two rounds. Lasts ~5 minutes or until sprung.\n'
                          '\n'
                          'See also: CALTROPS, SEARCH, DISARM',
           'syntax': 'snare',
           'title': 'Snare'},
 'swing': {'category': 'command',
           'description': 'Time your attack to the combat rhythm.\n'
                          '\n'
                          'Call SWING in the final stretch of the round (the gold window\n'
                          'on the round bar) and your next attack lands PERFECTLY:\n'
                          '\n'
                          'MECHANICS:\n'
                          '- Perfect strike: +30% damage and double poise damage\n'
                          '- Mistime it and you are off-balance for the rest of the round\n'
                          '- Fill an enemy\'s poise and they are STAGGERED: they lose a\n'
                          '  round and take +50% damage while reeling\n'
                          '\n'
                          'See also: EVADE, BRACE, SIDESTEP',
           'syntax': 'swing',
           'title': 'Swing (perfect timing)'},
 'evade': {'category': 'command',
           'description': 'Slip out of a marked danger zone before an area attack lands.\n'
                          '\n'
                          'When a hulking foe winds up a sweeping area attack, get clear\n'
                          'and EVADE just before it lands to avoid it entirely.\n'
                          '\n'
                          'MECHANICS:\n'
                          '- Only works against declared AREA attacks (⚠ sweeping blows)\n'
                          '- Call it in the last moments of the wind-up, not too early\n'
                          '- You forfeit your own attack that round (all-in on movement)\n'
                          '- Web client: simply WALK out of the red zone — it evades for you\n'
                          '\n'
                          'See also: SWING, BRACE, SIDESTEP',
           'syntax': 'evade',
           'title': 'Evade'},
 'brace': {'category': 'command',
           'description': 'Plant your feet against an incoming declared attack.\n'
                          '\n'
                          'When a foe winds up a heavy blow or AoE (watch for the ⚠\n'
                          'telegraph line), BRACE to weather it.\n'
                          '\n'
                          'MECHANICS:\n'
                          '- Halves the damage of the declared heavy/AoE hit\n'
                          '- Resists its stun, fear or paralysis\n'
                          '- Costs 10 move · Cooldown: 12s\n'
                          '- You keep attacking normally while braced\n'
                          '\n'
                          'See also: SIDESTEP, INTERRUPT',
           'syntax': 'brace',
           'title': 'Brace'},
 'sidestep': {'category': 'command',
              'description': 'Read an enemy wind-up and slip it entirely.\n'
                             '\n'
                             'When a foe winds up a heavy blow or AoE (watch for the ⚠\n'
                             'telegraph line), SIDESTEP to attempt a full evasion.\n'
                             '\n'
                             'MECHANICS:\n'
                             '- Success scales with your dodge skill and DEX\n'
                             '- On success the declared hit misses you completely\n'
                             '- You forfeit your own attack that round (all-in on evasion)\n'
                             '- Cooldown: 16s\n'
                             '\n'
                             'See also: BRACE, INTERRUPT',
              'syntax': 'sidestep',
              'title': 'Sidestep'},
 'intimidate': {'category': 'skill',
                'classes': ['warrior'],
                'description': 'A class skill. Use it to gain tactical advantages in combat or utility.\n'
                               '\n'
                               'TRAINING:\n'
                               '- Grows as you use it, up to 85%.\n'
                               '- Your guild\'s trainer teaches the rest.',
                'syntax': 'intimidate',
                'title': 'Intimidate'},
 'inventory': {'category': 'command', 'description': 'Show inventory.', 'syntax': 'inventory', 'title': 'Inventory'},
 'invis': {'category': 'command',
           'description': 'List all invisible players/mobs in room (immortal only).\n\nUsage: invis',
           'syntax': 'invis',
           'title': 'Invis'},
 'invisibility': {'category': 'spell',
                  'classes': ['bard', 'mage'],
                  'description': '\n'
                                 'Become invisible to enemies.\n'
                                 '\n'
                                 'MECHANICS:\n'
                                 '- Breaks on attack\n'
                                 '- Improves stealth rolls\n',
                  'level': 1,
                  'mana': 35,
                  'syntax': "cast 'invisibility'",
                  'title': 'Invisibility'},
 'journal': {'category': 'command',
             'description': 'Review your discovery journal.\n'
                            '\n'
                            'Usage:\n'
                            '    journal              - Show journal overview and recent entries\n'
                            '    journal stats        - Show discovery statistics\n'
                            '    journal lore         - Show lore entries\n'
                            '    journal secrets      - Show discovered secrets\n'
                            "    journal npcs         - Show NPCs you've met\n"
                            '    journal areas        - Show discovered areas\n'
                            '    journal read <num>   - Read a specific entry\n'
                            '    journal all          - Show all entries',
             'syntax': 'journal              - Show journal overview and recent entries',
             'title': 'Journal'},
 'judgment': {'category': 'command', 'description': 'Ranged holy strike.', 'syntax': 'judgment', 'title': 'Judgment'},
 'junk': {'category': 'command',
          'description': 'Destroy an item. Usage: junk <item>',
          'syntax': 'junk <item>',
          'title': 'Junk'},
 'kick': {'category': 'skill',
          'classes': ['warrior'],
          'description': 'Kick a target for extra damage.\n\nMECHANICS:\n- Usable in combat\n- Scales with STR\n',
          'syntax': 'kick',
          'title': 'Kick'},
 'kidneyshot': {'category': 'command',
                'description': 'Stun finisher that uses 4+ combo points.',
                'syntax': 'kidneyshot',
                'title': 'Kidneyshot'},
 'kill': {'category': 'command', 'description': 'Attack a target.', 'syntax': 'kill', 'title': 'Kill'},
 'killing_spree': {'category': 'command',
                   'description': 'Rapidly strike multiple enemies.',
                   'syntax': 'killing_spree',
                   'title': 'Killing Spree'},
 'knock': {'category': 'command',
           'description': 'Knock on a door. Usage: knock <direction>',
           'syntax': 'knock <direction>',
           'title': 'Knock'},
 'label': {'category': 'command',
           'description': 'Label a target for quick targeting in combat.\n'
                          '\n'
                          'Usage:\n'
                          '    label                    - Show all current labels\n'
                          '    label <target> <name>    - Label a target (e.g., label warrior DEAD)\n'
                          '    label clear              - Clear all labels\n'
                          '    label clear <name>       - Clear specific label\n'
                          '\n'
                          'Then use the label in commands: kill DEAD, cast fireball DEAD\n'
                          'Labels are case-insensitive and session-only (not saved).',
           'syntax': 'label                    - Show all current labels',
           'title': 'Label'},
 'laugh': {'category': 'command', 'description': 'Laugh.', 'syntax': 'laugh', 'title': 'Laugh'},
 'layhands': {'category': 'command',
              'description': 'Use lay on hands to heal yourself or an ally.',
              'syntax': 'layhands',
              'title': 'Layhands'},
 'leaderboard': {'category': 'command',
                 'description': 'View the server leaderboards.\n'
                                '\n'
                                'Usage: leaderboard [category]\n'
                                'Categories: level, kills, gold, deaths, achievements, quests',
                 'syntax': 'leaderboard [category]',
                 'title': 'Leaderboard'},
 'leave': {'category': 'command',
           'description': 'Leave a building to go outside. Usage: leave',
           'syntax': 'leave',
           'title': 'Leave'},
 'levels': {'category': 'command',
            'description': 'Show experience required for each level.',
            'syntax': 'levels',
            'title': 'Levels'},
 'lightning_bolt': {'category': 'spell',
                    'classes': ['mage'],
                    'description': '\n'
                                   'Strike a target with lightning.\n'
                                   '\n'
                                   'MECHANICS:\n'
                                   '- Damage scales with level\n'
                                   '- Offensive spell\n',
                    'level': 1,
                    'mana': 35,
                    'syntax': "cast 'lightning bolt' <target>",
                    'title': 'Lightning Bolt'},
 'list': {'category': 'command',
          'description': 'List items for sale in a shop. Usage: list',
          'syntax': 'list',
          'title': 'List'},
 'load': {'category': 'command',
          'description': 'Load a mob or object (immortal only).\n'
                         '\n'
                         'Usage:\n'
                         '    load mob <vnum>       - Load a mob\n'
                         '    load obj <vnum>       - Load an object to inventory\n'
                         '    load obj <vnum> room  - Load an object to room',
          'syntax': 'load mob <vnum>       - Load a mob',
          'title': 'Load'},
 'lock': {'category': 'command',
          'description': 'Lock a door or container. Usage: lock <door/container>',
          'syntax': 'lock <door/container>',
          'title': 'Lock'},
 'look': {'category': 'command', 'description': 'Look at the room or something.', 'syntax': 'look', 'title': 'Look'},
 'loot': {'category': 'command',
          'description': 'Loot items from a corpse. Supports numbered targeting (e.g., loot 2.corpse)',
          'syntax': 'loot',
          'title': 'Loot'},
 'lore': {'category': 'skill',
          'classes': ['bard'],
          'description': 'Review discovered lore.\n'
                         '\n'
                         'TRAINING:\n'
                         '- Grows as you use it, up to 85%.\n'
                         '- Your guild\'s trainer teaches the rest.',
          'syntax': 'lore',
          'title': 'Lore'},
 'mage': {'category': 'class',
          'description': 'The Mage class - master of arcane, fire, and frost magic.\n'
                         '\n'
                         'CORE MECHANIC - ARCANE CHARGES:\n'
                         '  Spells build Arcane Charges (max 5).\n'
                         '  Each charge: +8% spell damage, +10% mana cost.\n'
                         '  Risk/reward: more power costs more mana!\n\n'
                         '  Spending charges:\n'
                         '    Arcane Barrage: consume all for burst damage\n'
                         '    Evocation: reset charges + restore 30% mana\n'
                         '    Arcane Blast: damage + generate charge\n'
                         '\n'
                         'TALENT TREES:\n'
                         '  Fire - Burst damage, DoTs, ignite effects\n'
                         '  Frost - Control, slows, roots, shatter combos\n'
                         '  Arcane - Charge mastery, mana efficiency, raw power\n'
                         '\n'
                         'See also: HELP ARCANE_CHARGES, HELP ARCANE_BARRAGE',
          'title': 'Mage'},
 'magic_missile': {'category': 'spell',
                   'classes': ['mage'],
                   'description': 'Magic Missile\n'
                                  'TARGET: offensive\n'
                                  'DAMAGE: 1d4+1 + 1/level\n'
                                  '\n'
                                  'CASTING:\n'
                                  "- Use `cast 'magic missile'`.\n"
                                  '- Mana cost applies per cast.',
                   'level': 1,
                   'mana': 10,
                   'syntax': "cast 'magic missile' <target>",
                   'title': 'Magic Missile'},
 'mana_shield': {'category': 'spell',
                 'classes': ['mage'],
                 'description': 'Mana Shield\n'
                                'TARGET: self\n'
                                '\n'
                                'CASTING:\n'
                                "- Use `cast 'mana shield'`.\n"
                                '- Mana cost applies per cast.',
                 'level': 1,
                 'mana': 50,
                 'syntax': "cast 'mana shield'",
                 'title': 'Mana Shield'},
 'map': {'category': 'command',
         'description': 'Display ASCII map.\n'
                        '\n'
                        'Usage:\n'
                        '    map        - Show local explored map\n'
                        '    map full   - Show entire explored area\n'
                        '    map zone   - Show explored rooms in current zone',
         'syntax': 'map        - Show local explored map',
         'title': 'Map'},
 'mapurl': {'category': 'command',
            'description': 'Show the web map URL for this player.',
            'syntax': 'mapurl',
            'title': 'Mapurl'},
 'mark': {'category': 'command',
          'description': 'Mark a target for death, increasing damage against them.',
          'syntax': 'mark',
          'title': 'Mark'},
 'mark': {'category': 'skill',
          'classes': ['assassin'],
          'description': '\n'
                         'Mark a target to begin building Intel (Assassin only).\n'
                         '\n'
                         'Usage: mark <target>\n'
                         '       mark           (show current Intel status)\n'
                         '\n'
                         'EFFECTS:\n'
                         '- Designates target for Intel tracking\n'
                         '- Resets Intel to 0 (switching targets costs Intel!)\n'
                         '- Each hit on marked target builds +1 Intel\n'
                         '- Backstab from stealth builds +3 Intel\n'
                         '- Can only mark one target at a time\n'
                         '- Intel persists through Vanish\n'
                         '\n'
                         'STRATEGY:\n'
                         '- Mark your target BEFORE engaging\n'
                         '- Build to Intel 3 for Expose, 6 for Vital, 10 for Execute\n'
                         '- Avoid re-marking mid-fight (resets all Intel!)\n'
                         '\n'
                         'See also: HELP INTEL, HELP EXPOSE, HELP VITAL\n',
          'syntax': 'mark <target>',
          'title': 'Mark'},
 'mark_target': {'category': 'skill',
                 'classes': ['assassin'],
                 'description': 'See HELP MARK - the mark command now uses the Intel system.\n',
                 'syntax': 'mark <target>',
                 'title': 'Mark Target (see MARK)'},
 'marked_for_death': {'category': 'command',
                      'description': 'Mark a target for lethal focus.',
                      'syntax': 'marked_for_death',
                      'title': 'Marked For Death'},
 'marked_shot': {'category': 'command',
                 'description': 'Fire a powerful shot at a marked target for bonus damage.',
                 'syntax': 'marked_shot',
                 'title': 'Marked Shot'},
 'mass_charm': {'category': 'spell',
                'classes': ['bard'],
                'description': 'Mass Charm\n'
                               'TARGET: room\n'
                               '\n'
                               'CASTING:\n'
                               "- Use `cast 'mass charm'`.\n"
                               '- Mana cost applies per cast.',
                'level': 1,
                'mana': 100,
                'syntax': "cast 'mass charm'",
                'title': 'Mass Charm'},
 'medit': {'category': 'command',
           'description': 'Online mob editor (immortal only).',
           'syntax': 'medit',
           'title': 'Medit'},
 'meteor_swarm': {'category': 'spell',
                  'classes': ['mage'],
                  'description': 'Meteor Swarm — Call down a devastating barrage of meteors.\n\n'
                                 'MECHANICS:\n'
                                 '- Heavy single-target damage\n'
                                 '- Generates +1 Arcane Charge on cast\n'
                                 '- Damage boosted by Arcane Charges (+8% per charge)\n'
                                 '- Mana: 80 (increased by +10% per Arcane Charge)\n\n'
                                 'STRATEGY:\n'
                                 '- One of the mage\'s most powerful offensive spells\n'
                                 '- Stack charges with Arcane Blast, then Meteor Swarm\n'
                                 '- Follow up with Arcane Barrage to consume charges\n\n'
                                 'See also: HELP ARCANE_CHARGES, HELP ARCANE_BARRAGE, HELP MAGE',
                  'level': 1,
                  'mana': 80,
                  'syntax': "cast 'meteor swarm' <target>",
                  'title': 'Meteor Swarm'},
 'minimap': {'category': 'command',
             'description': 'Display a compact ASCII minimap centered on the player.',
             'syntax': 'minimap',
             'title': 'Minimap'},
 'minions': {'category': 'command',
             'description': 'List your summoned minions (undead, summons). Usage: minions',
             'syntax': 'minions',
             'title': 'Minions'},
 'mirror_image': {'category': 'spell',
                  'classes': ['mage'],
                  'description': 'Mirror Image\n'
                                 'TARGET: self\n'
                                 '\n'
                                 'CASTING:\n'
                                 "- Use `cast 'mirror image'`.\n"
                                 '- Mana cost applies per cast.',
                  'level': 1,
                  'mana': 40,
                  'syntax': "cast 'mirror image'",
                  'title': 'Mirror Image'},
 'mlist': {'category': 'command',
           'description': 'List all mobs in a zone (immortal only).\n'
                          '\n'
                          'Usage:\n'
                          '    mlist           - List mobs in current zone\n'
                          '    mlist <zone>    - List mobs in specified zone',
           'syntax': 'mlist           - List mobs in current zone',
           'title': 'Mlist'},
 'mload': {'category': 'command',
           'description': 'Load a mob into the current room (immortal only).\n\nUsage: mload <vnum>',
           'syntax': 'mload <vnum>',
           'title': 'Mload'},
 'mock': {'category': 'command',
          'description': 'Taunt an enemy with vicious mockery, debuffing them.',
          'syntax': 'mock',
          'title': 'Mock'},
 'mockery': {'category': 'skill',
             'classes': ['bard'],
             'description': '\n'
                            'Psychic taunt that damages and debuffs.\n'
                            '\n'
                            'MECHANICS:\n'
                            '- Deals psychic damage\n'
                            '- Reduces hitroll briefly\n',
             'syntax': 'mockery',
             'title': 'Mockery'},
 'mortal_strike': {'category': 'command',
                   'description': 'Heavy strike that wounds the target.',
                   'syntax': 'mortal_strike',
                   'title': 'Mortal Strike'},
 'motd': {'category': 'command', 'description': 'Display the Message of the Day.', 'syntax': 'motd', 'title': 'Motd'},
 'mount': {'category': 'command',
           'description': 'Mount a creature you own.\n\n'
                          'With no arguments, lists your owned mounts. MOUNT LAST mounts the one\n'
                          'you last rode (else your fastest). In the 3D client press R (or the\n'
                          'horseshoe in the menu, or right-click yourself) to mount or dismount.\n'
                          'Mounts increase movement speed and may provide combat bonuses.\n\n'
                          'Riding makes you travel faster (the 3D hero runs faster) and halves\n'
                          'what moving costs you; a hungry mount carries you slower. Haste stacks.\n\n'
                          'MOUNT TYPES (travel speed):\n'
                          '  Donkey / Pony   - +15% / +20%, 600 / 900 gold (stables)\n'
                          '  Horse           - +35%, 2,000 gold (stables)\n'
                          '  War Horse       - +30%, +2 damroll, stays mounted in combat, 5,000 gold\n'
                          '  Nightmare       - +50%, fire aura, Dark Brotherhood exalted\n'
                          '  Moonstag        - +45%, Elven Court exalted\n'
                          '  Stoneboar       - +30%, +1 damroll, fights with you, Dwarven Kingdom exalted\n'
                          '  Guard Warhorse  - +30%, +3 damroll, fights with you, Garathorm Guard exalted\n'
                          '  Merchant Camel  - +25%, never tires, Merchant League exalted\n'
                          '  Griffin         - +60%, flies over rough ground, won from the Roc Matriarch\n'
                          '  Clockwork Steed - +50%, never tires, won from the Carillon Engine\n\n'
                          'You are automatically dismounted when entering combat unless your mount\n'
                          'fights with you. Use FEED to keep loyalty up; RIDE to speedwalk.\n\n'
                          'See also: dismount, stable, feed, mounts, ride',
           'syntax': 'mount [name | last]',
           'title': 'Mount'},
 'mounts': {'category': 'command',
            'description': 'List your owned mounts. Same as typing "mount" with no arguments.',
            'syntax': 'mounts',
            'title': 'Mounts'},
 'feed': {'category': 'command',
          'description': 'Feed your mount to restore loyalty.\n\n'
                         'Uses a food item from inventory, or costs 10 gold if you have no food.\n'
                         'Mount loyalty decays over time. Low loyalty reduces speed bonuses.\n\n'
                         'See also: mount, stable',
          'syntax': 'feed',
          'title': 'Feed'},
 'move': {'category': 'command', 'description': 'Move in a direction.', 'syntax': 'move', 'title': 'Move'},
 'mute': {'category': 'command',
          'description': "Mute a player so they can't talk (immortal only).\n\nUsage: mute <player>",
          'syntax': 'mute <player>',
          'title': 'Mute'},
 'mutilate': {'category': 'command',
              'description': 'Dual strike that builds combo points.',
              'syntax': 'mutilate',
              'title': 'Mutilate'},
 'necromancer': {'category': 'class',
                 'description': 'Necromancers wield death magic, draining life and commanding the dead. They\n'
                                'excel at sustained pressure, debuffs, and undead minions, but are fragile\n'
                                'in direct melee.\n'
                                '\n'
                                'PLAYSTYLE:\n'
                                '- Open with debuffs (blindness, poison) and drain effects\n'
                                '- Use undead minions for frontline pressure\n'
                                '- Sustain with life drain and mana management\n'
                                '\n'
                                'RESOURCE LOOP:\n'
                                '- Mana fuels most damage; conserve with efficient drains\n'
                                '- Soul fragments extend undead duration (if available)\n'
                                '\n'
                                'PETS / MINIONS:\n'
                                '- Animate Dead creates temporary undead\n'
                                '- Undead minions persist for their duration and assist in combat\n'
                                '\n'
                                'DEFENSES:\n'
                                '- Armor/Shield spells improve survivability\n'
                                '- Keep distance; rely on control and minions\n'
                                '\n'
                                'SKILL TREE / PROGRESSION:\n'
                                '- Skills/spells unlock in the order listed for your class.\n'
                                '- Unlock tiers at levels: 2, 3, 5, 7, 10, 15, 20, 25, 30.\n'
                                '\n'
                                'SPELL ORDER:\n'
                                '- 1. Chill Touch\n'
                                '- 2. Animate Dead\n'
                                '- 3. Vampiric Touch\n'
                                '- 4. Enervation\n'
                                '- 5. Death Grip\n'
                                '- 6. Finger Of Death\n'
                                '- 7. Energy Drain\n'
                                '- 8. Poison\n'
                                '- 9. Weaken\n'
                                '- 10. Blindness\n'
                                '- 11. Fear\n'
                                '- 12. Armor\n'
                                '- 13. Shield\n'
                                '- 14. Protection From Good\n'
                                '\n'
                                'TRAINING:\n'
                                '- Grows as you use it, up to 85%; your guild\'s trainer teaches the rest.',
                 'title': 'Necromancer (Legacy)'},
 'necromancer': {'category': 'class',
                 'description': 'The Necromancer class.\n'
                                '\n'
                                'CORE MECHANIC - SOUL SHARDS:\n'
                                '  Necromancers harvest souls from dying enemies.\n'
                                '  Kill an enemy: +1 Soul Shard (undead kills: +2)\n'
                                '  Assist kill: +1 if you dealt damage\n'
                                '  Cap: 10 Soul Shards\n'
                                '  Passive: +5% spell damage per Shard held (up to +50%)\n'
                                '\n'
                                'SOUL SHARD ABILITIES:\n'
                                '  soul_bolt   (2 Shards) - 2x spell damage as shadow. 10s CD.\n'
                                '  drain_soul  (3 Shards) - 1.5x spell damage, heals same. 15s CD.\n'
                                '  bone_shield (4 Shards) - Absorbs 3 hits (500 each). 60s CD.\n'
                                '  soul_reap   (8 Shards) - Execute below 25% or 4x damage. 90s CD.\n'
                                '\n'
                                'TALENT TREES:\n'
                                '  Unholy - Minions, disease, army\n'
                                '  Blood  - Self-sustain, life drain\n'
                                '  Frost  - Control, burst damage\n'
                                '\n'
                                'See also: HELP SOUL_SHARDS, HELP SOUL_BOLT',
                 'title': 'Necromancer'},
 'newgameplus': {'category': 'command',
                 'description': 'Start a New Game+ cycle after completing the main story.',
                 'syntax': 'newgameplus',
                 'title': 'Newgameplus'},
 'news': {'category': 'command', 'description': 'Alias for updates command.', 'syntax': 'news', 'title': 'News'},
 'nod': {'category': 'command', 'description': 'Nod.', 'syntax': 'nod', 'title': 'Nod'},
 'nohassle': {'category': 'command',
              'description': 'Toggle immunity to mob attacks (immortal only).\n\nUsage: nohassle',
              'syntax': 'nohassle',
              'title': 'Nohassle'},
 'norepeat': {'category': 'command',
              'description': 'Toggle echoing of your own communication.',
              'syntax': 'norepeat',
              'title': 'Norepeat'},
 'north': {'category': 'command',
           'description': 'No additional details available yet.',
           'syntax': 'north',
           'title': 'North'},
 'noshout': {'category': 'command',
             'description': 'Toggle blocking of shouts and hollers.',
             'syntax': 'noshout',
             'title': 'Noshout'},
 'notell': {'category': 'command',
            'description': 'Toggle blocking of tells from other players.',
            'syntax': 'notell',
            'title': 'Notell'},
 'notick': {'category': 'command',
            'description': 'Alias for tick - toggle tick notifications.',
            'syntax': 'notick',
            'title': 'Notick'},
 'oedit': {'category': 'command',
           'description': 'Online object editor (immortal only).',
           'syntax': 'oedit',
           'title': 'Oedit'},
 'olist': {'category': 'command',
           'description': 'List all objects in a zone (immortal only).\n'
                          '\n'
                          'Usage:\n'
                          '    olist           - List objects in current zone\n'
                          '    olist <zone>    - List objects in specified zone',
           'syntax': 'olist           - List objects in current zone',
           'title': 'Olist'},
 'oload': {'category': 'command',
           'description': 'Load an object into the room or your inventory (immortal only).\n'
                          '\n'
                          'Usage: oload <vnum> [room]',
           'syntax': 'oload <vnum> [room]',
           'title': 'Oload'},
 'open': {'category': 'command',
          'description': 'Open a door or container. Usage: open <door/container>',
          'syntax': 'open <door/container>',
          'title': 'Open'},
 'order': {'category': 'command',
           'description': 'Order your companion or pet. Usage: order <action> [target] OR order <pet> <action> '
                          '[target]',
           'syntax': 'order <action> [target] OR order <pet> <action> [target]',
           'title': 'Order'},
 'overpower': {'category': 'command',
               'description': 'Quick counterattack.',
               'syntax': 'overpower',
               'title': 'Overpower'},
 'paladin': {'category': 'class',
             'description': 'The Paladin class.\n'
                            '\n'
                            'CORE MECHANIC - HOLY POWER:\n'
                            '  Paladins build Holy Power (0-5) through righteous combat.\n'
                            '  Melee hits: 25% chance +1 Holy Power\n'
                            '  Smite/Bash: guaranteed +1 Holy Power\n'
                            '  Healing an ally: +1 Holy Power\n'
                            '\n'
                            'HOLY POWER SPENDERS:\n'
                            '  templars_verdict (3 HP) - 2x weapon damage + holy bonus\n'
                            '  word_of_glory    (3 HP) - Heal self for 30% max HP\n'
                            '  divine_storm     (5 HP) - AoE holy damage. 30s CD.\n'
                            '\n'
                            'OATH SYSTEM:\n'
                            '  oath vengeance - +15% damage, -10% healing\n'
                            '  oath devotion  - +20% healing, +10% DR\n'
                            '  oath justice   - +10% damage, +10% healing\n'
                            '\n'
                            'TALENT TREES:\n'
                            '  Holy       - Healing, support\n'
                            '  Protection - Tanking, shields\n'
                            '  Retribution - Damage, Holy Power generation\n'
                            '\n'
                            'See also: HELP HOLY_POWER, HELP OATH, HELP TEMPLARS_VERDICT',
             'title': 'Paladin'},
 'parry': {'category': 'skill',
           'classes': ['warrior'],
           'description': 'Passive chance to deflect attacks when wielding a weapon.',
           'syntax': 'parry',
           'title': 'Parry'},
 'pat': {'category': 'command', 'description': 'Pat someone.', 'syntax': 'pat', 'title': 'Pat'},
 'peace': {'category': 'command',
           'description': 'Stop all combat in the current room (immortal only).\n\nUsage: peace',
           'syntax': 'peace',
           'title': 'Peace'},
 'perform': {'category': 'command',
             'description': '\n'
                            'Begin a bard performance.\n'
                            '\n'
                            'MECHANICS:\n'
                            '- Ongoing song with mana drain\n'
                            '- Moving cancels performance\n',
             'syntax': 'perform',
             'title': 'Perform'},
 'pet': {'category': 'command', 'description': 'Show your pets and companions.', 'syntax': 'pet', 'title': 'Pet'},
 'pets': {'category': 'command',
          'description': 'Manage all your pets. Usage: pets [list|report|assist|recall|dismiss all]',
          'syntax': 'pets [list|report|assist|recall|dismiss all]',
          'title': 'Pets'},
 'pick': {'category': 'command',
          'description': 'Pick a lock (Thief skill). Usage: pick <door/container>',
          'syntax': 'pick <door/container>',
          'title': 'Pick'},
 'pick_lock': {'category': 'skill',
               'classes': ['bard', 'thief'],
               'description': '\n'
                              'Pick locks on doors/containers.\n'
                              '\n'
                              'REQUIREMENTS:\n'
                              '- Lockpick skill\n'
                              '\n'
                              'MECHANICS:\n'
                              '- Skill roll vs difficulty\n'
                              '- Failure leaves lock intact\n',
               'syntax': 'pick_lock',
               'title': 'Pick Lock'},
 'poison': {'category': 'spell',
            'classes': ['necromancer'],
            'description': 'Poison\n'
                           'TARGET: offensive\n'
                           '\n'
                           'CASTING:\n'
                           "- Use `cast 'poison'`.\n"
                           '- Mana cost applies per cast.',
            'level': 1,
            'mana': 25,
            'syntax': "cast 'poison' <target>",
            'title': 'Poison'},
 'poke': {'category': 'command', 'description': 'Poke someone.', 'syntax': 'poke', 'title': 'Poke'},
 'policy': {'category': 'command',
            'description': 'Display server policies and rules.',
            'syntax': 'policy',
            'title': 'Policy'},
 'ponder': {'category': 'command', 'description': 'Ponder.', 'syntax': 'ponder', 'title': 'Ponder'},
 'pour': {'category': 'command',
          'description': 'Pour liquid between containers. Usage: pour <from> <to> OR pour <from> out',
          'syntax': 'pour <from> <to> OR pour <from> out',
          'title': 'Pour'},
 'practice': {'category': 'command',
              'description': 'Your abilities and how well you know them.\n\n'
                             'You learn an ability by reaching its level (at 50%), and it grows as you use '
                             'it, up to 85% (Mastered). Past that, your guild\'s trainer teaches it to 100%, '
                             '5% at a time, for gold (or a practice session left over from before).\n\n'
                             'practice            your abilities, and when the rest arrive\n'
                             'practice <ability>  train it with your guild\'s trainer (from 85%)\n\n'
                             'A spell known well fizzles less, and every ability hits (or heals) harder '
                             'the better you know it.',
              'syntax': 'practice [ability]',
              'title': 'Practice'},
 'predators_mark': {'category': 'command',
                    'description': 'Mark a target for increased damage and tracking.',
                    'syntax': 'predators_mark',
                    'title': 'Predators Mark'},
 'preparation': {'category': 'command',
                 'description': 'Reset major cooldowns.',
                 'syntax': 'preparation',
                 'title': 'Preparation'},
 'prompt': {'category': 'command',
            'description': 'Set custom prompt. Usage: prompt <format> or prompt default',
            'syntax': 'prompt <format> or prompt default',
            'title': 'Prompt'},
 'protection_from_evil': {'category': 'spell',
                          'classes': ['cleric', 'mage', 'paladin'],
                          'description': 'Protection from Evil\n'
                                         'TARGET: defensive\n'
                                         '\n'
                                         'CASTING:\n'
                                         "- Use `cast 'protection from evil'`.\n"
                                         '- Mana cost applies per cast.',
                          'level': 1,
                          'mana': 30,
                          'syntax': "cast 'protection from evil'",
                          'title': 'Protection From Evil'},
 'protection_from_good': {'category': 'spell',
                          'classes': ['mage', 'necromancer'],
                          'description': 'Protection from Good\n'
                                         'TARGET: defensive\n'
                                         '\n'
                                         'CASTING:\n'
                                         "- Use `cast 'protection from good'`.\n"
                                         '- Mana cost applies per cast.',
                          'level': 1,
                          'mana': 30,
                          'syntax': "cast 'protection from good'",
                          'title': 'Protection From Good'},
 'pull': {'category': 'command', 'description': 'Pull a lever for lever puzzles.', 'syntax': 'pull', 'title': 'Pull'},
 'purge': {'category': 'command',
           'description': 'Remove all mobs and objects from the room, or a specific target (immortal only).\n'
                          '\n'
                          'Usage: \n'
                          '    purge           - Remove all mobs/objects in room\n'
                          '    purge <target>  - Remove specific mob/object',
           'syntax': 'purge           - Remove all mobs/objects in room',
           'title': 'Purge'},
 'touch': {'category': 'command',
           'description': 'Touch something in the room, such as a mirror in a puzzle room. Usage: touch <thing>',
           'syntax': 'touch <thing>',
           'title': 'Touch'},
 'push': {'category': 'command',
          'description': 'Push a symbol or object for puzzle interactions.',
          'syntax': 'push',
          'title': 'Push'},
 'put': {'category': 'command',
         'description': 'Put an item into a container. Usage: put <item> <container> or put all <container>',
         'syntax': 'put <item> <container> or put all <container>',
         'title': 'Put'},
 'qsay': {'category': 'command',
          'description': 'Say something on the quest channel. Usage: qsay <message>',
          'syntax': 'qsay <message>',
          'title': 'Qsay'},
 'quaff': {'category': 'command',
           'description': 'Drink a potion. Usage: quaff <potion>',
           'syntax': 'quaff <potion>',
           'title': 'Quaff'},
 'quest': {'category': 'command', 'description': 'Manage quests.', 'syntax': 'quest', 'title': 'Quest'},
 'questlog': {'category': 'command',
              'description': 'Show quest log (alias for quest log).',
              'syntax': 'questlog',
              'title': 'Questlog'},
 'quit': {'category': 'command', 'description': 'Quit the game.', 'syntax': 'quit', 'title': 'Quit'},
 'rage': {'category': 'command', 'description': 'Display current rage level.', 'syntax': 'rage', 'title': 'Rage'},
 'raise': {'category': 'command',
           'description': 'Raise a necromancer servant. Usage: raise <knight|wraith|lich|stalker>',
           'syntax': 'raise <knight|wraith|lich|stalker>',
           'title': 'Raise'},
 'rampage': {'category': 'command',
             'description': 'Attack all enemies in the room.',
             'syntax': 'rampage',
             'title': 'Rampage'},
 'ranger': {'category': 'class',
            'description': 'The Ranger class - hunter, tracker, and beast master.\n'
                           '\n'
                           'CORE MECHANIC - FOCUS:\n'
                           '  Build Focus through steady combat (max 100).\n'
                           '  +10 per hit, +5 passive per round, +15 on dodge.\n'
                           '  At 100 Focus, next ability costs 50% less.\n\n'
                           '  Abilities:\n'
                           '    Aimed Shot (30): 2.5x damage, guaranteed hit\n'
                           '    Kill Command (25): pet attacks for 2x damage\n'
                           '    Rapid Fire (50): triple attack this round\n'
                           '    Hunter\'s Mark (free): +10% damage, +5 Focus/hit\n'
                           '\n'
                           'TALENT TREES:\n'
                           '  Beast Mastery - Pet power, bonding, spirit beasts\n'
                           '  Marksmanship - Ranged burst, precision, sniper skills\n'
                           '  Survival - Traps, self-sustain, wilderness utility\n'
                           '\n'
                           'See also: HELP FOCUS_GUIDE, HELP AIMED_SHOT',
            'title': 'Ranger'},
 'rapid_shot': {'category': 'command',
                'description': 'Fire multiple arrows in quick succession.',
                'syntax': 'rapid_shot',
                'title': 'Rapid Shot'},
 'read': {'category': 'command',
          'description': 'Read a book, scroll, or readable item.',
          'syntax': 'read',
          'title': 'Read'},
 'recall': {'category': 'command',
            'description': 'Recall to your recall point (temple).\n'
                           '\n'
                           'Usage:\n'
                           '    recall     - Teleport to your recall point\n'
                           '    recall set - Set current location as recall point',
            'syntax': 'recall     - Teleport to your recall point',
            'title': 'Recall'},
 'recite': {'category': 'command',
            'description': 'Read a scroll. Usage: recite <scroll> [target]',
            'syntax': 'recite <scroll> [target]',
            'title': 'Recite'},
 'redit': {'category': 'command',
           'description': 'Online room editor (immortal only).',
           'syntax': 'redit',
           'title': 'Redit'},
 'relight': {'category': 'command',
             'description': 'Relight your light source. Usage: relight light',
             'syntax': 'relight light',
             'title': 'Relight'},
 'remove': {'category': 'command',
            'description': "Remove worn equipment or 'remove all' to remove everything.",
            'syntax': 'remove',
            'title': 'Remove'},
 'remove_curse': {'category': 'spell',
                  'classes': ['cleric'],
                  'description': 'Remove Curse\n'
                                 'TARGET: defensive\n'
                                 '\n'
                                 'CASTING:\n'
                                 "- Use `cast 'remove curse'`.\n"
                                 '- Mana cost applies per cast.',
                  'level': 1,
                  'mana': 35,
                  'syntax': "cast 'remove curse'",
                  'title': 'Remove Curse'},
 'remove_poison': {'category': 'spell',
                   'classes': ['cleric'],
                   'description': 'Remove Poison\n'
                                  'TARGET: defensive\n'
                                  '\n'
                                  'CASTING:\n'
                                  "- Use `cast 'remove poison'`.\n"
                                  '- Mana cost applies per cast.',
                   'level': 1,
                   'mana': 30,
                   'syntax': "cast 'remove poison'",
                   'title': 'Remove Poison'},
 'rend': {'category': 'command', 'description': 'Apply a bleeding wound.', 'syntax': 'rend', 'title': 'Rend'},
 'rent': {'category': 'command',
          'description': 'Rent a room at the Inn to save your character and quit safely.',
          'syntax': 'rent',
          'title': 'Rent'},
 'report': {'category': 'command',
            'description': 'Report your status to the group.',
            'syntax': 'report',
            'title': 'Report'},
 'reputation': {'category': 'command',
                'description': '\n'
                               'Show your reputation standings with all factions.\n'
                               '\n'
                               'USAGE:\n'
                               '  reputation          - Show all faction standings with progress bars\n'
                               '  reputation <faction> - Show detailed info for a specific faction\n'
                               '  rep                  - Shortcut alias\n'
                               '\n'
                               'FACTIONS:\n'
                               '  Garathorm Guard    - City protectors (kill bandits/undead, guard quests)\n'
                               '  Thieves Guild     - Underground syndicate (pickpocket, steal, shady quests)\n'
                               '  Arcane Circle     - Mage scholars (identify items, kill magical creatures)\n'
                               "  Nature's Wardens  - Druids/rangers (kill undead, protect animals, forage)\n"
                               '  Dark Brotherhood  - Evil faction (kill guards, assassinate, dark rituals)\n'
                               '  Merchant League   - Traders (buy/sell large amounts, trade quests)\n'
                               '\n'
                               'REPUTATION LEVELS (0-1000 points each):\n'
                               '  Hated -> Hostile -> Unfriendly -> Neutral -> Friendly -> Honored -> Revered -> Exalted\n'
                               '\n'
                               'REWARDS BY TIER:\n'
                               '  Friendly - Discount at faction shops\n'
                               '  Honored  - Access to faction-specific quests\n'
                               '  Revered  - Faction title, special equipment\n'
                               '  Exalted  - Unique mount/pet, powerful item\n'
                               '\n'
                               'OPPOSING FACTIONS:\n'
                               '  Thieves Guild vs Garathorm Guard\n'
                               "  Dark Brotherhood vs Nature's Wardens\n"
                               '  Gaining rep with one loses rep with its rival.\n',
                'syntax': 'reputation',
                'title': 'Reputation'},
 'rescue': {'category': 'skill',
            'classes': ['paladin', 'warrior'],
            'description': '\n'
                           'Rescue an ally by pulling aggro.\n'
                           '\n'
                           'MECHANICS:\n'
                           '- Success scales with rescue skill, STR/DEX, and stance\n'
                           '- On success: attacker switches to you\n'
                           '- Short cooldown between attempts\n',
            'syntax': 'rescue',
            'title': 'Rescue'},
 'rest': {'category': 'command', 'description': 'Rest to regenerate faster.', 'syntax': 'rest', 'title': 'Rest'},
 'restore': {'category': 'command',
             'description': 'Fully restore HP/mana/move for self or a target (immortal only).\n'
                            '\n'
                            'Usage:\n'
                            '    restore         - Restore yourself\n'
                            '    restore <name>  - Restore a player',
             'syntax': 'restore         - Restore yourself',
             'title': 'Restore'},
 'resurrect': {'category': 'spell',
               'classes': ['cleric'],
               'description': 'Resurrect\n'
                              'TARGET: special\n'
                              '\n'
                              'CASTING:\n'
                              "- Use `cast 'resurrect'`.\n"
                              '- Mana cost applies per cast.',
               'level': 1,
               'mana': 150,
               'syntax': "cast 'resurrect'",
               'title': 'Resurrect'},
 'retrieve': {'category': 'command',
              'description': 'Retrieve an item from your house. Usage: retrieve <item>',
              'syntax': 'retrieve <item>',
              'title': 'Retrieve'},
 'righteous_fury': {'category': 'spell',
                    'classes': ['cleric'],
                    'description': 'Righteous Fury\n'
                                   'TARGET: self\n'
                                   '\n'
                                   'CASTING:\n'
                                   "- Use `cast 'righteous fury'`.\n"
                                   '- Mana cost applies per cast.',
                    'level': 1,
                    'mana': 55,
                    'syntax': "cast 'righteous fury'",
                    'title': 'Righteous Fury'},
 'ritual': {'category': 'command',
            'description': 'Perform dark ritual to empower all undead pets (Necromancer only).',
            'syntax': 'ritual',
            'title': 'Ritual'},
 'rlist': {'category': 'command',
           'description': 'List all rooms in a zone (immortal only).\n'
                          '\n'
                          'Usage:\n'
                          '    rlist           - List rooms in current zone\n'
                          '    rlist <zone>    - List rooms in specified zone',
           'syntax': 'rlist           - List rooms in current zone',
           'title': 'Rlist'},
 'sacred_shield': {'category': 'command',
                   'description': 'Apply a holy shield.',
                   'syntax': 'sacred_shield',
                   'title': 'Sacred Shield'},
 'sacrifice': {'category': 'command',
               'description': 'Sacrifice a corpse to the gods for gold.',
               'syntax': 'sacrifice',
               'title': 'Sacrifice'},
 'salute': {'category': 'command', 'description': 'Salute.', 'syntax': 'salute', 'title': 'Salute'},
 'sanctuary': {'category': 'spell',
               'classes': ['cleric'],
               'description': '\n'
                              'Holy aura that reduces incoming damage.\n'
                              '\n'
                              'MECHANICS:\n'
                              '- Percentage damage reduction\n'
                              '- Strong defensive buff\n',
               'level': 1,
               'mana': 75,
               'syntax': "cast 'sanctuary'",
               'title': 'Sanctuary'},
 'save': {'category': 'command', 'description': 'Save your character.', 'syntax': 'save', 'title': 'Save'},
 'say': {'category': 'command', 'description': 'Say something to the room.', 'syntax': 'say', 'title': 'Say'},
 'scan': {'category': 'skill',
          'classes': ['ranger'],
          'description': 'Scan for creatures in adjacent rooms.\n'
                         '\n'
                         'TRAINING:\n'
                         '- Grows as you use it, up to 85%.\n'
                         '- Your guild\'s trainer teaches the rest.',
          'syntax': 'scan',
          'title': 'Scan'},
 'score': {'category': 'command', 'description': 'Show player stats.', 'syntax': 'score', 'title': 'Score'},
 'scribe': {'category': 'skill',
            'classes': ['mage'],
            'description': 'A class skill. Use it to gain tactical advantages in combat or utility.\n'
                           '\n'
                           'TRAINING:\n'
                           '- Grows as you use it, up to 85%.\n'
                           '- Your guild\'s trainer teaches the rest.',
            'syntax': 'scribe',
            'title': 'Scribe'},
 'seal_of_command': {'category': 'command',
                     'description': 'Empower attacks with holy damage.',
                     'syntax': 'seal_of_command',
                     'title': 'Seal Of Command'},
 'search': {'category': 'command',
            'description': 'Search the room for hidden exits or items.',
            'syntax': 'search',
            'title': 'Search'},
 'secondwind': {'category': 'command',
                'description': 'Convert stamina or mana into a burst of movement recovery.',
                'syntax': 'secondwind',
                'title': 'Second Wind'},
 'second_attack': {'category': 'skill',
                   'classes': ['assassin', 'paladin', 'ranger', 'thief', 'warrior'],
                   'description': 'A class skill. Use it to gain tactical advantages in combat or utility.\n'
                                  '\n'
                                  'TRAINING:\n'
                                  '- Grows as you use it, up to 85%.\n'
                                  '- Your guild\'s trainer teaches the rest.',
                   'syntax': 'second_attack',
                   'title': 'Second Attack'},
 'sell': {'category': 'command',
          'description': 'Sell an item to a shop. Usage: sell <item>',
          'syntax': 'sell <item>',
          'title': 'Sell'},
 'set': {'category': 'command',
         'description': 'Set a field on a player or mob (immortal only).\n'
                        '\n'
                        'Usage: set <target> <field> <value>\n'
                        '\n'
                        'Fields for characters:\n'
                        '    level, hp, maxhp, mana, maxmana, move, maxmove\n'
                        '    str, int, wis, dex, con, cha\n'
                        '    gold, exp, alignment, hitroll, damroll, ac',
         'syntax': 'set <target> <field> <value>',
         'title': 'Set'},
 'sets': {'category': 'command', 'description': 'Show active zone set bonuses.', 'syntax': 'sets', 'title': 'Sets'},
 'settings': {'category': 'command',
              'description': 'Show toggleable settings.',
              'syntax': 'settings',
              'title': 'Settings'},
 'shadow_blade': {'category': 'command',
                  'description': 'Empower attacks from stealth.',
                  'syntax': 'shadow_blade',
                  'title': 'Shadow Blade'},
 'shadow_blink': {'category': 'command',
                  'description': 'Blink behind target and stealth briefly.',
                  'syntax': 'shadow_blink',
                  'title': 'Shadow Blink'},
 'shadow_dance': {'category': 'command',
                  'description': 'Use stealth abilities in combat for a short time.',
                  'syntax': 'shadow_dance',
                  'title': 'Shadow Dance'},
 'shadow_step': {'category': 'skill',
                 'classes': ['assassin'],
                 'description': 'Shadow Step - teleport and dodge.\n'
                                '\n'
                                'Usage: shadowstep <target>\n'
                                '\n'
                                'REQUIREMENTS:\n'
                                '- Must be an assassin\n'
                                '- Target must be in the room\n'
                                '- Cooldown: 30 seconds\n'
                                '\n'
                                'EFFECTS:\n'
                                '- Teleport behind target (flavor text)\n'
                                '- Dodge the NEXT incoming attack automatically\n'
                                '- Grants +1 Intel on marked target\n'
                                '\n'
                                'STRATEGY:\n'
                                '- Use to dodge a big hit while building Intel\n'
                                '- Good opener: Shadow Step -> Backstab\n'
                                '- The auto-dodge is consumed on next hit,\n'
                                '  so use it when you anticipate a big attack\n'
                                '\n'
                                'See also: HELP INTEL, HELP EVASION',
                 'syntax': 'shadowstep <target>',
                 'title': 'Shadow Step'},
 'shadowstep': {'category': 'command',
                'description': 'See HELP SHADOW_STEP.',
                'syntax': 'shadowstep <target>',
                'title': 'Shadowstep'},
 'shield': {'category': 'spell',
            'classes': ['mage', 'necromancer'],
            'description': 'Shield\n'
                           'TARGET: defensive\n'
                           '\n'
                           'CASTING:\n'
                           "- Use `cast 'shield'`.\n"
                           '- Mana cost applies per cast.\n'
                           '\n'
                           'MECHANICS:\n'
                           '- Improves armor class and grants a minor evasion boost.',
            'level': 1,
            'mana': 25,
            'syntax': "cast 'shield'",
            'title': 'Shield'},
 'shield_bash': {'category': 'command',
                 'description': '\n'
                                'Bash with a shield to stun/knock down.\n'
                                '\n'
                                'REQUIREMENTS:\n'
                                '- Shield equipped\n'
                                '\n'
                                'MECHANICS:\n'
                                '- Higher success with STR\n'
                                '- Stuns briefly on success\n',
                 'syntax': 'shield_bash',
                 'title': 'Shield Bash'},
 'shield_block': {'category': 'skill',
                  'classes': ['warrior'],
                  'description': 'Passive chance to block attacks with a shield.',
                  'syntax': 'shield_block',
                  'title': 'Shield Block'},
 'shield_of_faith': {'category': 'spell',
                     'classes': ['cleric', 'paladin'],
                     'description': 'Shield of Faith\n'
                                    'TARGET: defensive\n'
                                    '\n'
                                    'CASTING:\n'
                                    "- Use `cast 'shield of faith'`.\n"
                                    '- Mana cost applies per cast.\n'
                                    '\n'
                                    'MECHANICS:\n'
                                    '- Improves armor class and grants a minor evasion boost.',
                     'level': 1,
                     'mana': 35,
                     'syntax': "cast 'shield of faith'",
                     'title': 'Shield Of Faith'},
 'shield_wall': {'category': 'skill',
                 'classes': ['warrior'],
                 'description': 'Shield Wall — Chain ability (🟡) for Warriors.\n'
                                'Reduce damage taken by 50% for 10s. Extends chain.\n'
                                'Cooldown: 120s. No resource cost.\n\n'
                                'CHAIN TYPE: Chain — extends combo by 1 (defensive chain).\n'
                                'NAMED COMBO: Shield Slam → Shield Wall → Shield Slam = Iron Wall (duration doubled)',
                 'syntax': 'shield_wall',
                 'title': 'Shield Wall'},
 'shout': {'category': 'command', 'description': 'Shout to everyone in the zone.', 'syntax': 'shout', 'title': 'Shout'},
 'show': {'category': 'command',
          'description': 'Show various game statistics (immortal only).\n'
                         '\n'
                         'Usage:\n'
                         '    show zones    - List all zones\n'
                         '    show players  - List all online players with details\n'
                         '    show stats    - Show server statistics',
          'syntax': 'show zones    - List all zones',
          'title': 'Show'},
 'shrug': {'category': 'command', 'description': 'Shrug.', 'syntax': 'shrug', 'title': 'Shrug'},
 'shutdown': {'category': 'command',
              'description': 'Shutdown the MUD server (immortal only).\n\nUsage: shutdown [now|reboot]',
              'syntax': 'shutdown [now|reboot]',
              'title': 'Shutdown'},
 'sigh': {'category': 'command', 'description': 'Sigh.', 'syntax': 'sigh', 'title': 'Sigh'},
 'silence_strike': {'category': 'command',
                    'description': 'Strike and silence spellcasting.',
                    'syntax': 'silence_strike',
                    'title': 'Silence Strike'},
 'sit': {'category': 'command', 'description': 'Sit down.', 'syntax': 'sit', 'title': 'Sit'},
 'skill': {'category': 'command', 'description': 'Alias for skills command.', 'syntax': 'skill', 'title': 'Skill'},
 'skills': {'category': 'command',
            'description': 'Show all skills and spells available to your class, or pet abilities.',
            'syntax': 'skills',
            'title': 'Skills'},
 'slap': {'category': 'command', 'description': 'Slap someone.', 'syntax': 'slap', 'title': 'Slap'},
 'slay': {'category': 'command',
          'description': 'Instantly kill a target (immortal only).\n\nUsage: slay <target>',
          'syntax': 'slay <target>',
          'title': 'Slay'},
 'sleep': {'category': 'spell',
           'classes': ['bard', 'mage'],
           'description': "Sleep\nTARGET: offensive\n\nCASTING:\n- Use `cast 'sleep'`.\n- Mana cost applies per cast.",
           'level': 1,
           'mana': 20,
           'syntax': "cast 'sleep' <target>",
           'title': 'Sleep'},
 'slicedice': {'category': 'command',
               'description': 'DoT finisher that uses 3+ combo points.',
               'syntax': 'slicedice',
               'title': 'Slicedice'},
 'slip_away': {'category': 'command',
               'description': 'Enter stealth after a dodge.',
               'syntax': 'slip_away',
               'title': 'Slip Away'},
 'slow': {'category': 'spell',
          'classes': ['bard'],
          'description': "Slow\nTARGET: offensive\n\nCASTING:\n- Use `cast 'slow'`.\n- Mana cost applies per cast.",
          'level': 1,
          'mana': 35,
          'syntax': "cast 'slow' <target>",
          'title': 'Slow'},
 'smile': {'category': 'command', 'description': 'Smile at someone.', 'syntax': 'smile', 'title': 'Smile'},
 'smite': {'category': 'skill',
           'classes': ['paladin'],
           'description': '\n'
                          'Paladin holy strike.\n'
                          '\n'
                          'MECHANICS:\n'
                          '- Bonus damage vs undead/evil\n'
                          '- Uses holy_smite bonus where available\n',
           'syntax': 'smite',
           'title': 'Smite'},
 'sneak': {'category': 'skill',
           'classes': ['assassin', 'bard', 'ranger', 'thief'],
           'description': '\n'
                          'Move silently and avoid detection.\n'
                          '\n'
                          'MECHANICS:\n'
                          '- Persists until a failed movement check\n'
                          '- Detection vs mobs uses your stealth vs mob detect + environment\n'
                          '- Light penalizes stealth; dark/forest/swamp boosts it\n'
                          '\n'
                          'TIPS:\n'
                          '- Pair with Hide for best results\n'
                          '- Cover/snuff light to reduce penalties\n',
           'syntax': 'sneak',
           'title': 'Sneak'},
 'snicker': {'category': 'command', 'description': 'Snicker.', 'syntax': 'snicker', 'title': 'Snicker'},
 'snoop': {'category': 'command',
           'description': 'Watch what another player sees (immortal only).\n'
                          '\n'
                          'Usage:\n'
                          '    snoop <player>  - Start snooping on a player\n'
                          '    snoop           - Stop snooping',
           'syntax': 'snoop <player>  - Start snooping on a player',
           'title': 'Snoop'},
 'snuff': {'category': 'command',
           'description': 'Snuff your light source. Usage: snuff light',
           'syntax': 'snuff light',
           'title': 'Snuff'},
 'social': {'category': 'command', 'description': 'Process a social command.', 'syntax': 'social', 'title': 'Social'},
 'socials': {'category': 'command',
             'description': 'List all available social commands.',
             'syntax': 'socials',
             'title': 'Socials'},
 'songs': {'category': 'command',
           'description': '\n'
                          'List available bard songs and performance status.\n'
                          '\n'
                          'MECHANICS:\n'
                          '- Songs are ongoing buffs/debuffs\n'
                          '- Mana drains each tick while active\n',
           'syntax': 'songs',
           'title': 'Songs'},
 'soulstone': {'category': 'command',
               'description': 'Create a necromancer soulstone. Usage: soulstone [create]',
               'syntax': 'soulstone [create]',
               'title': 'Soulstone'},
 'south': {'category': 'command',
           'description': 'No additional details available yet.',
           'syntax': 'south',
           'title': 'South'},
 'spell_reflection': {'category': 'spell',
                      'classes': ['mage'],
                      'description': 'Spell Reflection\n'
                                     'TARGET: self\n'
                                     '\n'
                                     'CASTING:\n'
                                     "- Use `cast 'spell reflection'`.\n"
                                     '- Mana cost applies per cast.',
                      'level': 1,
                      'mana': 70,
                      'syntax': "cast 'spell reflection'",
                      'title': 'Spell Reflection'},
 'spells': {'category': 'command', 'description': 'Show known spells.', 'syntax': 'spells', 'title': 'Spells'},
 'split': {'category': 'command',
           'description': 'Split gold with your group. Usage: split <amount>',
           'syntax': 'split <amount>',
           'title': 'Split'},
 'stable': {'category': 'command',
            'description': 'Access the Garathorm Royal Stables.\n\n'
                           'COMMANDS:\n'
                           '  stable list       - View available mounts and prices\n'
                           '  stable buy <mount> - Purchase a mount\n'
                           '  stable store      - Safely stable your current mount\n\n'
                           'The stables are at the Stable Entrance, in the Stable & Temple quarter\n'
                           'north-east of the Temple. Brynn the Stable Master there can answer\n'
                           'questions about different mounts.\n\n'
                           'PURCHASABLE MOUNTS:\n'
                           '  Horse        - 2,000 gold (+50% speed)\n'
                           '  War Horse    - 5,000 gold (+50% speed, +2 damroll, combat-ready)\n\n'
                           'See also: mount, dismount, feed',
            'syntax': 'stable [list|buy <mount>|store]',
            'title': 'Stable'},
 'stampede': {'category': 'command',
              'description': 'Command all pets to attack.',
              'syntax': 'stampede',
              'title': 'Stampede'},
 'stance': {'category': 'command',
            'description': 'Set combat stance (aggressive, normal, defensive).',
            'syntax': 'stance [aggressive|normal|defensive]',
            'title': 'Stance'},
 'stand': {'category': 'command', 'description': 'Stand up.', 'syntax': 'stand', 'title': 'Stand'},
 'stat': {'category': 'command',
          'description': 'View detailed stats on a player, mob, or object (immortal only).\n\nUsage: stat <target>',
          'syntax': 'stat <target>',
          'title': 'Stat'},
 'steal': {'category': 'skill',
           'classes': ['thief'],
           'description': '\n'
                          'Attempt to steal gold from a target.\n'
                          '\n'
                          'REQUIREMENTS:\n'
                          '- Must be out of combat\n'
                          '\n'
                          'MECHANICS:\n'
                          '- DEX vs target DEX check\n'
                          '- Failure may anger the target\n',
           'syntax': 'steal',
           'title': 'Steal'},
 'stoneskin': {'category': 'spell',
               'classes': ['mage'],
               'description': 'Stoneskin\n'
                              'TARGET: defensive\n'
                              '\n'
                              'CASTING:\n'
                              "- Use `cast 'stoneskin'`.\n"
                              '- Mana cost applies per cast.',
               'level': 1,
               'mana': 60,
               'syntax': "cast 'stoneskin'",
               'title': 'Stoneskin'},
 'stats': {'category': 'info',
           'description': 'Stats & Influences\n'
                          '\n'
                          'STR: melee damage, shield block, bash/kick/cleave/charge.\n'
                          'DEX: accuracy, dodge/evasion/parry, stealth skills, move regen.\n'
                          'CON: max HP, HP regeneration, resilience.\n'
                          'INT: spell damage/crit, mana pool/regen (casters).\n'
                          'WIS: healing potency, spell resilience, tracking/taming.\n'
                          'CHA: bard inspiration, social checks, vendor reactions.\n'
                          '\n'
                          'Many skills add a small bonus from their primary stat.\n'
                          '\n'
                          'Worn gear adds to your stats, health, mana and moves while\n'
                          'worn. It may also ward against a kind of harm (fire, cold,\n'
                          'lightning, poison, disease, shadow, holy, arcane, nature,\n'
                          'sound; at most 75%), add to saving throws, resist spells or\n'
                          "quicken you. 'score' lists what your gear wards against.",
           'syntax': 'stats',
           'title': 'Stats'},
 'stop': {'category': 'command',
          'description': 'Stop the current bard performance.',
          'syntax': 'stop',
          'title': 'Stop'},
 'storage': {'category': 'command',
             'description': 'View items in your storage locker.',
             'syntax': 'storage',
             'title': 'Storage'},
 'store': {'category': 'command',
           'description': 'Store an item in your house. Usage: store <item>',
           'syntax': 'store <item>',
           'title': 'Store'},
 'story': {'category': 'command',
           'description': 'Show main story quest progress.',
           'syntax': 'story',
           'title': 'Story'},
 'summon': {'category': 'spell',
            'classes': ['cleric'],
            'description': "Summon\nTARGET: special\n\nCASTING:\n- Use `cast 'summon'`.\n- Mana cost applies per cast.",
            'level': 1,
            'mana': 75,
            'syntax': "cast 'summon'",
            'title': 'Summon'},
 'sunder_armor': {'category': 'command',
                  'description': 'Reduce target armor temporarily.',
                  'syntax': 'sunder_armor',
                  'title': 'Sunder Armor'},
 'tactical': {'category': 'command',
              'description': 'Show concise combat telemetry (OB/DB/PB totals + breakdown).\n\nFormula summary:\n- OB: hit bonus (includes stance)\n- DB: base(100-AC) + stance + shield magic + dodge(skill/item) - weight penalty\n- PB: base mitigation + stance + parry/shield_block - weight penalty\n- Escape/Flee: primarily DEX with capped WIL composure bonus',
              'syntax': 'tactical',
              'title': 'Tactical'},
 'take': {'category': 'command', 'description': 'Alias for get.', 'syntax': 'take', 'title': 'Take'},
 'talents': {'category': 'command',
             'description': 'View and spend talent points.\n'
                            '\n'
                            'Usage:\n'
                            '    talents           - Show all talent trees\n'
                            "    talents <tree>    - Show specific tree (e.g., 'talents fury')\n"
                            '    talents learn <id> - Learn/rank up a talent\n'
                            '    talents reset     - Reset all talents (costs gold)',
             'syntax': 'talents           - Show all talent trees',
             'title': 'Talents'},
 'talk': {'category': 'command', 'description': 'Talk to an NPC.', 'syntax': 'talk', 'title': 'Talk'},
 'tame': {'category': 'skill',
          'classes': ['ranger'],
          'description': 'Tame a wild creature. Usage: tame <creature>\n'
                         '\n'
                         'TRAINING:\n'
                         '- Grows as you use it, up to 85%.\n'
                         '- Your guild\'s trainer teaches the rest.',
          'syntax': 'tame',
          'title': 'Tame'},
 'target': {'category': 'command', 'description': 'Set your combat target.', 'syntax': 'target', 'title': 'Target'},
 'taste': {'category': 'command',
           'description': 'Taste food or drink. Usage: taste <item>',
           'syntax': 'taste <item>',
           'title': 'Taste'},
 'teleport': {'category': 'spell',
              'classes': ['mage'],
              'description': '\n'
                             'Teleport to a random safe location.\n'
                             '\n'
                             'MECHANICS:\n'
                             '- Random destination\n'
                             '- Cannot use in no-teleport rooms\n',
              'level': 1,
              'mana': 50,
              'syntax': "cast 'teleport'",
              'title': 'Teleport'},
 'tell': {'category': 'command', 'description': 'Send a private message.', 'syntax': 'tell', 'title': 'Tell'},
 'thank': {'category': 'command', 'description': 'Thank someone.', 'syntax': 'thank', 'title': 'Thank'},
 'thief': {'category': 'class',
           'description': 'The Thief (Scoundrel) class.\n'
                          '\n'
                          'CORE MECHANIC - LUCK SYSTEM:\n'
                          '  Thieves generate Luck (0-10) through combat.\n'
                          '  Successful hits: 15% chance +1 Luck\n'
                          '  Critical hits: always +1 Luck\n'
                          '  Dodge/parry: +1 Luck\n'
                          '  At Luck >= 5, dodges trigger free counterattacks!\n'
                          '\n'
                          'LUCK ABILITIES:\n'
                          '  pocket_sand  (3 Luck) - Blind target for 2 rounds. 20s CD.\n'
                          '  low_blow     (5 Luck) - Stun + weapon damage. 30s CD.\n'
                          '  rigged_dice  (7 Luck) - Next 3 attacks = guaranteed crits. 45s CD.\n'
                          '  jackpot     (10 Luck) - 4x weapon damage + steal gold. 60s CD.\n'
                          '\n'
                          'TALENT TREES:\n'
                          '  Fortune     - Luck generation and capitalization\n'
                          '  Dirty Tricks - Stuns, blinds, control\n'
                          '  Subtlety    - Stealth and ambush\n'
                          '\n'
                          'See also: HELP LUCK, HELP POCKET_SAND, HELP JACKPOT',
           'title': 'Thief'},
 'third_attack': {'category': 'skill',
                  'classes': ['warrior'],
                  'description': 'A class skill. Use it to gain tactical advantages in combat or utility.\n'
                                 '\n'
                                 'TRAINING:\n'
                                 '- Grows as you use it, up to 85%.\n'
                                 '- Your guild\'s trainer teaches the rest.',
                  'syntax': 'third_attack',
                  'title': 'Third Attack'},
 'tick': {'category': 'command',
          'description': 'Toggle tick timer notifications.\n'
                         '\n'
                         'Shows when game ticks happen (regen, combat, etc.)\n'
                         '\n'
                         'Usage:\n'
                         '    tick         - Toggle tick notifications\n'
                         '    tick on      - Turn on\n'
                         '    tick off     - Turn off',
          'syntax': 'tick         - Toggle tick notifications',
          'title': 'Tick'},
 'tickle': {'category': 'command', 'description': 'Tickle someone.', 'syntax': 'tickle', 'title': 'Tickle'},
 'time': {'category': 'command', 'description': 'Display the current game time.', 'syntax': 'time', 'title': 'Time'},
 'time_old': {'category': 'command',
              'description': 'Show the current in-game time (old version).',
              'syntax': 'time_old',
              'title': 'Time Old'},
 'appearance': {'category': 'command',
                'description': "How your hero looks in the 3D world, where their class has a choice. A mage chooses the "
                               "classic mage or the archmage (a tall hat, a long white beard, a robe to the ankles and a "
                               "moon staff). Chosen when a mage is made; change it any time.",
                'syntax': 'appearance [classic|archmage]',
                'title': 'Appearance'},
 'gender': {'category': 'command',
            'description': 'Whether your character is male or female: their pronouns, and their face and build in the 3D world. '
                           'Chosen when a character is made; one made before that was asked chooses once.',
            'syntax': 'gender [male|female]',
            'title': 'Gender'},
 'title': {'category': 'command',
           'description': 'Set your title. Usage: title <new title>',
           'syntax': 'title <new title>',
           'title': 'Title'},
 'toggle': {'category': 'command', 'description': 'Show all toggle settings.', 'syntax': 'toggle', 'title': 'Toggle'},
 'track': {'category': 'skill',
           'classes': ['ranger'],
           'description': '\n'
                          'Track a target through the wilderness.\n'
                          '\n'
                          'MECHANICS:\n'
                          '- WIS/DEX vs target stealth\n'
                          '- Best outdoors\n',
           'syntax': 'track',
           'title': 'Track'},
 'transfer': {'category': 'command',
              'description': 'Teleport a player to your location (immortal only).\n\nUsage: transfer <player>',
              'syntax': 'transfer <player>',
              'title': 'Transfer'},
 'travel': {'category': 'command',
            'description': 'Travel to a discovered waypoint.\n\nUsage:\n    travel <waypoint>',
            'syntax': 'travel <waypoint>',
            'title': 'Travel'},
 'trip': {'category': 'skill',
          'classes': ['thief'],
          'description': 'Trip — Sweep a target\'s legs to knock them down.\n\n'
                         'MECHANICS:\n'
                         '- Success based on trip skill + DEX vs target DEX\n'
                         '- On success: target is knocked to sitting position\n'
                         '- Sitting targets have reduced combat effectiveness\n'
                         '- No cooldown\n\n'
                         'STRATEGY:\n'
                         '- Use to interrupt casters or gain advantage\n'
                         '- Higher DEX improves your success rate\n\n'
                         'See also: HELP THIEF',
          'syntax': 'trip [target]',
          'title': 'Trip'},
 'tumble': {'category': 'skill',
            'classes': ['thief'],
            'description': 'Short evasive window reducing incoming damage.',
            'syntax': 'tumble',
            'title': 'Tumble'},
 'turn_undead': {'category': 'skill',
                 'classes': ['cleric', 'paladin'],
                 'description': '\n'
                                'Turn or repel undead creatures.\n'
                                '\n'
                                'MECHANICS:\n'
                                '- WIS + skill roll vs undead level\n'
                                '- On success: undead flee\n',
                 'syntax': 'turn_undead',
                 'title': 'Turn Undead'},
 'turnundead': {'category': 'command',
                'description': 'Turn undead creatures, causing fear or destroying weak ones.',
                'syntax': 'turnundead',
                'title': 'Turnundead'},
 'typo': {'category': 'command',
          'description': 'Report a typo. Usage: typo <description>',
          'syntax': 'typo <description>',
          'title': 'Typo'},
 'unalias': {'category': 'command', 'description': 'Remove a personal alias.', 'syntax': 'unalias', 'title': 'Unalias'},
 'uncover': {'category': 'command',
             'description': 'Uncover your light source. Usage: uncover light',
             'syntax': 'uncover light',
             'title': 'Uncover'},
 'ungroup': {'category': 'command',
             'description': 'Leave your group or remove someone from it.\n'
                            '\n'
                            'Usage:\n'
                            '    ungroup         - Leave your current group\n'
                            '    ungroup <name>  - Remove player from group (leader only)',
             'syntax': 'ungroup         - Leave your current group',
             'title': 'Ungroup'},
 'unlabel': {'category': 'command', 'description': 'Remove a target label.', 'syntax': 'unlabel', 'title': 'Unlabel'},
 'unlock': {'category': 'command',
            'description': 'Unlock a door or container. Usage: unlock <door/container>',
            'syntax': 'unlock <door/container>',
            'title': 'Unlock'},
 'up': {'category': 'command', 'description': 'No additional details available yet.', 'syntax': 'up', 'title': 'Up'},
 'updates': {'category': 'command',
             'description': 'Show recent game updates and changes. Usage: updates [number of days]',
             'syntax': 'updates [number of days]',
             'title': 'Updates'},
 'value': {'category': 'command',
           'description': 'Check how much a shop will pay for an item. Usage: value <item>',
           'syntax': 'value <item>',
           'title': 'Value'},
 'vampiric_touch': {'category': 'spell',
                    'classes': ['necromancer'],
                    'description': 'Vampiric Touch — Drain the life force from a target to sustain yourself.\n\n'
                                   'MECHANICS:\n'
                                   '- Deals necrotic damage to target\n'
                                   '- Heals you for the damage dealt\n'
                                   '- Mana: 30\n'
                                   '- Generates +1 Soul Shard on kill\n\n'
                                   'STRATEGY:\n'
                                   '- Your primary sustain spell\n'
                                   '- Use to keep HP topped off while dealing damage\n'
                                   '- Pairs well with Drain Soul for double sustain\n\n'
                                   'See also: HELP SOUL_SHARDS, HELP DRAIN_SOUL, HELP NECROMANCER',
                    'level': 1,
                    'mana': 30,
                    'syntax': "cast 'vampiric touch' <target>",
                    'title': 'Vampiric Touch'},
 'vanish': {'category': 'skill',
            'classes': ['assassin'],
            'description': 'Vanish - drop combat and re-enter stealth.\n'
                           '\n'
                           'Usage: vanish\n'
                           '\n'
                           'REQUIREMENTS:\n'
                           '- Must be an assassin\n'
                           '- Cooldown: 60 seconds\n'
                           '\n'
                           'EFFECTS:\n'
                           '- Immediately drops combat\n'
                           '- Enter hidden + sneaking state\n'
                           '- DOES NOT RESET INTEL (critical!)\n'
                           '\n'
                           'STRATEGY:\n'
                           '- Your emergency escape button\n'
                           '- Vanish when HP is low, heal up, then\n'
                           '  re-engage with Backstab for bonus Intel\n'
                           '- Intel persists through Vanish, so you\n'
                           '  keep all progress toward Execute Contract\n'
                           '- Shadow Mend talent: backstab from stealth\n'
                           '  after Vanish heals you\n'
                           '\n'
                           'See also: HELP INTEL, HELP EVASION, HELP BACKSTAB',
            'syntax': 'vanish',
            'title': 'Vanish'},
 'vendetta': {'category': 'command',
              'description': 'Legacy ability - replaced by the Intel system for assassins.\n'
                             'See HELP INTEL and HELP MARK for the new assassin mechanics.',
              'syntax': 'vendetta',
              'title': 'Vendetta (Legacy)'},
 'vital': {'category': 'skill',
           'classes': ['assassin'],
           'description': 'Vital Strike - Intel 6 threshold ability.\n'
                          '\n'
                          'Usage: vital\n'
                          '\n'
                          'REQUIREMENTS:\n'
                          '- Must be an assassin\n'
                          '- Must be fighting your marked target\n'
                          '- Requires at least 6 Intel\n'
                          '- Cooldown: 30 seconds\n'
                          '\n'
                          'EFFECTS:\n'
                          '- Deals 3x weapon damage\n'
                          '- Guaranteed critical hit\n'
                          '- Ignores 50% of target armor\n'
                          '- Consumes 6 Intel\n'
                          '\n'
                          'STRATEGY:\n'
                          '- Your mid-fight burst ability\n'
                          '- Use when Intel hits 6, then rebuild for Execute\n'
                          '- Or use Expose at 3, build back to 6, then Vital\n'
                          '- With Deadly Patience talent: Intel >= 6 also\n'
                          '  gives 15% damage reduction\n'
                          '\n'
                          'See also: HELP INTEL, HELP EXPOSE, HELP EXECUTE_CONTRACT',
           'syntax': 'vital',
           'title': 'Vital Strike'},
 'visible': {'category': 'command',
             'description': 'Come out of hiding or stop sneaking.',
             'syntax': 'visible',
             'title': 'Visible'},
 'volley': {'category': 'command',
            'description': 'Rain arrows on all enemies in the room.',
            'syntax': 'volley',
            'title': 'Volley'},
 'wake': {'category': 'command', 'description': 'Wake up.', 'syntax': 'wake', 'title': 'Wake'},
 'warcry': {'category': 'command',
            'description': 'Terrifying shout that fears enemies and buffs allies.',
            'syntax': 'warcry',
            'title': 'Warcry'},
 'wave': {'category': 'command', 'description': 'Wave.', 'syntax': 'wave', 'title': 'Wave'},
 'waypoints': {'category': 'command',
               'description': 'List discovered waypoints.',
               'syntax': 'waypoints',
               'title': 'Waypoints'},
 'weaken': {'category': 'spell',
            'classes': ['necromancer'],
            'description': 'Weaken\n'
                           'TARGET: offensive\n'
                           '\n'
                           'CASTING:\n'
                           "- Use `cast 'weaken'`.\n"
                           '- Mana cost applies per cast.',
            'level': 1,
            'mana': 20,
            'syntax': "cast 'weaken' <target>",
            'title': 'Weaken'},
 'wear': {'category': 'command',
          'description': "Wear an item or 'wear all' to wear everything you can. Each class wears only "
                         "what it is trained in: a mage or necromancer cloth, a thief, assassin or bard "
                         "leather, a ranger or cleric up to mail (and a shield), a warrior or paladin "
                         "anything. Leather boots, gloves and bracers suit anyone; gauntlets and sabatons "
                         "count as armour. Weapons too: a mage carries a staff, a wand or a dagger; a "
                         "thief no two-handed sword. In /play what you can't use is greyed.",
          'syntax': 'wear',
          'title': 'Wear'},
 'weather': {'category': 'command',
             'description': 'Check the current weather.',
             'syntax': 'weather',
             'title': 'Weather'},
 'west': {'category': 'command',
          'description': 'No additional details available yet.',
          'syntax': 'west',
          'title': 'West'},
 'where': {'category': 'command', 'description': 'Show where players/mobs are.', 'syntax': 'where', 'title': 'Where'},
 'who': {'category': 'command', 'description': 'Show online players.', 'syntax': 'who', 'title': 'Who'},
 'wield': {'category': 'command', 'description': 'Wield a weapon.', 'syntax': 'wield', 'title': 'Wield'},
 'wimpy': {'category': 'command',
           'description': 'Set auto-flee HP threshold for combat. Usage: wimpy [hp amount]',
           'syntax': 'wimpy [hp amount]',
           'title': 'Wimpy'},
 'wink': {'category': 'command', 'description': 'Wink.', 'syntax': 'wink', 'title': 'Wink'},
 'withdraw': {'category': 'command',
              'description': 'Withdraw gold from the bank. Usage: withdraw <amount>',
              'syntax': 'withdraw <amount>',
              'title': 'Withdraw'},
 'wizhelp': {'category': 'command',
             'description': 'List all immortal commands.\n\nUsage: wizhelp',
             'syntax': 'wizhelp',
             'title': 'Wizhelp'},
 'wizinvis': {'category': 'command',
              'description': 'Toggle invisibility to mortals (immortal only).\n\nUsage: wizinvis [level]',
              'syntax': 'wizinvis [level]',
              'title': 'Wizinvis'},
 'word_of_recall': {'category': 'spell',
                    'classes': ['cleric'],
                    'description': 'Word of Recall\n'
                                   'TARGET: self\n'
                                   '\n'
                                   'CASTING:\n'
                                   "- Use `cast 'word of recall'`.\n"
                                   '- Mana cost applies per cast.',
                    'level': 1,
                    'mana': 15,
                    'syntax': "cast 'word of recall'",
                    'title': 'Word Of Recall'},
 'worth': {'category': 'command',
           'description': 'Show your total wealth breakdown.\n\nUsage: worth',
           'syntax': 'worth',
           'title': 'Worth'},
 'wyvern_sting': {'category': 'command',
                  'description': 'Put target to sleep briefly.',
                  'syntax': 'wyvern_sting',
                  'title': 'Wyvern Sting'},
 'xp': {'category': 'command', 'description': 'Show XP breakdown and progress.', 'syntax': 'xp', 'title': 'Xp'},
 'yawn': {'category': 'command', 'description': 'Yawn.', 'syntax': 'yawn', 'title': 'Yawn'},
 'zreset': {'category': 'command',
            'description': 'Reset (repopulate) a zone (immortal only).\n'
                           '\n'
                           'Usage: \n'
                           '    zreset          - Reset current zone\n'
                           '    zreset <number> - Reset specific zone',
            'syntax': 'zreset          - Reset current zone',
            'title': 'Zreset'},

 # ========== LEVEL 31-60 ABILITIES ==========
 # These powerful abilities unlock at higher levels and define endgame play.

 # ----- WARRIOR LEVEL 31-60 -----
 'rallying_cry': {
     'category': 'skill',
     'classes': ['warrior'],
     'title': 'Rallying Cry',
     'description': 'Let out a rallying cry that buffs the entire party with increased max HP and regeneration.\n\n'
                    'MECHANICS:\n'
                    '- Increases max HP for all group members\n'
                    '- Lasts 30 seconds\n'
                    '- 2 minute cooldown\n\n'
                    'REQUIREMENTS:\n'
                    '- Warrior class\n'
                    '- Level 32\n',
     'syntax': 'rallying_cry',
     'level': 32,
     'cooldown': 120,
 },
 'shattering_blow': {
     'category': 'skill',
     'classes': ['warrior'],
     'title': 'Shattering Blow',
     'description': 'Strike with such force that the target\'s armor is reduced.\n\n'
                    'MECHANICS:\n'
                    '- Deals heavy damage\n'
                    '- Reduces target\'s armor for 20 seconds\n'
                    '- 15 second cooldown\n\n'
                    'REQUIREMENTS:\n'
                    '- Warrior class\n'
                    '- Level 38\n',
     'syntax': 'shattering_blow [target]',
     'level': 38,
     'cooldown': 15,
 },
 'commanding_shout': {
     'category': 'skill',
     'classes': ['warrior'],
     'title': 'Commanding Shout',
     'description': 'Let out a commanding shout that taunts all enemies in the room.\n\n'
                    'MECHANICS:\n'
                    '- Forces all enemies to attack you\n'
                    '- Taunt lasts 12 seconds\n'
                    '- 30 second cooldown\n\n'
                    'REQUIREMENTS:\n'
                    '- Warrior class\n'
                    '- Level 44\n',
     'syntax': 'commanding_shout',
     'level': 44,
     'cooldown': 30,
 },
 'heroic_leap': {
     'category': 'skill',
     'classes': ['warrior'],
     'title': 'Heroic Leap',
     'description': 'Leap to a target, dealing damage and stunning them.\n\n'
                    'MECHANICS:\n'
                    '- Gap closer - use to engage from range\n'
                    '- Stuns target for 6 seconds\n'
                    '- 45 second cooldown\n\n'
                    'REQUIREMENTS:\n'
                    '- Warrior class\n'
                    '- Level 50\n',
     'syntax': 'heroic_leap <target>',
     'level': 50,
     'cooldown': 45,
 },
 'warpath': {
     'category': 'skill',
     'classes': ['warrior'],
     'title': 'Warpath',
     'description': 'Enter a sustained damage mode where all attacks deal increased damage.\n\n'
                    'MECHANICS:\n'
                    '- +15 damage and haste for 40 seconds\n'
                    '- 2 minute cooldown\n\n'
                    'REQUIREMENTS:\n'
                    '- Warrior class\n'
                    '- Level 56\n',
     'syntax': 'warpath',
     'level': 56,
     'cooldown': 120,
 },
 'titans_wrath': {
     'category': 'skill',
     'classes': ['warrior'],
     'title': "Titan's Wrath",
     'description': 'CAPSTONE ABILITY: Invoke the power of a titan for 10 seconds of god mode.\n\n'
                    'MECHANICS:\n'
                    '- IMMUNE to all damage\n'
                    '- Double damage on all attacks\n'
                    '- Attacks cleave to all enemies\n'
                    '- 2 minute cooldown\n\n'
                    'REQUIREMENTS:\n'
                    '- Warrior class\n'
                    '- Level 60\n',
     'syntax': 'titans_wrath',
     'level': 60,
     'cooldown': 120,
 },

 # ----- MAGE LEVEL 31-60 -----
 'time_warp': {
     'category': 'spell',
     'classes': ['mage'],
     'title': 'Time Warp',
     'description': 'Bend the fabric of time, granting haste to you and your party.\n\n'
                    'MECHANICS:\n'
                    '- Haste + hit/damage bonus for whole group\n'
                    '- 40 second duration\n'
                    '- 2 minute cooldown\n\n'
                    'REQUIREMENTS:\n'
                    '- Mage class\n'
                    '- Level 38\n',
     'syntax': "cast 'time warp'",
     'level': 38,
     'mana': 120,
     'cooldown': 120,
 },
 'arcane_explosion': {
     'category': 'spell',
     'classes': ['mage'],
     'title': 'Arcane Explosion',
     'description': 'Unleash a massive arcane explosion that damages all enemies in the room.\n\n'
                    'MECHANICS:\n'
                    '- Massive AoE damage\n'
                    '- 30 second cooldown\n\n'
                    'REQUIREMENTS:\n'
                    '- Mage class\n'
                    '- Level 44\n',
     'syntax': "cast 'arcane explosion'",
     'level': 44,
     'mana': 80,
     'cooldown': 30,
 },
 'icy_veins': {
     'category': 'spell',
     'classes': ['mage'],
     'title': 'Icy Veins',
     'description': 'Channel frost power for increased crit chance and cast speed.\n\n'
                    'MECHANICS:\n'
                    '- +30% crit chance\n'
                    '- Haste effect\n'
                    '- +15 spell power\n'
                    '- 30 second duration\n'
                    '- 3 minute cooldown\n\n'
                    'REQUIREMENTS:\n'
                    '- Mage class\n'
                    '- Level 50\n',
     'syntax': "cast 'icy veins'",
     'level': 50,
     'mana': 100,
     'cooldown': 180,
 },
 'combustion_master': {
     'category': 'spell',
     'classes': ['mage'],
     'title': 'Combustion',
     'description': 'Ignite your inner fire - all fire spells are guaranteed critical hits.\n\n'
                    'MECHANICS:\n'
                    '- 100% fire spell critical chance\n'
                    '- +8 damage bonus\n'
                    '- 24 second duration\n'
                    '- 3 minute cooldown\n\n'
                    'REQUIREMENTS:\n'
                    '- Mage class\n'
                    '- Level 56\n',
     'syntax': "cast 'combustion'",
     'level': 56,
     'mana': 80,
     'cooldown': 180,
 },
 'meteor_storm': {
     'category': 'spell',
     'classes': ['mage'],
     'title': 'Meteor Storm',
     'description': 'CAPSTONE ABILITY: Call down a cataclysmic meteor storm from the heavens.\n\n'
                    'MECHANICS:\n'
                    '- MASSIVE AoE damage to all enemies\n'
                    '- Stuns all targets\n'
                    '- Leaves burning ground (DoT)\n'
                    '- 2 minute cooldown\n\n'
                    'REQUIREMENTS:\n'
                    '- Mage class\n'
                    '- Level 60\n',
     'syntax': "cast 'meteor storm'",
     'level': 60,
     'mana': 200,
     'cooldown': 120,
 },

 # ----- CLERIC LEVEL 31-60 -----
 'prayer_of_mending': {
     'category': 'spell',
     'classes': ['cleric'],
     'title': 'Prayer of Mending',
     'description': 'Place a prayer on a target that heals them and bounces to other injured allies.\n\n'
                    'MECHANICS:\n'
                    '- Heals target\n'
                    '- Bounces to 3 other injured allies\n'
                    '- 15 second cooldown\n\n'
                    'REQUIREMENTS:\n'
                    '- Cleric class\n'
                    '- Level 32\n',
     'syntax': "cast 'prayer of mending' <target>",
     'level': 32,
     'mana': 60,
     'cooldown': 15,
 },
 'spirit_link': {
     'category': 'spell',
     'classes': ['cleric'],
     'title': 'Spirit Link',
     'description': 'Link the spirits of your party, sharing damage equally among all members.\n\n'
                    'MECHANICS:\n'
                    '- All damage taken is split among party\n'
                    '- 30 second duration\n'
                    '- 2 minute cooldown\n\n'
                    'REQUIREMENTS:\n'
                    '- Cleric class\n'
                    '- Level 38\n',
     'syntax': "cast 'spirit link'",
     'level': 38,
     'mana': 100,
     'cooldown': 120,
 },
 'mass_dispel': {
     'category': 'spell',
     'classes': ['cleric'],
     'title': 'Mass Dispel',
     'description': 'Unleash a wave of purifying energy that removes all debuffs from allies and buffs from enemies.\n\n'
                    'MECHANICS:\n'
                    '- Removes all debuffs from allies\n'
                    '- Removes all buffs from enemies\n'
                    '- 1 minute cooldown\n\n'
                    'REQUIREMENTS:\n'
                    '- Cleric class\n'
                    '- Level 44\n',
     'syntax': "cast 'mass dispel'",
     'level': 44,
     'mana': 80,
     'cooldown': 60,
 },
 'lightwell': {
     'category': 'spell',
     'classes': ['cleric'],
     'title': 'Lightwell',
     'description': 'Summon a radiant lightwell that heals all allies in the room over time.\n\n'
                    'MECHANICS:\n'
                    '- Heals all allies each tick\n'
                    '- Lasts 60 seconds\n'
                    '- 3 minute cooldown\n\n'
                    'REQUIREMENTS:\n'
                    '- Cleric class\n'
                    '- Level 50\n',
     'syntax': "cast 'lightwell'",
     'level': 50,
     'mana': 100,
     'cooldown': 180,
 },
 'serenity': {
     'category': 'spell',
     'classes': ['cleric'],
     'title': 'Serenity',
     'description': 'Channel pure divine serenity, fully restoring a target\'s health.\n\n'
                    'MECHANICS:\n'
                    '- Fully heals one target\n'
                    '- 2 minute cooldown\n\n'
                    'REQUIREMENTS:\n'
                    '- Cleric class\n'
                    '- Level 56\n',
     'syntax': "cast 'serenity' <target>",
     'level': 56,
     'mana': 150,
     'cooldown': 120,
 },
 'divine_intervention': {
     'category': 'spell',
     'classes': ['cleric'],
     'title': 'Divine Intervention',
     'description': 'CAPSTONE ABILITY: Invoke direct divine intervention from the gods.\n\n'
                    'MECHANICS:\n'
                    '- Fully heals entire party\n'
                    '- Resurrects any dead party members\n'
                    '- Grants temporary immunity\n'
                    '- 2 minute cooldown\n\n'
                    'REQUIREMENTS:\n'
                    '- Cleric class\n'
                    '- Level 60\n',
     'syntax': "cast 'divine intervention'",
     'level': 60,
     'mana': 300,
     'cooldown': 120,
 },

 # ----- THIEF LEVEL 31-60 -----
 'nerve_strike': {
     'category': 'skill',
     'classes': ['thief'],
     'title': 'Nerve Strike',
     'description': 'Strike a target\'s nerve cluster, paralyzing them.\n\n'
                    'MECHANICS:\n'
                    '- Paralyzes target for 6 seconds\n'
                    '- 30 second cooldown\n\n'
                    'REQUIREMENTS:\n'
                    '- Thief class\n'
                    '- Level 32\n',
     'syntax': 'nerve_strike [target]',
     'level': 32,
     'cooldown': 30,
 },
 'garrote': {
     'category': 'skill',
     'classes': ['thief'],
     'title': 'Garrote',
     'description': 'Strangle a target from stealth, silencing them and causing bleed damage.\n\n'
                    'MECHANICS:\n'
                    '- Must be used from stealth\n'
                    '- Silences target for 10 seconds\n'
                    '- Applies strong bleed DoT\n'
                    '- 20 second cooldown\n\n'
                    'REQUIREMENTS:\n'
                    '- Thief class\n'
                    '- Level 44\n',
     'syntax': 'garrote <target>',
     'level': 44,
     'cooldown': 20,
 },
 'evasion_master': {
     'category': 'skill',
     'classes': ['thief'],
     'title': 'Evasion',
     'description': 'Enter a state of perfect evasion - 100% dodge chance for 10 seconds.\n\n'
                    'MECHANICS:\n'
                    '- All physical attacks miss\n'
                    '- 10 second duration\n'
                    '- 2 minute cooldown\n\n'
                    'REQUIREMENTS:\n'
                    '- Thief class\n'
                    '- Level 50\n',
     'syntax': 'evasion',
     'level': 50,
     'cooldown': 120,
 },
 'marked_for_death_thief': {
     'category': 'skill',
     'classes': ['thief'],
     'title': 'Marked for Death',
     'description': 'Mark a target for death - all your attacks deal 50% bonus damage.\n\n'
                    'MECHANICS:\n'
                    '- +50% damage to marked target\n'
                    '- Lasts 20 seconds\n'
                    '- 1 minute cooldown\n\n'
                    'REQUIREMENTS:\n'
                    '- Thief class\n'
                    '- Level 56\n',
     'syntax': 'marked_for_death <target>',
     'level': 56,
     'cooldown': 60,
 },
 'perfect_crime': {
     'category': 'skill',
     'classes': ['thief'],
     'title': 'Perfect Crime',
     'description': 'CAPSTONE ABILITY: 30 seconds of permanent stealth with guaranteed critical hits.\n\n'
                    'MECHANICS:\n'
                    '- Cannot be detected\n'
                    '- All attacks are critical hits\n'
                    '- 30 second duration\n'
                    '- 2 minute cooldown\n\n'
                    'REQUIREMENTS:\n'
                    '- Thief class\n'
                    '- Level 60\n',
     'syntax': 'perfect_crime',
     'level': 60,
     'cooldown': 120,
 },

 # ----- RANGER LEVEL 31-60 -----
 'volley_master': {
     'category': 'skill',
     'classes': ['ranger'],
     'title': 'Volley',
     'description': 'Rain arrows on all enemies in the room.\n\n'
                    'MECHANICS:\n'
                    '- AoE damage to all enemies\n'
                    '- 20 second cooldown\n\n'
                    'REQUIREMENTS:\n'
                    '- Ranger class\n'
                    '- Level 32\n',
     'syntax': 'volley',
     'level': 32,
     'cooldown': 20,
 },
 'camouflage_master': {
     'category': 'skill',
     'classes': ['ranger'],
     'title': 'Camouflage',
     'description': 'Enter advanced camouflage - much harder to detect than regular hide.\n\n'
                    'MECHANICS:\n'
                    '- Superior stealth\n'
                    '- +30 to stealth checks\n'
                    '- 40 second duration\n'
                    '- 30 second cooldown\n\n'
                    'REQUIREMENTS:\n'
                    '- Ranger class\n'
                    '- Level 38\n',
     'syntax': 'camouflage',
     'level': 38,
     'cooldown': 30,
 },
 'serpent_sting': {
     'category': 'skill',
     'classes': ['ranger'],
     'title': 'Serpent Sting',
     'description': 'Apply a strong poison DoT to your target.\n\n'
                    'MECHANICS:\n'
                    '- Initial damage + poison DoT\n'
                    '- DoT lasts 20 seconds\n'
                    '- 15 second cooldown\n\n'
                    'REQUIREMENTS:\n'
                    '- Ranger class\n'
                    '- Level 44\n',
     'syntax': 'serpent_sting <target>',
     'level': 44,
     'cooldown': 15,
 },
 'rapid_fire': {
     'category': 'skill',
     'classes': ['ranger'],
     'title': 'Rapid Fire',
     'description': 'Fire a rapid barrage of 5-7 arrows at your target.\n\n'
                    'MECHANICS:\n'
                    '- Multiple hits in quick succession\n'
                    '- 1 minute cooldown\n\n'
                    'REQUIREMENTS:\n'
                    '- Ranger class\n'
                    '- Level 50\n',
     'syntax': 'rapid_fire [target]',
     'level': 50,
     'cooldown': 60,
 },
 'kill_command': {
     'category': 'skill',
     'classes': ['ranger'],
     'title': 'Kill Command',
     'description': 'Command your pet to execute a wounded target.\n\n'
                    'MECHANICS:\n'
                    '- High damage attack\n'
                    '- DOUBLE damage if target below 35% HP\n'
                    '- 45 second cooldown\n\n'
                    'REQUIREMENTS:\n'
                    '- Ranger class\n'
                    '- Level 56\n'
                    '- Must have a pet\n',
     'syntax': 'kill_command [target]',
     'level': 56,
     'cooldown': 45,
 },
 'alpha_pack': {
     'category': 'skill',
     'classes': ['ranger'],
     'title': 'Alpha Pack',
     'description': 'CAPSTONE ABILITY: Summon ALL pet types simultaneously in a frenzy.\n\n'
                    'MECHANICS:\n'
                    '- Summons wolf, bear, hawk, cat, and boar\n'
                    '- All pets are in permanent frenzy\n'
                    '- Lasts 30 seconds\n'
                    '- 2 minute cooldown\n\n'
                    'REQUIREMENTS:\n'
                    '- Ranger class\n'
                    '- Level 60\n',
     'syntax': 'alpha_pack',
     'level': 60,
     'cooldown': 120,
 },

 # ----- PALADIN LEVEL 31-60 -----
 'hand_of_freedom': {
     'category': 'spell',
     'classes': ['paladin'],
     'title': 'Hand of Freedom',
     'description': 'Grant a target freedom from all movement-impairing effects.\n\n'
                    'MECHANICS:\n'
                    '- Removes snares, roots, slows\n'
                    '- Immunity for 16 seconds\n'
                    '- 30 second cooldown\n\n'
                    'REQUIREMENTS:\n'
                    '- Paladin class\n'
                    '- Level 32\n',
     'syntax': "cast 'hand of freedom' <target>",
     'level': 32,
     'mana': 40,
     'cooldown': 30,
 },
 'consecration': {
     'category': 'spell',
     'classes': ['paladin'],
     'title': 'Consecration',
     'description': 'Consecrate the ground with holy fire, damaging enemies standing in it.\n\n'
                    'MECHANICS:\n'
                    '- Damages all enemies in room each tick\n'
                    '- Lasts 20 seconds\n'
                    '- 20 second cooldown\n\n'
                    'REQUIREMENTS:\n'
                    '- Paladin class\n'
                    '- Level 38\n',
     'syntax': "cast 'consecration'",
     'level': 38,
     'mana': 60,
     'cooldown': 20,
 },
 'hammer_of_justice': {
     'category': 'spell',
     'classes': ['paladin'],
     'title': 'Hammer of Justice',
     'description': 'Hurl a hammer of holy justice that stuns your target.\n\n'
                    'MECHANICS:\n'
                    '- Ranged stun attack\n'
                    '- Stuns for 8 seconds\n'
                    '- 45 second cooldown\n\n'
                    'REQUIREMENTS:\n'
                    '- Paladin class\n'
                    '- Level 44\n',
     'syntax': "cast 'hammer of justice' <target>",
     'level': 44,
     'mana': 50,
     'cooldown': 45,
 },
 'avenging_wrath_master': {
     'category': 'spell',
     'classes': ['paladin'],
     'title': 'Avenging Wrath',
     'description': 'Wings of golden light burst from your back as divine wrath fills you.\n\n'
                    'MECHANICS:\n'
                    '- +12 damage, +8 hit\n'
                    '- +30% healing power\n'
                    '- Haste effect\n'
                    '- 40 second duration\n'
                    '- 3 minute cooldown\n\n'
                    'REQUIREMENTS:\n'
                    '- Paladin class\n'
                    '- Level 50\n',
     'syntax': "cast 'avenging wrath'",
     'level': 50,
     'mana': 120,
     'cooldown': 180,
 },
 'divine_shield_master': {
     'category': 'spell',
     'classes': ['paladin'],
     'title': 'Divine Shield',
     'description': 'Surround yourself with an impenetrable divine shield - complete immunity.\n\n'
                    'MECHANICS:\n'
                    '- IMMUNE to all damage\n'
                    '- 16 second duration\n'
                    '- 3 minute cooldown\n\n'
                    'REQUIREMENTS:\n'
                    '- Paladin class\n'
                    '- Level 56\n',
     'syntax': "cast 'divine shield'",
     'level': 56,
     'mana': 80,
     'cooldown': 180,
 },
 'crusaders_judgment': {
     'category': 'spell',
     'classes': ['paladin'],
     'title': "Crusader's Judgment",
     'description': 'CAPSTONE ABILITY: The ultimate judgment of the Light.\n\n'
                    'MECHANICS:\n'
                    '- MASSIVE holy damage to target\n'
                    '- Grants party temporary invulnerability\n'
                    '- Resurrects dead party members\n'
                    '- 2 minute cooldown\n\n'
                    'REQUIREMENTS:\n'
                    '- Paladin class\n'
                    '- Level 60\n',
     'syntax': "cast 'crusaders judgment' <target>",
     'level': 60,
     'mana': 250,
     'cooldown': 120,
 },

 # ----- NECROMANCER LEVEL 31-60 -----
 'death_coil': {
     'category': 'spell',
     'classes': ['necromancer'],
     'title': 'Death Coil',
     'description': 'Hurl a coil of death energy. Damages enemies OR heals your undead minions.\n\n'
                    'MECHANICS:\n'
                    '- Damages living targets\n'
                    '- Heals undead pets\n'
                    '- 12 second cooldown\n\n'
                    'REQUIREMENTS:\n'
                    '- Necromancer class\n'
                    '- Level 32\n',
     'syntax': "cast 'death coil' <target>",
     'level': 32,
     'mana': 45,
     'cooldown': 12,
 },
 'corpse_shield': {
     'category': 'spell',
     'classes': ['necromancer'],
     'title': 'Corpse Shield',
     'description': 'Your undead minion forms a protective barrier, absorbing damage for you.\n\n'
                    'MECHANICS:\n'
                    '- 50% of damage redirected to minion\n'
                    '- Lasts 30 seconds\n'
                    '- 1 minute cooldown\n\n'
                    'REQUIREMENTS:\n'
                    '- Necromancer class\n'
                    '- Level 38\n',
     'syntax': "cast 'corpse shield'",
     'level': 38,
     'mana': 60,
     'cooldown': 60,
 },
 'plague_strike': {
     'category': 'spell',
     'classes': ['necromancer'],
     'title': 'Plague Strike',
     'description': 'Strike with virulent plague that spreads to nearby enemies.\n\n'
                    'MECHANICS:\n'
                    '- Infects target with plague\n'
                    '- Spreads to nearby enemies\n'
                    '- 20 second duration\n'
                    '- 20 second cooldown\n\n'
                    'REQUIREMENTS:\n'
                    '- Necromancer class\n'
                    '- Level 44\n',
     'syntax': "cast 'plague strike' <target>",
     'level': 44,
     'mana': 55,
     'cooldown': 20,
 },
 'summon_gargoyle': {
     'category': 'spell',
     'classes': ['necromancer'],
     'title': 'Summon Gargoyle',
     'description': 'Summon a fearsome gargoyle from the shadows to fight for you.\n\n'
                    'MECHANICS:\n'
                    '- Summons a powerful flying pet\n'
                    '- Lasts 60 seconds\n'
                    '- 2 minute cooldown\n\n'
                    'REQUIREMENTS:\n'
                    '- Necromancer class\n'
                    '- Level 50\n',
     'syntax': "cast 'summon gargoyle'",
     'level': 50,
     'mana': 100,
     'cooldown': 120,
 },
 'soul_harvest': {
     'category': 'spell',
     'classes': ['necromancer'],
     'title': 'Soul Harvest',
     'description': 'Harvest the essence of fallen souls, gaining massive power.\n\n'
                    'MECHANICS:\n'
                    '- Gains soul fragments from nearby corpses\n'
                    '- Empowers necromancer abilities\n'
                    '- 2 minute cooldown\n\n'
                    'REQUIREMENTS:\n'
                    '- Necromancer class\n'
                    '- Level 56\n',
     'syntax': "cast 'soul harvest'",
     'level': 56,
     'mana': 80,
     'cooldown': 120,
 },
 'apocalypse_necro': {
     'category': 'spell',
     'classes': ['necromancer'],
     'title': 'Apocalypse',
     'description': 'CAPSTONE ABILITY: Raise EVERY corpse in the zone as your army.\n\n'
                    'MECHANICS:\n'
                    '- Raises all corpses in the zone\n'
                    '- Creates massive undead army\n'
                    '- 2 minute cooldown\n\n'
                    'REQUIREMENTS:\n'
                    '- Necromancer class\n'
                    '- Level 60\n',
     'syntax': "cast 'apocalypse'",
     'level': 60,
     'mana': 250,
     'cooldown': 120,
 },

 # ----- BARD LEVEL 31-60 -----
 'hymn_of_hope': {
     'category': 'spell',
     'classes': ['bard'],
     'title': 'Hymn of Hope',
     'description': 'Sing a hymn of hope that restores mana to your party.\n\n'
                    'MECHANICS:\n'
                    '- +100% mana regen for party\n'
                    '- +50 max mana\n'
                    '- 40 second duration\n'
                    '- 1 minute cooldown\n\n'
                    'REQUIREMENTS:\n'
                    '- Bard class\n'
                    '- Level 32\n',
     'syntax': "cast 'hymn of hope'",
     'level': 32,
     'mana': 50,
     'cooldown': 60,
 },
 'chord_of_disruption': {
     'category': 'spell',
     'classes': ['bard'],
     'title': 'Chord of Disruption',
     'description': 'Strike a discordant chord that silences all enemies in the room.\n\n'
                    'MECHANICS:\n'
                    '- AoE silence\n'
                    '- 8 second duration\n'
                    '- 45 second cooldown\n\n'
                    'REQUIREMENTS:\n'
                    '- Bard class\n'
                    '- Level 38\n',
     'syntax': "cast 'chord of disruption'",
     'level': 38,
     'mana': 70,
     'cooldown': 45,
 },
 'epic_tale': {
     'category': 'spell',
     'classes': ['bard'],
     'title': 'Epic Tale',
     'description': 'Weave an epic tale that buffs ALL stats for your party.\n\n'
                    'MECHANICS:\n'
                    '- +3 to ALL stats for party\n'
                    '- 60 second duration\n'
                    '- 2 minute cooldown\n\n'
                    'REQUIREMENTS:\n'
                    '- Bard class\n'
                    '- Level 44\n',
     'syntax': "cast 'epic tale'",
     'level': 44,
     'mana': 100,
     'cooldown': 120,
 },
 'siren_song': {
     'category': 'spell',
     'classes': ['bard'],
     'title': 'Siren Song',
     'description': 'Sing an irresistible siren song that charms all enemies.\n\n'
                    'MECHANICS:\n'
                    '- Mass charm effect\n'
                    '- 16 second duration\n'
                    '- 90 second cooldown\n\n'
                    'REQUIREMENTS:\n'
                    '- Bard class\n'
                    '- Level 50\n',
     'syntax': "cast 'siren song'",
     'level': 50,
     'mana': 80,
     'cooldown': 90,
 },
 'requiem': {
     'category': 'spell',
     'classes': ['bard'],
     'title': 'Requiem',
     'description': 'Begin a haunting requiem that drains the life of enemies over time.\n\n'
                    'MECHANICS:\n'
                    '- AoE DoT to all enemies\n'
                    '- 30 second duration\n'
                    '- 2 minute cooldown\n\n'
                    'REQUIREMENTS:\n'
                    '- Bard class\n'
                    '- Level 56\n',
     'syntax': "cast 'requiem'",
     'level': 56,
     'mana': 100,
     'cooldown': 120,
 },
 'magnum_opus': {
     'category': 'spell',
     'classes': ['bard'],
     'title': 'Magnum Opus',
     'description': 'CAPSTONE ABILITY: Perform your ultimate masterpiece.\n\n'
                    'MECHANICS:\n'
                    '- All songs active simultaneously\n'
                    '- +5 all stats\n'
                    '- +10 hit/damage\n'
                    '- Haste + 20% damage reduction\n'
                    '- 60 second duration\n'
                    '- 2 minute cooldown\n\n'
                    'REQUIREMENTS:\n'
                    '- Bard class\n'
                    '- Level 60\n',
     'syntax': "cast 'magnum opus'",
     'level': 60,
     'mana': 200,
     'cooldown': 120,
 },

 # ----- ASSASSIN LEVEL 31-60 -----
 'shadowstrike': {
     'category': 'skill',
     'classes': ['assassin'],
     'title': 'Shadowstrike',
     'description': 'Teleport through shadows behind your target and backstab them.\n\n'
                    'MECHANICS:\n'
                    '- Instant teleport to target\n'
                    '- Backstab damage\n'
                    '- 20 second cooldown\n\n'
                    'REQUIREMENTS:\n'
                    '- Assassin class\n'
                    '- Level 32\n',
     'syntax': 'shadowstrike <target>',
     'level': 32,
     'cooldown': 20,
 },
 'fan_of_knives': {
     'category': 'skill',
     'classes': ['assassin'],
     'title': 'Fan of Knives (Legacy)',
     'description': 'Legacy ability - removed from assassin core skills.\n'
                    'Replaced by the Intel system. See HELP ASSASSIN.',
     'syntax': 'fan_of_knives',
 },
 'rupture': {
     'category': 'skill',
     'classes': ['assassin'],
     'title': 'Rupture (Legacy)',
     'description': 'Legacy ability - removed from assassin core skills.\n'
                    'Poison DoTs are now handled through the Poison talent tree.\n'
                    'See HELP ASSASSIN.',
     'syntax': 'rupture',
 },
 'shadow_blades_master': {
     'category': 'skill',
     'classes': ['assassin'],
     'title': 'Shadow Blades (Legacy)',
     'description': 'Legacy ability - removed from assassin core skills.\n'
                    'Replaced by Shadow Blade talent (Shadow tree, Tier 5).\n'
                    'See HELP ASSASSIN.',
     'syntax': 'shadow_blades',
 },
 'vendetta_assassin': {
     'category': 'skill',
     'classes': ['assassin'],
     'title': 'Vendetta (Legacy)',
     'description': 'Legacy ability - replaced by the Intel system.\n'
                    'Use "mark" + build Intel + "execute_contract" instead.\n'
                    'See HELP INTEL, HELP EXECUTE_CONTRACT.',
     'syntax': 'vendetta',
 },
 'death_mark': {
     'category': 'skill',
     'classes': ['assassin'],
     'title': 'Death Mark (Legacy)',
     'description': 'Legacy ability - replaced by Execute Contract.\n'
                    'Build to Intel 10 and use "execute_contract" for instant kills.\n'
                    'See HELP EXECUTE_CONTRACT.',
     'syntax': 'death_mark',
 },
 # === CLASS REWORK WAVE 1 HELP ENTRIES ===
 'luck': {'category': 'guide',
          'description': 'The Luck System (Thief class)\n\nLuck is the thief\'s core resource (0-10).\n\nGENERATION:\n  Successful hit: 15% chance +1 Luck\n  Critical hit: always +1 Luck\n  Dodge/parry: +1 Luck\n  Cap: 10\n\nPASSIVE:\n  At Luck >= 5, dodging triggers a free counterattack.\n\nABILITIES:\n  pocket_sand (3) - Blind target 2 rounds. 20s CD.\n  low_blow (5) - Stun + damage. 30s CD.\n  rigged_dice (7) - 3 guaranteed crits. 45s CD.\n  jackpot (10) - 4x damage + steal gold. 60s CD.\n\nSee also: HELP THIEF',
          'title': 'Luck System'},
 'pocket_sand': {'category': 'skill', 'classes': ['thief'], 'description': 'Throw sand in your target\'s eyes!\n\nCost: 3 Luck\nEffect: Blind target for 2 rounds (50% miss chance)\nCooldown: 20 seconds\nCan open a fight: thrown at a foe you name, the fight begins.\n\nTalent synergies:\n- Dirty Fighting: +1 round blind per rank\n- Vanishing Act: enter stealth after using', 'syntax': 'pocket_sand [target]', 'title': 'Pocket Sand'},
 'low_blow': {'category': 'skill', 'classes': ['thief'], 'description': 'A devastating strike below the belt.\n\nCost: 5 Luck\nEffect: Stun target 1 round + weapon damage\nCooldown: 30 seconds\n\nTalent synergy:\n- Marked Man: target takes 10% more damage for 10s', 'syntax': 'low_blow', 'title': 'Low Blow'},
 'rigged_dice': {'category': 'skill', 'classes': ['thief'], 'description': 'Pull out your loaded dice.\n\nCost: 7 Luck\nEffect: Next 3 attacks are guaranteed crits\nCooldown: 45 seconds', 'syntax': 'rigged_dice', 'title': 'Rigged Dice'},
 'jackpot': {'category': 'skill', 'classes': ['thief'], 'description': 'Hit the jackpot!\n\nCost: 10 Luck\nEffect: 4x weapon damage + steal 25% of target gold\nCooldown: 60 seconds\n\nTalent synergies:\n- Jackpot Master: also stuns 1 round + heals 10% HP\n- Grand Heist: also steals an item from target', 'syntax': 'jackpot', 'title': 'Jackpot'},
 'soul_shards': {'category': 'guide',
                 'description': 'The Soul Shard System (Necromancer class)\n\nSoul Shards (0-10) are harvested from dying enemies.\n\nGENERATION:\n  Kill an enemy: +1 Shard\n  Kill undead: +2 Shards\n  Assist kill: +1 Shard\n\nPASSIVE:\n  +5% spell damage per Shard held (up to +50% at 10)\n\nABILITIES:\n  soul_bolt (2) - 2x spell damage. 10s CD.\n  drain_soul (3) - 1.5x spell damage + heal. 15s CD.\n  bone_shield (4) - Absorb 3 hits. 60s CD.\n  soul_reap (8) - Execute or 4x damage. 90s CD.\n\nSee also: HELP NECROMANCER',
                 'title': 'Soul Shard System'},
 'soul_bolt': {'category': 'skill', 'classes': ['necromancer'], 'description': 'Fire a bolt of shadow energy.\n\nCost: 2 Soul Shards\nDamage: 2x spell damage (INT*3 + Level*2)\nCooldown: 10 seconds', 'syntax': 'soul_bolt', 'title': 'Soul Bolt'},
 'drain_soul': {'category': 'skill', 'classes': ['necromancer'], 'description': 'Drain the life force from your target.\n\nCost: 3 Soul Shards\nDamage: 1.5x spell damage\nHeals you for the same amount\nCooldown: 15 seconds', 'syntax': 'drain_soul', 'title': 'Drain Soul'},
 'bone_shield': {'category': 'skill', 'classes': ['necromancer'], 'description': 'Surround yourself with a shield of bones.\n\nCost: 4 Soul Shards\nEffect: Absorbs next 3 hits (500 damage each)\nDuration: 60 seconds\nCooldown: 60 seconds\n\nTalent: Bone Armor Mastery increases absorb to 750', 'syntax': 'bone_shield', 'title': 'Bone Shield'},
 'soul_reap': {'category': 'skill', 'classes': ['necromancer'], 'description': 'Reap the soul of a weakened enemy.\n\nCost: 8 Soul Shards\nIf target below 25% HP (non-boss): instant kill\nBosses: 4x spell damage instead\nCooldown: 90 seconds', 'syntax': 'soul_reap', 'title': 'Soul Reap'},
 'holy_power': {'category': 'guide',
                'description': 'The Holy Power System (Paladin class)\n\nHoly Power (0-5) is built through righteous combat.\n\nGENERATION:\n  Melee hit: 25% chance +1\n  Smite/Bash: guaranteed +1\n  Healing: +1\n\nSPENDERS:\n  templars_verdict (3) - 2x weapon damage + holy\n  word_of_glory (3) - Heal self 30% max HP\n  divine_storm (5) - AoE holy damage. 30s CD.\n\nOATH SYSTEM:\n  oath vengeance - +15% dmg, -10% healing\n  oath devotion - +20% healing, +10% DR\n  oath justice - +10% dmg, +10% healing\n\nSee also: HELP PALADIN, HELP OATH',
                'title': 'Holy Power System'},
 'templars_verdict': {'category': 'skill', 'classes': ['paladin'], 'description': "Deliver divine judgment upon your enemy.\n\nCost: 3 Holy Power (spends all)\nDamage: 2x weapon damage + holy bonus\nNo cooldown\n\nAt 5 Holy Power with Sanctified Wrath talent: 3x damage", 'syntax': 'templars_verdict', 'title': "Templar's Verdict"},
 'word_of_glory': {'category': 'skill', 'classes': ['paladin'], 'description': 'Heal yourself with holy light.\n\nCost: 3 Holy Power\nHeals: 30% of max HP\nNo cooldown\n\nModified by Oath and Healing Light talent.', 'syntax': 'word_of_glory', 'title': 'Word of Glory'},
 'oath': {'category': 'skill', 'classes': ['paladin'], 'description': 'Swear a paladin oath.\n\nUsage: oath vengeance|devotion|justice\n\nVengeance: +15% damage, -10% healing, faster HP gen from hits\nDevotion: +20% healing, +10% DR, HP gen from heals\nJustice: +10% dmg, +10% healing, balanced\n\nSwitching oaths resets Holy Power to 0.', 'syntax': 'oath <type>', 'title': 'Oath'},
 'faith': {'category': 'guide',
           'description': 'The Faith System (Cleric class)\n\nFaith (0-10) is built through healing and holy actions.\n\nGENERATION:\n  Heal an ally: +1 Faith\n  Holy damage spell: +1 Faith\n  Shadow form: damage builds Faith instead\n  Below 30% HP when hit: +1 Faith (desperation)\n\nABILITIES:\n  divine_word (3) - AoE group heal 15% HP. 20s CD.\n  holy_fire (5) - Massive holy damage + DoT. 25s CD.\n  divine_intervention (10) - Invulnerable 8s. 5min CD.\n  shadowform - Toggle shadow form\n\nSee also: HELP CLERIC',
           'title': 'Faith System'},
 'divine_word': {'category': 'skill', 'classes': ['cleric'], 'description': 'Speak a divine word of healing.\n\nCost: 3 Faith\nEffect: Heals all group members in room for 15% max HP\nCooldown: 20 seconds\n\nReduced by 30% in shadow form.', 'syntax': 'divine_word', 'title': 'Divine Word'},
 'holy_fire': {'category': 'skill', 'classes': ['cleric'], 'description': 'Engulf your target in holy fire.\n\nCost: 5 Faith\nDamage: INT*5 + Level*3 + DoT (4 ticks)\nCooldown: 25 seconds', 'syntax': 'holy_fire', 'title': 'Holy Fire'},
 'divine_intervention': {'category': 'skill', 'classes': ['cleric'], 'description': 'Call upon divine power to protect.\n\nCost: 10 Faith\nEffect: Target becomes invulnerable for 8 seconds\nCooldown: 300 seconds (5 minutes)\n\nUsage: divine_intervention [target]', 'syntax': 'divine_intervention [target]', 'title': 'Divine Intervention'},
 'shadowform': {'category': 'skill', 'classes': ['cleric'], 'description': 'Toggle shadow form.\n\nIn shadow form:\n- +25% shadow damage\n- -30% healing done\n- Damage builds Faith instead of healing\n\nRequires Shadowform talent in the Shadow tree.', 'syntax': 'shadowform', 'title': 'Shadowform'},
 'arcane_charges': {'category': 'guide',
                    'description': 'The Arcane Charge System (Mage class)\n\n'
                                   'Mages build Arcane Charges through spellcasting.\n'
                                   'Each charge increases spell power but also mana cost.\n\n'
                                   'GENERATION:\n'
                                   '- Each offensive spell: +1 Arcane Charge (max 5)\n\n'
                                   'EFFECTS PER CHARGE:\n'
                                   '- +8% spell damage\n'
                                   '- +10% mana cost\n'
                                   '- At 5 charges: +40% damage, +50% mana cost\n\n'
                                   'SPENDING:\n'
                                   '- Arcane Barrage: consumes all charges for burst\n'
                                   '- Evocation: reset charges + restore 30% mana\n'
                                   '- Various talents spend charges for abilities\n\n'
                                   'DECAY:\n'
                                   '- Out of combat: -1 charge per 15 seconds\n\n'
                                   'TALENT SYNERGIES:\n'
                                   '- Arcane Potency: charge bonus +1% per rank\n'
                                   '- Arcane Stability: mana cost penalty reduced\n'
                                   '- Arcane Mastery: unlock 6th charge slot\n\n'
                                   'See also: HELP MAGE, HELP ARCANE_BARRAGE',
                    'title': 'Arcane Charges'},
 'arcane_barrage': {'category': 'skill', 'classes': ['mage'],
                    'description': 'Arcane Barrage - consume all Arcane Charges for burst damage.\n\n'
                                   'Usage: arcane_barrage\n\n'
                                   'Damage: charges × INT × 2\n'
                                   'More charges = bigger burst.\n'
                                   'No cooldown.\n\n'
                                   'See also: HELP ARCANE_CHARGES',
                    'syntax': 'arcane_barrage', 'title': 'Arcane Barrage'},
 'evocation': {'category': 'skill', 'classes': ['mage'],
               'description': 'Evocation - restore mana and reset charges.\n\n'
                              'Usage: evocation\n\n'
                              'Effects:\n'
                              '- Restores 30% max mana\n'
                              '- Resets Arcane Charges to 0\n'
                              'Cooldown: 120 seconds\n\n'
                              'Use when low on mana or to shed high charge mana costs.',
               'syntax': 'evocation', 'title': 'Evocation'},
 'arcane_blast': {'category': 'skill', 'classes': ['mage'],
                  'description': 'Arcane Blast - powerful arcane damage that builds charges.\n\n'
                                 'Usage: arcane_blast\n\n'
                                 'Damage: INT×3 + (charges × INT)\n'
                                 'Generates +1 Arcane Charge\n'
                                 'Cooldown: 8 seconds\n\n'
                                 'Your bread-and-butter damage + charge builder.',
                  'syntax': 'arcane_blast', 'title': 'Arcane Blast'},
 'focus_guide': {'category': 'guide',
                 'description': 'The Focus System (Ranger class)\n\n'
                                'Rangers build Focus through steady combat.\n'
                                'Spend Focus on powerful shots and pet commands.\n\n'
                                'GENERATION:\n'
                                '- Each melee/ranged hit: +10 Focus\n'
                                '- Each round in combat (passive): +5 Focus\n'
                                '- Dodge: +15 Focus\n'
                                '- Max: 100\n\n'
                                'ABILITIES:\n'
                                '- Aimed Shot (30 Focus): 2.5x damage, guaranteed hit\n'
                                '- Kill Command (25 Focus): pet attacks for 2x damage\n'
                                '- Rapid Fire (50 Focus): triple attack this round\n'
                                '- Hunter\'s Mark (free): +10% damage, +5 Focus/hit\n\n'
                                'AT 100 FOCUS:\n'
                                '- Next ability costs 50% less Focus\n\n'
                                'See also: HELP RANGER, HELP AIMED_SHOT',
                 'title': 'Focus (Ranger)'},
 'rage_guide': {'category': 'guide',
                'description': 'The Rage System (Warrior class)\n\n'
                               'Warriors build Rage through dealing and taking damage.\n\n'
                               'GENERATION:\n'
                               '- Dealing damage: +5 Rage + damage/20 bonus\n'
                               '- Taking damage: +3 Rage + damage_taken/30 bonus\n'
                               '- Battle Cry: instant +30 Rage\n'
                               '- Max: 100. Decays 5/tick out of combat.\n\n'
                               'STANCES:\n'
                               '- Battle: +5% damage, +5% Rage gen\n'
                               '- Defensive: -15% damage taken, -20% dealt\n'
                               '- Berserker: +25% dealt, +15% taken, +10% Rage gen\n\n'
                               'ABILITIES:\n'
                               '- Execute (30 Rage): 2x damage + Rage bonus, target <20% HP\n'
                               '- Mortal Strike (40 Rage): 2.5x damage + healing reduction\n'
                               '- Shield Wall (50 Rage): 50% damage reduction 10s\n'
                               '- Rampage (40 Rage): 3 rapid strikes\n'
                               '- Bladestorm (60 Rage): AoE spin, 3 rounds\n\n'
                               'See also: HELP WARRIOR, HELP STANCE',
                'title': 'Rage (Warrior)'},
 'battle_cry': {'category': 'skill', 'classes': ['warrior'],
                'description': 'Battle Cry - generate Rage and buff damage.\n\n'
                               'Usage: battle_cry\n\n'
                               'Effects:\n'
                               '- Instantly generates 30 Rage\n'
                               '- +10% damage for 6 seconds\n'
                               'Cooldown: 60 seconds\n'
                               'Cost: 0 Rage\n\n'
                               'Your Rage kickstarter. Use at fight start.',
                'syntax': 'battle_cry', 'title': 'Battle Cry'},
 'inspiration': {'category': 'guide',
                  'description': 'The Inspiration System (Bard class)\n\n'
                                 'Bards build Inspiration through songs, healing, and combat.\n\n'
                                 'GENERATION:\n'
                                 '- Performing a song: +1 per regen tick\n'
                                 '- Landing a hit: +1 (25% chance)\n'
                                 '- Healing an ally: +1\n'
                                 '- Group member kills a mob: +1\n'
                                 '- Max: 10\n\n'
                                 'PASSIVE:\n'
                                 '- Each Inspiration point = +1% to all song buffs\n\n'
                                 'ABILITIES:\n'
                                 '- Crescendo (5 Insp): Massive sonic damage (INT×5)\n'
                                 '- Encore (3 Insp): Double-strength song reapply\n'
                                 '- Discordant Note (4 Insp): Silence + sonic damage\n'
                                 '- Magnum Opus (10 Insp): Party-wide +20% everything\n\n'
                                 'See also: HELP BARD, HELP CRESCENDO',
                  'title': 'Inspiration'},
 'focus': {'category': 'guide',
           'description': 'The Focus System (Ranger class)\n\n'
                          'Rangers build Focus through combat and agility.\n\n'
                          'GENERATION:\n'
                          '- Hitting a target: +10 Focus (+5 bonus on marked target)\n'
                          '- Dodging an attack: +15 Focus\n'
                          '- Passive in combat: +5 per regen tick\n'
                          '- Max: 100\n\n'
                          'SPENDING:\n'
                          '- Aimed Shot: costs Focus for a powerful shot\n'
                          '- Kill Command: pet attack, costs Focus\n'
                          '- Rapid Fire: multi-shot volley, costs Focus\n'
                          '- Bestial Wrath: pet enrage, costs Focus\n'
                          '- Various talent abilities cost Focus\n\n'
                          'DECAY:\n'
                          '- Focus does not decay out of combat\n\n'
                          'TALENT SYNERGIES:\n'
                          '- Master Marksman: +2 Focus per hit per rank\n'
                          '- Sniper Training: stealth attacks generate 30 Focus\n\n'
                          'See also: HELP RANGER, HELP AIMED_SHOT, HELP HUNTERS_MARK',
           'title': 'Focus'},
 'inspiration_guide': {'category': 'guide',
                       'description': 'The Inspiration System (Bard class)\n\n'
                                      'Bards build Inspiration through songs and combat.\n\n'
                                      'GENERATION:\n'
                                      '- Performing a song: +1 per round\n'
                                      '- Landing a hit: +1 (25% chance)\n'
                                      '- Ally heals or kills nearby: +1\n'
                                      '- Max: 10\n\n'
                                      'PASSIVE:\n'
                                      '- Each Inspiration point = +1% to all song buffs\n\n'
                                      'ABILITIES:\n'
                                      '- Crescendo (5 Insp): Massive sonic damage (INT×5)\n'
                                      '- Encore (3 Insp): Double-strength song reapply\n'
                                      '- Discordant Note (4 Insp): Silence + sonic damage\n'
                                      '- Magnum Opus (10 Insp): Party-wide +20% everything\n\n'
                                      'See also: HELP BARD, HELP CRESCENDO',
                       'title': 'Inspiration (Bard)'},
 'crescendo': {'category': 'skill', 'classes': ['bard'],
               'description': 'Crescendo - massive sonic burst.\n\n'
                              'Usage: crescendo\n\n'
                              'Damage: INT × 5\n'
                              'Cost: 5 Inspiration\n'
                              'Cooldown: 20 seconds\n\n'
                              'Your big damage ability. Build Inspiration through\n'
                              'songs and combat, then unleash.',
               'syntax': 'crescendo', 'title': 'Crescendo'},
 'discordant_note': {'category': 'skill', 'classes': ['bard'],
                     'description': 'Discordant Note - silence and damage.\n\n'
                                    'Usage: discordant_note\n\n'
                                    'Effects:\n'
                                    '- Silences target for 2 rounds (no spellcasting)\n'
                                    '- Deals INT × 3 sonic damage\n'
                                    'Cost: 4 Inspiration\n'
                                    'Cooldown: 25 seconds',
                     'syntax': 'discordant_note', 'title': 'Discordant Note'},
 'charge': {'category': 'skill',
            'classes': ['warrior'],
            'description': 'Charge — Opener (🟢) for Warriors.\n'
                           'Rush at target, deals weapon damage. Must not be in combat (unless Battering Ram talent).\n'
                           'Starts chain + initiates combat. Cooldown: 15s.\n\n'
                           'CHAIN TYPE: Opener — starts chain at 1.',
            'syntax': 'charge <target>',
            'title': 'Charge'},
 'shield_slam': {'category': 'skill',
                 'classes': ['warrior'],
                 'description': 'Shield Slam — Opener (🟢) for Warriors.\n'
                                'Requires shield. Deals weapon damage + shield armor value. Starts chain.\n'
                                'Cooldown: 10s.\n\n'
                                'CHAIN TYPE: Opener — starts chain at 1.',
                 'syntax': 'shield_slam [target]',
                 'title': 'Shield Slam'},
 'rend': {'category': 'skill',
          'classes': ['warrior'],
          'description': 'Rend — Chain ability (🟡) for Warriors.\n'
                         'Apply a bleed DoT (weapon damage / 4 per tick, 4 ticks). Extends chain.\n'
                         'Cooldown: 8s.\n\n'
                         'CHAIN TYPE: Chain — extends combo by 1.',
          'syntax': 'rend [target]',
          'title': 'Rend'},
 'hamstring': {'category': 'skill',
               'classes': ['warrior'],
               'description': 'Hamstring — Chain ability (🟡) for Warriors.\n'
                              'Slow target + deal 0.75x weapon damage. Extends chain.\n'
                              'Cooldown: 6s.\n\n'
                              'CHAIN TYPE: Chain — extends combo by 1.',
               'syntax': 'hamstring [target]',
               'title': 'Hamstring'},
 'devastating_blow': {'category': 'skill',
                      'classes': ['warrior'],
                      'description': 'Devastating Blow — Finisher (🔴) for Warriors.\n'
                                     'Single target. 3x weapon damage + stun 1 round.\n'
                                     'At chain 4+: 4x + stun 2 rounds. Resets chain.\n'
                                     'Cooldown: 20s.\n\n'
                                     'CHAIN TYPE: Finisher — consumes chain.',
                      'syntax': 'devastating_blow [target]',
                      'title': 'Devastating Blow'},
 'chains': {'category': 'guide',
            'description': 'Warrior Combo Chain System\n\n'
                           'Warriors chain abilities in sequence for escalating power.\n\n'
                           'CHAIN TYPES:\n'
                           '  🟢 Openers — Start or reset chain (Bash, Charge, Shield Slam)\n'
                           '  🟡 Chains  — Extend combo +1 (Cleave, Rend, Disarm, Hamstring, Shield Wall)\n'
                           '  🔴 Finishers — Consume chain for massive damage (Execute, Bladestorm, Devastating Blow)\n\n'
                           'CHAIN RULES:\n'
                           '  - Each chain link: +15% damage to next ability\n'
                           '  - Chain max: 5 (7 with Chain Mastery talent)\n'
                           '  - Chain decays if no chain ability within 8 seconds\n'
                           '  - Openers mid-chain reset and start fresh at 1\n'
                           '  - Finishers at chain 0 work but with no bonus\n\n'
                           'NAMED COMBOS:\n'
                           '  Specific sequences trigger powerful bonus effects!\n'
                           '  See HELP COMBOS for the full list.\n\n'
                           'TALENT TREES:\n'
                           '  Vanguard — Stronger openers, chain initiation\n'
                           '  Tactician — Longer chains, defensive bonuses\n'
                           '  Executioner — Devastating finishers, combo mastery',
            'title': 'Combo Chains'},
 'combos': {'category': 'guide',
            'description': 'Named Combos — Warrior\n\n'
                           'Chain specific ability sequences to trigger powerful bonus effects!\n\n'
                           "  Bash → Rend → Execute = Butcher's Sequence\n"
                           '    Effect: Execute ignores armor\n\n'
                           '  Shield Slam → Disarm → Shield Slam = Fortress\n'
                           '    Effect: 50% damage reduction for 6s\n\n'
                           '  Charge → Cleave → Rend → Cleave → Bladestorm = Whirlwind of Steel\n'
                           '    Effect: Bladestorm hits 3x and heals 10% HP per enemy\n\n'
                           '  Hamstring → Rend → Hamstring → Execute = Death by a Thousand Cuts\n'
                           '    Effect: Execute deals +50% bonus per bleed on target\n\n'
                           '  Bash → Cleave → Bash = Stunning Assault\n'
                           '    Effect: Stun target for 2 rounds\n\n'
                           '  Shield Slam → Shield Wall → Shield Slam = Iron Wall\n'
                           '    Effect: Shield Wall duration doubled\n\n'
                           '  Charge → Rend → Cleave → Execute = Berserker Rush\n'
                           '    Effect: Execute damage tripled\n\n'
                           '  Bash → Cleave → Rend → Cleave → Devastating Blow = Titan\'s Combo\n'
                           '    Effect: Devastating Blow hits ALL enemies in room',
            'title': 'Named Combos'},
 'warrior': {'category': 'class',
             'description': 'The Warrior class — master of Martial Doctrines and Ability Evolution.\n\n'
                            'CORE MECHANIC — MOMENTUM (0-10):\n'
                            '  Use DIFFERENT abilities in sequence to build Momentum.\n'
                            '  Same ability twice in a row resets Momentum to 0.\n'
                            '  Each point: +5% damage, +3% attack speed.\n'
                            '  At 10: UNSTOPPABLE — CC immune for 4 rounds, +25% damage.\n\n'
                            'WAR DOCTRINES:\n'
                            '  Swear an oath to shape your abilities:\n'
                            '  Iron Wall   — Shields, taunts, outlasting\n'
                            '  Berserker   — Reckless offense, self-damage for power\n'
                            '  Warlord     — Tactical CC, debuffs, group utility\n'
                            '  Use "swear <doctrine>" to choose.\n\n'
                            'ABILITY EVOLUTION:\n'
                            '  6 base abilities evolve through use (50/150/300 uses).\n'
                            '  strike, bash, cleave, charge, rally, execute\n'
                            '  Each evolution is doctrine-specific and permanent.\n'
                            '  Use "evolve" to see status, "evolve <ability>" to evolve.\n\n'
                            'See also: HELP DOCTRINE, HELP MOMENTUM, HELP EVOLVE,\n'
                            '          HELP STRIKE, HELP BASH, HELP CLEAVE,\n'
                            '          HELP CHARGE, HELP RALLY, HELP EXECUTE',
             'title': 'Warrior'},
 'doctrine': {'category': 'guide',
              'description': 'War Doctrines — Warrior Specialization\n\n'
                             'Warriors choose a War Doctrine that shapes their abilities.\n\n'
                             'IRON WALL:\n'
                             '  Defensive mastery. Shields, taunts, damage reduction.\n'
                             '  Momentum bonus: +2% damage reduction per point.\n'
                             '  Your abilities generate shields and taunt enemies.\n\n'
                             'BERSERKER:\n'
                             '  Reckless offense. Trade HP for devastating damage.\n'
                             '  Momentum bonus: +2% lifesteal per point.\n'
                             '  Abilities cost HP but deal massive damage.\n\n'
                             'WARLORD:\n'
                             '  Tactical mastery. CC, debuffs, group utility.\n'
                             '  Momentum bonus: +1 round debuff duration per 3 Momentum.\n'
                             '  Abilities apply debuffs and buff your group.\n\n'
                             'Use "swear <doctrine>" to choose or switch.\n'
                             'WARNING: Switching resets all ability evolutions!\n\n'
                             'See also: HELP WARRIOR, HELP IRON_WALL, HELP BERSERKER, HELP WARLORD',
              'title': 'War Doctrines'},
 'swear': {'category': 'command',
           'description': 'Swear to a War Doctrine.\n\n'
                          'Usage: swear <doctrine>\n\n'
                          'Available doctrines: iron_wall, berserker, warlord\n\n'
                          'Switching doctrines resets ALL ability evolutions.\n'
                          'You will be asked to confirm before switching.',
           'syntax': 'swear <doctrine>',
           'title': 'Swear'},
 'evolve': {'category': 'command',
            'description': 'View or perform ability evolution.\n\n'
                           'Usage:\n'
                           '  evolve           — Show all abilities and evolution status\n'
                           '  evolve <ability> — Evolve an ability at its threshold\n\n'
                           'Abilities evolve at 50, 150, and 300 uses.\n'
                           'Each evolution is specific to your current doctrine.\n'
                           'Evolutions are permanent until you switch doctrines.',
            'syntax': 'evolve [ability]',
            'title': 'Evolve'},
 'momentum': {'category': 'guide',
              'description': 'Momentum — Warrior Combat Resource (0-10)\n\n'
                             'Build Momentum by using DIFFERENT abilities in sequence.\n'
                             'Using the same ability twice resets Momentum to 0.\n\n'
                             'BONUSES PER POINT:\n'
                             '  +5% damage\n'
                             '  +3% attack speed (reduced cooldowns)\n\n'
                             'DOCTRINE BONUSES:\n'
                             '  Iron Wall: +2% damage reduction per point\n'
                             '  Berserker: +2% lifesteal per point\n'
                             '  Warlord: +1 round debuff duration per 3 points\n\n'
                             'AT 10 MOMENTUM — UNSTOPPABLE:\n'
                             '  CC immune for 4 combat rounds\n'
                             '  All abilities deal +25% bonus damage\n\n'
                             'Momentum decays by 1 per regen tick when not in combat.',
              'title': 'Momentum'},
 'strike': {'category': 'skill',
            'classes': ['warrior'],
            'description': 'Strike — Enhanced basic attack. 4s cooldown.\n'
                           'Deals 1.5x weapon damage.\n\n'
                           'Evolutions (at 50/150/300 uses):\n'
                           '  Iron Wall: shield_strike → aegis_strike → immortal_strike\n'
                           '  Berserker: brutal_strike → savage_strike → deathwish_strike\n'
                           '  Warlord: precision_strike → analytical_strike → mastermind_strike',
            'syntax': 'strike [target]',
            'title': 'Strike'},
 'iron_wall': {'category': 'guide',
               'description': 'Iron Wall Doctrine — The Unbreakable Line\n\n'
                              'Focus: Shields, taunts, damage reduction, outlasting.\n'
                              'Momentum: +2% damage reduction per point.\n\n'
                              'EVOLUTION EXAMPLES:\n'
                              '  strike → shield_strike → aegis_strike → immortal_strike\n'
                              '  bash → fortress_bash → bastion_bash → unbreakable_bash\n'
                              '  rally → stand_your_ground → immovable_object → eternal_guardian\n'
                              '  execute → merciful_end → righteous_execution → divine_judgment',
               'title': 'Iron Wall'},
 'berserker': {'category': 'guide',
               'description': 'Berserker Doctrine — Pain is Power\n\n'
                              'Focus: Self-damage for devastating offense.\n'
                              'Momentum: +2% lifesteal per point.\n\n'
                              'EVOLUTION EXAMPLES:\n'
                              '  strike → brutal_strike → savage_strike → deathwish_strike\n'
                              '  charge → reckless_charge → death_from_above → extinction_event\n'
                              '  rally → blood_frenzy → berserker_rage → war_incarnate\n'
                              '  execute → overkill → massacre → annihilation',
               'title': 'Berserker'},
 'warlord': {'category': 'guide',
             'description': 'Warlord Doctrine — The Tactician\n\n'
                            'Focus: CC, debuffs, group utility.\n'
                            'Momentum: +1 round debuff duration per 3 points.\n\n'
                            'EVOLUTION EXAMPLES:\n'
                            '  strike → precision_strike → analytical_strike → mastermind_strike\n'
                            '  bash → concussive_bash → shockwave_bash → domination_bash\n'
                            '  rally → battle_orders → inspiring_command → supreme_command\n'
                            '  execute → subjugate → total_domination → absolute_authority',
             'title': 'Warlord'},
 'crafting': {'category': 'command',
              'description': 'The crafting system lets you gather materials and create items.\n\n'
                             'GATHERING COMMANDS:\n'
                             '  mine       — Mine ore from mountain/cave rooms\n'
                             '  forage     — Gather herbs from forest/field rooms\n'
                             '  skin [corpse] — Skin animal corpses for hides\n'
                             '  fish       — Fish in water rooms\n'
                             '  gather     — Auto-detect and gather from your environment\n\n'
                             'CRAFTING COMMANDS:\n'
                             '  craft list        — Show recipes available at current station\n'
                             '  craft <recipe_id> — Craft an item (must be at correct station)\n'
                             '  recipes [discipline] — Show all your known recipes\n\n'
                             'CRAFTING STATIONS (found in Garathorm shops):\n'
                             '  Forge (Weapon Shop / Armory) — Blacksmithing\n'
                             '  Alchemy Table (Magic Shop) — Alchemy\n'
                             '  Workbench (General Store) — Leatherworking\n'
                             '  Enchanting Circle (Mages Guild) — Enchanting\n\n'
                             'DISCIPLINES: Blacksmithing, Alchemy, Leatherworking, Enchanting\n'
                             'Each has its own level (1-20) gained by crafting.\n\n'
                             'RECIPE DISCOVERY: Learn recipes from scrolls, quest rewards, or drops.\n'
                             'Everyone starts with: Copper Dagger, Healing Potion, Leather Vest.\n\n'
                             'CRITICAL CRAFTS: 5% chance to create a superior quality item (+1 stats).\n'
                             'ENCHANTING: Requires the target item to be equipped.',
              'syntax': 'craft <recipe> | craft list | recipes | mine | forage | skin | fish',
              'title': 'Crafting System'},
 'mine': {'category': 'command',
          'description': 'Mine ore from mountain, hills, or dungeon rooms.\n'
                         'Uses the mining skill. Higher skill = better chance and rarer ores.\n'
                         'Costs 5 movement points per attempt.',
          'syntax': 'mine',
          'title': 'Mine'},
 'forage': {'category': 'command',
            'description': 'Forage for herbs in forest, field, or swamp rooms.\n'
                           'Uses the herbalism skill. Higher skill = rarer herbs.\n'
                           'Costs 3 movement points per attempt.',
            'syntax': 'forage',
            'title': 'Forage'},
 'skin': {'category': 'command',
          'description': 'Skin an animal corpse to obtain hides and pelts.\n'
                         'Uses the skinning skill. The type of hide depends on the creature.\n'
                         'Each corpse can only be skinned once. Costs 3 movement points.',
          'syntax': 'skin [corpse]',
          'title': 'Skin'},
 'fish': {'category': 'command',
          'description': 'Fish in water rooms to catch fish.\n'
                         'Uses the fishing skill. Rare golden carp have alchemical uses.\n'
                         'Costs 3 movement points per attempt.',
          'syntax': 'fish',
          'title': 'Fish'},
 'recipes': {'category': 'command',
             'description': 'Display all recipes you have learned, organized by discipline.\n'
                            'Shows crafting level, XP progress, required materials, and level.\n'
                            'Filter by discipline: recipes blacksmithing',
             'syntax': 'recipes [discipline]',
             'title': 'Recipes'},
}

# Category index for help listing
# Social & Communication help entries
HELP_TOPICS.update({
    'global': {'category': 'command', 'description': 'Send a message on the global chat channel.\n\nUsage: global <message>\n\nAll online players with the channel enabled will see your message.\nRate limited to prevent spam.\n\nSee also: channel, trade, newbie, lfg', 'syntax': 'global <message>', 'title': 'Global Chat'},
    'newbie_channel': {'category': 'command', 'description': 'Send a message on the newbie help channel.\n\nUsage: newbie <message>\n\nAvailable to players level 1-15 and designated helpers.', 'syntax': 'newbie <message>', 'title': 'Newbie Channel'},
    'newbie': {'category': 'general', 'syntax': 'help newbie', 'title': 'New Player Guide',
        'description': """Welcome to Misthollow! Here's everything you need to know, in the order you'll need it.

GETTING STARTED (Level 1-5)
  Movement:    north, south, east, west, up, down (or n, s, e, w, u, d)
  Look around: 'look' or 'l' to see the room, 'look <thing>' to examine
  Your stats:  'score' shows HP, mana, class resource, and stats
  Gear:        'equipment' (eq) and 'inventory' (i)
  Combat:      'kill <target>' to attack, 'flee' to escape
  Healing:     'rest' to recover, 'eat'/'drink' for sustenance
  Shops:       'list' to browse, 'buy <item>', 'sell <item>'
  Hint:        'hint' gives guidance on your current tutorial quest

SKILLS & CLASS RESOURCES (Level 1+)
  Type 'skills' and 'spells' to see your abilities.
  Each class has a unique resource shown in your 'score':
    Warrior: Rage (builds in combat)    Mage: Mana (spent on spells)
    Thief: Combo Points (build & spend) Cleric: Divine Favor (from healing)
    Ranger: Focus (builds in combat)    Paladin: Holy Power (radiant energy)
    Bard: Inspiration (from performing) Necromancer: Soul Fragments (from kills)
  Use 'practice' at a guildmaster to improve skills.

COMMUNICATION
  'say <msg>'       - Talk to people in your room
  'tell <player> <msg>' - Private message
  'global <msg>'    - Global chat channel
  'newbie <msg>'    - New player help channel (levels 1-15)
  'channel list'    - See all available channels
  'who'             - See who's online

QUESTS & EXPLORATION
  NPCs with [!] have quests for you — type 'talk <name>'
  NPCs with [?] are waiting for you to complete a quest
  'quests'          - View your active quest log
  'hint'            - Get help on your current objective
  Explore! You earn bonus XP for discovering new rooms.

GROUPING (Level 1+)
  'group invite <player>' - Invite someone to your group
  'group'            - See your group status
  'gtell <msg>'      - Talk to your group
  Groups share XP and make tough fights easier!

CRAFTING & GATHERING (Level 5+)
  Some rooms have resource nodes — look for them as you explore.
  'mine'             - Mine ore from rock deposits
  'forage'           - Gather herbs and plants
  'fish'             - Fish in bodies of water
  'craft'            - Combine materials into gear

TALENTS (Level 10)
  At level 10 you unlock talents! Type 'talents' to see your tree.
  Customize your build — respec available later.

COMPANIONS (Level 20)
  At level 20 you can recruit a companion! Type 'companion' to learn more.
  They fight alongside you and have their own abilities.

MOUNTS (Level 15+)
  Purchase or tame mounts for faster travel.
  'mount' and 'dismount' to ride. Some mounts are combat-capable!

HOUSING (Level 20+)
  Buy a home in the Realms! 'housing' for details.
  Decorate, store items, and invite friends.

ACHIEVEMENTS
  'achievements' — Track your progress across dozens of goals.
  Earn titles, gold, and bragging rights!

PvP ARENA (Level 10+)
  'arena' — Challenge other players in structured PvP.
  Earn PvP rating and exclusive rewards.

PRESTIGE CLASSES (Level 50)
  At the level cap, unlock powerful prestige specializations.
  Type 'help prestige' when you reach level 50.

USEFUL COMMANDS
  'help <topic>'     - Detailed help on any command
  'commands'         - Full command list
  'consider <mob>'   - Check if you can handle a fight
  'map'              - View a web-based area map
  'recall'           - Return to the Temple (costs move)

Need help? Use the 'newbie' channel — friendly players are always around!"""},
    'trade_channel': {'category': 'command', 'description': 'Send a message on the trade/economy channel.\n\nUsage: trade <message>', 'syntax': 'trade <message>', 'title': 'Trade Channel'},
    'lfg_channel': {'category': 'command', 'description': 'Send a message on the Looking For Group channel.\n\nUsage: lfg <message>', 'syntax': 'lfg <message>', 'title': 'LFG Channel'},
    'channel': {'category': 'command', 'description': 'Manage your chat channel subscriptions.\n\nUsage:\n  channel list         - Show all channels\n  channel on <name>    - Enable a channel\n  channel off <name>   - Disable a channel\n\nChannels: global, newbie, trade, lfg', 'syntax': 'channel list | channel on/off <name>', 'title': 'Channel Management'},
    'friend': {'category': 'command', 'description': 'Manage your friends list.\n\nUsage:\n  friend list          - Show friends and online status\n  friend add <player>  - Add a friend\n  friend remove <player> - Remove a friend\n  friend notify        - Toggle login/logout notifications', 'syntax': 'friend add/remove/list/notify', 'title': 'Friends List'},
    'ignore': {'category': 'command', 'description': 'Ignore a player, blocking their tells, channels, and emotes.\n\nUsage:\n  ignore              - Show your ignore list\n  ignore <player>     - Add to ignore list\n  unignore <player>   - Remove from ignore list', 'syntax': 'ignore [player]', 'title': 'Ignore'},
    'note': {'category': 'command', 'description': 'Keep private notes about other players (only you see them).\n\nUsage:\n  note                - Show all noted players\n  note <player>       - Show notes for a player\n  note <player> <text> - Add a note', 'syntax': 'note [player] [text]', 'title': 'Player Notes'},
    'finger': {'category': 'command', 'description': 'Show detailed info about a player (online or offline).\n\nUsage: finger <player>\nAlias: whois\n\nShows race, class, level, prestige, guild, last login, playtime,\nPvP rating, achievements, and faction standings.', 'syntax': 'finger <player>', 'title': 'Finger / Whois'},
    'accept': {'category': 'command', 'description': 'Accept a pending trade or duel request.\n\nUsage: accept\n\nSee also: trade, duel, decline', 'syntax': 'accept', 'title': 'Accept'},
    'decline': {'category': 'command', 'description': 'Decline a pending trade or duel request.\n\nUsage: decline\n\nSee also: trade, duel, accept', 'syntax': 'decline', 'title': 'Decline'},
    'duel': {'category': 'command', 'description': 'Challenge another player to a duel.\n\nUsage: duel <player>\n\nBoth players must accept. Death in a duel is non-permanent.\n\nSee also: accept, decline, arena', 'syntax': 'duel <player>', 'title': 'Duel'},
    'lfg': {'category': 'command', 'description': 'Send a message on the Looking For Group channel.\n\nUsage: lfg <message>\n\nSee also: channel, group', 'syntax': 'lfg <message>', 'title': 'LFG'},
    'mail': {'category': 'command', 'description': 'In-game mail system for offline messaging.\n\nUsage:\n  mail             - Check your mailbox\n  mail read <id>   - Read a message\n  mail send <player> <subject> - Send mail\n  mail delete <id> - Delete a message\n\nSee also: tell, friend', 'syntax': 'mail [read|send|delete] [args]', 'title': 'Mail'},
    'newbie': {'category': 'command', 'description': 'Send a message on the newbie help channel.\n\nUsage: newbie <message>\n\nAvailable to all players. Helpers and experienced players often respond.\n\nSee also: channel, help', 'syntax': 'newbie <message>', 'title': 'Newbie'},
    'prestige': {'category': 'command', 'description': 'View or select a prestige class.\n\nUsage:\n  prestige           - Show available prestige classes\n  prestige <class>   - Select a prestige class\n\nPrestige classes unlock at level 30+ with specific requirements.\nThey grant powerful new abilities and specialization.\n\nSee also: class, skills, spells', 'syntax': 'prestige [class]', 'title': 'Prestige Classes'},
    'respec': {'category': 'command', 'description': 'Reset your skill and talent points for redistribution.\n\nUsage: respec\n\nCosts gold based on level. Resets all trained skills and talents.\n\nSee also: practice, train, talents', 'syntax': 'respec', 'title': 'Respec'},
    'specialize': {'category': 'command', 'description': 'Choose a class specialization path.\n\nUsage: specialize <path>\n\nSee also: prestige, class', 'syntax': 'specialize <path>', 'title': 'Specialize'},
    'slip': {'category': 'command', 'description': 'Slip gold to another player covertly (thief skill).\n\nUsage: slip <amount> <player>\n\nRequires the slip skill. May go unnoticed by others.\n\nSee also: give, steal', 'syntax': 'slip <amount> <player>', 'title': 'Slip'},
    'trade': {'category': 'command', 'description': 'Initiate a trade with another player.\n\nUsage:\n  trade <player>         - Request a trade\n  trade add <item>       - Add item to trade window\n  trade gold <amount>    - Offer gold\n  trade confirm          - Confirm your side\n  trade cancel           - Cancel trade\n\nSee also: accept, decline, auction', 'syntax': 'trade <player>', 'title': 'Trade'},
    'unignore': {'category': 'command', 'description': 'Remove a player from your ignore list.\n\nUsage: unignore <player>\n\nSee also: ignore', 'syntax': 'unignore <player>', 'title': 'Unignore'},
    'use': {'category': 'command', 'description': 'Use an item from your inventory.\n\nUsage: use <item>\n\nActivates the special effect of usable items like potions, scrolls, wands.\n\nSee also: quaff, recite, zap', 'syntax': 'use <item>', 'title': 'Use'},
    'vnums': {'category': 'command', 'description': 'Toggle vnum display in room names (builder/immortal tool).\n\nUsage: vnums\n\nSee also: goto, stat', 'syntax': 'vnums', 'title': 'Vnums'},
    'wevent': {'category': 'command', 'description': 'View current and upcoming world events.\n\nUsage: wevent [list]\n\nShows active world events, invasions, and special happenings.\n\nSee also: time, weather', 'syntax': 'wevent [list]', 'title': 'World Events'},
    'whois': {'category': 'command', 'description': 'Show info about a player. Alias for finger.\n\nUsage: whois <player>\n\nSee also: finger, who', 'syntax': 'whois <player>', 'title': 'Whois'},
})

HELP_CATEGORIES = {'class': ['assassin', 'bard', 'cleric', 'mage', 'necromancer', 'paladin', 'ranger', 'thief', 'warrior'],
 'command': ['account',
             'achievements',
             'adrenaline_rush',
             'advance',
             'ai',
             'aimed_shot',
             'aistatus',
             'alias',
             'animate',
             'answer',
             'apologize',
             'ascii',
             'ask',
             'assist',
             'at',
             'attack',
             'auction',
             'aura',
             'autoattack',
             'autocombat',
             'autoexit',
             'autogold',
             'autoloot',
             'autorecall',
             'avatar_of_war',
             'backup',
             'balance',
             'bestial_wrath',
             'bind',
             'black_arrow',
             'blade_dance',
             'bladestorm',
             'blush',
             'bow',
             'brief',
             'bug',
             'buy',
             'cackle',
             'cast',
             'changelog',
             'chat',
             'chathistory',
             'cheer',
             'clear',
             'cloak_of_shadows',
             'close',
             'cold_blood',
             'collections',
             'color',
             'combat',
             'combo',
             'comfort',
             'commands',
             'compact',
             'companion',
             'companions',
             'compare',
             'consider',
             'cover',
             'craft',
             'cringe',
             'crippling_poison',
             'crusader_strike',
             'cry',
             'daily',
             'dance',
             'dc',
             'deadly_poison',
             'death_from_above',
             'deposit',
             'diagnose',
             'dismiss',
             'dismount',
             'disengage',
             'display',
             'divine_storm',
             'divinefavor',
             'donate',
             'down',
             'drink',
             'drink_alt',
             'drop',
             'dungeon',
             'east',
             'eat',
             'echo',
             'emote',
             'encore',
             'enter',
             'escape',
             'equipment',
             'eviscerate',
             'examine',
             'execute',
             'execute_contract',
             'exits',
             'expose',
             'explosive_trap',
             'faction',
             'fill',
             'find',
             'flee',
             'follow',
             'force',
             'freeze',
             'gather',
             'gecho',
             'get',
             'giggle',
             'give',
             'glare',
             'gossip',
             'goto',
             'grats',
             'greet',
             'grin',
             'group',
             'grumble',
             'gtell',
             'help',
             'hint',
             'hire',
             'holler',
             'holylight',
             'holysmite',
             'house',
             'hug',
             'hunters_mark',
             'idea',
             'ignorepain',
             'imbue',
             'immlist',
             'info',
             'interrupt',
             'inventory',
             'invis',
             'journal',
             'judgment',
             'junk',
             'kidneyshot',
             'kill',
             'killing_spree',
             'knock',
             'label',
             'laugh',
             'layhands',
             'leaderboard',
             'leave',
             'levels',
             'list',
             'load',
             'lock',
             'look',
             'loot',
             'map',
             'mapurl',
             'mark',
             'marked_for_death',
             'marked_shot',
             'medit',
             'minimap',
             'minions',
             'mlist',
             'mload',
             'mock',
             'mortal_strike',
             'motd',
             'mount',
             'mounts',
             'move',
             'mute',
             'mutilate',
             'newgameplus',
             'news',
             'nod',
             'nohassle',
             'norepeat',
             'north',
             'noshout',
             'notell',
             'notick',
             'oedit',
             'olist',
             'oload',
             'open',
             'order',
             'overpower',
             'pat',
             'peace',
             'perform',
             'pet',
             'pets',
             'pick',
             'poke',
             'policy',
             'ponder',
             'pour',
             'practice',
             'predators_mark',
             'preparation',
             'prompt',
             'protect',
             'pull',
             'purge',
             'push',
             'put',
             'qsay',
             'quaff',
             'quest',
             'questlog',
             'quit',
             'rage',
             'raise',
             'rampage',
             'rapid_shot',
             'read',
             'recall',
             'recite',
             'redit',
             'relight',
             'remove',
             'rend',
             'rent',
             'report',
             'reputation',
             'rest',
             'restore',
             'retrieve',
             'ritual',
             'rlist',
             'sacred_shield',
             'sacrifice',
             'salute',
             'save',
             'say',
             'score',
             'seal_of_command',
             'search',
             'secondwind',
             'sell',
             'set',
             'sets',
             'settings',
             'shadow_blade',
             'shadow_blink',
             'shadow_dance',
             'shadowstep',
             'shield_bash',
             'shield_wall',
             'shout',
             'show',
             'shrug',
             'shutdown',
             'sigh',
             'silence_strike',
             'sit',
             'skill',
             'skills',
             'slap',
             'slay',
             'slicedice',
             'slip_away',
             'smile',
             'snicker',
             'snoop',
             'snuff',
             'social',
             'socials',
             'songs',
             'soulstone',
             'south',
             'spells',
             'split',
             'stable',
             'stampede',
             'stance',
             'stand',
             'stat',
             'stop',
             'storage',
             'store',
             'story',
             'sunder_armor',
             'tactical',
             'take',
             'talents',
             'talk',
             'target',
             'taste',
             'tell',
             'thank',
             'tick',
             'tickle',
             'time',
             'time_old',
             'title',
             'toggle',
             'transfer',
             'travel',
             'turnundead',
             'typo',
             'unalias',
             'uncover',
             'ungroup',
             'unlabel',
             'unlock',
             'up',
             'updates',
             'value',
             'vanish',
             'vendetta',
             'visible',
             'vital',
             'volley',
             'wake',
             'warcry',
             'wave',
             'waypoints',
             'wear',
             'weather',
             'west',
             'where',
             'who',
             'wield',
             'wimpy',
             'wink',
             'withdraw',
             'wizhelp',
             'wizinvis',
             'worth',
             'wyvern_sting',
             'xp',
             'yawn',
             'zreset'],
 'skill': ['ambush',
           'assassinate',
           'backstab',
           'bash',
           'battleshout',
           'blur',
           'camouflage',
           'circle',
           'cleave',
           'countersong',
           'detect_traps',
           'disarm',
           'dodge',
           'dual_wield',
           'envenom',
           'evasion',
           'execute_contract',
           'expose',
           'fascinate',
           'feint',
           'garrote',
           'hide',
           'holy_smite',
           'intimidate',
           'kick',
           'lore',
           'mark',
           'mark_target',
           'mockery',
           'parry',
           'pick_lock',
           'rescue',
           'scan',
           'scribe',
           'second_attack',
           'shadow_step',
           'shield_block',
           'smite',
           'sneak',
           'steal',
           'tame',
           'third_attack',
           'track',
           'trip',
           'tumble',
           'turn_undead',
           'vanish',
           'vital'],
 'spell': ['aegis',
           'animate_dead',
           'armor',
           'barkskin',
           'bless',
           'blindness',
           'blink',
           'burning_hands',
           'call_lightning',
           'chain_lightning',
           'charm_person',
           'chill_touch',
           'color_spray',
           'create_food',
           'create_water',
           'cure_critical',
           'cure_light',
           'cure_serious',
           'death_grip',
           'detect_evil',
           'detect_magic',
           'dispel_evil',
           'displacement',
           'divine_protection',
           'divine_shield',
           'earthquake',
           'enchant_weapon',
           'energy_drain',
           'enervation',
           'entangle',
           'faerie_fire',
           'fear',
           'finger_of_death',
           'fire_shield',
           'fireball',
           'flamestrike',
           'fly',
           'group_heal',
           'harm',
           'haste',
           'heal',
           'heroism',
           'holy_aura',
           'ice_armor',
           'identify',
           'invisibility',
           'lightning_bolt',
           'magic_missile',
           'mana_shield',
           'mass_charm',
           'meteor_swarm',
           'mirror_image',
           'poison',
           'protection_from_evil',
           'protection_from_good',
           'remove_curse',
           'remove_poison',
           'resurrect',
           'righteous_fury',
           'sanctuary',
           'shield',
           'shield_of_faith',
           'sleep',
           'slow',
           'spell_reflection',
           'stoneskin',
           'summon',
           'teleport',
           'vampiric_touch',
           'weaken',
           'word_of_recall']}

# Merge prestige help entries
try:
    from prestige import PRESTIGE_HELP_ENTRIES
    HELP_TOPICS.update(PRESTIGE_HELP_ENTRIES)
except Exception:
    pass

# Merge auto-generated ability help (spells, skills, talents). This is the
# authoritative, in-sync source for every ability and overwrites any older
# hand-maintained spell/skill entries that have since been renamed/reworked.
try:
    from help_abilities import build_ability_help
    HELP_TOPICS.update(build_ability_help())
except Exception:
    pass

def get_help_text(topic: str) -> str:
    """Get formatted help text for a topic."""
    topic = topic.lower().replace(" ", "_")

    if topic in HELP_TOPICS:
        help_data = HELP_TOPICS[topic]
        output = []
        output.append("=" * 70)
        output.append(help_data["title"].center(70))
        output.append("=" * 70)

        if "syntax" in help_data:
            output.append("\nSYNTAX: " + help_data["syntax"])

        if help_data.get("category") == "skill":
            output.append("AVAILABLE TO: " + ", ".join(help_data.get("classes", [])))
        elif help_data.get("category") == "spell":
            output.append("AVAILABLE TO: " + ", ".join(help_data.get("classes", [])))
            output.append("LEVEL: " + str(help_data.get("level", 1)) + " | MANA: " + str(help_data.get("mana", 0)))

        output.append(help_data["description"])
        output.append("=" * 70)
        return "\n".join(output)

    return None

def get_help_index() -> str:
    """Get a categorized index of all help topics."""
    output = []
    output.append("=" * 70)
    output.append("HELP SYSTEM".center(70))
    output.append("=" * 70)
    output.append("\nType 'help <topic>' for detailed information.\n")

    for cat in sorted(HELP_CATEGORIES.keys()):
        output.append(cat.upper() + ":")
        for topic in HELP_CATEGORIES[cat]:
            output.append("  " + topic)
        output.append("")

    return "\n".join(output)