import pygame
import random
# Імпортуємо нові параметри великого світу замість екрану
from src.settings import (
    WORLD_WIDTH, WORLD_HEIGHT, WEAPONS, PLAYER_SPEED_NORMAL,
    PLAYER_SPEED_STEALTH, PLAYER_NOISE_NORMAL, PLAYER_NOISE_STEALTH
)
from src.objects.bullet import Bullet


class Player(pygame.sprite.Sprite):
    def __init__(self, x, y):
        super().__init__()
        self.base_image = self._create_placeholder_image()
        self.image = self.base_image.copy()

        self.hp = 100
        self.max_hp = 100
        self.armor = 50
        self.max_armor = 100

        self.pos = pygame.math.Vector2(x, y)
        self.rect = self.image.get_rect(center=self.pos)

        self.hitbox = pygame.Rect(0, 0, 32, 32)
        self.hitbox.center = self.pos

        # Стелс характеристики
        self.speed = PLAYER_SPEED_NORMAL
        self.current_noise_radius = PLAYER_NOISE_NORMAL
        self.is_hidden = False  # Чи сховався в кущах/шафі

        self.weapons = ["knife", "pistol_silenced", "rifle"]
        self.current_weapon_index = 1

        # ФІКС: Ініціалізуємо запас набоїв для кожної вогнепальної зброї на максимум з конфігу settings
        self.weapons_ammo = {
            "knife": 0,
            "pistol_silenced": WEAPONS["pistol_silenced"]["ammo_capacity"],
            "rifle": WEAPONS["rifle"]["ammo_capacity"]
        }

        # Зберігаємо точний час останнього пострілу/атаки в мілісекундах
        self.last_shot_time = 0

    def _create_placeholder_image(self):
        surface = pygame.Surface((50, 50), pygame.SRCALPHA)
        pygame.draw.circle(surface, (0, 128, 255), (25, 25), 20)
        pygame.draw.line(surface, (255, 0, 0), (25, 25), (50, 25), 4)
        return surface

    @property
    def current_weapon(self):
        return self.weapons[self.current_weapon_index]

    # ДИНАМІЧНА ВЛАСТИВІСТЬ: Повертає набої для поточної обраної зброї, щоб ui.py (player.ammo) працював без переробок
    @property
    def ammo(self):
        return self.weapons_ammo[self.current_weapon]

    # Сетер для ammo (про всяк випадок, якщо UI захоче напряму модифікувати значення)
    @ammo.setter
    def ammo(self, value):
        self.weapons_ammo[self.current_weapon] = value

    def handle_movement(self, keys, obstacles):
        if self.is_hidden:
            return  # Якщо сховався — рухатися не можна, поки не вийдеш

        # Перевірка на стелс-ходьбу (затиснутий Shift)
        if keys[pygame.K_LSHIFT]:
            self.speed = PLAYER_SPEED_STEALTH
            self.current_noise_radius = PLAYER_NOISE_STEALTH
        else:
            self.speed = PLAYER_SPEED_NORMAL
            self.current_noise_radius = PLAYER_NOISE_NORMAL

        dx, dy = 0, 0
        if keys[pygame.K_w] or keys[pygame.K_UP]: dy = -self.speed
        if keys[pygame.K_s] or keys[pygame.K_DOWN]: dy = self.speed
        if keys[pygame.K_a] or keys[pygame.K_LEFT]: dx = -self.speed
        if keys[pygame.K_d] or keys[pygame.K_RIGHT]: dx = self.speed

        if dx != 0 and dy != 0:
            dx *= 0.7071
            dy *= 0.7071

        # Рух X
        self.pos.x += dx
        self.hitbox.centerx = self.pos.x
        for obstacle in obstacles:
            if self.hitbox.colliderect(obstacle.rect):
                if dx > 0: self.hitbox.right = obstacle.rect.left
                if dx < 0: self.hitbox.left = obstacle.rect.right
                self.pos.x = self.hitbox.centerx

        # Рух Y
        self.pos.y += dy
        self.hitbox.centery = self.pos.y
        for obstacle in obstacles:
            if self.hitbox.colliderect(obstacle.rect):
                if dy > 0: self.hitbox.bottom = obstacle.rect.top
                if dy < 0: self.hitbox.top = obstacle.rect.bottom
                self.pos.y = self.hitbox.centery

        # ЗМІНЕНО: Обмеження тепер діють на весь ВЕЛИКИЙ СВІТ, а не лише екран
        if self.pos.x < 0: self.pos.x = 0
        if self.pos.x > WORLD_WIDTH: self.pos.x = WORLD_WIDTH
        if self.pos.y < 0: self.pos.y = 0
        if self.pos.y > WORLD_HEIGHT: self.pos.y = WORLD_HEIGHT

        self.hitbox.center = self.pos

        # Якщо гравець не рухається, він не створює шуму кроками
        if dx == 0 and dy == 0:
            self.current_noise_radius = 0

    def rotate_to_mouse(self, camera):
        """ЗМІНЕНО: тепер метод приймає об'єкт камери, щоб коригувати позицію миші"""
        if self.is_hidden: return

        # Переводимо координати миші з екрану у великий світ
        mouse_x, mouse_y = pygame.mouse.get_pos()
        world_mouse_x = mouse_x - camera.camera_rect.x
        world_mouse_y = mouse_y - camera.camera_rect.y

        direction = pygame.math.Vector2(world_mouse_x - self.pos.x, world_mouse_y - self.pos.y)
        _, angle = direction.as_polar()
        angle = -angle
        self.image = pygame.transform.rotate(self.base_image, angle)
        self.rect = self.image.get_rect(center=self.pos)

    def change_weapon(self, index):
        if 0 <= index < len(self.weapons):
            self.current_weapon_index = index
            print(f"Зброя змінена на: {self.weapons[index]} (Набої: {self.ammo})")

    def attack(self, camera):
        """ЗМІНЕНО: метод приймає камеру для точного розрахунку вектору польоту кулі"""
        if self.is_hidden:
            return None

        current_time = pygame.time.get_ticks()
        weapon_stats = WEAPONS[self.current_weapon]

        # 1. Перевірка кулдауну
        if current_time - self.last_shot_time < weapon_stats["shoot_cooldown"]:
            return None

        # 2. Обробка атаки ближнього бою
        if self.current_weapon == "knife":
            self.last_shot_time = current_time
            return "melee"

        # 3. ФІКС: Перевірка наявності набоїв для вогнепальної зброї
        if self.weapons_ammo[self.current_weapon] <= 0:
            return None

        # Витрачаємо один набій
        self.weapons_ammo[self.current_weapon] -= 1
        self.last_shot_time = current_time

        # Коригуємо мишу під координати світу
        mouse_x, mouse_y = pygame.mouse.get_pos()
        world_mouse = pygame.math.Vector2(mouse_x - camera.camera_rect.x, mouse_y - camera.camera_rect.y)

        dir_vector = world_mouse - self.pos

        if dir_vector.length() > 0:
            _, angle = dir_vector.as_polar()

            angle += random.uniform(-weapon_stats["spread"], weapon_stats["spread"])

            return Bullet(
                self.pos.x,
                self.pos.y,
                angle=angle,
                damage=weapon_stats["damage"],
                speed=weapon_stats["bullet_speed"],
                is_enemy_bullet=False
            )

        return None

    def update(self, keys, obstacles, camera):
        """ЗМІНЕНО: передаємо камеру всередину update"""
        self.handle_movement(keys, obstacles)
        self.rotate_to_mouse(camera)