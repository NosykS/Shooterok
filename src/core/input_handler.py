# src/core/input_handler.py
import logging

import pygame

from src.core.save_manager import SaveManager

logger = logging.getLogger(__name__)


class InputHandler:
    def __init__(self, game) -> None:
        self.game = game

    def handle_events(self) -> None:
        """Handles global OS/system events and user input for the current frame."""
        mouse_pos = pygame.mouse.get_pos()

        # Buttons still get updated every frame; the click itself defaults to False
        mouse_click = (False, False, False)

        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                self.game.running = False

            # Register a mouse click only on the press event itself (single-shot)
            elif event.type == pygame.MOUSEBUTTONDOWN:
                if event.button == 1:  # Left mouse button
                    mouse_click = (True, False, False)
                    # Update UI buttons immediately on the click event
                    self._update_ui_button_actions(mouse_pos, mouse_click)

            elif self.game.game_state == "PLAYING":
                self._handle_playing_inputs(event)
            else:
                self._handle_menu_inputs(event)

        # Hover-state check (button hover color) runs every frame
        if not mouse_click[0]:
            self._update_ui_button_actions(mouse_pos, (False, False, False))

        # Volume sliders update every frame regardless of the event queue, for smooth dragging
        if self.game.game_state == "SETTINGS":
            self._update_settings_sliders(mouse_pos)

    def _handle_playing_inputs(self, event: pygame.event.Event) -> None:
        """Handles gameplay hotkeys while the game is actively being played."""
        if event.type != pygame.KEYDOWN:
            return

        if event.key == pygame.K_ESCAPE:
            self.game.game_state = "PAUSE"
        elif event.key in [pygame.K_1, pygame.K_2, pygame.K_3, pygame.K_4]:
            self._handle_weapon_hotkey(event.key)
        elif event.key == pygame.K_r:
            self.game.levels.reset_game_world(new_map=True, new_level=False)
            self.game.missions.spawn_mission_objectives()
        elif event.key == pygame.K_e:
            self.game.player.toggle_hiding_spot(self.game.hiding_spots)

    def _handle_weapon_hotkey(self, key: int) -> None:
        """Switches the equipped weapon based on its unlocked-slot index."""
        unlocked = self.game.profile_data.get("unlocked_weapons", [])

        if key == pygame.K_1 and "knife" in unlocked:
            self.game.player.change_weapon(unlocked.index("knife"))
        elif key == pygame.K_2 and "pistol_silenced" in unlocked:
            self.game.player.change_weapon(unlocked.index("pistol_silenced"))
        elif key == pygame.K_3:
            if "shotgun" in unlocked:
                self.game.player.change_weapon(unlocked.index("shotgun"))
            else:
                logger.info("Shotgun not purchased yet!")
        elif key == pygame.K_4:
            if "rifle" in unlocked:
                self.game.player.change_weapon(unlocked.index("rifle"))
            else:
                logger.info("Rifle not purchased yet!")

    def _handle_menu_inputs(self, event: pygame.event.Event) -> None:
        """Handles keyboard input across the various menu screens."""
        if event.type != pygame.KEYDOWN:
            return

        if self.game.game_state == "MENU":
            if event.key == pygame.K_SPACE:
                current_level = self.game.profile_data.get("current_level", 1)
                self.game.missions.load_mission(current_level)
            elif event.key == pygame.K_1:
                self.game.missions.load_mission(1)
            elif event.key == pygame.K_ESCAPE:
                self.game.running = False

        elif self.game.game_state == "SETTINGS":
            if event.key == pygame.K_ESCAPE:
                SaveManager.save_game(self.game.profile_data)
                self.game.game_state = self.game.settings_return_state

        elif self.game.game_state == "GAME_OVER":
            if event.key == pygame.K_r:
                self.game.levels.reset_game_world(new_map=False, new_level=False)
                self.game.missions.spawn_mission_objectives()
                self.game.game_state = "PLAYING"
            elif event.key == pygame.K_SPACE:
                self.game.missions.load_mission(self.game.missions.current_mission_num)
                self.game.game_state = "PLAYING"
            elif event.key in [pygame.K_m, pygame.K_ESCAPE]:
                self.game.game_state = "MENU"

        elif self.game.game_state == "VICTORY":
            if event.key == pygame.K_SPACE:
                self.game.game_state = "SHOP"
            elif event.key in [pygame.K_m, pygame.K_ESCAPE]:
                self.game.game_state = "MENU"

        elif self.game.game_state == "VICTORY_ALL":
            if event.key == pygame.K_SPACE:
                self.game.missions.load_mission(1)
                self.game.game_state = "PLAYING"
            elif event.key in [pygame.K_m, pygame.K_ESCAPE]:
                self.game.game_state = "MENU"

        elif self.game.game_state == "PAUSE" and event.key == pygame.K_ESCAPE:
            self.game.game_state = "PLAYING"

        elif self.game.game_state == "SHOP":
            if event.key == pygame.K_SPACE:
                self.game.missions.load_mission(self.game.missions.current_mission_num + 1)
            elif event.key in [pygame.K_m, pygame.K_ESCAPE]:
                self.game.game_state = "MENU"

    def _update_settings_sliders(self, mouse_pos: tuple[int, int]) -> None:
        """Updates volume sliders and immediately applies changes to the SoundManager."""
        mouse_pressed = pygame.mouse.get_pressed()[0]
        music_slider, sfx_slider = self.game.settings_sliders

        music_slider.update(mouse_pos, mouse_pressed)
        sfx_slider.update(mouse_pos, mouse_pressed)

        self.game.sound.set_music_volume(music_slider.value)
        self.game.sound.set_sfx_volume(sfx_slider.value)
        self.game.profile_data["settings"]["music_volume"] = music_slider.value
        self.game.profile_data["settings"]["sfx_volume"] = sfx_slider.value

    def _update_ui_button_actions(self, mouse_pos: tuple[int, int], mouse_click: tuple[bool, bool, bool]) -> None:
        """Handles mouse clicks on the currently active screen's UI buttons."""
        active_buttons = self._get_active_buttons()

        for btn in active_buttons:
            action = btn.update(mouse_pos, mouse_click)
            if action:
                self._handle_button_action(action)

    def _get_active_buttons(self) -> list:
        """Returns the button list belonging to the current game state."""
        buttons_by_state = {
            "MENU": self.game.main_menu_buttons,
            "PAUSE": self.game.pause_buttons,
            "GAME_OVER": self.game.game_over_buttons,
            "VICTORY": self.game.victory_buttons,
            "VICTORY_ALL": self.game.victory_all_buttons,
            "SHOP": self.game.shop_buttons,
            "SETTINGS": self.game.settings_buttons,
        }
        return buttons_by_state.get(self.game.game_state, [])

    def _reset_player_shot_timer(self) -> None:
        """Resets the shot cooldown so a held menu click can't fire a weapon on spawn."""
        if hasattr(self.game, "player") and self.game.player:
            self.game.player.last_shot_time = pygame.time.get_ticks()

    def _handle_button_action(self, action: str) -> None:
        """Dispatches a single UI button action to its effect on the game state."""
        # Core game-state transitions
        if action == "NEW_GAME":
            self.game.missions.load_mission(1)
            self.game.game_state = "PLAYING"
            self._reset_player_shot_timer()
        elif action == "CONTINUE_GAME":
            current_level = self.game.profile_data.get("current_level", 1)
            self.game.missions.load_mission(current_level)
            self._reset_player_shot_timer()
        elif action == "OPEN_SETTINGS":
            # Remember where to return to (main menu or pause)
            self.game.settings_return_state = self.game.game_state
            self.game.game_state = "SETTINGS"
        elif action == "SETTINGS_BACK":
            SaveManager.save_game(self.game.profile_data)
            self.game.game_state = self.game.settings_return_state
        elif action == "SAVE_GAME":
            SaveManager.save_game(self.game.profile_data)
            self.game.save_feedback_timer = 90  # ~1.5s at 60 FPS
            logger.info("Game saved manually.")
        elif action == "CONTINUE":
            self.game.game_state = "PLAYING"
            self._reset_player_shot_timer()
        elif action == "RESTART":
            self.game.missions.load_mission(self.game.missions.current_mission_num)
            self.game.game_state = "PLAYING"
            self._reset_player_shot_timer()
        elif action == "RESTART_FIRST":
            self.game.missions.load_mission(1)
            self.game.game_state = "PLAYING"
            self._reset_player_shot_timer()
        elif action == "OPEN_SHOP":
            self.game.game_state = "SHOP"
        elif action == "NEXT_MISSION":
            # MissionManager.load_mission determines whether this was the last
            # mission and sets the matching game_state (PLAYING or VICTORY_ALL)
            self.game.missions.load_mission(self.game.missions.current_mission_num + 1)
            if self.game.game_state == "PLAYING":
                self._reset_player_shot_timer()
        elif action == "MAIN_MENU":
            self.game.game_state = "MENU"
        elif action == "QUIT":
            self.game.running = False
        else:
            self._handle_shop_action(action)

    def _handle_shop_action(self, action: str) -> None:
        """Handles skill-point upgrades and weapon purchases in the shop screen."""
        if action == "BUY_UPGRADE_HP":
            if self.game.progression.upgrade_skill("max_hp"):
                SaveManager.save_game(self.game.profile_data)
                # Refresh the current player's stats right after the purchase!
                self.game.apply_player_upgrades()
                logger.info("Health upgraded successfully!")
        elif action == "BUY_UPGRADE_ARMOR":
            if self.game.progression.upgrade_skill("max_armor"):
                SaveManager.save_game(self.game.profile_data)
                self.game.apply_player_upgrades()
                logger.info("Armor upgraded successfully!")
        elif action == "BUY_UPGRADE_SPEED":
            if self.game.progression.upgrade_skill("speed"):
                SaveManager.save_game(self.game.profile_data)
                self.game.apply_player_upgrades()
                logger.info("Speed upgraded successfully!")
        elif action == "BUY_WEAPON_RIFLE":
            success, msg = self.game.shop.buy_weapon("rifle")
            logger.info(msg)
            if success:
                SaveManager.save_game(self.game.profile_data)
        elif action == "BUY_WEAPON_SHOTGUN":
            success, msg = self.game.shop.buy_weapon("shotgun")
            logger.info(msg)
            if success:
                SaveManager.save_game(self.game.profile_data)
