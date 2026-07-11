# src/core/save_manager.py
import json
import os

SAVE_FILE = "savegame.json"

DEFAULT_DATA = {
    "current_level": 1,
    "money": 500,
    "xp": 0,
    "player_level": 1,
    "skill_points": 0,  # ДОДАНО: Зберігаємо невикористані очки навичок на диску!
    "upgrades": {
        "max_hp": 0,  # рівень прокачки (0, 1, 2... до 5)
        "max_armor": 0,
        "speed": 0
    },
    "unlocked_weapons": ["knife", "pistol_silenced"],  # ВИПРАВЛЕНО: замінено "pistol" на "pistol_silenced"
    "equipped_weapon": "pistol_silenced"  # ВИПРАВЛЕНО: замінено "pistol" на "pistol_silenced"
}


class SaveManager:
    @staticmethod
    def load_game():
        """Завантажує дані гравця. Якщо файлу немає, створює дефолтні."""
        if not os.path.exists(SAVE_FILE):
            SaveManager.save_game(DEFAULT_DATA)
            return DEFAULT_DATA.copy()

        try:
            with open(SAVE_FILE, "r", encoding="utf-8") as f:
                data = json.load(f)

                # Захист від старих збережень: якщо якогось поля немає, додаємо його дефолтне значення
                for key, value in DEFAULT_DATA.items():
                    if key not in data:
                        data[key] = value

                if "skill_points" not in data:
                    data["skill_points"] = 0

                # АВТОКОРЕКЦІЯ ДЛЯ СТАРИХ СЕЙВІВ:
                # Перевіряємо та виправляємо екіпіровану зброю
                if data.get("equipped_weapon") == "pistol":
                    data["equipped_weapon"] = "pistol_silenced"

                # Перевіряємо список купленої зброї
                if "unlocked_weapons" in data:
                    for idx, wp in enumerate(data["unlocked_weapons"]):
                        if wp == "pistol":
                            data["unlocked_weapons"][idx] = "pistol_silenced"

                return data
        except Exception as e:
            print(f"Помилка завантаження збереження: {e}")
            return DEFAULT_DATA.copy()

    @staticmethod
    def save_game(data):
        """Записує поточні дані у JSON файл."""
        try:
            with open(SAVE_FILE, "w", encoding="utf-8") as f:
                json.dump(data, f, indent=4, ensure_ascii=False)
        except Exception as e:
            print(f"Помилка збереження гри: {e}")