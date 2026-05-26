import pygame
import time
from typing import Optional

from core.map import GameMap
from core.territory import Territory
from enemy.enemy import Enemy_Player
from render.render import Renderer
from animation import Soldier, Explosion


SCREEN_W, SCREEN_H = 1200, 800
NUM_TERRITORIES = 40
NUM_AI = 3
AI_TURN_DELAY = 1.0
FPS = 60
PLAYER_ID = 0
SOLDIER_DELAY = 0.08   

PLAYER_COLORS = [
    (70,  130, 200),
    (200,  70,  70),
    (80,  180,  80),
    (200, 160,  40),
]

EXPLOSION_FOLDER = "assets/explosion"


class GameLoop:
    def __init__(self):
        pygame.init()
        self.screen = pygame.display.set_mode((SCREEN_W, SCREEN_H))
        pygame.display.set_caption("Territory Wars")
        self.clock = pygame.time.Clock()

        num_players = 1 + NUM_AI
        self.game_map = GameMap(SCREEN_W, SCREEN_H - 40, NUM_TERRITORIES, num_players)

        self.ai_players = [
            Enemy_Player(player_id=i + 1, aggression=0.8 + i * 0.3)
            for i in range(NUM_AI)
        ]

        self.renderer = Renderer(self.screen)

        try:
            Explosion.load_frames(EXPLOSION_FOLDER)
        except Exception as e:
            print(f"[warn] не удалось загрузить спрайтшит: {e}")

        self.current_player: int = PLAYER_ID
        self.turn: int = 1
        self.winner: Optional[int] = None

        self.selected_id: Optional[int] = None
        self.attackable: set[int] = set()

        self.soldiers: list[Soldier] = []
        self.explosions: list[Explosion] = []

        self.pending_attack: Optional[tuple[int, int, int, int]] = None

        self._last_ai_time: float = 0.0
        self._troops_distributed_this_round: bool = False
        self._last_player_turn_time: float = time.monotonic()


    def run(self) -> None:
        while True:
            dt = self.clock.tick(FPS) / 1000.0

            self._handle_events()
            self._update_animations(dt)

            if self.winner is None and not self._animation_running():
                if self.current_player == PLAYER_ID:
                    pass
                else:
                    self._ai_turn()

            self._render()

    def _animation_running(self) -> bool:
        return bool(self.soldiers) or bool(self.pending_attack)


    def _update_animations(self, dt: float) -> None:

        for s in self.soldiers:
            s.update(dt)

        arrived_positions = [s.end for s in self.soldiers if s.arrived]

        self.soldiers = [s for s in self.soldiers if not s.arrived]

        if arrived_positions and not self.soldiers:
            self.explosions.append(Explosion(arrived_positions[0]))

        for ex in self.explosions:
            ex.update(dt)

        self.explosions = [ex for ex in self.explosions if not ex.done]

        if not self.soldiers and self.pending_attack is not None:
            from_id, to_id, troops, _ = self.pending_attack
            self.pending_attack = None

            self._resolve_attack(from_id, to_id, troops)
            self._next_player()



    def _render(self) -> None:
        self.renderer.draw_map(
            self.game_map,
            selected_id=self.selected_id,
            attackable_ids=self.attackable,
        )

        for s in self.soldiers:
            s.draw(self.screen)

        for ex in self.explosions:
            ex.draw(self.screen)

        self.renderer.draw_ui(self.turn, self.current_player, self.winner)
        pygame.display.flip()



    def _handle_events(self) -> None:
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                pygame.quit()
                raise SystemExit

            if event.type == pygame.KEYDOWN and event.key == pygame.K_r:
                self.__init__()
                return

            if (
                event.type == pygame.MOUSEBUTTONDOWN
                and event.button == 1
                and self.current_player == PLAYER_ID
                and self.winner is None
                and not self._animation_running()
            ):
                self._handle_click(event.pos)

    def _handle_click(self, pos: tuple[int, int]) -> None:
        clicked_id = self._territory_at(pos)

        if clicked_id is None:
            self._deselect()
            return

        clicked = self.game_map.territories[clicked_id]

        if self.selected_id is None:
            if clicked.owner == PLAYER_ID and clicked.troops >= 2:
                self.selected_id = clicked_id
                self.attackable = {
                    nb for nb in clicked.neighbors
                    if self.game_map.territories.get(nb)
                    and self.game_map.territories[nb].owner != PLAYER_ID
                }
            return

        if clicked_id in self.attackable:
            self._launch_attack(self.selected_id, clicked_id, owner_id=PLAYER_ID)
            self._deselect()
            self._last_player_turn_time = time.monotonic()
            return


        if (
            clicked.owner == PLAYER_ID
            and clicked_id != self.selected_id
            and clicked_id in self.game_map.territories[self.selected_id].neighbors
        ):
            self._move_troops(self.selected_id, clicked_id)
            self._deselect()
            return
        
        elif clicked.owner == PLAYER_ID and clicked.troops >= 2:
            self.selected_id = clicked_id
            self.attackable = {
                nb for nb in clicked.neighbors
                if self.game_map.territories.get(nb)
                and self.game_map.territories[nb].owner != PLAYER_ID
            }
        else:
            self._deselect()

    def _territory_at(self, pos: tuple[int, int]) -> Optional[int]:
        px, py = pos
        best_id, best_dist = None, float("inf")
        for t in self.game_map.territories.values():
            dx = px - t.center[0]
            dy = py - t.center[1]
            d = dx * dx + dy * dy
            if d < best_dist:
                best_dist = d
                best_id = t.id
        return best_id

    def _deselect(self) -> None:
        self.selected_id = None
        self.attackable = set()

    def _move_troops(self, from_id: int, to_id: int) -> None:
        src = self.game_map.territories[from_id]
        tgt = self.game_map.territories[to_id]

        if src.troops <= 1:
            return

        moving = src.troops // 2

        src.troops -= moving
        tgt.troops += moving

    def _launch_attack(self, from_id: int, to_id: int, owner_id: int) -> None:
        src = self.game_map.territories[from_id]
        tgt = self.game_map.territories[to_id]
        troops = src.troops - 1

        color = PLAYER_COLORS[owner_id % len(PLAYER_COLORS)]

        for i in range(troops):
            self.soldiers.append(Soldier(
                start=src.center,
                end=tgt.center,
                delay=i * SOLDIER_DELAY,
                color=color,
            ))

        self.pending_attack = (from_id, to_id, troops, owner_id)


    def _resolve_attack(self, from_id: int, to_id: int, troops: int) -> None:
        src = self.game_map.territories[from_id]
        tgt = self.game_map.territories[to_id]

        success = tgt.resolve_attack(troops)
        if success:
            tgt.owner = src.owner
        src.troops = 1 if success else max(src.troops - troops, 1)

        self.winner = self.game_map.check_win()


    def _ai_turn(self) -> None:
        now = time.monotonic()

        if now - self._last_player_turn_time < 0.5:
            return
        if now - self._last_ai_time < AI_TURN_DELAY:
            return

        ai = next(
            (a for a in self.ai_players if a.player_id == self.current_player),
            None,
        )
        if ai:
            move = ai.take_turn(self.game_map)
            if move:
                from_id, to_id, _ = move
                self._launch_attack(from_id, to_id, owner_id=self.current_player)
                self._last_ai_time = now
                return 

        self._last_ai_time = now
        self._next_player()


    def _next_player(self) -> None:
        if self.winner is not None:
            return

        num_players = 1 + len(self.ai_players)
        self.current_player = (self.current_player + 1) % num_players

        for _ in range(num_players):
            if self.game_map.get_player_ter(self.current_player):
                break
            self.current_player = (self.current_player + 1) % num_players

        self._regenerate_troops()

        if self.current_player == PLAYER_ID:
            self.turn += 1
            self._troops_distributed_this_round = False
            self._distribute_troops()

    def _regenerate_troops(self) -> None:
        for ter in self.game_map.get_player_ter(self.current_player):
            ter.troops += 1

    def _distribute_troops(self) -> None:
        if self._troops_distributed_this_round:
            return
        self._troops_distributed_this_round = True

        num_players = 1 + len(self.ai_players)
        for pid in range(num_players):
            territories = self.game_map.get_player_ter(pid)
            if not territories:
                continue
            bonus = max(3, len(territories) // 3)
            border = self.game_map.get_near_ter(pid)
            target = border[0] if border else territories[0]
            target.troops += bonus