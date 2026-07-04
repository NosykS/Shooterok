# src/objects/bullet.py
import pygame


class Bullet(pygame.sprite.Sprite):
    def __init__(self, x: float, y: float, angle: float, damage: int, speed: float, is_enemy_bullet: bool = False):
        super().__init__()

        # Створюємо базову поверхню кулі (стрілка/прямокутник, що дивиться праворуч)
        base_image = pygame.Surface((12, 4), pygame.SRCALPHA)
        color = (255, 150, 0) if is_enemy_bullet else (255, 255, 0)
        base_image.fill(color)

        # ОПТИМІЗАЦІЯ ПОВОРОТУ: Pygame повертає ПРОТИ годинникової стрілки,
        # тому передаємо мінус кут, щоб збігалося з екранними координатами Y-вниз
        self.image = pygame.transform.rotate(base_image, -angle)
        self.rect = self.image.get_rect(center=(x, y))

        # Позиція кулі (float для плавності)
        self.pos = pygame.math.Vector2(x, y)

        # КРАЩИЙ ПІДХІД: Створюємо вектор напрямку праворуч і повертаємо його на потрібний кут
        # Вектори Pygame працюють у градусах, радіани рахувати не треба!
        self.velocity = pygame.math.Vector2(speed, 0).rotate(angle)

        self.damage = damage
        self.is_enemy_bullet = is_enemy_bullet  # Ключовий прапорець для перевірки колізій

    def update(self, map_width: int = 4000, map_height: int = 4000):
        """
        Оновлює позицію кулі. Приймає розміри карти для своєчасного видалення.
        """
        # Рух за вектором
        self.pos += self.velocity
        self.rect.center = self.pos

        # Видаляємо кулю, якщо вона вилетіла за реальні межі поточної карти
        if self.pos.x < 0 or self.pos.x > map_width or self.pos.y < 0 or self.pos.y > map_height:
            self.kill()