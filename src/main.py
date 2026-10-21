#!/usr/bin/env python3
"""
Misthollow - A Fantasy CircleMUD-style Multi-User Dungeon
=========================================================
A complete fantasy MUD with character classes, combat, magic, quests, and more.
"""

import asyncio
import signal
import sys
import os
import logging
import logging.handlers
from datetime import datetime

# Add src to path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from server import MUDServer
from world import World
from config import Config
from web_map import WebMapServer

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        # 10 MB a file, the last five kept (mud.log.1 ... mud.log.5): a busy week no longer
        # grows one file without end
        logging.handlers.RotatingFileHandler('../log/mud.log', maxBytes=10 * 1024 * 1024, backupCount=5),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger('Misthollow')

class Misthollow:
    """Main MUD application class."""
    
    def __init__(self):
        self.config = Config()
        self.world = None
        self.server = None
        self.web_map = None
        self.web_client = None
        self.admin_dashboard = None
        self.running = False
        self.start_time = None
        
    async def initialize(self):
        """Initialize the MUD world and systems."""
        logger.info("=" * 60)
        logger.info("Misthollow - Fantasy Multi-User Dungeon")
        logger.info("=" * 60)
        logger.info("Initializing game systems...")
        
        # Load the world
        self.world = World(self.config)
        await self.world.load()

        # Combat v2: structured events for the 3D client and distance rules (combat_hooks.py)
        try:
            import combat_hooks
            combat_hooks.install()
        except Exception as e:
            logger.error(f"combat hooks not installed: {e}")
        # Mob brains: the immortal "brain" and "brainstat" commands (brain/, docs/MOB_AI.md)
        try:
            import brain
            brain.install()
        except Exception as e:
            logger.error(f"mob brains not installed: {e}")
        # The marquee abilities (one per class, earned through a quest): their commands must
        # exist before mastery.install() wraps every class ability
        try:
            import marquee_abilities
            marquee_abilities.install()
        except Exception as e:
            logger.error(f"marquee abilities not installed: {e}")
        # Learn by doing: abilities unlock by level and grow with use (mastery.py)
        try:
            import mastery
            mastery.install()
        except Exception as e:
            logger.error(f"mastery rules not installed: {e}")
        # The marquee quests: one per class, offered by its guildmaster from level 45 (marquee.py)
        try:
            import marquee
            marquee.install(self.world)
        except Exception as e:
            logger.error(f"marquee quests not installed: {e}")
        
        # Create the server
        self.server = MUDServer(self.world, self.config)

        # Start web map server
        self.web_map = WebMapServer(self.world, self.config)
        try:
            await self.web_map.start()
        except OSError as e:
            logger.warning(f"Web map server failed to start: {e} — continuing without web map")
            self.web_map = None
        # Expose for map updates
        self.world.web_map = self.web_map

        # Start admin dashboard
        try:
            from admin_dashboard import AdminDashboard
            self.admin_dashboard = AdminDashboard(self.world, port=self.config.ADMIN_DASHBOARD_PORT,
                                                  host=self.config.ADMIN_DASHBOARD_HOST)
            await self.admin_dashboard.start()
        except Exception as e:
            logger.warning(f"Admin dashboard failed to start: {e}")

        # Start web client
        try:
            from web_client import WebClient
            self.web_client = WebClient(mud_port=self.config.PORT, web_port=4003)
            await self.web_client.start()
        except Exception as e:
            logger.warning(f"Web client failed to start: {e}")

        logger.info("Initialization complete!")
        
    async def run(self):
        """Main game loop."""
        self.running = True
        self.start_time = datetime.now()
        
        logger.info(f"Starting server on port {self.config.PORT}...")
        
        # Start the server
        await self.server.start()
        
        # Main game tick loop
        tick_rate = 1.0 / self.config.TICKS_PER_SECOND
        combat_tick = 0
        move_tick = 0
        regen_tick = 0
        minor_regen_tick = 0
        affect_tick = 0
        poison_tick = 0
        zone_tick = 0
        autosave_tick = 0
        time_tick = 0
        weather_tick = 0
        pet_tick = 0
        ambient_tick = 0
        decay_tick = 0
        world_event_tick = 0

        try:
            while self.running:
                tick_start = asyncio.get_event_loop().time()

                # Process game ticks
                combat_tick += 1
                regen_tick += 1
                minor_regen_tick += 1
                affect_tick += 1
                poison_tick += 1
                zone_tick += 1
                autosave_tick += 1
                time_tick += 1
                weather_tick += 1
                pet_tick += 1
                ambient_tick += 1
                decay_tick += 1

                # Time tick (every 1 second - virtual game time)
                if time_tick >= self.config.TICKS_PER_SECOND:
                    await self.world.time_tick()
                    time_tick = 0

                # Weather tick (every 5 minutes)
                if weather_tick >= self.config.TICKS_PER_SECOND * 300:
                    await self.world.weather_tick()
                    weather_tick = 0

                # Pet tick (every 10 seconds)
                if pet_tick >= self.config.TICKS_PER_SECOND * 10:
                    await self.world.pet_tick()
                    pet_tick = 0

                # Decay tick (every 6 seconds - corpses and ground items)
                if decay_tick >= self.config.TICKS_PER_SECOND * 6:
                    await self.world.decay_tick()
                    decay_tick = 0

                # Creatures in fights move (combat v2: melee closes in, archers keep away)
                move_tick += 1
                if move_tick >= 2:
                    move_tick = 0
                    try:
                        from combat_range import move_tick as _combat_move
                        _combat_move(self.world, 0.2)
                    except Exception as e:
                        logger.debug(f"combat move tick failed: {e}")
                    # real-time combat for the 3D client's action mode (action_combat.py)
                    try:
                        import action_combat
                        await action_combat.tick(self.world)
                    except Exception as e:
                        logger.debug(f"action combat tick failed: {e}")

                # Combat tick (every COMBAT_ROUND_SECONDS; creatures act a beat later)
                if combat_tick >= int(self.config.TICKS_PER_SECOND * self.config.COMBAT_ROUND_SECONDS):
                    await self.world.combat_tick()
                    combat_tick = 0

                # Affect tick (DOT/HOT effects)
                if affect_tick >= self.config.TICKS_PER_SECOND * self.config.AFFECT_TICK_SECONDS:
                    await self.world.affect_tick()
                    affect_tick = 0

                # Poison tick (faster feedback)
                if poison_tick >= int(self.config.TICKS_PER_SECOND * self.config.POISON_TICK_SECONDS):
                    await self.world.poison_tick()
                    poison_tick = 0

                # Regen tick every 60 seconds (CircleMUD standard)
                if regen_tick >= self.config.TICKS_PER_SECOND * 60:
                    await self.world.regen_tick()
                    regen_tick = 0

                # Regen tick warning (3 seconds before)
                if regen_tick == self.config.TICKS_PER_SECOND * 57:
                    c = self.config.COLORS
                    for p in self.world.players.values():
                        if getattr(p, 'show_ticks', False):
                            await p.send(f"{c['cyan']}[TICK in 3s]{c['reset']}")

                # Minor regen tick every 5 seconds
                if minor_regen_tick >= self.config.TICKS_PER_SECOND * 5:
                    await self.world.minor_regen_tick()
                    minor_regen_tick = 0
                
                # Ambient murmurs (every 10 seconds; ambient.py rate-limits each player)
                if ambient_tick >= self.config.TICKS_PER_SECOND * 10:
                    from ambient import AmbientManager
                    await AmbientManager.ambient_tick(self.world)
                    # (one system: ambient.py picks lines that fit the place, ambient_lines.py)
                    ambient_tick = 0
                
                # NPC schedule tick (every game hour change - handled in time_tick)
                # Schedule processing happens when hour changes in world.time_tick()
                
                # Zone reset tick (every 15 minutes)
                if zone_tick >= self.config.TICKS_PER_SECOND * 900:
                    await self.world.zone_reset_tick()
                    zone_tick = 0

                # World event tick (every 30 seconds)
                world_event_tick += 1
                if world_event_tick >= self.config.TICKS_PER_SECOND * 30:
                    if self.world.event_manager:
                        try:
                            await self.world.event_manager.tick()
                        except asyncio.CancelledError:
                            logger.error("World event tick cancelled (swallowed)")
                        except Exception as e:
                            logger.error(f"World event tick error: {e}")
                    world_event_tick = 0
                
                # Auction house expiration tick (every 5 minutes)
                if autosave_tick == self.config.TICKS_PER_SECOND * 150:
                    try:
                        from auction_house import AuctionHouse
                        AuctionHouse.process_expirations()
                    except Exception as e:
                        logger.error(f"Auction expiration tick error: {e}")

                # Autosave tick (every 5 minutes)
                if autosave_tick >= self.config.TICKS_PER_SECOND * 300:
                    await self.world.autosave()
                    autosave_tick = 0
                
                # Process player input and NPC AI
                await self.server.process_input()
                await self.world.process_npcs()
                
                # Maintain tick rate
                elapsed = asyncio.get_event_loop().time() - tick_start
                if elapsed < tick_rate:
                    await asyncio.sleep(tick_rate - elapsed)
                    
        except asyncio.CancelledError:
            logger.info("Shutdown requested...")
        finally:
            await self.shutdown()
            
    async def shutdown(self):
        """Gracefully shut down the MUD."""
        logger.info("Shutting down Misthollow...")
        self.running = False
        
        if self.world:
            await self.world.save_all()
            
        if self.server:
            await self.server.shutdown()

        if self.web_map:
            await self.web_map.stop()

        if hasattr(self, 'web_client') and self.web_client:
            await self.web_client.stop()
            
        logger.info("Shutdown complete. Farewell!")

async def main():
    """Entry point."""
    mud = Misthollow()
    
    # Handle shutdown signals (Unix only - Windows uses KeyboardInterrupt)
    if sys.platform != 'win32':
        loop = asyncio.get_event_loop()
        for sig in (signal.SIGTERM, signal.SIGINT):
            loop.add_signal_handler(sig, lambda: asyncio.create_task(mud.shutdown()))
    
    try:
        await mud.initialize()
        await mud.run()
    except KeyboardInterrupt:
        logger.info("Keyboard interrupt received...")
        await mud.shutdown()
    except Exception as e:
        logger.error(f"Fatal error: {e}", exc_info=True)
        sys.exit(1)

if __name__ == '__main__':
    print("""
    ===============================================================

      ___  ________ _____ _____ _   _ _____ _      _     _____  _    _
     |  \\/  |_   _/  ___|_   _| | | |  _  | |    | |   |  _  || |  | |
     | .  . | | | \\ `--.  | | | |_| | | | | |    | |   | | | || |  | |
     | |\\/| | | |  `--. \\ | | |  _  | | | | |    | |   | | | || |/\\| |
     | |  | |_| |_/\\__/ / | | | | | \\ \\_/ / |____| |___\\ \\_/ /\\  /\\  /
     \\_|  |_/\\___/\\____/  \\_/ \\_| |_/\\___/\\_____/\\_____/\\___/  \\/  \\/

           A World of Shadow and Mystery

    ===============================================================
    """)
    asyncio.run(main())
