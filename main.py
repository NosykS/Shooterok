# main.py
import logging
import sys

import pygame

from src.settings import SCREEN_WIDTH, SCREEN_HEIGHT
from src.core.game import Game


def main() -> None:
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
        datefmt="%H:%M:%S",
    )

    # Initialize Pygame and create the game window
    pygame.init()
    screen = pygame.display.set_mode((SCREEN_WIDTH, SCREEN_HEIGHT))
    pygame.display.set_caption("Military Stealth Shooter: Hardcore Stealth")

    # Create and run the game object
    game = Game(screen)
    game.run()

    # Shut down the application
    pygame.quit()
    sys.exit()


if __name__ == "__main__":
    main()