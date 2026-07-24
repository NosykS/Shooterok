# src/entities/player.py
import pygame
import random
from src.settings import (
    WEAPONS, PLAYER_SPEED_NORMAL,
    PLAYER_SPEED_STEALTH, PLAYER_NOISE_NORMAL, PLAYER_NOISE_STEALTH
)
from src.objects.bullet import Bullet
from src.core.physics import get_nearby_obstacles, resolve_axis_collision


class Player(pygame.sprite.Sprite):
    def __init__(self, game, x, y):
        super().__init__()
        self.game = game

        # Ініціалізація зброї першочергово, щоб знати яку картинку завантажити
        self._current_weapon = self.game.profile_data.get("equipped_weapon", "pistol_silenced")

        # Завантажуємо спрайт гравця замість геометричної заглушки
        self.base_image = self._load_player_image()
        self.image = self.base_image.copy()

        self.hp = 100
        self.max_hp = 100
        self.armor = 50
        self.max_armor = 100

        self.pos = pygame.math.Vector2(x, y)
        self.rect = self.image.get_rect(center=self.pos)

        self.hitbox = pygame.Rect(0, 0, 32, 32)
        self.hitbox.center = self.pos

        # СТЕЛС ТА ШВИДКІСТЬ
        self.base_speed = PLAYER_SPEED_NORMAL
        self.speed = self.base_speed

        self.current_noise_radius = 0
        self.is_hidden = False
        self.footstep_timer = 0

        # Боєзапас
        self.weapons_ammo = {}
        for w_name, w_data in WEAPONS.items():
            self.weapons_ammo[w_name] = w_data.get("ammo_capacity", 0)

        self.last_shot_time = pygame.time.get_ticks()
        self.refill_all_ammo()

    def _load_player_image(self):
        """Завантажує спрайт гравця з папки 'Hitman 1' залежно від обраної зброї"""
        folder_name = "Hitman 1"
        character_prefix = "hitman1"

        # Вибираємо суфікс залежно від поточної зброї
        if self._current_weapon == "knife":
            suffix = "hold"
        elif "silenced" in self._current_weapon:
            suffix = "silencer"
        elif self._current_weapon in ["rifle", "shotgun"]:
            suffix = "machine"
        else:
            suffix = "gun"

        image_path = f"assets/images/{folder_name}/{character_prefix}_{suffix}.png"

        try:
            surface = pygame.image.load(image_path).convert_alpha()
            return surface
        except Exception as e:
            print(f"[WARNING] Не вдалося завантажити спрайт гравця {image_path}: {e}. Використовуємо заглушку.")
            # Запасний варіант на випадок збою
            surface = pygame.Surface((50, 50), pygame.SRCALPHA).convert_alpha()
            pygame.draw.circle(surface, (0, 128, 255), (25, 25), 20)
            pygame.draw.line(surface, (255, 0, 0), (25, 25), (50, 25), 4)
            return surface

    @property
    def current_weapon(self):
        return self._current_weapon

    @property
    def weapon_stats(self):
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

        is_stealth = keys[pygame.K_LSHIFT]
        if is_stealth:
            self.speed = self.base_speed * (PLAYER_SPEED_STEALTH / PLAYER_SPEED_NORMAL)
            base_noise = PLAYER_NOISE_STEALTH
        else:
            self.speed = self.base_speed
            base_noise = PLAYER_NOISE_NORMAL

        dx, dy = 0, 0
        if keys[pygame.K_w] or keys[pygame.K_UP]: dy = -self.speed
        if keys[pygame.K_s] or keys[pygame.K_DOWN]: dy = self.speed
        if keys[pygame.K_a] or keys[pygame.K_LEFT]: dx = -self.speed
        if keys[pygame.K_d] or keys[pygame.K_RIGHT]: dx = self.speed

        if dx != 0 and dy != 0:
            dx *= 0.7071
            dy *= 0.7071

        is_moving = dx != 0 or dy != 0

        if not is_moving:
            self.current_noise_radius = max(0, self.current_noise_radius - 2)
        else:
            self.current_noise_radius = max(base_noise, self.current_noise_radius - 1)

        # Звук кроків лунає лише під час звичайної ходьби. Під час стелсу (LSHIFT) гравець рухається безшумно.
        if is_moving and not is_stealth:
            self.footstep_timer -= 1
            if self.footstep_timer <= 0:
                self.footstep_timer = 18  # ~0.3с між кроками при 60 FPS
                self.game.sound.play_footstep()
        else:
            self.footstep_timer = 0

        nearby_obstacles = get_nearby_obstacles(self.pos, obstacles)
        resolve_axis_collision(self.pos, self.hitbox, nearby_obstacles, "x", dx)
        resolve_axis_collision(self.pos, self.hitbox, nearby_obstacles, "y", dy)

        world_w = getattr(self.game, "WORLD_WIDTH", 2000)
        world_h = getattr(self.game, "WORLD_HEIGHT", 2000)

        if self.pos.x < 0: self.pos.x = 0
        if self.pos.x > world_w: self.pos.x = world_w
        if self.pos.y < 0: self.pos.y = 0
        if self.pos.y > world_h: self.pos.y = world_h

        self.hitbox.center = self.pos

    def angle_to_mouse(self, camera):
        """Кут (у градусах) від гравця до поточної позиції миші у світових координатах"""
        world_mouse = camera.screen_to_world(pygame.mouse.get_pos())
        to_mouse = world_mouse - self.pos
        return to_mouse.as_polar()[1] if to_mouse.length() > 0 else 0

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
        unlocked = self.game.profile_data["unlocked_weapons"]

        if 0 <= index < len(unlocked):
            weapon_name = unlocked[index]

            self._current_weapon = weapon_name
            self.game.profile_data["equipped_weapon"] = weapon_name
            self.shoot_cooldown_timer = 0

            # Оновлюємо спрайт під нову зброю
            self.base_image = self._load_player_image()
            self.image = self.base_image.copy()

            stats = self.weapon_stats
            print(f"[WEAPON] Увімкнено: {weapon_name} | Шкода: {stats['damage']} | Кулдаун: {stats['shoot_cooldown']}")

    def attack(self, camera):
        if self.is_hidden:
            return None

        current_time = pygame.time.get_ticks()
        stats = self.weapon_stats

        if current_time - self.last_shot_time < stats["shoot_cooldown"]:
            return None

        if self.current_weapon == "knife":
            self.last_shot_time = current_time
            self.current_noise_radius = stats.get("noise_radius", 0)
            return "melee"

        if self.weapons_ammo.get(self.current_weapon, 0) <= 0:
            return None

        self.weapons_ammo[self.current_weapon] -= 1
        self.last_shot_time = current_time
        self.current_noise_radius = stats["noise_radius"]

        mouse_x, mouse_y = pygame.mouse.get_pos()
        world_mouse = pygame.math.Vector2(mouse_x - camera.camera_rect.x, mouse_y - camera.camera_rect.y)
        dir_vector = world_mouse - self.pos

        if dir_vector.length() > 0:
            _, base_angle = dir_vector.as_polar()
            weapon_falloff = stats.get("falloff", 1.0)

            if self.current_weapon == "shotgun":
                bullets = []
                pellets = stats.get("pellets_count", 6)

                for _ in range(pellets):
                    random_spread = random.uniform(-stats["spread"], stats["spread"])
                    pellet_angle = base_angle + random_spread

                    bullets.append(Bullet(
                        self.pos.x,
                        self.pos.y,
                        angle=pellet_angle,
                        damage=stats["damage"],
                        speed=stats["bullet_speed"],
                        is_enemy_bullet=False,
                        falloff=weapon_falloff
                    ))
                return bullets

            else:
                angle = base_angle + random.uniform(-stats["spread"], stats["spread"])
                single_bullet = Bullet(
                    self.pos.x,
                    self.pos.y,
                    angle=angle,
                    damage=stats["damage"],
                    speed=stats["bullet_speed"],
                    is_enemy_bullet=False,
                    falloff=weapon_falloff
                )
                return [single_bullet]

        return None

    def update(self, keys, obstacles, camera):
        self.handle_movement(keys, obstacles)
        self.rotate_to_mouse(camera)
        self.rect.center = self.pos

    def refill_all_ammo(self):
        for w_name, w_data in WEAPONS.items():
            self.weapons_ammo[w_name] = w_data.get("ammo_capacity", 0)
        print("[AMMO] Боєзапас успішно відновлено для всієї зброї!")

    def toggle_hiding_spot(self, hiding_spots_group):
        if self.is_hidden:
            if hasattr(self, "current_hideout") and self.current_hideout:
                if hasattr(self.current_hideout, "exit_pos"):
                    self.pos = pygame.math.Vector2(self.current_hideout.exit_pos)
                self.current_hideout = None

            self.is_hidden = False
            self.hitbox.center = self.pos
            self.rect.center = self.pos
            print("[STEALTH] Гравець вийшов зі схованки у безпечну точку.")
        else:
            hit_spot = pygame.sprite.spritecollideany(self, hiding_spots_group)
            if hit_spot:
                self.is_hidden = True
                self.current_hideout = hit_spot
                self.pos = pygame.math.Vector2(hit_spot.rect.center)
                self.hitbox.center = self.pos
                self.rect.center = self.pos
                print("[STEALTH] Гравець сховався в кущ.")