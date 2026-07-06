# src/core/game.py
import pygame
import random
from src.settings import (
    SCREEN_WIDTH, SCREEN_HEIGHT, FPS, BG_COLOR,
    WEAPONS, WORLD_WIDTH, WORLD_HEIGHT
)
from src.core.ui import (
    draw_controls_help, draw_player_bars, draw_game_ui,
    draw_gunshot_flash, draw_knife_swing, UIButton
)
from src.core.crosshair import CrosshairController
from src.core.camera import Camera

# Підключення всіх менеджерів підсистем
from src.core.mission_manager import MissionManager
from src.core.collision_manager import CollisionManager
from src.core.level_manager import LevelManager
from src.core.input_handler import InputHandler


class Game:
    def __init__(self, screen):
        """Ініціалізація головного ігрового ядра, менеджерів станів та підсистем"""
        self.screen = screen
        self.clock = pygame.time.Clock()
        self.game_state = "MENU"
        self.running = True

        # Створення груп спрайтів (керуються через LevelManager)
        self.player = None
        self.all_sprites = pygame.sprite.Group()
        self.bullets = pygame.sprite.Group()
        self.enemies = pygame.sprite.Group()
        self.obstacles = pygame.sprite.Group()
        self.hiding_spots = pygame.sprite.Group()
        self.game_matrix = None

        self.camera = Camera(WORLD_WIDTH, WORLD_HEIGHT)

        # Пам'ять карти
        self.saved_game_matrix = None
        self.saved_hiding_spots_data = []

        # Візуальні ефекти
        self.gunshot_visual_timer = 0
        self.gunshot_visual_pos = (0, 0)
        self.gunshot_visual_radius = 0

        self.knife_visual_timer = 0
        self.knife_visual_pos = (0, 0)
        self.knife_attack_radius = WEAPONS["knife"].get("damage_radius", 60)

        pygame.font.init()
        self.pause_font_title = pygame.font.SysFont("Arial", 48, bold=True)
        self.pause_font_btn = pygame.font.SysFont("Arial", 22, bold=True)
        # НОВИЙ ШРИФТ: Створюємо компактний шрифт для тексту всередині ХП та Броні
        self.hud_small_font = pygame.font.SysFont("Arial", 14, bold=True)

        # Ініціалізація менеджерів
        self.levels = LevelManager(self)
        self.missions = MissionManager(self)
        self.collision_ctrl = CollisionManager(self)
        self.crosshair_ctrl = CrosshairController()
        self.inputs = InputHandler(self)

        self._init_ui_buttons()
        self.frame_counter = 0

    def _init_ui_buttons(self):
        """Ініціалізація інтерактивних UI кнопок для всіх типів екранів меню"""
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
            UIButton(cx, cy + 20, 260, 45, "НАСТУПНА МІСІЯ", self.pause_font_btn, green_b, green_h, "NEXT_MISSION"),
            UIButton(cx, cy + 80, 260, 45, "ГОЛОВНЕ МЕНЮ", self.pause_font_btn, b_color, h_color, "MAIN_MENU")
        ]

        self.victory_all_buttons = [
            UIButton(cx, cy - 30, 260, 45, "ПОЧАТИ ЗНОВУ", self.pause_font_btn, green_b, green_h, "RESTART_FIRST"),
            UIButton(cx, cy + 30, 260, 45, "ГОЛОВНЕ МЕНЮ", self.pause_font_btn, b_color, h_color, "MAIN_MENU"),
            UIButton(cx, cy + 90, 260, 45, "ВИЙТИ З ГРИ", self.pause_font_btn, red_b, red_h, "QUIT")
        ]

    def execute_knife_attack(self):
        """Розрахунок сектору ураження ближнього бою гравця при використанні ножа"""
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
                    from src.settings import ENEMY_LOSE_INTEREST_TIME
                    enemy.lose_interest_timer = ENEMY_LOSE_INTEREST_TIME

                    if enemy.hp <= 0: enemy.kill()

    def _handle_attacks(self):
        """Перевірка стану тригерів атаки гравця та генерація снарядів/колізій ножа"""
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
        """Сканування світу на звукові радіуси шуму від ніг або куль"""
        if self.player.current_noise_radius <= 0 or self.player.is_hidden:
            return

        for enemy in self.enemies:
            if enemy.pos.distance_to(self.player.pos) <= self.player.current_noise_radius:
                enemy.is_alerted = True
                enemy.last_known_player_pos = pygame.math.Vector2(self.player.pos)
                from src.settings import ENEMY_LOSE_INTEREST_TIME
                enemy.lose_interest_timer = ENEMY_LOSE_INTEREST_TIME

    def update(self):
        """Щокадрове оновлення станів ігрових об'єктів та обчислення логіки симуляції"""
        self.crosshair_ctrl.update(self.player, self.camera, self.knife_attack_radius, self.game_state)

        if self.game_state != "PLAYING":
            return

        self.frame_counter += 1

        keys = pygame.key.get_pressed()
        self.player.update(keys, self.obstacles, self.camera)

        self._handle_attacks()
        self.bullets.update()

        # Оптимізований апдейт ШІ (AI Throttling)
        update_bound = pygame.Rect(
            -self.camera.camera_rect.x - 200, -self.camera.camera_rect.y - 200,
            SCREEN_WIDTH + 400, SCREEN_HEIGHT + 400
        )

        for enemy in self.enemies:
            if update_bound.colliderect(enemy.rect) or enemy.is_alerted:
                enemy.update(self.player, self.game_matrix, self.obstacles)
            elif (self.frame_counter + id(enemy)) % 6 == 0:
                enemy.update(self.player, self.game_matrix, self.obstacles)

        # Створення куль для ворогів
        for enemy in self.enemies:
            if enemy.fired_bullet:
                if enemy.pos.distance_to(self.player.pos) <= 35:
                    enemy.fired_bullet = None
                    continue
                self.bullets.add(enemy.fired_bullet)
                self.all_sprites.add(enemy.fired_bullet)

        self._check_environmental_sounds()
        self.collision_ctrl.handle_all_collisions()
        self.missions.check_mission_conditions(self.frame_counter)

    def draw(self):
        """Оптимізований рендеринг графічних шарів із відсіканням (Culling) об'єктів поза екраном"""
        if self.game_state == "MENU":
            self.screen.fill((15, 20, 30))
            title = self.pause_font_title.render("STEALTH ACTION", True, (0, 150, 255))
            self.screen.blit(title, title.get_rect(center=(SCREEN_WIDTH // 2, SCREEN_HEIGHT // 2 - 120)))
            for btn in self.main_menu_buttons: btn.draw(self.screen)
            return

        if self.game_state == "PLAYING":
            self.camera.update(self.player)

        self.screen.fill(BG_COLOR)
        screen_bound = pygame.Rect(-self.camera.camera_rect.x, -self.camera.camera_rect.y, SCREEN_WIDTH, SCREEN_HEIGHT)

        # 1. Конуси зору ШІ
        for enemy in self.enemies:
            if screen_bound.colliderect(enemy.rect):
                enemy.draw_vision_cone(self.screen, self.camera)

        # 2. Шар спалахів
        if self.gunshot_visual_timer > 0:
            draw_gunshot_flash(self.screen, self.camera, self.gunshot_visual_pos, self.gunshot_visual_radius,
                               self.gunshot_visual_timer)
            if self.game_state == "PLAYING": self.gunshot_visual_timer -= 1

        if self.knife_visual_timer > 0:
            draw_knife_swing(self.screen, self.camera, self.player, self.knife_attack_radius)
            if self.game_state == "PLAYING": self.knife_visual_timer -= 1

        # 3. Радіус звуку кроків
        if self.player.current_noise_radius > 0 and not self.player.is_hidden:
            noise_pos = (
                int(self.player.pos.x + self.camera.camera_rect.x), int(self.player.pos.y + self.camera.camera_rect.y))
            color = (255, 100, 100) if self.player.current_noise_radius > 40 else (0, 150, 255)
            pygame.draw.circle(self.screen, color, noise_pos, int(self.player.current_noise_radius), 1)

        # 4. Рендеринг видимих об'єктів (Frustum Culling)
        for sprite in self.all_sprites:
            if sprite == self.player and self.player.is_hidden: continue
            if not screen_bound.colliderect(sprite.rect): continue
            self.screen.blit(sprite.image, self.camera.apply(sprite))

        # 5. Індикатори ворогів та кулі
        for enemy in self.enemies:
            if screen_bound.colliderect(enemy.rect):
                enemy.draw_health_bar(self.screen, self.camera)
                enemy.draw_suspicion_bar(self.screen, self.camera)

        for bullet in list(self.bullets):
            if screen_bound.colliderect(bullet.rect):
                self.screen.blit(bullet.image, self.camera.apply(bullet))

        # 6. Панелі HUD
        # ВИПРАВЛЕНО: передаємо новий маленький шрифт hud_small_font замість великого pause_font_btn
        draw_player_bars(self.screen, self.player, self.hud_small_font)
        draw_game_ui(self.screen, self.player, self.enemies, pygame.key.get_pressed(), self.pause_font_btn)

        if self.game_state == "PLAYING":
            draw_controls_help(self.screen, self.pause_font_btn)

            # Текст місій через менеджер місій
            mission_title = self.pause_font_btn.render(self.missions.cfg['title'], True, (255, 200, 0))
            self.screen.blit(mission_title, (20, 90))

            status_text = ""
            if self.missions.cfg["type"] == "STEALTH_ESCAPE":
                status_text = "Ціль: Дістатися виходу (НЕ ПРИВЕРТАЙ УВАГУ)"
            elif self.missions.cfg["type"] == "ELIMINATION":
                status_text = f"Ціль: Знищити всіх ({len(self.enemies)} залишилось)"
            elif self.missions.cfg["type"] == "DATA_HEIST":
                data_status = "ЗІБРАНО" if self.missions.data_collected else "ШУКАЙТЕ"
                status_text = f"Документи: {data_status} | Ціль: Евакуація"

            status_surf = self.pause_font_btn.render(status_text, True, (0, 200, 255))
            self.screen.blit(status_surf, (20, 115))

        # 7. Приціл та меню оверлею
        if self.game_state == "PLAYING":
            self.crosshair_ctrl.draw(self.screen, self.player)

        self._draw_overlay_menus()

    def _draw_overlay_menus(self):
        """Рендеринг модальних контекстних вікон для відображення системних станів гри"""
        if self.game_state not in ["PAUSE", "GAME_OVER", "VICTORY", "VICTORY_ALL"]: return

        # ВИПРАВЛЕНО: Якщо це екран фіналу кампанії (VICTORY_ALL), робимо рамку ширшою (420 замість 340)
        if self.game_state == "VICTORY_ALL":
            menu_w, menu_h = 420, 380
        else:
            menu_w, menu_h = 340, 380 if self.game_state == "PAUSE" else 260

        m_rect = pygame.Rect(SCREEN_WIDTH // 2 - menu_w // 2, SCREEN_HEIGHT // 2 - menu_h // 2, menu_w, menu_h)

        colors = {
            "PAUSE": ((25, 30, 40), (0, 150, 255), "ПАУЗА", self.pause_buttons),
            "GAME_OVER": ((30, 20, 20), (255, 50, 50), "ВИ ЗГИНУЛИ", self.game_over_buttons),
            "VICTORY": ((20, 35, 25), (50, 255, 100), "ПЕРЕМОГА!", self.victory_buttons),
            "VICTORY_ALL": ((20, 35, 40), (0, 255, 200), "ГРУ ПРОЙДЕНО!", self.victory_all_buttons)
        }
        bg_c, border_c, title_text, buttons = colors[self.game_state]

        pygame.draw.rect(self.screen, bg_c, m_rect, border_radius=12)
        pygame.draw.rect(self.screen, border_c, m_rect, width=2, border_radius=12)

        title_surf = self.pause_font_title.render(title_text, True, border_c)
        self.screen.blit(title_surf, title_surf.get_rect(center=(SCREEN_WIDTH // 2, m_rect.top + 40)))

        for btn in buttons: btn.draw(self.screen)

    def run(self):
        """Головний нескінченний цикл виконання додатку"""
        while self.running:
            self.inputs.handle_events()
            self.update()
            self.draw()
            pygame.display.flip()
            self.clock.tick(FPS)
