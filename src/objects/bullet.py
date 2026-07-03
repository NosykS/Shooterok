# src/bullet.py
import pygame
import math


class Bullet(pygame.sprite.Sprite):
    def __init__(self, x, y, angle, damage, speed, is_enemy_bullet=False):
        super().__init__()
        self.image = pygame.Surface((8, 4), pygame.SRCALPHA)
        # Кулі ворогів нехай будуть жовто-гарячі, гравця — жовті
        color = (255, 150, 0) if is_enemy_bullet else (255, 255, 0)
        self.image.fill(color)

        # Поворот поверхні кулі за вектором руху
        self.image = pygame.transform.rotate(self.image, -angle)
        self.rect = self.image.get_rect(center=(x, y))

        self.pos = pygame.math.Vector2(x, y)
        rad = math.radians(angle)
        self.velocity = pygame.math.Vector2(math.cos(rad), math.sin(rad)) * speed

        self.damage = damage
        self.is_enemy_bullet = is_enemy_bullet  # Ключовий прапорець

    def update(self):
        self.pos += self.velocity
        self.rect.center = self.pos

        # Виліт за межі екрану (тимчасово за розмірами вікна, потім підв'яжемо під карту)
        if self.pos.x < 0 or self.pos.x > 2000 or self.pos.y < 0 or self.pos.y > 2000:
            self.kill()