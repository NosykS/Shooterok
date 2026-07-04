# src/objects/obstacle.py
import pygame


class Obstacle(pygame.sprite.Sprite):
    def __init__(self, x: float, y: float, width: int, height: int, blocks_vision: bool = True,
                 blocks_bullets: bool = True):
        """
        x, y — лівий верхній кут перешкоди.
        width, height — розміри перешкоди в пікселях.
        blocks_vision — чи блокує цей об'єкт лінію зору ворога (для Raycast).
        blocks_bullets — чи зупиняє об'єкт кулі.
        """
        super().__init__()

        # ОПТИМІЗАЦІЯ: Створюємо поверхню та оптимізуємо її для швидкого рендерингу (.convert())
        self.image = pygame.Surface((width, height)).convert()

        # Колір залежить від типу перешкоди (наприклад, стіна — темніша, вікно/низький паркан — світліші)
        color = (70, 70, 70) if blocks_vision else (130, 130, 130)
        self.image.fill(color)

        # Сітка/контур навколо об'єкта, щоб у прототипі стіни не зливалися в одну суцільну пляму
        pygame.draw.rect(self.image, (40, 40, 40), (0, 0, width, height), 2)

        # Колізія в Pygame рахується через rect
        self.rect = self.image.get_rect(topleft=(x, y))

        # Зберігаємо центр для логіки ШІ, пошуку шляху (Pathfinding) або відскоків кулі
        self.pos = pygame.math.Vector2(self.rect.center)

        # СТЕЛС ТА БАЛІСТИКА: Параметри для взаємодії з іншими системами
        self.blocks_vision = blocks_vision
        self.blocks_bullets = blocks_bullets