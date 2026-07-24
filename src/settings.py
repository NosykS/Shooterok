# src/settings.py
from typing import Any

FPS: int = 60

# Size of a single map tile (grid cell)
TILE_SIZE: int = 32
GRID_WIDTH: int = 40
GRID_HEIGHT: int = 24

SCREEN_WIDTH: int = GRID_WIDTH * TILE_SIZE    # 40 * 32 = 1280
SCREEN_HEIGHT: int = GRID_HEIGHT * TILE_SIZE  # 24 * 32 = 768

# SIZE OF THE LARGE GAME WORLD (the world the camera scrolls across)
WORLD_GRID_WIDTH: int = 90   # Tiles wide (90 * 32 = 2880 pixels)
WORLD_GRID_HEIGHT: int = 60  # Tiles tall (60 * 32 = 1920 pixels)

WORLD_WIDTH: int = WORLD_GRID_WIDTH * TILE_SIZE
WORLD_HEIGHT: int = WORLD_GRID_HEIGHT * TILE_SIZE

# Colors
BG_COLOR: tuple[int, int, int] = (30, 30, 40)
WHITE: tuple[int, int, int] = (255, 255, 255)

# Enemy types and their base stats (HP, speed, view radius, color)
ENEMY_TYPES: dict[str, dict[str, Any]] = {
    "rookie": {
        "hp": 60,
        "armor": 0,           # No armor
        "speed": 2.0,
        "view_radius": 200,
        "view_angle": 70,
        "color": (0, 200, 0),
        "weapon": "pistol_silenced"  # Weaker, less frequent shots
    },
    "veteran": {
        "hp": 100,
        "armor": 50,          # Medium armor
        "speed": 2.5,
        "view_radius": 250,
        "view_angle": 80,
        "color": (200, 120, 0),
        "weapon": "rifle"            # Armed with a rifle
    },
    "commander": {
        "hp": 150,
        "armor": 100,         # Heavy armor
        "speed": 3.0,
        "view_radius": 300,
        "view_angle": 90,
        "color": (200, 0, 0),
        "weapon": "rifle"            # Dangerous assault unit
    }
}

# Weapon stats (noise radius in pixels, damage, cooldown, ammo, spread)
WEAPONS: dict[str, dict[str, Any]] = {
    "knife": {
        "damage": 50,
        "noise_radius": 0,
        "ammo_capacity": 0,
        "spread": 0,
        "bullet_speed": 0,
        "shoot_cooldown": 500
    },
    "pistol_silenced": {
        "damage": 60,
        "noise_radius": 60,
        "ammo_capacity": 12,
        "spread": 3,
        "bullet_speed": 12,
        "shoot_cooldown": 400
    },
    "rifle": {
        "damage": 40,
        "falloff": 0.998,
        "noise_radius": 350,     # Very loud (attracts half the map's attention)
        "ammo_capacity": 30,     # Large magazine
        "spread": 6,             # Medium accuracy at range
        "bullet_speed": 18,      # Fast bullet
        "shoot_cooldown": 150
    },
    "shotgun": {
        "damage": 20,
        "falloff": 0.982,  # Damage per SINGLE pellet. If all 8 hit -> 160 damage!
        "noise_radius": 400,
        "ammo_capacity": 6,
        "spread": 16,             # Pellet spread angle (fan pattern)
        "bullet_speed": 14,
        "shoot_cooldown": 600,
        "pellets_count": 8        # Number of pellets fired per shot
    }
}

# Player movement settings
PLAYER_SPEED_NORMAL: int = 5
PLAYER_SPEED_STEALTH: int = 2
PLAYER_NOISE_NORMAL: int = 100
PLAYER_NOISE_STEALTH: int = 0

# Time in frames (FPS * seconds) before an enemy loses interest
ENEMY_LOSE_INTEREST_TIME: int = 60 * 5  # 5 seconds at 60 FPS

# Mission types and completion conditions
MISSION_CONFIGS: dict[int, dict[str, Any]] = {
    1: {
        "title": "Місія 1: Тихі кроки",
        "type": "STEALTH_ESCAPE",
        "description": "Дійди до точки евакуації. Якщо ворог тебе виявить — місію провалено!",
        "fail_on_alert": True,
        "objectives": ["escape"],
        "enemies_count": 3
    },
    2: {
        "title": "Місія 2: Зачистка сектора",
        "type": "ELIMINATION",
        "description": "Знайди та ліквідуй усіх ворогів на локації.",
        "fail_on_alert": False,
        "objectives": ["kill_all"],
        "enemies_count": 5
    },
    3: {
        "title": "Місія 3: Викрадення даних",
        "type": "DATA_HEIST",
        "description": "Знайди секретні документи та дістанься виходу. Шпигуй або проривайся з боєм!",
        "fail_on_alert": False,
        "objectives": ["collect_data", "escape"],
        "enemies_count": 4
    }
}
