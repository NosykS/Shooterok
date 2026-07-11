# src/core/collision_manager.py
import pygame
from src.settings import ENEMY_LOSE_INTEREST_TIME

class CollisionManager:
    def __init__(self, game):
        self.game = game

    def handle_all_collisions(self):
        """Головний менеджер фізичних та логічних колізій на сцені"""
        self._handle_enemy_melee()
        self._handle_bullets()

    def _handle_enemy_melee(self):
        """Обробка ударів впритул з боку ворогів"""
        for enemy in self.game.enemies:
            if hasattr(enemy, "melee_cooldown") and enemy.melee_cooldown > 0:
                enemy.melee_cooldown -= 1

            if enemy.is_alerted and not self.game.player.is_hidden:
                dist_to_player = enemy.pos.distance_to(self.game.player.pos)
                if dist_to_player <= 35:
                    if getattr(enemy, "melee_cooldown", 0) == 0:
                        self.game.player.hp -= 10
                        enemy.melee_cooldown = 60  # 1 секунда кулдауну

                        # Відштовхування
                        push_dir = self.game.player.pos - enemy.pos
                        push_dir = push_dir.normalize() if push_dir.length() > 0 else pygame.math.Vector2(1, 0)

                        old_pos = pygame.math.Vector2(self.game.player.pos)
                        self.game.player.pos += push_dir * 45
                        self.game.player.rect.center = (int(self.game.player.pos.x), int(self.game.player.pos.y))

                        if pygame.sprite.spritecollideany(self.game.player, self.game.obstacles):
                            self.game.player.pos = old_pos
                            self.game.player.rect.center = (int(self.game.player.pos.x), int(self.game.player.pos.y))

                        if self.game.player.hp <= 0:
                            self.game.game_state = "GAME_OVER"
                        print("Ворог штовхнув вас прикладом!")

    def _handle_bullets(self):
        """Обробка траєкторій швидких куль у стіни та персонажів"""
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

    def _damage_player(self, damage):
        """Логіка поглинання шкоди бронежилетом гравця"""
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
            self.game.game_state = "GAME_OVER"

    def _damage_enemy(self, enemy, damage):
        """Логіка нанесення шкоди ворогу з урахуванням його броні"""
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

            # Нагорода за ліквідацію ворога з вогнепальної зброї
            self.game.progression.add_xp(100)
            self.game.shop.add_money(30)
            print(f"[REWARD] Ворог знищений! +100 XP | +30$")