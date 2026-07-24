# src/objects/mission_elements.py
import pygame

from src.settings import TILE_SIZE


class ExitZone(pygame.sprite.Sprite):
    def __init__(self, x: float, y: float) -> None:
        super().__init__()
        self.image = pygame.Surface((TILE_SIZE, TILE_SIZE), pygame.SRCALPHA)
        # Blue/gray extraction zone square with a border
        pygame.draw.rect(self.image, (0, 100, 255, 100), (0, 0, TILE_SIZE, TILE_SIZE))
        pygame.draw.rect(self.image, (0, 150, 255), (0, 0, TILE_SIZE, TILE_SIZE), 3)
        self.rect = self.image.get_rect(topleft=(x, y))


class DataDrive(pygame.sprite.Sprite):
    def __init__(self, x: float, y: float) -> None:
        super().__init__()
        self.image = pygame.Surface((24, 24), pygame.SRCALPHA)
        # Yellow folder/documents icon
        pygame.draw.rect(self.image, (230, 180, 40), (2, 4, 20, 16), border_radius=2)
        pygame.draw.rect(self.image, (255, 255, 255), (6, 2, 8, 4))  # Folder tab
        self.rect = self.image.get_rect(center=(x + TILE_SIZE // 2, y + TILE_SIZE // 2))
