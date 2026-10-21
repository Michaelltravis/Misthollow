"""
Time System

Provides virtual game time independent of real-world time, with day/night cycles,
seasons, and time-of-day effects.
"""

import logging
from typing import Dict, Tuple

logger = logging.getLogger(__name__)


class GameTime:
    """
    Manages the virtual game time progression.

    Game time advances independently of real time. The default rate is:
    2 minutes real time = 1 MUD hour (configurable)

    This means 48 minutes real time = 1 MUD day
    """

    # Time constants
    SECONDS_PER_MUD_HOUR = 120  # 2 minutes real = 1 MUD hour
    HOURS_PER_DAY = 24
    DAYS_PER_MONTH = 30
    MONTHS_PER_YEAR = 12

    # Time period definitions (hour ranges)
    TIME_PERIODS = {
        'night': (0, 5),       # Midnight to 5am
        'dawn': (5, 7),        # 5am to 7am
        'morning': (7, 12),    # 7am to noon
        'afternoon': (12, 18), # Noon to 6pm
        'dusk': (18, 20),      # 6pm to 8pm
        'evening': (20, 24)    # 8pm to midnight
    }

    # Season definitions (by month)
    SEASONS = ['Winter', 'Winter', 'Spring', 'Spring', 'Spring', 'Summer',
               'Summer', 'Summer', 'Autumn', 'Autumn', 'Autumn', 'Winter']

    # Month names
    MONTH_NAMES = ['Deep Winter', 'Late Winter', 'Early Spring', 'Mid Spring',
                  'Late Spring', 'Early Summer', 'Midsummer', 'Late Summer',
                  'Early Autumn', 'Mid Autumn', 'Late Autumn', 'Early Winter']

    def __init__(self, start_hour: int = 12, start_day: int = 1,
                 start_month: int = 6, start_year: int = 1000):
        """
        Initialize the game time system.

        Args:
            start_hour: Starting hour (0-23)
            start_day: Starting day (1-30)
            start_month: Starting month (1-12)
            start_year: Starting year
        """
        self.hour = start_hour
        self.day = start_day
        self.month = start_month
        self.year = start_year
        self.tick_counter = 0  # Counts seconds until next hour

        logger.info(f"Game time initialized: {self.get_time_string()}")

    def advance_tick(self, seconds: int = 1):
        """
        Advance game time by the specified number of real-world seconds.

        Args:
            seconds: Number of real-world seconds elapsed
        """
        self.tick_counter += seconds

        # Check if enough time has passed for a MUD hour
        if self.tick_counter >= self.SECONDS_PER_MUD_HOUR:
            hours_to_advance = self.tick_counter // self.SECONDS_PER_MUD_HOUR
            self.tick_counter %= self.SECONDS_PER_MUD_HOUR

            for _ in range(hours_to_advance):
                self._advance_hour()

    def _advance_hour(self):
        """Advance game time by one hour."""
        self.hour += 1

        if self.hour >= self.HOURS_PER_DAY:
            self.hour = 0
            self._advance_day()

    def _advance_day(self):
        """Advance game time by one day."""
        self.day += 1

        if self.day > self.DAYS_PER_MONTH:
            self.day = 1
            self._advance_month()

    def _advance_month(self):
        """Advance game time by one month."""
        self.month += 1

        if self.month > self.MONTHS_PER_YEAR:
            self.month = 1
            self.year += 1
            logger.info(f"New year! Welcome to year {self.year}")

    def is_day(self) -> bool:
        """
        Check if it's currently daytime.

        Returns:
            True if daytime (7am-8pm), False otherwise
        """
        return 7 <= self.hour < 20

    def is_night(self) -> bool:
        """
        Check if it's currently nighttime.

        Returns:
            True if nighttime (8pm-7am), False otherwise
        """
        return not self.is_day()

    def get_period(self) -> str:
        """
        Get the current time period name.

        Returns:
            Period name ('night', 'dawn', 'morning', 'afternoon', 'dusk', 'evening')
        """
        for period_name, (start, end) in self.TIME_PERIODS.items():
            if start <= self.hour < end:
                return period_name
        return 'night'  # Default fallback

    def get_season(self) -> str:
        """
        Get the current season.

        Returns:
            Season name ('Spring', 'Summer', 'Autumn', 'Winter')
        """
        return self.SEASONS[self.month - 1]

    def get_month_name(self) -> str:
        """
        Get the current month name.

        Returns:
            Month name
        """
        return self.MONTH_NAMES[self.month - 1]

    def total_hours(self) -> int:
        """Game hours since the calendar's start (counts on across a month and a year)."""
        days = ((self.year * self.MONTHS_PER_YEAR) + (self.month - 1)) * self.DAYS_PER_MONTH + (self.day - 1)
        return days * self.HOURS_PER_DAY + self.hour

    def moon_phase(self) -> float:
        """Where the moon is in its 28-day round: 0 new, 0.5 full."""
        return round((self.total_hours() / self.HOURS_PER_DAY % 28) / 28, 3)

    def get_light_level(self) -> float:
        """
        Get the current ambient light level (0.0 to 1.0).

        Returns:
            Light level from 0.0 (complete darkness) to 1.0 (full daylight)
        """
        if 8 <= self.hour <= 18:
            # Full daylight
            return 1.0
        elif 5 <= self.hour < 8:
            # Dawn - gradually increasing
            progress = (self.hour - 5) / 3.0
            return 0.3 + (0.7 * progress)
        elif 18 < self.hour <= 20:
            # Dusk - gradually decreasing
            progress = (self.hour - 18) / 2.0
            return 1.0 - (0.7 * progress)
        else:
            # Night - minimal light
            return 0.3

    def get_time_desc(self) -> str:
        """
        Get a descriptive string for the current time.

        Returns:
            Description like "early morning", "late afternoon", etc.
        """
        period = self.get_period()

        descriptions = {
            'night': "the dead of night",
            'dawn': "the break of dawn",
            'morning': "mid-morning",
            'afternoon': "mid-afternoon",
            'dusk': "dusk",
            'evening': "evening"
        }

        return descriptions.get(period, period)

    def get_time_string(self) -> str:
        """
        Get a formatted string representation of the current time.

        Returns:
            String like "12:00 PM, Day 15 of Midsummer, Year 1000"
        """
        # Convert to 12-hour format
        hour_12 = self.hour if self.hour <= 12 else self.hour - 12
        if hour_12 == 0:
            hour_12 = 12
        am_pm = "AM" if self.hour < 12 else "PM"

        return (f"{hour_12}:00 {am_pm}, Day {self.day} of {self.get_month_name()}, "
                f"Year {self.year}")

    def get_short_time_string(self) -> str:
        """
        Get a short formatted time string.

        Returns:
            String like "12:00 PM"
        """
        hour_12 = self.hour if self.hour <= 12 else self.hour - 12
        if hour_12 == 0:
            hour_12 = 12
        am_pm = "AM" if self.hour < 12 else "PM"

        return f"{hour_12}:00 {am_pm}"

    def get_time_announcement(self) -> str:
        """
        Get an announcement message for time changes.

        Returns:
            Announcement message for significant time changes
        """
        if self.hour == 0:
            return f"Midnight strikes. A new day begins - Day {self.day} of {self.get_month_name()}."
        elif self.hour == 6:
            return "The sun rises on the eastern horizon."
        elif self.hour == 12:
            return "The sun reaches its zenith at high noon."
        elif self.hour == 18:
            return "The sun begins to set in the west."
        elif self.hour == 20:
            return "Night falls across the land."
        else:
            return None

    def to_dict(self) -> Dict:
        """
        Serialize game time to a dictionary for saving.

        Returns:
            Dictionary containing time state
        """
        return {
            'hour': self.hour,
            'day': self.day,
            'month': self.month,
            'year': self.year,
            'tick_counter': self.tick_counter
        }

    @classmethod
    def from_dict(cls, data: Dict) -> 'GameTime':
        """
        Load game time from a dictionary.

        Args:
            data: Dictionary containing time state

        Returns:
            GameTime instance
        """
        game_time = cls(
            start_hour=data.get('hour', 12),
            start_day=data.get('day', 1),
            start_month=data.get('month', 6),
            start_year=data.get('year', 1000)
        )
        game_time.tick_counter = data.get('tick_counter', 0)
        return game_time

    def __str__(self) -> str:
        """String representation of the current time."""
        return self.get_time_string()

    def __repr__(self) -> str:
        """Developer representation of the GameTime object."""
        return f"GameTime(hour={self.hour}, day={self.day}, month={self.month}, year={self.year})"
