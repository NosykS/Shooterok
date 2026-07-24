# src/core/level_manager.py
import logging

import pygame
import pytmx

from src.settings import TILE_SIZE, ENEMY_TYPES
from src.entities.player import Player
from src.entities.enemy import Enemy
from src.objects.obstacle import Obstacle
from src.objects.hiding_spot import HidingSpot

logger = logging.getLogger(__name__)


class LevelManager:
    def __init__(self, game) -> None:
        self.game = game
        self.tmx_data: pytmx.TiledMap | None = None

    def generate_collision_matrix(self) -> list[list[int]]:
        """
        Generates a 2D walkability matrix for A* pathfinding.
        0 - free, 1 - obstacle (wall).
        """
        cols = self.game.WORLD_WIDTH // TILE_SIZE
        rows = self.game.WORLD_HEIGHT // TILE_SIZE

        # Empty grid (all zeros — free)
        matrix = [[0 for _ in range(cols)] for _ in range(rows)]

        # Fill in walls
        for wall in self.game.obstacles:
            grid_x = int(wall.rect.x // TILE_SIZE)
            grid_y = int(wall.rect.y // TILE_SIZE)

            # Bounds check to avoid IndexError
            if 0 <= grid_x < cols and 0 <= grid_y < rows:
                matrix[grid_y][grid_x] = 1

        return matrix

    def reset_game_world(self, new_map: bool = True, new_level: bool = False) -> None:
        """Fully or partially resets scene state and loads the map from a TMX file."""
        # 1. Clear sprite groups
        for sprite in self.game.all_sprites:
            sprite.kill()

        self.game.all_sprites = pygame.sprite.Group()
        self.game.bullets = pygame.sprite.Group()
        self.game.enemies = pygame.sprite.Group()
        self.game.obstacles = pygame.sprite.Group()
        self.game.hiding_spots = pygame.sprite.Group()

        # Reset the pathfinding matrix before loading the new level
        self.game.game_matrix = None

        # 2. Determine the map file name from the current mission
        mission_num = self.game.missions.current_mission_num
        map_path = f"assets/maps/level{mission_num}.tmx"

        self._load_tmx_map(map_path)

        # Temporary list for quest object spawn points
        self.game.quest_spawn_points = []
        player_spawn_pos = pygame.math.Vector2(100, 100)  # Default coordinates

        # Temporary list of enemy spawn data, created after the collision
        # matrix has been generated
        enemies_to_spawn = []

        if self.tmx_data:
            self._build_walls()

            # --- GENERATE THE COLLISION MATRIX RIGHT AFTER BUILDING WALLS ---
            self.game.game_matrix = self.generate_collision_matrix()

            player_spawn_pos, enemies_to_spawn = self._process_spawn_points(player_spawn_pos, enemies_to_spawn)

        self._spawn_enemies(enemies_to_spawn)

        # 5. Place the player at the spawn coordinates found above
        self.game.player = Player(self.game, player_spawn_pos.x, player_spawn_pos.y)
        self.game.all_sprites.add(self.game.player)

        # 6. Apply upgrades
        self.game.apply_player_upgrades()
        self.game.player.refill_all_ammo()

        self.game.gunshot_visual_timer = 0
        self.game.knife_visual_timer = 0

    def _load_tmx_map(self, map_path: str) -> None:
        """Loads the TMX map and updates world/camera bounds to match it."""
        try:
            self.tmx_data = pytmx.load_pygame(map_path, pixelalpha=True)
            logger.info("Map loaded successfully: %s", map_path)

            # Update world bounds dynamically based on the loaded map
            self.game.WORLD_WIDTH = self.tmx_data.width * self.tmx_data.tilewidth
            self.game.WORLD_HEIGHT = self.tmx_data.height * self.tmx_data.tileheight

            # Resize the camera to match the new map dimensions
            if hasattr(self.game, "camera"):
                self.game.camera.map_width = self.game.WORLD_WIDTH
                self.game.camera.map_height = self.game.WORLD_HEIGHT
        except Exception:
            logger.exception("Failed to load map %s", map_path)
            self.tmx_data = None

    def _build_walls(self) -> None:
        """Builds Obstacle sprites from the 'walls' layer of the loaded TMX map."""
        for layer in self.tmx_data.visible_layers:
            if isinstance(layer, pytmx.TiledTileLayer) and layer.name == "walls":
                for x, y, gid in layer:
                    tile = self.tmx_data.get_tile_image_by_gid(gid)
                    if tile:
                        pos_x = x * self.tmx_data.tilewidth
                        pos_y = y * self.tmx_data.tileheight
                        wall = Obstacle(pos_x, pos_y, self.tmx_data.tilewidth, self.tmx_data.tileheight)
                        wall.image = tile  # Apply the tile's texture to the wall sprite
                        self.game.obstacles.add(wall)
                        self.game.all_sprites.add(wall)

    def _process_spawn_points(
        self, player_spawn_pos: pygame.math.Vector2, enemies_to_spawn: list[tuple]
    ) -> tuple[pygame.math.Vector2, list[tuple]]:
        """Processes the 'spawn_points' object layer: player, enemies, hiding spots, quest points."""
        spawn_layer = self.tmx_data.get_layer_by_name("spawn_points")
        if not spawn_layer:
            return player_spawn_pos, enemies_to_spawn

        for obj in spawn_layer:
            obj_name = obj.name.lower() if obj.name else ""

            if obj_name == "player":
                player_spawn_pos = pygame.math.Vector2(obj.x, obj.y)
            elif obj_name == "enemy":
                enemies_to_spawn.append(self._parse_enemy_spawn(obj))
            elif obj_name in ["hiding_spot", "hiding_spots"]:
                self._spawn_hiding_spot(obj)
            elif obj_name in ["documents", "data", "escape", "exit"]:
                self.game.quest_spawn_points.append({"name": obj_name, "x": obj.x, "y": obj.y})

        return player_spawn_pos, enemies_to_spawn

    def _parse_enemy_spawn(self, obj) -> tuple[float, float, str, list[tuple[float, float]]]:
        """Reads an enemy's type and optional custom patrol route from its Tiled properties."""
        enemy_type = obj.properties.get("enemy_type", "rookie")
        if enemy_type not in ENEMY_TYPES:
            enemy_type = "rookie"

        # Custom patrol route format in Tiled (string): "100,200;400,200;400,500"
        custom_patrol_raw = obj.properties.get("patrol", "")
        custom_patrol = []
        if custom_patrol_raw:
            try:
                for point_str in custom_patrol_raw.split(";"):
                    if "," in point_str:
                        px, py = point_str.split(",")
                        custom_patrol.append((float(px.strip()), float(py.strip())))
            except ValueError:
                logger.warning("Failed to parse enemy patrol route: %s", custom_patrol_raw, exc_info=True)

        return obj.x, obj.y, enemy_type, custom_patrol

    def _spawn_hiding_spot(self, obj) -> None:
        """Creates a HidingSpot sprite, reading an optional custom exit point from Tiled."""
        exit_pos_raw = obj.properties.get("exit_pos", "")
        custom_exit_pos = None
        if exit_pos_raw and "," in exit_pos_raw:
            try:
                px, py = exit_pos_raw.split(",")
                custom_exit_pos = (float(px.strip()), float(py.strip()))
            except ValueError:
                logger.warning("Failed to parse hiding spot exit point: %s", exit_pos_raw, exc_info=True)

        spot = HidingSpot(
            obj.x, obj.y,
            obj.width if obj.width else TILE_SIZE,
            obj.height if obj.height else TILE_SIZE,
            custom_exit_pos=custom_exit_pos
        )
        self.game.hiding_spots.add(spot)
        self.game.all_sprites.add(spot)

    def _spawn_enemies(self, enemies_to_spawn: list[tuple]) -> None:
        """Instantiates enemies now that the pathfinding matrix is ready."""
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

    def draw_floor(self, surface: pygame.Surface, camera) -> None:
        """Draws the floor layer beneath all sprites, accounting for the camera offset."""
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
