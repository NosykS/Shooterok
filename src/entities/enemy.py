# src/entities/enemy.py
import pygame
import math
import random
from pathfinding.core.grid import Grid
from pathfinding.finder.a_star import AStarFinder
from pathfinding.core.diagonal_movement import DiagonalMovement
from src.settings import (
    ENEMY_TYPES, TILE_SIZE, ENEMY_LOSE_INTEREST_TIME,
    WEAPONS, WORLD_WIDTH, WORLD_HEIGHT, SCREEN_WIDTH, SCREEN_HEIGHT
)
from src.objects.bullet import Bullet
from src.core.physics import get_nearby_obstacles, resolve_axis_collision


class Enemy(pygame.sprite.Sprite):
    def __init__(self, x, y, enemy_type="rookie", game_matrix=None, custom_patrol=None):
        """Ініціалізація сутності ворога, його базових характеристик, пресетів зброї та маршруту"""
        super().__init__()
        self.type = enemy_type
        self.stats = ENEMY_TYPES[enemy_type]

        # Життєві показники та захист
        self.hp = self.stats["hp"]
        self.max_hp = self.stats["hp"]
        self.speed = self.stats["speed"]
        self.color = self.stats["color"]
        self.armor = self.stats["armor"]
        self.max_armor = self.stats["armor"]

        # Озброєння та бойові таймери
        self.weapon = self.stats["weapon"]
        self.shoot_cooldown = 0
        self.melee_cooldown = 0  # Внутрішній таймер кулдауну для атак ближнього бою

        # Базові конфігураційні параметри зору
        self.base_view_radius = self.stats["view_radius"]
        self.base_view_angle = self.stats["view_angle"]

        # Динамічні поточні параметри зору (змінюються в стані тривоги)
        self.view_radius = self.base_view_radius
        self.view_angle = self.base_view_angle

        # Завантаження справжнього спрайту ворога замість геометричної заглушки
        self.base_image = self._load_enemy_image()
        self.image = self.base_image.copy()

        # Рівняємо початкову позицію ворога чітко по центру тайла спавну!
        tile_x = int(x // TILE_SIZE)
        tile_y = int(y // TILE_SIZE)
        center_x = tile_x * TILE_SIZE + TILE_SIZE // 2
        center_y = tile_y * TILE_SIZE + TILE_SIZE // 2

        self.pos = pygame.math.Vector2(center_x, center_y)
        self.rect = self.image.get_rect(center=self.pos)

        # Зменшено розмір хітбоксу для більш гладкого проходу через двері та кути
        self.hitbox = pygame.Rect(0, 0, 18, 18)
        self.hitbox.center = self.pos

        # Стартовий випадковий вектор повороту
        self.rotation_vector = pygame.math.Vector2(1, 0).rotate(random.randint(0, 360))
        self.is_alerted = False

        # Система накопичення підозри (Стелс механіка)
        self.suspicion = 0.0  # Поточний рівень від 0.0 (чисто) до 1.0 (тривога)
        self.suspicion_speed = 1.5  # Множник швидкості накопичення підозри
        self.cool_down_speed = 0.8  # Швидкість заспокоєння, коли гравець зник

        # Координати останньої фіксації цілі
        self.last_known_player_pos = None
        self.lose_interest_timer = ENEMY_LOSE_INTEREST_TIME

        # Логіка патрулювання території
        self.patrol_points = []
        self.current_patrol_idx = 0
        self.patrol_wait_timer = 0

        if custom_patrol:
            # Якщо передано готові координати маршруту
            for pt in custom_patrol:
                self.patrol_points.append(pygame.math.Vector2(pt[0], pt[1]))
        elif game_matrix:
            # Залишаємо генерацію як запасний варіант
            self.generate_patrol_route(game_matrix, center_x, center_y)

        # Таймери та масив для пошуку шляхів алгоритмом A*
        self.path_update_timer = random.randint(0, 15)
        self.path = []

        # Посилання на випущену кулю для передачі в ядро гри game.py
        self.fired_bullet = None

        # Тимчасовий лічильник для пропуску перевірки зору
        self.raycast_timer = random.randint(0, 3)

    def _load_enemy_image(self):
        """Завантажує спрайт ворога з відповідної папки на основі його типу (rookie, veteran тощо)"""
        # Розподіляємо скіни залежно від типу ворога
        if self.type == "rookie":
            folder_name = "Man Blue"
            prefix = "manBlue"
        elif self.type == "veteran":
            folder_name = "Man Brown"
            prefix = "manBrown"
        else:
            folder_name = "Man Old"
            prefix = "manOld"

        # Вибираємо суфікс залежно від типу озброєння ворога
        if "silenced" in self.weapon:
            suffix = "silencer"
        elif self.weapon in ["rifle", "shotgun"]:
            suffix = "machine"
        else:
            suffix = "gun"

        image_path = f"assets/images/{folder_name}/{prefix}_{suffix}.png"

        try:
            surface = pygame.image.load(image_path).convert_alpha()
            return surface
        except Exception as e:
            print(f"[WARNING] Не вдалося завантажити спрайт ворога {image_path}: {e}. Використовуємо заглушку.")
            # Запасний варіант, якщо файл не знайдено
            surface = pygame.Surface((TILE_SIZE, TILE_SIZE), pygame.SRCALPHA).convert_alpha()
            pygame.draw.circle(surface, self.color, (TILE_SIZE // 2, TILE_SIZE // 2), TILE_SIZE // 2 - 2)
            pygame.draw.line(surface, (0, 0, 0), (TILE_SIZE // 2, TILE_SIZE // 2), (TILE_SIZE, TILE_SIZE // 2), 3)
            return surface

    def draw_health_bar(self, screen, camera):
        """Відображення індикаторів здоров'я та броні ворога на екрані з урахуванням зміщення камери"""
        if self.hp <= 0:
            return

        bar_width = 40
        bar_height = 4

        bar_x = (self.pos.x + camera.camera_rect.x) - bar_width // 2
        bar_y = (self.pos.y + camera.camera_rect.y) - 30

        # 1. Рендеринг смужки здоров'я (HP)
        pygame.draw.rect(screen, (80, 0, 0), pygame.Rect(bar_x, bar_y, bar_width, bar_height))
        hp_pct = max(0, self.hp / self.max_hp)
        current_hp_width = int(bar_width * hp_pct)
        if current_hp_width > 0:
            pygame.draw.rect(screen, (0, 255, 100), pygame.Rect(bar_x, bar_y, current_hp_width, bar_height))

        # 2. Рендеринг смужки броні (Shield)
        if self.max_armor > 0:
            armor_bar_height = 3
            armor_y = bar_y + bar_height + 1
            pygame.draw.rect(screen, (0, 0, 80), pygame.Rect(bar_x, armor_y, bar_width, armor_bar_height))
            armor_pct = max(0, self.armor / self.max_armor)
            current_armor_width = int(bar_width * armor_pct)
            if current_armor_width > 0:
                pygame.draw.rect(screen, (0, 150, 255),
                                 pygame.Rect(bar_x, armor_y, current_armor_width, armor_bar_height))

    def draw_suspicion_bar(self, screen, camera):
        """Малює динамічний кольоровий індикатор рівня підозри над головою ворога під час виявлення"""
        if self.suspicion <= 0 or self.is_alerted:
            return

        bar_width = 40
        bar_height = 5

        bar_x = (self.pos.x + camera.camera_rect.x) - bar_width // 2
        bar_y = (self.pos.y + camera.camera_rect.y) - 40

        pygame.draw.rect(screen, (40, 40, 40), pygame.Rect(bar_x, bar_y, bar_width, bar_height))

        red = 255
        green = int(220 * (1.0 - self.suspicion))
        blue = 0
        color = (red, green, blue)

        current_fill_width = int(bar_width * self.suspicion)
        if current_fill_width > 0:
            pygame.draw.rect(screen, color, pygame.Rect(bar_x, bar_y, current_fill_width, bar_height))

        pygame.draw.rect(screen, (0, 0, 0), pygame.Rect(bar_x, bar_y, bar_width, bar_height), 1)

    def draw_vision_cone(self, screen, camera):
        """Візуалізація полігонального сектора огляду ворога з урахуванням великого світу та камери"""
        cone_color = (255, 0, 0, 40) if self.is_alerted else (0, 255, 0, 30)

        vision_surface = pygame.Surface((SCREEN_WIDTH, SCREEN_HEIGHT), pygame.SRCALPHA)

        screen_pos = self.pos + pygame.math.Vector2(camera.camera_rect.x, camera.camera_rect.y)
        points = [screen_pos]

        num_segments = 16
        _, current_angle = self.rotation_vector.as_polar()
        start_angle = current_angle - self.view_angle / 2

        for i in range(num_segments + 1):
            angle = start_angle + (self.view_angle / num_segments) * i
            rad = math.radians(angle)
            target_point = screen_pos + pygame.math.Vector2(math.cos(rad), math.sin(rad)) * self.view_radius
            points.append(target_point)

        if len(points) >= 3:
            pygame.draw.polygon(vision_surface, cone_color, points)

        screen.blit(vision_surface, (0, 0))

    def check_for_player(self, player, obstacles):
        """Перевіряє, чи знаходиться гравець у конусі зору ворога і чи немає між ними стін (Line of Sight)"""
        enemy_to_player = player.pos - self.pos
        distance = enemy_to_player.length()

        if distance > self.view_radius:
            return False

        if getattr(player, "is_hidden", False):
            return False

        _, enemy_angle = self.rotation_vector.as_polar()
        _, angle_to_player = enemy_to_player.as_polar()

        angle_diff = (angle_to_player - enemy_angle) % 360
        if angle_diff > 180:
            angle_diff = 360 - angle_diff

        if angle_diff > self.view_angle / 2:
            return False

        if distance > 60:
            self.raycast_timer -= 1
            if self.raycast_timer > 0 and hasattr(self, "_last_los_result"):
                return self._last_los_result
            self.raycast_timer = 3

        if distance > 0:
            for obstacle in obstacles:
                if obstacle.rect.clipline(self.pos.x, self.pos.y, player.pos.x, player.pos.y):
                    self._last_los_result = False
                    return False

        self._last_los_result = True
        return True

    def generate_patrol_route(self, game_matrix, start_x, start_y):
        """Генерує чітко 3 досяжні точки патрулювання, перевіряючи їх через A* сітку"""
        self.patrol_points = []

        start_vec = pygame.math.Vector2(start_x, start_y)
        self.patrol_points.append(start_vec)

        grid_height = len(game_matrix)
        grid_width = len(game_matrix[0])

        inverted_matrix = [[1 if cell == 0 else 0 for cell in row] for row in game_matrix]
        grid = Grid(matrix=inverted_matrix)

        start_tile_x = max(1, min(int(start_x // TILE_SIZE), grid_width - 2))
        start_tile_y = max(1, min(int(start_y // TILE_SIZE), grid_height - 2))

        if not grid.walkable(start_tile_x, start_tile_y):
            return

        finder = AStarFinder(diagonal_movement=DiagonalMovement.never)
        attempts = 0
        min_distance = TILE_SIZE * 3

        while len(self.patrol_points) < 3 and attempts < 600:
            attempts += 1

            if attempts > 300:
                min_distance = TILE_SIZE * 1.5

            gx = random.randint(2, grid_width - 3)
            gy = random.randint(2, grid_height - 3)

            if game_matrix[gy][gx] == 0 and grid.walkable(gx, gy):
                pixel_x = gx * TILE_SIZE + TILE_SIZE // 2
                pixel_y = gy * TILE_SIZE + TILE_SIZE // 2
                new_pos = pygame.math.Vector2(pixel_x, pixel_y)

                if all(p.distance_to(new_pos) > min_distance for p in self.patrol_points):
                    prev_pos = self.patrol_points[-1]
                    p_start_x = max(0, min(int(prev_pos.x // TILE_SIZE), grid_width - 1))
                    p_start_y = max(0, min(int(prev_pos.y // TILE_SIZE), grid_height - 1))

                    start_node = grid.node(p_start_x, p_start_y)
                    end_node = grid.node(gx, gy)

                    path, _ = finder.find_path(start_node, end_node, grid)

                    if len(path) > 1:
                        self.patrol_points.append(new_pos)

        offsets = [(-3, 0), (3, 0), (0, -3), (0, 3)]
        for offset in offsets:
            if len(self.patrol_points) >= 3:
                break
            tx = max(1, min(start_tile_x + offset[0], grid_width - 2))
            ty = max(1, min(start_tile_y + offset[1], grid_height - 2))
            if game_matrix[ty][tx] == 0:
                fallback_pos = pygame.math.Vector2(tx * TILE_SIZE + TILE_SIZE // 2, ty * TILE_SIZE + TILE_SIZE // 2)
                if all(p.distance_to(fallback_pos) > TILE_SIZE for p in self.patrol_points):
                    self.patrol_points.append(fallback_pos)

    def move_with_collisions(self, velocity, obstacles):
        """Переміщує ворога по осях X та Y, перевіряючи колізії зі стінами.

        ОПТИМІЗАЦІЯ: замість перебору всіх obstacles на карті для кожного ворога
        щокадру, спершу відфільтровуємо лише перешкоди поблизу (як і для гравця) —
        це суттєво знижує навантаження при великій кількості ворогів/перешкод.
        """
        if velocity.length() == 0:
            return

        nearby_obstacles = get_nearby_obstacles(self.pos, obstacles)

        resolve_axis_collision(self.pos, self.hitbox, nearby_obstacles, "x", velocity.x)
        self.rect.centerx = self.hitbox.centerx

        resolve_axis_collision(self.pos, self.hitbox, nearby_obstacles, "y", velocity.y)
        self.rect.centery = self.hitbox.centery

    def update(self, player, game_matrix, obstacles):
        """Щокадрове оновлення поведінки ШІ, розрахунок стелс-станів, стрільби та пошуку шляху A*"""
        self.fired_bullet = None
        w_stats = WEAPONS[self.weapon]

        if not hasattr(self, "_stuck_check_pos"):
            self._stuck_check_pos = pygame.math.Vector2(self.pos)
            self._stuck_timer = 0

        can_see_player = self.check_for_player(player, obstacles)

        if not self.is_alerted:
            self.view_radius = self.base_view_radius
            self.view_angle = self.base_view_angle
            self.speed = self.stats["speed"] * 0.6

            if can_see_player:
                self.suspicion += 0.025
                if self.suspicion >= 1.0:
                    self.suspicion = 1.0
                    self.is_alerted = True
                    self.last_known_player_pos = pygame.math.Vector2(player.pos)
                    self.lose_interest_timer = ENEMY_LOSE_INTEREST_TIME
                    self.patrol_wait_timer = 0
                    self.path = []
            else:
                self.suspicion -= 0.015
                if self.suspicion < 0:
                    self.suspicion = 0.0
        else:
            self.suspicion = 1.0
            self.view_radius = self.base_view_radius * 2.5
            self.view_angle = min(360, self.base_view_angle + 80)
            self.speed = self.stats["speed"]

            if can_see_player:
                self.last_known_player_pos = pygame.math.Vector2(player.pos)
                self.lose_interest_timer = ENEMY_LOSE_INTEREST_TIME
                self.patrol_wait_timer = 0
                self.path = []

        move_straight_to_player = False
        target_pos = None

        if self.is_alerted and can_see_player:
            has_obstacle_between = False
            for obstacle in obstacles:
                if obstacle.rect.clipline(self.pos.x, self.pos.y, player.pos.x, player.pos.y):
                    has_obstacle_between = True
                    break

            if not has_obstacle_between:
                move_straight_to_player = True
            else:
                target_pos = player.pos

        elif self.is_alerted:
            if self.last_known_player_pos:
                if self.pos.distance_to(self.last_known_player_pos) <= 25:
                    self.path = []
                    self.lose_interest_timer -= 1
                    if self.lose_interest_timer <= 0:
                        self.is_alerted = False
                        self.last_known_player_pos = None
                        self.suspicion = 0.0
                else:
                    target_pos = self.last_known_player_pos
            else:
                self.is_alerted = False
                self.suspicion = 0.0

        if not self.is_alerted and self.patrol_points:
            current_target = self.patrol_points[self.current_patrol_idx]
            arrival_radius = TILE_SIZE * 0.8

            if self.pos.distance_to(current_target) <= arrival_radius:
                self.path = []

                direction_to_target = current_target - self.pos
                if direction_to_target.length() > 0.5:
                    self.pos += direction_to_target.normalize() * min(self.speed, direction_to_target.length())
                    self.rect.center = self.pos
                    self.hitbox.center = self.pos

                if self.patrol_wait_timer == 0:
                    self.patrol_wait_timer = 90

                self.patrol_wait_timer -= 1
                if self.patrol_wait_timer <= 0:
                    self.current_patrol_idx = (self.current_patrol_idx + 1) % len(self.patrol_points)
                    self.patrol_wait_timer = 0
            else:
                target_pos = current_target

                if not hasattr(self, "_patrol_stuck_timer"):
                    self._patrol_stuck_timer = 0
                    self._last_patrol_pos = pygame.math.Vector2(self.pos)

                if self.pos.distance_to(self._last_patrol_pos) < 0.3:
                    self._patrol_stuck_timer += 1
                    if self._patrol_stuck_timer > 90:
                        self.current_patrol_idx = (self.current_patrol_idx + 1) % len(self.patrol_points)
                        self._patrol_stuck_timer = 0
                else:
                    self._last_patrol_pos = pygame.math.Vector2(self.pos)
                    self._patrol_stuck_timer = 0

        if move_straight_to_player:
            direction = player.pos - self.pos
            if direction.length() > 0:
                self.rotation_vector = direction.normalize()
                velocity = self.rotation_vector * self.speed
                self.move_with_collisions(velocity, obstacles)

            if self.shoot_cooldown > 0:
                self.shoot_cooldown -= 1
            else:
                _, angle = direction.as_polar()
                spread_val = w_stats.get("spread", 5)
                angle += random.uniform(-spread_val, spread_val)

                self.fired_bullet = Bullet(
                    self.pos.x, self.pos.y, angle,
                    w_stats["damage"], w_stats["bullet_speed"], True
                )
                self.shoot_cooldown = w_stats["shoot_cooldown"] // 16

        elif target_pos:
            if self.shoot_cooldown > 0:
                self.shoot_cooldown -= 1

            max_grid_x = len(game_matrix[0]) - 1
            max_grid_y = len(game_matrix) - 1

            start_x = max(0, min(int(self.pos.x // TILE_SIZE), max_grid_x))
            start_y = max(0, min(int(self.pos.y // TILE_SIZE), max_grid_y))
            end_x = max(0, min(int(target_pos.x // TILE_SIZE), max_grid_x))
            end_y = max(0, min(int(target_pos.y // TILE_SIZE), max_grid_y))

            can_move_direct = True
            for obstacle in obstacles:
                if obstacle.rect.clipline(self.pos.x, self.pos.y, target_pos.x, target_pos.y):
                    can_move_direct = False
                    break

            if not can_move_direct and not self.path:
                self.path_update_timer = 0

            self.path_update_timer -= 1

            if self.path_update_timer <= 0 or not self.path:
                self.path_update_timer = 30

                inverted_matrix = [[1 if cell == 0 else 0 for cell in row] for row in game_matrix]
                grid = Grid(matrix=inverted_matrix)

                if grid.walkable(start_x, start_y) and grid.walkable(end_x, end_y):
                    start_node = grid.node(start_x, start_y)
                    end_node = grid.node(end_x, end_y)

                    finder = AStarFinder(diagonal_movement=DiagonalMovement.never)
                    self.path, _ = finder.find_path(start_node, end_node, grid)
                    if len(self.path) > 0:
                        self.path.pop(0)

            if self.path:
                target_grid_x, target_grid_y = self.path[0]
                target_pixel_x = target_grid_x * TILE_SIZE + TILE_SIZE // 2
                target_pixel_y = target_grid_y * TILE_SIZE + TILE_SIZE // 2

                move_target = pygame.math.Vector2(target_pixel_x, target_pixel_y)
                direction = move_target - self.pos

                if direction.length() <= self.speed:
                    self.pos = move_target
                    self.rect.center = self.pos
                    self.hitbox.center = self.pos
                    self.path.pop(0)
                else:
                    self.rotation_vector = direction.normalize()
                    velocity = self.rotation_vector * self.speed

                    old_pos = pygame.math.Vector2(self.pos)
                    self.move_with_collisions(velocity, obstacles)

                    if self.pos.distance_to(old_pos) < 0.05:
                        self.path = []
            elif can_move_direct or self.is_alerted:
                direction = target_pos - self.pos
                if direction.length() > 0:
                    self.rotation_vector = direction.normalize()
                    velocity = self.rotation_vector * self.speed
                    self.move_with_collisions(velocity, obstacles)

        if target_pos or move_straight_to_player:
            if self.pos.distance_to(self._stuck_check_pos) < 0.5:
                self._stuck_timer += 1
                if self._stuck_timer > 60:
                    self.path = []
                    if not self.is_alerted and self.patrol_points:
                        self.current_patrol_idx = (self.current_patrol_idx + 1) % len(self.patrol_points)
                    elif self.is_alerted:
                        self.last_known_player_pos = None
                    self._stuck_timer = 0
            else:
                self._stuck_check_pos = pygame.math.Vector2(self.pos)
                self._stuck_timer = 0

        # Оновлення графічного повороту спрайту ворога у бік руху/цілі
        _, angle = self.rotation_vector.as_polar()
        self.image = pygame.transform.rotate(self.base_image, -angle)
        self.rect = self.image.get_rect(center=self.pos)