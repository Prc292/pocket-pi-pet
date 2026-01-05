import math
from enum import Enum, auto
from dataclasses import dataclass

class PetState(Enum):
    """
    Enforces valid states for the pet behavior engine.
    Includes logic to handle old hyphenated save data names.
    """
    EGG = auto()
    BABY = auto()
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
    care_mistakes: int = 0 # This attribute is confirmed to exist now

    def clamp(self, value):
        return max(0.0, min(100.0, value))

    def tick(self, dt: float, current_state: PetState):
        """Standardized decay logic for real-time passage."""
        
        # --- Decay Rates (per hour) ---
        FULL_DECAY = 8.0
        HAPPY_DECAY = 10.0
        ENERGY_DECAY = 15.0
        ENERGY_REGEN = 30.0

        # Fullness decay (slower while sleeping)
        full_rate = FULL_DECAY if current_state!= PetState.SLEEPING else 2.0
        self.fullness = self.clamp(self.fullness - (full_rate / 3600.0) * dt)
        
        # Happiness decay (faster if hungry or sick)
        happy_rate = HAPPY_DECAY
        if self.fullness < 20.0: happy_rate += 5.0
        if current_state == PetState.SICK: happy_rate += 10.0
        self.happiness = self.clamp(self.happiness - (happy_rate / 3600.0) * dt)
        
        # Energy recovery vs drain
        if current_state == PetState.SLEEPING:
            self.energy = self.clamp(self.energy + (ENERGY_REGEN / 3600.0) * dt)
        elif current_state == PetState.PLAYING or current_state == PetState.TRAINING:
            self.energy = self.clamp(self.energy - (ENERGY_DECAY * 2 / 3600.0) * dt) # Double drain
        else:
            self.energy = self.clamp(self.energy - (ENERGY_DECAY / 3600.0) * dt)

        # Health decay
        if self.fullness == 0 or self.energy == 0 or current_state == PetState.SICK:
            self.health = self.clamp(self.health - (10.0 / 3600.0) * dt)
        elif self.health < 100.0:
            # Slow recovery if well cared for
            self.health = self.clamp(self.health + (2.0 / 3600.0) * dt)