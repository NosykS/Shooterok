# src/enemy.py
import pygame
import math
import random
from pathfinding.core.grid import Grid
from pathfinding.finder.a_star import AStarFinder
from src.settings import ENEMY_TYPES, TILE_SIZE, ENEMY_LOSE_INTEREST_TIME


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

    # ФІКС ВІДСТУПІВ: Тепер метод знаходиться на рівні класу, як і має бути!
    def draw_health_bar(self, screen):
        # Якщо ворог мертвий, нічого не малюємо
        if self.hp <= 0:
            return

        # Налаштування розмірів смужки
        bar_width = 40
        bar_height = 4
        # Малюємо смужку на 30 пікселів вище центру ворога
        bar_x = self.pos.x - bar_width // 2
        bar_y = self.pos.y - 30

        # 1. МАЛЮЄМО СМУЖКУ HP
        # Темний фон (задник)
        pygame.draw.rect(screen, (80, 0, 0), pygame.Rect(bar_x, bar_y, bar_width, bar_height))
        # Зелена або червона смужка поточного HP
        hp_pct = max(0, self.hp / self.max_hp)
        current_hp_width = int(bar_width * hp_pct)
        if current_hp_width > 0:
            pygame.draw.rect(screen, (0, 255, 100), pygame.Rect(bar_x, bar_y, current_hp_width, bar_height))

        # 2. МАЛЮЄМО СМУЖКУ БРОНІ (тільки якщо у цього типу ворога взагалі є броня)
        if self.max_armor > 0:
            armor_bar_height = 3
            # Смужка броні буде одразу під смужкою HP (на 5 пікселів нижче)
            armor_y = bar_y + bar_height + 1

            # Темний фон броні
            pygame.draw.rect(screen, (0, 0, 80), pygame.Rect(bar_x, armor_y, bar_width, armor_bar_height))

            # Синя смужка поточної броні
            armor_pct = max(0, self.armor / self.max_armor)
            current_armor_width = int(bar_width * armor_pct)
            if current_armor_width > 0:
                pygame.draw.rect(screen, (0, 150, 255),
                                 pygame.Rect(bar_x, armor_y, current_armor_width, armor_bar_height))

    def draw_vision_cone(self, screen):
        """Малює напівпрозорий сектор зору ворога на екрані."""
        cone_color = (255, 0, 0, 40) if self.is_alerted else (0, 255, 0, 30)

        from src.settings import SCREEN_WIDTH, SCREEN_HEIGHT
        vision_surface = pygame.Surface((SCREEN_WIDTH, SCREEN_HEIGHT), pygame.SRCALPHA)

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

        screen.blit(vision_surface, (0, 0))

    def check_for_player(self, player, obstacles):
        """Перевіряє, чи знаходиться гравець у конусі зору ворога і чи немає перешкод."""
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

        if distance > 0:
            ray_dir = enemy_to_player.normalize()
            step_size = 10
            steps = int(distance / step_size)

            for i in range(1, steps):
                check_pos = self.pos + ray_dir * (i * step_size)
                for obstacle in obstacles:
                    if obstacle.rect.collidepoint(check_pos):
                        return False

        return True

    def generate_patrol_route(self, game_matrix, start_x, start_y):
        """Генерує 3 точки патрулювання: початкова позиція + 2 випадкові вільні плитки"""
        self.patrol_points.append(pygame.math.Vector2(start_x, start_y))

        grid_height = len(game_matrix)
        grid_width = len(game_matrix[0])

        attempts = 0
        while len(self.patrol_points) < 3 and attempts < 100:
            attempts += 1
            gx = random.randint(1, grid_width - 2)
            gy = random.randint(1, grid_height - 2)
            if game_matrix[gy][gx] == 1:
                pixel_x = gx * TILE_SIZE + TILE_SIZE // 2
                pixel_y = gy * TILE_SIZE + TILE_SIZE // 2
                new_pos = pygame.math.Vector2(pixel_x, pixel_y)
                if all(p.distance_to(new_pos) > TILE_SIZE * 2 for p in self.patrol_points):
                    self.patrol_points.append(new_pos)

    def update(self, player, game_matrix, obstacles):
        self.fired_bullet = None
        if self.is_alerted:
            self.view_radius = self.base_view_radius * 2.5
            self.view_angle = min(360, self.base_view_angle + 80)
            self.speed = self.stats["speed"]
        else:
            self.view_radius = self.base_view_radius
            self.view_angle = self.base_view_angle
            from src.settings import ENEMY_TYPES
            self.speed = ENEMY_TYPES["rookie"]["speed"]

        can_see_player = self.check_for_player(player, obstacles)

        move_straight_to_player = False
        target_pos = None

        if can_see_player:
            self.is_alerted = True
            self.last_known_player_pos = pygame.math.Vector2(player.pos)
            self.lose_interest_timer = ENEMY_LOSE_INTEREST_TIME
            self.patrol_wait_timer = 0
            move_straight_to_player = True
            self.path = []
        elif self.is_alerted:
            if self.last_known_player_pos:
                if self.pos.distance_to(self.last_known_player_pos) <= 15:
                    self.path = []
                    self.lose_interest_timer -= 1
                    if self.lose_interest_timer <= 0:
                        self.is_alerted = False
                        self.last_known_player_pos = None
                else:
                    target_pos = self.last_known_player_pos
            else:
                self.is_alerted = False

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

        if move_straight_to_player:
            direction = player.pos - self.pos
            if direction.length() > 0:
                self.rotation_vector = direction.normalize()
                self.pos += self.rotation_vector * self.speed
            self.hitbox.center = self.pos

            if self.shoot_cooldown > 0:
                self.shoot_cooldown -= 1
            else:
                from src.objects.bullet import Bullet
                from src.settings import WEAPONS
                import random

                _, angle = direction.as_polar()
                spread_val = 15 if self.type == "rookie" else 5
                angle += random.uniform(-spread_val, spread_val)

                w_stats = WEAPONS[self.weapon]
                self.fired_bullet = Bullet(self.pos.x, self.pos.y, angle, w_stats["damage"], w_stats["bullet_speed"],
                                           True)
                self.shoot_cooldown = 45 if self.type == "rookie" else 15

        elif target_pos:
            self.shoot_cooldown = 0
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