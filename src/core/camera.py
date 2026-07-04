# src/core/camera.py
import pygame
from src.settings import SCREEN_WIDTH, SCREEN_HEIGHT


class Camera:
    def __init__(self, map_width: int, map_height: int):
        """
        map_width та map_height — це повні розміри всієї ігрової карти в пікселях.
        Наприклад, якщо карта 60x60 клітинок, а тайл 64x64, то розміри будуть 3840x3840.
        """
        # Створюємо Rect розміром з екран гри. Його topleft (x, y) буде зміщенням для малювання.
        self.camera_rect = pygame.Rect(0, 0, SCREEN_WIDTH, SCREEN_HEIGHT)
        self.map_width = map_width
        self.map_height = map_height

    def apply(self, entity: pygame.sprite.Sprite) -> pygame.Rect:
        """
        Зсуває прямокутник (rect) будь-якого ігрового об'єкта (гравець, ворог, кущ)
        на поточне зміщення камери. Використовується безпосередньо в screen.blit().
        """
        return entity.rect.move(self.camera_rect.topleft)

    def apply_rect(self, rect: pygame.Rect) -> pygame.Rect:
        """
        Аналог apply, але для звичайних pygame.Rect (наприклад, тайли стін чи декорацій).
        """
        return rect.move(self.camera_rect.topleft)

    def update(self, target):
        """
        Центрує камеру на об'єкті target (зазвичай це гравець).
        Пріоритет віддається target.pos (Vector2) для плавності, інакше використовується target.rect.
        """
        # ОПТИМІЗАЦІЯ: Перевіряємо наявність плавного вектора позиції pos, щоб уникнути мікро-дрижання
        if hasattr(target, 'pos'):
            target_x = target.pos.x
            target_y = target.pos.y
        else:
            target_x = target.rect.centerx
            target_y = target.rect.centery

        # Обчислюємо зміщення, щоб центр target збігався з центром екрана
        x = -int(target_x) + (SCREEN_WIDTH // 2)
        y = -int(target_y) + (SCREEN_HEIGHT // 2)

        # ОБМЕЖЕННЯ: Не дозволяємо камері виходити за межі ігрової карти
        x = min(0, x)  # Зупинка на лівій межі
        y = min(0, y)  # Зупинка на верхній межі

        # Права та нижня межі карти враховують ширину/висоту екрана
        # Використовуємо вбудований max(), як і було — це працює ідеально
        x = max(-(self.map_width - SCREEN_WIDTH), x)
        y = max(-(self.map_height - SCREEN_HEIGHT), y)

        # Зберігаємо координати зміщення
        self.camera_rect.topleft = (x, y)