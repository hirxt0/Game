import heapq
from typing import Optional

from core.map import GameMap
from core.territory import Territory


class Enemy_Player:
    """
    обычный бот с приоритетной очередью атак+
    сила атаки = (агрессия * кол-во вражеских войск у границы) - 0.5 * риск соседей
    """

    def __init__(self, player_id: int, aggression: float = 1.0):
        self.player_id = player_id
        self.aggression = aggression

    def take_turn(self, game_map: GameMap) -> tuple[int, int, int] | None:
        candidates = self._build_attack_queue(game_map)

        while candidates:
            score, from_id, to_id = heapq.heappop(candidates)
            src = game_map.territories.get(from_id)
            tgt = game_map.territories.get(to_id)

            if not src or not tgt:
                continue
            if src.owner != self.player_id or src.troops < 2:
                continue
            if tgt.owner == self.player_id:
                continue

            return (from_id, to_id, src.troops - 1)

        return None

    def _build_attack_queue(self, game_map: GameMap) -> list:
        heap = []
        for src in game_map.get_near_ter(self.player_id):
            if src.troops < 2:
                continue
            for nb_id in src.neighbors:
                tgt = game_map.territories.get(nb_id)
                if not tgt or tgt.owner == self.player_id:
                    continue
                score = self._evaluate(src, tgt, game_map)
                heapq.heappush(heap, (-score, src.id, tgt.id))
        return heap

    def _evaluate(self, src: Territory, tgt: Territory, game_map: GameMap) -> float:
        power = (src.troops - 1) - tgt.troops
        risk = sum(
            game_map.territories[nb].troops
            for nb in tgt.neighbors
            if nb in game_map.territories
            and game_map.territories[nb].owner not in (None, self.player_id, tgt.owner)
        )
        return self.aggression * power - 0.5 * risk


class DefensivePlayer:
    """
    бот который защищается
    пытается укрепить незащищенные территории
    """
           

    def __init__(self, player_id: int):
        self.player_id = player_id

    def take_turn(self, game_map: GameMap) -> tuple[int, int, int] | None:
        attack = self._find_safe_attack(game_map)
        if attack:
            return attack

        return self._reinforce(game_map)

    def _find_safe_attack(self, game_map: GameMap) -> tuple[int, int, int] | None:
        """атака если превосходим врага в 1.1 раза"""
        best = None
        best_ratio = 1.1

        for src in game_map.get_near_ter(self.player_id):
            troops_available = src.troops - 2
            if troops_available < 1:
                continue

            for nb_id in src.neighbors:
                tgt = game_map.territories.get(nb_id)
                if not tgt or tgt.owner == self.player_id:
                    continue
                if tgt.troops == 0:
                    continue

                ratio = troops_available / tgt.troops
                if ratio > best_ratio:
                    best_ratio = ratio
                    best = (src.id, tgt.id, troops_available)

        return best

    def _reinforce(self, game_map: GameMap) -> tuple[int, int, int] | None:
        """
        перекидываем войска с безопасной внутренней территории
        на самую уязвимую пограничную
        """
        border = game_map.get_near_ter(self.player_id)
        if not border:
            return None

        most_threatened = max(
            border,
            key=lambda t: sum(
                game_map.territories[nb].troops
                for nb in t.neighbors
                if nb in game_map.territories
                and game_map.territories[nb].owner not in (None, self.player_id)
            )
        )

        for nb_id in most_threatened.neighbors:
            nb = game_map.territories.get(nb_id)
            if not nb or nb.owner != self.player_id:
                continue
            available = nb.troops - 2
            if available >= 1:
                nb.troops -= available
                most_threatened.troops += available
                return None  

        return None


class FriendlyPLayer(Enemy_Player):
    """
    бот, который никогда не нападает на тебя
    """
  
    def __init__(self, player_id: int, aggression: float = 1.0):
        self.player_id = player_id
        self.aggression = aggression

    def take_turn(self, game_map: GameMap) -> tuple[int, int, int] | None:
        candidates = self._build_attack_queue(game_map)

        while candidates:
            _, from_id, to_id = heapq.heappop(candidates)
            src = game_map.territories.get(from_id)
            tgt = game_map.territories.get(to_id)

            if not src or not tgt:
                continue
            if src.owner != self.player_id or src.troops < 2:
                continue
            if tgt.owner == self.player_id:
                continue
            if tgt.owner == 0:
                continue

            return (from_id, to_id, src.troops - 1)

        return None
