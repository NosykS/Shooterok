# main.py
import gc
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

    # The cyclic garbage collector's periodic sweep was causing a reproducible
    # stutter mid-gameplay (profiled 24.08.2026 — a full gc.collect() pass over
    # the level's object graph, e.g. right after a level load builds a lot of
    # short-lived objects). Reference counting already frees the vast majority
    # of game objects immediately with GC disabled; LevelManager.reset_game_world
    # runs a manual collect() at level-load time instead, where a brief pause
    # is invisible to the player, so cyclic garbage (e.g. sprite<->group refs)
    # still gets reclaimed rather than growing unbounded over a long session.
    gc.disable()

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