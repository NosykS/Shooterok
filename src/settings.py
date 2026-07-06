# src/settings.py
FPS = 60

# Розмір одного тайла (клітинки мапи)
TILE_SIZE = 32
GRID_WIDTH = 40
GRID_HEIGHT = 24

SCREEN_WIDTH = GRID_WIDTH * TILE_SIZE   # 40 * 32 = 1280
SCREEN_HEIGHT = GRID_HEIGHT * TILE_SIZE # 24 * 32 = 768

# РОЗМІР ВЕЛИКОГО ІГРОВОГО СВІТУ (Світ, по якому рухається камера)
# Зробимо карту, наприклад, 100х100 або 80х60 клітинок
WORLD_GRID_WIDTH = 90  # Клітинок в ширину (90 * 32 = 2880 пікселів)
WORLD_GRID_HEIGHT = 60 # Клітинок в висоту (60 * 32 = 1920 пікселів)

WORLD_WIDTH = WORLD_GRID_WIDTH * TILE_SIZE
WORLD_HEIGHT = WORLD_GRID_HEIGHT * TILE_SIZE

# Кольори
BG_COLOR = (30, 30, 40)
WHITE = (255, 255, 255)

# Типи ворогів та їхні базові характеристики (Життя, Швидкість, Радіус огляду, Колір)
ENEMY_TYPES = {
    "rookie": {
        "hp": 60,
        "armor": 0,          # Без броні
        "speed": 2.0,
        "view_radius": 200,
        "view_angle": 70,
        "color": (0, 200, 0),
        "weapon": "pistol_silenced" # Стріляє слабше і рідше
    },
    "veteran": {
        "hp": 100,
        "armor": 50,         # Середня броня
        "speed": 2.5,
        "view_radius": 250,
        "view_angle": 80,
        "color": (200, 120, 0),
        "weapon": "rifle"           # Озброєний гвинтівкою
    },
    "commander": {
        "hp": 150,
        "armor": 100,        # Важка броня
        "speed": 3.0,
        "view_radius": 300,
        "view_angle": 90,
        "color": (200, 0, 0),
        "weapon": "rifle"           # Небезпечний штурмовик
    }
}

# Характеристики зброї (Шум в пікселях, Шкода)

WEAPONS = {
    "knife": {
        "damage": 50,
        "fire_rate": 250,
        "noise_radius": 0,
        "ammo_capacity": 0,
        "spread": 0,
        "bullet_speed": 0,
        "shoot_cooldown": 500
    },
    "pistol_silenced": {
        "damage": 60,
        "fire_rate": 400,
        "noise_radius": 60,
        "ammo_capacity": 12,
        "spread": 3,
        "bullet_speed": 12,
        "shoot_cooldown": 400
    },
    "rifle": {  # <--- НАША НОВА ШТУРМОВА ГВИНТІВКА
        "damage": 40,
        "fire_rate": 150,  # Стріляє швидко (мілісекунди між пострілами)
        "noise_radius": 300,  # Дуже гучна
        "ammo_capacity": 30,
        "spread": 7,  # Має базовий розліт куль
        "bullet_speed": 16,
        "shoot_cooldown": 150
    }
}

# Налаштування ходьби гравця
PLAYER_SPEED_NORMAL = 5
PLAYER_SPEED_STEALTH = 2
PLAYER_NOISE_NORMAL = 100
PLAYER_NOISE_STEALTH = 0

# Час у кадрах (FPS * секунди), через який ворог заспокоюється
ENEMY_LOSE_INTEREST_TIME = 60 * 5 # 5 секунд при 60 FPS

# Затримка реакції ворога (в кадрах). Поки що просто константа на майбутнє
ENEMY_REACTION_TIME = 30

# Місії типи та умови виконання
MISSION_CONFIGS = {
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