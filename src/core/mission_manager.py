# src/core/mission_manager.py
import pygame
from src.settings import MISSION_CONFIGS
from src.objects.mission_elements import ExitZone, DataDrive


class MissionManager:
    def __init__(self, game):
        self.game = game
        self.current_mission_num = 1
        self.data_collected = False
        self.cfg = MISSION_CONFIGS[1]

        # Прапорець активації фінального виходу (потрібен для місій на знищення)
        self.escape_activated = False

        self.exit_zones = pygame.sprite.Group()
        self.data_drives = pygame.sprite.Group()

    def load_mission(self, mission_num):
        """Завантаження конкретної місії"""
        if mission_num > len(MISSION_CONFIGS):
            self.game.game_state = "VICTORY_ALL"
            self.current_mission_num = 1
            self.data_collected = False
            self.game.levels.reset_game_world(new_map=True, new_level=False)
            return

        self.current_mission_num = mission_num
        self.data_collected = False
        self.escape_activated = False
        self.cfg = MISSION_CONFIGS[mission_num]

        # Завантажуємо відповідну TMX карту та створюємо світ
        self.game.levels.reset_game_world(new_map=True, new_level=True)
        self.spawn_mission_objectives()
        self.game.game_state = "PLAYING"

    def spawn_mission_objectives(self):
        """Спавн квестових об'єктів на основі точок з TMX карти"""
        self.exit_zones.empty()
        self.data_drives.empty()

        quest_points = getattr(self.game, 'quest_spawn_points', [])

        # 1. Сценарій: Тільки евакуація (Місія 1)
        if "escape" in self.cfg["objectives"] and "kill_all" not in self.cfg["objectives"] and "collect_data" not in \
                self.cfg["objectives"]:
            for pt in quest_points:
                if pt["name"] in ["escape", "exit"]:
                    exit_node = ExitZone(pt["x"], pt["y"])
                    self.exit_zones.add(exit_node)
                    self.game.all_sprites.add(exit_node)
                    print(f"[MISSION] Зону евакуації створено на ({pt['x']}, {pt['y']})")

        # 2. Сценарій: Збір даних (Місія 3)
        if "collect_data" in self.cfg["objectives"]:
            for pt in quest_points:
                if pt["name"] in ["documents", "data"]:
                    drive = DataDrive(pt["x"], pt["y"])
                    self.data_drives.add(drive)
                    self.game.all_sprites.add(drive)
                    print(f"[MISSION] Дані для збору розміщено на ({pt['x']}, {pt['y']})")

            # Також одразу створюємо зону виходу, але зайти в неї без даних не вийде
            for pt in quest_points:
                if pt["name"] in ["escape", "exit"]:
                    exit_node = ExitZone(pt["x"], pt["y"])
                    self.exit_zones.add(exit_node)
                    self.game.all_sprites.add(exit_node)

    def check_mission_conditions(self, frame_counter):
        """Гнучка перевірка умов виконання місій у кожному кадрі"""
        # 1. Перевірка провалу через тривогу
        if frame_counter % 10 == 0 and self.cfg.get("fail_on_alert", False):
            for enemy in self.game.enemies:
                if enemy.is_alerted:
                    self.game.game_state = "GAME_OVER"
                    print("Провал: Вас виявили!")
                    return

        # 2. Обробка збору даних (Місія 3)
        if frame_counter % 5 == 0 and "collect_data" in self.cfg["objectives"] and not self.data_collected:
            hit_drive = pygame.sprite.spritecollideany(self.game.player, self.data_drives)
            if hit_drive:
                self.data_collected = True
                hit_drive.kill()
                print("[MISSION] Дані успішно зібрано! Прямуйте до зони евакуації.")

        # 3. Динамічна активація евакуації після знищення ворогів (Місія 2)
        if "kill_all" in self.cfg["objectives"] and len(self.game.enemies) == 0 and not self.escape_activated:
            self.escape_activated = True
            quest_points = getattr(self.game, 'quest_spawn_points', [])
            for pt in quest_points:
                if pt["name"] in ["escape", "exit"]:
                    exit_node = ExitZone(pt["x"], pt["y"])
                    self.exit_zones.add(exit_node)
                    self.game.all_sprites.add(exit_node)
                    print("[MISSION] Усіх ворогів знищено! Точка евакуації тепер АКТИВНА.")

        # 4. Перевірка прибуття в зону евакуації
        if frame_counter % 5 == 0:
            if pygame.sprite.spritecollideany(self.game.player, self.exit_zones):
                can_escape = True

                # Не можна вийти без документів (Місія 3)
                if "collect_data" in self.cfg["objectives"] and not self.data_collected:
                    can_escape = False

                # Не можна втекти, поки вороги живі (Місія 2)
                if "kill_all" in self.cfg["objectives"] and not self.escape_activated:
                    can_escape = False

                if can_escape:
                    self.game.game_state = "VICTORY"
                    print(f"[MISSION] Місію {self.current_mission_num} виконано успішно!")