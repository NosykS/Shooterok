# src/core/game.py
import pygame
import random
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
    draw_gunshot_flash, draw_knife_swing, UIButton
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

        self.camera = Camera(WORLD_WIDTH, WORLD_HEIGHT)

        # Пам'ять карти для перезапуску
        self.saved_game_matrix = None
        self.saved_hiding_spots_data = []

        # Візуальні ефекти
        self.gunshot_visual_timer = 0
        self.gunshot_visual_pos = (0, 0)
        self.gunshot_visual_radius = 0

        self.knife_visual_timer = 0
        self.knife_visual_pos = (0, 0)
        self.knife_attack_radius = WEAPONS["knife"].get("damage_radius", 60)

        # --- ШРИФТИ ---
        pygame.font.init()
        self.pause_font_title = pygame.font.SysFont("Arial", 48, bold=True)
        self.pause_font_btn = pygame.font.SysFont("Arial", 22, bold=True)

        self.reset_game(new_map=True)
        self._init_ui_buttons()

    def _init_ui_buttons(self):
        """Ініціалізація всіх екранних кнопок"""
        cx, cy = SCREEN_WIDTH // 2, SCREEN_HEIGHT // 2
        b_color, h_color = (40, 45, 55), (60, 80, 110)
        red_b, red_h = (120, 35, 35), (160, 45, 45)
        green_b, green_h = (35, 120, 65), (45, 160, 85)

        self.pause_buttons = [
            UIButton(cx, cy - 90, 260, 45, "Продовжити", self.pause_font_btn, b_color, h_color, "CONTINUE"),
            UIButton(cx, cy - 30, 260, 45, "Перезапустити рівень", self.pause_font_btn, b_color, h_color, "RESTART"),
            UIButton(cx, cy + 30, 260, 45, "Головне меню", self.pause_font_btn, b_color, h_color, "MAIN_MENU"),
            UIButton(cx, cy + 90, 260, 45, "Вийти з гри", self.pause_font_btn, red_b, red_h, "QUIT")
        ]
        self.main_menu_buttons = [
            UIButton(cx, cy - 30, 260, 45, "СТАРТ", self.pause_font_btn, b_color, h_color, "START"),
            UIButton(cx, cy + 30, 260, 45, "ВИХІД", self.pause_font_btn, red_b, red_h, "QUIT")
        ]
        self.game_over_buttons = [
            UIButton(cx, cy + 20, 260, 45, "СПРОБУВАТИ ЗНОВУ", self.pause_font_btn, b_color, h_color, "RESTART"),
            UIButton(cx, cy + 80, 260, 45, "ГОЛОВНЕ МЕНЮ", self.pause_font_btn, b_color, h_color, "MAIN_MENU")
        ]
        self.victory_buttons = [
            UIButton(cx, cy + 20, 260, 45, "ГРАТИ ЗНОВУ", self.pause_font_btn, green_b, green_h, "RESTART"),
            UIButton(cx, cy + 80, 260, 45, "ГОЛОВНЕ МЕНЮ", self.pause_font_btn, b_color, h_color, "MAIN_MENU")
        ]

    def reset_game(self, new_map=True, new_level=False):
        self.player = Player(SCREEN_WIDTH // 2, SCREEN_HEIGHT // 2)
        self.gunshot_visual_timer = 0
        self.knife_visual_timer = 0

        for sprite in self.all_sprites:
            sprite.kill()

        self.all_sprites = pygame.sprite.Group(self.player)
        self.bullets = pygame.sprite.Group()
        self.enemies = pygame.sprite.Group()
        self.obstacles = pygame.sprite.Group()
        self.hiding_spots = pygame.sprite.Group()

        if new_map or self.saved_game_matrix is None:
            self.game_matrix, self.saved_hiding_spots_data = MapGenerator.generate_level(self.player.pos)
            self.saved_game_matrix = [row[:] for row in self.game_matrix]
        else:
            self.game_matrix = [row[:] for row in self.saved_game_matrix]

        # Побудова стін та схованок
        for r_idx, row in enumerate(self.game_matrix):
            for c_idx, val in enumerate(row):
                if val == 0:
                    wall = Obstacle(c_idx * TILE_SIZE, r_idx * TILE_SIZE, TILE_SIZE, TILE_SIZE)
                    self.obstacles.add(wall)
                    self.all_sprites.add(wall)

        for pos_x, pos_y in self.saved_hiding_spots_data:
            spot = HidingSpot(pos_x, pos_y, TILE_SIZE, TILE_SIZE)
            self.hiding_spots.add(spot)
            self.all_sprites.add(spot)

        # Спавн ворогів
        num_enemies = random.randint(4, 6) if new_level else random.randint(2, 4)
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
            elif self.game_state == "PLAYING":
                self._handle_playing_inputs(event)
            else:
                self._handle_menu_inputs(event)

        self._update_ui_button_actions(mouse_pos, mouse_click)

    def _handle_playing_inputs(self, event):
        if event.type == pygame.KEYDOWN:
            if event.key == pygame.K_ESCAPE:
                self.game_state = "PAUSE"
            elif event.key == pygame.K_1:
                self.player.change_weapon(0)
            elif event.key == pygame.K_2:
                self.player.change_weapon(1)
            elif event.key == pygame.K_3:
                self.player.change_weapon(2)
            elif event.key == pygame.K_r:
                self.reset_game(new_map=True, new_level=False)
            elif event.key == pygame.K_e:
                if self.player.is_hidden:
                    self.player.is_hidden = False
                else:
                    hit_spot = pygame.sprite.spritecollideany(self.player, self.hiding_spots)
                    if hit_spot:
                        self.player.is_hidden = True
                        self.player.pos = pygame.math.Vector2(hit_spot.rect.center)

    def _handle_menu_inputs(self, event):
        if event.type == pygame.KEYDOWN:
            if self.game_state == "MENU":
                if event.key in [pygame.K_1, pygame.K_SPACE]:
                    self.reset_game(new_map=True, new_level=False)
                    self.game_state = "PLAYING"
                elif event.key == pygame.K_ESCAPE:
                    self.running = False
            elif self.game_state == "GAME_OVER":
                if event.key == pygame.K_r:
                    self.reset_game(new_map=False, new_level=False)
                    self.game_state = "PLAYING"
                elif event.key == pygame.K_SPACE:
                    self.reset_game(new_map=True, new_level=False)
                    self.game_state = "PLAYING"
                elif event.key in [pygame.K_m, pygame.K_ESCAPE]:
                    self.game_state = "MENU"
            elif self.game_state == "VICTORY":
                if event.key == pygame.K_SPACE:
                    self.reset_game(new_map=True, new_level=True)
                    self.game_state = "PLAYING"
                elif event.key in [pygame.K_m, pygame.K_ESCAPE]:
                    self.game_state = "MENU"
            elif self.game_state == "PAUSE" and event.key == pygame.K_ESCAPE:
                self.game_state = "PLAYING"

    def _update_ui_button_actions(self, mouse_pos, mouse_click):
        active_buttons = []
        if self.game_state == "MENU":
            active_buttons = self.main_menu_buttons
        elif self.game_state == "PAUSE":
            active_buttons = self.pause_buttons
        elif self.game_state == "GAME_OVER":
            active_buttons = self.game_over_buttons
        elif self.game_state == "VICTORY":
            active_buttons = self.victory_buttons

        for btn in active_buttons:
            action = btn.update(mouse_pos, mouse_click)
            if action in ["START", "CONTINUE"]:
                if action == "START": self.reset_game(new_map=True, new_level=False)
                self.game_state = "PLAYING"
            elif action == "RESTART":
                self.reset_game(new_map=False, new_level=(self.game_state == "VICTORY"))
                self.game_state = "PLAYING"
            elif action == "MAIN_MENU":
                self.game_state = "MENU"
            elif action == "QUIT":
                self.running = False

    def execute_knife_attack(self):
        self.knife_attack_radius = WEAPONS["knife"].get("damage_radius", 60)
        self.knife_visual_timer = 6
        self.knife_visual_pos = (int(self.player.pos.x), int(self.player.pos.y))

        mouse_pos = pygame.mouse.get_pos()
        world_mouse = pygame.math.Vector2(mouse_pos[0] - self.camera.camera_rect.x,
                                          mouse_pos[1] - self.camera.camera_rect.y)
        player_to_mouse = world_mouse - self.player.pos
        player_angle = player_to_mouse.as_polar()[1] if player_to_mouse.length() > 0 else 0

        for enemy in list(self.enemies):
            enemy_vec = enemy.pos - self.player.pos
            distance = enemy_vec.length()

            if distance < self.knife_attack_radius and distance > 0:
                angle_to_enemy = enemy_vec.as_polar()[1]
                angle_diff = (angle_to_enemy - player_angle) % 360
                if angle_diff > 180: angle_diff = 360 - angle_diff

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

                    if enemy.hp <= 0: enemy.kill()

    def _handle_attacks(self):
        mouse_buttons = pygame.mouse.get_pressed()
        if mouse_buttons[0]:
            attack_result = self.player.attack(self.camera)
            if attack_result == "melee":
                self.execute_knife_attack()
            elif attack_result:
                self.all_sprites.add(attack_result)
                self.bullets.add(attack_result)

                weapon_stats = WEAPONS[self.player.current_weapon]
                self.gunshot_visual_timer = 8
                self.gunshot_visual_pos = (int(self.player.pos.x), int(self.player.pos.y))
                self.gunshot_visual_radius = weapon_stats["noise_radius"]

    def _check_environmental_sounds(self):
        if self.player.current_noise_radius > 0 and not self.player.is_hidden:
            for enemy in self.enemies:
                if enemy.pos.distance_to(self.player.pos) <= self.player.current_noise_radius:
                    enemy.is_alerted = True
                    enemy.last_known_player_pos = pygame.math.Vector2(self.player.pos)
                    enemy.lose_interest_timer = ENEMY_LOSE_INTEREST_TIME

    def _handle_bullet_collisions(self):
        for bullet in list(self.bullets):
            if pygame.sprite.spritecollideany(bullet, self.obstacles):
                bullet.kill()
                continue

            if bullet.is_enemy_bullet:
                if bullet.rect.colliderect(self.player.rect) and not self.player.is_hidden:
                    damage_to_deal = bullet.damage
                    if self.player.armor > 0:
                        absorption = int(damage_to_deal * 0.6)
                        if self.player.armor >= absorption:
                            self.player.armor -= absorption
                            damage_to_deal -= absorption
                        else:
                            damage_to_deal -= self.player.armor
                            self.player.armor = 0
                    self.player.hp -= damage_to_deal
                    if self.player.hp <= 0: self.game_state = "GAME_OVER"
                    bullet.kill()
            else:
                hit_enemies = pygame.sprite.spritecollide(bullet, self.enemies, False)
                for enemy in hit_enemies:
                    damage_to_deal = bullet.damage
                    if enemy.armor > 0:
                        absorption = int(damage_to_deal * 0.5)
                        if enemy.armor >= absorption:
                            enemy.armor -= absorption
                            damage_to_deal -= absorption
                        else:
                            damage_to_deal -= enemy.armor
                            enemy.armor = 0
                    enemy.hp -= damage_to_deal
                    enemy.is_alerted = True
                    enemy.last_known_player_pos = pygame.math.Vector2(self.player.pos)
                    bullet.kill()
                    if enemy.hp <= 0: enemy.kill()

    def update(self):
        if self.game_state != "PLAYING":
            return

        keys = pygame.key.get_pressed()
        self.player.update(keys, self.obstacles, self.camera)

        self._handle_attacks()
        self.bullets.update()
        self.enemies.update(self.player, self.game_matrix, self.obstacles)

        for enemy in self.enemies:
            if enemy.fired_bullet:
                self.bullets.add(enemy.fired_bullet)
                self.all_sprites.add(enemy.fired_bullet)

        self._check_environmental_sounds()
        self._handle_bullet_collisions()

        if len(self.enemies) == 0:
            self.game_state = "VICTORY"

    def draw(self):
        if self.game_state == "MENU":
            self.screen.fill((15, 20, 30))
            title = self.pause_font_title.render("STEALTH ACTION", True, (0, 150, 255))
            self.screen.blit(title, title.get_rect(center=(SCREEN_WIDTH // 2, SCREEN_HEIGHT // 2 - 120)))
            for btn in self.main_menu_buttons: btn.draw(self.screen)
            return

        if self.game_state == "PLAYING":
            self.camera.update(self.player)

        self.screen.fill(BG_COLOR)

        for enemy in self.enemies:
            enemy.draw_vision_cone(self.screen, self.camera)

        # Рендеринг ефектів (винесено розрахунки згасання)
        if self.gunshot_visual_timer > 0:
            draw_gunshot_flash(self.screen, self.camera, self.gunshot_visual_pos, self.gunshot_visual_radius,
                               self.gunshot_visual_timer)
            if self.game_state == "PLAYING": self.gunshot_visual_timer -= 1

        if self.knife_visual_timer > 0:
            draw_knife_swing(self.screen, self.camera, self.player, self.knife_attack_radius)
            if self.game_state == "PLAYING": self.knife_visual_timer -= 1

        # Радіус кроків навколо гравця
        if self.player.current_noise_radius > 0 and not self.player.is_hidden:
            noise_pos = (
            int(self.player.pos.x + self.camera.camera_rect.x), int(self.player.pos.y + self.camera.camera_rect.y))
            color = (255, 100, 100) if self.player.current_noise_radius > 40 else (0, 150, 255)
            pygame.draw.circle(self.screen, color, noise_pos, int(self.player.current_noise_radius), 1)

        # Рендеринг об'єктів сцени
        for sprite in self.all_sprites:
            if sprite == self.player and self.player.is_hidden: continue
            self.screen.blit(sprite.image, self.camera.apply(sprite))

        for enemy in self.enemies:
            enemy.draw_health_bar(self.screen, self.camera)
            enemy.draw_suspicion_bar(self.screen, self.camera)

        for bullet in self.bullets:
            self.screen.blit(bullet.image, self.camera.apply(bullet))

        # UI
        draw_player_bars(self.screen, self.player, self.pause_font_btn)
        draw_game_ui(self.screen, self.player, self.enemies, pygame.key.get_pressed(), self.pause_font_btn)

        if self.game_state == "PLAYING":
            draw_controls_help(self.screen, self.pause_font_btn)

        self._draw_overlay_menus()

    def _draw_overlay_menus(self):
        """Рендеринг модальних вікон станів гри"""
        if self.game_state not in ["PAUSE", "GAME_OVER", "VICTORY"]: return

        menu_w, menu_h = 340, 380 if self.game_state == "PAUSE" else 260
        m_rect = pygame.Rect(SCREEN_WIDTH // 2 - menu_w // 2, SCREEN_HEIGHT // 2 - menu_h // 2, menu_w, menu_h)

        colors = {
            "PAUSE": ((25, 30, 40), (0, 150, 255), "ПАУЗА", self.pause_buttons),
            "GAME_OVER": ((30, 20, 20), (255, 50, 50), "ВИ ЗГИНУЛИ", self.game_over_buttons),
            "VICTORY": ((20, 35, 25), (50, 255, 100), "ПЕРЕМОГА!", self.victory_buttons)
        }
        bg_c, border_c, title_text, buttons = colors[self.game_state]

        pygame.draw.rect(self.screen, bg_c, m_rect, border_radius=12)
        pygame.draw.rect(self.screen, border_c, m_rect, width=2, border_radius=12)

        title_surf = self.pause_font_title.render(title_text, True, border_c)
        self.screen.blit(title_surf, title_surf.get_rect(center=(SCREEN_WIDTH // 2, m_rect.top + 40)))

        for btn in buttons: btn.draw(self.screen)

    def run(self):
        while self.running:
            self.handle_events()
            self.update()
            self.draw()
            pygame.display.flip()
            self.clock.tick(FPS)