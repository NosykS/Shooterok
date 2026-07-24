# src/objects/obstacle.py
import pygame


class Obstacle(pygame.sprite.Sprite):
    def __init__(
        self, x: float, y: float, width: int, height: int,
        blocks_vision: bool = True, blocks_bullets: bool = True,
    ) -> None:
        """
        x, y — top-left corner of the obstacle.
        width, height — obstacle size in pixels.
        blocks_vision — whether this object blocks enemy line of sight (raycast).
        blocks_bullets — whether this object stops bullets.
        """
        super().__init__()

        # .convert() optimizes the surface for fast blitting
        self.image = pygame.Surface((width, height)).convert()

        # Color depends on the obstacle type (e.g. wall is darker, window/low fence is lighter)
        color = (70, 70, 70) if blocks_vision else (130, 130, 130)
        self.image.fill(color)

        # Outline so adjacent walls don't visually blend into one solid blob
        pygame.draw.rect(self.image, (40, 40, 40), (0, 0, width, height), 2)

        # Pygame collisions are computed via rect
        self.rect = self.image.get_rect(topleft=(x, y))

        # Center point, used by AI/pathfinding and bullet collision logic
        self.pos = pygame.math.Vector2(self.rect.center)

        # Stealth & ballistics: how this obstacle interacts with other systems
        self.blocks_vision = blocks_vision
        self.blocks_bullets = blocks_bullets
