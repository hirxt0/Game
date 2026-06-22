import pygame
import time

from core.map import GameMap
from core.territory import Territory
from enemy.enemy import Enemy_Player, DefensivePlayer, FriendlyPLayer 
from render.render import Renderer
from animation import Soldier, Explosion


PLAYER_COLORS = [(70,  130, 200),
                 (200,  70,  70),
                 (80,  180,  80),
                 (200, 160,  40)]


class GameLoop:
    def __init__(self):
        pygame.init()
        self.screen = pygame.display.set_mode((1000, 600 ))
        pygame.display.set_caption("Game")
        self.clock = pygame.time.Clock()

        num_players = 4
        self.game_map = GameMap(1000, 560, 30, num_players)

        self.bots = [
         FriendlyPLayer(player_id=1, aggression=1.0),    
            DefensivePlayer(player_id=2),                
            Enemy_Player(player_id=3, aggression=1.2),   
        ]

        self.renderer = Renderer(self.screen)
        Explosion.load_frames("assets/explosion")
        pygame.mixer.init()
        self.attack_sound = pygame.mixer.Sound("assets/babax.mp3")
        self.attack_sound.set_volume(0.6)
        self.current_player = 0
        self.turn = 1
        self.winner = None
        self.selected_id = None
        self.attackable = set()
        self.soldiers = []
        self.explosions = []
        self.pending_attack = None
        self._last_bot_time = 0.0
        self._troops_distributed_this_round = False
        self._last_player_turn_time = time.monotonic()


    def run(self) -> None:
        while True:
            dt = self.clock.tick(60) / 1000.0

            self._handle_events()
            self._update_animations(dt)

            if self.winner is None and not self._animation_running():
                if self.current_player == 0:
                    pass
                else:
                    self._bot_turn()

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

        self.renderer.draw_territory_bar(game_map=self.game_map, num_players=1 + len(self.bots))
        pygame.display.flip()



    def _handle_events(self) -> None:
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                pygame.quit()
                raise SystemExit

            if event.type == pygame.KEYDOWN and event.key == pygame.K_r:
                self.__init__()
                return

            if (event.type == pygame.MOUSEBUTTONDOWN
                and event.button == 1
                and self.current_player == 0
                and self.winner is None
                and not self._animation_running()):
                self._handle_click(event.pos)

    def _handle_click(self, pos: tuple[int, int]) -> None:
        clicked_id = self._territory_at(pos)

        if clicked_id is None:
            self._deselect()
            return

        clicked = self.game_map.territories[clicked_id]

        if self.selected_id is None:
            if clicked.owner == 0 and clicked.troops >= 2:
                self.selected_id = clicked_id
                self.attackable = {nb for nb in clicked.neighbors
                    if self.game_map.territories.get(nb)
                    and self.game_map.territories[nb].owner != 0}
            return

        if clicked_id in self.attackable:
            self._launch_attack(self.selected_id, clicked_id, owner_id=0)
            self._deselect()
            self._last_player_turn_time = time.monotonic()
            return


        if (clicked.owner == 0
            and clicked_id != self.selected_id
            and clicked_id in self.game_map.territories[self.selected_id].neighbors):
            self._move_troops(self.selected_id, clicked_id)
            self._deselect()
            return
        
        elif clicked.owner == 0 and clicked.troops >= 2:
            self.selected_id = clicked_id
            self.attackable = {
                nb for nb in clicked.neighbors
                if self.game_map.territories.get(nb)
                and self.game_map.territories[nb].owner != 0}
        else:
            self._deselect()

    def _territory_at(self, pos: tuple[int, int]) -> int | None:
        px, py = pos
        best_id, best_dist = None, 10**10
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
                delay=i * 0.08,
                color=color))

        self.pending_attack = (from_id, to_id, troops, owner_id)


    def _resolve_attack(self, from_id: int, to_id: int, troops: int) -> None:
        if self.attack_sound:
            self.attack_sound.play()
        src = self.game_map.territories[from_id]
        tgt = self.game_map.territories[to_id]

        success = tgt.resolve_attack(troops)
        if success:
            tgt.owner = src.owner
        src.troops = 1 if success else max(src.troops - troops, 1)

        self.winner = self.game_map.check_win()


    def _bot_turn(self) -> None:
        now = time.monotonic()
        if now - self._last_player_turn_time < 0.5:
            return
        if now - self._last_bot_time < 1:
            return

        bot = next((a for a in self.bots if a.player_id == self.current_player), None)
        if bot:
            move = bot.take_turn(self.game_map)
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

        num_players = 1 + len(self.bots)
        self.current_player = (self.current_player + 1) % num_players

        for _ in range(num_players):
            if self.game_map.get_player_ter(self.current_player):
                break
            self.current_player = (self.current_player + 1) % num_players

        self._regenerate_troops()

        if self.current_player == 0:
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

        num_players = 1 + len(self.bots)
        for pid in range(num_players):
            territories = self.game_map.get_player_ter(pid)
            if not territories:
                continue
            bonus = max(3, len(territories) // 3)
            border = self.game_map.get_near_ter(pid)
            target = border[0] if border else territories[0]
            target.troops += bonus