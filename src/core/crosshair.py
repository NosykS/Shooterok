# src/core/crosshair.py
import pygame
import math


class CrosshairController:
    def __init__(self):
        # Приховуємо системний курсор
        pygame.mouse.set_visible(False)
        self.screen_pos = (0, 0)

    def update(self, player, camera, knife_radius, game_state):
        if game_state != "PLAYING":
            pygame.mouse.set_visible(True)
            return

        pygame.mouse.set_visible(False)
        mouse_pos = pygame.mouse.get_pos()

        if player.current_weapon == "knife":
            # Переводимо екранну позицію миші у світові координати
            world_mouse = pygame.math.Vector2(
                mouse_pos[0] - camera.camera_rect.x,
                mouse_pos[1] - camera.camera_rect.y
            )

            # Вектор від гравця до миші
            to_mouse = world_mouse - player.pos

            # Якщо миша далі за радіус ножа — обмежуємо
            if to_mouse.length() > knife_radius:
                to_mouse.scale_to_length(knife_radius)

            limited_world_pos = player.pos + to_mouse

            # Повертаємо в екранні координати
            self.screen_pos = (
                int(limited_world_pos.x + camera.camera_rect.x),
                int(limited_world_pos.y + camera.camera_rect.y)
            )
        else:
            self.screen_pos = mouse_pos

    def draw(self, screen, player):
        """Малює відповідний приціл залежно від зброї"""
        x, y = self.screen_pos

        if player.current_weapon == "knife":
            # Приціл для ножа (кільце з точкою)
            pygame.draw.circle(screen, (255, 80, 80), (x, y), 6, 2)
            pygame.draw.circle(screen, (255, 255, 255), (x, y), 2)
        else:
            # Приціл для вогнепалу (зелений хрестик)
            color = (0, 255, 150)
            length, gap = 8, 4
            pygame.draw.line(screen, color, (x - length - gap, y), (x - gap, y), 2)
            pygame.draw.line(screen, color, (x + gap, y), (x + length + gap, y), 2)
            pygame.draw.line(screen, color, (x, y - length - gap), (x, y - gap), 2)
            pygame.draw.line(screen, color, (x, y + gap), (x, y + length + gap), 2)