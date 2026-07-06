# src/core/mission_manager.py
import pygame
import random
from src.settings import TILE_SIZE, MISSION_CONFIGS
from src.objects.mission_elements import ExitZone, DataDrive


class MissionManager:
    def __init__(self, game):
        self.game = game
        self.current_mission_num = 1
        self.data_collected = False
        self.cfg = MISSION_CONFIGS[1]

        self.exit_zones = pygame.sprite.Group()
        self.data_drives = pygame.sprite.Group()

    def load_mission(self, mission_num):
        """Завантаження конфігурації конкретної місії та генерація сцени"""
        # Якщо наступної місії не існує в списку конфігів
        if mission_num > len(MISSION_CONFIGS):
            self.game.game_state = "VICTORY_ALL"  # Перемикаємо на фінальний екран фіналу!
            self.current_mission_num = 1
            self.data_collected = False
            # Чистимо світ від залишків, щоб не було фантомних об'єктів
            self.game.levels.reset_game_world(new_map=True, new_level=False)
            return

        # Якщо місія існує, запускаємо її як зазвичай
        self.current_mission_num = mission_num
        self.data_collected = False
        self.cfg = MISSION_CONFIGS[mission_num]

        self.game.levels.reset_game_world(new_map=True, new_level=True)
        self.spawn_mission_objectives()
        self.game.game_state = "PLAYING"

    def spawn_mission_objectives(self):
        """Пошук підходящих точок на мапі та спавн квестових об'єктів місії"""
        self.exit_zones.empty()
        self.data_drives.empty()

        free_tiles = []
        for r_idx, row in enumerate(self.game.game_matrix):
            for c_idx, val in enumerate(row):
                if val == 1:
                    pos_x = c_idx * TILE_SIZE
                    pos_y = r_idx * TILE_SIZE
                    if pygame.math.Vector2(pos_x, pos_y).distance_to(self.game.player.pos) > 200:
                        free_tiles.append((pos_x, pos_y))

        random.shuffle(free_tiles)

        if "escape" in self.cfg["objectives"] and free_tiles:
            ex, ey = free_tiles.pop()
            exit_node = ExitZone(ex, ey)
            self.exit_zones.add(exit_node)
            self.game.all_sprites.add(exit_node)

        if "collect_data" in self.cfg["objectives"] and free_tiles:
            dx, dy = free_tiles.pop()
            drive = DataDrive(dx, dy)
            self.data_drives.add(drive)
            self.game.all_sprites.add(drive)

    def check_mission_conditions(self, frame_counter):
        """Перевірка глобальних умов виконання або провалу місії"""
        # 1. Провал стелсу
        if frame_counter % 10 == 0 and self.cfg.get("fail_on_alert", False):
            for enemy in self.game.enemies:
                if enemy.is_alerted:
                    self.game.game_state = "GAME_OVER"
                    print("Провал: Вас виявили!")
                    return

        # 2. Збір квестових даних
        if frame_counter % 5 == 0 and "collect_data" in self.cfg["objectives"] and not self.data_collected:
            hit_drive = pygame.sprite.spritecollideany(self.game.player, self.data_drives)
            if hit_drive:
                self.data_collected = True
                hit_drive.kill()
                print("Дані успішно зібрано!")

        # 3. Перевірка зони евакуації
        if frame_counter % 5 == 0 and "escape" in self.cfg["objectives"]:
            if pygame.sprite.spritecollideany(self.game.player, self.exit_zones):
                can_escape = True
                if "collect_data" in self.cfg["objectives"] and not self.data_collected:
                    can_escape = False

                if can_escape:
                    self.game.game_state = "VICTORY"
                    print(f"Місію {self.current_mission_num} виконано!")

        # 4. Перевірка зачистки сектору
        if frame_counter % 15 == 0 and "kill_all" in self.cfg["objectives"] and len(self.game.enemies) == 0:
            self.game.game_state = "VICTORY"
            print(f"Сектор повністю очищено. Місію {self.current_mission_num} виконано!")