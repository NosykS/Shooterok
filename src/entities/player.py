# src/entities/player.py
import logging
import random

import pygame

from src.settings import (
    WEAPONS, CLASS_DEFINITIONS, PLAYER_SPEED_NORMAL,
    PLAYER_SPEED_STEALTH, PLAYER_NOISE_NORMAL, PLAYER_NOISE_STEALTH
)
from src.objects.bullet import Bullet
from src.core.physics import get_nearby_obstacles, resolve_axis_collision
from src.core.sprite_loader import load_character_sprite
from src.core.ui import draw_gear_icons

logger = logging.getLogger(__name__)


class Player(pygame.sprite.Sprite):
    def __init__(self, game, x: float, y: float) -> None:
        super().__init__()
        self.game = game

        # RPG subclass (e.g. "dd_melee"); None until a class-selection UI exists.
        # hp_mult/armor_mult are applied separately in Game.apply_player_upgrades(),
        # which is the single place max_hp/max_armor get computed.
        self.player_class: str | None = self.game.profile_data.get("player_class")
        class_def = CLASS_DEFINITIONS.get(self.player_class, {})
        self.damage_mult: float = class_def.get("damage_mult", 1.0)
        self.evasion: float = class_def.get("evasion", 0.0)

        # Load the weapon first so we know which sprite variant to load
        self._current_weapon: str = self.game.profile_data.get("equipped_weapon", "pistol_silenced")
        self.is_reloading = False
        self.reload_start_time = 0

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

        # STEALTH AND SPEED
        self.base_speed = PLAYER_SPEED_NORMAL
        self.speed = self.base_speed

        self.current_noise_radius = 0
        self.is_hidden = False
        self.footstep_timer = 0

        # Ammo
        self.weapons_ammo: dict[str, int] = {}
        for w_name, w_data in WEAPONS.items():
            self.weapons_ammo[w_name] = w_data.get("ammo_capacity", 0)

        self.last_shot_time = pygame.time.get_ticks()
        self.refill_all_ammo()

    def _load_player_image(self) -> pygame.Surface:
        """Loads the player sprite from the 'Hitman 1' folder for the current weapon/state."""
        folder_name = "Hitman 1"
        character_prefix = "hitman1"

        # "sprite_suffix" in WEAPONS picks the closest existing pose; several
        # newer weapons (hammer, dual_swords, sniper_rifle, ...) don't have
        # dedicated art yet and reuse an existing one on purpose.
        suffix = "reload" if self.is_reloading else self.weapon_stats.get("sprite_suffix", "gun")

        image_path = f"assets/images/{folder_name}/{character_prefix}_{suffix}.png"

        surface = load_character_sprite(image_path)
        if surface is None:
            # Fallback placeholder in case the sprite file is missing
            surface = pygame.Surface((50, 50), pygame.SRCALPHA).convert_alpha()
            pygame.draw.circle(surface, (0, 128, 255), (25, 25), 20)
            pygame.draw.line(surface, (255, 0, 0), (25, 25), (50, 25), 4)

        # Cheap visual cue for gear with no dedicated sprite art (hammer/dual_swords
        # share the generic "hold" pose; off-hand items aren't drawn at all otherwise)
        class_def = CLASS_DEFINITIONS.get(self.player_class, {})
        draw_gear_icons(surface, self._current_weapon, class_def.get("off_hand"))
        return surface

    @property
    def current_weapon(self) -> str:
        return self._current_weapon

    @property
    def weapon_stats(self) -> dict:
        return WEAPONS.get(self._current_weapon, WEAPONS["knife"])

    @property
    def ammo(self) -> int:
        return self.weapons_ammo.get(self.current_weapon, 0)

    @ammo.setter
    def ammo(self, value: int) -> None:
        if self.current_weapon in self.weapons_ammo:
            self.weapons_ammo[self.current_weapon] = value

    def handle_movement(self, keys, obstacles) -> None:
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

        # Footsteps only play during normal walking; stealth (LSHIFT) is silent.
        if is_moving and not is_stealth:
            self.footstep_timer -= 1
            if self.footstep_timer <= 0:
                self.footstep_timer = 18  # ~0.3s between steps at 60 FPS
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

    def angle_to_mouse(self, camera) -> float:
        """Angle (in degrees) from the player to the current mouse position in world space."""
        world_mouse = camera.screen_to_world(pygame.mouse.get_pos())
        to_mouse = world_mouse - self.pos
        return to_mouse.as_polar()[1] if to_mouse.length() > 0 else 0

    def rotate_to_mouse(self, camera) -> None:
        if self.is_hidden:
            return

        mouse_x, mouse_y = pygame.mouse.get_pos()
        world_mouse_x = mouse_x - camera.camera_rect.x
        world_mouse_y = mouse_y - camera.camera_rect.y

        direction = pygame.math.Vector2(world_mouse_x - self.pos.x, world_mouse_y - self.pos.y)
        if direction.length() > 0:
            _, angle = direction.as_polar()
            angle = -angle
            self.image = pygame.transform.rotate(self.base_image, angle)
            self.rect = self.image.get_rect(center=self.pos)

    def _is_weapon_allowed(self, weapon_name: str) -> bool:
        """Gear restriction: a class with allowed_weapons in CLASS_DEFINITIONS can
        only equip those. No class assigned yet (player_class is None) -> unrestricted,
        matching current behavior since there's no class-selection UI."""
        class_def = CLASS_DEFINITIONS.get(self.player_class)
        if class_def is None:
            return True
        return weapon_name in class_def.get("allowed_weapons", [])

    def change_weapon(self, index: int) -> None:
        unlocked = self.game.profile_data["unlocked_weapons"]

        if 0 <= index < len(unlocked):
            weapon_name = unlocked[index]

            if not self._is_weapon_allowed(weapon_name):
                logger.info(
                    "Cannot equip %s: not in allowed_weapons for class %s",
                    weapon_name, self.player_class
                )
                return

            self._current_weapon = weapon_name
            self.game.profile_data["equipped_weapon"] = weapon_name
            self.shoot_cooldown_timer = 0
            self.is_reloading = False  # Switching weapons cancels an in-progress reload

            # Update the sprite to match the new weapon
            self.base_image = self._load_player_image()
            self.image = self.base_image.copy()

            stats = self.weapon_stats
            logger.info(
                "Weapon equipped: %s | Damage: %s | Cooldown: %s",
                weapon_name, stats["damage"], stats["shoot_cooldown"]
            )

    def attack(self, camera) -> str | list[Bullet] | None:
        if self.is_hidden:
            return None

        current_time = pygame.time.get_ticks()
        stats = self.weapon_stats

        if self.is_reloading:
            self._update_reload(current_time)
            return None

        if current_time - self.last_shot_time < stats["shoot_cooldown"]:
            return None

        if stats.get("is_melee", False):
            self.last_shot_time = current_time
            self.current_noise_radius = stats.get("noise_radius", 0)
            return "melee"

        if self.weapons_ammo.get(self.current_weapon, 0) <= 0:
            self._start_reload(current_time, stats)
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
            bullet_damage = stats["damage"] * self.damage_mult

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
                        damage=bullet_damage,
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
                    damage=bullet_damage,
                    speed=stats["bullet_speed"],
                    is_enemy_bullet=False,
                    falloff=weapon_falloff
                )
                return [single_bullet]

        return None

    def _start_reload(self, current_time: int, stats: dict) -> None:
        """Begins a reload on empty ammo, or refills instantly if the weapon has no reload_time set."""
        reload_time = stats.get("reload_time", 0)
        if reload_time <= 0:
            self.weapons_ammo[self.current_weapon] = stats.get("ammo_capacity", 0)
            return

        self.is_reloading = True
        self.reload_start_time = current_time
        self.base_image = self._load_player_image()
        self.image = self.base_image.copy()
        logger.info("Reloading %s (%d ms)...", self.current_weapon, reload_time)

    def _update_reload(self, current_time: int) -> None:
        """Finishes the in-progress reload once its reload_time has elapsed."""
        reload_time = self.weapon_stats.get("reload_time", 0)
        if current_time - self.reload_start_time < reload_time:
            return

        self.weapons_ammo[self.current_weapon] = self.weapon_stats.get("ammo_capacity", 0)
        self.is_reloading = False
        self.base_image = self._load_player_image()
        self.image = self.base_image.copy()
        logger.info("Reload complete: %s", self.current_weapon)

    def update(self, keys, obstacles, camera) -> None:
        self.handle_movement(keys, obstacles)
        self.rotate_to_mouse(camera)
        self.rect.center = self.pos

    def refill_all_ammo(self) -> None:
        for w_name, w_data in WEAPONS.items():
            self.weapons_ammo[w_name] = w_data.get("ammo_capacity", 0)
        logger.info("Ammo replenished for all weapons.")

    def toggle_hiding_spot(self, hiding_spots_group: pygame.sprite.Group) -> None:
        if self.is_hidden:
            if hasattr(self, "current_hideout") and self.current_hideout:
                if hasattr(self.current_hideout, "exit_pos"):
                    self.pos = pygame.math.Vector2(self.current_hideout.exit_pos)
                self.current_hideout = None

            self.is_hidden = False
            self.hitbox.center = self.pos
            self.rect.center = self.pos
            logger.info("Player left cover at a safe point.")
        else:
            hit_spot = pygame.sprite.spritecollideany(self, hiding_spots_group)
            if hit_spot:
                self.is_hidden = True
                self.current_hideout = hit_spot
                self.pos = pygame.math.Vector2(hit_spot.rect.center)
                self.hitbox.center = self.pos
                self.rect.center = self.pos
                logger.info("Player hid in a bush.")
