# src/core/level_manager.py
import pygame
import random
from src.settings import TILE_SIZE, ENEMY_TYPES, SCREEN_WIDTH, SCREEN_HEIGHT
from src.entities.player import Player
from src.entities.enemy import Enemy
from src.objects.obstacle import Obstacle
from src.objects.hiding_spot import HidingSpot
from src.world.map_generator import MapGenerator

class LevelManager:
    def __init__(self, game):
        self.game = game

    def reset_game_world(self, new_map=True, new_level=False):
        """Повне або часткове скидання стану сцени для перезапуску або переходу на новий рівень"""
        # 1. Спочатку створюємо гравця
        self.game.player = Player(self.game, SCREEN_WIDTH // 2, SCREEN_HEIGHT // 2)

        # 2. Застосовуємо апгрейди та підтягуємо стані з профілю
        self.game.apply_player_upgrades()

        # 3. І ТІЛЬКИ ТЕПЕР примусово видаємо набої, щоб апгрейди/збереження їх не затерли!
        self.game.player.refill_all_ammo()

        self.game.gunshot_visual_timer = 0
        self.game.knife_visual_timer = 0

        # Очищення груп спрайтів
        for sprite in self.game.all_sprites:
            sprite.kill()

        self.game.all_sprites = pygame.sprite.Group(self.game.player)
        self.game.bullets = pygame.sprite.Group()
        self.game.enemies = pygame.sprite.Group()
        self.game.obstacles = pygame.sprite.Group()
        self.game.hiding_spots = pygame.sprite.Group()

        # Робота з матрицею карти
        if new_map or self.game.saved_game_matrix is None:
            self.game.game_matrix, self.game.saved_hiding_spots_data = MapGenerator.generate_level(self.game.player.pos)
            self.game.saved_game_matrix = [row[:] for row in self.game.game_matrix]
        else:
            self.game.game_matrix = [row[:] for row in self.game.saved_game_matrix]

        # Побудова фізичних стін
        for r_idx, row in enumerate(self.game.game_matrix):
            for c_idx, val in enumerate(row):
                if val == 0:
                    wall = Obstacle(c_idx * TILE_SIZE, r_idx * TILE_SIZE, TILE_SIZE, TILE_SIZE)
                    self.game.obstacles.add(wall)
                    self.game.all_sprites.add(wall)

        # Розміщення точок приховування
        for pos_x, pos_y in self.game.saved_hiding_spots_data:
            spot = HidingSpot(pos_x, pos_y, TILE_SIZE, TILE_SIZE)
            self.game.hiding_spots.add(spot)
            self.game.all_sprites.add(spot)

        # Розрахунок та спавн ворогів
        num_enemies = random.randint(4, 6) if new_level else random.randint(2, 4)
        spawn_positions = MapGenerator.get_enemy_spawn_positions(
            self.game.game_matrix, self.game.saved_hiding_spots_data, self.game.player.pos, count=num_enemies
        )

        enemy_types_available = list(ENEMY_TYPES.keys())
        for pos_x, pos_y in spawn_positions:
            chosen_type = random.choice(enemy_types_available)
            enemy = Enemy(pos_x, pos_y, chosen_type, game_matrix=self.game.game_matrix)
            enemy.melee_cooldown = 0
            self.game.enemies.add(enemy)
            self.game.all_sprites.add(enemy)