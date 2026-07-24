# src/core/crosshair.py
import pygame


class CrosshairController:
    def __init__(self) -> None:
        # Hide the system cursor
        pygame.mouse.set_visible(False)
        self.screen_pos: tuple[int, int] = (0, 0)

    def update(self, player, camera, knife_radius: float, game_state: str) -> None:
        if game_state != "PLAYING":
            pygame.mouse.set_visible(True)
            return

        pygame.mouse.set_visible(False)
        mouse_pos = pygame.mouse.get_pos()

        if player.current_weapon == "knife":
            # Convert the screen-space mouse position to world coordinates
            world_mouse = camera.screen_to_world(mouse_pos)

            # Vector from the player to the mouse
            to_mouse = world_mouse - player.pos

            # Clamp the crosshair to the knife's attack radius
            if to_mouse.length() > knife_radius:
                to_mouse.scale_to_length(knife_radius)

            limited_world_pos = player.pos + to_mouse

            # Convert back to screen coordinates
            self.screen_pos = (
                int(limited_world_pos.x + camera.camera_rect.x),
                int(limited_world_pos.y + camera.camera_rect.y)
            )
        else:
            self.screen_pos = mouse_pos

    def draw(self, screen: pygame.Surface, player) -> None:
        """Draws the crosshair matching the currently equipped weapon."""
        x, y = self.screen_pos

        if player.current_weapon == "knife":
            # Melee crosshair: ring with a center dot
            pygame.draw.circle(screen, (255, 80, 80), (x, y), 6, 2)
            pygame.draw.circle(screen, (255, 255, 255), (x, y), 2)
        else:
            # Firearm crosshair: green cross
            color = (0, 255, 150)
            length, gap = 8, 4
            pygame.draw.line(screen, color, (x - length - gap, y), (x - gap, y), 2)
            pygame.draw.line(screen, color, (x + gap, y), (x + length + gap, y), 2)
            pygame.draw.line(screen, color, (x, y - length - gap), (x, y - gap), 2)
            pygame.draw.line(screen, color, (x, y + gap), (x, y + length + gap), 2)
