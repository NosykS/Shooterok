# src/core/physics.py
from typing import Iterable, Literal

import pygame

from src.settings import TILE_SIZE


def get_nearby_obstacles(
    pos: pygame.math.Vector2,
    obstacles: Iterable[pygame.sprite.Sprite],
    radius: float = TILE_SIZE * 2,
) -> list[pygame.sprite.Sprite]:
    """
    Filters obstacles near a position so collisions aren't checked against the
    whole map every frame for every entity (player or enemy).
    """
    return [
        obs for obs in obstacles
        if abs(obs.rect.centerx - pos.x) < radius and abs(obs.rect.centery - pos.y) < radius
    ]


def resolve_axis_collision(
    pos: pygame.math.Vector2,
    hitbox: pygame.Rect,
    obstacles: Iterable[pygame.sprite.Sprite],
    axis: Literal["x", "y"],
    delta: float,
) -> None:
    """
    Shifts an entity's position and hitbox along one axis ('x' or 'y') by delta
    pixels and rolls the movement back to the wall boundary on collision with
    an obstacle from the given list. The obstacle list is expected to already
    be filtered (see get_nearby_obstacles).
    """
    if delta == 0:
        return

    if axis == "x":
        pos.x += delta
        hitbox.centerx = round(pos.x)
        for obstacle in obstacles:
            if hitbox.colliderect(obstacle.rect):
                if delta > 0:
                    hitbox.right = obstacle.rect.left
                elif delta < 0:
                    hitbox.left = obstacle.rect.right
                pos.x = hitbox.centerx
    else:
        pos.y += delta
        hitbox.centery = round(pos.y)
        for obstacle in obstacles:
            if hitbox.colliderect(obstacle.rect):
                if delta > 0:
                    hitbox.bottom = obstacle.rect.top
                elif delta < 0:
                    hitbox.top = obstacle.rect.bottom
                pos.y = hitbox.centery
