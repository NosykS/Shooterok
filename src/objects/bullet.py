# src/objects/bullet.py
import pygame


class Bullet(pygame.sprite.Sprite):
    def __init__(
        self, x: float, y: float, angle: float, damage: float, speed: float,
        is_enemy_bullet: bool = False, falloff: float = 1.0,
    ) -> None:
        super().__init__()

        # Base bullet surface (arrow/rectangle facing right)
        base_image = pygame.Surface((12, 4), pygame.SRCALPHA)
        color = (255, 150, 0) if is_enemy_bullet else (255, 255, 0)
        base_image.fill(color)

        # Pygame rotates counter-clockwise, so we negate the angle to match
        # screen coordinates where Y increases downward.
        self.image = pygame.transform.rotate(base_image, -angle)
        self.rect = self.image.get_rect(center=(x, y))

        # Bullet position (float for smooth movement)
        self.pos = pygame.math.Vector2(x, y)

        # Direction vector: start facing right, then rotate to the target angle
        self.velocity = pygame.math.Vector2(speed, 0).rotate(angle)

        self.damage = damage
        self.original_damage = damage  # Kept to compute damage falloff over distance
        self.is_enemy_bullet = is_enemy_bullet  # Used by collision handling
        self.falloff = falloff  # Per-frame damage falloff multiplier

    def update(self, map_width: int = 4000, map_height: int = 4000) -> None:
        self.pos += self.velocity
        self.rect.center = self.pos

        # --- DAMAGE FALLOFF OVER DISTANCE ---
        if not getattr(self, "is_enemy_bullet", False) and self.falloff < 1.0:
            # Damage only decays if the falloff multiplier is below 1
            self.damage = max(self.damage * self.falloff, self.original_damage * 0.25)

        # Remove once the bullet leaves the map bounds
        if self.pos.x < 0 or self.pos.x > map_width or self.pos.y < 0 or self.pos.y > map_height:
            self.kill()
