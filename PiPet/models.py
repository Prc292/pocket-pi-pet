import math
from enum import Enum, auto
from dataclasses import dataclass

class GameState(Enum):
    PET_VIEW = auto()
    INVENTORY_VIEW = auto()
    ACTIVITIES_VIEW = auto()
    CATCH_THE_FOOD_MINIGAME = auto()
    GARDENING_MINIGAME = auto()

class PetState(Enum):
    """
    Enforces valid states for the pet behavior engine.
    Includes logic to handle old hyphenated save data names.
    """
    EGG = auto()
    BABY = auto()
    CHILD = auto()
    TEEN_GOOD = auto()
    TEEN_BAD = auto()
    ADULT_GOOD = auto()
    ADULT_BAD = auto()
    IDLE = auto()
    EATING = auto()
    PLAYING = auto()
    TRAINING = auto()
    SLEEPING = auto()
    SICK = auto()
    DEAD = auto()

    @classmethod
    def _missing_(cls, value):
        """
        Flexible lookup to handle legacy save data with hyphens (like 'ELITE-CHILD').
        It maps any unrecognized state to IDLE to prevent crashes.
        """
        if isinstance(value, str):
            normalized = value.replace('-', '_').upper()
            
            # Check if normalized state exists
            for member in cls:
                if member.name == normalized:
                    return member
            
            # Fallback for completely removed states (like 'ELITE_CHILD')
            if 'CHILD' in normalized or 'ELITE' in normalized:
                print(f"WARNING: Mapping deprecated state '{value}' to IDLE.")
                return cls.IDLE

        return super()._missing_(value)


@dataclass
class PetStats:
    """Uses a linear decay model: Vt = V0 - (r * dt)."""
    fullness: float = 50.0  # 100 = Full, 0 = Starving
    happiness: float = 100.0
    energy: float = 100.0
    health: float = 100.0
    discipline: float = 50.0
    care_mistakes: int = 0
    coins: int = 0

    def clamp(self, value):
        return max(0.0, min(100.0, value))

    def tick(self, dt: float, current_state: PetState, current_hour: int):
        """Standardized decay logic for real-time passage."""
        
        # --- Decay Rates (per second) ---
        FULL_DECAY_SEC = 8.0 / 3600.0   # 8 units per hour
        HAPPY_DECAY_SEC = 10.0 / 3600.0
        ENERGY_DECAY_SEC = 15.0 / 3600.0
        ENERGY_REGEN_SEC = 30.0 / 3600.0
        HEALTH_DECAY_SEC = 10.0 / 3600.0
        HEALTH_REGEN_SEC = 2.0 / 3600.0

        # Fullness decay (slower while sleeping)
        full_rate = FULL_DECAY_SEC if current_state!= PetState.SLEEPING else 2.0 / 3600.0
        self.fullness = self.clamp(self.fullness - full_rate * dt)
        
        # Happiness decay (faster if hungry or sick)
        happy_rate = HAPPY_DECAY_SEC
        if self.fullness < 20.0: happy_rate += 5.0 / 3600.0
        if current_state == PetState.SICK: happy_rate += 10.0 / 3600.0
        self.happiness = self.clamp(self.happiness - happy_rate * dt)
        
        # Energy recovery vs drain
        energy_drain_rate = ENERGY_DECAY_SEC
        if (current_hour >= 22 or current_hour < 6) and current_state != PetState.SLEEPING:
            energy_drain_rate *= 1.5 # 50% increased drain at night if not sleeping

        if current_state == PetState.SLEEPING:
            self.energy = self.clamp(self.energy + ENERGY_REGEN_SEC * dt)
        elif current_state == PetState.PLAYING or current_state == PetState.TRAINING:
            self.energy = self.clamp(self.energy - energy_drain_rate * 2 * dt) # Double drain
        else:
            self.energy = self.clamp(self.energy - energy_drain_rate * dt)

        # Health decay
        if self.fullness == 0 or self.energy == 0 or current_state == PetState.SICK:
            self.health = self.clamp(self.health - HEALTH_DECAY_SEC * dt)
        elif self.health < 100.0:
            # Slow recovery if well cared for
            self.health = self.clamp(self.health + HEALTH_REGEN_SEC * dt)