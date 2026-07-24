# src/core/sprite_loader.py
import logging

import pygame

logger = logging.getLogger(__name__)


def load_character_sprite(image_path: str) -> pygame.Surface | None:
    """
    Attempts to load a character sprite from disk. Returns None on failure so
    the caller can fall back to a generated placeholder image instead of
    crashing the game.
    """
    try:
        return pygame.image.load(image_path).convert_alpha()
    except (pygame.error, OSError):
        logger.warning("Failed to load sprite %s, using a placeholder instead", image_path, exc_info=True)
        return None
