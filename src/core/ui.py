#src/ui.py
import pygame
from src.settings import SCREEN_WIDTH, SCREEN_HEIGHT, WHITE, WEAPONS


font_large = None
font_medium = None
font_small = None


def init_fonts():
    """Цю функцію ми викличемо всередині кожної UI-функції, щоб створити шрифти в потрібний момент"""
    global font_large, font_medium, font_small

    pygame.font.init()

    # Якщо шрифти ще не створені — створюємо їх
    if font_large is None:
        font_large = pygame.font.SysFont("Arial", 48, bold=True)
        font_medium = pygame.font.SysFont("Arial", 28)
        font_small = pygame.font.SysFont("Arial", 18)

def draw_menu(screen):
    init_fonts()
    screen.fill((20, 25, 30))
    title_text = font_large.render("MILITARY STEALTH SHOOTER", True, (200, 50, 50))
    subtitle_text = font_medium.render("Hardcore Tactical Stealth", True, (150, 150, 150))
    play_button = font_medium.render("[ 1 ] START MISSION", True, WHITE)
    exit_button = font_medium.render("[ ESC ] ABANDON", True, (120, 120, 120))

    screen.blit(title_text, (SCREEN_WIDTH // 2 - title_text.get_width() // 2, 150))
    screen.blit(subtitle_text, (SCREEN_WIDTH // 2 - subtitle_text.get_width() // 2, 220))
    screen.blit(play_button, (SCREEN_WIDTH // 2 - play_button.get_width() // 2, 380))
    screen.blit(exit_button, (SCREEN_WIDTH // 2 - exit_button.get_width() // 2, 440))


def draw_game_over(screen):
    init_fonts()
    screen.fill((40, 10, 10))
    title_text = font_large.render("MISSION FAILED", True, (255, 0, 0))
    retry_text = font_medium.render("Press [ R ] to Restart", True, WHITE)
    menu_text = font_medium.render("Press [ M ] for Main Menu", True, (150, 150, 150))
    exit_text = font_medium.render("Press [ ESC ] to Quit Game", True, (200, 50, 50))

    screen.blit(title_text, (SCREEN_WIDTH // 2 - title_text.get_width() // 2, 180))
    screen.blit(retry_text, (SCREEN_WIDTH // 2 - retry_text.get_width() // 2, 300))
    screen.blit(menu_text, (SCREEN_WIDTH // 2 - menu_text.get_width() // 2, 360))
    screen.blit(exit_text, (SCREEN_WIDTH // 2 - exit_text.get_width() // 2, 420))


def draw_victory(screen):
    init_fonts()
    screen.fill((10, 35, 15))
    title_text = font_large.render("MISSION ACCOMPLISHED", True, (0, 255, 100))
    retry_text = font_medium.render("Press [ R ] to Play Again", True, WHITE)
    menu_text = font_medium.render("Press [ M ] for Main Menu", True, (150, 150, 150))
    exit_text = font_medium.render("Press [ ESC ] to Quit Game", True, (200, 50, 50))

    screen.blit(title_text, (SCREEN_WIDTH // 2 - title_text.get_width() // 2, 180))
    screen.blit(retry_text, (SCREEN_WIDTH // 2 - retry_text.get_width() // 2, 300))
    screen.blit(menu_text, (SCREEN_WIDTH // 2 - menu_text.get_width() // 2, 360))
    screen.blit(exit_text, (SCREEN_WIDTH // 2 - exit_text.get_width() // 2, 420))


def draw_controls_help(screen):
    init_fonts()
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
        txt = font_small.render(line, True, color)
        screen.blit(txt, (SCREEN_WIDTH - 230, start_y + idx * 22))


def draw_player_bars(screen, player):
    hp_bar_rect = pygame.Rect(20, 20, 200, 20)
    pygame.draw.rect(screen, (80, 0, 0), hp_bar_rect)
    hp_width = int((player.hp / player.max_hp) * 200)
    if hp_width > 0:
        pygame.draw.rect(screen, (220, 20, 20), pygame.Rect(20, 20, hp_width, 20))
    pygame.draw.rect(screen, WHITE, hp_bar_rect, 2)

    hp_text = font_small.render(f"HP: {max(0, player.hp)}/{player.max_hp}", True, WHITE)
    screen.blit(hp_text, (25, 21))

    armor_bar_rect = pygame.Rect(20, 45, 200, 15)
    pygame.draw.rect(screen, (0, 0, 80), armor_bar_rect)
    armor_width = int((player.armor / player.max_armor) * 200) # FIX: Changed player.armor to player.max_armor
    if armor_width > 0:
        pygame.draw.rect(screen, (0, 120, 255), pygame.Rect(20, 45, armor_width, 15))
    pygame.draw.rect(screen, WHITE, armor_bar_rect, 2)

    armor_text = font_small.render(f"ARMOR: {player.armor}/{player.max_armor}", True, WHITE)
    screen.blit(armor_text, (25, 44))


def draw_game_ui(screen, player, enemies, keys, WEAPONS):
    weapon_name = player.current_weapon.upper()
    weapon_stats = WEAPONS[player.current_weapon]

    ammo_str = f"AMMO: {weapon_stats['ammo_capacity']}/{weapon_stats['ammo_capacity']}" if weapon_stats['ammo_capacity'] > 0 else "AMMO: INF"

    stealth_status = "STEALTH" if keys[pygame.K_LSHIFT] else "RUNNING"
    if player.is_hidden: stealth_status = "HIDDEN"

    weapon_ui_text = font_medium.render(f"WEAPON: {weapon_name}  [{ammo_str}]", True, (255, 200, 50))
    status_ui_text = font_medium.render(f"MODE: {stealth_status}  |  ENEMIES LEFT: {len(enemies)}", True, WHITE)

    screen.blit(weapon_ui_text, (20, SCREEN_HEIGHT - 65))
    screen.blit(status_ui_text, (20, SCREEN_HEIGHT - 35))
