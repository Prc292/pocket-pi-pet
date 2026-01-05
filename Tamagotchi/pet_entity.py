import time
import math
import pygame
from models import PetState, PetStats
from constants import *

class Pet:
    """Manages evolution paths and procedural visuals."""
    def __init__(self, db_manager):
        self.db = db_manager
        self.stats = PetStats()
        self.is_alive = True
        self.birth_time = time.time()
        self.last_update = time.time()
        self.life_stage = "EGG"
        self.state = PetState.EGG
        self.state_timer = 0.0 
        self.mistake_counter_timer = 0.0 

    def transition_to(self, new_state: PetState):
        if self.state == new_state: return
        self.state = new_state
        self.state_timer = 0.0 

    def update(self):
        if self.state == PetState.DEAD: return
        now = time.time()
        dt = now - self.last_update
        self.last_update = now
        self.state_timer += 0.05 

        # Evolution Logic: EGG -> BABY -> Branching
        if self.state == PetState.EGG and (now - self.birth_time > 15):
            self.life_stage = "BABY"
            self.transition_to(PetState.IDLE)
        elif self.life_stage == "BABY" and (now - self.birth_time > 60):
            self.life_stage = "ELITE-CHILD" if self.stats.care_mistakes == 0 else "NEEDY-CHILD"
            self.transition_to(PetState.IDLE)

        # Mistake Tracking [8]
        if self.stats.fullness < 10 or self.stats.energy < 10:
            self.mistake_counter_timer += dt
            if self.mistake_counter_timer > 30: 
                self.stats.care_mistakes += 1
                self.mistake_counter_timer = 0
        else:
            self.mistake_counter_timer = 0

        self.stats.tick(dt, self.state)
        if self.stats.health <= 0:
            self.transition_to(PetState.DEAD)
            self.is_alive = False

    def draw(self, screen, cx, cy):
        """Procedural animation based on trig waves."""
        t = self.state_timer
        body_color = COLOR_SICK if self.stats.care_mistakes > 2 else COLOR_PET_BODY
        
        if self.state == PetState.SLEEPING:
            bob, eye_closed = 5 * math.sin(t * 1.5), True
        elif self.state == PetState.DEAD:
            pygame.draw.circle(screen, (80, 80, 80), (cx, cy), 45)
            return
        else:
            bob = 10 * abs(math.sin(t * 4))
            eye_closed = (pygame.time.get_ticks() // 100) % 30 == 0

        width, height = 45 + (2 * math.sin(t * 4)), 45 - (2 * math.sin(t * 4))
        if "ELITE" in self.life_stage: width += 10 
        
        pygame.draw.ellipse(screen, body_color, (cx - width, cy + bob - height, width*2, height*2))
        eye_y, mouth_y = cy + bob - 10, cy + bob + 12
        pygame.draw.circle(screen, COLOR_PET_EYES, (cx-12, eye_y), 4 if not eye_closed else 2)
        pygame.draw.circle(screen, COLOR_PET_EYES, (cx+12, eye_y), 4 if not eye_closed else 2)

        if self.state == PetState.EATING:
            pygame.draw.circle(screen, (0, 0, 0), (cx, mouth_y), int(6 + (4 * math.sin(t * 10))))
        else:
            if self.stats.happiness > 70:
                pygame.draw.arc(screen, (0, 0, 0), (cx-10, mouth_y-5, 20, 10), math.pi, 2*math.pi, 2)
            else:
                pygame.draw.line(screen, (0, 0, 0), (cx-10, mouth_y+2), (cx+10, mouth_y+2), 2)

    def save(self):
        data = {
            "fullness": self.stats.fullness, "happiness": self.stats.happiness,
            "energy": self.stats.energy, "health": self.stats.health,
            "discipline": self.stats.discipline, "care_mistakes": self.stats.care_mistakes,
            "is_alive": self.is_alive, "birth_time": self.birth_time,
            "life_stage": self.life_stage, "state": self.state.name
        }
        self.db.save_pet(data)

    def load(self):
        row = self.db.load_pet()
        if row:
            # Fixed Index Alignment (0-11)
            self.stats.fullness = row[1]
            self.stats.happiness = row[2]
            self.stats.energy = row[3]
            self.stats.health = row[4]
            self.stats.discipline = row[5]
            self.stats.care_mistakes = row[6]
            self.is_alive = bool(row[7])
            self.birth_time = row[8]
            self.life_stage = row[9]
            self.state = PetState[row[10]]
            # Offline Catch-up Logic
            offline_dt = time.time() - row[11]
            self.stats.tick(offline_dt, self.state)
            self.last_update = time.time()