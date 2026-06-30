# src/obstacle.py
import pygame


class Obstacle(pygame.sprite.Sprite):
    def __init__(self, x, y, width, height):
        super().__init__()
        # Створюємо поверхню заданого розміру
        self.image = pygame.Surface((width, height))
        self.image.fill((100, 100, 100))  # Сірий колір для стін

        # Задаємо позицію (колізія в Pygame рахується через rect)
        self.rect = self.image.get_rect(topleft=(x, y))
        self.pos = pygame.math.Vector2(self.rect.center)