import heapq
from typing import Optional


from core.map import GameMap
from core.territory import Territory


class Enemy_Player:
    """
    жадный игрок с приоритетной очередью атак.

    оценка каждой возможной атаки
        score = (мои войска - войска врага) - 0.5 * риск соседей
    чем выше score, тем выгоднее атака
    """

    def __init__(self, player_id: int, aggression: float = 1.0):
        self.player_id = player_id
        self.aggression = aggression

    def take_turn(self, game_map: GameMap) -> Optional[tuple[int, int, int]]:
        """
        возвращает (from_id, to_id, troops) или None если ход невозможен.
        troops — сколько войск отправляем (оставляем 1 дома чтобы было кем защищать).
        """
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

            troops_to_send = src.troops - 1  # оставляем 1 охранника
            return (from_id, to_id, troops_to_send)

        return None

    def _build_attack_queue(self, game_map: GameMap) -> list:
        """
        priority queue (min-heap, поэтому храним -score).
        """
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
        """
        подсчет выгоды атаки
        """
        power = (src.troops - 1) - tgt.troops  # сила атаки

        # риск: сумма войск врагов вокруг цели (кроме нас)
        risk = sum(
            game_map.territories[nb].troops
            for nb in tgt.neighbors
            if nb in game_map.territories
            and game_map.territories[nb].owner not in (None, self.player_id, tgt.owner)
        )

        return self.aggression * power - 0.5 * risk