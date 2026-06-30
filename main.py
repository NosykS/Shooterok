# main.py
import pygame
import sys
import random
import math
from src.settings import SCREEN_WIDTH, SCREEN_HEIGHT, FPS, BG_COLOR, WEAPONS, WHITE, TILE_SIZE, GRID_WIDTH, GRID_HEIGHT, \
    ENEMY_LOSE_INTEREST_TIME, ENEMY_TYPES
from src.player import Player
from src.enemy import Enemy
from src.obstacle import Obstacle
from src.hiding_spot import HidingSpot

pygame.init()
font_large = pygame.font.SysFont("Arial", 48, bold=True)
font_medium = pygame.font.SysFont("Arial", 28)
font_small = pygame.font.SysFont("Arial", 18)


def create_grid_matrix():
    matrix = [[1 for _ in range(GRID_WIDTH)] for _ in range(GRID_HEIGHT)]
    for x in range(3, 9): matrix[3][x] = 0
    for y in range(4, 11): matrix[y][14] = 0
    for x in range(2, 7): matrix[10][x] = 0
    for y in range(10, 14): matrix[y][6] = 0
    return matrix


def draw_menu(screen):
    screen.fill((20, 25, 30))
    title_text = font_large.render("MILITARY STEALTH SHOOTER", True, (200, 50, 50))
    subtitle_text = font_medium.render("Hardcore Tactical Stealth", True, (150, 150, 150))
    play_button = font_medium.render("[ 1 ] START MISSION", True, WHITE)
    exit_button = font_medium.render("[ ESC ] ABANDON", True, (120, 120, 120))

    screen.blit(title_text, (SCREEN_WIDTH // 2 - title_text.get_width() // 2, 150))
    screen.blit(subtitle_text, (SCREEN_WIDTH // 2 - subtitle_text.get_width() // 2, 220))
    screen.blit(play_button, (SCREEN_WIDTH // 2 - play_button.get_width() // 2, 380))
    screen.blit(exit_button, (SCREEN_WIDTH // 2 - exit_button.get_width() // 2, 440))


def draw_game_over(screen):
    screen.fill((40, 10, 10))
    title_text = font_large.render("MISSION FAILED", True, (255, 0, 0))
    retry_text = font_medium.render("Press [ R ] to Restart", True, WHITE)
    menu_text = font_medium.render("Press [ M ] for Main Menu", True, (150, 150, 150))
    exit_text = font_medium.render("Press [ ESC ] to Quit Game", True, (200, 50, 50))

    screen.blit(title_text, (SCREEN_WIDTH // 2 - title_text.get_width() // 2, 180))
    screen.blit(retry_text, (SCREEN_WIDTH // 2 - retry_text.get_width() // 2, 300))
    screen.blit(menu_text, (SCREEN_WIDTH // 2 - menu_text.get_width() // 2, 360))
    screen.blit(exit_text, (SCREEN_WIDTH // 2 - exit_text.get_width() // 2, 420))


def draw_victory(screen):
    screen.fill((10, 35, 15))
    title_text = font_large.render("MISSION ACCOMPLISHED", True, (0, 255, 100))
    retry_text = font_medium.render("Press [ R ] to Play Again", True, WHITE)
    menu_text = font_medium.render("Press [ M ] for Main Menu", True, (150, 150, 150))
    exit_text = font_medium.render("Press [ ESC ] to Quit Game", True, (200, 50, 50))

    screen.blit(title_text, (SCREEN_WIDTH // 2 - title_text.get_width() // 2, 180))
    screen.blit(retry_text, (SCREEN_WIDTH // 2 - retry_text.get_width() // 2, 300))
    screen.blit(menu_text, (SCREEN_WIDTH // 2 - menu_text.get_width() // 2, 360))
    screen.blit(exit_text, (SCREEN_WIDTH // 2 - exit_text.get_width() // 2, 420))


def draw_controls_help(screen):
    controls = [
        "CONTROLS:",
        "WASD - Movement",
        "LSHIFT - Slow Stealth Walk",
        "HOLD MOUSE - Continuous Attack",
        "1, 2, 3 - Switch Weapons",
        "E - Enter / Exit Cover (Bush)",
        "R - Manual Reset Level"
    ]
    start_y = 20
    for idx, line in enumerate(controls):
        color = (200, 200, 200) if idx > 0 else (255, 200, 50)
        txt = font_small.render(line, True, color)
        screen.blit(txt, (SCREEN_WIDTH - 230, start_y + idx * 22))


def draw_player_bars(screen, player):
    hp_bar_rect = pygame.Rect(20, 20, 200, 20)
    pygame.draw.rect(screen, (80, 0, 0), hp_bar_rect)
    hp_width = int((player.hp / player.max_hp) * 200)
    if hp_width > 0:
        pygame.draw.rect(screen, (220, 20, 20), pygame.Rect(20, 20, hp_width, 20))
    pygame.draw.rect(screen, WHITE, hp_bar_rect, 2)

    hp_text = font_small.render(f"HP: {max(0, player.hp)}/{player.max_hp}", True, WHITE)
    screen.blit(hp_text, (25, 21))

    armor_bar_rect = pygame.Rect(20, 45, 200, 15)
    pygame.draw.rect(screen, (0, 0, 80), armor_bar_rect)
    armor_width = int((player.armor / player.max_armor) * 200)
    if armor_width > 0:
        pygame.draw.rect(screen, (0, 120, 255), pygame.Rect(20, 45, armor_width, 15))
    pygame.draw.rect(screen, WHITE, armor_bar_rect, 2)

    armor_text = font_small.render(f"ARMOR: {player.armor}/{player.max_armor}", True, WHITE)
    screen.blit(armor_text, (25, 44))


def main():
    screen = pygame.display.set_mode((SCREEN_WIDTH, SCREEN_HEIGHT))
    pygame.display.set_caption("Military Stealth Shooter: Hardcore Stealth")
    clock = pygame.time.Clock()

    game_state = "MENU"

    # Створюємо змінні для збереження структури карти між програшами
    saved_game_matrix = None
    saved_hiding_spots_data = []

    def reset_game(new_map=True):
        nonlocal player, all_sprites, bullets, enemies, obstacles, hiding_spots, game_matrix
        nonlocal saved_game_matrix, saved_hiding_spots_data

        # Очищення старих спрайтів
        if all_sprites:
            for sprite in all_sprites:
                sprite.kill()

        player = Player(SCREEN_WIDTH // 2, SCREEN_HEIGHT // 2)

        all_sprites = pygame.sprite.Group()
        bullets = pygame.sprite.Group()
        enemies = pygame.sprite.Group()
        obstacles = pygame.sprite.Group()
        hiding_spots = pygame.sprite.Group()

        all_sprites.add(player)

        # --- ЛОГІКА КАРТИ (ЦІЛІСНІ СТІНИ) ---
        if new_map or saved_game_matrix is None:
            # 1. Заповнюємо карту пустотою (1 - вільна плитка)
            game_matrix = [[1 for _ in range(GRID_WIDTH)] for _ in range(GRID_HEIGHT)]

            # 2. Робимо глухі стіни по краях екрана
            for y in range(GRID_HEIGHT):
                for x in range(GRID_WIDTH):
                    if x == 0 or y == 0 or x == GRID_WIDTH - 1 or y == GRID_HEIGHT - 1:
                        game_matrix[y][x] = 0

            # 3. Генеруємо закінчені фігури стін (лінії та кути)
            num_walls = random.randint(5, 8)  # Кількість суцільних стін на карті
            for _ in range(num_walls):
                # Вибираємо випадкову початкову точку на сітці (відступаємо від країв)
                start_x = random.randint(2, GRID_WIDTH - 3)
                start_y = random.randint(2, GRID_HEIGHT - 3)

                # Випадкова довжина стіни (від 3 до 6 блоків)
                wall_length = random.randint(3, 6)
                # Напрямок: True - горизонтальна стіна, False - вертикальна
                is_horizontal = random.choice([True, False])

                for i in range(wall_length):
                    curr_x = start_x + (i if is_horizontal else 0)
                    curr_y = start_y + (0 if is_horizontal else i)

                    # Перевіряємо, щоб не вийти за межі карти
                    if 0 < curr_x < GRID_WIDTH - 1 and 0 < curr_y < GRID_HEIGHT - 1:
                        # Перевірка безпечної зони навколо гравця (щоб стіна не заспавнилась на гравцеві)
                        pixel_x = curr_x * TILE_SIZE + TILE_SIZE // 2
                        pixel_y = curr_y * TILE_SIZE + TILE_SIZE // 2
                        if pygame.math.Vector2(pixel_x, pixel_y).distance_to(player.pos) > 90:
                            game_matrix[curr_y][curr_x] = 0

            # Зберігаємо згенеровану карту
            saved_game_matrix = [row[:] for row in game_matrix]
            saved_hiding_spots_data = []
        else:
            game_matrix = [row[:] for row in saved_game_matrix]

        # Створюємо об'єкти стін
        for row_idx, row in enumerate(game_matrix):
            for col_idx, value in enumerate(row):
                if value == 0:
                    wall = Obstacle(col_idx * TILE_SIZE, row_idx * TILE_SIZE, TILE_SIZE, TILE_SIZE)
                    obstacles.add(wall)
                    all_sprites.add(wall)

        # --- ОНОВЛЕНА ЛОГІКА КУЩІВ (БІЛЬШЕ І ГРУПАМИ) ---
        if new_map or not saved_hiding_spots_data:
            # Створюємо 3-4 великі "зони" кущів (по кілька кущів поруч)
            num_bush_clusters = random.randint(3, 4)
            attempts = 0

            while num_bush_clusters > 0 and attempts < 100:
                attempts += 1
                # Центр майбутнього кластера кущів
                center_x = random.randint(2, GRID_WIDTH - 3)
                center_y = random.randint(2, GRID_HEIGHT - 3)

                if game_matrix[center_y][center_x] == 1:
                    # Спавним групу кущів 2х2 або в радіусі поруч з центром
                    cluster_size = random.randint(2, 4)  # Кількість кущів у групі

                    for _ in range(cluster_size):
                        # Розкид навколо центру кластера
                        offset_x = random.randint(-1, 1)
                        offset_y = random.randint(-1, 1)
                        gx = center_x + offset_x
                        gy = center_y + offset_y

                        # Перевіряємо умови спавну окремого куща
                        if 0 < gx < GRID_WIDTH - 1 and 0 < gy < GRID_HEIGHT - 1:
                            if game_matrix[gy][gx] == 1:
                                pixel_x = gx * TILE_SIZE
                                pixel_y = gy * TILE_SIZE
                                p_dist = pygame.math.Vector2(pixel_x + TILE_SIZE // 2,
                                                             pixel_y + TILE_SIZE // 2).distance_to(player.pos)

                                # Щоб кущі не дублювалися на одній плитці
                                already_exists = any(
                                    p[0] == pixel_x and p[1] == pixel_y for p in saved_hiding_spots_data)

                                if p_dist > 80 and not already_exists:
                                    spot = HidingSpot(pixel_x, pixel_y, TILE_SIZE, TILE_SIZE)
                                    hiding_spots.add(spot)
                                    all_sprites.add(spot)
                                    saved_hiding_spots_data.append((pixel_x, pixel_y))

                    num_bush_clusters -= 1
        else:
            # Відновлення кущів після програшу
            for pos_x, pos_y in saved_hiding_spots_data:
                spot = HidingSpot(pos_x, pos_y, TILE_SIZE, TILE_SIZE)
                hiding_spots.add(spot)
                all_sprites.add(spot)

        # --- СПАВН ВОРОГІВ ---
        num_enemies = random.randint(2, 4)
        enemy_types_available = list(ENEMY_TYPES.keys())

        for _ in range(num_enemies):
            enemy_x, enemy_y = 0, 0
            enemy_attempts = 0
            while enemy_attempts < 200:
                enemy_attempts += 1
                grid_x = random.randint(1, GRID_WIDTH - 2)
                grid_y = random.randint(1, GRID_HEIGHT - 2)
                if game_matrix[grid_y][grid_x] == 1:
                    pixel_x = grid_x * TILE_SIZE + TILE_SIZE // 2
                    pixel_y = grid_y * TILE_SIZE + TILE_SIZE // 2
                    is_on_bush = any(spot.rect.collidepoint(pixel_x, pixel_y) for spot in hiding_spots)
                    if pygame.math.Vector2(pixel_x, pixel_y).distance_to(player.pos) > 180 and not is_on_bush:
                        enemy_x, enemy_y = pixel_x, pixel_y
                        break

            if enemy_x != 0 and enemy_y != 0:
                chosen_type = random.choice(enemy_types_available)
                enemy = Enemy(enemy_x, enemy_y, chosen_type, game_matrix=game_matrix)
                enemies.add(enemy)
                all_sprites.add(enemy)
    player = None
    all_sprites = None
    bullets = None
    enemies = None
    obstacles = None
    hiding_spots = None
    game_matrix = None
    reset_game()

    gunshot_visual_timer = 0
    gunshot_visual_pos = (0, 0)
    gunshot_visual_radius = 0

    # ДОДАНО: Таймер та позиція для відображення зони ураження ножем
    knife_visual_timer = 0
    knife_visual_pos = (0, 0)
    knife_attack_radius = 60  # Радіус ураження ножем із твоєї логіки атак

    running = True
    while running:
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                running = False

            elif game_state == "MENU":
                if event.type == pygame.KEYDOWN:
                    if event.key == pygame.K_1:
                        reset_game()
                        game_state = "PLAYING"
                    elif event.key == pygame.K_ESCAPE:
                        running = False

            elif game_state in ["GAME_OVER", "VICTORY"]:
                if event.type == pygame.KEYDOWN:
                    if event.key == pygame.K_r:
                        reset_game()
                        game_state = "PLAYING"
                    elif event.key == pygame.K_m:
                        game_state = "MENU"
                    elif event.key == pygame.K_ESCAPE:
                        running = False

            elif game_state == "PLAYING":
                if event.type == pygame.KEYDOWN:
                    if event.key == pygame.K_1: player.change_weapon(0)
                    if event.key == pygame.K_2: player.change_weapon(1)
                    if event.key == pygame.K_3: player.change_weapon(2)
                    if event.key == pygame.K_r: reset_game()

                    if event.key == pygame.K_e:
                        if player.is_hidden:
                            player.is_hidden = False
                        else:
                            hit_spot = pygame.sprite.spritecollideany(player, hiding_spots)
                            if hit_spot:
                                player.is_hidden = True
                                player.pos = pygame.math.Vector2(hit_spot.rect.center)

        if game_state == "PLAYING":
            keys = pygame.key.get_pressed()
            is_moving_normally = player.current_noise_radius > 0 and (
                    keys[pygame.K_w] or keys[pygame.K_s] or keys[pygame.K_a] or keys[pygame.K_d])

            player.update(keys, obstacles)

            mouse_buttons = pygame.mouse.get_pressed()
            if mouse_buttons[0]:
                attack_result = player.attack()

                if attack_result == "melee":
                    # Отримуємо радіус атаки з налаштувань, якщо він там є, або використовуємо 60 як дефолт
                    knife_attack_radius = WEAPONS["knife"].get("damage_radius", 60)

                    # Динамічно прив'язуємо радіус та позицію для малювання
                    knife_visual_timer = 6
                    knife_visual_pos = (int(player.pos.x), int(player.pos.y))

                    # Визначаємо кут, куди дивиться гравець (на мишку)
                    mouse_pos = pygame.mouse.get_pos()
                    player_to_mouse = pygame.math.Vector2(mouse_pos) - player.pos

                    if player_to_mouse.length() > 0:
                        _, player_angle = player_to_mouse.as_polar()
                    else:
                        player_angle = 0  # Якщо мишка на гравцеві

                    for enemy in list(enemies):
                        enemy_vec = enemy.pos - player.pos
                        distance = enemy_vec.length()

                        # 1. Перевірка динамічної відстані
                        if distance < knife_attack_radius:
                            # 2. Перевірка конуса (наприклад, 90 градусів: +-45 від погляду)
                            if distance > 0:
                                _, angle_to_enemy = enemy_vec.as_polar()
                                angle_diff = (angle_to_enemy - player_angle) % 360
                                if angle_diff > 180:
                                    angle_diff = 360 - angle_diff

                                # Якщо ворог потрапляє в сектор 90 градусів (по 45 в кожен бік)
                                if angle_diff <= 45:
                                    if not enemy.is_alerted:
                                        enemy.hp = 0
                                        print(f"Тихий кіл ножем! Ворог {enemy.type} ліквідований.")
                                    else:
                                        enemy.hp -= WEAPONS["knife"]["damage"]
                                        print(f"Поранення ножем! HP ворога: {enemy.hp}")

                                    enemy.is_alerted = True
                                    enemy.last_known_player_pos = pygame.math.Vector2(player.pos)
                                    enemy.lose_interest_timer = ENEMY_LOSE_INTEREST_TIME

                                    # Тривога для інших
                                    for other_enemy in enemies:
                                        if other_enemy != enemy and not other_enemy.is_alerted:
                                            if other_enemy.check_for_player(player, obstacles):
                                                other_enemy.is_alerted = True
                                                other_enemy.last_known_player_pos = pygame.math.Vector2(player.pos)
                                                other_enemy.lose_interest_timer = ENEMY_LOSE_INTEREST_TIME
                                    if enemy.hp <= 0:
                                        enemy.kill()

                elif attack_result:
                    all_sprites.add(attack_result)
                    bullets.add(attack_result)

                    weapon_stats = WEAPONS[player.current_weapon]
                    noise_rad = weapon_stats["noise_radius"]

                    if noise_rad > 0 and not getattr(player, "is_hidden", False):
                        for enemy in enemies:
                            if enemy.pos.distance_to(player.pos) < noise_rad:
                                enemy.is_alerted = True
                                enemy.last_known_player_pos = pygame.math.Vector2(player.pos)
                                enemy.lose_interest_timer = ENEMY_LOSE_INTEREST_TIME

                        gunshot_visual_timer = 10
                        gunshot_visual_pos = (int(player.pos.x), int(player.pos.y))
                        gunshot_visual_radius = noise_rad

            bullets.update()
            enemies.update(player, game_matrix, obstacles)

            for enemy in enemies:
                if enemy.fired_bullet:
                    bullets.add(enemy.fired_bullet)
                    all_sprites.add(enemy.fired_bullet)

            if is_moving_normally and not player.is_hidden:
                for enemy in enemies:
                    if enemy.pos.distance_to(player.pos) <= player.current_noise_radius:
                        enemy.is_alerted = True
                        enemy.last_known_player_pos = pygame.math.Vector2(player.pos)
                        enemy.lose_interest_timer = ENEMY_LOSE_INTEREST_TIME

            for bullet in list(bullets):
                if pygame.sprite.spritecollideany(bullet, obstacles):
                    bullet.kill()
                    continue

                if bullet.is_enemy_bullet:
                    if bullet.rect.colliderect(player.rect):
                        if not player.is_hidden:
                            damage_to_deal = bullet.damage
                            if player.armor > 0:
                                armor_absorption = int(damage_to_deal * 0.6)
                                if player.armor >= armor_absorption:
                                    player.armor -= armor_absorption
                                    damage_to_deal -= armor_absorption
                                else:
                                    damage_to_deal -= player.armor
                                    player.armor = 0

                            player.hp -= damage_to_deal
                            print(f"Гравець поранений! HP: {player.hp} | Броня: {player.armor}")

                            if player.hp <= 0:
                                game_state = "GAME_OVER"
                        bullet.kill()

                else:
                    hit_enemies = pygame.sprite.spritecollide(bullet, enemies, False)
                    for enemy in hit_enemies:
                        damage_to_deal = bullet.damage
                        if enemy.armor > 0:
                            armor_absorption = int(damage_to_deal * 0.5)
                            if enemy.armor >= armor_absorption:
                                enemy.armor -= armor_absorption
                                damage_to_deal -= armor_absorption
                            else:
                                damage_to_deal -= enemy.armor
                                enemy.armor = 0

                        enemy.hp -= damage_to_deal
                        enemy.is_alerted = True
                        enemy.last_known_player_pos = pygame.math.Vector2(player.pos)
                        bullet.kill()

                        if enemy.hp <= 0:
                            enemy.kill()
            # ПРОГРАШ У РАЗІ КОЛИ ВОРОГ ПІДІЙШОВ У ПРИТУЛ ДО ГРАВЦЯ
            # for enemy in enemies:
            #     if enemy.hitbox.colliderect(player.rect) and not player.is_hidden:
            #         game_state = "GAME_OVER"

            if len(enemies) == 0:
                game_state = "VICTORY"

        if game_state == "MENU":
            draw_menu(screen)
        elif game_state == "GAME_OVER":
            draw_game_over(screen)
        elif game_state == "VICTORY":
            draw_victory(screen)
        elif game_state == "PLAYING":
            screen.fill(BG_COLOR)

            for enemy in enemies:
                enemy.draw_vision_cone(screen)

            if gunshot_visual_timer > 0:
                s = pygame.Surface((gunshot_visual_radius * 2, gunshot_visual_radius * 2), pygame.SRCALPHA)
                pygame.draw.circle(s, (100, 200, 255, 120), (gunshot_visual_radius, gunshot_visual_radius),
                                   gunshot_visual_radius, 4)
                screen.blit(s, (
                    gunshot_visual_pos[0] - gunshot_visual_radius, gunshot_visual_pos[1] - gunshot_visual_radius))
                gunshot_visual_timer -= 1

            # --- ОНОВЛЕНО: Малювання НАПІВПРОЗОРОГО КОНУСА атаки ножем ---
            if knife_visual_timer > 0:
                knife_attack_radius = WEAPONS["knife"].get("damage_radius", 60)
                knife_visual_pos = player.pos

                # Напрямок погляду гравця
                mouse_pos = pygame.mouse.get_pos()
                player_to_mouse = pygame.math.Vector2(mouse_pos) - player.pos

                if player_to_mouse.length() > 0:
                    _, player_angle = player_to_mouse.as_polar()
                else:
                    player_angle = 0

                # Створюємо поверхню для прозорості на весь екран (так простіше малювати глобальні сектори)
                knife_surf = pygame.Surface((SCREEN_WIDTH, SCREEN_HEIGHT), pygame.SRCALPHA)

                # Будуємо точки конуса (кут огляду сектора — 90 градусів)
                points = [knife_visual_pos]
                num_segments = 16
                view_angle = 90  # Кут конуса удару
                start_angle = player_angle - view_angle / 2

                for i in range(num_segments + 1):
                    ang = start_angle + (view_angle / num_segments) * i
                    rad = math.radians(ang)
                    target_point = knife_visual_pos + pygame.math.Vector2(math.cos(rad), math.sin(rad)) * knife_attack_radius
                    points.append(target_point)

                # Малюємо конус
                if len(points) >= 3:
                    pygame.draw.polygon(knife_surf, (255, 50, 50, 50), points)  # Заливка конуса
                    # Малюємо дугу (лінію ураження) для чіткості
                    pygame.draw.lines(knife_surf, (255, 100, 100, 180), False, points[1:], 2)

                screen.blit(knife_surf, (0, 0))
                knife_visual_timer -= 1

            if is_moving_normally and not player.is_hidden:
                pygame.draw.circle(screen, (0, 150, 255), (int(player.pos.x), int(player.pos.y)),
                                   player.current_noise_radius, 1)

            for sprite in all_sprites:
                if sprite == player and player.is_hidden: continue
                screen.blit(sprite.image, sprite.rect)

            for enemy in enemies:
                enemy.draw_health_bar(screen)

            bullets.draw(screen)

            draw_player_bars(screen, player)

            keys = pygame.key.get_pressed()
            weapon_name = player.current_weapon.upper()
            weapon_stats = WEAPONS[player.current_weapon]

            ammo_str = f"AMMO: {weapon_stats['ammo_capacity']}/{weapon_stats['ammo_capacity']}" if weapon_stats[
                                                                                                       'ammo_capacity'] > 0 else "AMMO: INF"

            stealth_status = "STEALTH" if keys[pygame.K_LSHIFT] else "RUNNING"
            if player.is_hidden: stealth_status = "HIDDEN"

            weapon_ui_text = font_medium.render(f"WEAPON: {weapon_name}  [{ammo_str}]", True, (255, 200, 50))
            status_ui_text = font_medium.render(f"MODE: {stealth_status}  |  ENEMIES LEFT: {len(enemies)}", True, WHITE)

            screen.blit(weapon_ui_text, (20, SCREEN_HEIGHT - 65))
            screen.blit(status_ui_text, (20, SCREEN_HEIGHT - 35))

            draw_controls_help(screen)

        pygame.display.flip()
        clock.tick(FPS)

    pygame.quit()
    sys.exit()


if __name__ == "__main__":
    main()