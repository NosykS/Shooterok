# src/core/ui.py
import pygame
import math
from src.settings import SCREEN_WIDTH, SCREEN_HEIGHT, WHITE, WEAPONS


# Клас кнопок з анімацією
class UIButton:
    def __init__(self, x, y, width, height, text, font, base_color, hover_color, action_value):
        self.text = text
        self.font = font
        self.base_color = base_color
        self.hover_color = hover_color
        self.action_value = action_value  # Що повертає кнопка при натисканні

        # Базові параметри геометрії
        self.original_rect = pygame.Rect(0, 0, width, height)
        self.original_rect.center = (x, y)

        # Поточний rect (може змінюватись для анімації)
        self.rect = self.original_rect.copy()
        self.current_color = self.base_color

        # Стани для анімації
        self.is_hovered = False
        self.is_pressed = False

    def update(self, mouse_pos, mouse_click):
        self.is_hovered = self.original_rect.collidepoint(mouse_pos)

        if self.is_hovered:
            self.current_color = self.hover_color
            if mouse_click[0]:  # Ліва кнопка миші затиснута
                self.is_pressed = True
                # Ефект натискання: кнопка візуально трохи зменшується
                self.rect = self.original_rect.inflate(-6, -6)
            else:
                if self.is_pressed:  # Кнопку відпустили над нею -> КЛІК!
                    self.is_pressed = False
                    self.rect = self.original_rect.copy()
                    return self.action_value
                self.rect = self.original_rect.copy()
        else:
            self.current_color = self.base_color
            self.is_pressed = False
            self.rect = self.original_rect.copy()

        return None

    def draw(self, screen):
        # Малюємо тінь для об'єму (зміщення на 4 пікселі вниз і вправо)
        shadow_rect = self.rect.move(4, 4)
        pygame.draw.rect(screen, (10, 10, 15), shadow_rect, border_radius=8)

        # Малюємо саму кнопку
        pygame.draw.rect(screen, self.current_color, self.rect, border_radius=8)
        # Рамка навколо кнопки
        pygame.draw.rect(screen, (255, 255, 255), self.rect, width=2, border_radius=8)

        # Текст по центру кнопки
        text_surf = self.font.render(self.text, True, (255, 255, 255))
        text_rect = text_surf.get_rect(center=self.rect.center)
        screen.blit(text_surf, text_rect)


def draw_controls_help(screen, font_ui):
    """Малює підказки керування, використовуючи переданий шрифт гри"""
    controls = [
        "CONTROLS:",
        "WASD - Movement",
        "LSHIFT - Slow Stealth Walk",
        "HOLD MOUSE - Continuous Attack",
        "1, 2, 3 - Switch Weapons",
        "E - Enter / Exit Cover (Bush)",
        "R - Manual Reset Level"
    ]
    start_y = 20
    for idx, line in enumerate(controls):
        color = (200, 200, 200) if idx > 0 else (255, 200, 50)
        txt = font_ui.render(line, True, color)
        screen.blit(txt, (SCREEN_WIDTH - 290, start_y + idx * 22))


def draw_player_bars(screen, player, font_small):
    # --- СМУЖКА ЗДОРОВ'Я (HP) ---
    hp_bar_rect = pygame.Rect(20, 20, 200, 20)
    pygame.draw.rect(screen, (80, 0, 0), hp_bar_rect)

    # Запобігаємо виходу смужки за межі при від'ємному HP
    hp_ratio = max(0.0, min(1.0, player.hp / player.max_hp))
    hp_width = int(hp_ratio * 200)

    if hp_width > 0:
        pygame.draw.rect(screen, (220, 20, 20), pygame.Rect(20, 20, hp_width, 20))
    pygame.draw.rect(screen, WHITE, hp_bar_rect, 2)

    hp_text = font_small.render(f"HP: {max(0, player.hp)}/{player.max_hp}", True, WHITE)
    screen.blit(hp_text, (25, 21))

    # --- СМУЖКА БРОНІ (ARMOR) ---
    armor_bar_rect = pygame.Rect(20, 45, 200, 15)
    pygame.draw.rect(screen, (0, 0, 80), armor_bar_rect)

    armor_ratio = max(0.0, min(1.0, player.armor / player.max_armor))
    armor_width = int(armor_ratio * 200)

    if armor_width > 0:
        pygame.draw.rect(screen, (0, 120, 255), pygame.Rect(20, 45, armor_width, 15))
    pygame.draw.rect(screen, WHITE, armor_bar_rect, 2)

    armor_text = font_small.render(f"ARMOR: {player.armor}/{player.max_armor}", True, WHITE)
    screen.blit(armor_text, (25, 44))


def draw_game_ui(screen, player, enemies, keys, font_small):
    """ФІКС: Прибрано дублюючий аргумент WEAPONS, додано загальний стелс-індикатор небезпеки"""
    weapon_name = player.current_weapon.upper()

    weapon_stats = WEAPONS.get(player.current_weapon, WEAPONS["pistol_silenced"])

    if weapon_stats['ammo_capacity'] > 0:
        ammo_str = f"AMMO: {player.ammo}/{weapon_stats['ammo_capacity']}"
    else:
        ammo_str = "AMMO: INF"

    stealth_status = "STEALTH" if keys[pygame.K_LSHIFT] else "RUNNING"
    if player.is_hidden:
        stealth_status = "HIDDEN"

    # --- РОЗРАХУНОК ЗАГАЛЬНОГО СТАНУ ЗАГРОЗИ ---
    max_suspicion = 0.0
    any_alerted = False

    for enemy in enemies:
        if enemy.is_alerted:
            any_alerted = True
        if enemy.suspicion > max_suspicion:
            max_suspicion = enemy.suspicion

    if any_alerted:
        threat_status = "ALERT"
        threat_color = (255, 0, 0)
    elif max_suspicion > 0:
        threat_status = f"CAUTION ({int(max_suspicion * 100)}%)"
        threat_color = (255, 165, 0)
    else:
        threat_status = "HIDDEN" if player.is_hidden else "CLEAR"
        threat_color = (0, 255, 100)

    # Виведення тексту інтерфейсу
    weapon_ui_text = font_small.render(f"WEAPON: {weapon_name}  [{ammo_str}]", True, (255, 200, 50))
    status_ui_text = font_small.render(f"MODE: {stealth_status}  |  ENEMIES LEFT: {len(enemies)}", True, WHITE)
    threat_ui_text = font_small.render(f"THREAT LEVEL: {threat_status}", True, threat_color)

    screen.blit(weapon_ui_text, (20, SCREEN_HEIGHT - 85))
    screen.blit(status_ui_text, (20, SCREEN_HEIGHT - 55))
    screen.blit(threat_ui_text, (20, SCREEN_HEIGHT - 25))

def draw_gunshot_flash(screen, camera, position, radius, timer):
    """Малює спалах згасаючого звукового/візуального шуму пострілу"""
    s = pygame.Surface((radius * 2, radius * 2), pygame.SRCALPHA)
    alpha = int((timer / 8) * 140)  # Обчислення прозорості
    pygame.draw.circle(s, (100, 200, 255, alpha), (radius, radius), radius, 3)

    flash_x = position[0] - radius + camera.camera_rect.x
    flash_y = position[1] - radius + camera.camera_rect.y
    screen.blit(s, (flash_x, flash_y))


def draw_knife_swing(screen, camera, player, attack_radius):
    """Розраховує та малює конус атаки бойовим ножем відповідно до миші"""
    mouse_pos = pygame.mouse.get_pos()
    world_mouse = pygame.math.Vector2(
        mouse_pos[0] - camera.camera_rect.x,
        mouse_pos[1] - camera.camera_rect.y
    )

    player_to_mouse = world_mouse - player.pos
    player_angle = player_to_mouse.as_polar()[1] if player_to_mouse.length() > 0 else 0

    knife_surf = pygame.Surface((screen.get_width(), screen.get_height()), pygame.SRCALPHA)
    player_screen_pos = player.pos + pygame.math.Vector2(camera.camera_rect.topleft)

    points = [player_screen_pos]
    num_segments = 16
    view_angle = 90
    start_angle = player_angle - view_angle / 2

    for i in range(num_segments + 1):
        ang = start_angle + (view_angle / num_segments) * i
        rad = math.radians(ang)
        world_point = player.pos + pygame.math.Vector2(math.cos(rad), math.sin(rad)) * attack_radius
        points.append(world_point + pygame.math.Vector2(camera.camera_rect.topleft))

    if len(points) >= 3:
        pygame.draw.polygon(knife_surf, (255, 50, 50, 40), points)
        pygame.draw.lines(knife_surf, (255, 100, 100, 150), False, points[1:], 2)

    screen.blit(knife_surf, (0, 0))