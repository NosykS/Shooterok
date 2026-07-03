import random
import pygame
from src.settings import GRID_WIDTH, GRID_HEIGHT, TILE_SIZE


class MapGenerator:
    @staticmethod
    def generate_level(player_start_pos):
        """Генерує нову матрицю карти та повертає її разом із координатами кущів."""
        # 1. Базова пуста матриця зі стінами по краях
        game_matrix = [[1 for _ in range(GRID_WIDTH)] for _ in range(GRID_HEIGHT)]
        for y in range(GRID_HEIGHT):
            for x in range(GRID_WIDTH):
                if x == 0 or y == 0 or x == GRID_WIDTH - 1 or y == GRID_HEIGHT - 1:
                    game_matrix[y][x] = 0

        # 2. Генерація суцільних стін
        num_walls = random.randint(5, 8)
        for _ in range(num_walls):
            start_x = random.randint(2, GRID_WIDTH - 3)
            start_y = random.randint(2, GRID_HEIGHT - 3)
            wall_length = random.randint(3, 6)
            is_horizontal = random.choice([True, False])

            for i in range(wall_length):
                curr_x = start_x + (i if is_horizontal else 0)
                curr_y = start_y + (0 if is_horizontal else i)

                if 0 < curr_x < GRID_WIDTH - 1 and 0 < curr_y < GRID_HEIGHT - 1:
                    pixel_x = curr_x * TILE_SIZE + TILE_SIZE // 2
                    pixel_y = curr_y * TILE_SIZE + TILE_SIZE // 2
                    if pygame.math.Vector2(pixel_x, pixel_y).distance_to(player_start_pos) > 90:
                        game_matrix[curr_y][curr_x] = 0

        # 3. Генерація кластерів кущів
        hiding_spots_data = []
        num_bush_clusters = random.randint(3, 4)
        attempts = 0

        while num_bush_clusters > 0 and attempts < 100:
            attempts += 1
            center_x = random.randint(2, GRID_WIDTH - 3)
            center_y = random.randint(2, GRID_HEIGHT - 3)

            if game_matrix[center_y][center_x] == 1:
                cluster_size = random.randint(2, 4)

                for _ in range(cluster_size):
                    offset_x = random.randint(-1, 1)
                    offset_y = random.randint(-1, 1)
                    gx = center_x + offset_x
                    gy = center_y + offset_y

                    if 0 < gx < GRID_WIDTH - 1 and 0 < gy < GRID_HEIGHT - 1:
                        if game_matrix[gy][gx] == 1:
                            pixel_x = gx * TILE_SIZE
                            pixel_y = gy * TILE_SIZE
                            p_dist = pygame.math.Vector2(pixel_x + TILE_SIZE // 2,
                                                         pixel_y + TILE_SIZE // 2).distance_to(player_start_pos)

                            already_exists = any(p[0] == pixel_x and p[1] == pixel_y for p in hiding_spots_data)

                            if p_dist > 80 and not already_exists:
                                hiding_spots_data.append((pixel_x, pixel_y))

                num_bush_clusters -= 1

        return game_matrix, hiding_spots_data

    @staticmethod
    def get_enemy_spawn_positions(game_matrix, hiding_spots_data, player_pos, count=3):
        """Знаходить безпечні координати для спавну ворогів."""
        positions = []
        enemy_attempts = 0

        while len(positions) < count and enemy_attempts < 200:
            enemy_attempts += 1
            grid_x = random.randint(1, GRID_WIDTH - 2)
            grid_y = random.randint(1, GRID_HEIGHT - 2)

            if game_matrix[grid_y][grid_x] == 1:
                pixel_x = grid_x * TILE_SIZE + TILE_SIZE // 2
                pixel_y = grid_y * TILE_SIZE + TILE_SIZE // 2

                is_on_bush = any(
                    (pixel_x - TILE_SIZE // 2 == bx and pixel_y - TILE_SIZE // 2 == by)
                    for bx, by in hiding_spots_data
                )

                if pygame.math.Vector2(pixel_x, pixel_y).distance_to(player_pos) > 180 and not is_on_bush:
                    positions.append((pixel_x, pixel_y))

        return positions