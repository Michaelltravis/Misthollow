"""
Misthollow World Events System
==============================
Dynamic world events that trigger periodically to keep the world feeling alive.
Event types: Invasion, World Boss, Treasure Hunt, Double XP, Weather Events.
"""

import msgkind
import random
import time
import logging
from typing import Dict, List, Optional, TYPE_CHECKING

if TYPE_CHECKING:
    from world import World
    from player import Player

from config import Config

logger = logging.getLogger('Misthollow.WorldEvents')

# ─── Event Announcements ─────────────────────────────────────────────────────

INVASION_ANNOUNCEMENTS = [
    "§R§B═══════════════════════════════════════════════════════════§N\n"
    "§R  ⚔️  INVASION! The forces of darkness march upon {zone}!  ⚔️§N\n"
    "§Y  Defend the realm! Slay the invaders for glory and treasure!§N\n"
    "§R§B═══════════════════════════════════════════════════════════§N",

    "§R§B═══════════════════════════════════════════════════════════§N\n"
    "§R  💀 The undead are rising in {zone}! 💀§N\n"
    "§Y  Heroes are needed to push back the tide of darkness!§N\n"
    "§R§B═══════════════════════════════════════════════════════════§N",

    "§R§B═══════════════════════════════════════════════════════════§N\n"
    "§R  🔥 {zone} is under siege! Monsters pour from the shadows! 🔥§N\n"
    "§Y  Rally to the defense! Great rewards await the brave!§N\n"
    "§R§B═══════════════════════════════════════════════════════════§N",
]

WORLD_BOSS_ANNOUNCEMENTS = [
    "§M§B═══════════════════════════════════════════════════════════§N\n"
    "§M  👑 A WORLD BOSS HAS APPEARED! 👑§N\n"
    "§R  {boss_name} has manifested in {room_name}!§N\n"
    "§Y  Gather your allies — this foe cannot be defeated alone!§N\n"
    "§M§B═══════════════════════════════════════════════════════════§N",
]

TREASURE_HUNT_CLUES = {
    "start": [
        "§Y§B═══════════════════════════════════════════════════════════§N\n"
        "§Y  🗺️  TREASURE HUNT! A legendary artifact has appeared! 🗺️§N\n"
        "§W  Clue: {clue}§N\n"
        "§Y  First to find it claims the prize!§N\n"
        "§Y§B═══════════════════════════════════════════════════════════§N",
    ],
    "hint": [
        "§Y  🗺️  Treasure Hunt Update: {clue}§N",
    ],
}

DOUBLE_XP_ANNOUNCEMENT = (
    "§G§B═══════════════════════════════════════════════════════════§N\n"
    "§G  ✨ THE GODS SMILE UPON THE REALM! ✨§N\n"
    "§W  All experience gains are DOUBLED for the next 30 minutes!§N\n"
    "§G  Go forth and slay, adventurers!§N\n"
    "§G§B═══════════════════════════════════════════════════════════§N"
)

WEATHER_EVENT_ANNOUNCEMENTS = {
    "storm": (
        "§B§B═══════════════════════════════════════════════════════════§N\n"
        "§B  ⛈️  A TERRIBLE STORM ROLLS ACROSS THE LAND! ⛈️§N\n"
        "§W  Lightning strikes outdoors! Seek shelter or fight on!§N\n"
        "§B§B═══════════════════════════════════════════════════════════§N"
    ),
    "fog": (
        "§C§B═══════════════════════════════════════════════════════════§N\n"
        "§C  🌫️  AN UNNATURAL FOG BLANKETS THE WORLD! 🌫️§N\n"
        "§W  Visibility is severely reduced. Accuracy suffers outdoors!§N\n"
        "§C§B═══════════════════════════════════════════════════════════§N"
    ),
    "blizzard": (
        "§W§B═══════════════════════════════════════════════════════════§N\n"
        "§W  ❄️  A HOWLING BLIZZARD DESCENDS! ❄️§N\n"
        "§C  Movement costs doubled outdoors. Frostbite damages the unwary!§N\n"
        "§W§B═══════════════════════════════════════════════════════════§N"
    ),
}

# ─── Color code translation ──────────────────────────────────────────────────

def _colorize(text: str, config: Config = None) -> str:
    """Replace §X color codes with ANSI colors."""
    if not config:
        config = Config()
    c = config.COLORS
    replacements = {
        '§R': c.get('bright_red', c.get('red', '')),
        '§G': c.get('bright_green', c.get('green', '')),
        '§Y': c.get('bright_yellow', c.get('yellow', '')),
        '§B': c.get('bright_white', c.get('white', '')),
        '§M': c.get('bright_magenta', c.get('magenta', '')),
        '§C': c.get('bright_cyan', c.get('cyan', '')),
        '§W': c.get('white', ''),
        '§N': c.get('reset', ''),
    }
    for code, ansi in replacements.items():
        text = text.replace(code, ansi)
    return text


# ─── Invasion Mob Templates ─────────────────────────────────────────────────

INVASION_MOB_TEMPLATES = [
    {
        "name": "a shadowy invader",
        "short_desc": "a shadowy invader",
        "long_desc": "A shadowy invader lurches forward, eyes burning with malice.",
        "damage_dice": "3d8+5",
        "flags": ["aggressive", "hunter"],
    },
    {
        "name": "a skeletal warrior",
        "short_desc": "a skeletal warrior",
        "long_desc": "A skeletal warrior clatters forward, sword raised.",
        "damage_dice": "4d6+8",
        "flags": ["aggressive"],
    },
    {
        "name": "a demon scout",
        "short_desc": "a demon scout",
        "long_desc": "A fiery demon scout snarls with infernal rage.",
        "damage_dice": "3d10+6",
        "flags": ["aggressive", "hunter"],
    },
    {
        "name": "a plague bearer",
        "short_desc": "a plague bearer",
        "long_desc": "A diseased figure shambles forward, oozing corruption.",
        "damage_dice": "2d8+10",
        "flags": ["aggressive", "poison"],
    },
]

# ─── World Boss Templates ────────────────────────────────────────────────────

WORLD_BOSS_TEMPLATES = [
    {
        "name": "Vortharion the Undying",
        "short_desc": "Vortharion the Undying",
        "long_desc": "A colossal lich radiating waves of necrotic power towers over everything.",
        "level": 60,
        "max_hp": 150000,
        "damage_dice": "10d12+50",
        "armor_class": -80,
        "hitroll": 40,
        "damroll": 35,
        "flags": ["aggressive", "boss", "hunter", "sentinel"],
        "special": "necromancer",
        "phase_thresholds": [75, 50, 25],
    },
    {
        "name": "Ignathar, the Infernal Wyrm",
        "short_desc": "Ignathar, the Infernal Wyrm",
        "long_desc": "An enormous dragon wreathed in hellfire fills the sky with shadow.",
        "level": 65,
        "max_hp": 200000,
        "damage_dice": "12d10+60",
        "armor_class": -100,
        "hitroll": 45,
        "damroll": 40,
        "flags": ["aggressive", "boss", "hunter", "sentinel"],
        "special": "firebreath",
        "phase_thresholds": [75, 50, 25],
    },
    {
        "name": "The Abyssal Behemoth",
        "short_desc": "The Abyssal Behemoth",
        "long_desc": "A mountain of tentacles and teeth, pulled from the deepest abyss.",
        "level": 55,
        "max_hp": 120000,
        "damage_dice": "8d12+40",
        "armor_class": -60,
        "hitroll": 35,
        "damroll": 30,
        "flags": ["aggressive", "boss", "hunter", "sentinel"],
        "special": "paralyze",
        "phase_thresholds": [80, 50, 20],
    },
]

# ─── Treasure Hunt Items ─────────────────────────────────────────────────────

TREASURE_HUNT_ITEMS = [
    {
        "name": "the Crown of Forgotten Kings",
        "short_desc": "a shimmering golden crown pulsing with ancient power",
        "long_desc": "A crown of impossibly pure gold lies here, whispering of forgotten kingdoms.",
        "item_type": "armor",
        "wear_slot": "head",
        "stats": {"str": 3, "int": 3, "wis": 3, "dex": 3, "con": 3, "cha": 5},
        "armor_bonus": -25,
        "clues": [
            "It rests where rulers once held court...",
            "Seek it in a place of stone and authority.",
            "The crown awaits near a throne.",
        ],
    },
    {
        "name": "the Blade of Eternal Twilight",
        "short_desc": "a blade that shimmers between light and shadow",
        "long_desc": "A legendary sword pulses with twilight energy, half light, half darkness.",
        "item_type": "weapon",
        "weapon_type": "slash",
        "damage_dice": "6d8+15",
        "stats": {"str": 4, "dex": 4, "hitroll": 10, "damroll": 8},
        "clues": [
            "It waits where day meets night...",
            "A place between worlds holds the blade.",
            "Look where shadows and light intertwine.",
        ],
    },
    {
        "name": "the Amulet of the World Serpent",
        "short_desc": "a jade amulet shaped like an ouroboros",
        "long_desc": "A jade amulet of incredible craftsmanship glows with primal energy.",
        "item_type": "armor",
        "wear_slot": "neck",
        "stats": {"con": 5, "wis": 4, "max_hp": 200, "max_mana": 100},
        "armor_bonus": -15,
        "clues": [
            "It coils in the depths, waiting to be found...",
            "Serpents guard its resting place.",
            "The amulet hides where water flows deep.",
        ],
    },
]


# ─── Event Classes ────────────────────────────────────────────────────────────

class WorldEvent:
    """Base class for all world events."""

    event_type = "unknown"

    def __init__(self, world: 'World', duration_minutes: int = 30):
        self.world = world
        self.start_time = time.time()
        self.duration = duration_minutes * 60  # seconds
        self.active = True
        self.spawned_mobs = []
        self.spawned_items = []

    @property
    def time_remaining(self) -> int:
        """Seconds remaining."""
        return max(0, int((self.start_time + self.duration) - time.time()))

    @property
    def time_remaining_str(self) -> str:
        remaining = self.time_remaining
        mins = remaining // 60
        secs = remaining % 60
        return f"{mins}m {secs}s"

    @property
    def is_expired(self) -> bool:
        return time.time() > self.start_time + self.duration

    async def start(self):
        """Start the event — override in subclasses."""
        pass

    async def tick(self):
        """Called every event tick (~30s). Override in subclasses."""
        pass

    async def end(self):
        """End and clean up the event."""
        self.active = False
        # Clean up spawned mobs
        for mob in self.spawned_mobs:
            if mob.room and mob in mob.room.characters:
                mob.room.characters.remove(mob)
            if mob in self.world.npcs:
                self.world.npcs.remove(mob)
        self.spawned_mobs.clear()
        # Clean up spawned items
        for item, room in self.spawned_items:
            if room and item in room.items:
                room.items.remove(item)
        self.spawned_items.clear()

    def summary(self) -> str:
        """One-line summary for 'events' command."""
        return f"{self.event_type}: {self.time_remaining_str} remaining"


class InvasionEvent(WorldEvent):
    """Waves of mobs spawn in a zone. Players defend for bonus XP/gold."""

    event_type = "invasion"

    def __init__(self, world: 'World', duration_minutes: int = 20):
        super().__init__(world, duration_minutes)
        self.zone = None
        self.zone_name = "Unknown"
        self.wave = 0
        self.max_waves = 5
        self.mobs_per_wave = 6
        self.kills = 0
        self.last_wave_time = 0
        self.wave_interval = 120  # seconds between waves
        self.bonus_xp_mult = 1.5
        self.bonus_gold_mult = 2.0

    async def start(self):
        # Pick a random zone with rooms
        # (not a land sealed until built, nor the God Rooms: nobody could answer the call)
        zones_with_rooms = [z for z in self.world.zones.values()
                            if z.rooms and z.number not in (0,) and not getattr(z, 'sealed', False)
                            and not all('imm_only' in r.flags for r in z.rooms.values())]
        if not zones_with_rooms:
            self.active = False
            return

        self.zone = random.choice(zones_with_rooms)
        self.zone_name = self.zone.name

        announcement = random.choice(INVASION_ANNOUNCEMENTS).format(zone=self.zone_name)
        await self.world.broadcast(_colorize(announcement), kind=msgkind.UI)
        logger.info(f"Invasion event started in {self.zone_name}")

        # Spawn first wave immediately
        await self._spawn_wave()

    async def tick(self):
        if not self.active:
            return
        # Spawn next wave if enough time passed
        if self.wave < self.max_waves and time.time() - self.last_wave_time >= self.wave_interval:
            await self._spawn_wave()

    async def _spawn_wave(self):
        self.wave += 1
        self.last_wave_time = time.time()

        # Get rooms in this zone
        zone_rooms = list(self.zone.rooms.values())
        if not zone_rooms:
            return

        c = Config().COLORS
        await self.world.broadcast(
            _colorize(f"§R  ⚔️  Wave {self.wave}/{self.max_waves} of invaders in {self.zone_name}! ⚔️§N"), kind=msgkind.UI
        )

        from mobs import Mobile
        template = random.choice(INVASION_MOB_TEMPLATES)

        for i in range(min(self.mobs_per_wave, len(zone_rooms))):
            room = random.choice(zone_rooms)
            # Scale mob to average player level + a few
            avg_level = max(5, self._avg_player_level() + 3 + self.wave)

            mob = Mobile(90000 + random.randint(0, 9999), self.world)
            mob.name = template["name"]
            mob.short_desc = template["short_desc"]
            mob.long_desc = template["long_desc"]
            mob.keywords = mob.name.lower().split()
            mob.level = avg_level
            mob.max_hp = int(avg_level * 80 * (1 + self.wave * 0.2))
            mob.hp = mob.max_hp
            mob.damage_dice = template["damage_dice"]
            mob.armor_class = 100 - avg_level * 3
            mob.hitroll = avg_level
            mob.damroll = avg_level // 2
            mob.flags = set(template["flags"])
            mob.flags.add("event_mob")
            mob.special = template.get("special")
            mob.exp = int(avg_level * 150 * self.bonus_xp_mult)
            mob.gold = int(avg_level * 10 * self.bonus_gold_mult)
            mob.home_zone = self.zone.number
            mob.room = room
            room.characters.append(mob)
            self.world.npcs.append(mob)
            self.spawned_mobs.append(mob)

            await room.send_to_room(
                f"{c['bright_red']}{mob.name} materializes from the shadows!{c['reset']}"
            )

    def _avg_player_level(self) -> int:
        if not self.world.players:
            return 10
        levels = [p.level for p in self.world.players.values()]
        return sum(levels) // len(levels)

    async def end(self):
        alive = sum(1 for m in self.spawned_mobs if m.hp > 0 and m.room)
        await self.world.broadcast(
            _colorize(
                f"§G§B═══════════════════════════════════════════════════════════§N\n"
                f"§G  ✨ The invasion of {self.zone_name} has ended! ✨§N\n"
                f"§W  {alive} invaders retreated. The realm is safe... for now.§N\n"
                f"§G§B═══════════════════════════════════════════════════════════§N"
            ), kind=msgkind.UI
        )
        await super().end()

    def summary(self) -> str:
        alive = sum(1 for m in self.spawned_mobs if m.hp > 0 and m.room)
        return f"⚔️ Invasion of {self.zone_name} — Wave {self.wave}/{self.max_waves}, {alive} mobs alive — {self.time_remaining_str} left"


class WorldBossEvent(WorldEvent):
    """A powerful boss spawns. Requires multiple players."""

    event_type = "world_boss"

    def __init__(self, world: 'World', duration_minutes: int = 45):
        super().__init__(world, duration_minutes)
        self.boss = None
        self.boss_template = None
        self.room = None
        self.phase = 0
        self.last_phase_announce = 0

    async def start(self):
        self.boss_template = random.choice(WORLD_BOSS_TEMPLATES)

        # Pick a room — prefer outdoor or large rooms
        rooms = [r for r in self.world.rooms.values()
                 if r.vnum > 0 and 'no_mob' not in r.flags and 'peaceful' not in r.flags
                 and 'imm_only' not in r.flags and not getattr(r.zone, 'sealed', False)]
        if not rooms:
            self.active = False
            return
        self.room = random.choice(rooms)

        from mobs import Mobile
        proto = dict(self.boss_template)
        proto["vnum"] = 99000 + random.randint(0, 999)
        mob = Mobile.from_prototype(proto, self.world)
        mob.flags.add("event_mob")
        mob.flags.add("boss")
        mob.room = self.room
        self.room.characters.append(mob)
        self.world.npcs.append(mob)
        self.spawned_mobs.append(mob)
        self.boss = mob

        room_name = self.room.name if self.room else "somewhere"
        zone_name = self.room.zone.name if hasattr(self.room, 'zone') and self.room.zone else ""
        loc = f"{room_name} ({zone_name})" if zone_name else room_name

        announcement = random.choice(WORLD_BOSS_ANNOUNCEMENTS).format(
            boss_name=mob.name, room_name=loc
        )
        await self.world.broadcast(_colorize(announcement))
        logger.info(f"World Boss '{mob.name}' spawned at room {self.room.vnum}")

    async def tick(self):
        if not self.active or not self.boss:
            return
        # Check if boss is dead
        if self.boss.hp <= 0:
            await self.world.broadcast(
                _colorize(
                    f"§M§B═══════════════════════════════════════════════════════════§N\n"
                    f"§M  👑 {self.boss.name} HAS BEEN DEFEATED! 👑§N\n"
                    f"§Y  The heroes of the realm have triumphed!§N\n"
                    f"§M§B═══════════════════════════════════════════════════════════§N"
                )
            )
            self.active = False
            return

        # Phase announcements at HP thresholds
        thresholds = self.boss_template.get("phase_thresholds", [75, 50, 25])
        hp_pct = (self.boss.hp / self.boss.max_hp) * 100
        for i, threshold in enumerate(thresholds):
            if hp_pct <= threshold and self.phase <= i:
                self.phase = i + 1
                phase_msgs = [
                    f"§R{self.boss.name} roars in fury! The ground shakes!§N",
                    f"§R{self.boss.name} enters a frenzy! Damage intensifies!§N",
                    f"§R{self.boss.name} is nearly defeated but grows desperate! BEWARE!§N",
                ]
                msg = phase_msgs[min(i, len(phase_msgs) - 1)]
                await self.world.broadcast(_colorize(msg))
                # Enrage at low HP
                if i >= len(thresholds) - 1:
                    self.boss.ai_state['enraged'] = True
                    self.boss.enrage_multiplier = 2.0

        # Periodic boss special attacks on the room
        if time.time() - getattr(self, '_last_special', 0) > 30 and self.boss.room:
            self._last_special = time.time()
            await self._boss_special_attack()

    async def _boss_special_attack(self):
        """Boss does AoE damage to the room periodically."""
        if not self.boss or not self.boss.room:
            return
        c = Config().COLORS
        room = self.boss.room
        aoe_damage = random.randint(50, 150) + self.boss.level * 2

        attack_msgs = [
            f"{self.boss.name} unleashes a devastating shockwave!",
            f"{self.boss.name} breathes destruction across the room!",
            f"{self.boss.name} slams the ground, sending cracks through the earth!",
        ]
        await room.send_to_room(f"{c['bright_red']}{random.choice(attack_msgs)} [{aoe_damage} AoE]{c['reset']}")

        for char in list(room.characters):
            if char == self.boss:
                continue
            if hasattr(char, 'connection'):  # player
                # a lich's blast is death magic, a dragon's fire; anything else a blow
                await char.take_damage(aoe_damage, self.boss, {'necromancer': 'necrotic', 'firebreath': 'fire'}.get(
                    getattr(self.boss, 'special', None), 'physical'))

    async def end(self):
        if self.boss and self.boss.hp > 0:
            await self.world.broadcast(
                _colorize(
                    f"§M  {self.boss.name} grows bored and vanishes into the ether...§N"
                )
            )
        await super().end()

    def summary(self) -> str:
        if self.boss and self.boss.hp > 0:
            hp_pct = int((self.boss.hp / self.boss.max_hp) * 100)
            return f"👑 World Boss: {self.boss.name} — {hp_pct}% HP — {self.time_remaining_str} left"
        return f"👑 World Boss: DEFEATED!"


class TreasureHuntEvent(WorldEvent):
    """A rare item spawns somewhere. Clues given periodically."""

    event_type = "treasure_hunt"

    def __init__(self, world: 'World', duration_minutes: int = 30):
        super().__init__(world, duration_minutes)
        self.treasure_template = None
        self.treasure_item = None
        self.treasure_room = None
        self.clue_index = 0
        self.last_clue_time = 0
        self.clue_interval = 300  # 5 min between clues
        self.found = False

    async def start(self):
        self.treasure_template = random.choice(TREASURE_HUNT_ITEMS)

        # Pick a room
        rooms = [r for r in self.world.rooms.values() if r.vnum > 0]
        if not rooms:
            self.active = False
            return
        self.treasure_room = random.choice(rooms)

        # Create the item
        from objects import Object
        item_vnum = 98000 + random.randint(0, 999)
        item = Object(item_vnum, self.world)
        item.name = self.treasure_template["name"]
        item.short_desc = self.treasure_template["short_desc"]
        item.long_desc = self.treasure_template["long_desc"]
        item.item_type = self.treasure_template.get("item_type", "treasure")
        item.keywords = item.name.lower().split()
        item.wear_slot = self.treasure_template.get("wear_slot")
        item.weight = 1
        item.cost = 50000
        # Apply stats
        for stat, val in self.treasure_template.get("stats", {}).items():
            setattr(item, stat, val)
        if "damage_dice" in self.treasure_template:
            item.damage_dice = self.treasure_template["damage_dice"]
            item.weapon_type = self.treasure_template.get("weapon_type", "slash")
        if "armor_bonus" in self.treasure_template:
            item.armor_bonus = self.treasure_template["armor_bonus"]
        # Mark as event treasure
        item.flags = {"event_treasure", "no_junk"}
        item.event_treasure = True

        self.treasure_item = item
        self.treasure_room.items.append(item)
        self.spawned_items.append((item, self.treasure_room))

        # First clue
        clues = self.treasure_template.get("clues", ["Somewhere in the world..."])
        first_clue = clues[0] if clues else "Somewhere in the world..."
        announcement = random.choice(TREASURE_HUNT_CLUES["start"]).format(clue=first_clue)
        await self.world.broadcast(_colorize(announcement))
        self.last_clue_time = time.time()
        self.clue_index = 1
        logger.info(f"Treasure Hunt started: {item.name} in room {self.treasure_room.vnum}")

    async def tick(self):
        if not self.active or self.found:
            return

        # Check if item was picked up
        if self.treasure_item and self.treasure_room:
            if self.treasure_item not in self.treasure_room.items:
                # Someone took it!
                self.found = True
                # Find who has it
                finder = None
                for p in self.world.players.values():
                    if self.treasure_item in p.inventory:
                        finder = p
                        break
                finder_name = finder.name if finder else "an unknown adventurer"
                await self.world.broadcast(
                    _colorize(
                        f"§Y§B═══════════════════════════════════════════════════════════§N\n"
                        f"§Y  🏆 {finder_name} has found {self.treasure_template['name']}! 🏆§N\n"
                        f"§W  The treasure hunt is over. Congratulations!§N\n"
                        f"§Y§B═══════════════════════════════════════════════════════════§N"
                    )
                )
                self.active = False
                return

        # Give clues periodically
        clues = self.treasure_template.get("clues", [])
        if (self.clue_index < len(clues) and
                time.time() - self.last_clue_time >= self.clue_interval):
            clue = clues[self.clue_index]
            hint_msg = random.choice(TREASURE_HUNT_CLUES["hint"]).format(clue=clue)
            await self.world.broadcast(_colorize(hint_msg))
            self.clue_index += 1
            self.last_clue_time = time.time()

    async def end(self):
        if not self.found:
            await self.world.broadcast(
                _colorize(f"§Y  The treasure hunt has ended. {self.treasure_template['name']} fades back into legend...§N")
            )
        await super().end()

    def summary(self) -> str:
        if self.found:
            return f"🗺️ Treasure Hunt: {self.treasure_template['name']} — FOUND!"
        return f"🗺️ Treasure Hunt: {self.treasure_template['name']} — {self.time_remaining_str} left"


class DoubleXPEvent(WorldEvent):
    """Simple buff — all XP gains are doubled."""

    event_type = "double_xp"

    def __init__(self, world: 'World', duration_minutes: int = 30):
        super().__init__(world, duration_minutes)

    async def start(self):
        await self.world.broadcast(_colorize(DOUBLE_XP_ANNOUNCEMENT), kind=msgkind.UI)
        logger.info("Double XP event started")

    async def tick(self):
        # 5-minute warning
        if 295 <= self.time_remaining <= 305:
            await self.world.broadcast(
                _colorize(f"§G  ✨ Double XP ends in 5 minutes! Make it count! ✨§N"), kind=msgkind.UI
            )

    async def end(self):
        await self.world.broadcast(
            _colorize(
                f"§G§B═══════════════════════════════════════════════════════════§N\n"
                f"§G  The gods turn their gaze elsewhere. XP gains return to normal.§N\n"
                f"§G§B═══════════════════════════════════════════════════════════§N"
            ), kind=msgkind.UI
        )
        await super().end()

    def summary(self) -> str:
        return f"✨ Double XP — {self.time_remaining_str} left"


class WeatherEventWorld(WorldEvent):
    """Extreme weather that affects combat outdoors."""

    event_type = "weather"

    OUTDOOR_SECTORS = {'field', 'forest', 'hills', 'mountain', 'water_swim',
                       'water_noswim', 'flying', 'desert', 'swamp'}

    def __init__(self, world: 'World', weather_type: str = None, duration_minutes: int = 20):
        super().__init__(world, duration_minutes)
        self.weather_type = weather_type or random.choice(["storm", "fog", "blizzard"])

    async def start(self):
        announcement = WEATHER_EVENT_ANNOUNCEMENTS.get(self.weather_type, "")
        if announcement:
            await self.world.broadcast(_colorize(announcement), kind=msgkind.UI)
        logger.info(f"Weather event started: {self.weather_type}")

    async def tick(self):
        """Apply weather effects to outdoor players."""
        if not self.active:
            return

        c = Config().COLORS
        for player in list(self.world.players.values()):
            if not player.room:
                continue
            if player.room.sector_type not in self.OUTDOOR_SECTORS:
                continue

            if self.weather_type == "storm":
                # Random lightning strikes
                if random.randint(1, 100) <= 5:
                    damage = random.randint(20, 60)
                    await player.send(
                        f"{c['bright_yellow']}⚡ Lightning strikes near you! [{damage} damage]{c['reset']}"
                    )
                    await player.take_damage(damage, None, 'lightning')

            elif self.weather_type == "blizzard":
                # Frostbite tick
                if random.randint(1, 100) <= 8:
                    damage = random.randint(10, 30)
                    await player.send(
                        f"{c['bright_cyan']}❄️ The biting cold saps your strength! [{damage} damage]{c['reset']}"
                    )
                    await player.take_damage(damage, None, 'frost')

    async def end(self):
        end_msgs = {
            "storm": "§B  The storm passes. Sunlight breaks through the clouds.§N",
            "fog": "§C  The unnatural fog lifts, and visibility returns to normal.§N",
            "blizzard": "§W  The blizzard fades. Warmth slowly returns to the land.§N",
        }
        await self.world.broadcast(_colorize(end_msgs.get(self.weather_type, "§W  The weather clears.§N")), kind=msgkind.UI)
        await super().end()

    def summary(self) -> str:
        icons = {"storm": "⛈️", "fog": "🌫️", "blizzard": "❄️"}
        icon = icons.get(self.weather_type, "🌤️")
        return f"{icon} {self.weather_type.title()} — {self.time_remaining_str} left"


# ─── Event Manager ────────────────────────────────────────────────────────────

EVENT_TYPES = {
    "invasion": InvasionEvent,
    "world_boss": WorldBossEvent,
    "boss": WorldBossEvent,
    "treasure_hunt": TreasureHuntEvent,
    "treasure": TreasureHuntEvent,
    "double_xp": DoubleXPEvent,
    "doublexp": DoubleXPEvent,
    "weather": WeatherEventWorld,
    "storm": lambda w: WeatherEventWorld(w, weather_type="storm"),
    "fog": lambda w: WeatherEventWorld(w, weather_type="fog"),
    "blizzard": lambda w: WeatherEventWorld(w, weather_type="blizzard"),
}


class WorldEventManager:
    """Manages all world events."""

    def __init__(self, world: 'World'):
        self.world = world
        self.active_events: List[WorldEvent] = []
        self.event_log: List[Dict] = []  # history
        self.last_auto_event = time.time()
        self.auto_event_interval = random.randint(1800, 3600)  # 30-60 min

    async def tick(self):
        """Called every ~30 seconds from the main loop."""
        # Tick active events
        for event in list(self.active_events):
            if event.is_expired and event.active:
                await event.end()
                self._log_event(event, "expired")
                self.active_events.remove(event)
            elif event.active:
                await event.tick()
            else:
                # Event ended itself (e.g., boss killed, treasure found)
                self._log_event(event, "completed")
                self.active_events.remove(event)

        # Auto-trigger events if enough time has passed and players are online
        if (len(self.world.players) >= 1 and
                time.time() - self.last_auto_event >= self.auto_event_interval and
                len(self.active_events) < 2):
            await self.start_random_event()
            self.last_auto_event = time.time()
            self.auto_event_interval = random.randint(1800, 3600)

    async def start_random_event(self):
        """Start a random event."""
        # Weight toward simpler events; boss is rarer
        weights = [
            ("invasion", 30),
            ("double_xp", 25),
            ("weather", 25),
            ("treasure_hunt", 15),
            ("world_boss", 5),
        ]
        choices, w = zip(*weights)
        event_type = random.choices(choices, weights=w, k=1)[0]
        await self.start_event(event_type)

    async def start_event(self, event_type: str) -> Optional[WorldEvent]:
        """Start an event by type name. Returns the event or None."""
        # Don't allow duplicate types
        for e in self.active_events:
            if e.event_type == event_type or (event_type in ("boss", "world_boss") and e.event_type == "world_boss"):
                return None

        factory = EVENT_TYPES.get(event_type.lower())
        if not factory:
            return None

        event = factory(self.world) if callable(factory) else factory
        # If factory returned a class instead of an instance (lambda vs class)
        if isinstance(event, type):
            event = event(self.world)

        self.active_events.append(event)
        await event.start()
        self._log_event(event, "started")
        return event

    async def stop_event(self, event_type: str = None) -> bool:
        """Stop an event. If no type given, stop all."""
        stopped = False
        for event in list(self.active_events):
            if event_type is None or event.event_type == event_type:
                await event.end()
                self._log_event(event, "stopped_by_immortal")
                self.active_events.remove(event)
                stopped = True
        return stopped

    def _log_event(self, event: WorldEvent, status: str):
        """Log event to history."""
        self.event_log.append({
            "type": event.event_type,
            "status": status,
            "time": time.time(),
            "summary": event.summary(),
        })
        # Keep only last 100 entries
        if len(self.event_log) > 100:
            self.event_log = self.event_log[-100:]

    def get_active_summaries(self) -> List[str]:
        """Get summaries of all active events."""
        return [e.summary() for e in self.active_events]

    def get_log(self, limit: int = 20) -> List[Dict]:
        """Get recent event log entries."""
        return self.event_log[-limit:]

    def has_double_xp(self) -> bool:
        """Check if double XP is active (used by combat/XP system)."""
        return any(e.event_type == "double_xp" and e.active for e in self.active_events)

    def has_weather_event(self, weather_type: str = None) -> bool:
        """Check if a weather event is active."""
        for e in self.active_events:
            if e.event_type == "weather" and e.active:
                if weather_type is None or e.weather_type == weather_type:
                    return True
        return False

    def get_fog_accuracy_penalty(self) -> int:
        """Get accuracy penalty from fog event (0 if no fog)."""
        for e in self.active_events:
            if e.event_type == "weather" and e.active and e.weather_type == "fog":
                return 4  # -4 to hit rolls
        return 0
