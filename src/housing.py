"""
Misthollow Housing System
========================
Full player housing with purchasing, storage, furniture, and teleportation.
"""

import json
import os
import time
import logging
from typing import Optional, Dict, List

logger = logging.getLogger('Misthollow.Housing')

# House sizes and costs
HOUSE_SIZES = {
    'small': {'cost': 5000, 'label': 'Small Cottage', 'storage_max': 50},
    'medium': {'cost': 15000, 'label': 'Medium Townhouse', 'storage_max': 50},
    'large': {'cost': 50000, 'label': 'Grand Estate', 'storage_max': 50},
}

SELL_REFUND_RATE = 0.5  # 50% refund

# Furniture definitions with bonuses
FURNITURE_DEFS = {
    'bed': {
        'vnum': 26050,
        'name': 'Oak Four-Poster Bed',
        'bonus_type': 'hp_regen',
        'bonus_desc': '+50% HP regen when resting at home',
    },
    'table': {
        'vnum': 26051,
        'name': 'Elegant Dining Table',
        'bonus_type': 'none',
        'bonus_desc': 'A fine place to dine.',
    },
    'trophy case': {
        'vnum': 26052,
        'name': 'Ornate Trophy Case',
        'bonus_type': 'trophy_display',
        'bonus_desc': 'Displays your achievements to visitors.',
    },
    'weapon rack': {
        'vnum': 26053,
        'name': 'Polished Weapon Rack',
        'bonus_type': 'weapon_display',
        'bonus_desc': 'Display your finest weapons.',
    },
    'bookshelf': {
        'vnum': 26054,
        'name': 'Mahogany Bookshelf',
        'bonus_type': 'lore_display',
        'bonus_desc': 'Stores and displays discovered lore.',
    },
}

FURNITURE_VNUMS = {v['vnum']: k for k, v in FURNITURE_DEFS.items()}

# Persistence file
HOUSING_DATA_FILE = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'data', 'housing.json')

HOME_COOLDOWN = 1800  # 30 minutes


def _ensure_data_dir():
    os.makedirs(os.path.dirname(HOUSING_DATA_FILE), exist_ok=True)


def load_housing_data() -> dict:
    """Load all housing data from JSON."""
    if os.path.exists(HOUSING_DATA_FILE):
        try:
            with open(HOUSING_DATA_FILE, 'r') as f:
                return json.load(f)
        except Exception:
            pass
    return {'houses': {}}


def save_housing_data(data: dict):
    """Save housing data to JSON."""
    _ensure_data_dir()
    with open(HOUSING_DATA_FILE, 'w') as f:
        json.dump(data, f, indent=2)


def get_house(player_name: str) -> Optional[dict]:
    """Get a player's house data."""
    data = load_housing_data()
    return data['houses'].get(player_name.lower())


def set_house(player_name: str, house_data: dict):
    """Set a player's house data."""
    data = load_housing_data()
    data['houses'][player_name.lower()] = house_data
    save_housing_data(data)


def remove_house(player_name: str):
    """Remove a player's house."""
    data = load_housing_data()
    data['houses'].pop(player_name.lower(), None)
    save_housing_data(data)


def get_plot_info(room) -> Optional[dict]:
    """Extract plot info from room flags. Returns {size, plot_num} or None."""
    for flag in getattr(room, 'flags', set()):
        if isinstance(flag, str) and flag.startswith('house_plot:'):
            parts = flag.split(':')
            if len(parts) == 3:
                return {'size': parts[1], 'plot_num': int(parts[2])}
    return None


def get_plot_owner(plot_num: int) -> Optional[str]:
    """Check if a plot is owned. Returns owner name or None."""
    data = load_housing_data()
    for owner, house in data['houses'].items():
        if house.get('plot_num') == plot_num:
            return owner
    return None


class HouseManager:
    """Manages player housing."""

    DEFAULT_HOUSE_COST = 5000

    @staticmethod
    def can_buy_here(player) -> bool:
        if not player.room:
            return False
        return get_plot_info(player.room) is not None

    @staticmethod
    async def buy_house(player, cost: Optional[int] = None) -> bool:
        """Buy a house at the current plot."""
        c = player.config.COLORS

        # Check if already owns a house
        existing = get_house(player.name)
        if existing:
            await player.send(f"{c['yellow']}You already own a house (Plot #{existing['plot_num']}). Sell it first with 'house sell'.{c['reset']}")
            return False

        # Check if standing on a plot
        plot = get_plot_info(player.room)
        if not plot:
            await player.send(f"{c['red']}You're not standing on a house plot. Visit the Housing District!{c['reset']}")
            return False

        # Check if plot is taken
        owner = get_plot_owner(plot['plot_num'])
        if owner:
            await player.send(f"{c['red']}This plot is already owned by {owner.title()}.{c['reset']}")
            return False

        size_info = HOUSE_SIZES.get(plot['size'])
        if not size_info:
            await player.send(f"{c['red']}Invalid plot size.{c['reset']}")
            return False

        cost = size_info['cost']
        if player.gold < cost:
            await player.send(f"{c['red']}You need {cost:,} gold to buy this {size_info['label']}. You have {player.gold:,}.{c['reset']}")
            return False

        player.gold -= cost
        player.house_vnum = player.room.vnum

        house_data = {
            'plot_num': plot['plot_num'],
            'room_vnum': player.room.vnum,
            'size': plot['size'],
            'cost': cost,
            'owner': player.name,
            'name': f"{player.name}'s {size_info['label']}",
            'description': None,
            'furniture': [],
            'storage': [],
            'guests': [],
            'locked': False,
            'purchased_at': time.time(),
        }
        set_house(player.name, house_data)

        await player.send(f"{c['bright_green']}═══ CONGRATULATIONS! ═══{c['reset']}")
        await player.send(f"{c['green']}You purchased Plot #{plot['plot_num']} ({size_info['label']}) for {cost:,} gold!{c['reset']}")
        await player.send(f"{c['cyan']}Use 'house name <name>' to name your home.{c['reset']}")
        await player.send(f"{c['cyan']}Use 'home' to teleport here from anywhere (30 min cooldown).{c['reset']}")
        await player.send(f"{c['cyan']}Use 'store <item>' / 'retrieve <item>' to use your storage chest.{c['reset']}")
        logger.info(f"{player.name} bought house plot #{plot['plot_num']} ({plot['size']}) for {cost} gold")
        return True

    @staticmethod
    async def sell_house(player):
        """Sell the player's house back."""
        c = player.config.COLORS
        house = get_house(player.name)
        if not house:
            await player.send(f"{c['red']}You don't own a house.{c['reset']}")
            return

        # Check storage is empty
        if house.get('storage'):
            await player.send(f"{c['yellow']}You must retrieve all items from storage before selling! ({len(house['storage'])} items remaining){c['reset']}")
            return

        refund = int(house['cost'] * SELL_REFUND_RATE)
        player.gold += refund
        player.house_vnum = None
        player.house_storage = []
        remove_house(player.name)

        await player.send(f"{c['yellow']}You sold your house for {refund:,} gold (50% refund).{c['reset']}")
        logger.info(f"{player.name} sold house plot #{house['plot_num']} for {refund} gold")

    @staticmethod
    async def list_houses(player):
        """Show available and owned houses."""
        c = player.config.COLORS
        data = load_housing_data()

        # Build owned plots set
        owned = {}
        for owner, house in data['houses'].items():
            owned[house['plot_num']] = (owner, house)

        await player.send(f"\n{c['bright_cyan']}═══ Garathorm Housing District ═══{c['reset']}")
        # (the heading in step with the rows below: "  {plot:>3}   {size:<16} {cost:>6,}g  {status}")
        await player.send(f"{c['white']}  {'#':>3}   {'Size':<16} {'Cost':>7}  {'Status'}{c['reset']}")
        await player.send(f"{c['white']}{'─'*55}{c['reset']}")

        for plot_num in range(1, 21):
            size = 'small' if plot_num <= 4 or (11 <= plot_num <= 14) else ('medium' if plot_num <= 7 or (15 <= plot_num <= 17) else 'large')
            size_info = HOUSE_SIZES[size]

            if plot_num in owned:
                owner_name, house = owned[plot_num]
                house_name = house.get('name', f"{owner_name.title()}'s House")
                if owner_name.lower() == player.name.lower():
                    status = f"{c['bright_green']}★ YOURS - {house_name}{c['reset']}"
                else:
                    status = f"{c['red']}Owned by {owner_name.title()}{c['reset']}"
            else:
                status = f"{c['green']}Available{c['reset']}"

            await player.send(f"  {c['white']}{plot_num:>3}   {size_info['label']:<16} {size_info['cost']:>6,}g  {status}")

        await player.send(f"\n{c['cyan']}Stand on a plot and type 'house buy' to purchase.{c['reset']}")

    @staticmethod
    async def teleport_home(player):
        """Teleport player to their house."""
        c = player.config.COLORS
        house = get_house(player.name)
        if not house:
            await player.send(f"{c['red']}You don't own a house. Visit the Housing District to buy one!{c['reset']}")
            return

        # Cooldown check
        last_home = getattr(player, '_home_cooldown', 0)
        remaining = HOME_COOLDOWN - (time.time() - last_home)
        if remaining > 0:
            mins = int(remaining // 60)
            secs = int(remaining % 60)
            await player.send(f"{c['yellow']}You must wait {mins}m {secs}s before teleporting home again.{c['reset']}")
            return

        # Can't teleport while fighting
        if player.fighting:
            player.fighting = None
            player.position = 'standing'

        if player.position == 'fighting':
            player.position = 'standing'

        target_room = player.world.get_room(house['room_vnum'])
        if not target_room:
            await player.send(f"{c['red']}Your house seems to have vanished! Contact an admin.{c['reset']}")
            return

        # Move player
        if player.room:
            await player.room.send_to_room(f"{player.name} vanishes in a shimmer of light.", exclude=[player])
            if player in player.room.characters:
                player.room.characters.remove(player)

        player.room = target_room
        if player not in target_room.characters:
            target_room.characters.append(player)

        player._home_cooldown = time.time()
        await player.send(f"{c['bright_cyan']}You close your eyes and feel the familiar pull of home...{c['reset']}")
        await player.send(f"{c['bright_green']}You materialize in your house!{c['reset']}")
        await target_room.send_to_room(f"{player.name} materializes in a shimmer of light.", exclude=[player])
        await player.do_look([])

    @staticmethod
    async def lock_house(player):
        """Lock the house to prevent others from entering."""
        c = player.config.COLORS
        house = get_house(player.name)
        if not house:
            await player.send(f"{c['red']}You don't own a house.{c['reset']}")
            return
        house['locked'] = True
        set_house(player.name, house)
        await player.send(f"{c['green']}Your house is now locked. Only you and invited guests may enter.{c['reset']}")

    @staticmethod
    async def unlock_house(player):
        """Unlock the house to allow anyone to enter."""
        c = player.config.COLORS
        house = get_house(player.name)
        if not house:
            await player.send(f"{c['red']}You don't own a house.{c['reset']}")
            return
        house['locked'] = False
        set_house(player.name, house)
        await player.send(f"{c['yellow']}Your house is now unlocked. Anyone may enter.{c['reset']}")

    @staticmethod
    async def invite_guest(player, guest_name: str):
        """Invite a player to visit your house."""
        c = player.config.COLORS
        house = get_house(player.name)
        if not house:
            await player.send(f"{c['red']}You don't own a house.{c['reset']}")
            return

        guest_name = guest_name.lower()
        if guest_name in house.get('guests', []):
            await player.send(f"{c['yellow']}{guest_name.title()} is already on your guest list.{c['reset']}")
            return

        if 'guests' not in house:
            house['guests'] = []
        house['guests'].append(guest_name)
        set_house(player.name, house)
        await player.send(f"{c['green']}{guest_name.title()} has been added to your guest list.{c['reset']}")

        # Notify if online
        guest = player.world.get_player(guest_name) if player.world else None
        if guest:
            await guest.send(f"{c['cyan']}{player.name} has invited you to visit their house!{c['reset']}")

    @staticmethod
    async def set_name(player, name: str):
        """Set a custom house name."""
        c = player.config.COLORS
        house = get_house(player.name)
        if not house:
            await player.send(f"{c['red']}You don't own a house.{c['reset']}")
            return
        if len(name) > 60:
            await player.send(f"{c['red']}House name too long (max 60 characters).{c['reset']}")
            return
        house['name'] = name
        set_house(player.name, house)
        await player.send(f"{c['green']}Your house is now named: {c['bright_white']}{name}{c['reset']}")

    @staticmethod
    async def set_description(player, desc: str):
        """Set a custom house description."""
        c = player.config.COLORS
        house = get_house(player.name)
        if not house:
            await player.send(f"{c['red']}You don't own a house.{c['reset']}")
            return
        if len(desc) > 500:
            await player.send(f"{c['red']}Description too long (max 500 characters).{c['reset']}")
            return
        house['description'] = desc
        set_house(player.name, house)
        await player.send(f"{c['green']}House description updated!{c['reset']}")

    @staticmethod
    async def show_furniture(player):
        """Show installed furniture and bonuses."""
        c = player.config.COLORS
        house = get_house(player.name)
        if not house:
            await player.send(f"{c['red']}You don't own a house.{c['reset']}")
            return

        furniture = house.get('furniture', [])
        await player.send(f"\n{c['bright_cyan']}═══ {house.get('name', 'Your House')} - Furniture ═══{c['reset']}")

        if not furniture:
            await player.send(f"{c['yellow']}No furniture installed. Buy some from Hearth & Home Furnishings!{c['reset']}")
            return

        for item_key in furniture:
            fdef = FURNITURE_DEFS.get(item_key)
            if fdef:
                await player.send(f"  {c['bright_white']}{fdef['name']}{c['reset']} - {c['cyan']}{fdef['bonus_desc']}{c['reset']}")

    @staticmethod
    async def install_furniture(player, item_name: str):
        """Install furniture from inventory into house."""
        c = player.config.COLORS
        house = get_house(player.name)
        if not house:
            await player.send(f"{c['red']}You don't own a house.{c['reset']}")
            return

        if not HouseManager.in_house(player):
            await player.send(f"{c['red']}You must be in your house to install furniture.{c['reset']}")
            return

        # Find furniture item in inventory
        item_name_lower = item_name.lower()
        item = None
        for obj in player.inventory:
            if item_name_lower in obj.name.lower() or item_name_lower in obj.short_desc.lower():
                if getattr(obj, 'vnum', None) in FURNITURE_VNUMS:
                    item = obj
                    break

        if not item:
            await player.send(f"{c['red']}You don't have that furniture item. Buy some from Hearth & Home Furnishings!{c['reset']}")
            return

        furn_key = FURNITURE_VNUMS.get(item.vnum)
        if not furn_key:
            await player.send(f"{c['red']}That item can't be installed as furniture.{c['reset']}")
            return

        if furn_key in house.get('furniture', []):
            await player.send(f"{c['yellow']}You already have a {FURNITURE_DEFS[furn_key]['name']} installed.{c['reset']}")
            return

        if 'furniture' not in house:
            house['furniture'] = []
        house['furniture'].append(furn_key)
        set_house(player.name, house)
        player.inventory.remove(item)

        fdef = FURNITURE_DEFS[furn_key]
        await player.send(f"{c['bright_green']}You install {fdef['name']} in your house!{c['reset']}")
        await player.send(f"{c['cyan']}Bonus: {fdef['bonus_desc']}{c['reset']}")

    @staticmethod
    async def store_item(player, item_name: str):
        """Store an item in the house chest."""
        c = player.config.COLORS
        house = get_house(player.name)
        if not house:
            await player.send(f"{c['red']}You don't own a house.{c['reset']}")
            return

        if not HouseManager.in_house(player):
            await player.send(f"{c['red']}You must be in your house to store items.{c['reset']}")
            return

        storage = house.get('storage', [])
        if len(storage) >= 50:
            await player.send(f"{c['red']}Your storage chest is full! (50/50 items){c['reset']}")
            return

        item = None
        item_name_lower = item_name.lower()
        for obj in player.inventory:
            if item_name_lower in obj.name.lower() or item_name_lower in obj.short_desc.lower():
                item = obj
                break

        if not item:
            await player.send(f"{c['red']}You don't have that item.{c['reset']}")
            return

        player.inventory.remove(item)
        storage.append(item.to_dict())
        house['storage'] = storage
        set_house(player.name, house)

        # Also update player's house_storage for save compat
        player.house_storage.append(item)

        await player.send(f"{c['green']}You store {item.short_desc} in your chest. ({len(storage)}/50){c['reset']}")

    @staticmethod
    async def retrieve_item(player, item_name: str):
        """Retrieve an item from the house chest."""
        c = player.config.COLORS
        house = get_house(player.name)
        if not house:
            await player.send(f"{c['red']}You don't own a house.{c['reset']}")
            return

        if not HouseManager.in_house(player):
            await player.send(f"{c['red']}You must be in your house to retrieve items.{c['reset']}")
            return

        storage = house.get('storage', [])
        if not storage:
            await player.send(f"{c['yellow']}Your storage chest is empty.{c['reset']}")
            return

        from objects import Object
        item_name_lower = item_name.lower()
        for i, item_data in enumerate(storage):
            name = item_data.get('name', '').lower()
            short = item_data.get('short_desc', '').lower()
            if item_name_lower in name or item_name_lower in short:
                obj = Object.from_dict(item_data, player.world)
                player.inventory.append(obj)
                storage.pop(i)
                house['storage'] = storage
                set_house(player.name, house)

                # Sync player house_storage
                for j, hs_item in enumerate(player.house_storage):
                    if hasattr(hs_item, 'name') and hs_item.name.lower() == name:
                        player.house_storage.pop(j)
                        break

                await player.send(f"{c['green']}You retrieve {obj.short_desc} from your chest. ({len(storage)}/50){c['reset']}")
                return

        await player.send(f"{c['red']}That item is not in your chest.{c['reset']}")

    @staticmethod
    async def show_storage(player):
        """List items in storage chest."""
        c = player.config.COLORS
        house = get_house(player.name)
        if not house:
            await player.send(f"{c['red']}You don't own a house.{c['reset']}")
            return

        if not HouseManager.in_house(player):
            await player.send(f"{c['red']}You must be in your house to view storage.{c['reset']}")
            return

        storage = house.get('storage', [])
        await player.send(f"\n{c['bright_cyan']}═══ Storage Chest ({len(storage)}/50) ═══{c['reset']}")

        if not storage:
            await player.send(f"{c['yellow']}Your chest is empty.{c['reset']}")
            return

        for item_data in storage:
            await player.send(f"  {c['white']}{item_data.get('short_desc', item_data.get('name', 'Unknown'))}{c['reset']}")

    @staticmethod
    async def show_info(player):
        """Show detailed house info."""
        c = player.config.COLORS
        house = get_house(player.name)
        if not house:
            await player.send(f"{c['yellow']}You don't own a house.{c['reset']}")
            await player.send(f"{c['cyan']}Visit the Housing District to buy one! Type 'house list' for plots.{c['reset']}")
            return

        size_info = HOUSE_SIZES.get(house['size'], {})
        await player.send(f"\n{c['bright_cyan']}═══ {house.get('name', 'Your House')} ═══{c['reset']}")
        await player.send(f"  {c['white']}Plot:        {c['bright_white']}#{house['plot_num']}{c['reset']}")
        await player.send(f"  {c['white']}Size:        {c['bright_white']}{size_info.get('label', house['size'])}{c['reset']}")
        await player.send(f"  {c['white']}Room:        {c['bright_white']}{house['room_vnum']}{c['reset']}")
        locked_str = f"{c['red']}Locked" if house.get('locked') else f"{c['green']}Unlocked"
        await player.send(f"  {c['white']}Status:      {locked_str}{c['reset']}")
        guests = house.get('guests', [])
        guest_str = ', '.join([g.title() for g in guests]) if guests else 'None'
        await player.send(f"  {c['white']}Guests:      {c['bright_white']}{guest_str}{c['reset']}")
        furniture = house.get('furniture', [])
        furn_str = ', '.join([FURNITURE_DEFS[f]['name'] for f in furniture if f in FURNITURE_DEFS]) if furniture else 'None'
        await player.send(f"  {c['white']}Furniture:   {c['bright_white']}{furn_str}{c['reset']}")
        storage = house.get('storage', [])
        await player.send(f"  {c['white']}Storage:     {c['bright_white']}{len(storage)}/50 items{c['reset']}")
        if house.get('description'):
            await player.send(f"  {c['white']}Description: {c['bright_white']}{house['description']}{c['reset']}")

    @staticmethod
    def in_house(player) -> bool:
        """Check if player is in their own house."""
        house = get_house(player.name)
        if not house:
            return False
        return player.room and player.room.vnum == house.get('room_vnum')

    @staticmethod
    def has_furniture(player, furniture_key: str) -> bool:
        """Check if a player's house has specific furniture installed."""
        house = get_house(player.name)
        if not house:
            return False
        return furniture_key in house.get('furniture', [])

    @staticmethod
    def get_home_regen_bonus(player) -> float:
        """Get HP regen multiplier if player is resting at home with a bed."""
        if not HouseManager.in_house(player):
            return 1.0
        if HouseManager.has_furniture(player, 'bed'):
            return 1.5  # +50% HP regen
        return 1.0
