"""
Misthollow PvP Arena System
==========================
Opt-in PvP arena with ELO rating, matchmaking, and spectating.
"""

import asyncio
import random
import time
import logging
from typing import Dict, List, Optional, TYPE_CHECKING

if TYPE_CHECKING:
    from player import Player

logger = logging.getLogger('Misthollow.Arena')

# Arena room vnums
ARENA_LOBBY_VNUM = 25000
ARENA_GALLERY_VNUM = 25006
ARENA_ROOM_VNUMS = [25001, 25002, 25003, 25004, 25005]
ARENA_ROOM_NAMES = {
    25001: "The Open Sands",
    25002: "The Pillared Hall",
    25003: "The Elevated Platforms",
    25004: "The Water Pit",
    25005: "The Lava Bridge",
}

# ELO constants
ELO_START = 1000
ELO_K = 32

# Rewards
ARENA_GOLD_REWARD = 100
ARENA_POINTS_REWARD = 10


def _ensure_arena_stats(player):
    """Ensure player has arena stat attributes."""
    if not hasattr(player, 'arena_wins'):
        player.arena_wins = 0
    if not hasattr(player, 'arena_losses'):
        player.arena_losses = 0
    if not hasattr(player, 'arena_rating'):
        player.arena_rating = ELO_START
    if not hasattr(player, 'arena_highest_rating'):
        player.arena_highest_rating = ELO_START
    if not hasattr(player, 'arena_points'):
        player.arena_points = 0


def _calc_elo(winner_rating: int, loser_rating: int) -> tuple:
    """Calculate new ELO ratings. Returns (new_winner, new_loser)."""
    exp_w = 1 / (1 + 10 ** ((loser_rating - winner_rating) / 400))
    exp_l = 1 - exp_w
    new_w = round(winner_rating + ELO_K * (1 - exp_w))
    new_l = max(100, round(loser_rating + ELO_K * (0 - exp_l)))
    return new_w, new_l


class ArenaManager:
    """Manages the PvP arena system."""

    # Active matches: {match_id: {'player1': p, 'player2': p, 'room_vnum': int, 'started': bool}}
    active_matches: Dict[int, dict] = {}
    _match_counter = 0

    # Matchmaking queue
    queue: List = []  # list of Player objects

    # Pending challenges: {target_name_lower: {'challenger': Player, 'time': float}}
    pending_challenges: Dict[str, dict] = {}

    @classmethod
    def _next_match_id(cls) -> int:
        cls._match_counter += 1
        return cls._match_counter

    @classmethod
    def _is_in_lobby(cls, player) -> bool:
        return player.room and getattr(player.room, 'vnum', None) == ARENA_LOBBY_VNUM

    @classmethod
    def _is_in_gallery(cls, player) -> bool:
        return player.room and getattr(player.room, 'vnum', None) == ARENA_GALLERY_VNUM

    @classmethod
    def _get_match_for_player(cls, player) -> Optional[dict]:
        for match in cls.active_matches.values():
            if match['player1'] == player or match['player2'] == player:
                return match
        return None

    @classmethod
    async def _broadcast_to_gallery(cls, world, message: str):
        """Send a message to all players in the spectator gallery."""
        gallery = world.get_room(ARENA_GALLERY_VNUM) if world else None
        if gallery:
            await gallery.send_to_room(message)

    @classmethod
    async def _broadcast_to_lobby(cls, world, message: str):
        """Send a message to all players in the arena lobby."""
        lobby = world.get_room(ARENA_LOBBY_VNUM) if world else None
        if lobby:
            await lobby.send_to_room(message)

    @classmethod
    async def cmd_challenge(cls, player, args: list):
        """Challenge another player to an arena duel."""
        from config import Config
        c = Config().COLORS

        if not cls._is_in_lobby(player):
            await player.send(f"{c['red']}You must be in the Arena Lobby to issue challenges.{c['reset']}")
            return

        if not args:
            await player.send(f"{c['yellow']}Usage: challenge <player>{c['reset']}")
            return

        if cls._get_match_for_player(player):
            await player.send(f"{c['red']}You are already in a match!{c['reset']}")
            return

        target_name = args[0].lower()
        if target_name == player.name.lower():
            await player.send(f"{c['red']}You can't challenge yourself.{c['reset']}")
            return

        # Find target in lobby
        target = None
        for ch in player.room.characters:
            if hasattr(ch, 'connection') and ch.name.lower() == target_name and ch != player:
                target = ch
                break

        if not target:
            await player.send(f"{c['red']}That player is not in the lobby.{c['reset']}")
            return

        if cls._get_match_for_player(target):
            await player.send(f"{c['red']}{target.name} is already in a match.{c['reset']}")
            return

        # Store challenge
        cls.pending_challenges[target.name.lower()] = {
            'challenger': player,
            'time': time.time()
        }

        _ensure_arena_stats(player)
        _ensure_arena_stats(target)

        await player.send(f"{c['bright_yellow']}You challenge {target.name} to an arena duel!{c['reset']}")
        await target.send(
            f"\n{c['bright_yellow']}⚔ {player.name} challenges you to an arena duel! "
            f"(Rating: {player.arena_rating}){c['reset']}\n"
            f"{c['white']}Type 'accept' to fight or 'decline' to refuse.{c['reset']}"
        )

    @classmethod
    async def cmd_accept(cls, player, args: list):
        """Accept a pending arena challenge."""
        from config import Config
        c = Config().COLORS

        challenge = cls.pending_challenges.get(player.name.lower())
        if not challenge:
            await player.send(f"{c['yellow']}You have no pending arena challenges.{c['reset']}")
            return

        challenger = challenge['challenger']
        del cls.pending_challenges[player.name.lower()]

        # Validate both still in lobby
        if not cls._is_in_lobby(player) or not cls._is_in_lobby(challenger):
            await player.send(f"{c['red']}Both players must be in the Arena Lobby.{c['reset']}")
            return

        if not challenger.connection:
            await player.send(f"{c['red']}{challenger.name} is no longer online.{c['reset']}")
            return

        await cls._start_match(player, challenger)

    @classmethod
    async def cmd_decline(cls, player, args: list):
        """Decline a pending arena challenge."""
        from config import Config
        c = Config().COLORS

        challenge = cls.pending_challenges.get(player.name.lower())
        if not challenge:
            await player.send(f"{c['yellow']}You have no pending arena challenges.{c['reset']}")
            return

        challenger = challenge['challenger']
        del cls.pending_challenges[player.name.lower()]

        await player.send(f"{c['cyan']}You decline {challenger.name}'s challenge.{c['reset']}")
        if challenger.connection:
            await challenger.send(f"{c['yellow']}{player.name} declines your arena challenge.{c['reset']}")

    @classmethod
    async def cmd_arena(cls, player, args: list):
        """Arena subcommands: join, stats, top."""
        from config import Config
        c = Config().COLORS

        if not args:
            await player.send(
                f"{c['bright_cyan']}═══ Arena Commands ═══{c['reset']}\n"
                f"  {c['white']}challenge <player>{c['reset']} — Challenge someone to a duel\n"
                f"  {c['white']}accept / decline{c['reset']}   — Respond to a challenge\n"
                f"  {c['white']}arena join{c['reset']}         — Queue for random matchmaking\n"
                f"  {c['white']}arena stats{c['reset']}        — View your PvP record\n"
                f"  {c['white']}arena top{c['reset']}          — Leaderboard (top 10)\n"
                f"  {c['white']}arena rewards{c['reset']}      — Spend arena points (titles, consumables)\n"
            )
            return

        sub = args[0].lower()

        if sub == 'join':
            await cls._queue_join(player)
        elif sub == 'stats':
            await cls._show_stats(player, args[1:])
        elif sub == 'top':
            await cls._show_leaderboard(player)
        elif sub == 'leave':
            await cls._queue_leave(player)
        elif sub in ('rewards', 'shop', 'store'):
            await cls._show_rewards(player)
        elif sub == 'buy' and len(args) > 1:
            await cls._buy_reward(player, args[1].lower())
        else:
            await player.send(f"{c['yellow']}Unknown arena command. Type 'arena' for help.{c['reset']}")

    # Arena-point rewards: titles are cosmetic, consumables use stock vnums,
    # so no new prototypes are needed. Gives arena points a purpose.
    ARENA_REWARDS = {
        'duelist':   {'name': "Title: the Duelist",        'cost': 200, 'type': 'title', 'value': 'the Duelist'},
        'gladiator': {'name': "Title: the Gladiator",      'cost': 500, 'type': 'title', 'value': 'the Gladiator'},
        'champion':  {'name': "Title: Champion of the Arena", 'cost': 1200, 'type': 'title', 'value': 'Champion of the Arena'},
        'heal':      {'name': "Greater Healing Potion x3", 'cost': 60,  'type': 'item',  'value': 3134, 'qty': 3},
        'mana':      {'name': "Greater Mana Potion x3",    'cost': 60,  'type': 'item',  'value': 3135, 'qty': 3},
    }

    @classmethod
    async def _show_rewards(cls, player):
        from config import Config
        c = Config().COLORS
        pts = getattr(player, 'arena_points', 0)
        await player.send(f"\n{c['bright_cyan']}═══ Arena Quartermaster ═══{c['reset']}")
        await player.send(f"{c['yellow']}You have {pts} arena point{'s' if pts != 1 else ''}.{c['reset']}\n")
        for key, r in cls.ARENA_REWARDS.items():
            afford = c['bright_green'] if pts >= r['cost'] else c['red']
            await player.send(f"  {c['white']}{key:<10}{c['reset']} {r['name']:<32} {afford}{r['cost']} pts{c['reset']}")
        await player.send(f"\n{c['cyan']}Buy with 'arena buy <name>' (e.g. 'arena buy gladiator').{c['reset']}")

    @classmethod
    async def _buy_reward(cls, player, key):
        from config import Config
        c = Config().COLORS
        r = cls.ARENA_REWARDS.get(key)
        if not r:
            await player.send(f"{c['red']}No such reward. Type 'arena rewards' to browse.{c['reset']}")
            return
        pts = getattr(player, 'arena_points', 0)
        if pts < r['cost']:
            await player.send(f"{c['red']}You need {r['cost']} arena points ({pts}/{r['cost']}).{c['reset']}")
            return
        if r['type'] == 'title':
            titles = getattr(player, 'available_titles', None)
            if titles is None:
                titles = []; player.available_titles = titles
            if r['value'] in titles:
                await player.send(f"{c['yellow']}You already own that title.{c['reset']}")
                return
            titles.append(r['value'])
            await player.send(f"{c['bright_yellow']}Title unlocked: '{r['value']}'! Set it with 'title {r['value']}'.{c['reset']}")
        elif r['type'] == 'item':
            from objects import create_object, create_preset_object
            qty = r.get('qty', 1)
            made = 0
            for _ in range(qty):
                obj = create_object(r['value'], getattr(player, 'world', None)) or create_preset_object(r['value'])
                if obj:
                    player.inventory.append(obj); made += 1
            if not made:
                await player.send(f"{c['red']}The quartermaster's stock is out. (No charge.){c['reset']}")
                return
            await player.send(f"{c['bright_green']}You receive {r['name']}.{c['reset']}")
        player.arena_points = pts - r['cost']
        await player.send(f"{c['cyan']}Arena points remaining: {player.arena_points}.{c['reset']}")

    @classmethod
    async def _queue_join(cls, player):
        from config import Config
        c = Config().COLORS

        if not cls._is_in_lobby(player):
            await player.send(f"{c['red']}You must be in the Arena Lobby to queue.{c['reset']}")
            return

        if cls._get_match_for_player(player):
            await player.send(f"{c['red']}You are already in a match!{c['reset']}")
            return

        if player in cls.queue:
            await player.send(f"{c['yellow']}You are already in the queue. Type 'arena leave' to leave.{c['reset']}")
            return

        _ensure_arena_stats(player)
        cls.queue.append(player)
        await player.send(f"{c['bright_green']}You join the arena queue. ({len(cls.queue)} in queue){c['reset']}")

        # Try to match
        if len(cls.queue) >= 2:
            p1 = cls.queue.pop(0)
            p2 = cls.queue.pop(0)
            # Validate both still valid
            if p1.connection and p2.connection and cls._is_in_lobby(p1) and cls._is_in_lobby(p2):
                await cls._start_match(p1, p2)
            else:
                # Put valid ones back
                if p1.connection and cls._is_in_lobby(p1):
                    cls.queue.insert(0, p1)
                if p2.connection and cls._is_in_lobby(p2):
                    cls.queue.insert(0, p2)

    @classmethod
    async def _queue_leave(cls, player):
        from config import Config
        c = Config().COLORS

        if player in cls.queue:
            cls.queue.remove(player)
            await player.send(f"{c['cyan']}You leave the arena queue.{c['reset']}")
        else:
            await player.send(f"{c['yellow']}You are not in the queue.{c['reset']}")

    @classmethod
    async def _start_match(cls, p1, p2):
        """Teleport players to a random arena room and start the fight."""
        from config import Config
        c = Config().COLORS

        _ensure_arena_stats(p1)
        _ensure_arena_stats(p2)

        # Remove from queue if present
        if p1 in cls.queue:
            cls.queue.remove(p1)
        if p2 in cls.queue:
            cls.queue.remove(p2)

        # Pick random arena room
        room_vnum = random.choice(ARENA_ROOM_VNUMS)
        world = p1.world
        arena_room = world.get_room(room_vnum) if world else None

        if not arena_room:
            await p1.send(f"{c['red']}Arena error: could not find arena room.{c['reset']}")
            await p2.send(f"{c['red']}Arena error: could not find arena room.{c['reset']}")
            return

        match_id = cls._next_match_id()
        match = {
            'id': match_id,
            'player1': p1,
            'player2': p2,
            'room_vnum': room_vnum,
            'started': False,
        }
        cls.active_matches[match_id] = match

        # Tag players with match id
        p1._arena_match_id = match_id
        p2._arena_match_id = match_id

        # Teleport both players
        for p in (p1, p2):
            if p.room and p in p.room.characters:
                p.room.characters.remove(p)
            p.room = arena_room
            if p not in arena_room.characters:
                arena_room.characters.append(p)

        room_name = ARENA_ROOM_NAMES.get(room_vnum, "the Arena")

        # Announce
        announce = (
            f"{c['bright_yellow']}⚔ ARENA MATCH ⚔ {p1.name} (Rating: {p1.arena_rating}) vs "
            f"{p2.name} (Rating: {p2.arena_rating}) — {room_name}{c['reset']}"
        )
        await cls._broadcast_to_lobby(world, announce)
        await cls._broadcast_to_gallery(world, announce)

        await p1.send(f"\n{c['bright_red']}You are teleported to {room_name}!{c['reset']}")
        await p2.send(f"\n{c['bright_red']}You are teleported to {room_name}!{c['reset']}")

        # Show room
        await p1.do_look([])
        await p2.do_look([])

        # Countdown
        for i in (3, 2, 1):
            msg = f"{c['bright_yellow']}... {i} ...{c['reset']}"
            await p1.send(msg)
            await p2.send(msg)
            await cls._broadcast_to_gallery(world, msg)
            await asyncio.sleep(1)

        # Verify still valid
        if not p1.connection or not p2.connection or p1.hp <= 0 or p2.hp <= 0:
            await cls._abort_match(match_id, "A player disconnected.")
            return

        fight_msg = f"{c['bright_red']}*** FIGHT! ***{c['reset']}"
        await p1.send(fight_msg)
        await p2.send(fight_msg)
        await cls._broadcast_to_gallery(world, fight_msg)

        match['started'] = True

        # Start combat
        from combat import CombatHandler
        p1.fighting = p2
        p2.fighting = p1
        p1.position = 'fighting'
        p2.position = 'fighting'
        await CombatHandler.one_round(p1, p2)

    @classmethod
    async def _abort_match(cls, match_id: int, reason: str = ""):
        """Abort a match and return players to lobby."""
        from config import Config
        c = Config().COLORS

        match = cls.active_matches.pop(match_id, None)
        if not match:
            return

        for p in (match['player1'], match['player2']):
            if p and p.connection:
                # Stop combat
                p.fighting = None
                if p.position == 'fighting':
                    p.position = 'standing'
                await cls._teleport_to_lobby(p)
                if reason:
                    await p.send(f"{c['yellow']}Match aborted: {reason}{c['reset']}")
            if hasattr(p, '_arena_match_id'):
                del p._arena_match_id

    @classmethod
    async def _teleport_to_lobby(cls, player):
        """Teleport a player to the arena lobby."""
        world = player.world
        lobby = world.get_room(ARENA_LOBBY_VNUM) if world else None
        if not lobby:
            return

        if player.room and player in player.room.characters:
            player.room.characters.remove(player)
        player.room = lobby
        if player not in lobby.characters:
            lobby.characters.append(player)

    @classmethod
    async def handle_arena_death(cls, winner, loser) -> bool:
        """Called when a player would die in an arena match.
        Returns True if this was an arena fight (death intercepted), False otherwise.
        """
        match = cls._get_match_for_player(loser)
        if not match or not match.get('started'):
            return False

        from config import Config
        c = Config().COLORS

        match_id = match['id']
        cls.active_matches.pop(match_id, None)

        # Stop combat for both
        winner.fighting = None
        loser.fighting = None
        winner.position = 'standing'
        loser.position = 'standing'

        # Loser gets 1 HP, no death
        loser.hp = 1

        # ELO calculation
        _ensure_arena_stats(winner)
        _ensure_arena_stats(loser)

        old_w = winner.arena_rating
        old_l = loser.arena_rating
        new_w, new_l = _calc_elo(old_w, old_l)

        winner.arena_rating = new_w
        loser.arena_rating = new_l
        winner.arena_wins += 1
        loser.arena_losses += 1
        winner.arena_points = getattr(winner, 'arena_points', 0) + ARENA_POINTS_REWARD
        winner.gold += ARENA_GOLD_REWARD

        if new_w > winner.arena_highest_rating:
            winner.arena_highest_rating = new_w

        w_delta = new_w - old_w
        l_delta = new_l - old_l
        world = winner.world

        # Result messages
        result_msg = (
            f"\n{c['bright_yellow']}═══════════════════════════════════════{c['reset']}\n"
            f"{c['bright_green']}  ⚔ {winner.name} WINS! ⚔{c['reset']}\n"
            f"{c['white']}  {winner.name}: {old_w} → {new_w} ({'+' if w_delta >= 0 else ''}{w_delta}){c['reset']}\n"
            f"{c['white']}  {loser.name}: {old_l} → {new_l} ({'+' if l_delta >= 0 else ''}{l_delta}){c['reset']}\n"
            f"{c['yellow']}  Reward: {ARENA_GOLD_REWARD} gold, {ARENA_POINTS_REWARD} arena points{c['reset']}\n"
            f"{c['bright_yellow']}═══════════════════════════════════════{c['reset']}\n"
        )

        await winner.send(result_msg)
        await loser.send(result_msg)
        await cls._broadcast_to_gallery(world, result_msg)
        await cls._broadcast_to_lobby(world, result_msg)

        # Teleport both back to lobby
        await cls._teleport_to_lobby(winner)
        await cls._teleport_to_lobby(loser)
        await winner.do_look([])
        await loser.do_look([])

        # Clean up tags
        for p in (winner, loser):
            if hasattr(p, '_arena_match_id'):
                del p._arena_match_id

        return True

    @classmethod
    async def _show_stats(cls, player, args: list):
        from config import Config
        c = Config().COLORS

        _ensure_arena_stats(player)

        total = player.arena_wins + player.arena_losses
        winrate = f"{(player.arena_wins / total * 100):.1f}%" if total > 0 else "N/A"

        await player.send(
            f"\n{c['bright_cyan']}═══ Arena Stats: {player.name} ═══{c['reset']}\n"
            f"  {c['white']}Rating:{c['reset']}          {c['bright_yellow']}{player.arena_rating}{c['reset']}\n"
            f"  {c['white']}Highest Rating:{c['reset']} {player.arena_highest_rating}\n"
            f"  {c['white']}Wins:{c['reset']}            {c['green']}{player.arena_wins}{c['reset']}\n"
            f"  {c['white']}Losses:{c['reset']}          {c['red']}{player.arena_losses}{c['reset']}\n"
            f"  {c['white']}Win Rate:{c['reset']}        {winrate}\n"
            f"  {c['white']}Arena Points:{c['reset']}    {getattr(player, 'arena_points', 0)}\n"
            f"  {c['white']}Total Matches:{c['reset']}   {total}\n"
        )

    @classmethod
    async def _show_leaderboard(cls, player):
        from config import Config
        import os, json
        c = Config().COLORS

        # Scan all player files for arena stats
        entries = []
        player_dir = Config.PLAYER_DIR
        if os.path.isdir(player_dir):
            for fname in os.listdir(player_dir):
                if fname.endswith('.json'):
                    try:
                        with open(os.path.join(player_dir, fname)) as f:
                            data = json.load(f)
                        wins = data.get('arena_wins', 0)
                        losses = data.get('arena_losses', 0)
                        rating = data.get('arena_rating', ELO_START)
                        if wins + losses > 0:
                            entries.append({
                                'name': data.get('name', fname[:-5]),
                                'rating': rating,
                                'wins': wins,
                                'losses': losses,
                            })
                    except Exception:
                        pass

        # Also include online players with arena stats
        if player.world:
            online = getattr(player.world, 'players', None) or {}
            for p in (online.values() if isinstance(online, dict) else online):   # (a dict: name -> player)
                _ensure_arena_stats(p)
                if p.arena_wins + p.arena_losses > 0:
                    # Update or add
                    found = False
                    for e in entries:
                        if e['name'].lower() == p.name.lower():
                            e['rating'] = p.arena_rating
                            e['wins'] = p.arena_wins
                            e['losses'] = p.arena_losses
                            found = True
                            break
                    if not found:
                        entries.append({
                            'name': p.name,
                            'rating': p.arena_rating,
                            'wins': p.arena_wins,
                            'losses': p.arena_losses,
                        })

        entries.sort(key=lambda e: e['rating'], reverse=True)
        top10 = entries[:10]

        if not top10:
            await player.send(f"{c['yellow']}No arena matches have been fought yet.{c['reset']}")
            return

        header = (
            f"\n{c['bright_yellow']}═══ Arena Leaderboard (Top 10) ═══{c['reset']}\n"
            f"  {c['cyan']}{'#':>2}  {'Name':<16} {'Rating':>6}  {'W':>4} / {'L':<4}  {'Win%':>5}{c['reset']}\n"
            f"  {c['cyan']}{'─' * 48}{c['reset']}"
        )
        await player.send(header)

        for i, e in enumerate(top10, 1):
            total = e['wins'] + e['losses']
            wr = f"{e['wins']/total*100:.0f}%" if total > 0 else "N/A"
            rank_color = c['bright_yellow'] if i <= 3 else c['white']
            await player.send(
                f"  {rank_color}{i:>2}  {e['name']:<16} {e['rating']:>6}  "
                f"{c['green']}{e['wins']:>4}{c['white']} / {c['red']}{e['losses']:<4}{c['reset']}  {wr:>5}"
            )

        await player.send("")

    @classmethod
    async def handle_arena_combat_message(cls, attacker, defender, message: str):
        """Broadcast combat messages to the spectator gallery."""
        match = cls._get_match_for_player(attacker)
        if not match or not match.get('started'):
            return
        world = attacker.world
        if world:
            await cls._broadcast_to_gallery(world, message)

    @classmethod
    def is_in_arena_match(cls, player) -> bool:
        """Check if a player is currently in an arena match."""
        return cls._get_match_for_player(player) is not None

    @classmethod
    def cleanup_player(cls, player):
        """Clean up when a player logs out."""
        if player in cls.queue:
            cls.queue.remove(player)
        # Remove pending challenges
        cls.pending_challenges.pop(player.name.lower(), None)
        to_remove = [k for k, v in cls.pending_challenges.items() if v['challenger'] == player]
        for k in to_remove:
            del cls.pending_challenges[k]
