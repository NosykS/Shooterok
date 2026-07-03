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

    def apply(self, entity) -> pygame.Rect:
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
        target повинен мати атрибут target.rect.
        """
        # Обчислюємо зміщення, щоб центр target збігався з центром екрана
        x = -target.rect.centerx + int(SCREEN_WIDTH / 2)
        y = -target.rect.centery + int(SCREEN_HEIGHT / 2)

        # ОГРАНИЧЕННЯ: Не дозволяємо камері виходити за межі ігрової карти
        x = min(0, x)  # Зупинка на лівій межі
        y = min(0, y)  # Зупинка на верхній межі

        # Права та нижня межі карти враховують ширину/висоту екрана
        x = max(-(self.map_width - SCREEN_WIDTH), x)
        y = max(-(self.map_height - SCREEN_HEIGHT), y)

        # Зберігаємо координати зміщення
        self.camera_rect.topleft = (x, y)