# src/core/save_manager.py
import copy
import json
import logging
import os
from typing import Any

logger = logging.getLogger(__name__)

SAVE_FILE = "savegame.json"

# How many character slots a player can have at once. Kept small since character
# selection has no scrolling/pagination UI yet.
MAX_CHARACTER_SLOTS = 4

DEFAULT_CHARACTER: dict[str, Any] = {
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
    "player_class": None,  # RPG subclass key (e.g. "dd_melee"); set at character creation
    "unlocked_skills": [],  # Pending/assigned RPG skill slots; see ProgressionManager
}

# Top-level save shape: settings are shared across all characters, progress is not.
DEFAULT_SAVE: dict[str, Any] = {
    "settings": {
        "music_volume": 1.0,
        "sfx_volume": 1.0
    },
    "characters": [],
}


class SaveManager:
    @staticmethod
    def load_game() -> dict[str, Any]:
        """Loads the save file (shared settings + the character list). Creates a default one if missing."""
        if not os.path.exists(SAVE_FILE):
            SaveManager.save_game(DEFAULT_SAVE)
            return copy.deepcopy(DEFAULT_SAVE)

        try:
            with open(SAVE_FILE, "r", encoding="utf-8") as f:
                data = json.load(f)

                data.setdefault("settings", {})
                for key, value in DEFAULT_SAVE["settings"].items():
                    data["settings"].setdefault(key, value)

                data.setdefault("characters", [])
                for character in data["characters"]:
                    SaveManager._repair_character(character)

                return data
        except (OSError, json.JSONDecodeError):
            logger.error("Failed to load save file", exc_info=True)
            return copy.deepcopy(DEFAULT_SAVE)

    @staticmethod
    def _repair_character(character: dict[str, Any]) -> None:
        """Fills in fields missing from an older character save, in place."""
        for key, value in DEFAULT_CHARACTER.items():
            if key not in character:
                character[key] = copy.deepcopy(value)

        # AUTO-FIX FOR OLD SAVES: repair the equipped weapon id
        if character.get("equipped_weapon") == "pistol":
            character["equipped_weapon"] = "pistol_silenced"

        for idx, wp in enumerate(character["unlocked_weapons"]):
            if wp == "pistol":
                character["unlocked_weapons"][idx] = "pistol_silenced"

    @staticmethod
    def create_character() -> dict[str, Any]:
        """Returns a fresh character profile, not yet attached to any save."""
        return copy.deepcopy(DEFAULT_CHARACTER)

    @staticmethod
    def save_game(data: dict[str, Any]) -> None:
        """Writes the current save data (settings + characters) to the JSON save file."""
        try:
            with open(SAVE_FILE, "w", encoding="utf-8") as f:
                json.dump(data, f, indent=4, ensure_ascii=False)
        except OSError:
            logger.error("Failed to save game", exc_info=True)
