# src/hiding_spot.py
import pygame

class HidingSpot(pygame.sprite.Sprite):
    def __init__(self, x, y, width=50, height=50):
        super().__init__()
        self.image = pygame.Surface((width, height), pygame.SRCALPHA)
        # Малюємо кущ (темно-зелене коло/квадрат)
        pygame.draw.rect(self.image, (34, 139, 34), (0, 0, width, height), border_radius=10)
        self.rect = self.image.get_rect(topleft=(x, y))
        self.pos = pygame.math.Vector2(self.rect.center)