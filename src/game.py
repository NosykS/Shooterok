import pygame
import random
import math
from src.settings import (
    SCREEN_WIDTH, SCREEN_HEIGHT, FPS, BG_COLOR, TILE_SIZE,
    ENEMY_LOSE_INTEREST_TIME, ENEMY_TYPES, WEAPONS
)
from src.player import Player
from src.enemy import Enemy
from src.obstacle import Obstacle
from src.hiding_spot import HidingSpot
from src.map_generator import MapGenerator
from src.ui import (
    draw_menu, draw_game_over, draw_victory,
    draw_controls_help, draw_player_bars, draw_game_ui
)


class Game:
    def __init__(self, screen):
        self.screen = screen
        self.clock = pygame.time.Clock()
        self.game_state = "MENU"
        self.running = True

        # Створення груп спрайтів
        self.player = None
        self.all_sprites = pygame.sprite.Group()
        self.bullets = pygame.sprite.Group()
        self.enemies = pygame.sprite.Group()
        self.obstacles = pygame.sprite.Group()
        self.hiding_spots = pygame.sprite.Group()
        self.game_matrix = None

        # Пам'ять карти для перезапуску після смерті
        self.saved_game_matrix = None
        self.saved_hiding_spots_data = []

        # Візуальні ефекти
        self.gunshot_visual_timer = 0
        self.gunshot_visual_pos = (0, 0)
        self.gunshot_visual_radius = 0

        self.knife_visual_timer = 0
        self.knife_visual_pos = (0, 0)
        self.knife_attack_radius = WEAPONS["knife"].get("damage_radius", 60)

        self.reset_game(new_map=True)

    def reset_game(self, new_map=True):
        # Очищення сцени
        for sprite in self.all_sprites:
            sprite.kill()

        self.player = Player(SCREEN_WIDTH // 2, SCREEN_HEIGHT // 2)

        self.all_sprites = pygame.sprite.Group(self.player)
        self.bullets = pygame.sprite.Group()
        self.enemies = pygame.sprite.Group()
        self.obstacles = pygame.sprite.Group()
        self.hiding_spots = pygame.sprite.Group()

        # Делегуємо генерацію карти окремому класу
        if new_map or self.saved_game_matrix is None:
            self.game_matrix, self.saved_hiding_spots_data = MapGenerator.generate_level(self.player.pos)
            self.saved_game_matrix = [row[:] for row in self.game_matrix]
        else:
            self.game_matrix = [row[:] for row in self.saved_game_matrix]

        # Ініціалізація стін на основі матриці
        for row_idx, row in enumerate(self.game_matrix):
            for col_idx, value in enumerate(row):
                if value == 0:
                    wall = Obstacle(col_idx * TILE_SIZE, row_idx * TILE_SIZE, TILE_SIZE, TILE_SIZE)
                    self.obstacles.add(wall)
                    self.all_sprites.add(wall)

        # Ініціалізація кущів
        for pos_x, pos_y in self.saved_hiding_spots_data:
            spot = HidingSpot(pos_x, pos_y, TILE_SIZE, TILE_SIZE)
            self.hiding_spots.add(spot)
            self.all_sprites.add(spot)

        # Спавн ворогів у безпечних зонах
        num_enemies = random.randint(2, 4)
        spawn_positions = MapGenerator.get_enemy_spawn_positions(
            self.game_matrix, self.saved_hiding_spots_data, self.player.pos, count=num_enemies
        )

        enemy_types_available = list(ENEMY_TYPES.keys())
        for pos_x, pos_y in spawn_positions:
            chosen_type = random.choice(enemy_types_available)
            enemy = Enemy(pos_x, pos_y, chosen_type, game_matrix=self.game_matrix)
            self.enemies.add(enemy)
            self.all_sprites.add(enemy)

    def handle_events(self):
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                self.running = False

            elif self.game_state == "MENU":
                if event.type == pygame.KEYDOWN:
                    if event.key == pygame.K_1:
                        self.reset_game(new_map=True)
                        self.game_state = "PLAYING"
                    elif event.key == pygame.K_ESCAPE:
                        self.running = False

            elif self.game_state in ["GAME_OVER", "VICTORY"]:
                if event.type == pygame.KEYDOWN:
                    if event.key == pygame.K_r:
                        self.reset_game(new_map=False)  # Граємо на тій самій карті
                        self.game_state = "PLAYING"
                    elif event.key == pygame.K_m:
                        self.game_state = "MENU"
                    elif event.key == pygame.K_ESCAPE:
                        self.running = False

            elif self.game_state == "PLAYING":
                if event.type == pygame.KEYDOWN:
                    if event.key == pygame.K_1: self.player.change_weapon(0)
                    if event.key == pygame.K_2: self.player.change_weapon(1)
                    if event.key == pygame.K_3: self.player.change_weapon(2)
                    if event.key == pygame.K_r: self.reset_game(new_map=True)

                    if event.key == pygame.K_e:
                        if self.player.is_hidden:
                            self.player.is_hidden = False
                        else:
                            hit_spot = pygame.sprite.spritecollideany(self.player, self.hiding_spots)
                            if hit_spot:
                                self.player.is_hidden = True
                                self.player.pos = pygame.math.Vector2(hit_spot.rect.center)

    def execute_knife_attack(self):
        """Обробляє конус ураження та логіку ближнього бою ножем."""
        self.knife_attack_radius = WEAPONS["knife"].get("damage_radius", 60)
        self.knife_visual_timer = 6
        self.knife_visual_pos = (int(self.player.pos.x), int(self.player.pos.y))

        mouse_pos = pygame.mouse.get_pos()
        player_to_mouse = pygame.math.Vector2(mouse_pos) - self.player.pos
        player_angle = player_to_mouse.as_polar()[1] if player_to_mouse.length() > 0 else 0

        for enemy in list(self.enemies):
            enemy_vec = enemy.pos - self.player.pos
            distance = enemy_vec.length()

            if distance < self.knife_attack_radius and distance > 0:
                angle_to_enemy = enemy_vec.as_polar()[1]
                angle_diff = (angle_to_enemy - player_angle) % 360
                if angle_diff > 180:
                    angle_diff = 360 - angle_diff

                if angle_diff <= 45:  # Сектор 90 градусів
                    if not enemy.is_alerted:
                        enemy.hp = 0
                        print(f"Тихий кіл ножем! Ворог {enemy.type} ліквідований.")
                    else:
                        enemy.hp -= WEAPONS["knife"]["damage"]
                        print(f"Поранення ножем! HP ворога: {enemy.hp}")

                    enemy.is_alerted = True
                    enemy.last_known_player_pos = pygame.math.Vector2(self.player.pos)
                    enemy.lose_interest_timer = ENEMY_LOSE_INTEREST_TIME

                    # Піднімаємо тривогу у ворогів, які бачать цей момент
                    for other_enemy in self.enemies:
                        if other_enemy != enemy and not other_enemy.is_alerted:
                            if other_enemy.check_for_player(self.player, self.obstacles):
                                other_enemy.is_alerted = True
                                other_enemy.last_known_player_pos = pygame.math.Vector2(self.player.pos)
                                other_enemy.lose_interest_timer = ENEMY_LOSE_INTEREST_TIME
                    if enemy.hp <= 0:
                        enemy.kill()

    def update(self):
        if self.game_state != "PLAYING":
            return

        keys = pygame.key.get_pressed()
        is_moving_normally = self.player.current_noise_radius > 0 and (
                keys[pygame.K_w] or keys[pygame.K_s] or keys[pygame.K_a] or keys[pygame.K_d])

        self.player.update(keys, self.obstacles)

        # Обробка атак
        mouse_buttons = pygame.mouse.get_pressed()
        if mouse_buttons[0]:
            attack_result = self.player.attack()

            if attack_result == "melee":
                self.execute_knife_attack()
            elif attack_result:
                self.all_sprites.add(attack_result)
                self.bullets.add(attack_result)

                weapon_stats = WEAPONS[self.player.current_weapon]
                noise_rad = weapon_stats["noise_radius"]

                if noise_rad > 0 and not getattr(self.player, "is_hidden", False):
                    for enemy in self.enemies:
                        if enemy.pos.distance_to(self.player.pos) < noise_rad:
                            enemy.is_alerted = True
                            enemy.last_known_player_pos = pygame.math.Vector2(self.player.pos)
                            enemy.lose_interest_timer = ENEMY_LOSE_INTEREST_TIME

                    self.gunshot_visual_timer = 10
                    self.gunshot_visual_pos = (int(self.player.pos.x), int(self.player.pos.y))
                    self.gunshot_visual_radius = noise_rad

        self.bullets.update()
        self.enemies.update(self.player, self.game_matrix, self.obstacles)

        # Реєстрація пострілів ворогів
        for enemy in self.enemies:
            if enemy.fired_bullet:
                self.bullets.add(enemy.fired_bullet)
                self.all_sprites.add(enemy.fired_bullet)

        # Звук кроків гравця приваблює ворогів
        if is_moving_normally and not self.player.is_hidden:
            for enemy in self.enemies:
                if enemy.pos.distance_to(self.player.pos) <= self.player.current_noise_radius:
                    enemy.is_alerted = True
                    enemy.last_known_player_pos = pygame.math.Vector2(self.player.pos)
                    enemy.lose_interest_timer = ENEMY_LOSE_INTEREST_TIME

        # Розрахунок зіткнень куль
        for bullet in list(self.bullets):
            if pygame.sprite.spritecollideany(bullet, self.obstacles):
                bullet.kill()
                continue

            if bullet.is_enemy_bullet:
                if bullet.rect.colliderect(self.player.rect):
                    if not self.player.is_hidden:
                        damage_to_deal = bullet.damage
                        if self.player.armor > 0:
                            armor_absorption = int(damage_to_deal * 0.6)
                            if self.player.armor >= armor_absorption:
                                self.player.armor -= armor_absorption
                                damage_to_deal -= armor_absorption
                            else:
                                damage_to_deal -= self.player.armor
                                self.player.armor = 0

                        self.player.hp -= damage_to_deal
                        print(f"Гравець поранений! HP: {self.player.hp} | Броня: {self.player.armor}")

                        if self.player.hp <= 0:
                            self.game_state = "GAME_OVER"
                    bullet.kill()
            else:
                hit_enemies = pygame.sprite.spritecollide(bullet, self.enemies, False)
                for enemy in hit_enemies:
                    damage_to_deal = bullet.damage
                    if enemy.armor > 0:
                        armor_absorption = int(damage_to_deal * 0.5)
                        if enemy.armor >= armor_absorption:
                            enemy.armor -= armor_absorption
                            damage_to_deal -= armor_absorption
                        else:
                            damage_to_deal -= enemy.armor
                            enemy.armor = 0

                    enemy.hp -= damage_to_deal
                    enemy.is_alerted = True
                    enemy.last_known_player_pos = pygame.math.Vector2(self.player.pos)
                    bullet.kill()

                    if enemy.hp <= 0:
                        enemy.kill()

        if len(self.enemies) == 0:
            self.game_state = "VICTORY"

    def draw(self):
        if self.game_state == "MENU":
            draw_menu(self.screen)
        elif self.game_state == "GAME_OVER":
            draw_game_over(self.screen)
        elif self.game_state == "VICTORY":
            draw_victory(self.screen)
        elif self.game_state == "PLAYING":
            self.screen.fill(BG_COLOR)

            for enemy in self.enemies:
                enemy.draw_vision_cone(self.screen)

            # Малювання спалаху від пострілу
            if self.gunshot_visual_timer > 0:
                s = pygame.Surface((self.gunshot_visual_radius * 2, self.gunshot_visual_radius * 2), pygame.SRCALPHA)
                pygame.draw.circle(s, (100, 200, 255, 120), (self.gunshot_visual_radius, self.gunshot_visual_radius),
                                   self.gunshot_visual_radius, 4)
                self.screen.blit(s, (
                    self.gunshot_visual_pos[0] - self.gunshot_visual_radius,
                    self.gunshot_visual_pos[1] - self.gunshot_visual_radius
                ))
                self.gunshot_visual_timer -= 1

            # Малювання конуса удару ножем
            if self.knife_visual_timer > 0:
                mouse_pos = pygame.mouse.get_pos()
                player_to_mouse = pygame.math.Vector2(mouse_pos) - self.player.pos
                player_angle = player_to_mouse.as_polar()[1] if player_to_mouse.length() > 0 else 0

                knife_surf = pygame.Surface((SCREEN_WIDTH, SCREEN_HEIGHT), pygame.SRCALPHA)
                points = [self.player.pos]
                num_segments = 16
                view_angle = 90
                start_angle = player_angle - view_angle / 2

                for i in range(num_segments + 1):
                    ang = start_angle + (view_angle / num_segments) * i
                    rad = math.radians(ang)
                    target_point = self.player.pos + pygame.math.Vector2(math.cos(rad),
                                                                         math.sin(rad)) * self.knife_attack_radius
                    points.append(target_point)

                if len(points) >= 3:
                    pygame.draw.polygon(knife_surf, (255, 50, 50, 50), points)
                    pygame.draw.lines(knife_surf, (255, 100, 100, 180), False, points[1:], 2)

                self.screen.blit(knife_surf, (0, 0))
                self.knife_visual_timer -= 1

            keys = pygame.key.get_pressed()
            is_moving_normally = self.player.current_noise_radius > 0 and (
                    keys[pygame.K_w] or keys[pygame.K_s] or keys[pygame.K_a] or keys[pygame.K_d])

            if is_moving_normally and not self.player.is_hidden:
                pygame.draw.circle(self.screen, (0, 150, 255), (int(self.player.pos.x), int(self.player.pos.y)),
                                   self.player.current_noise_radius, 1)

            for sprite in self.all_sprites:
                if sprite == self.player and self.player.is_hidden: continue
                self.screen.blit(sprite.image, sprite.rect)

            for enemy in self.enemies:
                enemy.draw_health_bar(self.screen)

            self.bullets.draw(self.screen)
            draw_player_bars(self.screen, self.player)
            draw_game_ui(self.screen, self.player, self.enemies, keys, WEAPONS)
            draw_controls_help(self.screen)

    def run(self):
        while self.running:
            self.handle_events()
            self.update()
            self.draw()
            pygame.display.flip()
            self.clock.tick(FPS)