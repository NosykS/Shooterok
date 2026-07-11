# src/entities/player.py
import pygame
import random
from src.settings import (
    WORLD_WIDTH, WORLD_HEIGHT, WEAPONS, PLAYER_SPEED_NORMAL,
    PLAYER_SPEED_STEALTH, PLAYER_NOISE_NORMAL, PLAYER_NOISE_STEALTH,
    TILE_SIZE
)
from src.objects.bullet import Bullet


class Player(pygame.sprite.Sprite):
    def __init__(self, game, x, y):
        super().__init__()
        self.game = game
        self.base_image = self._create_placeholder_image()
        self.image = self.base_image.copy()

        self.hp = 100
        self.max_hp = 100
        self.armor = 50
        self.max_armor = 100

        self.pos = pygame.math.Vector2(x, y)
        self.rect = self.image.get_rect(center=self.pos)

        self.hitbox = pygame.Rect(0, 0, 32, 32)
        self.hitbox.center = self.pos

        # Стелс характеристики
        self.speed = PLAYER_SPEED_NORMAL
        self.current_noise_radius = 0  # Шум генерується діями
        self.is_hidden = False  # Чи сховався в кущах/шафі

        # ВИПРАВЛЕНО: Ініціалізуємо поточну зброю на основі збереження або ставимо дефолтну
        self._current_weapon = self.game.profile_data.get("equipped_weapon", "pistol_silenced")

        # ВИПРАВЛЕНО: Динамічно заповнюємо боєзапас для ВСІЄЇ існуючої в грі зброї з settings.py
        self.weapons_ammo = {}
        for w_name, w_data in WEAPONS.items():
            self.weapons_ammo[w_name] = w_data.get("ammo_capacity", 0)

        # Зберігаємо точний час останнього пострілу/атаки в мілісекундах
        self.last_shot_time = pygame.time.get_ticks()

        # ВИКЛИК: гарантує наявність набоїв при першому створенні
        self.refill_all_ammo()

    def _create_placeholder_image(self):
        surface = pygame.Surface((50, 50), pygame.SRCALPHA).convert_alpha()
        pygame.draw.circle(surface, (0, 128, 255), (25, 25), 20)
        pygame.draw.line(surface, (255, 0, 0), (25, 25), (50, 25), 4)
        return surface

    @property
    def current_weapon(self):
        """Геттер: завжди повертає назву поточної екіпірованої зброї"""
        return self._current_weapon

    @property
    def weapon_stats(self):
        """Новий геттер: автоматично повертає актуальні налаштування з settings.py"""
        from src.settings import WEAPONS
        return WEAPONS.get(self._current_weapon, WEAPONS["knife"])

    @property
    def ammo(self):
        return self.weapons_ammo.get(self.current_weapon, 0)

    @ammo.setter
    def ammo(self, value):
        if self.current_weapon in self.weapons_ammo:
            self.weapons_ammo[self.current_weapon] = value

    def handle_movement(self, keys, obstacles):
        if self.is_hidden:
            self.current_noise_radius = 0
            return

        if keys[pygame.K_LSHIFT]:
            self.speed = PLAYER_SPEED_STEALTH
            base_noise = PLAYER_NOISE_STEALTH
        else:
            self.speed = PLAYER_SPEED_NORMAL
            base_noise = PLAYER_NOISE_NORMAL

        dx, dy = 0, 0
        if keys[pygame.K_w] or keys[pygame.K_UP]: dy = -self.speed
        if keys[pygame.K_s] or keys[pygame.K_DOWN]: dy = self.speed
        if keys[pygame.K_a] or keys[pygame.K_LEFT]: dx = -self.speed
        if keys[pygame.K_d] or keys[pygame.K_RIGHT]: dx = self.speed

        if dx != 0 and dy != 0:
            dx *= 0.7071
            dy *= 0.7071

        if dx == 0 and dy == 0:
            self.current_noise_radius = max(0, self.current_noise_radius - 2)
        else:
            self.current_noise_radius = max(base_noise, self.current_noise_radius - 1)

        nearby_obstacles = [
            obs for obs in obstacles
            if abs(obs.rect.centerx - self.pos.x) < TILE_SIZE * 2 and
               abs(obs.rect.centery - self.pos.y) < TILE_SIZE * 2
        ]

        if dx != 0:
            self.pos.x += dx
            self.hitbox.centerx = self.pos.x
            for obstacle in nearby_obstacles:
                if self.hitbox.colliderect(obstacle.rect):
                    if dx > 0:
                        self.hitbox.right = obstacle.rect.left
                    elif dx < 0:
                        self.hitbox.left = obstacle.rect.right
                    self.pos.x = self.hitbox.centerx

        if dy != 0:
            self.pos.y += dy
            self.hitbox.centery = self.pos.y
            for obstacle in nearby_obstacles:
                if self.hitbox.colliderect(obstacle.rect):
                    if dy > 0:
                        self.hitbox.bottom = obstacle.rect.top
                    elif dy < 0:
                        self.hitbox.top = obstacle.rect.bottom
                    self.pos.y = self.hitbox.centery

        if self.pos.x < 0: self.pos.x = 0
        if self.pos.x > WORLD_WIDTH: self.pos.x = WORLD_WIDTH
        if self.pos.y < 0: self.pos.y = 0
        if self.pos.y > WORLD_HEIGHT: self.pos.y = WORLD_HEIGHT

        self.hitbox.center = self.pos

    def rotate_to_mouse(self, camera):
        if self.is_hidden: return

        mouse_x, mouse_y = pygame.mouse.get_pos()
        world_mouse_x = mouse_x - camera.camera_rect.x
        world_mouse_y = mouse_y - camera.camera_rect.y

        direction = pygame.math.Vector2(world_mouse_x - self.pos.x, world_mouse_y - self.pos.y)
        if direction.length() > 0:
            _, angle = direction.as_polar()
            angle = -angle
            self.image = pygame.transform.rotate(self.base_image, angle)
            self.rect = self.image.get_rect(center=self.pos)

    def change_weapon(self, index):
        """Перемикання зброї на основі індексу розблокованого арсеналу"""
        unlocked = self.game.profile_data["unlocked_weapons"]

        if 0 <= index < len(unlocked):
            weapon_name = unlocked[index]

            self._current_weapon = weapon_name
            self.game.profile_data["equipped_weapon"] = weapon_name
            self.shoot_cooldown_timer = 0

            stats = self.weapon_stats
            print(f"[WEAPON] Увімкнено: {weapon_name} | Шкода: {stats['damage']} | Кулдаун: {stats['shoot_cooldown']}")

    def attack(self, camera):
        if self.is_hidden:
            return None

        current_time = pygame.time.get_ticks()
        # Беремо характеристики через наш безпечний проперті-геттер
        stats = self.weapon_stats

        # 1. Перевірка кулдауну
        if current_time - self.last_shot_time < stats["shoot_cooldown"]:
            return None

        # 2. Обробка атаки ближнього бою
        if self.current_weapon == "knife":
            self.last_shot_time = current_time
            self.current_noise_radius = stats.get("noise_radius", 0)
            return "melee"

        # 3. Перевірка наявності набоїв
        if self.weapons_ammo.get(self.current_weapon, 0) <= 0:
            return None

        # --- ВИПРАВЛЕНО ВІДСТУПИ: Цей код тепер працює, коли набої Є ---
        # Витрачаємо один набій та встановлюємо спалах шуму
        self.weapons_ammo[self.current_weapon] -= 1
        self.last_shot_time = current_time
        self.current_noise_radius = stats["noise_radius"]

        # Коригуємо мишу під координати світу
        mouse_x, mouse_y = pygame.mouse.get_pos()
        world_mouse = pygame.math.Vector2(mouse_x - camera.camera_rect.x, mouse_y - camera.camera_rect.y)
        dir_vector = world_mouse - self.pos

        if dir_vector.length() > 0:
            _, base_angle = dir_vector.as_polar()

            # Отримуємо коефіцієнт згасання з налаштувань (якщо немає — 1.0)
            weapon_falloff = stats.get("falloff", 1.0)

            # --- ЛОГІКА ДЛЯ ДРОБОВИКА (СПИСОК КУЛЬ) ---
            if self.current_weapon == "shotgun":
                bullets = []
                pellets = stats.get("pellets_count", 6)

                for _ in range(pellets):
                    # Кожна дробина отримує свій випадковий кут у межах розліту
                    random_spread = random.uniform(-stats["spread"], stats["spread"])
                    pellet_angle = base_angle + random_spread

                    bullets.append(Bullet(
                        self.pos.x,
                        self.pos.y,
                        angle=pellet_angle,
                        damage=stats["damage"],
                        speed=stats["bullet_speed"],
                        is_enemy_bullet=False,
                        falloff=weapon_falloff  # ДОДАНO: передаємо згасання урону
                    ))
                return bullets  # Повертаємо список дробин

            # --- ЛОГІКА ДЛЯ ІНШОЇ ЗБРОЇ (ОДНА КУЛЯ В СПИСКУ) ---
            else:
                angle = base_angle + random.uniform(-stats["spread"], stats["spread"])
                single_bullet = Bullet(
                    self.pos.x,
                    self.pos.y,
                    angle=angle,
                    damage=stats["damage"],
                    speed=stats["bullet_speed"],
                    is_enemy_bullet=False,
                    falloff=weapon_falloff  # ДОДАНO: передаємо згасання урону
                )
                return [single_bullet]  # Теж повертаємо як список

        return None

    def update(self, keys, obstacles, camera):
        self.handle_movement(keys, obstacles)
        self.rotate_to_mouse(camera)

    def refill_all_ammo(self):
        """Повністю відновлює набої для всієї зброї до максимального рівня з конфігу"""
        from src.settings import WEAPONS
        for w_name, w_data in WEAPONS.items():
            self.weapons_ammo[w_name] = w_data.get("ammo_capacity", 0)
        print("[AMMO] Боєзапас успішно відновлено для всієї зброї!")