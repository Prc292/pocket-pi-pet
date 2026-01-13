import time
import math
import pygame
import random
import os
import datetime
import sqlite3
from models import PetState, PetStats
from constants import COLOR_PET_BODY, COLOR_PET_EYES, COLOR_HEALTH, COLOR_TEXT, COLOR_SICK, TIME_SCALE_FACTOR 

# --- EVOLUTION TIMES (in real seconds, scaled by TIME_SCALE_FACTOR) ---
TIME_TO_BABY_SEC = 10.0  # 90 game-seconds (90 / 10)
TIME_TO_CHILD_SEC = 17280.0 # 2 game-days (2 * 24 * 60 * 60 / 10)
TIME_TO_TEEN_SEC = 34560.0 # 4 game-days (4 * 24 * 60 * 60 / 10)
TIME_TO_ADULT_SEC = 60480.0 # 7 game-days (7 * 24 * 60 * 60 / 10)
class Pet:

    def __init__(self, db_manager, name="Pet", message_callback=None): 
        self.name = name
        self.db = db_manager # DatabaseManager instance
        self.stats = PetStats() 
        self.state = PetState.EGG
        self.life_stage = PetState.EGG
        self.message_callback = message_callback # Store the callback

        self.is_alive = True
        self.birth_time = time.time() 
        self.last_update = time.time()

        # Animation State (initialized before _load_sprites)
        self.play_bounce_timer = 0.0
        self.idle_bob_offset = 0.0
        self.crack_level = 0.0 # Egg cracking animation

        # Animation variables
        self.idle_animation_frames = []
        self.idle_frame_index = 0
        self.idle_animation_timer = 0
        self.idle_animation_speed = 0.1  # 100ms per frame

        self.blink_animation_frames = []
        self.blink_frame_index = 0
        self.blink_animation_timer = 0
        self.blink_animation_speed = 0.1  # 100ms per frame
        self.is_blinking = False
        self.blink_intervals = [1, 3, 6]
        self.shuffled_blink_intervals = self.blink_intervals.copy()
        random.shuffle(self.shuffled_blink_intervals)
        self.current_blink_interval_index = 0
        self.time_to_next_blink = self.shuffled_blink_intervals[self.current_blink_interval_index]

        self.sleep_animation_frames = []
        self.sleep_frame_index = 0
        self.sleep_animation_timer = 0
        self.sleep_animation_speed = 0.2  # 200ms per frame

        self._load_sprites()
        
        # For tracking previous stats to trigger low stat messages once
        self.prev_fullness = self.stats.fullness
        self.prev_happiness = self.stats.happiness
        self.prev_energy = self.stats.energy
        
        # Action feedback
        self.action_timer = 0.0
        self.action_duration = 3.0
        self.action_feedback_timer = 0.0
        self.action_feedback_text = ""

    def _load_sprites(self):
        base_path = os.path.dirname(__file__)
        self.sprite_idle = pygame.image.load(os.path.join(base_path, "assets", "sprites", "bobo_idle.png")).convert_alpha()
        self.sprite_blink = pygame.image.load(os.path.join(base_path, "assets", "sprites", "bobo_blink.png")).convert_alpha()
        self.sprite_sleeping = pygame.image.load(os.path.join(base_path, "assets", "sprites", "bobo_sleeping-sheet.png")).convert_alpha()

        # Parse spritesheets
        sprite_width = 64
        sprite_height = 64
        
        sheet_width_idle = self.sprite_idle.get_width()
        for x in range(0, sheet_width_idle, sprite_width):
            frame = self.sprite_idle.subsurface(pygame.Rect(x, 0, sprite_width, sprite_height))
            self.idle_animation_frames.append(frame)

        sheet_width_blink = self.sprite_blink.get_width()
        for x in range(0, sheet_width_blink, sprite_width):
            frame = self.sprite_blink.subsurface(pygame.Rect(x, 0, sprite_width, sprite_height))
            self.blink_animation_frames.append(frame)

        sheet_width_sleeping = self.sprite_sleeping.get_width()
        for x in range(0, sheet_width_sleeping, sprite_width):
            frame = self.sprite_sleeping.subsurface(pygame.Rect(x, 0, sprite_width, sprite_height))
            self.sleep_animation_frames.append(frame)
    
    def transition_to(self, new_state: PetState):
        if self.state != new_state:
            old_state = self.state
            print(f"Pet transitioning from {old_state.name} to {new_state.name}")
            self.state = new_state
            self.action_timer = 0.0 

            # Trigger messages for state changes
            if self.message_callback:
                if new_state == PetState.SLEEPING:
                    self.message_callback(f"{self.name} is now fast asleep.")
                elif old_state == PetState.SLEEPING and new_state == PetState.IDLE:
                    self.message_callback(f"{self.name} woke up! Good morning!")
                elif new_state == PetState.SICK:
                    self.message_callback(f"Oh no! {self.name} is feeling sick.")
                elif old_state == PetState.SICK and new_state == PetState.IDLE:
                    self.message_callback(f"{self.name} is feeling better!")
                elif new_state == PetState.DEAD:
                    self.message_callback(f"Alas, {self.name} has passed away...")
                elif new_state == PetState.IDLE and old_state == PetState.EGG: # Check old_state for hatching
                    self.message_callback(f"It's a {self.name}! Welcome to the world!")

    def handle_action_complete(self, action_name: str):

        
        if self.state == PetState.EATING:
            self.stats.fullness = self.stats.clamp(self.stats.fullness + 20)
            self.stats.health = self.stats.clamp(self.stats.health + 5)
            if self.message_callback: self.message_callback({"text": f"{self.name} enjoyed the meal! Fullness +20, Health +5.", "notify": False})
        elif self.state == PetState.PLAYING:
            self.stats.happiness = self.stats.clamp(self.stats.happiness + 30)
            self.stats.energy = self.stats.clamp(self.stats.energy - 10)
            if self.message_callback: self.message_callback({"text": f"{self.name} had a blast! Happiness +30, Energy -10.", "notify": False})
        elif self.state == PetState.TRAINING:
            self.stats.discipline = self.stats.clamp(self.stats.discipline + 15)
            self.stats.happiness = self.stats.clamp(self.stats.happiness - 5) # Training can be tiring
            if self.message_callback: self.message_callback({"text": f"{self.name} learned something new! Discipline +15, Happiness -5.", "notify": False})
        
        self.transition_to(PetState.IDLE)
        
    def heal(self):
        if self.state == PetState.SICK:
            if self.stats.discipline >= 10:
                self.stats.health = self.stats.clamp(self.stats.health + 20)
                self.stats.discipline = self.stats.clamp(self.stats.discipline - 10)
                if self.message_callback: self.message_callback({"text": f"{self.name} is feeling much better! Health +20.", "notify": False})
                self.transition_to(PetState.IDLE)
            else:
                if self.message_callback: self.message_callback({"text": f"{self.name} needs more discipline to accept treatment.", "notify": False})


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
        
        # Trigger messages for low stats
        if self.message_callback:
            if self.stats.fullness < 20 and self.prev_fullness >= 20:
                self.message_callback(f"{self.name} is feeling very hungry!")
            if self.stats.happiness < 20 and self.prev_happiness >= 20:
                self.message_callback(f"{self.name} is feeling lonely.")
            if self.stats.energy < 20 and self.prev_energy >= 20:
                self.message_callback(f"{self.name} is very tired.")
        
        self.prev_fullness = self.stats.fullness
        self.prev_happiness = self.stats.happiness
        self.prev_energy = self.stats.energy
        
        # 3. Handle Animation Timers (Use real dt for smooth visuals)

        # Update idle animation
        if not self.is_blinking:
            self.idle_animation_timer += dt
            if self.idle_animation_timer >= self.idle_animation_speed:
                self.idle_animation_timer = 0
                self.idle_frame_index = (self.idle_frame_index + 1) % len(self.idle_animation_frames)

        # Blinking logic
        if self.state != PetState.SLEEPING:
            if not self.is_blinking:
                self.time_to_next_blink -= dt
                if self.time_to_next_blink <= 0:
                    self.is_blinking = True
                    self.blink_animation_timer = 0
            else:
                self.blink_animation_timer += dt
                if self.blink_animation_timer >= self.blink_animation_speed:
                    self.blink_animation_timer = 0
                    self.blink_frame_index += 1
                    if self.blink_frame_index >= len(self.blink_animation_frames):
                        self.is_blinking = False
                        self.blink_frame_index = 0
                        self.current_blink_interval_index += 1
                        if self.current_blink_interval_index >= len(self.shuffled_blink_intervals):
                            random.shuffle(self.shuffled_blink_intervals)
                            self.current_blink_interval_index = 0
                        self.time_to_next_blink = self.shuffled_blink_intervals[self.current_blink_interval_index]
        elif self.state == PetState.SLEEPING:
            self.sleep_animation_timer += dt
            if self.sleep_animation_timer >= self.sleep_animation_speed:
                self.sleep_animation_timer = 0
                self.sleep_frame_index = (self.sleep_frame_index + 1) % len(self.sleep_animation_frames)

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
            if self.message_callback: self.message_callback(f"Congratulations! {self.name} has hatched into a Baby!")
            self.save() # Ensure the life stage change is saved
        elif self.life_stage == PetState.BABY and total_game_time > TIME_TO_CHILD_SEC:
            self.life_stage = PetState.CHILD
            self.transition_to(PetState.IDLE)
            if self.message_callback: self.message_callback(f"{self.name} has grown into a Child!")
        elif self.life_stage == PetState.CHILD and total_game_time > TIME_TO_TEEN_SEC:
            if self.stats.care_mistakes < 3 and self.stats.discipline > 50:
                self.life_stage = PetState.TEEN_GOOD
                if self.message_callback: self.message_callback(f"{self.name} evolved into a well-behaved Teen!")
            else:
                self.life_stage = PetState.TEEN_BAD
                if self.message_callback: self.message_callback(f"{self.name} evolved into a rebellious Teen...")
            self.transition_to(PetState.IDLE)
        elif self.life_stage in [PetState.TEEN_GOOD, PetState.TEEN_BAD] and total_game_time > TIME_TO_ADULT_SEC:
            if self.stats.care_mistakes < 5 and self.stats.happiness > 75:
                self.life_stage = PetState.ADULT_GOOD
                if self.message_callback: self.message_callback(f"Amazing! {self.name} is now a thriving Adult!")
            else:
                self.life_stage = PetState.ADULT_BAD
                if self.message_callback: self.message_callback(f"{self.name} has reached adulthood, but seems a bit rough around the edges.")
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
                if len(row) > 13:
                    self.stats.coins = row[13]
            
            # Initial message after loading
            if self.message_callback:
                self.message_callback(f"Welcome back! {self.name} is {self.life_stage.name.lower()}.")

        except sqlite3.Error as e:
            print(f"Error loading pet: {e}. Initializing new pet.")
            self.stats = PetStats() 
            self.state = PetState.EGG
            self.life_stage = PetState.EGG
            self.birth_time = time.time()
            self.last_update = time.time()
            if self.message_callback: self.message_callback(f"A new {self.name} egg has appeared!")

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
            'name': self.name,
            'coins': self.stats.coins
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
        egg_colour = (245, 245, 210)
        crack_colour = (100, 80, 50)
        
        # Base egg shape
        egg_rect = pygame.Rect(cx - radius, cy - radius * 1.5, radius * 2, radius * 3)
        pygame.draw.ellipse(surface, egg_colour, egg_rect)

        # Main crack line (grows with crack_level)
        if crack_level > 0:
            # Crack from top-ish to bottom-ish
            start_x = cx + (radius * 0.2 * math.sin(crack_level * math.pi * 2))
            start_y = cy - radius * (1.2 - crack_level * 0.5) 
            end_x = cx + (radius * 0.3 * math.sin(crack_level * math.pi * 3 + math.pi/2))
            end_y = cy + radius * (1.2 - (1-crack_level) * 0.5)
            pygame.draw.line(surface, crack_colour, (start_x, start_y), (end_x, end_y), 2)
            
            # Branches for the crack
            if crack_level > 0.3:
                branch1_x = start_x + (end_x - start_x) * 0.3
                branch1_y = start_y + (end_y - start_y) * 0.3
                pygame.draw.line(surface, crack_colour, (branch1_x, branch1_y), (branch1_x - radius * 0.5 * crack_level, branch1_y - radius * 0.2 * crack_level), 2)
            
            if crack_level > 0.6:
                branch2_x = start_x + (end_x - start_x) * 0.7
                branch2_y = start_y + (end_y - start_y) * 0.7
                pygame.draw.line(surface, crack_colour, (branch2_x, branch2_y), (branch2_x + radius * 0.4 * crack_level, branch2_y - radius * 0.3 * crack_level), 2)
        
    def draw(self, surface, cx, cy, font):
        """Draws the pet, applying visual modifications based on state and health."""


        # --- Handle DEAD/EGG State (Early Exit) ---
        if self.state == PetState.DEAD:
            dead_colour = (80, 80, 80)
            # Use a generic sprite size for positioning purposes, e.g., 64x64
            # This is a placeholder since the pet is dead and just displays text
            dead_sprite_width = 64
            dead_sprite_height = 64
            pygame.draw.ellipse(surface, dead_colour, (cx - dead_sprite_width // 2, cy - dead_sprite_height // 4 + 10, dead_sprite_width, dead_sprite_height // 2))
            dead_text = font.render("REST IN PEACE", False, (255, 0, 0))
            text_rect = dead_text.get_rect(center=(cx, cy))
            surface.blit(dead_text, text_rect)
            return
        
        if self.life_stage == PetState.EGG:
            time_elapsed_game = (time.time() - self.birth_time) * TIME_SCALE_FACTOR
            self.crack_level = min(1.0, time_elapsed_game / TIME_TO_BABY_SEC)
            
            # For egg drawing, we still use procedural shapes
            egg_radius = 20 # fixed size for egg
            self._draw_egg_crack(surface, cx, cy, egg_radius, self.crack_level)
            
            time_left = max(0, int(TIME_TO_BABY_SEC - time_elapsed_game))
            minutes = time_left // 60
            seconds = time_left % 60
            time_str = f"{minutes:02d}:{seconds:02d}"

            egg_text = font.render(time_str, False, COLOR_TEXT)
            # Position the text to the left of the egg
            text_rect = egg_text.get_rect(midright=(cx - egg_radius - 10, cy))
            surface.blit(egg_text, text_rect)
            return # Ensure nothing else is drawn when in EGG state
        
        # For all other states, draw the current pet sprite (idle or blinking)
        current_sprite_frame = None
        if self.state == PetState.SLEEPING:
            current_sprite_frame = self.sleep_animation_frames[self.sleep_frame_index]
        elif self.is_blinking:
            current_sprite_frame = self.blink_animation_frames[self.blink_frame_index]
        else:
            current_sprite_frame = self.idle_animation_frames[self.idle_frame_index]
        
        # Apply idle bobbing animation to the sprite's position
        sprite_center_y = cy
        sprite_rect = current_sprite_frame.get_rect(center=(cx, sprite_center_y))
        surface.blit(current_sprite_frame, sprite_rect)
        
        # --- Action Feedback Overlay ---