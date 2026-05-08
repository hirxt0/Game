from dataclasses import dataclass
 
 
@dataclass
class Territory:
 
    id: int
    center: tuple[float, float] 
    vertices: list[tuple[float, float]] 
    neighbors: list[int]
 
    owner: int | None = None   
    troops: int = 1
 
    def is_neutral(self) -> bool:
        return self.owner is None
 
    def can_attack(self, target: "Territory") -> bool:
        return target.id in self.neighbors and target.owner != self.owner
 
    def resolve_attack(self, attacker_troops: int) -> bool:
        if attacker_troops > self.troops:
            self.troops = attacker_troops - self.troops
            return True
        else:
            self.troops -= attacker_troops
            self.troops = max(self.troops, 0)
            return False
 