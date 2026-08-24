# src/core/progression_manager.py
import logging
from typing import Any

from src.settings import SKILL_UNLOCK_LEVELS, PLAYER_LEVEL_CAP

logger = logging.getLogger(__name__)


class ProgressionManager:
    def __init__(self, game_data: dict[str, Any]) -> None:
        self.data = game_data  # reference to the data loaded by SaveManager

        # Safety net: initialize the field if an old save doesn't have it
        if "skill_points" not in self.data:
            self.data["skill_points"] = 0

        if "unlocked_skills" not in self.data:
            self.data["unlocked_skills"] = []

    @property
    def skill_points(self) -> int:
        """Convenience property backed directly by the save data dict."""
        return self.data["skill_points"]

    @skill_points.setter
    def skill_points(self, value: int) -> None:
        self.data["skill_points"] = value

    @property
    def unlocked_skills(self) -> list[dict[str, Any]]:
        """Skill slots unlocked so far via level-up (see _register_skill_unlock_if_due)."""
        return self.data["unlocked_skills"]

    def get_pending_skill_slots(self) -> list[dict[str, Any]]:
        """Unlocked slots with no skill assigned yet — there's no skill catalog or
        pick-a-skill UI to resolve them (RPG_CLASS_SYSTEM.md section 7), so every
        slot stays pending until that's built."""
        return [slot for slot in self.unlocked_skills if slot["skill_id"] is None]

    def calculate_xp_for_next_level(self) -> int:
        """XP required for the next level: current_level * 1000."""
        return self.data["player_level"] * 1000

    def add_xp(self, amount: int) -> None:
        """Adds XP and handles level-up(s), capped at PLAYER_LEVEL_CAP.

        XP still accumulates past the cap (simplest option — it's just never
        spent again once player_level can't rise any further).
        """
        self.data["xp"] += amount
        xp_needed = self.calculate_xp_for_next_level()

        while self.data["xp"] >= xp_needed and self.data["player_level"] < PLAYER_LEVEL_CAP:
            self.data["xp"] -= xp_needed
            self.data["player_level"] += 1
            self.skill_points += 1
            logger.info("Level up! New level: %s. Gained 1 skill point.", self.data["player_level"])
            self._register_skill_unlock_if_due(self.data["player_level"])
            xp_needed = self.calculate_xp_for_next_level()

    def _register_skill_unlock_if_due(self, level: int) -> None:
        """Records a pending RPG skill slot when `level` lands on the unlock cadence
        (SKILL_UNLOCK_LEVELS: every 2nd level, alternating active/passive from level 2).
        No skill catalog exists yet, so the slot is left with skill_id=None — a future
        pick-a-skill UI resolves it later (RPG_CLASS_SYSTEM.md sections 4 and 7)."""
        if level not in SKILL_UNLOCK_LEVELS:
            return

        slot_index = SKILL_UNLOCK_LEVELS.index(level)
        slot_type = "active" if slot_index % 2 == 0 else "passive"

        self.data["unlocked_skills"].append({"level": level, "type": slot_type, "skill_id": None})
        logger.info("Skill slot unlocked at level %s (%s) — pending, no skill catalog yet.", level, slot_type)

    def upgrade_skill(self, stat_name: str, max_tier: int = 5) -> bool:
        """Spends a skill point to upgrade the given stat by one tier."""
        if stat_name not in self.data["upgrades"]:
            return False

        if self.skill_points > 0 and self.data["upgrades"][stat_name] < max_tier:
            self.data["upgrades"][stat_name] += 1
            self.skill_points -= 1
            return True
        return False
