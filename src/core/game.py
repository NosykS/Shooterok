import pygame
import random
import math
from src.settings import (
    SCREEN_WIDTH, SCREEN_HEIGHT, FPS, BG_COLOR, TILE_SIZE,
    ENEMY_LOSE_INTEREST_TIME, ENEMY_TYPES, WEAPONS,
    WORLD_WIDTH, WORLD_HEIGHT
)
from src.entities.player import Player
from src.entities.enemy import Enemy
from src.objects.obstacle import Obstacle
from src.objects.hiding_spot import HidingSpot
from src.world.map_generator import MapGenerator
from src.core.ui import (
    draw_controls_help, draw_player_bars, draw_game_ui,
    UIButton
)
from src.core.camera import Camera


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

        # Ініціалізуємо камеру, передаючи повні піксельні розміри нашого великого світу
        self.camera = Camera(WORLD_WIDTH, WORLD_HEIGHT)

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

        # --- ІНІЦІАЛІЗАЦІЯ ШРИФТІВ ---
        pygame.font.init()
        self.pause_font_title = pygame.font.SysFont("Arial", 48, bold=True)
        self.pause_font_btn = pygame.font.SysFont("Arial", 22, bold=True)

        # Спочатку запускаємо базове скидання гри (тепер після створення шрифтів)
        self.reset_game(new_map=True)

        # Визначаємо центр екрана для вирівнювання кнопок
        cx = SCREEN_WIDTH // 2
        cy = SCREEN_HEIGHT // 2

        # Колірна палітра: базовий темно-сірий та синьо-блакитний при наведенні
        b_color = (40, 45, 55)
        h_color = (60, 80, 110)

        # Червона палітра для небезпечних дій (виходу чи поразки)
        red_b_color = (120, 35, 35)
        red_h_color = (160, 45, 45)

        # Зелена палітра для тріумфальних дій (перемоги)
        green_b_color = (35, 120, 65)
        green_h_color = (45, 160, 85)

        # --- ІНІЦІАЛІЗАЦІЯ МЕНЮ ПАУЗИ ---
        self.pause_buttons = [
            UIButton(cx, cy - 90, 260, 45, "Продовжити", self.pause_font_btn, b_color,
                     h_color, "CONTINUE"),
            UIButton(cx, cy - 30, 260, 45, "Перезапустити рівень", self.pause_font_btn,
                     b_color, h_color, "RESTART"),
            UIButton(cx, cy + 30, 260, 45, "Головне меню", self.pause_font_btn, b_color,
                     h_color, "MAIN_MENU"),
            UIButton(cx, cy + 90, 260, 45, "Вийти з гри", self.pause_font_btn, red_b_color,
                     red_h_color, "QUIT")
        ]

        # --- КНОПКИ ГОЛОВНОГО МЕНЮ ---
        self.main_menu_buttons = [
            UIButton(cx, cy - 30, 260, 45, "СТАРТ", self.pause_font_btn, b_color,
                     h_color, "START"),
            UIButton(cx, cy + 30, 260, 45, "ВИХІД", self.pause_font_btn, red_b_color,
                     red_h_color, "QUIT")
        ]

        # --- КНОПКИ ЕКРАНУ ПОРАЗКИ ---
        self.game_over_buttons = [
            UIButton(cx, cy + 20, 260, 45, "СПРОБУВАТИ ЗНОВУ", self.pause_font_btn, b_color,
                     h_color, "RESTART"),
            UIButton(cx, cy + 80, 260, 45, "ГОЛОВНЕ МЕНЮ", self.pause_font_btn, b_color,
                     h_color, "MAIN_MENU")
        ]

        # --- КНОПКИ ЕКРАНУ ПЕРЕМОГИ ---
        self.victory_buttons = [
            UIButton(cx, cy + 20, 260, 45, "ГРАТИ ЗНОВУ", self.pause_font_btn, green_b_color,
                     green_h_color, "RESTART"),
            UIButton(cx, cy + 80, 260, 45, "ГОЛОВНЕ МЕНЮ", self.pause_font_btn, b_color,
                     h_color, "MAIN_MENU")
        ]

    def reset_game(self, new_map=True, new_level=False):
        self.player = Player(SCREEN_WIDTH // 2, SCREEN_HEIGHT // 2)

        # Скидання візуальних таймерів ефектів, щоб вони не зависали при перезапуску
        self.gunshot_visual_timer = 0
        self.knife_visual_timer = 0

        # Очищення сцени та груп спрайтів
        for sprite in self.all_sprites:
            sprite.kill()

        self.all_sprites = pygame.sprite.Group(self.player)
        self.bullets = pygame.sprite.Group()
        self.enemies = pygame.sprite.Group()
        self.obstacles = pygame.sprite.Group()
        self.hiding_spots = pygame.sprite.Group()

        # Делегуємо генерацію карти
        if new_map or self.saved_game_matrix is None:
            self.game_matrix, self.saved_hiding_spots_data = MapGenerator.generate_level(self.player.pos)
            self.saved_game_matrix = [row[:] for row in self.game_matrix]
        else:
            self.game_matrix = [row[:] for row in self.saved_game_matrix]

        # Ініціалізація стін
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

        # Спавн ворогів
        if new_level:
            num_enemies = random.randint(4, 6)
        else:
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
        mouse_pos = pygame.mouse.get_pos()
        mouse_click = pygame.mouse.get_pressed()

        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                self.running = False

            elif self.game_state == "MENU":
                if event.type == pygame.KEYDOWN:
                    if event.key in [pygame.K_1, pygame.K_SPACE]:
                        self.reset_game(new_map=True, new_level=False)
                        self.game_state = "PLAYING"
                    elif event.key == pygame.K_ESCAPE:
                        self.running = False

            elif self.game_state == "GAME_OVER":
                if event.type == pygame.KEYDOWN:
                    if event.key == pygame.K_r:
                        self.reset_game(new_map=False, new_level=False)
                        self.game_state = "PLAYING"
                    elif event.key == pygame.K_SPACE:
                        self.reset_game(new_map=True, new_level=False)
                        self.game_state = "PLAYING"
                    elif event.key in [pygame.K_m, pygame.K_ESCAPE]:
                        self.game_state = "MENU"

            elif self.game_state == "VICTORY":
                if event.type == pygame.KEYDOWN:
                    if event.key == pygame.K_SPACE:
                        self.reset_game(new_map=True, new_level=True)
                        self.game_state = "PLAYING"
                    elif event.key in [pygame.K_m, pygame.K_ESCAPE]:
                        self.game_state = "MENU"

            elif self.game_state == "PAUSE":
                if event.type == pygame.KEYDOWN:
                    if event.key == pygame.K_ESCAPE:
                        self.game_state = "PLAYING"

            elif self.game_state == "PLAYING":
                if event.type == pygame.KEYDOWN:
                    if event.key == pygame.K_ESCAPE:
                        self.game_state = "PAUSE"
                        continue

                    if event.key == pygame.K_1: self.player.change_weapon(0)
                    if event.key == pygame.K_2: self.player.change_weapon(1)
                    if event.key == pygame.K_3: self.player.change_weapon(2)
                    if event.key == pygame.K_r: self.reset_game(new_map=True, new_level=False)

                    if event.key == pygame.K_e:
                        if self.player.is_hidden:
                            self.player.is_hidden = False
                        else:
                            hit_spot = pygame.sprite.spritecollideany(self.player, self.hiding_spots)
                            if hit_spot:
                                self.player.is_hidden = True
                                self.player.pos = pygame.math.Vector2(hit_spot.rect.center)

        # Обрахунок взаємодії з кнопками UI
        if self.game_state == "MENU":
            for btn in self.main_menu_buttons:
                action = btn.update(mouse_pos, mouse_click)
                if action == "START":
                    self.reset_game(new_map=True, new_level=False)
                    self.game_state = "PLAYING"
                elif action == "QUIT":
                    self.running = False

        elif self.game_state == "PAUSE":
            for btn in self.pause_buttons:
                action = btn.update(mouse_pos, mouse_click)
                if action == "CONTINUE":
                    self.game_state = "PLAYING"
                elif action == "RESTART":
                    self.reset_game(new_map=False, new_level=False)
                    self.game_state = "PLAYING"
                elif action == "MAIN_MENU":
                    self.game_state = "MENU"
                elif action == "QUIT":
                    self.running = False

        elif self.game_state == "GAME_OVER":
            for btn in self.game_over_buttons:
                action = btn.update(mouse_pos, mouse_click)
                if action == "RESTART":
                    self.reset_game(new_map=False, new_level=False)
                    self.game_state = "PLAYING"
                elif action == "MAIN_MENU":
                    self.game_state = "MENU"

        elif self.game_state == "VICTORY":
            for btn in self.victory_buttons:
                action = btn.update(mouse_pos, mouse_click)
                if action == "RESTART":
                    self.reset_game(new_map=True, new_level=True)
                    self.game_state = "PLAYING"
                elif action == "MAIN_MENU":
                    self.game_state = "MENU"

    def execute_knife_attack(self):
        self.knife_attack_radius = WEAPONS["knife"].get("damage_radius", 60)
        self.knife_visual_timer = 6
        self.knife_visual_pos = (int(self.player.pos.x), int(self.player.pos.y))

        mouse_pos = pygame.mouse.get_pos()
        world_mouse_x = mouse_pos[0] - self.camera.camera_rect.x
        world_mouse_y = mouse_pos[1] - self.camera.camera_rect.y
        world_mouse = pygame.math.Vector2(world_mouse_x, world_mouse_y)

        player_to_mouse = world_mouse - self.player.pos
        player_angle = player_to_mouse.as_polar()[1] if player_to_mouse.length() > 0 else 0

        for enemy in list(self.enemies):
            enemy_vec = enemy.pos - self.player.pos
            distance = enemy_vec.length()

            if distance < self.knife_attack_radius and distance > 0:
                angle_to_enemy = enemy_vec.as_polar()[1]
                angle_diff = (angle_to_enemy - player_angle) % 360
                if angle_diff > 180:
                    angle_diff = 360 - angle_diff

                if angle_diff <= 45:
                    if not enemy.is_alerted:
                        enemy.hp = 0
                        print(f"Тихий кіл ножем! Ворог {enemy.type} ліквідований.")
                    else:
                        enemy.hp -= WEAPONS["knife"]["damage"]
                        print(f"Поранення ножем! HP ворога: {enemy.hp}")

                    enemy.is_alerted = True
                    enemy.last_known_player_pos = pygame.math.Vector2(self.player.pos)
                    enemy.lose_interest_timer = ENEMY_LOSE_INTEREST_TIME

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
        is_moving = keys[pygame.K_w] or keys[pygame.K_s] or keys[pygame.K_a] or keys[pygame.K_d]

        self.player.update(keys, self.obstacles, self.camera)

        mouse_buttons = pygame.mouse.get_pressed()
        if mouse_buttons[0]:
            attack_result = self.player.attack(self.camera)

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

        for enemy in self.enemies:
            if enemy.fired_bullet:
                self.bullets.add(enemy.fired_bullet)
                self.all_sprites.add(enemy.fired_bullet)

        if is_moving and self.player.current_noise_radius > 0 and not self.player.is_hidden:
            for enemy in self.enemies:
                if enemy.pos.distance_to(self.player.pos) <= self.player.current_noise_radius:
                    enemy.is_alerted = True
                    enemy.last_known_player_pos = pygame.math.Vector2(self.player.pos)
                    enemy.lose_interest_timer = ENEMY_LOSE_INTEREST_TIME

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
            self.screen.fill((15, 20, 30))
            title_surf = self.pause_font_title.render("STEALTH ACTION", True, (0, 150, 255))
            title_rect = title_surf.get_rect(center=(SCREEN_WIDTH // 2, SCREEN_HEIGHT // 2 - 120))
            self.screen.blit(title_surf, title_rect)

            for btn in self.main_menu_buttons:
                btn.draw(self.screen)

        elif self.game_state in ["PLAYING", "PAUSE", "GAME_OVER", "VICTORY"]:
            if self.game_state == "PLAYING":
                self.camera.update(self.player)

            self.screen.fill(BG_COLOR)

            for enemy in self.enemies:
                enemy.draw_vision_cone(self.screen, self.camera)

            if self.gunshot_visual_timer > 0:
                s = pygame.Surface((self.gunshot_visual_radius * 2, self.gunshot_visual_radius * 2),
                                   pygame.SRCALPHA)
                pygame.draw.circle(s, (100, 200, 255, 120), (self.gunshot_visual_radius,
                                                             self.gunshot_visual_radius),
                                   self.gunshot_visual_radius, 4)

                flash_x = self.gunshot_visual_pos[0] - self.gunshot_visual_radius + self.camera.camera_rect.x
                flash_y = self.gunshot_visual_pos[1] - self.gunshot_visual_radius + self.camera.camera_rect.y
                self.screen.blit(s, (flash_x, flash_y))
                if self.game_state == "PLAYING":
                    self.gunshot_visual_timer -= 1

            if self.knife_visual_timer > 0:
                mouse_pos = pygame.mouse.get_pos()
                world_mouse = pygame.math.Vector2(mouse_pos[0] - self.camera.camera_rect.x,
                                                  mouse_pos[1] - self.camera.camera_rect.y)

                player_to_mouse = world_mouse - self.player.pos
                player_angle = player_to_mouse.as_polar()[1] if player_to_mouse.length() > 0 else 0

                knife_surf = pygame.Surface((SCREEN_WIDTH, SCREEN_HEIGHT), pygame.SRCALPHA)
                player_screen_pos = self.player.pos + pygame.math.Vector2(self.camera.camera_rect.topleft)
                points = [player_screen_pos]
                num_segments = 16
                view_angle = 90
                start_angle = player_angle - view_angle / 2

                for i in range(num_segments + 1):
                    ang = start_angle + (view_angle / num_segments) * i
                    rad = math.radians(ang)
                    world_point = self.player.pos + pygame.math.Vector2(math.cos(rad),
                                                                        math.sin(rad)) * self.knife_attack_radius
                    points.append(world_point + pygame.math.Vector2(self.camera.camera_rect.topleft))

                if len(points) >= 3:
                    pygame.draw.polygon(knife_surf, (255, 50, 50, 50), points)
                    pygame.draw.lines(knife_surf, (255, 100, 100, 180), False, points[1:], 2)

                self.screen.blit(knife_surf, (0, 0))
                if self.game_state == "PLAYING":
                    self.knife_visual_timer -= 1

            keys = pygame.key.get_pressed()
            is_moving = keys[pygame.K_w] or keys[pygame.K_s] or keys[pygame.K_a] or keys[pygame.K_d]

            if is_moving and self.player.current_noise_radius > 0 and not self.player.is_hidden:
                noise_x = int(self.player.pos.x + self.camera.camera_rect.x)
                noise_y = int(self.player.pos.y + self.camera.camera_rect.y)
                pygame.draw.circle(self.screen, (0, 150, 255), (noise_x, noise_y),
                                   self.player.current_noise_radius, 1)

            for sprite in self.all_sprites:
                if sprite == self.player and self.player.is_hidden:
                    continue
                self.screen.blit(sprite.image, self.camera.apply(sprite))

            for enemy in self.enemies:
                enemy.draw_health_bar(self.screen, self.camera)
                enemy.draw_suspicion_bar(self.screen, self.camera)

            for bullet in self.bullets:
                self.screen.blit(bullet.image, self.camera.apply(bullet))

            # --- МАЛЮВАННЯ ІНТЕРФЕЙСУ (ФІКС: Використовуємо існуючий self.pause_font_btn) ---
            draw_player_bars(self.screen, self.player, self.pause_font_btn)
            draw_game_ui(self.screen, self.player, self.enemies, keys, WEAPONS, self.pause_font_btn)

            if self.game_state == "PLAYING":
                draw_controls_help(self.screen, self.pause_font_btn)

            if self.game_state == "PAUSE":
                menu_width, menu_height = 340, 380
                menu_rect = pygame.Rect(SCREEN_WIDTH // 2 - menu_width // 2, SCREEN_HEIGHT // 2 - menu_height // 2,
                                        menu_width, menu_height)

                pygame.draw.rect(self.screen, (25, 30, 40), menu_rect, border_radius=12)
                pygame.draw.rect(self.screen, (0, 150, 255), menu_rect, width=2, border_radius=12)

                title_surf = self.pause_font_title.render("ПАУЗА", True, (0, 150, 255))
                title_rect = title_surf.get_rect(center=(SCREEN_WIDTH // 2, menu_rect.top + 40))
                self.screen.blit(title_surf, title_rect)

                for btn in self.pause_buttons:
                    btn.draw(self.screen)

            elif self.game_state == "GAME_OVER":
                menu_width, menu_height = 340, 260
                menu_rect = pygame.Rect(SCREEN_WIDTH // 2 - menu_width // 2, SCREEN_HEIGHT // 2 - menu_height // 2,
                                        menu_width, menu_height)

                pygame.draw.rect(self.screen, (30, 20, 20), menu_rect, border_radius=12)
                pygame.draw.rect(self.screen, (255, 50, 50), menu_rect, width=2, border_radius=12)

                title_surf = self.pause_font_title.render("ВИ ЗГИНУЛИ", True, (255, 50, 50))
                title_rect = title_surf.get_rect(center=(SCREEN_WIDTH // 2, menu_rect.top + 40))
                self.screen.blit(title_surf, title_rect)

                for btn in self.game_over_buttons:
                    btn.draw(self.screen)

            elif self.game_state == "VICTORY":
                menu_width, menu_height = 340, 260
                menu_rect = pygame.Rect(SCREEN_WIDTH // 2 - menu_width // 2, SCREEN_HEIGHT // 2 - menu_height // 2,
                                        menu_width, menu_height)

                pygame.draw.rect(self.screen, (20, 35, 25), menu_rect, border_radius=12)
                pygame.draw.rect(self.screen, (50, 255, 100), menu_rect, width=2, border_radius=12)

                title_surf = self.pause_font_title.render("ПЕРЕМОГА!", True, (50, 255, 100))
                title_rect = title_surf.get_rect(center=(SCREEN_WIDTH // 2, menu_rect.top + 40))
                self.screen.blit(title_surf, title_rect)

                for btn in self.victory_buttons:
                    btn.draw(self.screen)

    def run(self):
        while self.running:
            self.handle_events()
            self.update()
            self.draw()  # Всередині draw вже немає display.flip()
            pygame.display.flip()  # Єдиний правильний оновлювач екрана тут
            self.clock.tick(FPS)