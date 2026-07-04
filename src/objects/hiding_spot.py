# src/objects/hiding_spot.py
import pygame


class HidingSpot(pygame.sprite.Sprite):
    def __init__(self, x: float, y: float, width: int = 64, height: int = 64):
        """
        x, y — координати лівого верхнього кута куща (topleft).
        Змінив дефолтний розмір на 64x64, щоб він гарно вписувався в стандартну сітку тайлів.
        """
        super().__init__()

        self.image = pygame.Surface((width, height), pygame.SRCALPHA)
        # Малюємо кущ (темно-зелений із заокругленими кутами)
        pygame.draw.rect(self.image, (34, 139, 34), (0, 0, width, height), border_radius=12)

        self.rect = self.image.get_rect(topleft=(x, y))

        # Зберігаємо центр для логіки ШІ (наприклад, куди ворогу дивитися/йти перевіряти)
        self.pos = pygame.math.Vector2(self.rect.center)

        # СТЕЛС-МЕХАНІКА: Список сутностей (гравець/вороги), які зараз всередині цього куща
        self.contained_entities = set()

    def is_entity_hidden(self, entity) -> bool:
        """
        Перевіряє, чи сутність (наприклад, гравець) знаходиться глибоко в кущі.
        Можна перевіряти за колізією центрів, щоб гравець не вважався схованим,
        якщо він просто торкнувся куща мізинцем ноги.
        """
        return self.rect.collidepoint(entity.rect.center)

    def update(self):
        """
        Тут можна буде додавати анімацію колишерня куща,
        якщо гравець всередині активно рухається або стріляє.
        """
        pass