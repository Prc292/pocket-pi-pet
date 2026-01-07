import time
import math
import pygame
import random
import datetime # Add this import
from models import PetState, PetStats
from constants import COLOR_PET_BODY, COLOR_PET_EYES, COLOR_HEALTH, COLOR_TEXT, COLOR_SICK, TIME_SCALE_FACTOR 

# --- EVOLUTION TIMES (in real seconds, scaled by TIME_SCALE_FACTOR) ---
TIME_TO_BABY_SEC = 60.0  # 90 game-seconds (90 / 10)
TIME_TO_CHILD_SEC = 17280.0 # 2 game-days (2 * 24 * 60 * 60 / 10)
TIME_TO_TEEN_SEC = 34560.0 # 4 game-days (4 * 24 * 60 * 60 / 10)
TIME_TO_ADULT_SEC = 60480.0 # 7 game-days (7 * 24 * 60 * 60 / 10)
class Pet:
    # ------------------------------------------------------------------
    # FIX #1: Correct __init__ signature (fixes "Pet() takes no arguments")
    # ------------------------------------------------------------------
    def __init__(self, db_manager, name="Pet"): 
        self.name = name
        self.db = db_manager # DatabaseManager instance
        self.stats = PetStats() 
        self.state = PetState.EGG
        self.life_stage = PetState.EGG

        self.is_alive = True
        self.birth_time = time.time() 
        self.last_update = time.time()

        # Animation State
        self.idle_bob_offset = 0.0
        self.idle_bob_timer = 0.0
        self.play_bounce_timer = 0.0
        self.eye_timer = 0.0
        self.eye_blink_duration = 0.1
        self.eyes_open = True
        
        # Egg cracking animation
        self.crack_level = 0.0
        
        # Action feedback
        self.action_timer = 0.0
        self.action_duration = 3.0
        self.action_feedback_timer = 0.0
        self.action_feedback_text = ""

    def transition_to(self, new_state: PetState):
        if self.state != new_state:
            print(f"Pet transitioning from {self.state.name} to {new_state.name}")
            self.state = new_state
            self.action_timer = 0.0 

    def handle_action_complete(self, action_name: str):
        self.action_feedback_timer = 2.0 
        
        if self.state == PetState.EATING:
            self.stats.fullness = self.stats.clamp(self.stats.fullness + 20)
            self.stats.health = self.stats.clamp(self.stats.health + 5)
            self.action_feedback_text = "YUMMY!"
        elif self.state == PetState.PLAYING:
            self.stats.happiness = self.stats.clamp(self.stats.happiness + 30)
            self.stats.energy = self.stats.clamp(self.stats.energy - 10)
            self.action_feedback_text = "WOOHOO!"
        elif self.state == PetState.TRAINING:
            self.stats.discipline = self.stats.clamp(self.stats.discipline + 15)
            self.stats.happiness = self.stats.clamp(self.stats.happiness - 5)
            self.action_feedback_text = "SMART!"
        
        self.transition_to(PetState.IDLE)
        
    def heal(self):
        if self.state == PetState.SICK:
            if self.stats.discipline >= 10:
                self.stats.health = self.stats.clamp(self.stats.health + 20)
                self.stats.discipline = self.stats.clamp(self.stats.discipline - 10)
                self.action_feedback_text = "FEELING BETTER!"
                self.action_feedback_timer = 2.0
                self.transition_to(PetState.IDLE)
            else:
                self.action_feedback_text = "NEED DISCIPLINE TO HEAL!"
                self.action_feedback_timer = 2.0


    def update(self, dt, current_hour):
        """Handles real-time stat decay, action timers, and evolution checks."""

        scaled_dt = dt * TIME_SCALE_FACTOR
        
        if not self.is_alive and self.state == PetState.DEAD:
            return

        # 1. Update action timer (Use real dt for fixed action duration)
        if self.state in [PetState.EATING, PetState.PLAYING, PetState.TRAINING]:
            self.action_timer += dt 
            if self.action_timer >= self.action_duration:
                self.handle_action_complete(self.state.name)
        
        # 2. Update Stats (Use scaled_dt for accelerated decay)
        self.stats.tick(scaled_dt, self.state, current_hour)
        
        # 3. Handle Animation Timers and Feedback (Use real dt for smooth visuals)
        self.idle_bob_timer = (self.idle_bob_timer + dt) % (math.pi * 2) 
        self.idle_bob_offset = math.sin(self.idle_bob_timer * 3) * 2 
        
        if self.action_feedback_timer > 0:
            self.action_feedback_timer -= dt

        # Blinking logic (Use real dt)
        if self.state != PetState.SLEEPING:
            self.eye_timer += dt
            if self.eyes_open:
                if self.eye_timer > 3.0 + (random.random() * 2.0): 
                    self.eyes_open = False
                    self.eye_timer = 0.0
            else:
                if self.eye_timer > self.eye_blink_duration:
                    self.eyes_open = True
                    self.eye_timer = 0.0

        # 4. State Checks and Evolution
        
        # Death check is prioritized
        if self.stats.health == 0.0 and self.is_alive:
            self.is_alive = False
            self.transition_to(PetState.DEAD)
            self.save() 
            return
            
        # Sickness check
        if self.stats.fullness == 0.0 or self.stats.health < 10.0:
            if self.state != PetState.SICK and self.state != PetState.DEAD:
                self.transition_to(PetState.SICK)
                self.stats.care_mistakes += 1
        elif self.state == PetState.SICK and self.stats.health > 50:
             self.transition_to(PetState.IDLE) 
            
        # Life Stage check (based on total accumulated game time)
        total_game_time = (time.time() - self.birth_time) * TIME_SCALE_FACTOR
        
        if self.life_stage == PetState.EGG and total_game_time > TIME_TO_BABY_SEC:
            self.life_stage = PetState.BABY
            self.transition_to(PetState.IDLE)
        elif self.life_stage == PetState.BABY and total_game_time > TIME_TO_CHILD_SEC:
            self.life_stage = PetState.CHILD
            self.transition_to(PetState.IDLE)
        elif self.life_stage == PetState.CHILD and total_game_time > TIME_TO_TEEN_SEC:
            if self.stats.care_mistakes < 3 and self.stats.discipline > 50:
                self.life_stage = PetState.TEEN_GOOD
            else:
                self.life_stage = PetState.TEEN_BAD
            self.transition_to(PetState.IDLE)
        elif self.life_stage in [PetState.TEEN_GOOD, PetState.TEEN_BAD] and total_game_time > TIME_TO_ADULT_SEC:
            if self.stats.care_mistakes < 5 and self.stats.happiness > 75:
                self.life_stage = PetState.ADULT_GOOD
            else:
                self.life_stage = PetState.ADULT_BAD
            self.transition_to(PetState.IDLE)


        # 5. Save state every few seconds
        if time.time() - self.last_update > 5: 
            self.save()
            self.last_update = time.time()

   
    # ------------------------------------------------------------------
    def load(self):

        """Fetches data from the database and initializes pet state."""
        try:
            row = self.db.load_pet() 

            if row:
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
                self.life_stage = PetState[row[10]]
                self.state = PetState[row[11]]
                if len(row) > 12: 
                    self.name = row[12] 
            
            # Adjust stats based on time passed since last save (scaled time)
            time_passed_real = time.time() - self.last_update
            time_passed_game = time_passed_real * TIME_SCALE_FACTOR
            self.stats.tick(time_passed_game, self.state, datetime.datetime.now().hour) 

        except Exception as e:
            print(f"Loading failed, starting fresh (Error: {e})")
            self.stats = PetStats() 
            self.state = PetState.EGG
            self.life_stage = PetState.EGG
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
            'life_stage': self.life_stage.name,
            'state': self.state.name,
            'name': self.name
        }
        self.db.save_pet(pet_data)
    
    # --- Drawing Logic (Retained animation updates) ---
    def _draw_body(self, surface, cx, cy, radius, color, scale_x=1.0, scale_y=1.0):
        """Draws a base body shape (ellipse) and simple limbs with scaling applied."""
        
        radius_x = radius * scale_x
        radius_y = radius * scale_y
        
        body_h = radius_y * 1.6
        body_w = radius_x * 1.8
        
        cy = cy + self.idle_bob_offset 
        
        body_rect = pygame.Rect(cx - body_w // 2, cy - body_h // 2, body_w, body_h)
        pygame.draw.ellipse(surface, color, body_rect)
        
        # Feet/Paws
        paw_w, paw_h = radius_x // 3, radius_y // 5
        pygame.draw.ellipse(surface, color, (cx - radius_x + paw_w, cy + body_h // 2 - paw_h, paw_w, paw_h))
        pygame.draw.ellipse(surface, color, (cx + radius_x - (2*paw_w), cy + body_h // 2 - paw_h, paw_w, paw_h))

        return cx, cy, body_w, body_h

    def _draw_egg_crack(self, surface, cx, cy, radius, crack_level):
        """Draws cracks on the egg based on the crack_level."""
        egg_color = (245, 245, 210)
        crack_color = (100, 80, 50)
        
        # Base egg shape
        egg_rect = pygame.Rect(cx - radius, cy - radius * 1.5, radius * 2, radius * 3)
        pygame.draw.ellipse(surface, egg_color, egg_rect)

        # Main crack line (grows with crack_level)
        if crack_level > 0:
            # Crack from top-ish to bottom-ish
            start_x = cx + (radius * 0.2 * math.sin(crack_level * math.pi * 2))
            start_y = cy - radius * (1.2 - crack_level * 0.5) 
            end_x = cx + (radius * 0.3 * math.sin(crack_level * math.pi * 3 + math.pi/2))
            end_y = cy + radius * (1.2 - (1-crack_level) * 0.5)
            pygame.draw.line(surface, crack_color, (start_x, start_y), (end_x, end_y), 2)
            
            # Branches for the crack
            if crack_level > 0.3:
                branch1_x = start_x + (end_x - start_x) * 0.3
                branch1_y = start_y + (end_y - start_y) * 0.3
                pygame.draw.line(surface, crack_color, (branch1_x, branch1_y), (branch1_x - radius * 0.5 * crack_level, branch1_y - radius * 0.2 * crack_level), 2)
            
            if crack_level > 0.6:
                branch2_x = start_x + (end_x - start_x) * 0.7
                branch2_y = start_y + (end_y - start_y) * 0.7
                pygame.draw.line(surface, crack_color, (branch2_x, branch2_y), (branch2_x + radius * 0.4 * crack_level, branch2_y - radius * 0.3 * crack_level), 2)
        
    def draw(self, surface, cx, cy, font):
        """Draws the pet, applying visual modifications based on state and health."""


        # 1. Determine base size and color
        radius = 15
        if self.life_stage == PetState.EGG:
            radius = 20
        elif self.life_stage == PetState.BABY:
            radius = 30
        elif self.life_stage == PetState.CHILD:
            radius = 40
        elif self.life_stage in [PetState.TEEN_GOOD, PetState.TEEN_BAD]:
            radius = 50
        elif self.life_stage in [PetState.ADULT_GOOD, PetState.ADULT_BAD]:
            radius = 60
            
        base_color = COLOR_PET_BODY
        # Dynamic color shift for low health
        if self.stats.health < 50:
            ratio = 1.0 - (self.stats.health / 50.0) 
            r = int(base_color[0] + (100 - base_color[0]) * ratio)
            g = int(base_color[1] + (100 - base_color[1]) * ratio)
            b = int(base_color[2] + (100 - base_color[2]) * ratio)
            pet_color = (r, g, b)
        else:
            pet_color = base_color

        
        # --- Animation & State-specific drawing setup ---
        scale_x, scale_y = 1.0, 1.0
        y_offset_action = 0 
        
        if self.state == PetState.IDLE:
            squash_factor = math.sin(self.idle_bob_timer * 3)
            scale_x = 1.0 + squash_factor * 0.05
            scale_y = 1.0 - squash_factor * 0.05

        if self.state == PetState.EATING:
            # Shrink and darken the color slightly when eating
            scale_x, scale_y = 0.9, 0.9
            pet_color = (max(0, pet_color[0]-20), max(0, pet_color[1]-20), max(0, pet_color[2]-20))
            
        elif self.state == PetState.PLAYING:
            # Apply a rapid, exaggerated bounce for playing
            self.play_bounce_timer = (self.play_bounce_timer + time.time() * 10) % (math.pi * 2)
            y_offset_action = math.sin(self.play_bounce_timer) * 1
            # Draw a brighter color when happy/playing
            pet_color = (min(255, pet_color[0]+30), min(255, pet_color[1]+30), min(255, pet_color[2]+30))
            
        # --- Handle DEAD/EGG State (Early Exit) ---
        if self.state == PetState.DEAD:
             dead_color = (80, 80, 80)
             pygame.draw.ellipse(surface, dead_color, (cx - radius, cy - radius // 2 + 10, radius * 2, radius))
             dead_text = font.render("REST IN PEACE", True, (255, 0, 0))
             surface.blit(dead_text, dead_text.get_rect(center=(cx, cy)))
             return
        

        if self.life_stage == PetState.EGG:
            time_elapsed_game = (time.time() - self.birth_time) * TIME_SCALE_FACTOR
            self.crack_level = min(1.0, time_elapsed_game / TIME_TO_BABY_SEC)
            
            self._draw_egg_crack(surface, cx, cy, radius, self.crack_level)
            
            time_left = max(0, int(TIME_TO_BABY_SEC - time_elapsed_game))
            egg_text = font.render(f"EGG ({time_left}s)", True, COLOR_TEXT)
            surface.blit(egg_text, egg_text.get_rect(center=(cx, cy)))
            return # Ensure nothing else is drawn when in EGG state
            
        # --- Draw Active Pet Body ---
        else:
            cx, cy = cx, cy + y_offset_action 
            cx, cy_body_center, body_w, body_h = self._draw_body(surface, cx, cy, radius, pet_color, scale_x, scale_y)
            
            # --- Draw Evolution Features ---
            if self.life_stage in [PetState.TEEN_GOOD, PetState.ADULT_GOOD]:
                # Draw a halo for "good" evolutions
                pygame.draw.circle(surface, (255, 255, 0), (cx, cy_body_center - body_h // 2 - 10), radius // 4, 2)
            elif self.life_stage in [PetState.TEEN_BAD, PetState.ADULT_BAD]:
                # Draw horns for "bad" evolutions
                pygame.draw.polygon(surface, (100, 0, 0), [(cx - radius // 2, cy_body_center - body_h // 2), (cx - radius // 4, cy_body_center - body_h), (cx, cy_body_center - body_h // 2)])
                pygame.draw.polygon(surface, (100, 0, 0), [(cx + radius // 2, cy_body_center - body_h // 2), (cx + radius // 4, cy_body_center - body_h), (cx, cy_body_center - body_h // 2)])

            
            # --- Draw Face ---
            eye_y = cy_body_center - radius * scale_y // 3
            eye_w, eye_h = radius * scale_x // 4, radius * scale_y // 3
            
            # Eyes
            if self.state == PetState.SLEEPING:
                zzz = font.render("Zzz", True, COLOR_TEXT)
                surface.blit(zzz, zzz.get_rect(center=(cx + radius + 5, cy_body_center - radius)))
                pygame.draw.line(surface, COLOR_PET_EYES, (cx - eye_w, eye_y), (cx - eye_w // 2, eye_y), 2)
                pygame.draw.line(surface, COLOR_PET_EYES, (cx + eye_w // 2, eye_y), (cx + eye_w, eye_y), 2)
            elif self.eyes_open:
                pygame.draw.ellipse(surface, COLOR_PET_EYES, (cx - eye_w * 1.5, eye_y - eye_h // 2, eye_w, eye_h))
                pygame.draw.ellipse(surface, COLOR_PET_EYES, (cx + eye_w * 0.5, eye_y - eye_h // 2, eye_w, eye_h))
            else:
                pygame.draw.line(surface, COLOR_PET_EYES, (cx - eye_w * 1.5, eye_y), (cx - eye_w * 0.5, eye_y), 2)
                pygame.draw.line(surface, COLOR_PET_EYES, (cx + eye_w * 0.5, eye_y), (cx + eye_w * 1.5, eye_y), 2)
            
            # --- Mouth ---
            mouth_y = cy_body_center + radius * scale_y // 3
            mouth_w = radius * scale_x // 3

            # Eating animation overrides normal mouth
            if self.state == PetState.EATING:
                chew_h = (math.sin(self.action_timer * 10) + 1) * 4 # Oscillates between 0 and 8
                mouth_rect = pygame.Rect(cx - mouth_w // 2, mouth_y, mouth_w, chew_h)
                pygame.draw.ellipse(surface, COLOR_PET_EYES, mouth_rect)
            # Happy/Sad mouth
            elif self.stats.happiness > 70:
                # Smile (arc)
                mouth_rect = pygame.Rect(cx - mouth_w // 2, mouth_y - 5, mouth_w, 10)
                pygame.draw.arc(surface, COLOR_PET_EYES, mouth_rect, math.pi, 2 * math.pi, 2)
            elif self.stats.happiness < 30:
                # Frown (arc)
                mouth_rect = pygame.Rect(cx - mouth_w // 2, mouth_y, mouth_w, 10)
                pygame.draw.arc(surface, COLOR_PET_EYES, mouth_rect, 0, math.pi, 2)
            else:
                # Neutral mouth
                pygame.draw.line(surface, COLOR_PET_EYES, (cx - mouth_w // 2, mouth_y), (cx + mouth_w // 2, mouth_y), 2)


            # --- State Visuals ---
            if self.state == PetState.EATING:
                # Food item moving towards the pet (animation)
                food_x_start = cx + radius + 15
                food_x_end = cx + mouth_w + 5
                food_x = food_x_start - (food_x_start - food_x_end) * (self.action_timer / self.action_duration)
                pygame.draw.circle(surface, (255, 0, 0), (int(food_x), cy_body_center + radius * scale_y // 3), 3) 
            
            if self.state == PetState.PLAYING:
                # Bouncing hearts (animation)
                heart_font = pygame.font.Font(None, 20)
                heart_sym = heart_font.render("<3", True, (255, 100, 150))
                
                heart_y_offset = math.sin(self.play_bounce_timer * 0.5) * 5 

                surface.blit(heart_sym, heart_sym.get_rect(center=(cx - radius * 1.2, cy_body_center - radius * 1.5 + heart_y_offset)))
                surface.blit(heart_sym, heart_sym.get_rect(center=(cx + radius * 1.2, cy_body_center - radius * 1.5 - heart_y_offset)))
            
            if self.state == PetState.SICK:
                skull_font = pygame.font.Font(None, 40)
                sick_sym = skull_font.render("X", True, COLOR_SICK)
                surface.blit(sick_sym, sick_sym.get_rect(center=(cx, cy_body_center - body_h * 0.75)))


        # --- Action Feedback Overlay ---
        if self.action_feedback_timer > 0:
            feedback_surf = font.render(self.action_feedback_text, True, COLOR_HEALTH)
            surface.blit(feedback_surf, feedback_surf.get_rect(center=(cx, cy_body_center - body_h - 10)))