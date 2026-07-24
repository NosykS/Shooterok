# src/core/mission_manager.py
import logging

import pygame

from src.settings import MISSION_CONFIGS
from src.objects.mission_elements import ExitZone, DataDrive

logger = logging.getLogger(__name__)


class MissionManager:
    def __init__(self, game) -> None:
        self.game = game
        self.current_mission_num = 1
        self.data_collected = False
        self.cfg = MISSION_CONFIGS[1]

        # Whether the final escape zone is active (needed for elimination missions)
        self.escape_activated = False

        self.exit_zones = pygame.sprite.Group()
        self.data_drives = pygame.sprite.Group()

    def load_mission(self, mission_num: int) -> None:
        """Loads a specific mission by number."""
        if mission_num > len(MISSION_CONFIGS):
            self.game.game_state = "VICTORY_ALL"
            self.current_mission_num = 1
            self.data_collected = False
            self.game.levels.reset_game_world(new_map=True, new_level=False)
            return

        self.current_mission_num = mission_num
        self.data_collected = False
        self.escape_activated = False
        self.cfg = MISSION_CONFIGS[mission_num]

        # Load the matching TMX map and build the world
        self.game.levels.reset_game_world(new_map=True, new_level=True)
        self.spawn_mission_objectives()
        self.game.game_state = "PLAYING"

    def spawn_mission_objectives(self) -> None:
        """Spawns quest objects based on spawn points from the TMX map."""
        self.exit_zones.empty()
        self.data_drives.empty()

        quest_points = getattr(self.game, "quest_spawn_points", [])
        objectives = self.cfg["objectives"]

        # 1. Escape-only scenario (Mission 1)
        if "escape" in objectives and "kill_all" not in objectives and "collect_data" not in objectives:
            self._spawn_exit_zones(quest_points)

        # 2. Data collection scenario (Mission 3)
        if "collect_data" in objectives:
            for pt in quest_points:
                if pt["name"] in ["documents", "data"]:
                    drive = DataDrive(pt["x"], pt["y"])
                    self.data_drives.add(drive)
                    self.game.all_sprites.add(drive)
                    logger.info("Data drive placed at (%s, %s)", pt["x"], pt["y"])

            # Also create the exit zone immediately, though it stays locked without the data
            self._spawn_exit_zones(quest_points)

    def _spawn_exit_zones(self, quest_points: list[dict]) -> None:
        """Creates ExitZone sprites for every escape/exit spawn point."""
        for pt in quest_points:
            if pt["name"] in ["escape", "exit"]:
                exit_node = ExitZone(pt["x"], pt["y"])
                self.exit_zones.add(exit_node)
                self.game.all_sprites.add(exit_node)
                logger.info("Escape zone created at (%s, %s)", pt["x"], pt["y"])

    def check_mission_conditions(self, frame_counter: int) -> None:
        """Runs all mission completion/failure checks for the current frame."""
        if self._check_alert_failure(frame_counter):
            return
        self._check_data_collection(frame_counter)
        self._check_escape_activation()
        self._check_escape_arrival(frame_counter)

    def _check_alert_failure(self, frame_counter: int) -> bool:
        """Fails the mission if stealth is required and an enemy is alerted."""
        if frame_counter % 10 != 0 or not self.cfg.get("fail_on_alert", False):
            return False

        for enemy in self.game.enemies:
            if enemy.is_alerted:
                self.game.game_state = "GAME_OVER"
                logger.info("Mission failed: you were spotted!")
                return True
        return False

    def _check_data_collection(self, frame_counter: int) -> None:
        """Marks mission data as collected once the player reaches the drive (Mission 3)."""
        if frame_counter % 5 != 0 or "collect_data" not in self.cfg["objectives"] or self.data_collected:
            return

        hit_drive = pygame.sprite.spritecollideany(self.game.player, self.data_drives)
        if hit_drive:
            self.data_collected = True
            hit_drive.kill()
            logger.info("Data successfully collected! Head to the extraction zone.")

    def _check_escape_activation(self) -> None:
        """Activates the escape zone once all enemies are eliminated (Mission 2)."""
        if "kill_all" not in self.cfg["objectives"] or len(self.game.enemies) != 0 or self.escape_activated:
            return

        self.escape_activated = True
        quest_points = getattr(self.game, "quest_spawn_points", [])
        for pt in quest_points:
            if pt["name"] in ["escape", "exit"]:
                exit_node = ExitZone(pt["x"], pt["y"])
                self.exit_zones.add(exit_node)
                self.game.all_sprites.add(exit_node)
                logger.info("All enemies eliminated! Extraction point is now ACTIVE.")

    def _check_escape_arrival(self, frame_counter: int) -> None:
        """Completes the mission once the player reaches an active exit zone."""
        if frame_counter % 5 != 0:
            return
        if not pygame.sprite.spritecollideany(self.game.player, self.exit_zones):
            return

        can_escape = True

        # Can't leave without the documents (Mission 3)
        if "collect_data" in self.cfg["objectives"] and not self.data_collected:
            can_escape = False

        # Can't escape while enemies are still alive (Mission 2)
        if "kill_all" in self.cfg["objectives"] and not self.escape_activated:
            can_escape = False

        if can_escape:
            self.game.game_state = "VICTORY"
            logger.info("Mission %s completed successfully!", self.current_mission_num)
