# main.py
import pygame
import sys
from src.settings import SCREEN_WIDTH, SCREEN_HEIGHT
from src.core.game import Game

def main():
    # Ініціалізація Pygame та створення вікна
    pygame.init()
    screen = pygame.display.set_mode((SCREEN_WIDTH, SCREEN_HEIGHT))
    pygame.display.set_caption("Military Stealth Shooter: Hardcore Stealth")

    # Створення та запуск об'єкта гри
    game = Game(screen)
    game.run()

    # Завершення роботи програми
    pygame.quit()
    sys.exit()

if __name__ == "__main__":
    main()