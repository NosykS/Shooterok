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

# Weapon stats (noise radius in pixels, damage, cooldown, ammo, spread).
# "is_melee" weapons skip ammo/reload entirely. "sprite_suffix" picks which
# Hitman pose variant to render (see Player._load_player_image) — several
# new weapons below reuse the closest existing pose since dedicated art
# doesn't exist yet.
WEAPONS: dict[str, dict[str, Any]] = {
    "knife": {
        "damage": 50,
        "noise_radius": 0,
        "ammo_capacity": 0,
        "spread": 0,
        "bullet_speed": 0,
        "shoot_cooldown": 500,
        "is_melee": True,
        "damage_radius": 50,     # Shortest reach — a plain knife, not a polearm
        "sprite_suffix": "hold",
    },
    "hammer": {
        "damage": 80,
        "noise_radius": 30,       # Still makes some noise on impact
        "ammo_capacity": 0,
        "spread": 0,
        "bullet_speed": 0,
        "shoot_cooldown": 900,    # Heavy, slow swings (tank_melee main hand)
        "is_melee": True,
        "damage_radius": 90,      # Longest reach — heavy two-handed weapon
        "sprite_suffix": "hold",
    },
    "dual_swords": {
        "damage": 35,
        "noise_radius": 20,
        "ammo_capacity": 0,
        "spread": 0,
        "bullet_speed": 0,
        "shoot_cooldown": 280,    # Fast paired strikes (dd_melee main hand)
        "is_melee": True,
        "damage_radius": 75,      # Longer than a knife — twin blades extend the reach
        "sprite_suffix": "hold",
    },
    "pistol": {
        "damage": 45,
        "noise_radius": 150,
        "ammo_capacity": 14,
        "spread": 4,
        "bullet_speed": 13,
        "shoot_cooldown": 350,
        "reload_time": 1200,
        "sprite_suffix": "gun",
    },
    "pistol_silenced": {
        "damage": 60,
        "noise_radius": 60,
        "ammo_capacity": 12,
        "spread": 3,
        "bullet_speed": 12,
        "shoot_cooldown": 400,
        "reload_time": 1000,
        "sprite_suffix": "silencer",
    },
    "rifle": {
        "damage": 40,
        "falloff": 0.998,
        "noise_radius": 350,     # Very loud (attracts half the map's attention)
        "ammo_capacity": 30,     # Large magazine
        "spread": 6,             # Medium accuracy at range
        "bullet_speed": 18,      # Fast bullet
        "shoot_cooldown": 150,
        "reload_time": 1800,
        "sprite_suffix": "machine",
    },
    "assault_rifle": {
        "damage": 32,
        "falloff": 0.994,        # Holds accuracy at mid-range, weaker further out
        "noise_radius": 320,
        "ammo_capacity": 25,
        "spread": 4,              # Tighter cone than "rifle" (dd_ranged_mid main hand)
        "bullet_speed": 17,
        "shoot_cooldown": 180,    # Medium fire rate (between pistol and rifle)
        "reload_time": 1600,
        "sprite_suffix": "machine",
    },
    "sniper_rifle": {
        "damage": 150,
        "falloff": 0.9995,        # Barely loses damage with distance
        "noise_radius": 450,      # Very loud
        "ammo_capacity": 4,
        "spread": 1,               # Very precise (dd_ranged_glass main hand)
        "bullet_speed": 24,
        "shoot_cooldown": 1100,   # Slow fire rate
        "reload_time": 2800,      # Long reload, per RPG_CLASS_SYSTEM.md
        "sprite_suffix": "machine",
    },
    "shotgun": {
        "damage": 20,
        "falloff": 0.982,  # Damage per SINGLE pellet. If all 8 hit -> 160 damage!
        "noise_radius": 400,
        "ammo_capacity": 6,
        "spread": 16,             # Pellet spread angle (fan pattern)
        "bullet_speed": 14,
        "shoot_cooldown": 600,
        "pellets_count": 8,       # Number of pellets fired per shot
        "reload_time": 1500,
        "sprite_suffix": "machine",
    },
    "combat_shotgun": {
        "damage": 18,
        "falloff": 0.992,         # Holds up better at medium range than "shotgun"
        "noise_radius": 380,
        "ammo_capacity": 8,
        "spread": 8,               # Tighter cone than "shotgun" (tank_ranged main hand)
        "bullet_speed": 15,
        "shoot_cooldown": 700,
        "pellets_count": 6,
        "reload_time": 1800,
        "sprite_suffix": "machine",
    },
}

# Off-hand items: purely descriptive right now, no combat stats of their
# own. Shield's defensive effect is already expressed via tank_*'s
# armor_mult/evasion in CLASS_DEFINITIONS; scepter is the flavor "channel"
# for heal/buff/control active skills, which aren't implemented yet
# (see RPG_CLASS_SYSTEM.md sections 4-5).
OFFHAND_ITEMS: dict[str, dict[str, Any]] = {
    "shield": {
        "description": "Passive defensive off-hand for tank subtypes.",
    },
    "scepter": {
        "description": "Off-hand channel for heal/buff/control active skills.",
    },
}

# RPG class definitions: base_class groups the 4 player-facing classes
# (tank / dd / heal / support); the dict key is the concrete subtype that
# gets assigned once skill picks settle it. Multipliers apply on top of
# base stats (Player's hp/armor fields, or ENEMY_TYPES for enemies) so the
# same table drives both Player and Enemy without duplicating logic.
# See RPG_CLASS_SYSTEM.md section 3 for the full design rationale.
CLASS_DEFINITIONS: dict[str, dict[str, Any]] = {
    "tank_melee": {
        "base_class": "tank",
        "hp_mult": 1.6,
        "armor_mult": 1.8,
        "evasion": 0.0,
        "damage_mult": 0.7,
        "range_type": "melee",
        "main_hand": "hammer",
        "off_hand": "shield",
        "allowed_weapons": ["knife", "hammer"],
        # Cumulative enemy passive buffs per unlocked passive slot (see ENEMY_SKILL_UNLOCK_LEVELS)
        "passive_buffs_per_tier": [
            {"damage_reduction_flat": 2, "hp_regen_per_sec": 0.2},
            {"damage_reduction_flat": 2, "hp_regen_per_sec": 0.2},
            {"damage_reduction_flat": 1, "hp_regen_per_sec": 0.1},
        ],
    },
    "tank_ranged": {
        "base_class": "tank",
        "hp_mult": 1.1,
        "armor_mult": 0.9,
        "evasion": 0.25,          # Dodge chance substitutes for armor
        "damage_mult": 0.8,
        "range_type": "ranged",
        "main_hand": "combat_shotgun",
        "off_hand": "shield",
        "allowed_weapons": ["knife", "combat_shotgun"],
        "passive_buffs_per_tier": [
            {"damage_reduction_flat": 1, "hp_regen_per_sec": 0.1},
            {"damage_reduction_flat": 1, "hp_regen_per_sec": 0.1},
            {"damage_reduction_flat": 1, "hp_regen_per_sec": 0.1},
        ],
    },
    "dd_melee": {
        "base_class": "dd",
        "hp_mult": 1.1,            # Tankier than other DD subtypes
        "armor_mult": 1.0,
        "evasion": 0.1,
        "damage_mult": 1.4,
        "range_type": "melee",
        "main_hand": "dual_swords",
        "off_hand": None,          # Both hands wielding the paired swords
        "allowed_weapons": ["knife", "dual_swords"],
        "passive_buffs_per_tier": [
            {"damage_reduction_flat": 1, "hp_regen_per_sec": 0.1},
            {"damage_reduction_flat": 0, "hp_regen_per_sec": 0.1},
            {"damage_reduction_flat": 0, "hp_regen_per_sec": 0.0},
        ],
    },
    "dd_ranged_glass": {
        "base_class": "dd",
        "hp_mult": 0.6,
        "armor_mult": 0.4,
        "evasion": 0.1,
        "damage_mult": 2.0,
        "range_type": "ranged",
        "main_hand": "sniper_rifle",
        "off_hand": None,
        "allowed_weapons": ["knife", "sniper_rifle"],
        # Glass cannon: no defensive passives at all
        "passive_buffs_per_tier": [
            {"damage_reduction_flat": 0, "hp_regen_per_sec": 0.0},
            {"damage_reduction_flat": 0, "hp_regen_per_sec": 0.0},
            {"damage_reduction_flat": 0, "hp_regen_per_sec": 0.0},
        ],
    },
    "dd_ranged_mid": {
        "base_class": "dd",
        "hp_mult": 0.85,
        "armor_mult": 0.7,
        "evasion": 0.1,
        "damage_mult": 1.3,        # Linear damage, no burst
        "range_type": "ranged",
        "main_hand": "assault_rifle",
        "off_hand": None,
        "allowed_weapons": ["knife", "assault_rifle"],
        "passive_buffs_per_tier": [
            {"damage_reduction_flat": 1, "hp_regen_per_sec": 0.05},
            {"damage_reduction_flat": 0, "hp_regen_per_sec": 0.05},
            {"damage_reduction_flat": 0, "hp_regen_per_sec": 0.05},
        ],
    },
    "heal_hot": {
        "base_class": "heal",
        "hp_mult": 0.9,
        "armor_mult": 0.7,
        "evasion": 0.1,
        "damage_mult": 0.4,
        "range_type": "mid",       # No shields; multiple stacking HoT effects
        "main_hand": "pistol",
        "off_hand": "scepter",
        "allowed_weapons": ["knife", "pistol"],
        # Highest regen — thematically matches the HoT specialization
        "passive_buffs_per_tier": [
            {"damage_reduction_flat": 0, "hp_regen_per_sec": 0.2},
            {"damage_reduction_flat": 0, "hp_regen_per_sec": 0.2},
            {"damage_reduction_flat": 0, "hp_regen_per_sec": 0.2},
        ],
    },
    "heal_direct": {
        "base_class": "heal",
        "hp_mult": 0.8,
        "armor_mult": 0.6,
        "evasion": 0.1,
        "damage_mult": 0.4,
        "range_type": "ranged",    # Instant heal on cast
        "main_hand": "pistol",
        "off_hand": "scepter",
        "allowed_weapons": ["knife", "pistol"],
        "passive_buffs_per_tier": [
            {"damage_reduction_flat": 0, "hp_regen_per_sec": 0.1},
            {"damage_reduction_flat": 1, "hp_regen_per_sec": 0.1},
            {"damage_reduction_flat": 0, "hp_regen_per_sec": 0.1},
        ],
    },
    "support_buff": {
        "base_class": "support",
        "hp_mult": 0.9,
        "armor_mult": 0.8,
        "evasion": 0.1,
        "damage_mult": 0.7,        # Deals damage, but noticeably less than DD
        "range_type": "mid",
        "main_hand": "pistol",
        "off_hand": "scepter",
        "allowed_weapons": ["knife", "pistol"],
        "passive_buffs_per_tier": [
            {"damage_reduction_flat": 1, "hp_regen_per_sec": 0.1},
            {"damage_reduction_flat": 1, "hp_regen_per_sec": 0.1},
            {"damage_reduction_flat": 0, "hp_regen_per_sec": 0.0},
        ],
    },
    "support_control": {
        "base_class": "support",
        "hp_mult": 0.85,
        "armor_mult": 0.7,
        "evasion": 0.15,
        "damage_mult": 0.5,        # Lowest damage among support subtypes
        "range_type": "mid",
        "main_hand": "pistol",
        "off_hand": "scepter",
        "allowed_weapons": ["knife", "pistol"],
        "passive_buffs_per_tier": [
            {"damage_reduction_flat": 1, "hp_regen_per_sec": 0.1},
            {"damage_reduction_flat": 1, "hp_regen_per_sec": 0.1},
            {"damage_reduction_flat": 0, "hp_regen_per_sec": 0.05},
        ],
    },
}

# RPG skill unlock cadence: a new skill slot unlocks every 2nd level, alternating
# active/passive starting with active at level 2 (RPG_CLASS_SYSTEM.md section 4) —
# 10 slots total (5 active + 5 passive) by level 20. No skill catalog exists yet
# (see section 7), so ProgressionManager only tracks *when* a slot unlocks and its
# type; slots stay pending (skill_id=None) until a catalog + selection UI exist.
SKILL_UNLOCK_LEVELS: list[int] = [2, 4, 6, 8, 10, 12, 14, 16, 18, 20]

# Enemy skill unlock cadence (RPG_CLASS_SYSTEM.md section 5): a fixed 5-slot kit per
# class (3 passive + 2 active), tied to player_level rather than the enemy's own
# leveling. Passive slots unlock first (no AI decision-making needed); active slots
# are metadata-only for now — no active-skill catalog or trigger logic exists yet.
# Passive slot count directly indexes CLASS_DEFINITIONS[...]["passive_buffs_per_tier"].
ENEMY_SKILL_UNLOCK_LEVELS: list[dict[str, Any]] = [
    {"level": 1, "type": "passive"},
    {"level": 5, "type": "passive"},
    {"level": 10, "type": "active"},
    {"level": 15, "type": "passive"},
    {"level": 20, "type": "active"},
]

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
