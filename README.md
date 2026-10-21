# Misthollow - A Fantasy Multi-User Dungeon

```
    ╔═══════════════════════════════════════════════════════════════╗
    ║                                                               ║
    ║   ██████╗ ███████╗ █████╗ ██╗     ███╗   ███╗███████╗         ║
    ║   ██╔══██╗██╔════╝██╔══██╗██║     ████╗ ████║██╔════╝         ║
    ║   ██████╔╝█████╗  ███████║██║     ██╔████╔██║███████╗         ║
    ║   ██╔══██╗██╔══╝  ██╔══██║██║     ██║╚██╔╝██║╚════██║         ║
    ║   ██║  ██║███████╗██║  ██║███████╗██║ ╚═╝ ██║███████║         ║
    ║   ╚═╝  ╚═╝╚══════╝╚═╝  ╚═╝╚══════╝╚═╝     ╚═╝╚══════╝         ║
    ║                       MUD                                     ║
    ║                                                               ║
    ╚═══════════════════════════════════════════════════════════════╝
```

> **Start here:** [`docs/PROJECT_OVERVIEW.md`](docs/PROJECT_OVERVIEW.md): what the game is today (the 3D client at `/play`, the server's systems, the owner's data files, testing and deploy), and how it got here. The push-by-push log of the 3D rebuild is [`docs/REBUILD_PLAN.md`](docs/REBUILD_PLAN.md).

A complete fantasy MUD (Multi-User Dungeon) inspired by CircleMUD, written in Python 3. 
Features a rich fantasy world with multiple zones, character classes, magic system, 
combat, NPCs, and more!

## Features

### Character System
- **7 Playable Races**: Human, Elf, Dwarf, Halfling, Half-Orc, Gnome, Dark Elf
- **8 Character Classes**: Warrior, Mage, Cleric, Thief, Ranger, Paladin, Necromancer, Bard
- **Stat System**: Strength, Intelligence, Wisdom, Dexterity, Constitution, Charisma
- **Leveling System**: Gain experience, level up, learn new skills and spells

### Combat System
- Real-time combat with automatic attack rounds
- Skills: Kick, Bash, Backstab, Second Attack, Third Attack
- Flee mechanics with experience penalty
- Consider command to gauge enemy strength

### Magic System
- **30+ Spells** including:
  - Offensive: Magic Missile, Fireball, Lightning Bolt, Flamestrike
  - Healing: Cure Light, Cure Serious, Heal, Group Heal
  - Buffs: Armor, Bless, Sanctuary, Haste, Invisibility, Fly
  - Debuffs: Sleep, Blindness, Poison, Weaken, Fear
  - Utility: Teleport, Word of Recall, Detect Magic, Identify

### World
- **7 Unique Zones**:
  - The City of Midgaard (starting city with shops, inn, temple)
  - Haon Dor Forest (wildlife, druids, and dangerous creatures)
  - Greystone Castle (royal court and armory)
  - The Goblin Warrens (goblin tribe dungeon)
  - The Forgotten Crypt (undead and necromancer boss)
  - The Dragon's Domain (end-game content with ancient dragon)
  - Limbo (admin zone)
- Automatic zone resets for mob respawning
- Day/night cycle with nighttime darkness

### Items & Equipment
- 19 equipment slots (weapon, armor, jewelry, etc.)
- Weapon types with different damage
- Magical items with stat bonuses
- Containers, food, drinks, potions, scrolls

### Quest System
- Quest givers with kill, collect, talk, and visit objectives
- Quest log with accept/abandon tracking and rewards

### Crafting & Gathering
- Gathering skills: mining, herbalism, skinning
- Crafting skills: blacksmithing, alchemy, leatherworking
- Recipes that combine materials into useful items

### Communication
- Say, Shout, Gossip, Tell (private message)
- Emotes for roleplay

## Quick Start

### Requirements
- Python 3.8+
- `aiohttp` (the web map, the /play bridge, the admin dashboard): `python3 -m pip install -r requirements.txt`

Install it into the same Python that runs the server. On Windows, `py main.py` follows the
script's `#!/usr/bin/env python3` line and can start a different Python than the one you
installed into; run that Python by name instead (`python main.py`, or its full path), from `src/`.
Tools only: `tools/audio/build.py` also needs `imageio-ffmpeg`.

### Running the Server

```bash
# Make the launch script executable
chmod +x run.sh

# Start the server
./run.sh

# Or run directly with Python
cd src && python3 main.py
```

The server will start on port **4000** by default.

### Connecting

Use any telnet client or MUD client:

```bash
telnet localhost 4000
```

Or use a dedicated MUD client like:
- Mudlet
- TinTin++
- MUSHclient
- zMUD

## Commands Reference

### Movement
| Command | Description |
|---------|-------------|
| `north`, `n` | Move north |
| `south`, `s` | Move south |
| `east`, `e` | Move east |
| `west`, `w` | Move west |
| `up`, `u` | Move up |
| `down`, `d` | Move down |

### Information
| Command | Description |
|---------|-------------|
| `look`, `l` | Look at room or target |
| `score`, `sc` | View character stats |
| `inventory`, `i` | List carried items |
| `equipment`, `eq` | Show worn equipment |
| `who` | List online players |
| `where` | Find players/mobs in zone |
| `consider` | Gauge enemy difficulty |
| `time` | View the current in-game time |

### Combat
| Command | Description |
|---------|-------------|
| `kill <target>` | Attack a target |
| `flee` | Attempt to escape combat |
| `kick` | Use kick skill |
| `bash` | Use bash skill |
| `backstab <target>` | Sneak attack |
| `cast <spell> [target]` | Cast a spell |

### Pets & Summons
| Command | Description |
|---------|-------------|
| `pet` | Show your current pets and companions |
| `dismiss` | Dismiss temporary summoned pets |
| `raise <type>` | Necromancer: raise an undead servant (warrior/healer/caster/rogue) |

### Items
| Command | Description |
|---------|-------------|
| `get <item>` | Pick up an item |
| `drop <item>` | Drop an item |
| `wear <item>` | Wear armor/jewelry |
| `wield <item>` | Wield a weapon |
| `remove <item>` | Remove equipment |
| `give <item> <player>` | Give item to someone |

### Communication
| Command | Description |
|---------|-------------|
| `say <message>` | Speak to room |
| `shout <message>` | Shout to zone |
| `gossip <message>` | Global chat |
| `tell <player> <msg>` | Private message |
| `emote <action>` | Roleplay action |

### Position
| Command | Description |
|---------|-------------|
| `sit` | Sit down |
| `rest` | Rest (faster regen) |
| `sleep` | Sleep (fastest regen) |
| `wake` | Wake up |
| `stand` | Stand up |

### Quests & Crafting
| Command | Description |
|---------|-------------|
| `quest list` | List available quests from nearby NPCs |
| `quest accept <id>` | Accept a quest |
| `quest log` | View active quests |
| `quest abandon <id>` | Abandon a quest |
| `craft list` | List known recipes |
| `craft <recipe>` | Craft an item |
| `gather` | Gather nearby materials |
| `talk <npc>` | Talk to an NPC (quest givers) |

### Other
| Command | Description |
|---------|-------------|
| `skills` | View known skills |
| `spells` | View known spells |
| `practice` | Practice skills/spells |
| `eat <food>` | Eat food |
| `drink <container>` | Drink liquid |
| `quaff <potion>` | Drink a potion |
| `save` | Save character |
| `quit` | Exit game |
| `help` | View help |

## Directory Structure

```
fantasymud/
├── run.sh              # Launch script
├── README.md           # This file
├── src/
│   ├── main.py         # Entry point
│   ├── config.py       # Configuration
│   ├── server.py       # Network server
│   ├── player.py       # Player class
│   ├── world.py        # World management
│   ├── world_builder.py # World generation
│   ├── commands.py     # Command handler
│   ├── combat.py       # Combat system
│   ├── mobs.py         # NPC/Monster class
│   ├── objects.py      # Item class
│   └── spells.py       # Magic system
├── world/
│   └── zones/          # Zone data files
├── lib/
│   └── players/        # Player save files
└── log/
    └── mud.log         # Server log
```

## Configuration

Edit `src/config.py` to customize:

- `PORT`: Server port (default: 4000)
- `MAX_PLAYERS`: Maximum concurrent players
- `STARTING_ROOM`: Where new players spawn
- Race/Class definitions
- Spell costs and effects
- Combat parameters

### Admin dashboard (port 4002)

The dashboard (server status, player list, recent logs, broadcast) listens on `127.0.0.1`
only, and every `/api/*` call needs the admin token in an `Authorization: Bearer <token>`
header. The page at `http://localhost:4002` asks for the token once.

Setting the token, either way:

- **Environment variable** (wins when set): start the server with `MISTHOLLOW_ADMIN_TOKEN`
  set to a long random string, e.g. `python3 -c "import secrets; print(secrets.token_urlsafe(32))"`.
  Under launchd, put it in the job's `EnvironmentVariables`. Do not commit it.
- **Key file**: with no variable set, the server makes a random key on first start and keeps
  it in `lib/admin_key` (not in git, readable by the owner only). Read it with
  `cat lib/admin_key`; delete the file and restart to get a new one.

```bash
curl -H "Authorization: Bearer $(cat lib/admin_key)" http://127.0.0.1:4002/api/players
```

To reach it from another machine, prefer an SSH tunnel (`ssh -L 4002:127.0.0.1:4002 <server>`)
and leave the bind alone. Opting in to a wider bind is `MISTHOLLOW_ADMIN_HOST=0.0.0.0` (the
default lives in `src/config.py`, `ADMIN_DASHBOARD_HOST`), plus `MISTHOLLOW_ADMIN_HOSTS` for
the host names it should answer to. Do not route port 4002 through the public proxy.

Test: `python3 tests/test_admin_dashboard.py` (offline, needs only `aiohttp`).

## Extending the MUD

### Adding New Zones
1. Create a new method in `world_builder.py`
2. Define rooms, mobs, and objects
3. Call the method from `build_default_world()`

### Adding New Spells
1. Add spell definition to `SPELLS` dict in `spells.py`
2. Add spell to appropriate class in `config.py`

### Adding New Commands
1. Create `cmd_yourcommand` method in `commands.py`
2. Optionally add to `ALIASES` dict

## Credits

Inspired by CircleMUD and the classic DikuMUD codebase. Built with Python 3 
using only the standard library for maximum compatibility.

## License

This project is open source and available for personal and educational use.

---

*Welcome to the Realms, adventurer. Your legend awaits!*
