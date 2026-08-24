# src/core/game.py
import logging
import random

import pygame

from src.settings import (
    SCREEN_WIDTH, SCREEN_HEIGHT, FPS, BG_COLOR,
    WEAPONS, CLASS_DEFINITIONS, WORLD_WIDTH, WORLD_HEIGHT, ENEMY_LOSE_INTEREST_TIME
)
from src.core.ui import (
    draw_controls_help, draw_player_bars, draw_game_ui,
    draw_gunshot_flash, draw_knife_swing, UIButton, UISlider
)
from src.core.crosshair import CrosshairController
from src.core.camera import Camera
from src.core.mission_manager import MissionManager
from src.core.collision_manager import CollisionManager
from src.core.level_manager import LevelManager
from src.core.input_handler import InputHandler
from src.core.save_manager import SaveManager, MAX_CHARACTER_SLOTS
from src.core.progression_manager import ProgressionManager
from src.core.shop_manager import ShopManager
from src.core.sound_manager import SoundManager

logger = logging.getLogger(__name__)

# Short display label per RPG subtype (CLASS_DEFINITIONS key), used on the
# class-select grid and to label characters on the character-select screen.
# Order matches CLASS_DEFINITIONS, grouped 3 per row for the select-screen grid.
CLASS_SUBTYPE_LABELS: list[tuple[str, str]] = [
    ("tank_melee", "Танк: Ближній (Молот)"),
    ("tank_ranged", "Танк: Дальній (Дробовик)"),
    ("dd_melee", "DD: Ближній (Мечі)"),
    ("dd_ranged_glass", "DD: Снайпер (Glass Cannon)"),
    ("dd_ranged_mid", "DD: Штурмовик (АГ)"),
    ("heal_hot", "Лікар: HoT (Пістолет)"),
    ("heal_direct", "Лікар: Директ (Пістолет)"),
    ("support_buff", "Підтримка: Баф (Пістолет)"),
    ("support_control", "Підтримка: Контроль (Пістолет)"),
]
CLASS_SUBTYPE_LABEL_MAP: dict[str, str] = dict(CLASS_SUBTYPE_LABELS)


class Game:
    def __init__(self, screen: pygame.Surface) -> None:
        """Initializes the game core, state managers, and subsystems."""
        self.screen = screen
        self.clock = pygame.time.Clock()
        self.game_state = "CHARACTER_SELECT"
        self.running = True

        # Top-level save: settings are shared across characters, progress isn't
        # (see save_manager.DEFAULT_SAVE). self.profile_data below is a *reference*
        # into save_data["characters"] once a character is picked/created, so
        # mutating it (as most of the codebase already does) mutates save_data too.
        self.save_data = SaveManager.load_game()

        # No character selected yet — set once CHARACTER_SELECT/CLASS_SELECT finish.
        self.profile_data: dict | None = None
        self.progression: ProgressionManager | None = None
        self.shop: ShopManager | None = None

        # Sprite groups (managed via LevelManager)
        self.player = None
        self.all_sprites = pygame.sprite.Group()
        self.bullets = pygame.sprite.Group()
        self.enemies = pygame.sprite.Group()
        self.obstacles = pygame.sprite.Group()
        self.hiding_spots = pygame.sprite.Group()
        self.game_matrix = None
        # Shared A* walkability grid, built once per level load (LevelManager);
        # every enemy reuses it instead of rebuilding it from scratch per re-path
        self.pathfinding_grid = None

        self.camera = Camera(WORLD_WIDTH, WORLD_HEIGHT)

        saved_settings = self.save_data["settings"]
        self.sound = SoundManager(
            sfx_volume=saved_settings.get("sfx_volume", 1.0),
            music_volume=saved_settings.get("music_volume", 1.0)
        )

        # State to return to from the settings screen (MENU or PAUSE)
        self.settings_return_state = "MENU"
        # Frame counter for the brief "game saved" visual confirmation
        self.save_feedback_timer = 0
        # Character index armed for deletion (needs a second confirming click); None = no pending delete
        self.pending_delete_index: int | None = None

        # Map memory
        self.saved_game_matrix = None
        self.saved_hiding_spots_data = []

        # Visual effects
        self.gunshot_visual_timer = 0
        self.gunshot_visual_pos = (0, 0)
        self.gunshot_visual_radius = 0

        self.knife_visual_timer = 0
        self.knife_visual_pos = (0, 0)
        # Radius the swing visual/hit-check used at the moment of the last melee
        # attack — captured then (not read live) so switching weapons mid-swing
        # doesn't retroactively change an already-triggered attack's reach.
        self.knife_visual_radius = WEAPONS["knife"].get("damage_radius", 60)

        pygame.font.init()
        self.pause_font_title = pygame.font.SysFont("Arial", 48, bold=True)
        self.pause_font_btn = pygame.font.SysFont("Arial", 22, bold=True)
        # Compact font for text inside the HP/Armor bars
        self.hud_small_font = pygame.font.SysFont("Arial", 14, bold=True)

        # Manager initialization (the mission number is picked up when the game starts)
        self.levels = LevelManager(self)
        self.missions = MissionManager(self)
        self.collision_ctrl = CollisionManager(self)
        self.crosshair_ctrl = CrosshairController()
        self.inputs = InputHandler(self)

        self._init_ui_buttons()
        self.frame_counter = 0

    def apply_player_upgrades(self) -> None:
        """Applies the profile's upgrade tiers to the current player object."""
        if not self.player:
            return

        class_def = CLASS_DEFINITIONS.get(self.player.player_class, {})
        hp_mult = class_def.get("hp_mult", 1.0)
        armor_mult = class_def.get("armor_mult", 1.0)

        # 1. Health bonus: +20 HP per upgrade tier, scaled by the player's class
        hp_level = self.profile_data["upgrades"].get("max_hp", 0)
        self.player.max_hp = round((100 + hp_level * 20) * hp_mult)
        self.player.hp = self.player.max_hp

        # 2. Armor bonus: +20 Armor per upgrade tier, scaled by the player's class
        armor_level = self.profile_data["upgrades"].get("max_armor", 0)
        self.player.max_armor = round((50 + armor_level * 20) * armor_mult)
        self.player.armor = self.player.max_armor

        # 3. Speed bonus: +10% speed per upgrade tier
        speed_level = self.profile_data["upgrades"].get("speed", 0)
        # Update base_speed specifically to avoid conflicts during sprint/stealth
        self.player.base_speed = 4 * (1.0 + (speed_level * 0.1))

    def create_character(self, subtype: str) -> None:
        """Creates a new character with the chosen RPG subtype, auto-grants its
        main_hand weapon, adds it to the save, and makes it the active character."""
        class_def = CLASS_DEFINITIONS.get(subtype)
        if class_def is None:
            logger.warning("Unknown class subtype selected: %s", subtype)
            return

        if len(self.save_data["characters"]) >= MAX_CHARACTER_SLOTS:
            logger.warning("Character slots full (%d) — cannot create another.", MAX_CHARACTER_SLOTS)
            return

        character = SaveManager.create_character()
        character["player_class"] = subtype

        main_hand = class_def.get("main_hand")
        if main_hand:
            character["unlocked_weapons"].append(main_hand)
            character["equipped_weapon"] = main_hand

        self.save_data["characters"].append(character)
        self._activate_character(len(self.save_data["characters"]) - 1)
        SaveManager.save_game(self.save_data)
        logger.info("Character created: %s (main hand: %s)", subtype, main_hand)

    def select_character(self, index: int) -> None:
        """Makes an existing character (by index in save_data['characters']) the active one."""
        if not (0 <= index < len(self.save_data["characters"])):
            logger.warning("Invalid character index selected: %s", index)
            return
        self._activate_character(index)

    def _activate_character(self, index: int) -> None:
        """Points profile_data/progression/shop at the given character slot."""
        self.profile_data = self.save_data["characters"][index]
        self.progression = ProgressionManager(self.profile_data)
        self.shop = ShopManager(self.profile_data)

    def delete_character(self, index: int) -> None:
        """Permanently removes a character's progress from the save."""
        characters = self.save_data["characters"]
        if not (0 <= index < len(characters)):
            logger.warning("Invalid character index to delete: %s", index)
            return

        removed = characters.pop(index)

        # If the deleted character was the active one, drop the now-dangling reference
        if self.profile_data is removed:
            self.profile_data = None
            self.progression = None
            self.shop = None

        SaveManager.save_game(self.save_data)
        logger.info("Character deleted (slot %s, class %s)", index, removed.get("player_class"))

    def _init_ui_buttons(self) -> None:
        """Initializes interactive UI buttons for every menu screen."""
        cx, cy = SCREEN_WIDTH // 2, SCREEN_HEIGHT // 2
        b_color, h_color = (40, 45, 55), (60, 80, 110)
        red_b, red_h = (120, 35, 35), (160, 45, 45)
        green_b, green_h = (35, 120, 65), (45, 160, 85)

        self.pause_buttons = [
            UIButton(cx, cy - 137, 260, 45, "Продовжити", self.pause_font_btn, b_color, h_color, "CONTINUE"),
            UIButton(cx, cy - 82, 260, 45, "Перезапустити рівень", self.pause_font_btn, b_color, h_color, "RESTART"),
            UIButton(cx, cy - 27, 260, 45, "Налаштування", self.pause_font_btn, b_color, h_color, "OPEN_SETTINGS"),
            UIButton(cx, cy + 28, 260, 45, "Зберегти гру", self.pause_font_btn, green_b, green_h, "SAVE_GAME"),
            UIButton(cx, cy + 83, 260, 45, "Головне меню", self.pause_font_btn, b_color, h_color, "MAIN_MENU"),
            UIButton(cx, cy + 138, 260, 45, "Вийти з гри", self.pause_font_btn, red_b, red_h, "QUIT")
        ]
        self.main_menu_buttons = [
            UIButton(cx, cy - 130, 260, 45, "ПРОДОВЖИТИ", self.pause_font_btn, b_color, h_color, "CONTINUE_GAME"),
            UIButton(cx, cy - 75, 260, 45, "НОВА ГРА", self.pause_font_btn, b_color, h_color, "NEW_GAME"),
            UIButton(cx, cy - 20, 260, 45, "ЗМІНИТИ ПЕРСОНАЖА", self.pause_font_btn, b_color, h_color, "CHANGE_CHARACTER"),
            UIButton(cx, cy + 35, 260, 45, "НАЛАШТУВАННЯ", self.pause_font_btn, b_color, h_color, "OPEN_SETTINGS"),
            UIButton(cx, cy + 90, 260, 45, "ВИХІД", self.pause_font_btn, red_b, red_h, "QUIT")
        ]
        self.settings_buttons = [
            UIButton(cx, cy + 150, 260, 45, "Назад", self.pause_font_btn, b_color, h_color, "SETTINGS_BACK"),
        ]
        self.class_select_buttons = self._build_class_select_buttons(cx, cy, b_color, h_color)
        self.character_select_buttons: list[UIButton] = []
        self.refresh_character_select_buttons()
        self.settings_sliders = [
            UISlider(cx, cy - 40, 320, 20, "Гучність музики", self.hud_small_font, self.save_data["settings"]["music_volume"]),
            UISlider(cx, cy + 40, 320, 20, "Гучність ефектів", self.hud_small_font, self.save_data["settings"]["sfx_volume"]),
        ]
        self.game_over_buttons = [
            UIButton(cx, cy + 20, 260, 45, "СПРОБУВАТИ ЗНОВУ", self.pause_font_btn, b_color, h_color, "RESTART"),
            UIButton(cx, cy + 80, 260, 45, "ГОЛОВНЕ МЕНЮ", self.pause_font_btn, b_color, h_color, "MAIN_MENU")
        ]
        # After victory we go to the shop/upgrades screen first
        self.victory_buttons = [
            UIButton(cx, cy + 20, 260, 45, "В МАГАЗИН / ПРОКАЧКУ", self.pause_font_btn, green_b, green_h, "OPEN_SHOP"),
            UIButton(cx, cy + 80, 260, 45, "ГОЛОВНЕ МЕНЮ", self.pause_font_btn, b_color, h_color, "MAIN_MENU")
        ]

        self.victory_all_buttons = [
            UIButton(cx, cy - 30, 260, 45, "ПОЧАТИ ЗНОВУ", self.pause_font_btn, green_b, green_h, "RESTART_FIRST"),
            UIButton(cx, cy + 30, 260, 45, "ГОЛОВНЕ МЕНЮ", self.pause_font_btn, b_color, h_color, "MAIN_MENU"),
            UIButton(cx, cy + 90, 260, 45, "ВИЙТИ З ГРИ", self.pause_font_btn, red_b, red_h, "QUIT")
        ]

        # Buttons inside the Shop / Upgrades screen itself (precisely aligned grid)
        self.shop_buttons = [
            UIButton(cx - 140, cy + 160, 240, 45, "НАСТУПНА МІСІЯ", self.pause_font_btn, green_b, green_h, "NEXT_MISSION"),
            UIButton(cx + 140, cy + 160, 240, 45, "ГОЛОВНЕ МЕНЮ", self.pause_font_btn, b_color, h_color, "MAIN_MENU"),

            # Quick stat upgrade buttons (centered against the text rows)
            UIButton(cx - 60, cy - 15, 35, 25, "+", self.hud_small_font, b_color, h_color, "BUY_UPGRADE_HP"),
            UIButton(cx - 60, cy + 25, 35, 25, "+", self.hud_small_font, b_color, h_color, "BUY_UPGRADE_ARMOR"),
            UIButton(cx - 60, cy + 65, 35, 25, "+", self.hud_small_font, b_color, h_color, "BUY_UPGRADE_SPEED"),

            # Weapon purchase buttons
            UIButton(cx + 210, cy - 15, 75, 25, "1200$", self.hud_small_font, b_color, h_color, "BUY_WEAPON_RIFLE"),
            UIButton(cx + 210, cy + 25, 75, 25, "1000$", self.hud_small_font, b_color, h_color, "BUY_WEAPON_SHOTGUN")
        ]

    def _build_class_select_buttons(self, cx: int, cy: int, b_color, h_color) -> list[UIButton]:
        """Builds one button per RPG subtype (CLASS_DEFINITIONS key), laid out in a 3x3 grid."""
        labels = CLASS_SUBTYPE_LABELS
        col_offsets = [-260, 0, 260]
        row_offsets = [-140, -70, 0]

        buttons = []
        for idx, (subtype, label) in enumerate(labels):
            col, row = idx % 3, idx // 3
            btn_x = cx + col_offsets[col]
            btn_y = cy + row_offsets[row]
            buttons.append(UIButton(
                btn_x, btn_y, 230, 55, label, self.hud_small_font,
                b_color, h_color, f"SELECT_CLASS:{subtype}"
            ))

        buttons.append(UIButton(cx, cy + 90, 230, 45, "Назад", self.pause_font_btn, b_color, h_color, "CLASS_SELECT_BACK"))
        return buttons

    def refresh_character_select_buttons(self) -> None:
        """Rebuilds the character-select button list from save_data["characters"].

        Called at init and whenever the list changes (a character was just
        created/deleted) or the screen is entered, since the character count
        and pending-delete confirmation state both vary.
        """
        cx, cy = SCREEN_WIDTH // 2, SCREEN_HEIGHT // 2
        b_color, h_color = (40, 45, 55), (60, 80, 110)
        green_b, green_h = (35, 120, 65), (45, 160, 85)
        red_b, red_h = (120, 35, 35), (160, 45, 45)
        confirm_b, confirm_h = (170, 90, 20), (210, 115, 30)
        characters = self.save_data["characters"]

        buttons = []
        for idx, character in enumerate(characters):
            class_label = CLASS_SUBTYPE_LABEL_MAP.get(character.get("player_class"), "?")
            label = f"Персонаж {idx + 1}: {class_label} (Рівень {character.get('player_level', 1)})"
            btn_y = cy - 190 + idx * 65
            buttons.append(UIButton(cx - 30, btn_y, 380, 50, label, self.hud_small_font, b_color, h_color, f"PICK_CHARACTER:{idx}"))

            if self.pending_delete_index == idx:
                buttons.append(UIButton(cx + 230, btn_y, 90, 50, "Точно?", self.hud_small_font,
                                         confirm_b, confirm_h, f"DELETE_CHARACTER:{idx}"))
            else:
                buttons.append(UIButton(cx + 230, btn_y, 60, 50, "✕", self.pause_font_btn,
                                         red_b, red_h, f"DELETE_CHARACTER:{idx}"))

        if len(characters) < MAX_CHARACTER_SLOTS:
            btn_y = cy - 190 + len(characters) * 65
            buttons.append(UIButton(cx - 30, btn_y, 380, 50, "+ Створити персонажа", self.hud_small_font,
                                     green_b, green_h, "CREATE_CHARACTER"))

        buttons.append(UIButton(cx, cy + 150, 260, 45, "ВИХІД", self.pause_font_btn, red_b, red_h, "QUIT"))
        self.character_select_buttons = buttons

    def execute_knife_attack(self) -> None:
        """Computes the melee damage arc for the player's currently equipped melee weapon."""
        self.knife_visual_timer = 6
        self.knife_visual_pos = (int(self.player.pos.x), int(self.player.pos.y))
        self.knife_visual_radius = self.player.weapon_stats.get("damage_radius", 60)

        player_angle = self.player.angle_to_mouse(self.camera)

        for enemy in list(self.enemies):
            enemy_vec = enemy.pos - self.player.pos
            distance = enemy_vec.length()

            if distance < self.knife_visual_radius and distance > 0:
                angle_to_enemy = enemy_vec.as_polar()[1]
                angle_diff = (angle_to_enemy - player_angle) % 360
                if angle_diff > 180: angle_diff = 360 - angle_diff

                if angle_diff <= 45:
                    self._apply_knife_hit(enemy)

    def _apply_knife_hit(self, enemy) -> None:
        """Applies a single melee hit to an enemy: instant kill if unaware, damage otherwise.

        Damage comes from the player's currently equipped melee weapon (not always
        the knife) and is scaled by the player's class damage_mult, same as ranged attacks.
        """
        if not enemy.is_alerted:
            # Stealth takedown: the enemy never sees it coming, so evasion doesn't apply
            enemy.hp = 0
            e_type = getattr(enemy, "enemy_type", getattr(enemy, "type", "unknown"))
            logger.info("Silent melee takedown! Enemy %s eliminated.", e_type)
        elif random.random() < getattr(enemy, "evasion", 0.0):
            logger.info("Melee attack missed — enemy dodged (evasion=%.2f)", enemy.evasion)
        else:
            raw_damage = self.player.weapon_stats["damage"] * self.player.damage_mult
            melee_damage = max(0.0, raw_damage - getattr(enemy, "damage_reduction_flat", 0.0))
            enemy.hp -= melee_damage
            logger.info("Melee hit (%s)! Enemy HP: %s", self.player.current_weapon, enemy.hp)

        enemy.is_alerted = True
        enemy.last_known_player_pos = pygame.math.Vector2(self.player.pos)
        enemy.lose_interest_timer = ENEMY_LOSE_INTEREST_TIME

        if enemy.hp <= 0:
            enemy.kill()
            self.sound.play("enemy_death")
            self.progression.add_xp(150)
            self.shop.add_money(50)

    def _handle_attacks(self) -> None:
        """Checks the player's attack trigger and spawns bullets/melee hits accordingly."""
        mouse_buttons = pygame.mouse.get_pressed()
        if mouse_buttons[0]:
            attack_result = self.player.attack(self.camera)

            if attack_result == "melee":
                self.sound.play_weapon(self.player.current_weapon)
                self.execute_knife_attack()

            elif attack_result:  # Expects a list [Bullet, Bullet, ...]
                for bullet in attack_result:
                    self.all_sprites.add(bullet)
                    self.bullets.add(bullet)

                self.sound.play_weapon(self.player.current_weapon)

                weapon_stats = WEAPONS[self.player.current_weapon]
                self.gunshot_visual_timer = 8
                self.gunshot_visual_pos = (int(self.player.pos.x), int(self.player.pos.y))
                self.gunshot_visual_radius = weapon_stats["noise_radius"]

    def _check_environmental_sounds(self) -> None:
        """Scans the world for noise radii from footsteps or gunfire."""
        if self.player.current_noise_radius <= 0 or self.player.is_hidden:
            return

        for enemy in self.enemies:
            if enemy.pos.distance_to(self.player.pos) <= self.player.current_noise_radius:
                enemy.is_alerted = True
                enemy.last_known_player_pos = pygame.math.Vector2(self.player.pos)
                enemy.lose_interest_timer = ENEMY_LOSE_INTEREST_TIME

    def update(self) -> None:
        """Per-frame update of game object state and simulation logic."""
        # self.player can be None before a character/mission is active (menus,
        # character select); guard so the crosshair's melee-range clamp doesn't
        # crash reading weapon_stats off a None player.
        melee_radius = self.player.weapon_stats.get("damage_radius", 60) if self.player else 60
        self.crosshair_ctrl.update(self.player, self.camera, melee_radius, self.game_state)
        self._sync_background_music()

        if self.save_feedback_timer > 0:
            self.save_feedback_timer -= 1

        if self.game_state != "PLAYING":
            return

        self.frame_counter += 1

        keys = pygame.key.get_pressed()
        self.player.update(keys, self.obstacles, self.camera)

        # Camera follows immediately after the player moves
        self.camera.update(self.player)

        self._handle_attacks()
        self.bullets.update()
        self._update_enemies()
        self._spawn_enemy_bullets()

        self._check_environmental_sounds()
        self.collision_ctrl.handle_all_collisions()

        self._check_mission_progress()

    def _update_enemies(self) -> None:
        """Updates enemy AI, throttled for enemies far outside the camera view."""
        update_bound = pygame.Rect(
            -self.camera.camera_rect.x - 200, -self.camera.camera_rect.y - 200,
            SCREEN_WIDTH + 400, SCREEN_HEIGHT + 400
        )

        for enemy in self.enemies:
            if update_bound.colliderect(enemy.rect) or enemy.is_alerted:
                enemy.update(self.player, self.pathfinding_grid, self.obstacles)
            elif (self.frame_counter + id(enemy)) % 6 == 0:
                enemy.update(self.player, self.pathfinding_grid, self.obstacles)

    def _spawn_enemy_bullets(self) -> None:
        """Turns any bullets fired by enemies this frame into live Bullet sprites."""
        for enemy in self.enemies:
            if enemy.fired_bullet:
                if enemy.pos.distance_to(self.player.pos) <= 35:
                    enemy.fired_bullet = None
                    continue
                self.bullets.add(enemy.fired_bullet)
                self.all_sprites.add(enemy.fired_bullet)
                self.sound.play_weapon(enemy.weapon)

    def _check_mission_progress(self) -> None:
        """Checks mission completion and grants rewards/autosaves on victory."""
        old_state = self.game_state
        self.missions.check_mission_conditions(self.frame_counter)

        if old_state == "PLAYING" and self.game_state in ["VICTORY", "VICTORY_ALL"]:
            self.sound.play("victory_jingle")
            self.sound.stop_music()

            mission_money = 300
            mission_xp = 500

            self.shop.add_money(mission_money)
            self.progression.add_xp(mission_xp)

            if self.game_state == "VICTORY":
                self.profile_data["current_level"] += 1

            SaveManager.save_game(self.save_data)
            logger.info("[SAVE] Autosave successful! Reward: +%s$ | +%s XP", mission_money, mission_xp)

    def _sync_background_music(self) -> None:
        """Background music only plays while the game is actively being played."""
        if self.game_state == "PLAYING":
            self.sound.start_music()
        elif self.sound.is_music_playing():
            self.sound.pause_music()

    def draw(self) -> None:
        """Renders the current frame's graphics layers."""
        if self.game_state == "CHARACTER_SELECT":
            self._draw_character_select_screen()
            return

        if self.game_state == "MENU":
            self._draw_menu_screen()
            return

        if self.game_state == "SHOP":
            self._draw_shop_screen()
            return

        if self.game_state == "SETTINGS":
            self._draw_settings_screen()
            return

        if self.game_state == "CLASS_SELECT":
            self._draw_class_select_screen()
            return

        self._draw_world()
        self._draw_hud_and_mission_status()

        if self.game_state == "PLAYING":
            self.crosshair_ctrl.draw(self.screen, self.player)

        self._draw_overlay_menus()

    def _draw_menu_screen(self) -> None:
        """Renders the main menu screen."""
        self.screen.fill((15, 20, 30))
        cx = SCREEN_WIDTH // 2
        title = self.pause_font_title.render("STEALTH ACTION", True, (0, 150, 255))
        self.screen.blit(title, title.get_rect(center=(cx, SCREEN_HEIGHT // 2 - 235)))

        class_label = CLASS_SUBTYPE_LABEL_MAP.get(self.profile_data.get("player_class"), "?")
        active_text = self.hud_small_font.render(
            f"Активний персонаж: {class_label} (Рівень {self.profile_data.get('player_level', 1)})",
            True, (150, 200, 255)
        )
        self.screen.blit(active_text, active_text.get_rect(center=(cx, SCREEN_HEIGHT // 2 - 185)))

        for btn in self.main_menu_buttons:
            btn.draw(self.screen)

    def _draw_world(self) -> None:
        """Renders the map, vision cones, effects, sprites, and bullets."""
        self.screen.fill(BG_COLOR)
        self.levels.draw_floor(self.screen, self.camera)

        screen_bound = pygame.Rect(-self.camera.camera_rect.x, -self.camera.camera_rect.y, SCREEN_WIDTH, SCREEN_HEIGHT)

        for enemy in self.enemies:
            if screen_bound.inflate(100, 100).colliderect(enemy.rect):
                enemy.draw_vision_cone(self.screen, self.camera)

        self._draw_visual_effects()
        self._draw_noise_radius()
        self._draw_sprites()
        self._draw_enemy_indicators()
        self._draw_bullets()

    def _draw_visual_effects(self) -> None:
        """Draws the fading gunshot flash and knife swing effects."""
        if self.gunshot_visual_timer > 0:
            draw_gunshot_flash(self.screen, self.camera, self.gunshot_visual_pos, self.gunshot_visual_radius,
                               self.gunshot_visual_timer)
            if self.game_state == "PLAYING":
                self.gunshot_visual_timer -= 1

        if self.knife_visual_timer > 0:
            draw_knife_swing(self.screen, self.camera, self.player, self.knife_visual_radius)
            if self.game_state == "PLAYING":
                self.knife_visual_timer -= 1

    def _draw_noise_radius(self) -> None:
        """Draws the player's footstep noise radius indicator."""
        if self.player.current_noise_radius > 0 and not self.player.is_hidden:
            noise_pos = (
                int(self.player.pos.x + self.camera.camera_rect.x), int(self.player.pos.y + self.camera.camera_rect.y))
            color = (255, 100, 100) if self.player.current_noise_radius > 40 else (0, 150, 255)
            pygame.draw.circle(self.screen, color, noise_pos, int(self.player.current_noise_radius), 1)

    def _draw_sprites(self) -> None:
        """Renders all sprites except hiding spots and the player while hidden."""
        for sprite in self.all_sprites:
            if sprite in self.hiding_spots:
                continue
            if sprite == self.player and self.player.is_hidden:
                continue
            self.screen.blit(sprite.image, self.camera.apply(sprite))

    def _draw_enemy_indicators(self) -> None:
        """Draws enemy health and suspicion bars."""
        for enemy in self.enemies:
            enemy.draw_health_bar(self.screen, self.camera)
            enemy.draw_suspicion_bar(self.screen, self.camera)

    def _draw_bullets(self) -> None:
        """Draws all active bullets."""
        for bullet in list(self.bullets):
            self.screen.blit(bullet.image, self.camera.apply(bullet))

    def _draw_hud_and_mission_status(self) -> None:
        """Draws the HUD panels and, while playing, the controls help and mission status text."""
        draw_player_bars(self.screen, self.player, self.hud_small_font)
        draw_game_ui(self.screen, self.player, self.enemies, pygame.key.get_pressed(), self.pause_font_btn)

        if self.game_state == "PLAYING":
            draw_controls_help(self.screen, self.pause_font_btn)
            self._draw_mission_status()

    def _draw_mission_status(self) -> None:
        """Draws the current mission's title and objective status text."""
        mission_title = self.pause_font_btn.render(self.missions.cfg["title"], True, (255, 200, 0))
        self.screen.blit(mission_title, (20, 90))

        status_text = ""
        if self.missions.cfg["type"] == "STEALTH_ESCAPE":
            status_text = "Ціль: Дістатися виходу (НЕ ПРИВЕРТАЙ УВАГУ)"
        elif self.missions.cfg["type"] == "ELIMINATION":
            status_text = f"Ціль: Знищити всіх ({len(self.enemies)} залишилось)"
        elif self.missions.cfg["type"] == "DATA_HEIST":
            data_status = "ЗІБРАНО" if self.missions.data_collected else "ШУКАЙТЕ"
            status_text = f"Документи: {data_status} | Ціль: Евакуація"

        status_surf = self.pause_font_btn.render(status_text, True, (0, 200, 255))
        self.screen.blit(status_surf, (20, 115))

    def _draw_overlay_menus(self) -> None:
        """Renders modal overlay screens for pause/game-over/victory states."""
        if self.game_state not in ["PAUSE", "GAME_OVER", "VICTORY", "VICTORY_ALL"]:
            return

        if self.game_state == "VICTORY_ALL":
            menu_w, menu_h = 420, 380
        elif self.game_state == "PAUSE":
            menu_w, menu_h = 340, 460
        else:
            menu_w, menu_h = 340, 260

        m_rect = pygame.Rect(SCREEN_WIDTH // 2 - menu_w // 2, SCREEN_HEIGHT // 2 - menu_h // 2, menu_w, menu_h)

        colors = {
            "PAUSE": ((25, 30, 40), (0, 150, 255), "ПАУЗА", self.pause_buttons),
            "GAME_OVER": ((30, 20, 20), (255, 50, 50), "ВИ ЗГИНУЛИ", self.game_over_buttons),
            "VICTORY": ((20, 35, 25), (50, 255, 100), "ПЕРЕМОГА!", self.victory_buttons),
            "VICTORY_ALL": ((20, 35, 40), (0, 255, 200), "ГРУ ПРОЙДЕНО!", self.victory_all_buttons)
        }
        bg_c, border_c, title_text, buttons = colors[self.game_state]

        pygame.draw.rect(self.screen, bg_c, m_rect, border_radius=12)
        pygame.draw.rect(self.screen, border_c, m_rect, width=2, border_radius=12)

        title_surf = self.pause_font_title.render(title_text, True, border_c)
        self.screen.blit(title_surf, title_surf.get_rect(center=(SCREEN_WIDTH // 2, m_rect.top + 40)))

        for btn in buttons:
            btn.draw(self.screen)

        # Brief visual confirmation of a manual save
        if self.game_state == "PAUSE" and self.save_feedback_timer > 0:
            toast = self.hud_small_font.render("Гру збережено!", True, (100, 255, 150))
            self.screen.blit(toast, toast.get_rect(center=(SCREEN_WIDTH // 2, m_rect.bottom - 20)))

    def _draw_character_select_screen(self) -> None:
        """Renders the character-select screen: pick an existing character or create a new one."""
        self.screen.fill((15, 20, 30))
        cx = SCREEN_WIDTH // 2

        title = self.pause_font_title.render("ПЕРСОНАЖІ", True, (0, 150, 255))
        self.screen.blit(title, title.get_rect(center=(cx, 90)))

        subtitle = self.hud_small_font.render(
            f"Оберіть персонажа або створіть нового (макс. {MAX_CHARACTER_SLOTS})", True, (180, 180, 180)
        )
        self.screen.blit(subtitle, subtitle.get_rect(center=(cx, 130)))

        for btn in self.character_select_buttons:
            btn.draw(self.screen)

    def _draw_class_select_screen(self) -> None:
        """Renders the character-creation screen: pick a new character's RPG subtype directly."""
        self.screen.fill((15, 20, 30))
        cx = SCREEN_WIDTH // 2

        title = self.pause_font_title.render("ОБЕРІТЬ КЛАС", True, (0, 150, 255))
        self.screen.blit(title, title.get_rect(center=(cx, 90)))

        subtitle = self.hud_small_font.render(
            "Клас визначає стати, дозволену зброю та стартову екіпіровку", True, (180, 180, 180)
        )
        self.screen.blit(subtitle, subtitle.get_rect(center=(cx, 130)))

        for btn in self.class_select_buttons:
            btn.draw(self.screen)

    def _draw_settings_screen(self) -> None:
        """Renders the settings screen (music/SFX volume sliders)."""
        self.screen.fill((20, 25, 35))
        cx, cy = SCREEN_WIDTH // 2, SCREEN_HEIGHT // 2

        title = self.pause_font_title.render("НАЛАШТУВАННЯ", True, (0, 200, 255))
        self.screen.blit(title, title.get_rect(center=(cx, 90)))

        for slider in self.settings_sliders:
            slider.draw(self.screen)

        for btn in self.settings_buttons:
            btn.draw(self.screen)

    def run(self) -> None:
        """The main application loop."""
        while self.running:
            self.inputs.handle_events()
            self.update()
            self.draw()
            pygame.display.flip()
            self.clock.tick(FPS)

    def _draw_shop_screen(self) -> None:
        """Renders the full-screen shop / upgrades interface."""
        self.screen.fill((20, 25, 35))
        cx, cy = SCREEN_WIDTH // 2, SCREEN_HEIGHT // 2

        title = self.pause_font_title.render("БАЗА / КРАМНИЦЯ ОНОВЛЕНЬ", True, (0, 200, 255))
        self.screen.blit(title, title.get_rect(center=(cx, 60)))

        self._draw_shop_stats_bar(cx)
        self._draw_shop_upgrade_panel(cx, cy)
        self._draw_shop_weapons_panel(cx, cy)

        for btn in self.shop_buttons:
            btn.draw(self.screen)

    def _draw_shop_stats_bar(self, cx: int) -> None:
        """Draws the money/level/skill-points summary row at the top of the shop screen."""
        stats_y = 120
        money_surf = self.pause_font_btn.render(f"Баланс: {self.profile_data['money']}$", True, (255, 215, 0))
        xp_surf = self.pause_font_btn.render(
            f"Рівень: {self.profile_data['player_level']} ({self.profile_data['xp']} XP)", True, (200, 200, 200))
        sp_surf = self.pause_font_btn.render(f"Очки навичок (SP): {self.progression.skill_points}", True,
                                             (50, 255, 150))

        self.screen.blit(money_surf, (cx - 280, stats_y))
        self.screen.blit(xp_surf, (cx - 40, stats_y))
        self.screen.blit(sp_surf, (cx + 120, stats_y))

    def _draw_shop_upgrade_panel(self, cx: int, cy: int) -> None:
        """Draws the left-hand character upgrade panel."""
        pygame.draw.rect(self.screen, (30, 35, 45), (cx - 280, cy - 70, 260, 200), border_radius=8)
        pygame.draw.rect(self.screen, (0, 255, 150), (cx - 280, cy - 70, 260, 200), width=1,
                         border_radius=8)

        left_title = self.pause_font_btn.render("Прокачка персонажа", True, (0, 255, 150))
        self.screen.blit(left_title, (cx - 260, cy - 55))

        hp_lv = self.profile_data["upgrades"].get("max_hp", 0)
        arm_lv = self.profile_data["upgrades"].get("max_armor", 0)
        sp_lv = self.profile_data["upgrades"].get("speed", 0)

        self.screen.blit(self.hud_small_font.render(f"Макс Здоров'я (Рівень {hp_lv}/5)", True, (255, 255, 255)),
                         (cx - 275, cy - 22))
        self.screen.blit(self.hud_small_font.render(f"Макс Броня (Рівень {arm_lv}/5)", True, (255, 255, 255)),
                         (cx - 275, cy + 18))
        self.screen.blit(self.hud_small_font.render(f"Швидкість бігу (Рівень {sp_lv}/5)", True, (255, 255, 255)),
                         (cx - 275, cy + 58))

    def _draw_shop_weapons_panel(self, cx: int, cy: int) -> None:
        """Draws the right-hand weapon purchase panel."""
        pygame.draw.rect(self.screen, (30, 35, 45), (cx + 20, cy - 70, 260, 200), border_radius=8)
        pygame.draw.rect(self.screen, (255, 150, 0), (cx + 20, cy - 70, 260, 200), width=1, border_radius=8)

        right_title = self.pause_font_btn.render("Купівля озброєння", True, (255, 150, 0))
        self.screen.blit(right_title, (cx + 40, cy - 55))

        rif_status = "КУПЛЕНО" if "rifle" in self.profile_data["unlocked_weapons"] else "Штурмова гвинтівка"
        sht_status = "КУПЛЕНО" if "shotgun" in self.profile_data["unlocked_weapons"] else "Дробовик"

        self.screen.blit(self.hud_small_font.render(rif_status, True, (255, 255, 255)), (cx + 40, cy - 22))
        self.screen.blit(self.hud_small_font.render(sht_status, True, (255, 255, 255)), (cx + 40, cy + 18))
