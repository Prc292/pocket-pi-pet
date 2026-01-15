import pygame
import time
import random
import os
import json
from typing import Callable

from models import PetState, PetStats, PetAnimations
from database import DatabaseManager
from constants import (
    SCREEN_WIDTH, TIME_SCALE_FACTOR, TIME_TO_BABY_SEC, TIME_TO_CHILD_SEC,
    TIME_TO_TEEN_SEC, TIME_TO_ADULT_SEC, COLOR_TEXT
)

class AnimationManager:
    """Manages animations for the pet"""
    def __init__(self):
        self.animations = {}
        self.current_animation = PetAnimations.IDLE
        self.current_frame = 0
        self.animation_timer = 0.0
        self.frame_duration = 0.1 # Default frame duration
        self.loop = True

    def add_animation(self, name: PetAnimations, frames: list, frame_duration: float = 0.1, loop: bool = True):
        self.animations[name] = {"frames": frames, "frame_duration": frame_duration, "loop": loop}

    def set_animation(self, name: PetAnimations):
        if self.current_animation != name and name in self.animations:
            self.current_animation = name
            self.current_frame = 0
            self.animation_timer = 0.0
            self.frame_duration = self.animations[name].get("frame_duration", 0.1)
            self.loop = self.animations[name].get("loop", True)

    def update(self, dt: float):
        if self.current_animation not in self.animations:
            return

        self.animation_timer += dt
        if self.animation_timer >= self.frame_duration:
            self.animation_timer = 0
            if self.loop:
                self.current_frame = (self.current_frame + 1) % len(self.animations[self.current_animation]["frames"])
            else:
                self.current_frame = min(self.current_frame + 1, len(self.animations[self.current_animation]["frames"]) - 1)


    def get_current_frame(self) -> pygame.Surface:
        if self.current_animation not in self.animations or not self.animations[self.current_animation]["frames"]:
            return None
        return self.animations[self.current_animation]["frames"][self.current_frame]

    def reset_animation(self):
        self.current_frame = 0
        self.animation_timer = 0.0
    
    def is_animation_complete(self) -> bool:
        return not self.loop and self.current_frame == len(self.animations[self.current_animation]["frames"]) - 1

class Pet:
    def __init__(self, db: DatabaseManager, name: str, message_callback: Callable, initial_x: int, initial_y: int):
        self.name = name
        self.db = db
        self.message_callback = message_callback
        
        self.stats = PetStats()
        self.state = PetState.IDLE
        self.animation_manager = AnimationManager()
        self.birth_time = time.time() # This needs to be set on initialization, and loaded from DB
        self.last_update = time.time()
        self.life_stage = PetState.EGG # Initial life stage
        self.is_alive = True # Initial state

        self.action_timer = 0.0 # Timer for actions like eating, playing
        self.action_duration = 2.0 # Default duration for actions

        self.x = initial_x
        self.y = initial_y
        self.move_speed = 200 # pixels per second
        
        # Physics variables for movement
        self.velocity_x = 0.0
        self.velocity_y = 0.0
        self.acceleration_x = 1000.0 # pixels/second^2
        self.gravity = 1500.0 # pixels/second^2
        self.jump_strength = 600.0 # initial upward velocity
        self.max_speed_x = 300.0 # max horizontal speed
        self.friction_x = 800.0 # deceleration when not accelerating
        self.on_ground = False # Is the pet currently on a platform?

        # Movement state for input handling
        self.is_moving_left = False
        self.is_moving_right = False
        
        # Blink logic using animation manager
        self.next_blink_time = time.time() + random.uniform(2.0, 5.0)

        # Store previous stats for flashing UI.
        self.prev_fullness = 0
        self.prev_happiness = 0
        self.prev_energy = 0

        self._load_animations()
        self.animation_manager.set_animation(PetAnimations.IDLE)


    def _load_animations(self):
        base_path = os.path.dirname(__file__)
        sprites_dir = os.path.join(base_path, "assets", "sprites")

        # Helper to load spritesheet frames
        def _load_spritesheet_frames(sheet_path, json_path):
            if not os.path.exists(sheet_path) or not os.path.exists(json_path):
                return []
            spritesheet = pygame.image.load(sheet_path).convert_alpha()
            with open(json_path, 'r') as f:
                sprite_data = json.load(f)
            
            frames = []
            
            if "meta" in sprite_data and "slices" in sprite_data["meta"] and sprite_data["meta"]["slices"]:
                # Prioritize 'slices' for animations if they exist (like Aseprite slices)
                # Sort slices by their x-position to ensure correct animation order
                sorted_slices = sorted(sprite_data["meta"]["slices"], key=lambda s: s["keys"][0]["bounds"]["x"])
                for slice_data in sorted_slices:
                    bounds = slice_data["keys"][0]["bounds"]
                    x, y, w, h = bounds["x"], bounds["y"], bounds["w"], bounds["h"]
                    frames.append(spritesheet.subsurface(pygame.Rect(x, y, w, h)))
            elif "frames" in sprite_data:
                # Fallback to 'frames' if 'slices' are not present or empty
                frame_keys = sprite_data["frames"].keys()
                
                def try_numeric_sort_key(frame_name):
                    try:
                        base_name = os.path.splitext(frame_name)[0]
                        parts = base_name.split('_')
                        if len(parts) > 1 and parts[-1].isdigit():
                            return int(parts[-1])
                        parts = base_name.split(' ')
                        if len(parts) > 1 and parts[-1].isdigit():
                            return int(parts[-1])
                        return frame_name
                    except ValueError:
                        return frame_name

                sorted_frame_names = sorted(frame_keys, key=try_numeric_sort_key)

                for frame_name in sorted_frame_names:
                    frame = sprite_data["frames"][frame_name]["frame"]
                    x, y, w, h = frame['x'], frame['y'], frame['w'], frame['h']
                    frames.append(spritesheet.subsurface(pygame.Rect(x, y, w, h)))
            return frames

        # Load Idle animation
        bobo_idle_path = os.path.join(sprites_dir, "bobo_idle.png")
        if os.path.exists(bobo_idle_path):
            self.animation_manager.add_animation(PetAnimations.IDLE, [pygame.image.load(bobo_idle_path).convert_alpha()])
        
        # Load Sleep animation
        bobo_sleeping_sheet_path = os.path.join(sprites_dir, "bobo_sleeping.png")
        bobo_sleeping_json_path = os.path.join(sprites_dir, "bobo_sleeping.json")
        sleeping_frames = _load_spritesheet_frames(bobo_sleeping_sheet_path, bobo_sleeping_json_path)
        if sleeping_frames:
            self.animation_manager.add_animation(PetAnimations.SLEEPING, sleeping_frames, frame_duration=0.2)

        # Load Blink animation
        bobo_blink_sheet_path = os.path.join(sprites_dir, "bobo_blink.png")
        bobo_blink_json_path = os.path.join(sprites_dir, "bobo_blink.json")
        blink_frames = _load_spritesheet_frames(bobo_blink_sheet_path, bobo_blink_json_path)
        if blink_frames:
            self.animation_manager.add_animation(PetAnimations.BLINK, blink_frames, frame_duration=0.1, loop=False)

        # Load Jump animation
        bobo_jump_sheet_path = os.path.join(sprites_dir, "bobo_jump.png")
        bobo_jump_json_path = os.path.join(sprites_dir, "bobo_jump.json")
        jump_frames = _load_spritesheet_frames(bobo_jump_sheet_path, bobo_jump_json_path)
        if jump_frames:
            self.animation_manager.add_animation(PetAnimations.JUMP, jump_frames, frame_duration=0.08, loop=False)


    def move_left(self, dt):
        """Move pet left with frame-rate independent physics"""
        self.velocity_x -= self.acceleration_x * dt
        self.is_moving_left = True

    def move_right(self, dt):
        """Move pet right with frame-rate independent physics"""
        self.velocity_x += self.acceleration_x * dt
        self.is_moving_right = True

    def jump(self):
        if self.on_ground:
            self.velocity_y = -self.jump_strength
            self.on_ground = False # Immediately set to false to prevent double jump
            self.animation_manager.set_animation(PetAnimations.JUMP)
    
    def transition_to(self, new_state: PetState):
        if self.state != new_state:
            old_state = self.state
            print(f"Pet transitioning from {old_state.name} to {new_state.name}")
            self.state = new_state
            self.action_timer = 0.0 

            # Set animation based on new state
            if self.state == PetState.SLEEPING:
                self.animation_manager.set_animation(PetAnimations.SLEEPING)
            elif self.state == PetState.IDLE:
                self.animation_manager.set_animation(PetAnimations.IDLE)
            # For other states, animation might be handled by action functions or jump animation

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
                elif new_state == PetState.IDLE and old_state == PetState.EGG:
                    self.message_callback(f"It's a {self.name}! Welcome to the world!")

    def handle_action_complete(self, action_name: str):

        
        if self.state == PetState.EATING:
            self.stats.fullness = self.stats.clamp(self.stats.fullness + 20)
            self.stats.health = self.stats.clamp(self.stats.health + 5)
            if self.message_callback:
                self.message_callback({"text": f"{self.name} enjoyed the meal! Fullness +20, Health +5.", "notify": False})
        elif self.state == PetState.PLAYING:
            self.stats.happiness = self.stats.clamp(self.stats.happiness + 30)
            self.stats.energy = self.stats.clamp(self.stats.energy - 10)
            if self.message_callback:
                self.message_callback({"text": f"{self.name} had a blast! Happiness +30, Energy -10.", "notify": False})
        elif self.state == PetState.TRAINING:
            self.stats.discipline = self.stats.clamp(self.stats.discipline + 15)
            self.stats.happiness = self.stats.clamp(self.stats.happiness - 5) # Training can be tiring
            if self.message_callback:
                self.message_callback({"text": f"{self.name} learned something new! Discipline +15, Happiness -5.", "notify": False})
        
        self.transition_to(PetState.IDLE)
        
    def heal(self):
        if self.state == PetState.SICK:
            if self.stats.discipline >= 10:
                self.stats.health = self.stats.clamp(self.stats.health + 20)
                self.stats.discipline = self.stats.clamp(self.stats.discipline - 10)
                if self.message_callback:
                    self.message_callback({"text": f"{self.name} is feeling much better! Health +20.", "notify": False})
                self.transition_to(PetState.IDLE)
            else:
                if self.message_callback:
                    self.message_callback({"text": f"{self.name} needs more discipline to accept treatment.", "notify": False})


    def update(self, dt, current_hour, platforms=None): # Added platforms parameter
        """Handles real-time stat decay, action timers, and evolution checks, plus physics."""

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
            if self.stats.fullness < 20 and self.prev_fullness >= 20: # Added prev_fullness for checking state change
                self.message_callback(f"{self.name} is feeling very hungry!")
            if self.stats.happiness < 20 and self.prev_happiness >= 20:
                self.message_callback(f"{self.name} is feeling lonely.")
            if self.stats.energy < 20 and self.prev_energy >= 20:
                self.message_callback(f"{self.name} is very tired.")
        
        self.prev_fullness = self.stats.fullness
        self.prev_happiness = self.stats.happiness
        self.prev_energy = self.stats.energy
        
        # --- Physics Update (Movement, Gravity, Collisions) ---

        # Apply horizontal acceleration based on input flags
        if self.is_moving_left:
            self.velocity_x -= self.acceleration_x * dt
        elif self.is_moving_right:
            self.velocity_x += self.acceleration_x * dt
        else:
            # Apply friction
            if self.velocity_x > 0:
                self.velocity_x = max(0, self.velocity_x - self.friction_x * dt)
            elif self.velocity_x < 0:
                self.velocity_x = min(0, self.velocity_x + self.friction_x * dt)

        # Clamp horizontal velocity
        self.velocity_x = max(-self.max_speed_x, min(self.max_speed_x, self.velocity_x))

        # Apply gravity
        self.velocity_y += self.gravity * dt

        # Update position
        self.x += self.velocity_x * dt
        self.y += self.velocity_y * dt

        # Determine current sprite size for collision
        pet_width = 64
        pet_height = 64
        current_frame = self.animation_manager.get_current_frame()
        if current_frame:
            pet_width = current_frame.get_width()
            pet_height = current_frame.get_height()

        # Screen bounds
        self.x = max(pet_width // 2, min(SCREEN_WIDTH - pet_width // 2, self.x))

        # Collision with platforms (bottom-center reference)
        self.on_ground = False
        if platforms:
            for platform in platforms:
                if self.velocity_y >= 0:  # Only check falling down
                    pet_bottom = self.y
                    pet_top = self.y - pet_height
                    pet_left = self.x - pet_width // 2
                    pet_right = self.x + pet_width // 2
                    if (pet_right > platform.left and pet_left < platform.right and
                        pet_bottom >= platform.top and pet_top < platform.top):
                        self.y = platform.top
                        self.velocity_y = 0
                        self.on_ground = True
                        break

        # Fallback to bottom of screen
        if not self.on_ground and self.y > 600:
            self.y = 600
            self.velocity_y = 0
            self.on_ground = True

        # Reset movement flags
        self.is_moving_left = False
        self.is_moving_right = False


        # 4. Handle Animation Timers (uses updated physics position)
        self.animation_manager.update(dt)

        # Handle non-looping animations (e.g., jump, blink)
        if self.animation_manager.current_animation == PetAnimations.JUMP and self.animation_manager.is_animation_complete():
            self.animation_manager.set_animation(PetAnimations.IDLE)
        
        # Blinking logic (independent of pet state)
        if self.animation_manager.current_animation == PetAnimations.IDLE:
            if time.time() > self.next_blink_time:
                self.animation_manager.set_animation(PetAnimations.BLINK)
                self.next_blink_time = time.time() + random.uniform(2.0, 5.0) # Schedule next blink
        elif self.animation_manager.current_animation == PetAnimations.BLINK and self.animation_manager.is_animation_complete():
            self.animation_manager.set_animation(PetAnimations.IDLE) # Return to idle after blink

        # 5. State Checks and Evolution
        
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
            if self.message_callback:
                self.message_callback(f"Congratulations! {self.name} has hatched into a Baby!")
            self.save() # Ensure the life stage change is saved
        elif self.life_stage == PetState.BABY and total_game_time > TIME_TO_CHILD_SEC:
            self.life_stage = PetState.CHILD
            self.transition_to(PetState.IDLE)
            if self.message_callback:
                self.message_callback(f"{self.name} has grown into a Child!")
        elif self.life_stage == PetState.CHILD and total_game_time > TIME_TO_TEEN_SEC:
            if self.stats.care_mistakes < 3 and self.stats.discipline > 50:
                self.life_stage = PetState.TEEN_GOOD
                if self.message_callback:
                    self.message_callback(f"Congratulations! {self.name} evolved into a well-behaved Teen!")
            else:
                self.life_stage = PetState.TEEN_BAD
                if self.message_callback:
                    self.message_callback(f"{self.name} evolved into a rebellious Teen...")
            self.transition_to(PetState.IDLE)
        elif self.life_stage in [PetState.TEEN_GOOD, PetState.TEEN_BAD] and total_game_time > TIME_TO_ADULT_SEC:
            if self.stats.care_mistakes < 5 and self.stats.happiness > 75:
                self.life_stage = PetState.ADULT_GOOD
                if self.message_callback:
                    self.message_callback(f"Amazing! {self.name} is now a thriving Adult!")
            else:
                self.life_stage = PetState.ADULT_BAD
                if self.message_callback:
                    self.message_callback(f"{self.name} has reached adulthood, but seems a bit rough around the edges.")
            self.transition_to(PetState.IDLE)


        # 6. Save state every few seconds
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

        except Exception as e: # Catch generic exception as sqlite3.Error might not catch all
            print(f"Error loading pet: {e}. Initializing new pet.")
            self.stats = PetStats() 
            self.state = PetState.EGG
            self.life_stage = PetState.EGG
            self.birth_time = time.time()
            self.last_update = time.time()
            if self.message_callback:
                self.message_callback(f"A new {self.name} egg has appeared!")

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
    
    def start_jump_animation(self):
        """Triggers the jump animation."""
        if self.animation_manager.current_animation != PetAnimations.JUMP:
            self.animation_manager.set_animation(PetAnimations.JUMP)
    
    # --- Drawing Logic ---
    def draw(self, surface: pygame.Surface, font: pygame.font.Font):
        """Draws the pet, applying visual modifications based on state and health."""

        # --- Handle DEAD/EGG State (Early Exit) ---
        if self.state == PetState.DEAD:
            dead_colour = (80, 80, 80)
            # Placeholder for dead pet
            pygame.draw.rect(surface, dead_colour, (self.x - 32, self.y - 32, 64, 64))
            dead_text = font.render("REST IN PEACE", False, (255, 0, 0))
            text_rect = dead_text.get_rect(center=(self.x, self.y + 40))
            surface.blit(dead_text, text_rect)
            return
        
        if self.life_stage == PetState.EGG:
            time_elapsed_game = (time.time() - self.birth_time) * TIME_SCALE_FACTOR
            crack_level = min(1.0, time_elapsed_game / TIME_TO_BABY_SEC)
            
            # Simple egg placeholder
            egg_color = (245, 245, 210)
            pygame.draw.ellipse(surface, egg_color, (self.x - 30, self.y - 50, 60, 80))
            # Draw crack lines based on crack_level (simplified)
            if crack_level > 0.3:
                pygame.draw.line(surface, (100, 80, 50), (self.x - 20, self.y - 20), (self.x + 20, self.y - 10), 2)
            if crack_level > 0.6:
                pygame.draw.line(surface, (100, 80, 50), (self.x - 10, self.y + 10), (self.x + 10, self.y + 20), 2)
            
            time_left = max(0, int(TIME_TO_BABY_SEC - time_elapsed_game))
            minutes = time_left // 60
            seconds = time_left % 60
            time_str = f"{minutes:02d}:{seconds:02d}"

            egg_text = font.render(time_str, False, COLOR_TEXT)
            text_rect = egg_text.get_rect(midright=(self.x - 40, self.y))
            surface.blit(egg_text, text_rect)
            return # Ensure nothing else is drawn when in EGG state
        
        # Get current sprite frame from AnimationManager
        current_sprite_frame = self.animation_manager.get_current_frame()
        
        if current_sprite_frame:
            sprite_rect = current_sprite_frame.get_rect(midbottom=(self.x, self.y))
            surface.blit(current_sprite_frame, sprite_rect)
        
        # --- Action Feedback Overlay ---
        # (This part of the original code was for displaying specific action feedback)
        # I'll assume this is handled by the message bubble in main.py for now.
        # Original code here included drawing hearts, bubbles, etc.
        # This can be re-added later if needed.