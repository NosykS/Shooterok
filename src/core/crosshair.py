# src/core/crosshair.py
import pygame


class CrosshairController:
    def __init__(self) -> None:
        # Hide the system cursor
        pygame.mouse.set_visible(False)
        self.screen_pos: tuple[int, int] = (0, 0)
        # Only set while a melee weapon is equipped: the actual cursor position
        # clamped to the weapon's attack radius, shown as a separate marker
        # alongside the real-cursor crosshair (not instead of it) so the player
        # can compare "where I'm aiming" against "how far this weapon reaches".
        self.melee_range_screen_pos: tuple[int, int] | None = None

    def update(self, player, camera, knife_radius: float, game_state: str) -> None:
        if game_state != "PLAYING":
            pygame.mouse.set_visible(True)
            return

        pygame.mouse.set_visible(False)
        mouse_pos = pygame.mouse.get_pos()
        self.screen_pos = mouse_pos

        if player.weapon_stats.get("is_melee", False):
            # Convert the screen-space mouse position to world coordinates
            world_mouse = camera.screen_to_world(mouse_pos)

            # Vector from the player to the mouse
            to_mouse = world_mouse - player.pos

            # Clamp to the weapon's attack radius
            if to_mouse.length() > knife_radius:
                to_mouse.scale_to_length(knife_radius)

            limited_world_pos = player.pos + to_mouse

            # Convert back to screen coordinates
            self.melee_range_screen_pos = (
                int(limited_world_pos.x + camera.camera_rect.x),
                int(limited_world_pos.y + camera.camera_rect.y)
            )
        else:
            self.melee_range_screen_pos = None

    def draw(self, screen: pygame.Surface, player) -> None:
        """Draws the real-cursor crosshair, plus a melee attack-range marker if relevant."""
        if self.melee_range_screen_pos is not None:
            rx, ry = self.melee_range_screen_pos
            pygame.draw.circle(screen, (255, 60, 60), (rx, ry), 6, 2)
            pygame.draw.circle(screen, (255, 255, 255), (rx, ry), 2)

        # Crosshair at the actual mouse position — always shown, regardless of weapon
        x, y = self.screen_pos
        color = (0, 255, 150)
        length, gap = 8, 4
        pygame.draw.line(screen, color, (x - length - gap, y), (x - gap, y), 2)
        pygame.draw.line(screen, color, (x + gap, y), (x + length + gap, y), 2)
        pygame.draw.line(screen, color, (x, y - length - gap), (x, y - gap), 2)
        pygame.draw.line(screen, color, (x, y + gap), (x, y + length + gap), 2)
