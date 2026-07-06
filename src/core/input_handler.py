# src/core/input_handler.py
import pygame

class InputHandler:
    def __init__(self, game):
        self.game = game

    def handle_events(self):
        """Обробка глобальних системних подій операційної системи та введення користувача"""
        mouse_pos = pygame.mouse.get_pos()
        mouse_click = pygame.mouse.get_pressed()

        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                self.game.running = False
            elif self.game.game_state == "PLAYING":
                self._handle_playing_inputs(event)
            else:
                self._handle_menu_inputs(event)

        self._update_ui_button_actions(mouse_pos, mouse_click)

    def _handle_playing_inputs(self, event):
        """Обробка гарячих клавіш керування безпосередньо під час ігрового процесу"""
        if event.type == pygame.KEYDOWN:
            if event.key == pygame.K_ESCAPE:
                self.game.game_state = "PAUSE"
            elif event.key == pygame.K_1:
                self.game.player.change_weapon(0)
            elif event.key == pygame.K_2:
                self.game.player.change_weapon(1)
            elif event.key == pygame.K_3:
                self.game.player.change_weapon(2)
            elif event.key == pygame.K_r:
                self.game.levels.reset_game_world(new_map=True, new_level=False)
                self.game.missions.spawn_mission_objectives()
            elif event.key == pygame.K_e:
                if self.game.player.is_hidden:
                    self.game.player.is_hidden = False
                else:
                    hit_spot = pygame.sprite.spritecollideany(self.game.player, self.game.hiding_spots)
                    if hit_spot:
                        self.game.player.is_hidden = True
                        self.game.player.pos = pygame.math.Vector2(hit_spot.rect.center)

    def _handle_menu_inputs(self, event):
        """Обробка натискань клавіатури в інтерфейсах меню"""
        if event.type == pygame.KEYDOWN:
            if self.game.game_state == "MENU":
                if event.key in [pygame.K_1, pygame.K_SPACE]:
                    self.game.missions.load_mission(1)
                    self.game.game_state = "PLAYING"
                elif event.key == pygame.K_ESCAPE:
                    self.game.running = False
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
                    # Просто викликаємо завантаження, менеджер сам вирішить, чи це фінал
                    self.game.missions.load_mission(self.game.missions.current_mission_num + 1)
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

    def _update_ui_button_actions(self, mouse_pos, mouse_click):
        """Обробка кліків миші по активних кнопках поточного стану графічного інтерфейсу"""
        active_buttons = []
        if self.game.game_state == "MENU":
            active_buttons = self.game.main_menu_buttons
        elif self.game.game_state == "PAUSE":
            active_buttons = self.game.pause_buttons
        elif self.game.game_state == "GAME_OVER":
            active_buttons = self.game.game_over_buttons
        elif self.game.game_state == "VICTORY":
            active_buttons = self.game.victory_buttons
        elif self.game.game_state == "VICTORY_ALL":
            active_buttons = self.game.victory_all_buttons

        for btn in active_buttons:
            action = btn.update(mouse_pos, mouse_click)
            if action == "START":
                self.game.missions.load_mission(1)
                self.game.game_state = "PLAYING"
            elif action == "CONTINUE":
                self.game.game_state = "PLAYING"
            elif action == "RESTART":
                self.game.missions.load_mission(self.game.missions.current_mission_num)
                self.game.game_state = "PLAYING"
            elif action == "RESTART_FIRST":
                self.game.missions.load_mission(1)
                self.game.game_state = "PLAYING"
            elif action == "NEXT_MISSION":
                # Жодних імпортів! Делегуємо всю роботу менеджеру місій
                self.game.missions.load_mission(self.game.missions.current_mission_num + 1)
            elif action == "MAIN_MENU":
                self.game.game_state = "MENU"
            elif action == "QUIT":
                self.game.running = False