# src/core/camera.py
from typing import Protocol

import pygame

from src.settings import SCREEN_WIDTH, SCREEN_HEIGHT


class _CameraTarget(Protocol):
    rect: pygame.Rect
    pos: pygame.math.Vector2


class Camera:
    def __init__(self, map_width: int, map_height: int) -> None:
        """
        map_width and map_height are the full size of the entire game map in
        pixels. For example, a 60x60-tile map with 64x64 tiles is 3840x3840.
        """
        # Rect the size of the screen. Its topleft (x, y) is the drawing offset.
        self.camera_rect = pygame.Rect(0, 0, SCREEN_WIDTH, SCREEN_HEIGHT)
        self.map_width = map_width
        self.map_height = map_height

    def apply(self, entity: pygame.sprite.Sprite) -> pygame.Rect:
        """
        Shifts a game object's rect (player, enemy, bush) by the current
        camera offset. Used directly in screen.blit().
        """
        return entity.rect.move(self.camera_rect.topleft)

    def apply_rect(self, rect: pygame.Rect) -> pygame.Rect:
        """Same as apply, but for plain pygame.Rect values (wall/decor tiles)."""
        return rect.move(self.camera_rect.topleft)

    def screen_to_world(self, screen_pos: tuple[int, int]) -> pygame.math.Vector2:
        """Converts screen coordinates (e.g. mouse position) to world coordinates."""
        return pygame.math.Vector2(
            screen_pos[0] - self.camera_rect.x,
            screen_pos[1] - self.camera_rect.y
        )

    def update(self, target: _CameraTarget) -> None:
        """
        Centers the camera on target (usually the player). target.pos (Vector2)
        is preferred for smoothness, falling back to target.rect otherwise.
        """
        # Prefer the smooth pos vector to avoid micro-jitter.
        if hasattr(target, "pos"):
            target_x = target.pos.x
            target_y = target.pos.y
        else:
            target_x = target.rect.centerx
            target_y = target.rect.centery

        # Offset so the target's center aligns with the screen's center.
        x = -int(target_x) + (SCREEN_WIDTH // 2)
        y = -int(target_y) + (SCREEN_HEIGHT // 2)

        # Clamp so the camera never scrolls past the map edges.
        x = min(0, x)  # Left edge
        y = min(0, y)  # Top edge

        # Right/bottom edges account for the screen's width/height.
        x = max(-(self.map_width - SCREEN_WIDTH), x)
        y = max(-(self.map_height - SCREEN_HEIGHT), y)

        self.camera_rect.topleft = (x, y)
