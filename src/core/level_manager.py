# src/core/level_manager.py
import pygame
import pytmx
from src.settings import TILE_SIZE, ENEMY_TYPES
from src.entities.player import Player
from src.entities.enemy import Enemy
from src.objects.obstacle import Obstacle
from src.objects.hiding_spot import HidingSpot


class LevelManager:
    def __init__(self, game):
        self.game = game
        self.tmx_data = None

    def generate_collision_matrix(self):
        """
        Генерує двовимірну матрицю проходимості для пошуку шляху (A*).
        0 - вільно, 1 - перешкода (стіна).
        """
        cols = self.game.WORLD_WIDTH // TILE_SIZE
        rows = self.game.WORLD_HEIGHT // TILE_SIZE

        # Створюємо пусту сітку (всі нулі — вільно)
        matrix = [[0 for _ in range(cols)] for _ in range(rows)]

        # Заповнюємо стінами
        for wall in self.game.obstacles:
            grid_x = int(wall.rect.x // TILE_SIZE)
            grid_y = int(wall.rect.y // TILE_SIZE)

            # Перевіряємо межі масиву, щоб уникнути IndexError
            if 0 <= grid_x < cols and 0 <= grid_y < rows:
                matrix[grid_y][grid_x] = 1

        return matrix

    def reset_game_world(self, new_map=True, new_level=False):
        """Повне або часткове скидання стану сцени та завантаження карти з TMX-файлу"""
        # 1. Очищення груп спрайтів
        for sprite in self.game.all_sprites:
            sprite.kill()

        self.game.all_sprites = pygame.sprite.Group()
        self.game.bullets = pygame.sprite.Group()
        self.game.enemies = pygame.sprite.Group()
        self.game.obstacles = pygame.sprite.Group()
        self.game.hiding_spots = pygame.sprite.Group()

        # Скидаємо матрицю перед завантаженням нового рівня
        self.game.game_matrix = None

        # 2. Визначаємо назву файлу карти на основі поточної місії
        mission_num = self.game.missions.current_mission_num
        map_path = f"assets/maps/level{mission_num}.tmx"

        try:
            # Завантажуємо TMX карту за допомогою pytmx
            self.tmx_data = pytmx.load_pygame(map_path, pixelalpha=True)
            print(f"[LEVEL] Успішно завантажено карту: {map_path}")

            # Динамічно оновлюємо межі світу на основі завантаженої карти
            self.game.WORLD_WIDTH = self.tmx_data.width * self.tmx_data.tilewidth
            self.game.WORLD_HEIGHT = self.tmx_data.height * self.tmx_data.tileheight

            # Переналаштовуємо камеру під нові розміри карти
            if hasattr(self.game, 'camera'):
                self.game.camera.map_width = self.game.WORLD_WIDTH
                self.game.camera.map_height = self.game.WORLD_HEIGHT

        except Exception as e:
            print(f"[LEVEL_ERROR] Не вдалося завантажити карту {map_path}: {e}")
            self.tmx_data = None

        # Створюємо тимчасовий список для точок спавну квестових об'єктів
        self.game.quest_spawn_points = []
        player_spawn_pos = pygame.math.Vector2(100, 100)  # Дефолтні координати

        # Тимчасовий список для збереження інформації про ворогів,
        # щоб створити їх після того, як буде згенерована матриця стін
        enemies_to_spawn = []

        if self.tmx_data:
            # 3. Будуємо стіни (Obstacles) з шару 'walls'
            for layer in self.tmx_data.visible_layers:
                if isinstance(layer, pytmx.TiledTileLayer):
                    if layer.name == "walls":
                        for x, y, gid in layer:
                            tile = self.tmx_data.get_tile_image_by_gid(gid)
                            if tile:
                                pos_x = x * self.tmx_data.tilewidth
                                pos_y = y * self.tmx_data.tileheight
                                wall = Obstacle(pos_x, pos_y, self.tmx_data.tilewidth, self.tmx_data.tileheight)
                                wall.image = tile  # Передаємо текстуру тайлу в об'єкт стіни
                                self.game.obstacles.add(wall)
                                self.game.all_sprites.add(wall)

            # --- ГЕНЕРУЄМО МАТРИЦЮ КОЛІЗІЙ ОДРАЗУ ПІСЛЯ СТВОРЕННЯ СТІН ---
            self.game.game_matrix = self.generate_collision_matrix()

            # 4. Обробляємо шар об'єктів 'spawn_points'
            spawn_layer = self.tmx_data.get_layer_by_name("spawn_points")
            if spawn_layer:
                for obj in spawn_layer:
                    obj_name = obj.name.lower() if obj.name else ""

                    if obj_name == "player":
                        player_spawn_pos = pygame.math.Vector2(obj.x, obj.y)

                    elif obj_name == "enemy":
                        enemy_type = obj.properties.get("enemy_type", "rookie")
                        if enemy_type not in ENEMY_TYPES:
                            enemy_type = "rookie"

                        # Зчитуємо кастомний маршрут із властивостей Tiled (якщо є)
                        # Формат у Tiled (рядок): "100,200;400,200;400,500"
                        custom_patrol_raw = obj.properties.get("patrol", "")
                        custom_patrol = []
                        if custom_patrol_raw:
                            try:
                                for point_str in custom_patrol_raw.split(";"):
                                    if "," in point_str:
                                        px, py = point_str.split(",")
                                        custom_patrol.append((float(px.strip()), float(py.strip())))
                            except Exception as e:
                                print(f"[TGI_ERROR] Помилка парсингу маршруту ворога: {e}")

                        # Зберігаємо параметри ворога разом із його маршрутом
                        enemies_to_spawn.append((obj.x, obj.y, enemy_type, custom_patrol))


                    elif obj_name in ["hiding_spot", "hiding_spots"]:

                        # Зчитуємо кастомну точку виходу, якщо вона задана в Tiled (формат: "x,y")
                        exit_pos_raw = obj.properties.get("exit_pos", "")
                        custom_exit_pos = None
                        if exit_pos_raw and "," in exit_pos_raw:
                            try:
                                px, py = exit_pos_raw.split(",")
                                custom_exit_pos = (float(px.strip()), float(py.strip()))
                            except Exception as e:
                                print(f"[LEVEL_ERROR] Помилка парсингу точки виходу схованки: {e}")
                        spot = HidingSpot(
                            obj.x, obj.y,
                            obj.width if obj.width else TILE_SIZE,
                            obj.height if obj.height else TILE_SIZE,
                            custom_exit_pos=custom_exit_pos
                        )

                        self.game.hiding_spots.add(spot)
                        self.game.all_sprites.add(spot)

                    elif obj_name in ["documents", "data", "escape", "exit"]:
                        self.game.quest_spawn_points.append({
                            "name": obj_name,
                            "x": obj.x,
                            "y": obj.y
                        })

        # --- ТЕПЕР СПАВНИМО ВОРОГІВ, ПЕРЕДАЮЧИ ЇМ СТВОРЕНУ МАТРИЦЮ ---
        for x, y, enemy_type, custom_patrol in enemies_to_spawn:
            enemy = Enemy(
                x, y,
                enemy_type=enemy_type,
                game_matrix=self.game.game_matrix,
                custom_patrol=custom_patrol if custom_patrol else None
            )
            enemy.melee_cooldown = 0
            self.game.enemies.add(enemy)
            self.game.all_sprites.add(enemy)

        # 5. Ініціалізуємо гравця на знайдених координатах спавну
        self.game.player = Player(self.game, player_spawn_pos.x, player_spawn_pos.y)
        self.game.all_sprites.add(self.game.player)

        # 6. Налаштовуємо покращення
        self.game.apply_player_upgrades()
        self.game.player.refill_all_ammo()

        self.game.gunshot_visual_timer = 0
        self.game.knife_visual_timer = 0

    def draw_floor(self, surface, camera):
        """Візуальне малювання шару підлоги під усіма спрайтами з урахуванням зміщення камери"""
        if not self.tmx_data:
            surface.fill((30, 30, 30))
            return

        offset_x = camera.camera_rect.x
        offset_y = camera.camera_rect.y

        for layer in self.tmx_data.visible_layers:
            if isinstance(layer, pytmx.TiledTileLayer) and layer.name in ["floor", "decorations"]:
                for x, y, gid in layer:
                    tile = self.tmx_data.get_tile_image_by_gid(gid)
                    if tile:
                        pos_x = x * self.tmx_data.tilewidth + offset_x
                        pos_y = y * self.tmx_data.tileheight + offset_y

                        if -self.tmx_data.tilewidth < pos_x < surface.get_width() and \
                                -self.tmx_data.tileheight < pos_y < surface.get_height():
                            surface.blit(tile, (pos_x, pos_y))