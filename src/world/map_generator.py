import random
import pygame
from src.settings import GRID_WIDTH, GRID_HEIGHT, TILE_SIZE

# --- ШАБЛОНИ КІМНАТ (0 - стіна, 1 - підлога) ---
PREFABS = [
    [
        [0, 1, 1, 1, 1, 1, 1, 0],
        [1, 1, 1, 1, 1, 1, 1, 1],
        [1, 1, 0, 1, 1, 0, 1, 1],
        [1, 1, 1, 1, 1, 1, 1, 1],
        [1, 1, 1, 1, 1, 1, 1, 1],
        [1, 1, 0, 1, 1, 0, 1, 1],
        [1, 1, 1, 1, 1, 1, 1, 1],
        [0, 1, 1, 1, 1, 1, 1, 0]
    ],
    [
        [0, 1, 1, 1, 1, 1, 1, 0],
        [1, 1, 0, 0, 1, 0, 1, 1],
        [1, 1, 0, 0, 1, 0, 1, 1],
        [1, 1, 1, 1, 1, 1, 1, 1],
        [1, 1, 1, 1, 1, 1, 1, 1],
        [1, 1, 0, 1, 0, 0, 1, 1],
        [1, 1, 0, 1, 0, 0, 1, 1],
        [0, 1, 1, 1, 1, 1, 1, 0]
    ]
]

P_SIZE = 8


class MapGenerator:
    @staticmethod
    def generate_level(player_start_pos):
        """
        Розсовує дизайнерські кімнати на відстань і з'єднує їх
        довгими широкими коридорами, руйнуючи видиму структуру сітки.
        """
        game_matrix = [[0 for _ in range(GRID_WIDTH)] for _ in range(GRID_HEIGHT)]

        # Задаємо гнучку сітку: тепер сектори набагато більші за самі префаби
        cols = 3
        rows = 3
        sector_w = GRID_WIDTH // cols
        sector_h = GRID_HEIGHT // rows

        rooms = []
        room_centers = []

        # --- КРОК 1: Розміщення кімнат із випадковим зміщенням ---
        for r in range(rows):
            for c in range(cols):
                # Базові координати початку поточного сектора
                sec_x = c * sector_w
                sec_y = r * sector_h

                max_shift_x = sector_w - P_SIZE - 2
                max_shift_y = sector_h - P_SIZE - 2

                shift_x = random.randint(1, max_shift_x) if max_shift_x > 1 else 1
                shift_y = random.randint(1, max_shift_y) if max_shift_y > 1 else 1

                # ФІКС: Розрахунок від sec_x та sec_y, а не від max_shift!
                grid_x = sec_x + shift_x
                grid_y = sec_y + shift_y

                # Копіюємо префаб
                prefab = random.choice(PREFABS)
                for y in range(P_SIZE):
                    for x in range(P_SIZE):
                        tx = grid_x + x
                        ty = grid_y + y
                        if 0 < tx < GRID_WIDTH - 1 and 0 < ty < GRID_HEIGHT - 1:
                            game_matrix[ty][tx] = prefab[y][x]

                # Запам'ятовуємо центр кімнати для прокладання коридорів
                rooms.append(pygame.Rect(grid_x, grid_y, P_SIZE, P_SIZE))
                room_centers.append((grid_x + P_SIZE // 2, grid_y + P_SIZE // 2))

        # --- КРОК 2: Прокладання гарантовано ШИРОКИХ коридорів між кімнатами ---
        corridor_thickness = 3

        for i in range(len(room_centers) - 1):
            cx1, cy1 = room_centers[i]
            cx2, cy2 = room_centers[i + 1]

            if random.choice([True, False]):
                MapGenerator._draw_h_corridor(game_matrix, cx1, cx2, cy1, corridor_thickness)
                MapGenerator._draw_v_corridor(game_matrix, cy1, cy2, cx2, corridor_thickness)
            else:
                MapGenerator._draw_v_corridor(game_matrix, cy1, cy2, cx1, corridor_thickness)
                MapGenerator._draw_h_corridor(game_matrix, cx1, cx2, cy2, corridor_thickness)

        # --- КРОК 2.5: Пост-обробка для видалення випадкових 1-клітинних звужень ---
        game_matrix = MapGenerator._widen_passages(game_matrix)

        # --- КРОК 3: Безпечна зона для гравця ---
        player_grid_x = max(2, min(int(player_start_pos.x // TILE_SIZE), GRID_WIDTH - 3))
        player_grid_y = max(2, min(int(player_start_pos.y // TILE_SIZE), GRID_HEIGHT - 3))

        for ry in range(player_grid_y - 1, player_grid_y + 2):
            for rx in range(player_grid_x - 1, player_grid_x + 2):
                game_matrix[ry][rx] = 1

        # --- КРОК 4: Flood Fill валідація ---
        accessible = MapGenerator._flood_fill(game_matrix, player_grid_x, player_grid_y)

        for y in range(GRID_HEIGHT):
            for x in range(GRID_WIDTH):
                if game_matrix[y][x] == 1 and (x, y) not in accessible:
                    game_matrix[y][x] = 0

        # --- КРОК 5: Розстановка кущів у коридорах та кімнатах ---
        hiding_spots_data = []
        num_bush_chains = random.randint(8, 12)

        valid_floor_tiles = [
            (x, y) for (x, y) in accessible
            if pygame.math.Vector2(x * TILE_SIZE + TILE_SIZE // 2, y * TILE_SIZE + TILE_SIZE // 2).distance_to(
                player_start_pos) > 100
        ]

        for _ in range(num_bush_chains):
            if not valid_floor_tiles:
                break

            start_tile = random.choice(valid_floor_tiles)
            chain_length = random.randint(2, 4)
            curr_tile = start_tile

            for _ in range(chain_length):
                tx, ty = curr_tile
                pixel_x = tx * TILE_SIZE
                pixel_y = ty * TILE_SIZE

                if (pixel_x, pixel_y) not in hiding_spots_data:
                    hiding_spots_data.append((pixel_x, pixel_y))

                neighbors = []
                for dx, dy in [(-1, 0), (1, 0), (0, -1), (0, 1)]:
                    nx, ny = tx + dx, ty + dy
                    if (nx, ny) in valid_floor_tiles:
                        neighbors.append((nx, ny))

                if neighbors:
                    curr_tile = random.choice(neighbors)
                else:
                    break

        return game_matrix, hiding_spots_data

    @staticmethod
    def _widen_passages(matrix):
        """ Забезпечує, що проходи будуть комфортними для круглого гравця. """
        new_matrix = [row[:] for row in matrix]
        for y in range(1, GRID_HEIGHT - 1):
            for x in range(1, GRID_WIDTH - 1):
                if matrix[y][x] == 1:
                    if matrix[y][x - 1] == 0 and matrix[y][x + 1] == 0:
                        if x + 2 < GRID_WIDTH - 1:
                            new_matrix[y][x + 1] = 1
                    if matrix[y - 1][x] == 0 and matrix[y + 1][x] == 0:
                        if y + 2 < GRID_HEIGHT - 1:
                            new_matrix[y + 1][x] = 1
        return new_matrix

    @staticmethod
    def _draw_h_corridor(matrix, x1, x2, y, thickness):
        step = 1 if x2 > x1 else -1
        offset_start = -(thickness // 2)
        for cx in range(x1, x2 + step, step):
            for offset in range(thickness):
                cy = y + offset_start + offset
                if 0 < cx < GRID_WIDTH - 1 and 0 < cy < GRID_HEIGHT - 1:
                    matrix[cy][cx] = 1

    @staticmethod
    def _draw_v_corridor(matrix, y1, y2, x, thickness):
        step = 1 if y2 > y1 else -1
        offset_start = -(thickness // 2)
        for cy in range(y1, y2 + step, step):
            for offset in range(thickness):
                cx = x + offset_start + offset
                if 0 < cx < GRID_WIDTH - 1 and 0 < cy < GRID_HEIGHT - 1:
                    matrix[cy][cx] = 1

    @staticmethod
    def _flood_fill(matrix, start_x, start_y):
        visited = set()
        queue = [(start_x, start_y)]
        visited.add((start_x, start_y))

        while queue:
            cx, cy = queue.pop(0)
            for dx, dy in [(-1, 0), (1, 0), (0, -1), (0, 1)]:
                nx, ny = cx + dx, cy + dy
                if 0 <= nx < len(matrix[0]) and 0 <= ny < len(matrix):
                    if matrix[ny][nx] == 1 and (nx, ny) not in visited:
                        visited.add((nx, ny))
                        queue.append((nx, ny))
        return visited

    @staticmethod
    def get_enemy_spawn_positions(game_matrix, hiding_spots_data, player_pos, count=3):
        positions = []
        enemy_attempts = 0
        floor_positions = []

        for y in range(len(game_matrix)):
            for x in range(len(game_matrix[0])):
                if game_matrix[y][x] == 1:
                    px = x * TILE_SIZE + TILE_SIZE // 2
                    py = y * TILE_SIZE + TILE_SIZE // 2
                    floor_positions.append((px, py))

        if not floor_positions:
            return positions

        while len(positions) < count and enemy_attempts < 600:
            enemy_attempts += 1
            pixel_x, pixel_y = random.choice(floor_positions)

            is_on_bush = any(
                (pixel_x - TILE_SIZE // 2 == bx and pixel_y - TILE_SIZE // 2 == by)
                for bx, by in hiding_spots_data
            )

            if player_pos.distance_to((pixel_x, pixel_y)) > 180 and not is_on_bush:
                if (pixel_x, pixel_y) not in positions:
                    positions.append((pixel_x, pixel_y))

        return positions