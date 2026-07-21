# src/core/input_handler.py
import pygame
from src.core.save_manager import SaveManager


class InputHandler:
    def __init__(self, game):
        self.game = game

    def handle_events(self):
        """Обробка глобальних системних подій операційної системи та введення користувача"""
        mouse_pos = pygame.mouse.get_pos()

        # Залишаємо ініціалізацію для кнопок, але клік передаємо як False за замовчуванням
        mouse_click = (False, False, False)

        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                self.game.running = False

            # ВИПРАВЛЕНО: Фіксуємо клік миші ТІЛЬКИ в момент натискання (одинична подія)
            elif event.type == pygame.MOUSEBUTTONDOWN:
                if event.button == 1:  # Ліва кнопка миші
                    mouse_click = (True, False, False)
                    # Оновлюємо кнопки інтерфейсу безпосередньо під час події кліку
                    self._update_ui_button_actions(mouse_pos, mouse_click)

            elif self.game.game_state == "PLAYING":
                self._handle_playing_inputs(event)
            else:
                self._handle_menu_inputs(event)

        # Перевірка наведення курсору (hover ефект для кольору кнопок) викликається кожен кадр
        if not mouse_click[0]:
            self._update_ui_button_actions(mouse_pos, (False, False, False))

    def _handle_playing_inputs(self, event):
        """Обробка гарячих клавіш керування безпосередньо під час ігрового процесу"""
        if event.type == pygame.KEYDOWN:
            if event.key == pygame.K_ESCAPE:
                self.game.game_state = "PAUSE"

            # --- ОНОВЛЕНА ЛОГІКА ЗМІНИ ЗБРОЇ (ДИНАМІЧНІ ІНДЕКСИ) ---
            elif event.key in [pygame.K_1, pygame.K_2, pygame.K_3, pygame.K_4]:
                unlocked = self.game.profile_data.get("unlocked_weapons", [])

                if event.key == pygame.K_1 and "knife" in unlocked:
                    self.game.player.change_weapon(unlocked.index("knife"))

                elif event.key == pygame.K_2 and "pistol_silenced" in unlocked:
                    self.game.player.change_weapon(unlocked.index("pistol_silenced"))

                elif event.key == pygame.K_3:
                    if "shotgun" in unlocked:
                        self.game.player.change_weapon(unlocked.index("shotgun"))
                    else:
                        print("[INPUT] Шотган ще не куплено!")

                elif event.key == pygame.K_4:
                    if "rifle" in unlocked:
                        self.game.player.change_weapon(unlocked.index("rifle"))
                    else:
                        print("[INPUT] Гвинтівка ще не куплена!")
            # --------------------------------------------------------

            elif event.key == pygame.K_r:
                self.game.levels.reset_game_world(new_map=True, new_level=False)
                self.game.missions.spawn_mission_objectives()
            elif event.key == pygame.K_e:
                if self.game.player.is_hidden:
                    # ВИХІД ЗІ СХОВАНКИ: Телепортуємо у безпечну точку виходу цього куща
                    if hasattr(self.game.player, "current_hideout") and self.game.player.current_hideout:
                        if hasattr(self.game.player.current_hideout, "exit_pos"):
                            self.game.player.pos = pygame.math.Vector2(self.game.player.current_hideout.exit_pos)
                        self.game.player.current_hideout = None

                    self.game.player.is_hidden = False
                    self.game.player.hitbox.center = self.game.player.pos
                    self.game.player.rect.center = self.game.player.pos
                    print("[STEALTH] Гравець вийшов у безпечну точку.")
                else:
                    # ВХІД У СХОВАНКУ: Шукаємо найближчий кущ
                    hit_spot = pygame.sprite.spritecollideany(self.game.player, self.game.hiding_spots)
                    if hit_spot:
                        self.game.player.is_hidden = True
                        self.game.player.current_hideout = hit_spot
                        self.game.player.pos = pygame.math.Vector2(hit_spot.rect.center)
                        self.game.player.hitbox.center = self.game.player.pos
                        self.game.player.rect.center = self.game.player.pos
                        print("[STEALTH] Гравець сховався.")

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
        elif self.game.game_state == "SHOP":
            active_buttons = self.game.shop_buttons

        for btn in active_buttons:
            action = btn.update(mouse_pos, mouse_click)
            if not action:
                continue

            # Базові ігрові стани
            if action == "START":
                self.game.missions.load_mission(1)
                self.game.game_state = "PLAYING"
                # ГАРАНТОВАНИЙ ФІКС: скидаємо кулдаун відразу після старту
                if hasattr(self.game, 'player') and self.game.player:
                    self.game.player.last_shot_time = pygame.time.get_ticks()

            elif action == "CONTINUE":
                self.game.game_state = "PLAYING"
                # ГАРАНТОВАНИЙ ФІКС: оновлюємо час, щоб затиснутий клік меню не став ударом ножа/пострілом
                if hasattr(self.game, 'player') and self.game.player:
                    self.game.player.last_shot_time = pygame.time.get_ticks()

            elif action == "RESTART":
                self.game.missions.load_mission(self.game.missions.current_mission_num)
                self.game.game_state = "PLAYING"
                if hasattr(self.game, 'player') and self.game.player:
                    self.game.player.last_shot_time = pygame.time.get_ticks()

            elif action == "RESTART_FIRST":
                self.game.missions.load_mission(1)
                self.game.game_state = "PLAYING"
                if hasattr(self.game, 'player') and self.game.player:
                    self.game.player.last_shot_time = pygame.time.get_ticks()

            elif action == "OPEN_SHOP":
                self.game.game_state = "SHOP"


            elif action == "NEXT_MISSION":
                # Перевіряємо, чи поточна місія була останньою (наприклад, 3-ю)
                # Якщо у вашому MissionManager є загальна кількість місій, можна використовувати її,
                # але зараз зафіксуємо перевірку на 3 місії:
                if self.game.missions.current_mission_num >= 3:
                    self.game.game_state = "VICTORY_ALL"
                    print("[MISSIONS] Усі місії пройдені! Перехід на екран фіналу кампанії.")
                else:
                    self.game.missions.load_mission(self.game.missions.current_mission_num + 1)
                    self.game.game_state = "PLAYING"
                    if hasattr(self.game, 'player') and self.game.player:
                        self.game.player.last_shot_time = pygame.time.get_ticks()
            elif action == "MAIN_MENU":
                self.game.game_state = "MENU"
            elif action == "QUIT":
                self.game.running = False

            # Обробка дій прокачки навичок (За очка Skill Points)
            elif action == "BUY_UPGRADE_HP":
                if self.game.progression.upgrade_skill("max_hp"):
                    SaveManager.save_game(self.game.profile_data)
                    # Оновлюємо характеристики поточного гравця відразу після покупки!
                    self.game.apply_player_upgrades()
                    print("[SHOP] Здоров'я успішно прокачано!")
            elif action == "BUY_UPGRADE_ARMOR":
                if self.game.progression.upgrade_skill("max_armor"):
                    SaveManager.save_game(self.game.profile_data)
                    self.game.apply_player_upgrades()
                    print("[SHOP] Броню успішно прокачано!")
            elif action == "BUY_UPGRADE_SPEED":
                if self.game.progression.upgrade_skill("speed"):
                    SaveManager.save_game(self.game.profile_data)
                    self.game.apply_player_upgrades()
                    print("[SHOP] Швидкість успішно прокачано!")

            # Обробка дій купівлі зброї (За гроші)
            elif action == "BUY_WEAPON_RIFLE":
                success, msg = self.game.shop.buy_weapon("rifle")
                print(f"[SHOP] {msg}")
                if success:
                    SaveManager.save_game(self.game.profile_data)
            elif action == "BUY_WEAPON_SHOTGUN":
                success, msg = self.game.shop.buy_weapon("shotgun")
                print(f"[SHOP] {msg}")
                if success:
                    SaveManager.save_game(self.game.profile_data)