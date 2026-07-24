# src/core/physics.py
from src.settings import TILE_SIZE


def get_nearby_obstacles(pos, obstacles, radius=TILE_SIZE * 2):
    """
    Фільтрує перешкоди поблизу позиції, щоб не перевіряти колізії з усією картою
    на кожному кадрі для кожної сутності (гравця чи ворога).
    """
    return [
        obs for obs in obstacles
        if abs(obs.rect.centerx - pos.x) < radius and abs(obs.rect.centery - pos.y) < radius
    ]


def resolve_axis_collision(pos, hitbox, obstacles, axis, delta):
    """
    Зсуває позицію та hitbox сутності по одній осі ('x' або 'y') на delta пікселів
    і відкочує рух назад до межі стіни при колізії з перешкодою зі списку obstacles.
    Список obstacles очікується вже відфільтрованим (див. get_nearby_obstacles).
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
