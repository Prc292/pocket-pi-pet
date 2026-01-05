import math
from enum import Enum, auto
from dataclasses import dataclass

class PetState(Enum):
    """Enforces valid states for the pet behavior engine."""
    EGG = auto()
    BABY = auto()
    IDLE = auto()
    EATING = auto()
    SLEEPING = auto()
    SICK = auto()
    DEAD = auto()

@dataclass
class PetStats:
    """Uses a linear decay model: Vt = V0 - (r * dt)."""
    fullness: float = 50.0  # 100 = Full, 0 = Starving
    happiness: float = 100.0
    energy: float = 100.0
    health: float = 100.0
    discipline: float = 50.0
    care_mistakes: int = 0

    def clamp(self, value):
        return max(0.0, min(100.0, value))

    def tick(self, dt: float, current_state: PetState):
        """Standardized decay logic for real-time passage."""
        # Slower fullness decay while sleeping
        full_rate = 8.0 if current_state!= PetState.SLEEPING else 2.0
        self.fullness = self.clamp(self.fullness - (full_rate / 3600.0) * dt)
        
        # Energy recovery vs drain
        if current_state == PetState.SLEEPING:
            self.energy = self.clamp(self.energy + (30.0 / 3600.0) * dt)
        else:
            self.energy = self.clamp(self.energy - (4.0 / 3600.0) * dt)

        self.happiness = self.clamp(self.happiness - (6.0 / 3600.0) * dt)

        # Health logic: decay if needs are critically low
        if self.fullness < 10 or self.energy < 10:
            self.health = self.clamp(self.health - (20.0 / 3600.0) * dt)
        elif self.fullness > 50:
            self.health = self.clamp(self.health + (5.0 / 3600.0) * dt)