# src/world/map_generator.py
import random
import pygame
from src.settings import GRID_WIDTH, GRID_HEIGHT, TILE_SIZE

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
        game_matrix = [[0 for _ in range(GRID_WIDTH)] for _ in range(GRID_HEIGHT)]

        cols, rows = 3, 3
        sector_w = GRID_WIDTH // cols
        sector_h = GRID_HEIGHT // rows

        room_centers = []
        # Двовимірний масив для розумного трекінгу сусідніх кімнат
        rooms_grid = [[None for _ in range(cols)] for _ in range(rows)]

        # --- КРОК 1: Розміщення кімнат із випадковим зміщенням ---
        for r in range(rows):
            for c in range(cols):
                sec_x = c * sector_w
                sec_y = r * sector_h

                max_shift_x = sector_w - P_SIZE - 2
                max_shift_y = sector_h - P_SIZE - 2

                shift_x = random.randint(2, max_shift_x) if max_shift_x > 2 else 2
                shift_y = random.randint(2, max_shift_y) if max_shift_y > 2 else 2

                grid_x = sec_x + shift_x
                grid_y = sec_y + shift_y

                prefab = random.choice(PREFABS)
                for y in range(P_SIZE):
                    for x in range(P_SIZE):
                        tx = grid_x + x
                        ty = grid_y + y
                        if 0 < tx < GRID_WIDTH - 1 and 0 < ty < GRID_HEIGHT - 1:
                            game_matrix[ty][tx] = prefab[y][x]

                center = (grid_x + P_SIZE // 2, grid_y + P_SIZE // 2)
                rooms_grid[r][c] = center
                room_centers.append(center)

        # --- КРОК 2: Розумне прокладання коридорів (Сусіди по сітці) ---
        corridor_thickness = 3

        for r in range(rows):
            for c in range(cols):
                current_room = rooms_grid[r][c]
                # З'єднуємо з правою кімнатою
                if c + 1 < cols:
                    next_room = rooms_grid[r][c + 1]
                    MapGenerator._connect_rooms(game_matrix, current_room, next_room, corridor_thickness)
                # З'єднуємо з нижньою кімнатою
                if r + 1 < rows:
                    next_room = rooms_grid[r + 1][c]
                    MapGenerator._connect_rooms(game_matrix, current_room, next_room, corridor_thickness)

        # Очищення вузьких проходів
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

        # --- КРОК 5: Розстановка кущів (Тільки в безпечних місцях) ---
        hiding_spots_data = []
        num_bush_chains = random.randint(10, 15)

        valid_floor_tiles = [
            (x, y) for (x, y) in accessible
            if pygame.math.Vector2(x * TILE_SIZE + TILE_SIZE // 2, y * TILE_SIZE + TILE_SIZE // 2).distance_to(
                player_start_pos) > 150
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
    def _connect_rooms(matrix, room1, room2, thickness):
        cx1, cy1 = room1
        cx2, cy2 = room2
        if random.choice([True, False]):
            MapGenerator._draw_h_corridor(matrix, cx1, cx2, cy1, thickness)
            MapGenerator._draw_v_corridor(matrix, cy1, cy2, cx2, thickness)
        else:
            MapGenerator._draw_v_corridor(matrix, cy1, cy2, cx1, thickness)
            MapGenerator._draw_h_corridor(matrix, cx1, cx2, cy2, thickness)

    @staticmethod
    def _widen_passages(matrix):
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
        start, end = min(x1, x2), max(x1, x2)
        offset_start = -(thickness // 2)
        for cx in range(start, end + 1):
            for offset in range(thickness):
                cy = y + offset_start + offset
                if 0 < cx < GRID_WIDTH - 1 and 0 < cy < GRID_HEIGHT - 1:
                    matrix[cy][cx] = 1

    @staticmethod
    def _draw_v_corridor(matrix, y1, y2, x, thickness):
        start, end = min(y1, y2), max(y1, y2)
        offset_start = -(thickness // 2)
        for cy in range(start, end + 1):
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
        floor_positions = []

        # БЕЗПЕКА КОЛІЗІЙ: Шукаємо підлогу, яка повністю оточена іншою підлогою,
        # щоб великі вороги не з'являлися на половину всередині стін.
        for y in range(1, len(game_matrix) - 1):
            for x in range(1, len(game_matrix[0]) - 1):
                if game_matrix[y][x] == 1:
                    # Перевіряємо сусідів (опціонально для максимальної безпеки)
                    neighbors_ok = all(
                        game_matrix[y + dy][x + dx] == 1 for dx, dy in [(-1, 0), (1, 0), (0, -1), (0, 1)])
                    if neighbors_ok:
                        px = x * TILE_SIZE + TILE_SIZE // 2
                        py = y * TILE_SIZE + TILE_SIZE // 2
                        floor_positions.append((px, py))

        if not floor_positions:
            # Фолбек, якщо карта дуже вузька
            return positions

        random.shuffle(floor_positions)

        for pixel_x, pixel_y in floor_positions:
            if len(positions) >= count:
                break

            is_on_bush = any(
                (pixel_x - TILE_SIZE // 2 == bx and pixel_y - TILE_SIZE // 2 == by)
                for bx, by in hiding_spots_data
            )

            if player_pos.distance_to((pixel_x, pixel_y)) > 200 and not is_on_bush:
                if (pixel_x, pixel_y) not in positions:
                    positions.append((pixel_x, pixel_y))

        return positions