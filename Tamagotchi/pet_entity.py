import time
import math
import pygame
import random
from models import PetState, PetStats
from constants import COLOR_PET_BODY, COLOR_PET_EYES

# Assuming DatabaseManager is imported/available, but we rely on a passed db object

class Pet:
    def __init__(self, db_manager, name="Pet"):
        self.name = name
        self.db = db_manager # DatabaseManager instance
        self.stats = PetStats() # Fix: Use PetStats dataclass
        self.state = PetState.EGG
        self.life_stage = "EGG" # For display
        self.is_alive = True
        self.birth_time = time.time()
        self.last_update = time.time()

        # Animation State
        self.idle_bob_offset = 0.0
        self.idle_bob_timer = 0.0
        self.eye_timer = 0.0
        self.eye_blink_duration = 0.1
        self.eyes_open = True
        self.action_timer = 0.0
        self.action_duration = 3.0 # Duration for EATING, PLAYING, etc.

    def transition_to(self, new_state: PetState):
        """Fix: Implements the missing state transition method."""
        if self.state != new_state:
            print(f"Pet transitioning from {self.state.name} to {new_state.name}")
            self.state = new_state
            self.action_timer = 0.0 # Reset timer on new action

    def handle_action_complete(self, action_name: str):
        """Logic for when an action (FEED, PLAY, etc.) is complete."""
        if self.state == PetState.EATING:
            self.stats.fullness = self.stats.clamp(self.stats.fullness + 20)
            self.stats.health = self.stats.clamp(self.stats.health + 5)
        elif self.state == PetState.PLAYING:
            self.stats.happiness = self.stats.clamp(self.stats.happiness + 30)
            self.stats.energy = self.stats.clamp(self.stats.energy - 10)
        elif self.state == PetState.TRAINING:
            self.stats.discipline = self.stats.clamp(self.stats.discipline + 15)
            self.stats.happiness = self.stats.clamp(self.stats.happiness - 5)
        
        self.transition_to(PetState.IDLE)


    def update(self, dt):
        """Handles real-time stat decay, action timers, and evolution checks."""
        
        # 1. Update action timer
        if self.state in [PetState.EATING, PetState.PLAYING, PetState.TRAINING]:
            self.action_timer += dt
            if self.action_timer >= self.action_duration:
                self.handle_action_complete(self.state.name)
        
        # 2. Update Stats
        self.stats.tick(dt, self.state)
        
        # 3. Handle Animation Timers (Bobbing and Blinking)
        # Smooth bobbing motion
        self.idle_bob_timer = (self.idle_bob_timer + dt) % (math.pi * 2) # Cycle every ~6.28 seconds
        self.idle_bob_offset = math.sin(self.idle_bob_timer * 3) * 2 # Moves pet up/down 2 pixels slowly

        # Blinking logic
        if self.state != PetState.SLEEPING:
            self.eye_timer += dt
            if self.eyes_open:
                # Blink approx every 3-5 seconds
                if self.eye_timer > 3.0 + (random.random() * 2.0): 
                    self.eyes_open = False
                    self.eye_timer = 0.0
            else:
                # Keep eyes closed for a short duration
                if self.eye_timer > self.eye_blink_duration:
                    self.eyes_open = True
                    self.eye_timer = 0.0

        # 4. State Checks and Evolution (Simplified)
        if self.state != PetState.DEAD:
            if self.stats.fullness == 0.0 or self.stats.health == 0.0:
                self.transition_to(PetState.SICK) # Or DEAD, depending on rules
                self.stats.care_mistakes += 1
            
            # Simplified Life Stage check (based on total time or discipline)
            if self.life_stage == "EGG" and time.time() - self.birth_time > 10: # Hatch after 10s
                self.life_stage = "BABY"
                self.transition_to(PetState.BABY)
            elif self.life_stage == "BABY" and time.time() - self.birth_time > 60: # Grow after 60s
                self.life_stage = "CHILD"
                self.transition_to(PetState.IDLE) # Child/Adult maps to IDLE


        # 5. Save state every few seconds
        if time.time() - self.last_update > 5: # Save every 5 seconds
            self.save()
            self.last_update = time.time()


    def load(self):
        """Fetches data from the database and initializes pet state."""
        try:
            row = self.db.load_pet() # Get the last saved row

            if row:
                # Data indices based on DatabaseManager.create_tables schema:
                # (1:fullness, 2:happiness, 3:energy, 4:health, 5:discipline, 6:care_mistakes, 
                # 7:is_alive, 8:birth_time, 9:last_update, 10:life_stage, 11:state)
                
                # Update PetStats
                self.stats.fullness = row[1]
                self.stats.happiness = row[2]
                self.stats.energy = row[3]
                self.stats.health = row[4]
                self.stats.discipline = row[5]
                self.stats.care_mistakes = row[6]
                
                # Update Pet attributes
                self.is_alive = bool(row[7])
                self.birth_time = row[8]
                self.last_update = row[9]
                self.life_stage = row[10] # e.g., "CHILD"
                
                # Fix: Use PetState() constructor which uses the _missing_ logic
                # Index 11 is the 'state' column
                self.state = PetState(row[11]) 
            
            # Adjust stats based on time passed since last save
            time_passed = time.time() - self.last_update
            # Simulate decay that occurred while the game was shut down
            self.stats.tick(time_passed, self.state) 

        except Exception as e:
            print(f"Loading failed, starting fresh (Error: {e})")
            # If loading fails, start a new pet
            self.stats = PetStats() 
            self.state = PetState.EGG
            self.life_stage = "EGG"
            self.birth_time = time.time()
            self.last_update = time.time()

    def save(self):
        """Saves current state to the database."""
        pet_data = {
            'fullness': self.stats.fullness,
            'happiness': self.stats.happiness,
            'energy': self.stats.energy,
            'health': self.stats.health,
            'discipline': self.stats.discipline,
            'care_mistakes': self.stats.care_mistakes,
            'is_alive': self.is_alive,
            'birth_time': self.birth_time,
            # last_update is set in DatabaseManager.save_pet
            'life_stage': self.life_stage,
            'state': self.state.name
        }
        self.db.save_pet(pet_data)

    def draw(self, surface, cx, cy):
        """Fix: Implements the missing draw method with simple animations."""
        
        # --- Pet Drawing Parameters (Relative to center) ---
        body_w, body_h = 60, 50
        eye_w, eye_h = 8, 10
        mouth_w, mouth_h = 10, 5
        
        # Apply idle bob offset
        cy = cy + self.idle_bob_offset

        # --- Draw Body ---
        body_rect = pygame.Rect(cx - body_w // 2, cy - body_h // 2, body_w, body_h)
        # Use a smooth circle/oval for the body
        pygame.draw.circle(surface, COLOR_PET_BODY, (cx, cy), body_w // 2)

        # Draw Feet/Paws
        paw_w, paw_h = 10, 5
        pygame.draw.ellipse(surface, COLOR_PET_BODY, (cx - 20, cy + body_h // 2 - paw_h, paw_w, paw_h))
        pygame.draw.ellipse(surface, COLOR_PET_BODY, (cx + 10, cy + body_h // 2 - paw_h, paw_w, paw_h))
        
        # --- Draw Face ---
        
        # Eyes
        if self.state == PetState.SLEEPING:
            # Draw closed eyes
            pygame.draw.line(surface, COLOR_PET_EYES, (cx - 15, cy - 10), (cx - 5, cy - 10), 2)
            pygame.draw.line(surface, COLOR_PET_EYES, (cx + 5, cy - 10), (cx + 15, cy - 10), 2)
        elif self.eyes_open:
            # Open eyes
            pygame.draw.ellipse(surface, COLOR_PET_EYES, (cx - 15, cy - 15, eye_w, eye_h))
            pygame.draw.ellipse(surface, COLOR_PET_EYES, (cx + 5, cy - 15, eye_w, eye_h))
        else:
            # Blinking eyes (a line)
            pygame.draw.line(surface, COLOR_PET_EYES, (cx - 15, cy - 10), (cx - 5, cy - 10), 2)
            pygame.draw.line(surface, COLOR_PET_EYES, (cx + 5, cy - 10), (cx + 15, cy - 10), 2)
        
        # Mouth (simple rectangle)
        mouth_rect = pygame.Rect(cx - mouth_w // 2, cy + 5, mouth_w, mouth_h)
        pygame.draw.rect(surface, COLOR_PET_EYES, mouth_rect, border_radius=1)

        # --- State Visuals ---
        if self.state == PetState.EATING:
            # Food item above mouth
            pygame.draw.circle(surface, (100, 50, 0), (cx + 10, cy), 5) 
        
        if self.state == PetState.SICK:
            # Draw a sick icon (cross)
            pygame.draw.line(surface, (255, 0, 0), (cx - 20, cy - 30), (cx - 10, cy - 40), 3)
            pygame.draw.line(surface, (255, 0, 0), (cx - 10, cy - 30), (cx - 20, cy - 40), 3)