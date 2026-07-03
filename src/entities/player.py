# src/player.py
import pygame
from src.settings import SCREEN_WIDTH, SCREEN_HEIGHT, WEAPONS, PLAYER_SPEED_NORMAL, PLAYER_SPEED_STEALTH, \
    PLAYER_NOISE_NORMAL, PLAYER_NOISE_STEALTH
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

        # ДОДАНО: Зберігаємо точний час останнього пострілу/атаки в мілісекундах
        self.last_shot_time = 0

    def _create_placeholder_image(self):
        surface = pygame.Surface((50, 50), pygame.SRCALPHA)
        pygame.draw.circle(surface, (0, 128, 255), (25, 25), 20)
        pygame.draw.line(surface, (255, 0, 0), (25, 25), (50, 25), 4)
        return surface

    @property
    def current_weapon(self):
        return self.weapons[self.current_weapon_index]

    def handle_movement(self, keys, obstacles):
        if self.is_hidden:
            return  # Якщо сховався — рухатися не можна, поки не вийдеш

        # Перевірка на стелс-ходьбу (затиснутий Shift)
        if keys[pygame.K_LSHIFT]:
            self.speed = PLAYER_SPEED_STEALTH
            # Якщо гравець іде на Шифті, але стоїть на місці — шуму 0. Якщо йде — PLAYER_NOISE_STEALTH (0)
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

        # Обмеження екрану
        if self.pos.x < 0: self.pos.x = 0
        if self.pos.x > SCREEN_WIDTH: self.pos.x = SCREEN_WIDTH
        if self.pos.y < 0: self.pos.y = 0
        if self.pos.y > SCREEN_HEIGHT: self.pos.y = SCREEN_HEIGHT

        self.hitbox.center = self.pos

        # Якщо гравець не рухається, він не створює шуму кроками
        if dx == 0 and dy == 0:
            self.current_noise_radius = 0

    def rotate_to_mouse(self):
        if self.is_hidden: return
        mouse_x, mouse_y = pygame.mouse.get_pos()
        direction = pygame.math.Vector2(mouse_x - self.pos.x, mouse_y - self.pos.y)
        _, angle = direction.as_polar()
        angle = -angle
        self.image = pygame.transform.rotate(self.base_image, angle)
        self.rect = self.image.get_rect(center=self.pos)

    def change_weapon(self, index):
        if 0 <= index < len(self.weapons):
            self.current_weapon_index = index
            print(f"Зброя змінена на: {self.weapons[index]}")

    def attack(self):
        if self.is_hidden:
            return None  # Зі схованки стріляти не можна

        # ДОДАНО: Перевіряємо кулдаун за системним часом Pygame
        current_time = pygame.time.get_ticks()
        weapon_stats = WEAPONS[self.current_weapon]

        # Якщо з моменту минулої атаки пройшло менше мілісекунд, ніж вказано в shoot_cooldown — блокуємо постріл
        if current_time - self.last_shot_time < weapon_stats["shoot_cooldown"]:
            return None

        # Оновлюємо час останньої успішної атаки
        self.last_shot_time = current_time

        # Якщо обрано ніж — повертаємо маркер ближнього бою
        if self.current_weapon == "knife":
            return "melee"

        mouse_pos = pygame.mouse.get_pos()
        dir_vector = pygame.math.Vector2(mouse_pos) - self.pos

        if dir_vector.length() > 0:
            _, angle = dir_vector.as_polar()

            import random
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

    def update(self, keys, obstacles):
        self.handle_movement(keys, obstacles)
        self.rotate_to_mouse()