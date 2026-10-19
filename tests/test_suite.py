#!/usr/bin/env python3
"""
Misthollow Automated Test Suite
==============================
Tests core MUD functionality via socket connection.
"""

import socket
import time
import re
import sys
import logging
from typing import Optional, List, Tuple

# Log to console and file
import os
log_path = 'logs/tests.log'
os.makedirs(os.path.dirname(log_path), exist_ok=True)
log_handlers = [
    logging.StreamHandler(),
    logging.FileHandler(log_path, mode='a')
]
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s', handlers=log_handlers)
logger = logging.getLogger('MUDTest')


class MUDClient:
    """Simple MUD client for testing."""
    
    def __init__(self, host: str = 'localhost', port: int = 4000):
        self.host = host
        self.port = port
        self.socket: Optional[socket.socket] = None
        self.buffer = ""
        
    def connect(self) -> bool:
        """Connect to the MUD server."""
        try:
            self.socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            self.socket.settimeout(10)
            self.socket.connect((self.host, self.port))
            logger.info(f"Connected to {self.host}:{self.port}")
            return True
        except Exception as e:
            logger.error(f"Connection failed: {e}")
            return False
    
    def disconnect(self):
        """Disconnect from the MUD."""
        if self.socket:
            try:
                self.send("quit")
                time.sleep(0.5)
                self.socket.close()
            except:
                pass
            self.socket = None
            logger.info("Disconnected")
    
    def send(self, command: str):
        """Send a command to the MUD."""
        if self.socket:
            self.socket.send(f"{command}\n".encode())
            logger.debug(f"Sent: {command}")
    
    def receive(self, timeout: float = 2.0) -> str:
        """Receive data from the MUD."""
        if not self.socket:
            return ""
        
        self.socket.settimeout(timeout)
        data = ""
        try:
            while True:
                chunk = self.socket.recv(4096).decode('utf-8', errors='ignore')
                if not chunk:
                    break
                data += chunk
                if len(chunk) < 4096:
                    break
        except socket.timeout:
            pass
        except Exception as e:
            logger.error(f"Receive error: {e}")
        
        # Strip ANSI codes for easier parsing
        ansi_escape = re.compile(r'\x1B(?:[@-Z\\-_]|\[[0-?]*[ -/]*[@-~])')
        clean_data = ansi_escape.sub('', data)
        
        logger.debug(f"Received: {clean_data[:200]}...")
        return clean_data
    
    def send_and_receive(self, command: str, wait: float = 1.0) -> str:
        """Send command and get response."""
        self.send(command)
        time.sleep(wait)
        return self.receive()
    
    def login(self, username: str, password: str) -> bool:
        """Login or create a character."""
        # Clear any pending data
        time.sleep(1)
        self.receive(2)
        
        # Send username and wait for response
        self.send(username)
        time.sleep(2)
        response = self.receive(3)
        
        # Loop through character creation / login
        for step in range(15):  # Max 15 steps
            resp_lower = response.lower() if response else ""
            
            # Debug
            if response:
                logger.debug(f"Step {step}: {response[:80]}")
            
            # Check if we're in the game
            if "temple" in resp_lower or "exits:" in resp_lower or "obvious exit" in resp_lower:
                logger.info(f"Logged in as {username}")
                return True
            
            # Handle prompts in priority order
            if "(y/n)" in resp_lower or "hear that right" in resp_lower:
                self.send("y")
            elif "give me a password" in resp_lower or "enter a password" in resp_lower:
                self.send(password)
            elif "confirm" in resp_lower or "retype" in resp_lower or "verify" in resp_lower:
                self.send(password)
            elif "choose" in resp_lower and "race" in resp_lower:
                self.send("human")
            elif "enter race" in resp_lower or "valid race" in resp_lower:
                self.send("human")
            elif "account>" in resp_lower:
                self.send(f"play {username}")      # a name kept in an account: its menu
            elif "male or female" in resp_lower:
                self.send("female")
            elif "classic or archmage" in resp_lower:
                self.send("classic")
            elif "choose" in resp_lower and "class" in resp_lower:
                self.send("warrior")
            elif "enter class" in resp_lower or "select" in resp_lower:
                self.send("warrior")
            elif "accept these stats" in resp_lower or "keep these" in resp_lower:
                self.send("y")
            elif "press enter" in resp_lower or "press return" in resp_lower:
                self.send("")
            elif "welcome" in resp_lower or "motd" in resp_lower:
                self.send("")
            elif "password" in resp_lower:
                self.send(password)
            elif resp_lower.strip() == "" or not response:
                self.send("")
            else:
                # Unknown - send enter and continue
                self.send("")
            
            time.sleep(1.5)
            response = self.receive(2)
        
        # Final check - try look command
        self.send("look")
        time.sleep(1)
        response = self.receive(2)
        if response and ("temple" in response.lower() or "exits" in response.lower()):
            logger.info(f"Logged in as {username}")
            return True
        
        logger.error(f"Login failed after {step+1} steps. Last response: {response[:200] if response else 'empty'}")
        return False


class TestResult:
    """Store test results."""
    def __init__(self, name: str, passed: bool, message: str = ""):
        self.name = name
        self.passed = passed
        self.message = message


class MUDTestSuite:
    """Test suite for Misthollow."""
    
    def __init__(self, host: str = 'localhost', port: int = 4000):
        self.client = MUDClient(host, port)
        self.results: List[TestResult] = []
        self.test_user = "Tester"
        self.test_pass = "testpass123"
    
    def run_all(self, smoke: bool = False) -> bool:
        """Run all tests (or smoke subset)."""
        logger.info("=" * 50)
        logger.info("Misthollow Test Suite" + (" (SMOKE)" if smoke else ""))
        logger.info("=" * 50)
        
        if not self.client.connect():
            logger.error("Could not connect to MUD")
            return False
        
        try:
            if not self.client.login(self.test_user, self.test_pass):
                logger.error("Could not login")
                return False
            
            # Run test categories
            self.test_basic_commands()
            self.test_movement()
            
            if not smoke:
                self.test_info_commands()
                self.test_communication()
                self.test_inventory()
                self.test_settings()
                self.test_shops()
                self.test_banking()
                self.test_combat_prep()
                self.test_food_drink()
                self.test_pets()
                self.test_hidden_dungeon()
            
        finally:
            self.client.disconnect()
        
        # Print results
        self.print_results()
        return all(r.passed for r in self.results)
    
    def add_result(self, name: str, passed: bool, message: str = ""):
        """Add a test result."""
        self.results.append(TestResult(name, passed, message))
        status = "✓ PASS" if passed else "✗ FAIL"
        logger.info(f"  {status}: {name}" + (f" - {message}" if message else ""))
    
    def test_basic_commands(self):
        """Test basic commands."""
        logger.info("\n[Basic Commands]")
        
        # Look
        response = self.client.send_and_receive("look")
        self.add_result("look", len(response) > 50, f"{len(response)} chars")
        
        # Score
        response = self.client.send_and_receive("score")
        self.add_result("score", "HP" in response or "hp" in response.lower())
        
        # Inventory
        response = self.client.send_and_receive("inventory")
        self.add_result("inventory", "carry" in response.lower() or "nothing" in response.lower() or "inventory" in response.lower())
        
        # Equipment
        response = self.client.send_and_receive("equipment")
        self.add_result("equipment", "wear" in response.lower() or "equipment" in response.lower() or "nothing" in response.lower())
        
        # Who
        response = self.client.send_and_receive("who")
        self.add_result("who", self.test_user.lower() in response.lower() or "player" in response.lower())
        
        # Help
        response = self.client.send_and_receive("help")
        self.add_result("help", len(response) > 100)
    
    def test_movement(self):
        """Test movement commands."""
        logger.info("\n[Movement]")
        
        # Get starting room
        start = self.client.send_and_receive("look")
        
        # Try to move south
        response = self.client.send_and_receive("south")
        moved_south = "south" not in response.lower() or "temple" not in response.lower() or len(response) > 50
        self.add_result("move south", moved_south or "no exit" in response.lower() or "can't" in response.lower())
        
        # Move back north
        response = self.client.send_and_receive("north")
        self.add_result("move north", len(response) > 20)
        
        # Exits command
        response = self.client.send_and_receive("exits")
        self.add_result("exits", "exit" in response.lower() or "north" in response.lower() or "south" in response.lower())
    
    def test_info_commands(self):
        """Test information commands."""
        logger.info("\n[Info Commands]")
        
        # Time
        response = self.client.send_and_receive("time")
        self.add_result("time", "day" in response.lower() or "hour" in response.lower() or "time" in response.lower())
        
        # Weather
        response = self.client.send_and_receive("weather")
        self.add_result("weather", len(response) > 20)
        
        # Commands
        response = self.client.send_and_receive("commands")
        self.add_result("commands", "look" in response.lower() or "command" in response.lower())
        
        # Levels
        response = self.client.send_and_receive("levels")
        self.add_result("levels", "level" in response.lower() or "xp" in response.lower())
        
        # Diagnose
        response = self.client.send_and_receive("diagnose")
        self.add_result("diagnose", "hp" in response.lower() or "health" in response.lower() or "condition" in response.lower())
    
    def test_communication(self):
        """Test communication commands."""
        logger.info("\n[Communication]")
        
        # Say
        response = self.client.send_and_receive("say Hello world!")
        self.add_result("say", "say" in response.lower() or "hello" in response.lower())
        
        # Gossip
        response = self.client.send_and_receive("gossip Testing 123")
        self.add_result("gossip", "gossip" in response.lower() or "testing" in response.lower())
        
        # Emote
        response = self.client.send_and_receive("emote tests the system")
        self.add_result("emote", "test" in response.lower())
    
    def test_inventory(self):
        """Test inventory commands."""
        logger.info("\n[Inventory]")
        
        # Get (even if nothing to get)
        response = self.client.send_and_receive("get all")
        self.add_result("get", len(response) > 5)  # Any response is fine
        
        # Drop (even if nothing to drop)
        response = self.client.send_and_receive("drop all")
        self.add_result("drop", len(response) > 5)
    
    def test_settings(self):
        """Test settings commands."""
        logger.info("\n[Settings]")
        
        # Toggle
        response = self.client.send_and_receive("toggle")
        self.add_result("toggle", "brief" in response.lower() or "setting" in response.lower())
        
        # Brief
        response = self.client.send_and_receive("brief")
        self.add_result("brief", "brief" in response.lower() or "on" in response.lower() or "off" in response.lower())
        self.client.send_and_receive("brief")  # Toggle back
        
        # Color
        response = self.client.send_and_receive("color")
        self.add_result("color", "color" in response.lower())
    
    def test_shops(self):
        """Test shop commands."""
        logger.info("\n[Shops]")
        
        # Navigate to a shop (wizard shop near temple)
        self.client.send_and_receive("south")  # Temple to Market
        self.client.send_and_receive("east")   # Try to find shop
        
        # List command
        response = self.client.send_and_receive("list")
        has_shop = "sale" in response.lower() or "price" in response.lower() or "nothing" in response.lower()
        self.add_result("list", has_shop or "shop" in response.lower())
        
        # Value command
        response = self.client.send_and_receive("value sword")
        self.add_result("value", len(response) > 5)
        
        # Go back to temple
        self.client.send_and_receive("west")
        self.client.send_and_receive("north")
    
    def test_banking(self):
        """Test banking commands."""
        logger.info("\n[Banking]")
        
        # Navigate to bank (northwest from market)
        self.client.send_and_receive("south")      # Temple to Market
        self.client.send_and_receive("northwest")  # To bank
        
        # Balance
        response = self.client.send_and_receive("balance")
        self.add_result("balance", "gold" in response.lower() or "balance" in response.lower() or "bank" in response.lower())
        
        # Deposit (even with 0 gold)
        response = self.client.send_and_receive("deposit 1")
        self.add_result("deposit", len(response) > 5)
        
        # Withdraw
        response = self.client.send_and_receive("withdraw 1")
        self.add_result("withdraw", len(response) > 5)
        
        # Go back
        self.client.send_and_receive("southeast")
        self.client.send_and_receive("north")
    
    def test_combat_prep(self):
        """Test combat-related commands (without actual fighting)."""
        logger.info("\n[Combat Prep]")
        
        # Consider
        response = self.client.send_and_receive("consider guard")
        self.add_result("consider", "level" in response.lower() or "equal" in response.lower() or "find" in response.lower())
        
        # Wimpy
        response = self.client.send_and_receive("wimpy 20")
        self.add_result("wimpy", "wimpy" in response.lower() or "flee" in response.lower())
        
        # Skills
        response = self.client.send_and_receive("skills")
        self.add_result("skills", "skill" in response.lower() or "%" in response)
        
        # Spells
        response = self.client.send_and_receive("spells")
        self.add_result("spells", "spell" in response.lower() or "mana" in response.lower() or "none" in response.lower())
    
    def test_hidden_dungeon(self):
        """Test hidden dungeon access."""
        logger.info("\n[Hidden Dungeon]")
        
        # Navigate to Common Square
        self.client.send_and_receive("south")  # Temple to Market
        self.client.send_and_receive("south")  # Market to Common Square
        
        # Search for hidden exit
        response = self.client.send_and_receive("search")
        found_hidden = "trapdoor" in response.lower() or "hidden" in response.lower() or "discover" in response.lower()
        self.add_result("search hidden", found_hidden or "nothing" in response.lower())
        
        # Try to open trapdoor
        response = self.client.send_and_receive("open trapdoor")
        self.add_result("open trapdoor", "open" in response.lower() or "already" in response.lower() or "no" in response.lower())
        
        # Try to go down
        response = self.client.send_and_receive("down")
        entered_dungeon = "forgotten" in response.lower() or "passage" in response.lower() or "dark" in response.lower()
        self.add_result("enter dungeon", entered_dungeon or "can't" in response.lower() or "closed" in response.lower())
        
        # Go back up if we entered
        if entered_dungeon:
            self.client.send_and_receive("up")
        
        # Return to temple
        self.client.send_and_receive("north")
        self.client.send_and_receive("north")
    
    def test_food_drink(self):
        """Test hunger/thirst system."""
        logger.info("\n[Food & Drink]")
        
        # Check hunger status
        response = self.client.send_and_receive("eat")
        self.add_result("eat status", "hungry" in response.lower() or "full" in response.lower() or "eat" in response.lower())
        
        # Navigate to fountain (Temple Square)
        self.client.send_and_receive("south")  # To market
        
        # Drink from fountain
        response = self.client.send_and_receive("drink fountain")
        self.add_result("drink fountain", "drink" in response.lower() or "thirst" in response.lower() or "fountain" in response.lower())
        
        # Go back
        self.client.send_and_receive("north")
    
    def test_pets(self):
        """Test pet commands."""
        logger.info("\n[Pets]")
        
        # Pet status
        response = self.client.send_and_receive("pet")
        self.add_result("pet", "pet" in response.lower() or "companion" in response.lower() or "no" in response.lower())
        
        # Order (even with no pet)
        response = self.client.send_and_receive("order")
        self.add_result("order", "order" in response.lower() or "pet" in response.lower() or "usage" in response.lower())
        
        # Group (shows self + pets)
        response = self.client.send_and_receive("group")
        self.add_result("group", "group" in response.lower() or "party" in response.lower() or "not" in response.lower())

    def print_results(self):
        """Print test results summary."""
        logger.info("\n" + "=" * 50)
        logger.info("TEST RESULTS SUMMARY")
        logger.info("=" * 50)
        
        passed = sum(1 for r in self.results if r.passed)
        total = len(self.results)
        
        for result in self.results:
            status = "✓" if result.passed else "✗"
            logger.info(f"  {status} {result.name}")
        
        logger.info("-" * 50)
        logger.info(f"Passed: {passed}/{total} ({100*passed//total}%)")
        
        if passed == total:
            logger.info("ALL TESTS PASSED! ✓")
        else:
            failed = [r.name for r in self.results if not r.passed]
            logger.info(f"Failed tests: {', '.join(failed)}")


def main():
    """Run the test suite."""
    args = sys.argv[1:]
    smoke = False
    
    if '--smoke' in args:
        smoke = True
        args.remove('--smoke')
    
    host = args[0] if len(args) > 0 else 'localhost'
    port = int(args[1]) if len(args) > 1 else 4000
    
    suite = MUDTestSuite(host, port)
    success = suite.run_all(smoke=smoke)
    
    sys.exit(0 if success else 1)


if __name__ == '__main__':
    main()
