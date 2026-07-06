# src/core/game.py
import pygame
import random
from src.settings import (
    SCREEN_WIDTH, SCREEN_HEIGHT, FPS, BG_COLOR, TILE_SIZE,
    ENEMY_LOSE_INTEREST_TIME, ENEMY_TYPES, WEAPONS,
    WORLD_WIDTH, WORLD_HEIGHT, MISSION_CONFIGS
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
from src.core.crosshair import CrosshairController
from src.core.camera import Camera
from src.objects.mission_elements import ExitZone, DataDrive


class Game:
    def __init__(self, screen):
        """Ініціалізація головного ігрового ядра, менеджерів станів та ресурсів"""
        self.screen = screen
        self.clock = pygame.time.Clock()
        self.game_state = "MENU"
        self.running = True

        # Створення груп спрайтів для рендерингу та колізій
        self.player = None
        self.all_sprites = pygame.sprite.Group()
        self.bullets = pygame.sprite.Group()
        self.enemies = pygame.sprite.Group()
        self.obstacles = pygame.sprite.Group()
        self.hiding_spots = pygame.sprite.Group()
        self.game_matrix = None

        # Камера, яка слідує за гравцем у межах світу
        self.camera = Camera(WORLD_WIDTH, WORLD_HEIGHT)

        # Пам'ять карти для перезапуску поточного генераційного пресету
        self.saved_game_matrix = None
        self.saved_hiding_spots_data = []

        # Візуальні ефекти та їхні таймери згасання
        self.gunshot_visual_timer = 0
        self.gunshot_visual_pos = (0, 0)
        self.gunshot_visual_radius = 0

        self.knife_visual_timer = 0
        self.knife_visual_pos = (0, 0)
        self.knife_attack_radius = WEAPONS["knife"].get("damage_radius", 60)

        # Ініціалізація системних шрифтів Pygame
        pygame.font.init()
        self.pause_font_title = pygame.font.SysFont("Arial", 48, bold=True)
        self.pause_font_btn = pygame.font.SysFont("Arial", 22, bold=True)

        # Ініціалізація груп завдань та стану місії
        self.exit_zones = pygame.sprite.Group()
        self.data_drives = pygame.sprite.Group()
        self.current_mission_num = 1
        self.data_collected = False
        self.cfg = MISSION_CONFIGS[1]  # Тимчасова заглушка

        self._init_ui_buttons()
        self.crosshair_ctrl = CrosshairController()

        # Початковий запуск першої місії
        self.load_mission(self.current_mission_num)

        # Лічильник кадрів для оптимізації тиків ШІ та місій
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

    def load_mission(self, mission_num):
        """Завантаження конфігурації конкретної місії та генерація сцени під неї"""
        if mission_num > len(MISSION_CONFIGS):
            self.game_state = "MENU"  # Усі місії пройдено!
            self.current_mission_num = 1  # Скидаємо лічильник для майбутнього старту
            return

        self.current_mission_num = mission_num
        self.data_collected = False
        self.cfg = MISSION_CONFIGS[mission_num]

        # Скидаємо гру та генеруємо нову карту під параметри рівня
        self.reset_game(new_map=True, new_level=True)
        self.spawn_mission_objectives()

    def spawn_mission_objectives(self):
        """Пошук підходящих точок на мапі та спавн квестових об'єктів місії"""
        self.exit_zones.empty()
        self.data_drives.empty()

        free_tiles = []
        for r_idx, row in enumerate(self.game_matrix):
            for c_idx, val in enumerate(row):
                if val == 1:
                    pos_x = c_idx * TILE_SIZE
                    pos_y = r_idx * TILE_SIZE
                    # Об'єкти місії не повинні спавнитися на голові у гравця
                    if pygame.math.Vector2(pos_x, pos_y).distance_to(self.player.pos) > 200:
                        free_tiles.append((pos_x, pos_y))

        random.shuffle(free_tiles)

        if "escape" in self.cfg["objectives"] and free_tiles:
            ex, ey = free_tiles.pop()
            exit_node = ExitZone(ex, ey)
            self.exit_zones.add(exit_node)
            self.all_sprites.add(exit_node)

        if "collect_data" in self.cfg["objectives"] and free_tiles:
            dx, dy = free_tiles.pop()
            drive = DataDrive(dx, dy)
            self.data_drives.add(drive)
            self.all_sprites.add(drive)

    def reset_game(self, new_map=True, new_level=False):
        """Повне або часткове скидання стану сцени для перезапуску або переходу на новий рівень"""
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

        # Побудова фізичних стін (Obstacles)
        for r_idx, row in enumerate(self.game_matrix):
            for c_idx, val in enumerate(row):
                if val == 0:
                    wall = Obstacle(c_idx * TILE_SIZE, r_idx * TILE_SIZE, TILE_SIZE, TILE_SIZE)
                    self.obstacles.add(wall)
                    self.all_sprites.add(wall)

        # Розміщення інтерактивних точок приховування (Hiding Spots)
        for pos_x, pos_y in self.saved_hiding_spots_data:
            spot = HidingSpot(pos_x, pos_y, TILE_SIZE, TILE_SIZE)
            self.hiding_spots.add(spot)
            self.all_sprites.add(spot)

        # Розрахунок та спавн ворожих юнітів
        num_enemies = random.randint(4, 6) if new_level else random.randint(2, 4)
        spawn_positions = MapGenerator.get_enemy_spawn_positions(
            self.game_matrix, self.saved_hiding_spots_data, self.player.pos, count=num_enemies
        )

        enemy_types_available = list(ENEMY_TYPES.keys())
        for pos_x, pos_y in spawn_positions:
            chosen_type = random.choice(enemy_types_available)
            enemy = Enemy(pos_x, pos_y, chosen_type, game_matrix=self.game_matrix)
            enemy.melee_cooldown = 0
            self.enemies.add(enemy)
            self.all_sprites.add(enemy)

    def handle_events(self):
        """Обробка глобальних системних подій операційної системи та введення користувача"""
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
        """Обробка гарячих клавіш керування безпосередньо під час ігрового процесу"""
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
                self.spawn_mission_objectives()  # Обов'язково оновлюємо цілі при швидкому рестарті!
            elif event.key == pygame.K_e:
                if self.player.is_hidden:
                    self.player.is_hidden = False
                else:
                    hit_spot = pygame.sprite.spritecollideany(self.player, self.hiding_spots)
                    if hit_spot:
                        self.player.is_hidden = True
                        self.player.pos = pygame.math.Vector2(hit_spot.rect.center)

    def _handle_menu_inputs(self, event):
        """Обробка натискань клавіатури в інтерфейсах меню, екранах поразки чи перемоги"""
        if event.type == pygame.KEYDOWN:
            if self.game_state == "MENU":
                if event.key in [pygame.K_1, pygame.K_SPACE]:
                    self.load_mission(1)
                    self.game_state = "PLAYING"
                elif event.key == pygame.K_ESCAPE:
                    self.running = False
            elif self.game_state == "GAME_OVER":
                if event.key == pygame.K_r:
                    self.reset_game(new_map=False, new_level=False)
                    self.spawn_mission_objectives()
                    self.game_state = "PLAYING"
                elif event.key == pygame.K_SPACE:
                    self.load_mission(self.current_mission_num)
                    self.game_state = "PLAYING"
                elif event.key in [pygame.K_m, pygame.K_ESCAPE]:
                    self.game_state = "MENU"
            elif self.game_state == "VICTORY":
                if event.key == pygame.K_SPACE:
                    self.load_mission(self.current_mission_num + 1)
                    self.game_state = "PLAYING"
                elif event.key in [pygame.K_m, pygame.K_ESCAPE]:
                    self.game_state = "MENU"
            elif self.game_state == "PAUSE" and event.key == pygame.K_ESCAPE:
                self.game_state = "PLAYING"

    def _update_ui_button_actions(self, mouse_pos, mouse_click):
        """Обробка кліків миші по активних кнопках поточного стану графічного інтерфейсу"""
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
            if action == "START":
                self.load_mission(1)
                self.game_state = "PLAYING"
            elif action == "CONTINUE":
                self.game_state = "PLAYING"
            elif action == "RESTART":
                self.load_mission(self.current_mission_num)
                self.game_state = "PLAYING"
            elif action == "NEXT_MISSION":
                self.load_mission(self.current_mission_num + 1)
                self.game_state = "PLAYING"
            elif action == "MAIN_MENU":
                self.game_state = "MENU"
            elif action == "QUIT":
                self.running = False

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
                    enemy.lose_interest_timer = ENEMY_LOSE_INTEREST_TIME

                    if enemy.hp <= 0: enemy.kill()

    def _handle_attacks(self):
        """Перевірка стану тригерів атаки гравця (ЛКМ) та генерація відповідних снарядів або колізій ножа"""
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
        """Сканування світу на звукові радіуси шуму: привернення уваги ШІ кроками або пострілами"""
        # ОПТИМІЗАЦІЯ: Якщо шуму немає або гравець сховався, взагалі не перевіряємо ворогів
        if self.player.current_noise_radius <= 0 or self.player.is_hidden:
            return

        for enemy in self.enemies:
            if enemy.pos.distance_to(self.player.pos) <= self.player.current_noise_radius:
                enemy.is_alerted = True
                enemy.last_known_player_pos = pygame.math.Vector2(self.player.pos)
                enemy.lose_interest_timer = ENEMY_LOSE_INTEREST_TIME

    def _handle_collisions(self):
        """Фізичний менеджер колізій: обробка куль, влучань, а також квестових механік місій"""

        # --- МЕХАНІКА КОНТАКТНОГО БОЮ ШІ (ВЛУЧАННЯ ВПРИТУЛ) ---
        for enemy in self.enemies:
            if hasattr(enemy, "melee_cooldown") and enemy.melee_cooldown > 0:
                enemy.melee_cooldown -= 1

            if enemy.is_alerted and not self.player.is_hidden:
                dist_to_player = enemy.pos.distance_to(self.player.pos)
                if dist_to_player <= 35:
                    if getattr(enemy, "melee_cooldown", 0) == 0:
                        self.player.hp -= 10
                        enemy.melee_cooldown = 60  # 1 секунда кулдауну

                        push_dir = self.player.pos - enemy.pos
                        push_dir = push_dir.normalize() if push_dir.length() > 0 else pygame.math.Vector2(1, 0)

                        old_pos = pygame.math.Vector2(self.player.pos)
                        self.player.pos += push_dir * 45
                        self.player.rect.center = (int(self.player.pos.x), int(self.player.pos.y))

                        if pygame.sprite.spritecollideany(self.player, self.obstacles):
                            self.player.pos = old_pos
                            self.player.rect.center = (int(self.player.pos.x), int(self.player.pos.y))

                        if self.player.hp <= 0:
                            self.game_state = "GAME_OVER"
                        print("Ворог штовхнув вас прикладом!")

        # --- ЛОГІКА МІСІЙ ТА ЗАВДАНЬ ---

        # 1. Перевірка на провал стелсу (ОПТИМІЗОВАНО: перевіряємо лише раз на 10 кадрів)
        if self.frame_counter % 10 == 0 and self.cfg.get("fail_on_alert", False):
            for enemy in self.enemies:
                if enemy.is_alerted:
                    self.game_state = "GAME_OVER"
                    print("Провал: Вас виявили!")
                    break

        # 2. Збір квестових даних (ОПТИМІЗОВАНО: перевіряємо раз на 5 кадрів)
        if self.frame_counter % 5 == 0 and "collect_data" in self.cfg["objectives"] and not self.data_collected:
            hit_drive = pygame.sprite.spritecollideany(self.player, self.data_drives)
            if hit_drive:
                self.data_collected = True
                hit_drive.kill()
                print("Дані успішно зібрано!")

        # 3. Перевірка зони евакуації (ОПТИМІЗОВАНО: перевіряємо раз на 5 кадрів)
        if self.frame_counter % 5 == 0 and "escape" in self.cfg["objectives"]:
            if pygame.sprite.spritecollideany(self.player, self.exit_zones):
                can_escape = True
                if "collect_data" in self.cfg["objectives"] and not self.data_collected:
                    can_escape = False

                if can_escape:
                    self.game_state = "VICTORY"
                    print(f"Місію {self.current_mission_num} виконано!")

        # 4. Перевірка зачистки сектору (ОПТИМІЗОВАНО: перевіряємо раз на 15 кадрів)
        if self.frame_counter % 15 == 0 and "kill_all" in self.cfg["objectives"] and len(self.enemies) == 0:
            self.game_state = "VICTORY"
            print(f"Сектор повністю очищено. Місію {self.current_mission_num} виконано!")

        # --- КЛАСИЧНА ОБРОБКА КУЛЬ (залишаємо кожен кадр, бо кулі швидкі) ---
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
        """Щокадрове оновлення станів ігрових об'єктів та обчислення логіки симуляції"""
        self.crosshair_ctrl.update(self.player, self.camera, self.knife_attack_radius, self.game_state)

        if self.game_state != "PLAYING":
            return

        # Інкрементуємо лічильник кадрів
        self.frame_counter += 1

        keys = pygame.key.get_pressed()
        self.player.update(keys, self.obstacles, self.camera)

        self._handle_attacks()
        self.bullets.update()

        # --- ОПТИМІЗОВАНИЙ АПДЕЙТ ШІ (AI THROTTLING) ---
        # Визначаємо збільшену зону навколо екрана (запас 200 пікселів), щоб вороги не «замерзали» прямо на межі екрана
        update_bound = pygame.Rect(
            -self.camera.camera_rect.x - 200,
            -self.camera.camera_rect.y - 200,
            SCREEN_WIDTH + 400,
            SCREEN_HEIGHT + 400
        )

        for enemy in self.enemies:
            # Якщо ворог близько або він наляканий — оновлюємо КОЖЕН кадр
            if update_bound.colliderect(enemy.rect) or enemy.is_alerted:
                enemy.update(self.player, self.game_matrix, self.obstacles)
            # Якщо він далеко і спокійний — оновлюємо його лише раз на 6 кадрів (розподіляємо по id)
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
        self._handle_collisions()

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

        # Створюємо рект екрана в координатах світу для відсікання (Culling)
        # Все, що не перетинається з цим прямокутником, не малюється!
        screen_bound = pygame.Rect(-self.camera.camera_rect.x, -self.camera.camera_rect.y, SCREEN_WIDTH, SCREEN_HEIGHT)

        # 1. Шар конусів зору ШІ (малюємо тільки якщо ворог на екрані)
        for enemy in self.enemies:
            if screen_bound.colliderect(enemy.rect):
                enemy.draw_vision_cone(self.screen, self.camera)

        # 2. Шар спалахів та ефектів атаки зброї
        if self.gunshot_visual_timer > 0:
            draw_gunshot_flash(self.screen, self.camera, self.gunshot_visual_pos, self.gunshot_visual_radius,
                               self.gunshot_visual_timer)
            if self.game_state == "PLAYING": self.gunshot_visual_timer -= 1

        if self.knife_visual_timer > 0:
            draw_knife_swing(self.screen, self.camera, self.player, self.knife_attack_radius)
            if self.game_state == "PLAYING": self.knife_visual_timer -= 1

        # 3. Радіус звуку кроків навколо гравця
        if self.player.current_noise_radius > 0 and not self.player.is_hidden:
            noise_pos = (
                int(self.player.pos.x + self.camera.camera_rect.x),
                int(self.player.pos.y + self.camera.camera_rect.y)
            )
            color = (255, 100, 100) if self.player.current_noise_radius > 40 else (0, 150, 255)
            pygame.draw.circle(self.screen, color, noise_pos, int(self.player.current_noise_radius), 1)

        # 4. ОПТИМІЗОВАНИЙ РЕНДЕРИНГ: Малюємо тільки те, що бачить камера
        for sprite in self.all_sprites:
            if sprite == self.player and self.player.is_hidden:
                continue
            # Якщо це стіна або інший об'єкт, і він поза екраном — пропускаємо blit
            if not screen_bound.colliderect(sprite.rect):
                continue
            self.screen.blit(sprite.image, self.camera.apply(sprite))

        # 5. Індикатори стану ворогів поверх їхніх текстур
        for enemy in self.enemies:
            if screen_bound.colliderect(enemy.rect):
                enemy.draw_health_bar(self.screen, self.camera)
                enemy.draw_suspicion_bar(self.screen, self.camera)

        for bullet in self.bullets:
            if screen_bound.colliderect(bullet.rect):
                self.screen.blit(bullet.image, self.camera.apply(bullet))

        # 6. Статичні панелі HUD та підказки UI (вони завжди на екрані)
        draw_player_bars(self.screen, self.player, self.pause_font_btn)
        draw_game_ui(self.screen, self.player, self.enemies, pygame.key.get_pressed(), self.pause_font_btn)

        if self.game_state == "PLAYING":
            draw_controls_help(self.screen, self.pause_font_btn)

            # ВІДОБРАЖЕННЯ ТЕКСТУ МІСІЇ ТА ЗАВДАНЬ
            mission_title = self.pause_font_btn.render(self.cfg['title'], True, (255, 200, 0))
            self.screen.blit(mission_title, (20, 20))

            status_text = ""
            if self.cfg["type"] == "STEALTH_ESCAPE":
                status_text = "Ціль: Дістатися виходу (НЕ ПРИВЕРТАЙ УВАГУ)"
            elif self.cfg["type"] == "ELIMINATION":
                status_text = f"Ціль: Знищити всіх ({len(self.enemies)} залишилось)"
            elif self.cfg["type"] == "DATA_HEIST":
                data_status = "ЗІБРАНО" if self.data_collected else "ШУКАЙТЕ"
                status_text = f"Документи: {data_status} | Ціль: Евакуація"

            status_surf = self.pause_font_btn.render(status_text, True, (0, 200, 255))
            self.screen.blit(status_surf, (20, 45))

        # 7. Шар кастомного прицілу
        if self.game_state == "PLAYING":
            self.crosshair_ctrl.draw(self.screen, self.player)

        # 8. Оверлей модальних меню
        self._draw_overlay_menus()

    def _draw_overlay_menus(self):
        """Рендеринг модальних контекстних вікон для відображення системних станів гри"""
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
        """Головний нескінченний цикл виконання додатку з фіксацією кадрової частоти (FPS)"""
        while self.running:
            self.handle_events()
            self.update()
            self.draw()
            pygame.display.flip()
            self.clock.tick(FPS)