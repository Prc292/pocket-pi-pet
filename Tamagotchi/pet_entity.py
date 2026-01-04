import time
import math
import pygame
from models import PetState, PetStats
from constants import *

class Pet:
    """Orchestrates FSM transitions and procedural animations.[4, 5]"""
    def __init__(self, db_manager):
        self.db = db_manager
        self.stats = PetStats()
        self.is_alive = True
        self.birth_time = time.time()
        self.last_update = time.time()
        self.life_stage = "EGG"
        self.state = PetState.EGG
        self.state_timer = 0.0 

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

        if self.state == PetState.EGG:
            if now - self.birth_time > 15:
                self.transition_to(PetState.IDLE)
                self.life_stage = "BABY"
            return

        self.stats.tick(dt, self.state)
        if self.stats.health <= 0:
            self.transition_to(PetState.DEAD)
            self.is_alive = False

    def draw(self, screen, cx, cy):
        """Visual representation using Procedural Animation.[5]"""
        t = self.state_timer
        if self.state == PetState.SLEEPING:
            bob, eye_closed = 5 * math.sin(t * 1.5), True
        elif self.state == PetState.DEAD:
            pygame.draw.circle(screen, (80, 80, 80), (cx, cy), 45)
            return
        else:
            bob = 10 * abs(math.sin(t * 4))
            eye_closed = (pygame.time.get_ticks() // 100) % 30 == 0

        # Body with Squash & Stretch
        width = 45 + (2 * math.sin(t * 4))
        height = 45 - (2 * math.sin(t * 4))
        pygame.draw.ellipse(screen, COLOR_PET_BODY, (cx - width, cy + bob - height, width*2, height*2))
        
        # Eyes and Mood-based Mouth
        eye_y, mouth_y = cy + bob - 10, cy + bob + 12
        if eye_closed or self.state == PetState.SLEEPING:
            pygame.draw.line(screen, COLOR_PET_EYES, (cx-15, eye_y), (cx-5, eye_y), 2)
            pygame.draw.line(screen, COLOR_PET_EYES, (cx+5, eye_y), (cx+15, eye_y), 2)
        else:
            pygame.draw.circle(screen, COLOR_PET_EYES, (cx-12, eye_y), 4)
            pygame.draw.circle(screen, COLOR_PET_EYES, (cx+12, eye_y), 4)

        if self.state == PetState.EATING:
            pygame.draw.circle(screen, (0, 0, 0), (cx, mouth_y), int(6 + (4 * math.sin(t * 10))))
        else:
            if self.stats.happiness > 70:
                pygame.draw.arc(screen, (0, 0, 0), (cx-10, mouth_y-5, 20, 10), math.pi, 2*math.pi, 2)
            elif self.stats.happiness < 30:
                pygame.draw.arc(screen, (0, 0, 0), (cx-10, mouth_y, 20, 10), 0, math.pi, 2)
            else:
                pygame.draw.line(screen, (0, 0, 0), (cx-10, mouth_y+2), (cx+10, mouth_y+2), 2)

    def save(self):
        data = {
            "hunger": self.stats.hunger, "happiness": self.stats.happiness,
            "energy": self.stats.energy, "health": self.stats.health,
            "is_alive": self.is_alive, "birth_time": self.birth_time,
            "life_stage": self.life_stage, "state": self.state.name
        }
        self.db.save_pet(data)

    def load(self):
        row = self.db.load_pet()
        if row:
            self.stats.hunger, self.stats.happiness = row[6], row[1]
            self.stats.energy, self.stats.health = row[7], row[8]
            self.is_alive, self.birth_time, self.life_stage = bool(row[9]), row[10], row[11]
            self.state = PetState[row[12]]
            offline_dt = time.time() - row[13]
            self.stats.tick(offline_dt, self.state)
            self.last_update = time.time()