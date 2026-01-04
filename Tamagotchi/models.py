import math
from enum import Enum, auto
from dataclasses import dataclass

class PetState(Enum):
    """Enforces valid states for the Finite State Machine ."""
    EGG = auto()
    BABY = auto()
    IDLE = auto()
    EATING = auto()
    SLEEPING = auto()
    DEAD = auto()

@dataclass
class PetStats:
    """Standardized container for pet vital signs ."""
    hunger: float = 50.0    # 0 = Full, 100 = Starving
    happiness: float = 100.0
    energy: float = 100.0
    health: float = 100.0

    def clamp(self, value):
        return max(0.0, min(100.0, value))

    def tick(self, dt: float, current_state: PetState):
        """Calculates decay based on elapsed real-time: Vt = V0 ± (r * dt) ."""
        # Hunger increases faster if active
        hunger_rate = 8.0 if current_state!= PetState.SLEEPING else 2.0
        self.hunger = self.clamp(self.hunger + (hunger_rate / 3600.0) * dt)
        
        # Energy logic: recover while sleeping, drain while awake
        if current_state == PetState.SLEEPING:
            self.energy = self.clamp(self.energy + (30.0 / 3600.0) * dt)
        else:
            self.energy = self.clamp(self.energy - (4.0 / 3600.0) * dt)

        self.happiness = self.clamp(self.happiness - (6.0 / 3600.0) * dt)

        # Health logic: decay if needs are not met
        if self.hunger > 80 or self.energy < 10:
            self.health = self.clamp(self.health - (15.0 / 3600.0) * dt)
        elif self.hunger < 50:
            self.health = self.clamp(self.health + (5.0 / 3600.0) * dt)