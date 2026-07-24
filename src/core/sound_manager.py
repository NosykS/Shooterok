# src/core/sound_manager.py
import logging
import os

import pygame

logger = logging.getLogger(__name__)

SOUNDS_DIR = "assets/sounds"

# Relative volumes for individual effect categories (0.0 - 1.0)
_SFX_VOLUMES: dict[str, float] = {
    "weapon_knife": 0.7,
    "weapon_pistol_silenced": 0.6,
    "weapon_rifle": 0.7,
    "weapon_shotgun": 0.8,
    "player_death": 0.9,
    "enemy_death": 0.8,
    "footstep1": 0.35,
    "footstep2": 0.35,
    "defeat_jingle": 0.9,
    "victory_jingle": 0.9,
}

_SFX_FILES: dict[str, str] = {
    "weapon_knife": "weapons/knife.wav",
    "weapon_pistol_silenced": "weapons/pistol_silenced.wav",
    "weapon_rifle": "weapons/rifle.wav",
    "weapon_shotgun": "weapons/shotgun.wav",
    "player_death": "player_death.wav",
    "enemy_death": "enemy_death.wav",
    "footstep1": "footstep1.wav",
    "footstep2": "footstep2.wav",
    "defeat_jingle": "defeat_jingle.wav",
    "victory_jingle": "victory_jingle.wav",
}

MUSIC_PATH = os.path.join(SOUNDS_DIR, "music_ambient.wav")
MUSIC_VOLUME = 0.18


class SoundManager:
    """Centralized playback of sound effects and background music.

    If the audio subsystem is unavailable (no audio device, etc.), the manager
    silently disables itself (self.enabled = False) and the game keeps running
    without sound.
    """

    def __init__(self, sfx_volume: float = 1.0, music_volume: float = 1.0) -> None:
        self.enabled = True
        try:
            if pygame.mixer.get_init() is None:
                pygame.mixer.init()
        except pygame.error:
            logger.warning("Audio subsystem unavailable", exc_info=True)
            self.enabled = False

        self.sfx: dict[str, pygame.mixer.Sound] = {}
        self._music_state = "stopped"  # stopped | playing | paused
        self._footstep_toggle = False

        # Volume multipliers controlled by the player via the settings screen (0.0 - 1.0)
        self.sfx_volume = max(0.0, min(1.0, sfx_volume))
        self.music_volume = max(0.0, min(1.0, music_volume))

        if self.enabled:
            for key, rel_path in _SFX_FILES.items():
                self._load_sfx(key, rel_path)

    def _load_sfx(self, key: str, rel_path: str) -> None:
        path = os.path.join(SOUNDS_DIR, rel_path)
        try:
            sound = pygame.mixer.Sound(path)
            sound.set_volume(_SFX_VOLUMES.get(key, 0.7) * self.sfx_volume)
            self.sfx[key] = sound
        except (pygame.error, OSError):
            logger.warning("Failed to load sound file %s", path, exc_info=True)

    def set_sfx_volume(self, value: float) -> None:
        """Sets the overall SFX volume multiplier (0.0 - 1.0)."""
        self.sfx_volume = max(0.0, min(1.0, value))
        for key, sound in self.sfx.items():
            sound.set_volume(_SFX_VOLUMES.get(key, 0.7) * self.sfx_volume)

    def set_music_volume(self, value: float) -> None:
        """Sets the overall background music volume multiplier (0.0 - 1.0)."""
        self.music_volume = max(0.0, min(1.0, value))
        if self.enabled:
            pygame.mixer.music.set_volume(MUSIC_VOLUME * self.music_volume)

    def play(self, key: str) -> None:
        if not self.enabled:
            return
        sound = self.sfx.get(key)
        if sound:
            sound.play()

    def play_weapon(self, weapon_name: str) -> None:
        self.play(f"weapon_{weapon_name}")

    def play_footstep(self) -> None:
        """Alternates between two footstep samples for a more natural sound."""
        self._footstep_toggle = not self._footstep_toggle
        self.play("footstep1" if self._footstep_toggle else "footstep2")

    def start_music(self) -> None:
        """Starts (or resumes) background music. Only called during gameplay."""
        if not self.enabled or self._music_state == "playing":
            return

        if self._music_state == "paused":
            pygame.mixer.music.unpause()
        else:
            try:
                pygame.mixer.music.load(MUSIC_PATH)
                pygame.mixer.music.set_volume(MUSIC_VOLUME * self.music_volume)
                pygame.mixer.music.play(loops=-1)
            except (pygame.error, OSError):
                logger.warning("Failed to load background music", exc_info=True)
                return

        self._music_state = "playing"

    def pause_music(self) -> None:
        """Pauses background music (menu, pause, shop, etc.)."""
        if not self.enabled or self._music_state != "playing":
            return
        pygame.mixer.music.pause()
        self._music_state = "paused"

    def stop_music(self) -> None:
        """Fully stops background music (e.g. before the victory/defeat jingle)."""
        if not self.enabled:
            return
        pygame.mixer.music.stop()
        self._music_state = "stopped"

    def is_music_playing(self) -> bool:
        return self._music_state == "playing"
