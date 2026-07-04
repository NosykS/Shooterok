# src/entities/enemy.py
import pygame
import math
import random
from pathfinding.core.grid import Grid
from pathfinding.finder.a_star import AStarFinder
from src.settings import (
    ENEMY_TYPES, TILE_SIZE, ENEMY_LOSE_INTEREST_TIME,
    WEAPONS, WORLD_WIDTH, WORLD_HEIGHT
)
from src.objects.bullet import Bullet


class Enemy(pygame.sprite.Sprite):
    def __init__(self, x, y, enemy_type="rookie", game_matrix=None):
        super().__init__()
        self.type = enemy_type
        self.stats = ENEMY_TYPES[enemy_type]

        self.hp = self.stats["hp"]
        self.max_hp = self.stats["hp"]
        self.speed = self.stats["speed"]
        self.color = self.stats["color"]
        self.armor = self.stats["armor"]
        self.max_armor = self.stats["armor"]
        self.weapon = self.stats["weapon"]
        self.shoot_cooldown = 0

        # Базові параметри зору
        self.base_view_radius = self.stats["view_radius"]
        self.base_view_angle = self.stats["view_angle"]

        # Динамічні параметри зору
        self.view_radius = self.base_view_radius
        self.view_angle = self.base_view_angle

        self.base_image = pygame.Surface((TILE_SIZE, TILE_SIZE), pygame.SRCALPHA)
        pygame.draw.circle(self.base_image, self.color, (TILE_SIZE // 2, TILE_SIZE // 2), TILE_SIZE // 2 - 2)
        pygame.draw.line(self.base_image, (0, 0, 0), (TILE_SIZE // 2, TILE_SIZE // 2), (TILE_SIZE, TILE_SIZE // 2), 3)
        self.image = self.base_image.copy()

        self.pos = pygame.math.Vector2(x, y)
        self.rect = self.image.get_rect(center=self.pos)
        self.hitbox = pygame.Rect(0, 0, 28, 28)
        self.hitbox.center = self.pos

        self.rotation_vector = pygame.math.Vector2(1, 0).rotate(random.randint(0, 360))
        self.is_alerted = False

        self.suspicion = 0.0  # Рівень підозри від 0.0 до 1.0
        self.suspicion_speed = 1.5  # Як швидко заповнюється
        self.cool_down_speed = 0.8  # Як швидко ворог заспокоюється

        # Стелс-таймери та координати погоні
        self.last_known_player_pos = None
        self.lose_interest_timer = ENEMY_LOSE_INTEREST_TIME

        # ЛОГІКА ПАТРУЛЮВАННЯ
        self.patrol_points = []
        self.current_patrol_idx = 0
        self.patrol_wait_timer = 0
        if game_matrix:
            self.generate_patrol_route(game_matrix, x, y)

        self.path_update_timer = 0
        self.path = []

        self.fired_bullet = None

    def draw_health_bar(self, screen, camera):
        """Відображення здоров'я та броні ворога на екрані з урахуванням зміщення камери"""
        if self.hp <= 0:
            return

        bar_width = 40
        bar_height = 4

        bar_x = (self.pos.x + camera.camera_rect.x) - bar_width // 2
        bar_y = (self.pos.y + camera.camera_rect.y) - 30

        # 1. Смужка HP
        pygame.draw.rect(screen, (80, 0, 0), pygame.Rect(bar_x, bar_y, bar_width, bar_height))
        hp_pct = max(0, self.hp / self.max_hp)
        current_hp_width = int(bar_width * hp_pct)
        if current_hp_width > 0:
            pygame.draw.rect(screen, (0, 255, 100), pygame.Rect(bar_x, bar_y, current_hp_width, bar_height))

        # 2. Смужка броні
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
        """Малює індикатор підозри над головою ворога під час засікання"""
        if self.suspicion <= 0 or self.is_alerted:
            return

        bar_width = 40
        bar_height = 5

        bar_x = (self.pos.x + camera.camera_rect.x) - bar_width // 2
        bar_y = (self.pos.y + camera.camera_rect.y) - 40

        pygame.draw.rect(screen, (40, 40, 40), pygame.Rect(bar_x, bar_y, bar_width, bar_height))

        # Градієнт кольору: від жовтого до червоного
        red = 255
        green = int(220 * (1.0 - self.suspicion))
        blue = 0
        color = (red, green, blue)

        current_fill_width = int(bar_width * self.suspicion)
        if current_fill_width > 0:
            pygame.draw.rect(screen, color, pygame.Rect(bar_x, bar_y, current_fill_width, bar_height))

        pygame.draw.rect(screen, (0, 0, 0), pygame.Rect(bar_x, bar_y, bar_width, bar_height), 1)

    def draw_vision_cone(self, screen, camera):
        """Візуалізація сектору огляду ворога з урахуванням великого світу та камери"""
        cone_color = (255, 0, 0, 40) if self.is_alerted else (0, 255, 0, 30)

        # ФІКС: Створюємо тимчасову поверхню під розмір ВСЬОГО світу
        vision_surface = pygame.Surface((WORLD_WIDTH, WORLD_HEIGHT), pygame.SRCALPHA)

        # Точки малюються в глобальних координатах світу
        points = [self.pos]

        num_segments = 30
        _, current_angle = self.rotation_vector.as_polar()
        start_angle = current_angle - self.view_angle / 2

        for i in range(num_segments + 1):
            angle = start_angle + (self.view_angle / num_segments) * i
            rad = math.radians(angle)
            target_point = self.pos + pygame.math.Vector2(math.cos(rad), math.sin(rad)) * self.view_radius
            points.append(target_point)

        if len(points) >= 3:
            pygame.draw.polygon(vision_surface, cone_color, points)

        # Малюємо поверхню на екран із застосуванням зміщення камери
        screen.blit(vision_surface, (camera.camera_rect.x, camera.camera_rect.y))

    def check_for_player(self, player, obstacles):
        """Перевіряє, чи знаходиться гравець у конусі зору ворога і чи немає перешкод (апгрейджений рейкаст)."""
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

        # Оптимізований та точний Line-of-Sight чек через clipline
        if distance > 0:
            for obstacle in obstacles:
                # Перевіряємо, чи перетинає лінія погляду прямокутник стіни
                if obstacle.rect.clipline(self.pos.x, self.pos.y, player.pos.x, player.pos.y):
                    return False

        return True

    def generate_patrol_route(self, game_matrix, start_x, start_y):
        """Генерує 3 точки патрулювання: початкова позиція + 2 випадкові вільні плитки"""
        self.patrol_points.append(pygame.math.Vector2(start_x, start_y))

        grid_height = len(game_matrix)
        grid_width = len(game_matrix[0])

        attempts = 0
        while len(self.patrol_points) < 3 and attempts < 150:
            attempts += 1
            gx = random.randint(1, grid_width - 2)
            gy = random.randint(1, grid_height - 2)
            if game_matrix[gy][gx] == 1:
                pixel_x = gx * TILE_SIZE + TILE_SIZE // 2
                pixel_y = gy * TILE_SIZE + TILE_SIZE // 2
                new_pos = pygame.math.Vector2(pixel_x, pixel_y)
                if all(p.distance_to(new_pos) > TILE_SIZE * 3 for p in self.patrol_points):
                    self.patrol_points.append(new_pos)

    def update(self, player, game_matrix, obstacles):
        self.fired_bullet = None
        w_stats = WEAPONS[self.weapon]

        # 1. Перевіряємо, чи бачить ворог гравця
        can_see_player = self.check_for_player(player, obstacles)

        # 2. Логіка індикатора підозри та станів тривоги
        if not self.is_alerted:
            self.view_radius = self.base_view_radius
            self.view_angle = self.base_view_angle
            self.speed = self.stats["speed"] * 0.6  # Патрульна швидкість

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

        # 3. Визначаємо поведінку руху
        move_straight_to_player = False
        target_pos = None

        if self.is_alerted and can_see_player:
            move_straight_to_player = True
        elif self.is_alerted:
            if self.last_known_player_pos:
                if self.pos.distance_to(self.last_known_player_pos) <= 15:
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
            if self.pos.distance_to(current_target) <= 15:
                self.path = []
                if self.patrol_wait_timer == 0:
                    self.patrol_wait_timer = 120
                self.patrol_wait_timer -= 1
                if self.patrol_wait_timer <= 0:
                    self.current_patrol_idx = (self.current_patrol_idx + 1) % len(self.patrol_points)
            else:
                target_pos = current_target

        # Стрільба та пряме переслідування
        if move_straight_to_player:
            direction = player.pos - self.pos
            if direction.length() > 0:
                self.rotation_vector = direction.normalize()
                self.pos += self.rotation_vector * self.speed
            self.hitbox.center = self.pos

            if self.shoot_cooldown > 0:
                self.shoot_cooldown -= 1
            else:
                _, angle = direction.as_polar()
                # Розраховуємо розліт на основі поточної зброї ворога (з settings.py)
                spread_val = w_stats.get("spread", 5)
                angle += random.uniform(-spread_val, spread_val)

                self.fired_bullet = Bullet(
                    self.pos.x, self.pos.y, angle,
                    w_stats["damage"], w_stats["bullet_speed"], True
                )
                # ФІКС: Кулдаун береться безпосередньо з налаштувань конкретної зброї
                self.shoot_cooldown = w_stats["shoot_cooldown"] // 16  # переводимо мс в кадри (~60fps)

        # Пошук шляху за алгоритмом A*
        elif target_pos:
            if self.shoot_cooldown > 0:
                self.shoot_cooldown -= 1

            self.path_update_timer -= 1
            max_grid_x = len(game_matrix[0]) - 1
            max_grid_y = len(game_matrix) - 1

            start_x = max(0, min(int(self.pos.x // TILE_SIZE), max_grid_x))
            start_y = max(0, min(int(self.pos.y // TILE_SIZE), max_grid_y))
            end_x = max(0, min(int(target_pos.x // TILE_SIZE), max_grid_x))
            end_y = max(0, min(int(target_pos.y // TILE_SIZE), max_grid_y))

            if self.path_update_timer <= 0:
                self.path_update_timer = 15
                grid = Grid(matrix=game_matrix)

                if grid.walkable(start_x, start_y) and grid.walkable(end_x, end_y):
                    start_node = grid.node(start_x, start_y)
                    end_node = grid.node(end_x, end_y)

                    finder = AStarFinder()
                    self.path, _ = finder.find_path(start_node, end_node, grid)
                    if len(self.path) > 0:
                        self.path.pop(0)

            if self.path:
                target_grid_x, target_grid_y = self.path[0]
                target_pixel_x = target_grid_x * TILE_SIZE + TILE_SIZE // 2
                target_pixel_y = target_grid_y * TILE_SIZE + TILE_SIZE // 2

                move_target = pygame.math.Vector2(target_pixel_x, target_pixel_y)
                direction = move_target - self.pos

                if direction.length() > self.speed:
                    self.rotation_vector = direction.normalize()
                    self.pos += self.rotation_vector * self.speed
                else:
                    self.pos = move_target
                    if len(self.path) > 0:
                        self.path.pop(0)
            else:
                direction = target_pos - self.pos
                if direction.length() > self.speed:
                    self.rotation_vector = direction.normalize()
                    self.pos += self.rotation_vector * self.speed

            self.hitbox.center = self.pos

        _, angle = self.rotation_vector.as_polar()
        self.image = pygame.transform.rotate(self.base_image, -angle)
        self.rect = self.image.get_rect(center=self.pos)