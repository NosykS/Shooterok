# src/core/collision_manager.py
import logging

import pygame

from src.settings import ENEMY_LOSE_INTEREST_TIME

logger = logging.getLogger(__name__)


class CollisionManager:
    def __init__(self, game) -> None:
        self.game = game

    def handle_all_collisions(self) -> None:
        """Main entry point for all physical and logical collisions in the scene."""
        self._handle_enemy_melee()
        self._handle_bullets()

    def _handle_enemy_melee(self) -> None:
        """Handles close-range melee strikes from enemies."""
        for enemy in self.game.enemies:
            if hasattr(enemy, "melee_cooldown") and enemy.melee_cooldown > 0:
                enemy.melee_cooldown -= 1

            if enemy.is_alerted and not self.game.player.is_hidden:
                dist_to_player = enemy.pos.distance_to(self.game.player.pos)
                if dist_to_player <= 35:
                    if getattr(enemy, "melee_cooldown", 0) == 0:
                        self._apply_melee_hit(enemy)

    def _apply_melee_hit(self, enemy) -> None:
        """Damages and knocks back the player from a single melee strike."""
        self.game.player.hp -= 10
        enemy.melee_cooldown = 60  # 1 second cooldown

        push_dir = self.game.player.pos - enemy.pos
        push_dir = push_dir.normalize() if push_dir.length() > 0 else pygame.math.Vector2(1, 0)

        old_pos = pygame.math.Vector2(self.game.player.pos)
        self.game.player.pos += push_dir * 45
        self.game.player.rect.center = (int(self.game.player.pos.x), int(self.game.player.pos.y))

        if pygame.sprite.spritecollideany(self.game.player, self.game.obstacles):
            self.game.player.pos = old_pos
            self.game.player.rect.center = (int(self.game.player.pos.x), int(self.game.player.pos.y))

        if self.game.player.hp <= 0:
            self._trigger_game_over()
        logger.debug("Enemy hit the player with a melee strike")

    def _handle_bullets(self) -> None:
        """Handles fast-moving bullet trajectories against walls and characters."""
        for bullet in list(self.game.bullets):
            if pygame.sprite.spritecollideany(bullet, self.game.obstacles):
                bullet.kill()
                continue

            if bullet.is_enemy_bullet:
                if bullet.rect.colliderect(self.game.player.rect) and not self.game.player.is_hidden:
                    self._damage_player(bullet.damage)
                    bullet.kill()
            else:
                hit_enemies = pygame.sprite.spritecollide(bullet, self.game.enemies, False)
                for enemy in hit_enemies:
                    self._damage_enemy(enemy, bullet.damage)
                    bullet.kill()

    def _damage_player(self, damage: float) -> None:
        """Applies damage to the player, absorbed first by armor."""
        damage_to_deal = damage
        if self.game.player.armor > 0:
            absorption = int(damage_to_deal * 0.6)
            if self.game.player.armor >= absorption:
                self.game.player.armor -= absorption
                damage_to_deal -= absorption
            else:
                damage_to_deal -= self.game.player.armor
                self.game.player.armor = 0
        self.game.player.hp -= damage_to_deal
        if self.game.player.hp <= 0:
            self._trigger_game_over()

    def _trigger_game_over(self) -> None:
        """Centralized transition to the defeat state, with matching sounds."""
        if self.game.game_state == "GAME_OVER":
            return
        self.game.game_state = "GAME_OVER"
        self.game.sound.play("player_death")
        self.game.sound.play("defeat_jingle")
        self.game.sound.stop_music()

    def _damage_enemy(self, enemy, damage: float) -> None:
        """Applies damage to an enemy, absorbed first by armor."""
        damage_to_deal = damage
        if enemy.armor > 0:
            absorption = int(damage_to_deal * 0.5)
            if enemy.armor >= absorption:
                enemy.armor -= absorption
                damage_to_deal -= absorption
            else:
                damage_to_deal -= enemy.armor
                enemy.armor = 0
        enemy.hp -= damage_to_deal
        enemy.is_alerted = True
        enemy.last_known_player_pos = pygame.math.Vector2(self.game.player.pos)
        enemy.lose_interest_timer = ENEMY_LOSE_INTEREST_TIME
        if enemy.hp <= 0:
            enemy.kill()
            self.game.sound.play("enemy_death")

            # Reward for eliminating an enemy with a firearm
            self.game.progression.add_xp(100)
            self.game.shop.add_money(30)
            logger.info("Enemy eliminated! +100 XP | +30$")
