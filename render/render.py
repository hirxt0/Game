import pygame
 
from core.map import GameMap
from core.territory import Territory
 
PLAYER_COLORS = [
    (70, 130, 200),
    (200, 70, 70),
    (80, 180, 80),
    (200, 160, 40),
]

 
class Renderer:
    def __init__(self, screen: pygame.Surface):
        self.screen = screen
        self.font = pygame.font.SysFont("monospace", 14, bold=True)
        self.font_small = pygame.font.SysFont("monospace", 11, bold=True)
 
    def draw_map(self, game_map: GameMap, selected_id: int | None = None,
                 attackable_ids: set[int] | None = None) -> None:
        self.screen.fill((20, 20, 20))
        attackable_ids = attackable_ids or set()
 
        for t in game_map.territories.values():
            self._draw_territory(t, selected_id, attackable_ids)
 
        for t in game_map.territories.values():
            self._draw_troops(t)
 
    def _draw_territory(self, t: Territory, selected_id: int | None,
                        attackable_ids: set[int]) -> None:
        if len(t.vertices) < 3:
            return
 
        pts = [(int(x), int(y)) for x, y in t.vertices]
 
        if t.id == selected_id:
            fill = (255, 255, 80)
        elif t.id in attackable_ids:
            fill = (255, 200, 50)
        elif t.owner is not None and t.owner < len(PLAYER_COLORS):
            fill = PLAYER_COLORS[t.owner]
        else:
            fill = (150, 150, 140)
 
        pygame.draw.polygon(self.screen, fill, pts)
        pygame.draw.polygon(self.screen, (30, 30, 0), pts, 2)
 
    def _draw_troops(self, t: Territory) -> None:
        cx, cy = int(t.center[0]), int(t.center[1])
        text = self.font.render(str(t.troops), True, (255, 255, 255))
        rect = text.get_rect(center=(cx, cy))
        bg = rect.inflate(6, 4)
        pygame.draw.rect(self.screen, (0, 0, 0, 160), bg, border_radius=3)
        self.screen.blit(text, rect)
 
    def draw_territory_bar(self, game_map: "GameMap", num_players: int) -> None:
        sw = self.screen.get_width()
        sh = self.screen.get_height()
 
        total = len(game_map.territories)
        if total == 0:
            return
 
        bar_rect = pygame.Rect(0, sh - 28, sw, 28)
        pygame.draw.rect(self.screen, (15, 15, 15), bar_rect)
        pygame.draw.line(self.screen, (60, 60, 60), (0, sh - 28), (sw, sh - 28), 1)
 
        counts = {}
        neutral = 0
        for t in game_map.territories.values():
            if t.owner is None:
                neutral += 1
            else:
                counts[t.owner] = counts.get(t.owner, 0) + 1
 
        bar_w = sw - 12
        x = 6
        y = sh - 32
        seg_h = 20
 
        for pid in range(num_players):
            cnt = counts.get(pid, 0)
            if cnt == 0:
                continue
            seg_w = int(bar_w * cnt / total)
            color = PLAYER_COLORS[pid % len(PLAYER_COLORS)]
 
            seg_rect = pygame.Rect(x, y, seg_w, seg_h)
            pygame.draw.rect(self.screen, color, seg_rect, border_radius=3)
 
            x += seg_w + 1
 
 