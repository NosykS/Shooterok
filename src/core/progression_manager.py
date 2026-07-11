# src/core/progression_manager.py

class ProgressionManager:
    def __init__(self, game_data):
        self.data = game_data  # посилання на завантажені дані з SaveManager

        # ГАРАНТІЯ БЕЗПЕКИ: якщо гра завантажила старий сейв без цього поля, ініціалізуємо його
        if "skill_points" not in self.data:
            self.data["skill_points"] = 0

    @property
    def skill_points(self):
        """Зручний property-доступ до очок навичок безпосередньо у словнику збереження"""
        return self.data["skill_points"]

    @skill_points.setter
    def skill_points(self, value):
        """Зручне оновлення значення прямо в структурі даних для SaveManager"""
        self.data["skill_points"] = value

    def calculate_xp_for_next_level(self):
        """Формула розрахунку необхідного досвіду: Level * 1000"""
        return self.data["player_level"] * 1000

    def add_xp(self, amount):
        """Додає досвід та перевіряє Level Up"""
        self.data["xp"] += amount
        xp_needed = self.calculate_xp_for_next_level()

        while self.data["xp"] >= xp_needed:
            self.data["xp"] -= xp_needed
            self.data["player_level"] += 1

            # ВИПРАВЛЕНО: тепер очки додаються безпосередньо у словник даних
            self.skill_points += 1
            print(f"LEVEL UP! Новий рівень: {self.data['player_level']}. Отримано 1 очко навичок.")
            xp_needed = self.calculate_xp_for_next_level()

    def upgrade_skill(self, stat_name, max_tier=5):
        """Прокачка конкретної характеристики за очки навичок"""
        if stat_name not in self.data["upgrades"]:
            return False

        # ВИПРАВЛЕНО: перевірка та зменшення очок синхронізовані зі збереженням
        if self.skill_points > 0 and self.data["upgrades"][stat_name] < max_tier:
            self.data["upgrades"][stat_name] += 1
            self.skill_points -= 1
            return True
        return False