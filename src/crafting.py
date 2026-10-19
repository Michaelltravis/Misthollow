"""
Crafting System
===============
Gathering skills, crafting stations, recipes, crafting levels, and recipe discovery.
"""

import logging
import random
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Any

from objects import Object

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

GATHERING_SKILLS = ['mining', 'herbalism', 'skinning', 'fishing']
CRAFTING_DISCIPLINES = ['blacksmithing', 'alchemy', 'leatherworking', 'enchanting']

DISCIPLINE_STATIONS = {
    'blacksmithing': 'forge',
    'alchemy': 'alchemy_table',
    'leatherworking': 'workbench',
    'enchanting': 'enchanting_circle',
}

STATION_NAMES = {
    'forge': 'a dwarven forge',
    'alchemy_table': 'an alchemy table',
    'workbench': 'a sturdy workbench',
    'enchanting_circle': 'a glowing enchanting circle',
}

# Rooms in Garathorm (zone 030) that contain crafting stations
STATION_ROOMS = {
    3011: 'forge',             # Weapon Shop
    3020: 'forge',             # The Armory
    3033: 'alchemy_table',     # The Magic Shop
    3010: 'workbench',         # The General Store
    3017: 'enchanting_circle', # Mages' Guild entrance
}

# Crafting XP thresholds per level (1-20)
CRAFTING_XP_TABLE = [0] + [i * 100 for i in range(1, 21)]  # 100, 200, ... 2000

# ---------------------------------------------------------------------------
# Materials
# ---------------------------------------------------------------------------

MATERIALS: Dict[str, dict] = {
    # ---- Mining ores ----
    'copper_ore':   {'vnum': 9001, 'name': 'copper ore',   'short_desc': 'a chunk of copper ore',   'room_desc': 'A chunk of copper ore lies here.',   'description': 'A rough chunk of copper ore, ready to be smelted.', 'item_type': 'material', 'weight': 2, 'cost': 5},
    'iron_ore':     {'vnum': 9002, 'name': 'iron ore',     'short_desc': 'a chunk of iron ore',     'room_desc': 'A chunk of iron ore lies here.',     'description': 'A heavy chunk of iron ore.',                       'item_type': 'material', 'weight': 3, 'cost': 8},
    'silver_ore':   {'vnum': 9003, 'name': 'silver ore',   'short_desc': 'a nugget of silver ore',  'room_desc': 'A nugget of silver ore glints here.', 'description': 'A shimmering nugget of silver ore.',               'item_type': 'material', 'weight': 2, 'cost': 12},
    'gold_ore':     {'vnum': 9008, 'name': 'gold ore',     'short_desc': 'a nugget of gold ore',    'room_desc': 'A nugget of gold ore gleams here.',   'description': 'A heavy nugget of gold ore.',                      'item_type': 'material', 'weight': 3, 'cost': 20},
    'mithril_ore':  {'vnum': 9009, 'name': 'mithril ore',  'short_desc': 'a shard of mithril ore',  'room_desc': 'A shard of mithril ore shimmers here.','description': 'A rare shard of mithril, light and incredibly strong.','item_type': 'material','weight': 1, 'cost': 50},
    'steel_ingot':  {'vnum': 9010, 'name': 'steel ingot',  'short_desc': 'a steel ingot',           'room_desc': 'A steel ingot rests here.',           'description': 'A refined steel ingot, forged from iron.',          'item_type': 'material', 'weight': 4, 'cost': 15},

    # ---- Herbs (foraging) ----
    'healing_herb':   {'vnum': 9004, 'name': 'healing herb',   'short_desc': 'a bundle of healing herbs',   'room_desc': 'A bundle of healing herbs lies here.',   'description': 'Fragrant herbs used in healing remedies.',          'item_type': 'material', 'weight': 1, 'cost': 6},
    'mana_leaf':      {'vnum': 9005, 'name': 'mana leaf',      'short_desc': 'a shimmering mana leaf',      'room_desc': 'A shimmering leaf rests on the ground.', 'description': 'A leaf that hums faintly with magical energy.',     'item_type': 'material', 'weight': 1, 'cost': 10},
    'nightshade':     {'vnum': 9011, 'name': 'nightshade',     'short_desc': 'a sprig of nightshade',       'room_desc': 'A dark sprig of nightshade lies here.',  'description': 'A poisonous plant, useful in dark alchemy.',        'item_type': 'material', 'weight': 1, 'cost': 14},
    'firebloom':      {'vnum': 9012, 'name': 'firebloom',      'short_desc': 'a fiery firebloom petal',     'room_desc': 'A glowing firebloom petal lies here.',   'description': 'A petal radiating heat, prized by alchemists.',     'item_type': 'material', 'weight': 1, 'cost': 16},
    'starflower':     {'vnum': 9013, 'name': 'starflower',     'short_desc': 'a luminous starflower',       'room_desc': 'A starflower glows softly here.',        'description': 'A rare flower that blooms under moonlight.',        'item_type': 'material', 'weight': 1, 'cost': 22},
    'bloodmoss':      {'vnum': 9014, 'name': 'bloodmoss',      'short_desc': 'a clump of bloodmoss',        'room_desc': 'A dark red clump of bloodmoss lies here.','description': 'A crimson moss with restorative properties.',       'item_type': 'material', 'weight': 1, 'cost': 12},

    # ---- Hides (skinning) ----
    'sturdy_hide':  {'vnum': 9006, 'name': 'sturdy hide',  'short_desc': 'a sturdy animal hide',  'room_desc': 'A sturdy animal hide lies here.',  'description': 'A thick hide suitable for leatherworking.',        'item_type': 'material', 'weight': 3, 'cost': 9},
    'thick_hide':   {'vnum': 9007, 'name': 'thick hide',   'short_desc': 'a thick animal hide',   'room_desc': 'A thick animal hide lies here.',   'description': 'A heavy hide from a large beast.',                 'item_type': 'material', 'weight': 4, 'cost': 12},
    'dragon_scale':  {'vnum': 9015, 'name': 'dragon scale', 'short_desc': 'a gleaming dragon scale','room_desc': 'A dragon scale gleams here.',      'description': 'An iridescent scale from a dragon.',               'item_type': 'material', 'weight': 2, 'cost': 80},
    'wolf_pelt':    {'vnum': 9016, 'name': 'wolf pelt',    'short_desc': 'a grey wolf pelt',      'room_desc': 'A grey wolf pelt lies here.',      'description': 'A soft grey pelt from a timber wolf.',             'item_type': 'material', 'weight': 2, 'cost': 7},
    'bear_hide':    {'vnum': 9017, 'name': 'bear hide',    'short_desc': 'a thick bear hide',     'room_desc': 'A bear hide lies here.',           'description': 'A massive hide from a cave bear.',                 'item_type': 'material', 'weight': 5, 'cost': 15},

    # ---- Fish (fishing) ----
    'trout':        {'vnum': 9018, 'name': 'trout',        'short_desc': 'a fresh trout',         'room_desc': 'A fresh trout lies here.',         'description': 'A silvery trout, still glistening.',               'item_type': 'food', 'weight': 1, 'cost': 4, 'food_value': 8},
    'salmon':       {'vnum': 9019, 'name': 'salmon',       'short_desc': 'a large salmon',        'room_desc': 'A large salmon lies here.',        'description': 'A hefty salmon with pink flesh.',                  'item_type': 'food', 'weight': 2, 'cost': 6, 'food_value': 12},
    'golden_carp':  {'vnum': 9020, 'name': 'golden carp',  'short_desc': 'a golden carp',         'room_desc': 'A golden carp gleams here.',       'description': 'A rare golden carp, said to have alchemical uses.','item_type': 'material', 'weight': 1, 'cost': 25},

    # ---- Enchanting reagents ----
    'arcane_dust':  {'vnum': 9021, 'name': 'arcane dust',  'short_desc': 'a pinch of arcane dust', 'room_desc': 'Arcane dust shimmers on the ground.','description': 'Glittering dust used in enchantments.',          'item_type': 'material', 'weight': 1, 'cost': 18},
    'soul_ember':   {'vnum': 9022, 'name': 'soul ember',   'short_desc': 'a flickering soul ember','room_desc': 'A soul ember flickers here.',       'description': 'A shard of crystallized soul energy.',             'item_type': 'material', 'weight': 1, 'cost': 30},
    'elemental_core':{'vnum': 9023,'name': 'elemental core','short_desc': 'an elemental core',     'room_desc': 'An elemental core pulses here.',    'description': 'A core of raw elemental energy.',                  'item_type': 'material', 'weight': 1, 'cost': 40},
}

# ---------------------------------------------------------------------------
# Recipes
# ---------------------------------------------------------------------------

@dataclass
class Recipe:
    """Defines a crafting recipe."""
    recipe_id: str
    name: str
    skill: str           # crafting discipline
    skill_required: int  # crafting level required
    ingredients: Dict[str, int]  # material_id -> count
    output: Dict[str, Any]       # object definition dict
    exp_reward: int = 50
    station: str = ''    # required station type (auto-filled from discipline)

    def __post_init__(self):
        if not self.station:
            self.station = DISCIPLINE_STATIONS.get(self.skill, '')


# All recipes keyed by recipe_id
RECIPES: Dict[str, Recipe] = {}

def _r(recipe_id, name, skill, level, ingredients, output, exp=50):
    """Helper to register a recipe."""
    RECIPES[recipe_id] = Recipe(recipe_id, name, skill, level, ingredients, output, exp)

# ==================== BLACKSMITHING (10 recipes) ====================

_r('copper_dagger', 'Copper Dagger', 'blacksmithing', 1,
   {'copper_ore': 2},
   {'vnum': 9101, 'name': 'a copper dagger', 'short_desc': 'a copper dagger', 'room_desc': 'A copper dagger lies here.',
    'description': 'A simple dagger forged from copper.', 'item_type': 'weapon', 'weapon_type': 'stab', 'damage_dice': '1d4', 'weight': 2, 'cost': 25},
   exp=40)

_r('iron_sword', 'Iron Sword', 'blacksmithing', 3,
   {'iron_ore': 3},
   {'vnum': 9102, 'name': 'an iron sword', 'short_desc': 'an iron sword', 'room_desc': 'An iron sword lies here.',
    'description': 'A sturdy iron sword with a keen edge.', 'item_type': 'weapon', 'weapon_type': 'slash', 'damage_dice': '2d4', 'weight': 5, 'cost': 80,
    'affects': [{'type': 'hitroll', 'value': 1}]},
   exp=60)

_r('iron_mace', 'Iron Mace', 'blacksmithing', 3,
   {'iron_ore': 3, 'copper_ore': 1},
   {'vnum': 9103, 'name': 'an iron mace', 'short_desc': 'an iron mace', 'room_desc': 'An iron mace lies here.',
    'description': 'A heavy iron mace with a flanged head.', 'item_type': 'weapon', 'weapon_type': 'pound', 'damage_dice': '2d5', 'weight': 8, 'cost': 90},
   exp=65)

_r('steel_shield', 'Steel Shield', 'blacksmithing', 5,
   {'iron_ore': 2, 'steel_ingot': 2},
   {'vnum': 9104, 'name': 'a steel shield', 'short_desc': 'a polished steel shield', 'room_desc': 'A steel shield lies here.',
    'description': 'A well-crafted steel shield.', 'item_type': 'armor', 'wear_slot': 'shield', 'armor': 6, 'weight': 8, 'cost': 150,
    'affects': [{'type': 'armor', 'value': -5}]},
   exp=80)

_r('steel_longsword', 'Steel Longsword', 'blacksmithing', 6,
   {'steel_ingot': 3},
   {'vnum': 9105, 'name': 'a steel longsword', 'short_desc': 'a gleaming steel longsword', 'room_desc': 'A steel longsword gleams here.',
    'description': 'A finely forged longsword of tempered steel.', 'item_type': 'weapon', 'weapon_type': 'slash', 'damage_dice': '2d6', 'weight': 6, 'cost': 200,
    'affects': [{'type': 'hitroll', 'value': 2}]},
   exp=100)

_r('steel_breastplate', 'Steel Breastplate', 'blacksmithing', 7,
   {'steel_ingot': 4, 'iron_ore': 2},
   {'vnum': 9106, 'name': 'a steel breastplate', 'short_desc': 'a steel breastplate', 'room_desc': 'A steel breastplate lies here.',
    'description': 'A solid breastplate of hammered steel.', 'item_type': 'armor', 'wear_slot': 'body', 'armor': 12, 'weight': 15, 'cost': 300,
    'affects': [{'type': 'armor', 'value': -10}]},
   exp=120)

_r('silver_ring', 'Silver Ring', 'blacksmithing', 4,
   {'silver_ore': 2},
   {'vnum': 9107, 'name': 'a silver ring', 'short_desc': 'a polished silver ring', 'room_desc': 'A silver ring glints here.',
    'description': 'A simple but elegant silver ring.', 'item_type': 'armor', 'wear_slot': 'finger', 'armor': 0, 'weight': 1, 'cost': 60,
    'affects': [{'type': 'mana', 'value': 10}]},
   exp=55)

_r('mithril_chainmail', 'Mithril Chainmail', 'blacksmithing', 10,
   {'mithril_ore': 4, 'steel_ingot': 2},
   {'vnum': 9108, 'name': 'mithril chainmail', 'short_desc': 'a suit of mithril chainmail', 'room_desc': 'A suit of mithril chainmail shimmers here.',
    'description': 'Incredibly light chainmail forged from mithril. It gleams with an inner light.',
    'item_type': 'armor', 'wear_slot': 'body', 'armor': 18, 'weight': 6, 'cost': 800,
    'affects': [{'type': 'armor', 'value': -15}, {'type': 'dex', 'value': 1}]},
   exp=200)

_r('gold_circlet', 'Gold Circlet', 'blacksmithing', 8,
   {'gold_ore': 3, 'silver_ore': 1},
   {'vnum': 9109, 'name': 'a gold circlet', 'short_desc': 'a gleaming gold circlet', 'room_desc': 'A gold circlet gleams here.',
    'description': 'An ornate circlet of gold, fit for royalty.', 'item_type': 'armor', 'wear_slot': 'head', 'armor': 4, 'weight': 2, 'cost': 350,
    'affects': [{'type': 'cha', 'value': 2}, {'type': 'mana', 'value': 15}]},
   exp=130)

_r('mithril_warhammer', 'Mithril Warhammer', 'blacksmithing', 12,
   {'mithril_ore': 5, 'steel_ingot': 3},
   {'vnum': 9110, 'name': 'a mithril warhammer', 'short_desc': 'a mithril warhammer', 'room_desc': 'A mithril warhammer radiates power here.',
    'description': 'A devastating warhammer forged from mithril, impossibly light yet crushing.',
    'item_type': 'weapon', 'weapon_type': 'pound', 'damage_dice': '3d5', 'weight': 7, 'cost': 1200,
    'affects': [{'type': 'hitroll', 'value': 3}, {'type': 'damroll', 'value': 2}]},
   exp=250)

# ==================== ALCHEMY (10 recipes) ====================

_r('healing_potion', 'Healing Potion', 'alchemy', 1,
   {'healing_herb': 2},
   {'vnum': 9201, 'name': 'a healing potion', 'short_desc': 'a vial of red liquid', 'room_desc': 'A vial of red liquid sits here.',
    'description': 'A potion that mends wounds.', 'item_type': 'potion', 'weight': 1, 'cost': 30,
    'spell_effects': [{'spell': 'cure_light', 'level': 5}]},
   exp=40)

_r('mana_potion', 'Mana Potion', 'alchemy', 2,
   {'mana_leaf': 2},
   {'vnum': 9202, 'name': 'a mana potion', 'short_desc': 'a vial of blue liquid', 'room_desc': 'A vial of blue liquid sits here.',
    'description': 'A potion that restores magical energy.', 'item_type': 'potion', 'weight': 1, 'cost': 35,
    'spell_effects': [{'spell': 'restore_mana', 'level': 5}]},
   exp=45)

_r('poison_vial', 'Poison Vial', 'alchemy', 4,
   {'nightshade': 2, 'bloodmoss': 1},
   {'vnum': 9203, 'name': 'a poison vial', 'short_desc': 'a vial of dark liquid', 'room_desc': 'A vial of dark liquid sits here.',
    'description': 'A concentrated poison. Apply to weapons for extra damage.', 'item_type': 'potion', 'weight': 1, 'cost': 50,
    'spell_effects': [{'spell': 'poison', 'level': 8}]},
   exp=60)

_r('elixir_strength', 'Elixir of Strength', 'alchemy', 6,
   {'firebloom': 2, 'bloodmoss': 1, 'healing_herb': 1},
   {'vnum': 9204, 'name': 'an elixir of strength', 'short_desc': 'a glowing amber elixir', 'room_desc': 'An amber elixir glows here.',
    'description': 'Drinking this elixir temporarily increases strength.',
    'item_type': 'potion', 'weight': 1, 'cost': 100,
    'spell_effects': [{'spell': 'strength', 'level': 12}]},
   exp=90)

_r('greater_healing', 'Greater Healing Potion', 'alchemy', 5,
   {'healing_herb': 3, 'bloodmoss': 2},
   {'vnum': 9205, 'name': 'a greater healing potion', 'short_desc': 'a large vial of crimson liquid', 'room_desc': 'A large crimson vial sits here.',
    'description': 'A powerful healing draught.', 'item_type': 'potion', 'weight': 1, 'cost': 75,
    'spell_effects': [{'spell': 'cure_serious', 'level': 10}]},
   exp=70)

_r('elixir_agility', 'Elixir of Agility', 'alchemy', 6,
   {'mana_leaf': 2, 'starflower': 1},
   {'vnum': 9206, 'name': 'an elixir of agility', 'short_desc': 'a silvery elixir', 'room_desc': 'A silvery elixir shimmers here.',
    'description': 'Temporarily increases dexterity when consumed.',
    'item_type': 'potion', 'weight': 1, 'cost': 100,
    'spell_effects': [{'spell': 'agility', 'level': 12}]},
   exp=90)

_r('antidote', 'Antidote', 'alchemy', 3,
   {'healing_herb': 1, 'mana_leaf': 1},
   {'vnum': 9207, 'name': 'an antidote', 'short_desc': 'a green vial of antidote', 'room_desc': 'A green vial sits here.',
    'description': 'Cures poison when consumed.', 'item_type': 'potion', 'weight': 1, 'cost': 40,
    'spell_effects': [{'spell': 'remove_poison', 'level': 8}]},
   exp=50)

_r('elixir_wisdom', 'Elixir of Wisdom', 'alchemy', 7,
   {'starflower': 2, 'mana_leaf': 2},
   {'vnum': 9208, 'name': 'an elixir of wisdom', 'short_desc': 'a pearl-white elixir', 'room_desc': 'A pearl-white elixir sits here.',
    'description': 'Temporarily increases wisdom when consumed.',
    'item_type': 'potion', 'weight': 1, 'cost': 120,
    'spell_effects': [{'spell': 'wisdom', 'level': 14}]},
   exp=100)

_r('firebomb', 'Firebomb', 'alchemy', 8,
   {'firebloom': 3, 'nightshade': 1},
   {'vnum': 9209, 'name': 'a firebomb', 'short_desc': 'a volatile firebomb', 'room_desc': 'A firebomb sits here, looking unstable.',
    'description': 'A throwable explosive that bursts into flame.',
    'item_type': 'potion', 'weight': 2, 'cost': 150,
    'spell_effects': [{'spell': 'fireball', 'level': 15}]},
   exp=120)

_r('golden_elixir', 'Golden Elixir', 'alchemy', 10,
   {'golden_carp': 1, 'starflower': 2, 'healing_herb': 3},
   {'vnum': 9210, 'name': 'a golden elixir', 'short_desc': 'a radiant golden elixir', 'room_desc': 'A golden elixir radiates warmth here.',
    'description': 'A legendary elixir brewed from a golden carp. Fully restores health.',
    'item_type': 'potion', 'weight': 1, 'cost': 500,
    'spell_effects': [{'spell': 'heal', 'level': 20}]},
   exp=200)

# ==================== LEATHERWORKING (8 recipes) ====================

_r('leather_vest', 'Leather Vest', 'leatherworking', 1,
   {'sturdy_hide': 2},
   {'vnum': 9301, 'name': 'a leather vest', 'short_desc': 'a leather vest', 'room_desc': 'A leather vest lies here.',
    'description': 'A reinforced leather vest.', 'item_type': 'armor', 'wear_slot': 'body', 'armor': 6, 'weight': 4, 'cost': 40},
   exp=40)

_r('leather_boots', 'Leather Boots', 'leatherworking', 2,
   {'sturdy_hide': 1, 'wolf_pelt': 1},
   {'vnum': 9302, 'name': 'leather boots', 'short_desc': 'a pair of leather boots', 'room_desc': 'A pair of leather boots lies here.',
    'description': 'Sturdy leather boots lined with wolf fur.', 'item_type': 'armor', 'wear_slot': 'feet', 'armor': 3, 'weight': 3, 'cost': 35,
    'affects': [{'type': 'dex', 'value': 1}]},
   exp=45)

_r('leather_armor', 'Leather Armor', 'leatherworking', 4,
   {'thick_hide': 3, 'sturdy_hide': 1},
   {'vnum': 9303, 'name': 'leather armor', 'short_desc': 'a suit of leather armor', 'room_desc': 'A suit of leather armor lies here.',
    'description': 'Well-crafted leather armor offering solid protection.', 'item_type': 'armor', 'wear_slot': 'body', 'armor': 9, 'weight': 8, 'cost': 100,
    'affects': [{'type': 'armor', 'value': -5}]},
   exp=70)

_r('ranger_boots', 'Ranger\'s Boots', 'leatherworking', 6,
   {'thick_hide': 2, 'wolf_pelt': 2},
   {'vnum': 9304, 'name': "ranger's boots", 'short_desc': "a pair of ranger's boots", 'room_desc': "Ranger's boots lie here.",
    'description': 'Silent boots favored by rangers and scouts.', 'item_type': 'armor', 'wear_slot': 'feet', 'armor': 4, 'weight': 2, 'cost': 150,
    'affects': [{'type': 'dex', 'value': 2}, {'type': 'sneak', 'value': 5}]},
   exp=90)

_r('quiver', 'Quiver', 'leatherworking', 3,
   {'sturdy_hide': 2, 'wolf_pelt': 1},
   {'vnum': 9305, 'name': 'a leather quiver', 'short_desc': 'a leather quiver', 'room_desc': 'A leather quiver lies here.',
    'description': 'A finely stitched leather quiver.', 'item_type': 'armor', 'wear_slot': 'about', 'armor': 1, 'weight': 2, 'cost': 50,
    'affects': [{'type': 'hitroll', 'value': 1}]},
   exp=55)

_r('hardened_leathers', 'Hardened Leather Armor', 'leatherworking', 8,
   {'bear_hide': 2, 'thick_hide': 2},
   {'vnum': 9306, 'name': 'hardened leather armor', 'short_desc': 'hardened leather armor', 'room_desc': 'Hardened leather armor lies here.',
    'description': 'Boiled and hardened leather armor, nearly as tough as chain.', 'item_type': 'armor', 'wear_slot': 'body', 'armor': 14, 'weight': 10, 'cost': 250,
    'affects': [{'type': 'armor', 'value': -10}, {'type': 'con', 'value': 1}]},
   exp=130)

_r('wolf_cloak', 'Wolf-fur Cloak', 'leatherworking', 5,
   {'wolf_pelt': 3},
   {'vnum': 9307, 'name': 'a wolf-fur cloak', 'short_desc': 'a wolf-fur cloak', 'room_desc': 'A wolf-fur cloak lies here.',
    'description': 'A thick cloak of grey wolf fur.', 'item_type': 'armor', 'wear_slot': 'about', 'armor': 3, 'weight': 4, 'cost': 80,
    'affects': [{'type': 'con', 'value': 1}]},
   exp=70)

_r('dragonscale_vest', 'Dragonscale Vest', 'leatherworking', 12,
   {'dragon_scale': 4, 'thick_hide': 2},
   {'vnum': 9308, 'name': 'a dragonscale vest', 'short_desc': 'a vest of dragon scales', 'room_desc': 'A dragonscale vest gleams here.',
    'description': 'A vest crafted from dragon scales. Nearly impervious.',
    'item_type': 'armor', 'wear_slot': 'body', 'armor': 20, 'weight': 7, 'cost': 1500,
    'affects': [{'type': 'armor', 'value': -20}, {'type': 'str', 'value': 1}, {'type': 'con', 'value': 1}]},
   exp=250)

# ==================== ENCHANTING (6 recipes) ====================
# Enchanting recipes add magical properties. They consume the equipment piece
# and produce an upgraded version.

_r('enchant_hit', 'Enchant Weapon: Precision', 'enchanting', 3,
   {'arcane_dust': 3},
   {'vnum': 0, 'enchant': True, 'target': 'weapon',
    'bonus': {'type': 'hitroll', 'value': 2},
    'suffix': 'of Precision'},
   exp=80)

_r('enchant_dam', 'Enchant Weapon: Force', 'enchanting', 5,
   {'arcane_dust': 2, 'soul_ember': 1},
   {'vnum': 0, 'enchant': True, 'target': 'weapon',
    'bonus': {'type': 'damroll', 'value': 2},
    'suffix': 'of Force'},
   exp=100)

_r('enchant_hp', 'Enchant Armor: Vitality', 'enchanting', 4,
   {'arcane_dust': 2, 'soul_ember': 1},
   {'vnum': 0, 'enchant': True, 'target': 'armor',
    'bonus': {'type': 'hp', 'value': 15},
    'suffix': 'of Vitality'},
   exp=90)

_r('enchant_mana', 'Enchant Armor: Sorcery', 'enchanting', 5,
   {'arcane_dust': 3, 'mana_leaf': 2},
   {'vnum': 0, 'enchant': True, 'target': 'armor',
    'bonus': {'type': 'mana', 'value': 20},
    'suffix': 'of Sorcery'},
   exp=100)

_r('enchant_fire', 'Enchant Weapon: Flame', 'enchanting', 8,
   {'elemental_core': 1, 'soul_ember': 2, 'firebloom': 2},
   {'vnum': 0, 'enchant': True, 'target': 'weapon',
    'bonus': {'type': 'damroll', 'value': 3},
    'suffix': 'of Flame',
    'flag': 'flaming'},
   exp=150)

_r('enchant_frost', 'Enchant Weapon: Frost', 'enchanting', 8,
   {'elemental_core': 1, 'soul_ember': 2, 'starflower': 2},
   {'vnum': 0, 'enchant': True, 'target': 'weapon',
    'bonus': {'type': 'hitroll', 'value': 3},
    'suffix': 'of Frost',
    'flag': 'frost'},
   exp=150)


# ---------------------------------------------------------------------------
# Starter recipes (everyone knows these)
# ---------------------------------------------------------------------------

STARTER_RECIPES = ['copper_dagger', 'healing_potion', 'leather_vest']

# ---------------------------------------------------------------------------
# Helper functions
# ---------------------------------------------------------------------------

def _ensure_crafting_data(player):
    """Ensure player has crafting attributes."""
    if not hasattr(player, 'known_recipes') or player.known_recipes is None:
        player.known_recipes = list(STARTER_RECIPES)
    if not hasattr(player, 'crafting_levels') or player.crafting_levels is None:
        player.crafting_levels = {}
    if not hasattr(player, 'crafting_xp') or player.crafting_xp is None:
        player.crafting_xp = {}


def get_crafting_level(player, discipline: str) -> int:
    """Return crafting level for a discipline."""
    _ensure_crafting_data(player)
    return player.crafting_levels.get(discipline, 1)


def get_crafting_xp(player, discipline: str) -> int:
    _ensure_crafting_data(player)
    return player.crafting_xp.get(discipline, 0)


def add_crafting_xp(player, discipline: str, amount: int) -> bool:
    """Add crafting XP. Returns True if leveled up."""
    _ensure_crafting_data(player)
    current = player.crafting_xp.get(discipline, 0)
    current += amount
    player.crafting_xp[discipline] = current
    level = player.crafting_levels.get(discipline, 1)
    leveled = False
    while level < 20 and current >= CRAFTING_XP_TABLE[level]:
        current -= CRAFTING_XP_TABLE[level]
        level += 1
        leveled = True
    player.crafting_xp[discipline] = current
    player.crafting_levels[discipline] = level
    return leveled


def learn_recipe(player, recipe_id: str) -> bool:
    """Teach a recipe. Returns True if new."""
    _ensure_crafting_data(player)
    if recipe_id not in RECIPES:
        return False
    if recipe_id in player.known_recipes:
        return False
    player.known_recipes.append(recipe_id)
    return True


def _create_object_from_def(obj_def: Dict[str, Any], world=None) -> Object:
    obj = Object(obj_def.get('vnum', 0), world)
    obj.name = obj_def.get('name', obj.name)
    obj.short_desc = obj_def.get('short_desc', obj.short_desc)
    obj.room_desc = obj_def.get('room_desc', obj.room_desc)
    obj.description = obj_def.get('description', obj.description)
    obj.item_type = obj_def.get('item_type', obj.item_type)
    obj.wear_slot = obj_def.get('wear_slot', obj.wear_slot)
    obj.weight = obj_def.get('weight', obj.weight)
    obj.cost = obj_def.get('cost', obj.cost)
    obj.damage_dice = obj_def.get('damage_dice', obj.damage_dice)
    obj.weapon_type = obj_def.get('weapon_type', obj.weapon_type)
    obj.armor = obj_def.get('armor', obj.armor)
    obj.food_value = obj_def.get('food_value', obj.food_value)
    obj.drinks = obj_def.get('drinks', obj.drinks)
    obj.liquid = obj_def.get('liquid', obj.liquid)
    obj.affects = list(obj_def.get('affects', []))
    obj.spell_effects = list(obj_def.get('spell_effects', []))
    obj.flags = set(obj_def.get('flags', []))
    return obj


def create_material(material_id: str, world=None) -> Optional[Object]:
    mat_def = MATERIALS.get(material_id)
    if not mat_def:
        return None
    obj = _create_object_from_def(mat_def, world)
    obj.material_id = material_id
    # Add food_value for fish
    if 'food_value' in mat_def:
        obj.food_value = mat_def['food_value']
    return obj


def _count_materials(player, material_id: str) -> int:
    count = 0
    for item in player.inventory:
        if getattr(item, 'material_id', None) == material_id:
            count += 1
    return count


def _consume_materials(player, material_id: str, amount: int):
    removed = 0
    for item in list(player.inventory):
        if removed >= amount:
            break
        if getattr(item, 'material_id', None) == material_id:
            player.inventory.remove(item)
            removed += 1


def _room_has_station(player, station_type: str) -> bool:
    """Check if current room has the required crafting station."""
    if not player.room:
        return False
    vnum = getattr(player.room, 'vnum', 0)
    if STATION_ROOMS.get(vnum) == station_type:
        return True
    # Also check room flags/extras
    if station_type in getattr(player.room, 'flags', set()):
        return True
    return False


def _skill_check(skill_level: int, crafting_level: int, recipe_level: int) -> bool:
    """Success check based on crafting level vs recipe level."""
    level_diff = crafting_level - recipe_level
    base = 50 + level_diff * 8 + skill_level // 2
    chance = max(15, min(95, base))
    return random.randint(1, 100) <= chance


def _is_critical() -> bool:
    """5% chance for critical craft."""
    return random.randint(1, 100) <= 5


# ---------------------------------------------------------------------------
# Gathering Commands
# ---------------------------------------------------------------------------

# Terrain -> (gathering skill, possible materials, weighted)
MINE_MATERIALS = {
    'mountain': [('copper_ore', 30), ('iron_ore', 40), ('silver_ore', 20), ('gold_ore', 8), ('mithril_ore', 2)],
    'hills':    [('copper_ore', 40), ('iron_ore', 35), ('silver_ore', 20), ('gold_ore', 5)],
    'dungeon':  [('iron_ore', 30), ('silver_ore', 25), ('gold_ore', 15), ('mithril_ore', 10), ('copper_ore', 20)],
}

FORAGE_MATERIALS = {
    'forest': [('healing_herb', 30), ('mana_leaf', 20), ('bloodmoss', 15), ('nightshade', 10), ('starflower', 5), ('firebloom', 5)],
    'field':  [('healing_herb', 40), ('mana_leaf', 25), ('bloodmoss', 15), ('firebloom', 10)],
    'swamp':  [('nightshade', 30), ('bloodmoss', 25), ('healing_herb', 20), ('mana_leaf', 10)],
}

FISH_MATERIALS = {
    'water_swim':   [('trout', 50), ('salmon', 35), ('golden_carp', 5)],
    'water_noswim': [('trout', 40), ('salmon', 40), ('golden_carp', 10)],
}

SKIN_MATERIALS_BY_CORPSE = {
    'wolf': [('wolf_pelt', 80), ('sturdy_hide', 20)],
    'bear': [('bear_hide', 70), ('thick_hide', 30)],
    'dragon': [('dragon_scale', 60), ('thick_hide', 40)],
    'default': [('sturdy_hide', 50), ('thick_hide', 40), ('wolf_pelt', 10)],
}


def _weighted_choice(options):
    """Pick from weighted list of (id, weight) tuples."""
    total = sum(w for _, w in options)
    r = random.randint(1, total)
    cumulative = 0
    for mat_id, weight in options:
        cumulative += weight
        if r <= cumulative:
            return mat_id
    return options[-1][0]


async def cmd_mine(player, args):
    """Mine ore from mountain/cave rooms."""
    c = player.config.COLORS
    if player.fighting:
        await player.send(f"{c['red']}You can't mine while fighting!{c['reset']}")
        return
    if not player.room:
        await player.send("You are nowhere!")
        return

    sector = getattr(player.room, 'sector_type', '')
    options = MINE_MATERIALS.get(sector)
    if not options:
        await player.send(f"{c['yellow']}There is nothing to mine here. Try mountain or cave areas.{c['reset']}")
        return

    if player.move < 5:
        await player.send(f"{c['yellow']}You are too exhausted to mine.{c['reset']}")
        return
    player.move -= 5

    _ensure_crafting_data(player)
    skill = player.skills.get('mining', 1)
    import nodes
    vein = nodes.at(player.room, 'ore')         # an ore vein here gives surely, and more
    if not vein and random.randint(1, 100) > min(90, 30 + skill + player.level * 2):
        await player.send(f"{c['yellow']}You swing your pick but find nothing useful.{c['reset']}")
        # Skill up chance on failure too
        if hasattr(player, 'improve_skill') and random.randint(1, 100) <= 15:
            await player.improve_skill('mining', difficulty=4)
        return

    mat_id = _weighted_choice(options)
    material = create_material(mat_id, getattr(player, 'world', None))
    if material:
        player.inventory.append(material)
        await player.send(f"{c['bright_cyan']}You mine {material.short_desc}.{c['reset']}")
        if vein:
            await _work_spot(player, options, 'You work the ore vein until it gives no more', 'bright_cyan')
        if hasattr(player, 'improve_skill'):
            await player.improve_skill('mining', difficulty=4)
        # Quest progress
        try:
            from quests import QuestManager
            await QuestManager.check_quest_progress(player, 'collect', {'item_vnum': material.vnum, 'item_name': material.name})
        except Exception:
            pass


async def _work_spot(player, options, words, colour):
    """A herb patch or ore vein worked (nodes.py): a second find from the better half of the
    ground's table, and the spot is spent a while."""
    import nodes
    c = player.config.COLORS
    nodes.take(player.room)
    best = sorted(options, key=lambda o: o[1])[:max(1, (len(options) + 1) // 2)]
    extra = create_material(_weighted_choice(best), getattr(player, 'world', None))
    if extra:
        player.inventory.append(extra)
        await player.send(f"{c[colour]}{words}: {extra.short_desc} as well.{c['reset']}")
    wm = getattr(getattr(player, 'world', None), 'web_map', None)
    if wm:
        try:
            await wm.notify_player(player)
        except Exception:
            pass


async def cmd_forage(player, args):
    """Forage for herbs in forest/field rooms."""
    c = player.config.COLORS
    if player.fighting:
        await player.send(f"{c['red']}You can't forage while fighting!{c['reset']}")
        return
    if not player.room:
        await player.send("You are nowhere!")
        return

    sector = getattr(player.room, 'sector_type', '')
    options = FORAGE_MATERIALS.get(sector)
    if not options:
        await player.send(f"{c['yellow']}There is nothing to forage here. Try forests or fields.{c['reset']}")
        return

    if player.move < 3:
        await player.send(f"{c['yellow']}You are too exhausted to forage.{c['reset']}")
        return
    player.move -= 3

    skill = player.skills.get('herbalism', 1)
    import nodes
    patch = nodes.at(player.room, 'herb')       # a herb patch here gives surely, and more
    if not patch and random.randint(1, 100) > min(90, 35 + skill + player.level * 2):
        await player.send(f"{c['yellow']}You search through the undergrowth but find nothing useful.{c['reset']}")
        if hasattr(player, 'improve_skill') and random.randint(1, 100) <= 15:
            await player.improve_skill('herbalism', difficulty=4)
        return

    mat_id = _weighted_choice(options)
    material = create_material(mat_id, getattr(player, 'world', None))
    if material:
        player.inventory.append(material)
        await player.send(f"{c['bright_green']}You find {material.short_desc}.{c['reset']}")
        if patch:
            await _work_spot(player, options, 'You pick the herb patch clean', 'bright_green')
        if hasattr(player, 'improve_skill'):
            await player.improve_skill('herbalism', difficulty=4)
        try:
            from quests import QuestManager
            await QuestManager.check_quest_progress(player, 'collect', {'item_vnum': material.vnum, 'item_name': material.name})
        except Exception:
            pass


async def cmd_fish(player, args):
    """Fish in water rooms."""
    c = player.config.COLORS
    if player.fighting:
        await player.send(f"{c['red']}You can't fish while fighting!{c['reset']}")
        return
    if not player.room:
        await player.send("You are nowhere!")
        return

    sector = getattr(player.room, 'sector_type', '')
    options = FISH_MATERIALS.get(sector)
    if not options:
        await player.send(f"{c['yellow']}There's no water here to fish in.{c['reset']}")
        return

    if player.move < 3:
        await player.send(f"{c['yellow']}You are too exhausted to fish.{c['reset']}")
        return
    player.move -= 3

    skill = player.skills.get('fishing', 1)
    if random.randint(1, 100) > min(90, 30 + skill + player.level * 2):
        await player.send(f"{c['yellow']}You wait patiently but nothing bites.{c['reset']}")
        if hasattr(player, 'improve_skill') and random.randint(1, 100) <= 15:
            await player.improve_skill('fishing', difficulty=3)
        return

    mat_id = _weighted_choice(options)
    material = create_material(mat_id, getattr(player, 'world', None))
    if material:
        player.inventory.append(material)
        await player.send(f"{c['bright_cyan']}You catch {material.short_desc}!{c['reset']}")
        if hasattr(player, 'improve_skill'):
            await player.improve_skill('fishing', difficulty=3)
        try:
            from quests import QuestManager
            await QuestManager.check_quest_progress(player, 'collect', {'item_vnum': material.vnum, 'item_name': material.name})
        except Exception:
            pass


async def cmd_skin(player, args):
    """Skin an animal corpse for hides."""
    c = player.config.COLORS
    if player.fighting:
        await player.send(f"{c['red']}You can't skin while fighting!{c['reset']}")
        return
    if not player.room:
        await player.send("You are nowhere!")
        return

    # Find a corpse
    target_name = ' '.join(args).lower() if args else ''
    corpse = None
    for item in player.room.items:
        if getattr(item, 'item_type', '') == 'container' and 'corpse' in item.name.lower():
            if getattr(item, 'skinned', False):
                continue
            if target_name and target_name not in item.name.lower():
                continue
            corpse = item
            break

    if not corpse:
        await player.send(f"{c['yellow']}There's no suitable corpse to skin here.{c['reset']}")
        return

    if player.move < 3:
        await player.send(f"{c['yellow']}You are too exhausted to skin.{c['reset']}")
        return
    player.move -= 3

    skill = player.skills.get('skinning', 1)
    if random.randint(1, 100) > min(90, 30 + skill + player.level * 2):
        await player.send(f"{c['yellow']}You fail to properly skin the corpse.{c['reset']}")
        corpse.skinned = True  # Still mark as attempted
        if hasattr(player, 'improve_skill') and random.randint(1, 100) <= 15:
            await player.improve_skill('skinning', difficulty=4)
        return

    # Determine hide type based on corpse name
    corpse_lower = corpse.name.lower()
    options = SKIN_MATERIALS_BY_CORPSE.get('default')
    for key in SKIN_MATERIALS_BY_CORPSE:
        if key != 'default' and key in corpse_lower:
            options = SKIN_MATERIALS_BY_CORPSE[key]
            break

    mat_id = _weighted_choice(options)
    material = create_material(mat_id, getattr(player, 'world', None))
    if material:
        player.inventory.append(material)
        corpse.skinned = True
        await player.send(f"{c['bright_cyan']}You skin {corpse.short_desc} and obtain {material.short_desc}.{c['reset']}")
        if hasattr(player, 'improve_skill'):
            await player.improve_skill('skinning', difficulty=4)
        try:
            from quests import QuestManager
            await QuestManager.check_quest_progress(player, 'collect', {'item_vnum': material.vnum, 'item_name': material.name})
        except Exception:
            pass


async def gather(player):
    """Legacy gather command - routes to appropriate skill."""
    c = player.config.COLORS
    if not player.room:
        await player.send("You are nowhere!")
        return

    sector = getattr(player.room, 'sector_type', '')

    # Check for skinnable corpse first
    for item in player.room.items:
        if getattr(item, 'item_type', '') == 'container' and 'corpse' in item.name.lower():
            if not getattr(item, 'skinned', False):
                await cmd_skin(player, [])
                return

    if sector in MINE_MATERIALS:
        await cmd_mine(player, [])
    elif sector in FORAGE_MATERIALS:
        await cmd_forage(player, [])
    elif sector in FISH_MATERIALS:
        await cmd_fish(player, [])
    else:
        await player.send(f"{c['yellow']}There's nothing to gather here.{c['reset']}")


# ---------------------------------------------------------------------------
# Crafting Commands
# ---------------------------------------------------------------------------

async def craft(player, recipe_id: str):
    """Craft an item from a recipe."""
    c = player.config.COLORS
    _ensure_crafting_data(player)

    if player.fighting:
        await player.send(f"{c['red']}You can't craft while fighting!{c['reset']}")
        return

    recipe = RECIPES.get(recipe_id)
    if not recipe:
        await player.send(f"{c['yellow']}Unknown recipe '{recipe_id}'. Type 'recipes' to see known recipes.{c['reset']}")
        return

    # Must know recipe
    if recipe_id not in player.known_recipes:
        await player.send(f"{c['yellow']}You don't know that recipe. Find a recipe scroll or learn it from a trainer.{c['reset']}")
        return

    # Check crafting level
    craft_level = get_crafting_level(player, recipe.skill)
    if craft_level < recipe.skill_required:
        await player.send(f"{c['yellow']}Your {recipe.skill} level ({craft_level}) is too low. You need level {recipe.skill_required}.{c['reset']}")
        return

    # Check station (enchanting and others need a station)
    if recipe.station and not _room_has_station(player, recipe.station):
        station_name = STATION_NAMES.get(recipe.station, recipe.station)
        await player.send(f"{c['yellow']}You need to be at {station_name} to craft this.{c['reset']}")
        return

    # Enchanting special: need a target item equipped
    is_enchant = recipe.output.get('enchant', False)
    enchant_target = None
    if is_enchant:
        target_type = recipe.output.get('target', 'weapon')
        if target_type == 'weapon':
            enchant_target = player.equipment.get('wield')
        elif target_type == 'armor':
            # Find first armor piece
            for slot in ['body', 'head', 'legs', 'feet', 'arms', 'hands', 'about', 'shield']:
                if player.equipment.get(slot):
                    enchant_target = player.equipment[slot]
                    break
        if not enchant_target:
            await player.send(f"{c['yellow']}You need to have a {target_type} equipped to enchant.{c['reset']}")
            return

    # Check ingredients
    missing = []
    for mat_id, amount in recipe.ingredients.items():
        have = _count_materials(player, mat_id)
        if have < amount:
            mat_name = MATERIALS.get(mat_id, {}).get('name', mat_id.replace('_', ' '))
            missing.append(f"{amount}x {mat_name} (have {have})")

    if missing:
        await player.send(f"{c['yellow']}Missing materials: {', '.join(missing)}{c['reset']}")
        return

    # Consume materials
    for mat_id, amount in recipe.ingredients.items():
        _consume_materials(player, mat_id, amount)

    # Skill check
    skill_level = player.skills.get(recipe.skill, 0)
    success = _skill_check(skill_level, craft_level, recipe.skill_required)

    if not success:
        await player.send(f"{c['red']}Your crafting attempt fails! The materials are wasted.{c['reset']}")
        # Still get some XP on failure
        add_crafting_xp(player, recipe.skill, recipe.exp_reward // 4)
        logger.info(f"{player.name} failed recipe {recipe_id}")
        return

    critical = _is_critical()

    if is_enchant:
        # Apply enchantment to target item
        bonus = dict(recipe.output['bonus'])
        suffix = recipe.output.get('suffix', '')
        flag = recipe.output.get('flag')
        if critical:
            bonus['value'] = bonus.get('value', 0) + 1
        if not hasattr(enchant_target, 'affects') or enchant_target.affects is None:
            enchant_target.affects = []
        enchant_target.affects.append(bonus)
        if suffix and suffix not in enchant_target.short_desc:
            enchant_target.short_desc += f" {suffix}"
            enchant_target.name += f" {suffix.lower()}"
        if flag:
            if not hasattr(enchant_target, 'flags'):
                enchant_target.flags = set()
            enchant_target.flags.add(flag)
        quality = f" {c['bright_magenta']}(Superior!){c['reset']}" if critical else ""
        await player.send(f"{c['bright_green']}You enchant {enchant_target.short_desc} with {recipe.name}!{quality}{c['reset']}")
    else:
        # Create crafted item
        item = _create_object_from_def(recipe.output, getattr(player, 'world', None))
        item.flags.add('crafted')

        if critical:
            # Boost stats by +1
            if item.affects:
                for aff in item.affects:
                    if isinstance(aff, dict):
                        aff['value'] = aff.get('value', 0) + 1
            if item.item_type == 'weapon':
                # Parse and boost damage dice
                parts = item.damage_dice.split('d')
                if len(parts) == 2:
                    try:
                        num, sides = parts[0], parts[1]
                        # Handle +N suffix
                        plus = 0
                        if '+' in sides:
                            sides, plus_str = sides.split('+')
                            plus = int(plus_str)
                        item.damage_dice = f"{num}d{sides}+{plus + 1}"
                    except Exception:
                        pass
            elif item.item_type == 'armor':
                item.armor += 1
            item.short_desc = f"{item.short_desc} (superior)"
            item.flags.add('superior')

        player.inventory.append(item)
        quality = f" {c['bright_magenta']}(Superior quality!){c['reset']}" if critical else ""
        await player.send(f"{c['bright_green']}You craft {item.short_desc}!{quality}{c['reset']}")

        # Track for collections/quests
        try:
            from quests import QuestManager
            await QuestManager.check_quest_progress(player, 'collect', {'item_vnum': item.vnum, 'item_name': item.name})
        except Exception:
            pass

    # XP
    leveled = add_crafting_xp(player, recipe.skill, recipe.exp_reward)
    await player.send(f"{c['bright_yellow']}You gain {recipe.exp_reward} {recipe.skill} XP.{c['reset']}")
    if leveled:
        new_level = get_crafting_level(player, recipe.skill)
        await player.send(f"{c['bright_magenta']}Your {recipe.skill} skill has reached level {new_level}!{c['reset']}")

    # General XP reward (smaller)
    char_xp = recipe.exp_reward // 2
    player.exp += char_xp
    await player.send(f"{c['bright_yellow']}You gain {char_xp} experience.{c['reset']}")

    # Skill improvement
    if hasattr(player, 'improve_skill'):
        await player.improve_skill(recipe.skill, difficulty=6)

    logger.info(f"{player.name} crafted {recipe_id} (critical={critical})")


async def show_recipes(player, args=None):
    """Show recipes the player knows."""
    c = player.config.COLORS
    _ensure_crafting_data(player)

    filter_disc = None
    if args:
        arg = args[0].lower()
        if arg in CRAFTING_DISCIPLINES:
            filter_disc = arg

    if not player.known_recipes:
        await player.send(f"{c['yellow']}You don't know any recipes yet. Find recipe scrolls or visit a trainer.{c['reset']}")
        return

    await player.send(f"\n{c['bright_yellow']}{'═' * 60}")
    await player.send(f"{'KNOWN RECIPES':^60}")
    await player.send(f"{'═' * 60}{c['reset']}")

    by_disc = {}
    for rid in player.known_recipes:
        recipe = RECIPES.get(rid)
        if not recipe:
            continue
        if filter_disc and recipe.skill != filter_disc:
            continue
        by_disc.setdefault(recipe.skill, []).append(recipe)

    for disc in CRAFTING_DISCIPLINES:
        recipes = by_disc.get(disc, [])
        if not recipes:
            continue
        level = get_crafting_level(player, disc)
        xp = get_crafting_xp(player, disc)
        next_xp = CRAFTING_XP_TABLE[level] if level < 20 else 0
        await player.send(f"\n{c['bright_cyan']}{disc.title()} (Level {level}, {xp}/{next_xp} XP):{c['reset']}")
        for r in sorted(recipes, key=lambda x: x.skill_required):
            mats = ", ".join(f"{amt}x {MATERIALS.get(mid,{}).get('name', mid.replace('_',' '))}" for mid, amt in r.ingredients.items())
            can_craft = level >= r.skill_required
            color = c['bright_green'] if can_craft else c['red']
            await player.send(f"  {color}{r.recipe_id:20}{c['white']} {r.name:25} [Lv{r.skill_required}] {c['yellow']}{mats}{c['reset']}")

    await player.send(f"\n{c['white']}Use 'craft <recipe_id>' to craft. Enchanting requires the item equipped.{c['reset']}")


async def craft_list(player, args=None):
    """Show available recipes at current crafting station."""
    c = player.config.COLORS
    _ensure_crafting_data(player)

    # Determine station
    vnum = getattr(player.room, 'vnum', 0) if player.room else 0
    station = STATION_ROOMS.get(vnum)

    if not station:
        await player.send(f"{c['yellow']}You're not at a crafting station. Visit a forge, alchemy table, workbench, or enchanting circle.{c['reset']}")
        return

    station_name = STATION_NAMES.get(station, station)
    disc = [d for d, s in DISCIPLINE_STATIONS.items() if s == station]
    if not disc:
        return
    disc = disc[0]

    level = get_crafting_level(player, disc)
    await player.send(f"\n{c['bright_yellow']}Recipes available at {station_name} ({disc.title()} Lv{level}):{c['reset']}")

    found = False
    for rid, recipe in sorted(RECIPES.items(), key=lambda x: x[1].skill_required):
        if recipe.skill != disc:
            continue
        known = rid in player.known_recipes
        can_craft = level >= recipe.skill_required and known
        mats = ", ".join(f"{amt}x {MATERIALS.get(mid,{}).get('name', mid.replace('_',' '))}" for mid, amt in recipe.ingredients.items())
        if known:
            color = c['bright_green'] if can_craft else c['red']
            await player.send(f"  {color}{rid:20} {recipe.name:25} [Lv{recipe.skill_required}] {c['yellow']}{mats}{c['reset']}")
        else:
            await player.send(f"  {c['blue']}{'???':20} {'Unknown Recipe':25} [Lv{recipe.skill_required}]{c['reset']}")
        found = True

    if not found:
        await player.send(f"  {c['yellow']}No recipes for this station.{c['reset']}")


# ---------------------------------------------------------------------------
# Recipe scroll items
# ---------------------------------------------------------------------------

def create_recipe_scroll(recipe_id: str, world=None) -> Optional[Object]:
    """Create a recipe scroll item that teaches a recipe when read."""
    recipe = RECIPES.get(recipe_id)
    if not recipe:
        return None
    obj = Object(9500 + hash(recipe_id) % 500, world)
    obj.name = f"a recipe scroll: {recipe.name}"
    obj.short_desc = f"a recipe scroll: {recipe.name}"
    obj.room_desc = f"A recipe scroll for {recipe.name} lies here."
    obj.description = f"A scroll containing instructions for crafting {recipe.name}. Read it to learn the recipe."
    obj.item_type = 'scroll'
    obj.weight = 1
    obj.cost = recipe.skill_required * 25
    obj.recipe_id = recipe_id
    obj.readable_text = f"Recipe: {recipe.name}\nDiscipline: {recipe.skill.title()}\nRequired Level: {recipe.skill_required}\nIngredients: {', '.join(f'{v}x {k.replace(chr(95),chr(32))}' for k,v in recipe.ingredients.items())}"
    obj.flags.add('recipe_scroll')
    return obj


async def handle_recipe_scroll(player, item) -> bool:
    """Called when a player reads a recipe scroll. Returns True if consumed."""
    recipe_id = getattr(item, 'recipe_id', None)
    if not recipe_id:
        return False
    c = player.config.COLORS
    _ensure_crafting_data(player)
    if learn_recipe(player, recipe_id):
        recipe = RECIPES[recipe_id]
        await player.send(f"{c['bright_magenta']}You learn the recipe: {recipe.name}!{c['reset']}")
        if item in player.inventory:
            player.inventory.remove(item)
        return True
    else:
        await player.send(f"{c['yellow']}You already know this recipe.{c['reset']}")
        return False


# ---------------------------------------------------------------------------
# Save/Load helpers
# ---------------------------------------------------------------------------

def save_crafting_data(player) -> dict:
    """Return crafting data for player save."""
    _ensure_crafting_data(player)
    return {
        'known_recipes': player.known_recipes,
        'crafting_levels': player.crafting_levels,
        'crafting_xp': player.crafting_xp,
    }


def load_crafting_data(player, data: dict):
    """Load crafting data from save dict."""
    player.known_recipes = data.get('known_recipes', list(STARTER_RECIPES))
    player.crafting_levels = data.get('crafting_levels', {})
    player.crafting_xp = data.get('crafting_xp', {})


# ---------------------------------------------------------------------------
# List helper for commands
# ---------------------------------------------------------------------------

def list_recipes() -> Dict[str, Recipe]:
    return RECIPES
