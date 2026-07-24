# src/core/progression_manager.py
import logging
from typing import Any

logger = logging.getLogger(__name__)


class ProgressionManager:
    def __init__(self, game_data: dict[str, Any]) -> None:
        self.data = game_data  # reference to the data loaded by SaveManager

        # Safety net: initialize the field if an old save doesn't have it
        if "skill_points" not in self.data:
            self.data["skill_points"] = 0

    @property
    def skill_points(self) -> int:
        """Convenience property backed directly by the save data dict."""
        return self.data["skill_points"]

    @skill_points.setter
    def skill_points(self, value: int) -> None:
        self.data["skill_points"] = value

    def calculate_xp_for_next_level(self) -> int:
        """XP required for the next level: current_level * 1000."""
        return self.data["player_level"] * 1000

    def add_xp(self, amount: int) -> None:
        """Adds XP and handles level-up(s)."""
        self.data["xp"] += amount
        xp_needed = self.calculate_xp_for_next_level()

        while self.data["xp"] >= xp_needed:
            self.data["xp"] -= xp_needed
            self.data["player_level"] += 1
            self.skill_points += 1
            logger.info("Level up! New level: %s. Gained 1 skill point.", self.data["player_level"])
            xp_needed = self.calculate_xp_for_next_level()

    def upgrade_skill(self, stat_name: str, max_tier: int = 5) -> bool:
        """Spends a skill point to upgrade the given stat by one tier."""
        if stat_name not in self.data["upgrades"]:
            return False

        if self.skill_points > 0 and self.data["upgrades"][stat_name] < max_tier:
            self.data["upgrades"][stat_name] += 1
            self.skill_points -= 1
            return True
        return False
