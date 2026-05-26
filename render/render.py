import pygame
from typing import Optional


from core.map import GameMap
from core.territory import Territory

PLAYER_COLORS = [
    (70,  130, 200),   
    (200,  70,  70),   
    (80,  180,  80),   
    (200, 160,  40),   
]
NEUTRAL_COLOR   = (255, 255, 255)
BORDER_COLOR    = (140, 140, 140)
SELECTED_COLOR  = (255, 255,  80)
HIGHLIGHT_COLOR = (140, 10, 10)

FONT_SIZE_TROOPS = 14


class Renderer:
    def __init__(self, screen: pygame.Surface):
        self.screen = screen
        self.font = pygame.font.SysFont("monospace", FONT_SIZE_TROOPS, bold=True)

    def draw_map(
        self,
        game_map: "GameMap",
        selected_id: Optional[int] = None,
        attackable_ids: Optional[set[int]] = None,
    ) -> None:
        self.screen.fill((20, 20, 20))

        attackable_ids = attackable_ids or set()

        for t in game_map.territories.values():
            self._draw_territory(t, selected_id, attackable_ids)

        for t in game_map.territories.values():
            self._draw_troops(t)

    def _draw_territory(
        self,
        t: "Territory",
        selected_id: Optional[int],
        attackable_ids: set[int],
    ) -> None:
        if len(t.vertices) < 3:
            return

        pts = [(int(x), int(y)) for x, y in t.vertices]

        # Основной цвет
        if t.id == selected_id:
            fill = SELECTED_COLOR
        elif t.id in attackable_ids:
            fill = HIGHLIGHT_COLOR
        elif t.owner is not None and t.owner < len(PLAYER_COLORS):
            fill = PLAYER_COLORS[t.owner]
        else:
            fill = NEUTRAL_COLOR

        pygame.draw.polygon(self.screen, fill, pts)
        pygame.draw.polygon(self.screen, BORDER_COLOR, pts, 2)

    def _draw_troops(self, t: "Territory") -> None:
        cx, cy = int(t.center[0]), int(t.center[1])
        text = self.font.render(str(t.troops), True, (255, 255, 255))
        rect = text.get_rect(center=(cx, cy))
        bg = rect.inflate(6, 4)
        pygame.draw.rect(self.screen, (0, 0, 0, 160), bg, border_radius=3)
        self.screen.blit(text, rect)

    def draw_ui(self, turn: int, current_player: int, winner: Optional[int]) -> None:
        """HUD сверху."""
        if winner is not None:
            msg = f"Победитель: {'Вы' if winner == 0 else f'ИИ {winner}'}"
            color = (255, 220, 50)
        else:
            who = "Ваш ход" if current_player == 0 else f"Ход ИИ {current_player}"
            msg = f"Ход {turn}  |  {who}"
            color = (220, 220, 220)

        surf = self.font.render(msg, True, color)
        self.screen.blit(surf, (10, 10))