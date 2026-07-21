# src/objects/hiding_spot.py
import pygame

class HidingSpot(pygame.sprite.Sprite):
    def __init__(self, x: float, y: float, width: int = 64, height: int = 64, custom_exit_pos=None):
        super().__init__()

        self.image = pygame.Surface((width, height), pygame.SRCALPHA)
        pygame.draw.rect(self.image, (34, 139, 34), (0, 0, width, height), border_radius=12)

        self.rect = self.image.get_rect(topleft=(x, y))
        self.pos = pygame.math.Vector2(self.rect.center)

        # Якщо в Tiled задана точна точка виходу — використовуємо її,
       # інакше за замовчуванням викидаємо на 45 пікселів праворуч (на дорогу)
        if custom_exit_pos:
            self.exit_pos = pygame.math.Vector2(custom_exit_pos)
        else:
            self.exit_pos = pygame.math.Vector2(self.rect.centerx + 45, self.rect.centery)

        self.contained_entities = set()

    def is_entity_hidden(self, entity) -> bool:
        return self.rect.collidepoint(entity.rect.center)

    def update(self):
        pass