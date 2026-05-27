"""
    1) random points
    2) lloyd relaxation
    3) mirror points (искусственные)
    4) Voronoi(all_points)
    5) берём только первые n регионов
    6) clip polygon (Сазерленд)
    7) строим Territory
    8) строим граф соседей
    9) раздаём стартовые позиции
"""

import random
from collections import deque

import numpy as np
from scipy.spatial import Voronoi

from .territory import Territory


class GameMap:
    """
    основа карты игры
    генерация территории через алгоритм Вороного,
    строит граф смежности и раздает стартовые позиции
    """

    def __init__(self, widht: int, height: int, 
                 chunk_count: int, players_count: int):
        self.widht = widht
        self.height = height
        self.chunk_count = chunk_count
        self.territories: dict[int, Territory] = {}
        self._generate(chunk_count)
        self._start_possisions(players_count)


    def _generate(self, n: int) -> None:
        """
        генерирует n случайных точек
        применяет релаксацию Ллойда, чтобы точки не были близко друг к другу
        строит диаграмму Вороного через scipy
        обрезает регионы по границам через отзеркаливание
        строит граф смежности
        """

        indent = 40
        points = np.array([
            [random.uniform(indent, self.widht - indent),
            random.uniform(indent, self.height - indent)] for _ in range(n)
        ])

        points = self._lloyd_relax(points, indent)
        mirrored = self._mirror_points(points)
        all_points = np.vstack([points, mirrored])

        vor = Voronoi(all_points)

        for i in range(n):
            reg_index = vor.point_region[i]
            region = vor.regions[reg_index]

            if -1 in region or len(region) == 0:
                continue

            vertices = [tuple(vor.vertices[i]) for i in region]

            cx = sum(v[0] for v in vertices) / len(vertices)
            cy = sum(v[1] for v in vertices) / len(vertices)

            ter = Territory(id=i, center=(cx, cy), vertices=vertices, neighbors=[])
            self.territories[i] = ter
        
        self._build_neigh(vor, n)

    def _lloyd_relax(self, points: np.array, indent: int) -> np.array:
        mirrored = self._mirror_points(points)
        all_pts = np.vstack([points, mirrored])
        vor = Voronoi(all_pts)

        new_points = points.copy()
        n = len(points)
        for i in range(n):
            region_index = vor.point_region[i]
            region = vor.regions[region_index]

            if -1 in region or not region:
                continue
            verts = vor.vertices[region]
            centroid = verts.mean(axis=0)
            centroid[0] = np.clip(centroid[0], indent, self.widht - indent)
            centroid[1] = np.clip(centroid[1], indent, self.height - indent)
            new_points[i] = centroid

        return new_points
    
    def _mirror_points(self, points: np.ndarray) -> np.ndarray:
        """
        отражает все точки на 4 стороны, 
        чтобы алгоритм Вороного работал корректно
        """    
        w, h = self.widht, self.height
        return np.vstack([
            np.column_stack([-points[:, 0], points[:, 1]]),
            np.column_stack([2 * w - points[:, 0], points[:, 1]]),
            np.column_stack([points[:, 0], -points[:, 1]]),
            np.column_stack([points[:, 0], 2 * h - points[:, 1]])
        ])
    
    def _build_neigh(self, vor: Voronoi, n: int) -> None:
        """
        ищет смежные регионы. два региона смежные если они оба делят 
        ребро диаграммы   Вороного
        """
        for p1, p2 in vor.ridge_points:
            if p1 < n and p2 < n:
                if p1 in self.territories and p2 in self.territories:
                    
                    if p2 not in self.territories[p1].neighbors:
                        self.territories[p1].neighbors.append(p2)
                    if p1 not in self.territories[p2].neighbors:
                        self.territories[p2].neighbors.append(p1)

    def _start_possisions(self, players_count: int) -> None:
        """
        игроки получают удаленные друг от друга территории
        """
        index = list(self.territories.keys())
        if not index:
            return
        
        start = [random.choice(index)]
        for _ in range(players_count - 1):
            best, best_dist = None, -1
            for candidate in index:
                if candidate in start:
                    continue
                cx, cy = self.territories[candidate].center
                min_d = min(
                    (cx - self.territories[s].center[0]) ** 2 + 
                    (cy - self.territories[s].center[1]) ** 2
                    for s in start
                )

                if min_d > best_dist:
                    best_dist = min_d
                    best = candidate
            
            if best is not None:
                start.append(best)


        for player_id, Territory_id in enumerate(start):
            ter = self.territories[Territory_id]
            ter.owner = player_id
            ter.troops = 5


    

    def get_player_ter(self, player_id: int) -> list[Territory]:

        return [ter for ter in self.territories.values() if ter.owner == player_id]
    
    def get_near_ter(self, player_id: int) -> list[Territory]:
        """
        на выходе территории игрока, у которых есть противники
        """
        enemy_ter = []
        for ter in self.get_player_ter(player_id):
            for enemy_id in ter.neighbors:
                enemy = self.territories.get(enemy_id)
                if enemy and enemy.owner != player_id:
                    enemy_ter.append(ter)
                    break
        
        return enemy_ter
            
    def connected_ter(self, player_id: int) -> bool:
        """
        проверяет что все территории игрока связны
        """
        owned = [ter.id for ter in self.get_player_ter(player_id)]
        if not owned:
            return False
        visited = set()
        queue = deque([owned[0]])
        while queue:
            cur = queue.popleft()
            if cur in visited:
                continue
            visited.add(cur)
            for nb in self.territories[cur].neighbors:
                if nb in self.territories and self.territories[nb].owner == player_id:
                    queue.append(nb)
        return len(visited) == len(owned)
 
    def check_win(self) -> int | None:
        """
        возвращает id победителя
        """
        owners = {ter.owner for ter in self.territories.values() if ter.owner is not None}
        if len(owners) == 1:
            return owners.pop()
        return None