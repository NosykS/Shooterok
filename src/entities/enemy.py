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

        # Створення базової графічної поверхні ворога (кола з вектором напрямку погляду)
        self.base_image = pygame.Surface((TILE_SIZE, TILE_SIZE), pygame.SRCALPHA)
        pygame.draw.circle(self.base_image, self.color, (TILE_SIZE // 2, TILE_SIZE // 2), TILE_SIZE // 2 - 2)
        pygame.draw.line(self.base_image, (0, 0, 0), (TILE_SIZE // 2, TILE_SIZE // 2), (TILE_SIZE, TILE_SIZE // 2), 3)
        self.image = self.base_image.copy()

        # Фізичні вектори та хітбокси
        self.pos = pygame.math.Vector2(x, y)
        self.rect = self.image.get_rect(center=self.pos)
        self.hitbox = pygame.Rect(0, 0, 28, 28)
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
        if game_matrix:
            self.generate_patrol_route(game_matrix, x, y)

        # Таймери та масив для пошуку шляхів алгоритмом A*
        self.path_update_timer = 0
        self.path = []

        # Посилання на випущену кулю для передачі в ядро гри game.py
        self.fired_bullet = None

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

        # Плавний градієнт кольору: від жовтого (низька підозра) до червоного (тривога)
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

        # Створюємо тимчасову поверхню під розмір ВСЬОГО світу для альфа-каналу
        vision_surface = pygame.Surface((WORLD_WIDTH, WORLD_HEIGHT), pygame.SRCALPHA)

        # Центр конуса — це позиція самого ворога
        points = [self.pos]

        num_segments = 30
        _, current_angle = self.rotation_vector.as_polar()
        start_angle = current_angle - self.view_angle / 2

        # Розраховуємо точки по дузі конуса огляду
        for i in range(num_segments + 1):
            angle = start_angle + (self.view_angle / num_segments) * i
            rad = math.radians(angle)
            target_point = self.pos + pygame.math.Vector2(math.cos(rad), math.sin(rad)) * self.view_radius
            points.append(target_point)

        if len(points) >= 3:
            pygame.draw.polygon(vision_surface, cone_color, points)

        # Малюємо поверхню на екран із застосуванням поточного зсуву камери
        screen.blit(vision_surface, (camera.camera_rect.x, camera.camera_rect.y))

    def check_for_player(self, player, obstacles):
        """Перевіряє, чи знаходиться гравець у конусі зору ворога і чи немає між ними стін (Line of Sight)"""
        enemy_to_player = player.pos - self.pos
        distance = enemy_to_player.length()

        # Якщо гравець за межами радіуса бачення — одразу False
        if distance > self.view_radius:
            return False

        # Якщо гравець сховався в кущах/шафі — ворог його не бачить
        if getattr(player, "is_hidden", False):
            return False

        _, enemy_angle = self.rotation_vector.as_polar()
        _, angle_to_player = enemy_to_player.as_polar()

        # Розрахунок мінімальної кутової різниці
        angle_diff = (angle_to_player - enemy_angle) % 360
        if angle_diff > 180:
            angle_diff = 360 - angle_diff

        # Якщо кут між поглядом ворога та гравцем більший за половину конуса — гравець поза зоною
        if angle_diff > self.view_angle / 2:
            return False

        # Точний геометричний рейкаст через clipline: перевірка перетину лінії зору зі стінами
        if distance > 0:
            for obstacle in obstacles:
                if obstacle.rect.clipline(self.pos.x, self.pos.y, player.pos.x, player.pos.y):
                    return False

        return True

    def generate_patrol_route(self, game_matrix, start_x, start_y):
        """Генерує циклічний маршрут патрулювання з 3 точок: стартова позиція + 2 випадкові вільні тайли"""
        self.patrol_points.append(pygame.math.Vector2(start_x, start_y))

        grid_height = len(game_matrix)
        grid_width = len(game_matrix[0])

        attempts = 0
        while len(self.patrol_points) < 3 and attempts < 150:
            attempts += 1
            gx = random.randint(1, grid_width - 2)
            gy = random.randint(1, grid_height - 2)
            if game_matrix[gy][gx] == 1:  # 1 означає вільну підлогу
                pixel_x = gx * TILE_SIZE + TILE_SIZE // 2
                pixel_y = gy * TILE_SIZE + TILE_SIZE // 2
                new_pos = pygame.math.Vector2(pixel_x, pixel_y)
                # Перевіряємо, щоб точки не спавнилися занадто близько одна до одної
                if all(p.distance_to(new_pos) > TILE_SIZE * 3 for p in self.patrol_points):
                    self.patrol_points.append(new_pos)

    def update(self, player, game_matrix, obstacles):
        """Щокадрове оновлення поведінки ШІ, розрахунок стелс-станів, стрільби та пошуку шляху A*"""
        self.fired_bullet = None
        w_stats = WEAPONS[self.weapon]

        # 1. Сканування середовища на наявність гравця
        can_see_player = self.check_for_player(player, obstacles)

        # 2. Менеджер станів: Патруль / Накопичення підозри / Активна тривога
        if not self.is_alerted:
            self.view_radius = self.base_view_radius
            self.view_angle = self.base_view_angle
            self.speed = self.stats["speed"] * 0.6  # Зменшена швидкість під час спокійного патрулювання

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
            # У стані тривоги зіниці ворога розширюються (кут та радіус зору значно збільшуються)
            self.suspicion = 1.0
            self.view_radius = self.base_view_radius * 2.5
            self.view_angle = min(360, self.base_view_angle + 80)
            self.speed = self.stats["speed"]

            if can_see_player:
                self.last_known_player_pos = pygame.math.Vector2(player.pos)
                self.lose_interest_timer = ENEMY_LOSE_INTEREST_TIME
                self.patrol_wait_timer = 0
                self.path = []

        # 3. Визначення вектора руху та цілі переслідування
        move_straight_to_player = False
        target_pos = None

        if self.is_alerted and can_see_player:
            move_straight_to_player = True
        elif self.is_alerted:
            if self.last_known_player_pos:
                # Перевіряємо, чи прибув ворог на останню відому позицію гравця
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

        # Перемикання точок патрулювання у спокійному стані
        if not self.is_alerted and self.patrol_points:
            current_target = self.patrol_points[self.current_patrol_idx]
            if self.pos.distance_to(current_target) <= 15:
                self.path = []
                if self.patrol_wait_timer == 0:
                    self.patrol_wait_timer = 120  # Затримка на точці огляду (2 секунди при 60 FPS)
                self.patrol_wait_timer -= 1
                if self.patrol_wait_timer <= 0:
                    self.current_patrol_idx = (self.current_patrol_idx + 1) % len(self.patrol_points)
            else:
                target_pos = current_target

        # Сценарій А: Пряме переслідування та ведення вогню на ураження
        if move_straight_to_player:
            direction = player.pos - self.pos
            if direction.length() > 0:
                self.rotation_vector = direction.normalize()
                self.pos += self.rotation_vector * self.speed
            self.hitbox.center = self.pos

            # Обробка таймера перезарядки зброї
            if self.shoot_cooldown > 0:
                self.shoot_cooldown -= 1
            else:
                _, angle = direction.as_polar()
                # Розраховуємо розліт куль на основі характеристик зброї ворога
                spread_val = w_stats.get("spread", 5)
                angle += random.uniform(-spread_val, spread_val)

                # Генеруємо об'єкт кулі (game.py перехопить її, якщо гравець не впритул)
                self.fired_bullet = Bullet(
                    self.pos.x, self.pos.y, angle,
                    w_stats["damage"], w_stats["bullet_speed"], True
                )
                self.shoot_cooldown = w_stats["shoot_cooldown"] // 16  # Переведення мілісекунд у кадри

        # Сценарій Б: Обхід перешкод за допомогою алгоритму пошуку шляху A* (якщо є проміжна ціль)
        elif target_pos:
            if self.shoot_cooldown > 0:
                self.shoot_cooldown -= 1

            self.path_update_timer -= 1
            max_grid_x = len(game_matrix[0]) - 1
            max_grid_y = len(game_matrix) - 1

            # Конвертація піксельних координат у індекси двовимірної матриці карти
            start_x = max(0, min(int(self.pos.x // TILE_SIZE), max_grid_x))
            start_y = max(0, min(int(self.pos.y // TILE_SIZE), max_grid_y))
            end_x = max(0, min(int(target_pos.x // TILE_SIZE), max_grid_x))
            end_y = max(0, min(int(target_pos.y // TILE_SIZE), max_grid_y))

            # Оптимізація: перераховуємо шлях A* не кожен кадр, а раз на 15 кадрів
            if self.path_update_timer <= 0:
                self.path_update_timer = 15
                grid = Grid(matrix=game_matrix)

                if grid.walkable(start_x, start_y) and grid.walkable(end_x, end_y):
                    start_node = grid.node(start_x, start_y)
                    end_node = grid.node(end_x, end_y)

                    finder = AStarFinder()
                    self.path, _ = finder.find_path(start_node, end_node, grid)
                    if len(self.path) > 0:
                        self.path.pop(0)  # Видаляємо початкову точку, де ворог уже стоїть

            # Покрокове переміщення по знайдених нодах шляху A*
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
                # Фоллбек механіка: якщо шлях не знайдено, рухаємося напряму
                direction = target_pos - self.pos
                if direction.length() > self.speed:
                    self.rotation_vector = direction.normalize()
                    self.pos += self.rotation_vector * self.speed

            self.hitbox.center = self.pos

        # Оновлення графічного повороту спрайту на основі вектора руху
        _, angle = self.rotation_vector.as_polar()
        self.image = pygame.transform.rotate(self.base_image, -angle)
        self.rect = self.image.get_rect(center=self.pos)