# src/core/sound_manager.py
import os
import pygame

SOUNDS_DIR = "assets/sounds"

# Відносні гучності для окремих категорій ефектів (0.0 - 1.0)
_SFX_VOLUMES = {
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

_SFX_FILES = {
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
    """Централізоване відтворення звукових ефектів та фонової музики.

    Якщо звукова підсистема недоступна (немає аудіопристрою тощо), менеджер
    тихо вимикається (self.enabled = False), і гра продовжує працювати без звуку.
    """

    def __init__(self, sfx_volume=1.0, music_volume=1.0):
        self.enabled = True
        try:
            if pygame.mixer.get_init() is None:
                pygame.mixer.init()
        except Exception as e:
            print(f"[SOUND] Аудіопідсистема недоступна: {e}")
            self.enabled = False

        self.sfx = {}
        self._music_state = "stopped"  # stopped | playing | paused
        self._footstep_toggle = False

        # Множники гучності, які регулюються гравцем через екран налаштувань (0.0 - 1.0)
        self.sfx_volume = max(0.0, min(1.0, sfx_volume))
        self.music_volume = max(0.0, min(1.0, music_volume))

        if self.enabled:
            for key, rel_path in _SFX_FILES.items():
                self._load_sfx(key, rel_path)

    def _load_sfx(self, key, rel_path):
        path = os.path.join(SOUNDS_DIR, rel_path)
        try:
            sound = pygame.mixer.Sound(path)
            sound.set_volume(_SFX_VOLUMES.get(key, 0.7) * self.sfx_volume)
            self.sfx[key] = sound
        except Exception as e:
            print(f"[SOUND] Не вдалося завантажити {path}: {e}")

    def set_sfx_volume(self, value):
        """Встановлює загальний множник гучності ефектів (0.0 - 1.0)"""
        self.sfx_volume = max(0.0, min(1.0, value))
        for key, sound in self.sfx.items():
            sound.set_volume(_SFX_VOLUMES.get(key, 0.7) * self.sfx_volume)

    def set_music_volume(self, value):
        """Встановлює загальний множник гучності фонової музики (0.0 - 1.0)"""
        self.music_volume = max(0.0, min(1.0, value))
        if self.enabled:
            pygame.mixer.music.set_volume(MUSIC_VOLUME * self.music_volume)

    def play(self, key):
        if not self.enabled:
            return
        sound = self.sfx.get(key)
        if sound:
            sound.play()

    def play_weapon(self, weapon_name):
        self.play(f"weapon_{weapon_name}")

    def play_footstep(self):
        """Чергує два семпли кроків для природнішого звучання ходьби"""
        self._footstep_toggle = not self._footstep_toggle
        self.play("footstep1" if self._footstep_toggle else "footstep2")

    def start_music(self):
        """Запускає (або знімає з паузи) фонову музику. Викликається лише під час гри."""
        if not self.enabled or self._music_state == "playing":
            return

        if self._music_state == "paused":
            pygame.mixer.music.unpause()
        else:
            try:
                pygame.mixer.music.load(MUSIC_PATH)
                pygame.mixer.music.set_volume(MUSIC_VOLUME * self.music_volume)
                pygame.mixer.music.play(loops=-1)
            except Exception as e:
                print(f"[SOUND] Не вдалося завантажити фонову музику: {e}")
                return

        self._music_state = "playing"

    def pause_music(self):
        """Ставить фонову музику на паузу (меню, пауза, магазин тощо)"""
        if not self.enabled or self._music_state != "playing":
            return
        pygame.mixer.music.pause()
        self._music_state = "paused"

    def stop_music(self):
        """Повністю зупиняє фонову музику (напр. перед мелодією перемоги/програшу)"""
        if not self.enabled:
            return
        pygame.mixer.music.stop()
        self._music_state = "stopped"

    def is_music_playing(self):
        return self._music_state == "playing"
