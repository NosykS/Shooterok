# src/core/save_manager.py
import copy
import json
import logging
import os
from typing import Any

logger = logging.getLogger(__name__)

SAVE_FILE = "savegame.json"

DEFAULT_DATA: dict[str, Any] = {
    "current_level": 1,
    "money": 500,
    "xp": 0,
    "player_level": 1,
    "skill_points": 0,
    "upgrades": {
        "max_hp": 0,  # upgrade tier (0, 1, 2... up to 5)
        "max_armor": 0,
        "speed": 0
    },
    "unlocked_weapons": ["knife", "pistol_silenced"],
    "equipped_weapon": "pistol_silenced",
    "player_class": None,  # RPG subclass key (e.g. "dd_melee"); None until class selection UI exists
    "unlocked_skills": [],  # Pending/assigned RPG skill slots; see ProgressionManager
    "settings": {
        "music_volume": 1.0,
        "sfx_volume": 1.0
    }
}


class SaveManager:
    @staticmethod
    def load_game() -> dict[str, Any]:
        """Loads player data. Creates default data if no save file exists."""
        if not os.path.exists(SAVE_FILE):
            SaveManager.save_game(DEFAULT_DATA)
            return copy.deepcopy(DEFAULT_DATA)

        try:
            with open(SAVE_FILE, "r", encoding="utf-8") as f:
                data = json.load(f)

                # Guard against old saves missing fields: fill in defaults.
                # deepcopy so a save never ends up sharing a list/dict instance
                # with DEFAULT_DATA itself (mutating one would otherwise leak
                # into every other save loaded afterward in the same run).
                for key, value in DEFAULT_DATA.items():
                    if key not in data:
                        data[key] = copy.deepcopy(value)

                if "skill_points" not in data:
                    data["skill_points"] = 0

                # Guard against old saves missing volume settings
                data.setdefault("settings", {})
                for key, value in DEFAULT_DATA["settings"].items():
                    data["settings"].setdefault(key, value)

                # AUTO-FIX FOR OLD SAVES: repair the equipped weapon id
                if data.get("equipped_weapon") == "pistol":
                    data["equipped_weapon"] = "pistol_silenced"

                # Repair the unlocked weapons list too
                if "unlocked_weapons" in data:
                    for idx, wp in enumerate(data["unlocked_weapons"]):
                        if wp == "pistol":
                            data["unlocked_weapons"][idx] = "pistol_silenced"

                return data
        except (OSError, json.JSONDecodeError):
            logger.error("Failed to load save file", exc_info=True)
            return copy.deepcopy(DEFAULT_DATA)

    @staticmethod
    def save_game(data: dict[str, Any]) -> None:
        """Writes the current data to the JSON save file."""
        try:
            with open(SAVE_FILE, "w", encoding="utf-8") as f:
                json.dump(data, f, indent=4, ensure_ascii=False)
        except OSError:
            logger.error("Failed to save game", exc_info=True)
