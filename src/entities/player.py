# src/entities/player.py
import pygame
import random
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
        self.current_noise_radius = 0  # Починаємо з нуля, шум генерується діями
        self.is_hidden = False  # Чи сховався в кущах/шафі

        self.weapons = ["knife", "pistol_silenced", "rifle"]
        self.current_weapon_index = 1

        # Запас набоїв з конфігу settings
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

    @property
    def ammo(self):
        return self.weapons_ammo[self.current_weapon]

    @ammo.setter
    def ammo(self, value):
        self.weapons_ammo[self.current_weapon] = value

    def handle_movement(self, keys, obstacles):
        if self.is_hidden:
            self.current_noise_radius = 0
            return

        # Базове визначення шуму від руху
        if keys[pygame.K_LSHIFT]:
            self.speed = PLAYER_SPEED_STEALTH
            base_noise = PLAYER_NOISE_STEALTH
        else:
            self.speed = PLAYER_SPEED_NORMAL
            base_noise = PLAYER_NOISE_NORMAL

        dx, dy = 0, 0
        if keys[pygame.K_w] or keys[pygame.K_UP]: dy = -self.speed
        if keys[pygame.K_s] or keys[pygame.K_DOWN]: dy = self.speed
        if keys[pygame.K_a] or keys[pygame.K_LEFT]: dx = -self.speed
        if keys[pygame.K_d] or keys[pygame.K_RIGHT]: dx = self.speed

        if dx != 0 and dy != 0:
            dx *= 0.7071
            dy *= 0.7071

        # Якщо гравець рухається — присвоюємо шум руху, якщо стоїть — 0
        # (Але не перебиваємо шум від пострілу, який ставиться в attack())
        if dx == 0 and dy == 0:
            self.current_noise_radius = max(0, self.current_noise_radius - 2) # Плавне згасання спалаху шуму
        else:
            self.current_noise_radius = max(base_noise, self.current_noise_radius - 1)

        # Рух X з колізіями
        self.pos.x += dx
        self.hitbox.centerx = self.pos.x
        for obstacle in obstacles:
            if self.hitbox.colliderect(obstacle.rect):
                if dx > 0: self.hitbox.right = obstacle.rect.left
                if dx < 0: self.hitbox.left = obstacle.rect.right
                self.pos.x = self.hitbox.centerx

        # Рух Y з колізіями
        self.pos.y += dy
        self.hitbox.centery = self.pos.y
        for obstacle in obstacles:
            if self.hitbox.colliderect(obstacle.rect):
                if dy > 0: self.hitbox.bottom = obstacle.rect.top
                if dy < 0: self.hitbox.top = obstacle.rect.bottom
                self.pos.y = self.hitbox.centery

        # Обмеження під великий світ
        if self.pos.x < 0: self.pos.x = 0
        if self.pos.x > WORLD_WIDTH: self.pos.x = WORLD_WIDTH
        if self.pos.y < 0: self.pos.y = 0
        if self.pos.y > WORLD_HEIGHT: self.pos.y = WORLD_HEIGHT

        self.hitbox.center = self.pos

    def rotate_to_mouse(self, camera):
        if self.is_hidden: return

        mouse_x, mouse_y = pygame.mouse.get_pos()
        world_mouse_x = mouse_x - camera.camera_rect.x
        world_mouse_y = mouse_y - camera.camera_rect.y

        direction = pygame.math.Vector2(world_mouse_x - self.pos.x, world_mouse_y - self.pos.y)
        if direction.length() > 0:
            _, angle = direction.as_polar()
            angle = -angle
            self.image = pygame.transform.rotate(self.base_image, angle)
            self.rect = self.image.get_rect(center=self.pos)

    def change_weapon(self, index):
        if 0 <= index < len(self.weapons):
            self.current_weapon_index = index

    def attack(self, camera):
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
            # Ніж теж видає мікро-шум при змаху
            self.current_noise_radius = weapon_stats.get("noise_radius", 15)
            return "melee"

        # 3. Перевірка наявності набоїв
        if self.weapons_ammo[self.current_weapon] <= 0:
            return None

        # Витрачаємо один набій та встановлюємо спалах шуму з конфігу зброї!
        self.weapons_ammo[self.current_weapon] -= 1
        self.last_shot_time = current_time
        self.current_noise_radius = weapon_stats["noise_radius"]

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
        self.handle_movement(keys, obstacles)
        self.rotate_to_mouse(camera)