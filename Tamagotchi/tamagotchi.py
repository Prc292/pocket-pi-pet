import os
import sys
import time
import sqlite3
import pygame
import math
import platform
from enum import Enum, auto
from dataclasses import dataclass

# --- CONFIGURATION ---
SCREEN_WIDTH = 480
SCREEN_HEIGHT = 320
FPS = 30
DB_FILE = "pet_life.db"

# Retro UI Palette
COLOR_BG = (40, 44, 52)
COLOR_PET_BODY = (171, 220, 255)
COLOR_PET_EYES = (33, 37, 43)
COLOR_UI_BAR_BG = (62, 68, 81)
COLOR_HEALTH = (152, 195, 121)
COLOR_HUNGER = (224, 108, 117)
COLOR_HAPPY = (229, 192, 123)
COLOR_ENERGY = (97, 175, 239)

# --- 1. DATABASE MANAGER ---
class DatabaseManager:
    """Handles all SQL operations to keep the pet 'alive' on disk."""
    def __init__(self, db_path):
        self.conn = sqlite3.connect(db_path)
        self.create_tables()

    def create_tables(self):
        """
        Creates the schema. Column Mapping:
        0: id, 1: hunger, 2: happiness, 3: energy, 4: health,
        5: is_alive, 6: birth_time, 7: last_update, 8: life_stage, 9: state
        """
        query = """
        CREATE TABLE IF NOT EXISTS pet_stats (
            id INTEGER PRIMARY KEY,
            hunger REAL, happiness REAL, energy REAL, health REAL,
            is_alive INTEGER, birth_time REAL, last_update REAL,
            life_stage TEXT, state TEXT
        )
        """
        self.conn.execute(query)
        self.conn.commit()

    def save_pet(self, pet_data):
        query = """
        INSERT OR REPLACE INTO pet_stats 
        (id, hunger, happiness, energy, health, is_alive, birth_time, last_update, life_stage, state)
        VALUES (1,?,?,?,?,?,?,?,?,?)
        """
        self.conn.execute(query, (
            pet_data['hunger'], pet_data['happiness'], pet_data['energy'], pet_data['health'],
            1 if pet_data['is_alive'] else 0, pet_data['birth_time'], time.time(),
            pet_data['life_stage'], pet_data['state']
        ))
        self.conn.commit()

    def load_pet(self):
        cursor = self.conn.execute("SELECT * FROM pet_stats WHERE id = 1")
        return cursor.fetchone()

# --- 2. FINITE STATE MACHINE ---
class PetState(Enum):
    """Enforces valid states and prevents 'illegal' transitions."""
    EGG = auto()
    BABY = auto()
    IDLE = auto()
    EATING = auto()
    SLEEPING = auto()
    DEAD = auto()

@dataclass
class PetStats:
    hunger: float = 50.0  # 0 = Full, 100 = Starving
    happiness: float = 100.0
    energy: float = 100.0
    health: float = 100.0

    def clamp(self, value):
        return max(0.0, min(100.0, value))

    def tick(self, dt: float, current_state: PetState):
        """Calculates decay based on elapsed time and current state."""
        # Hunger increases faster if active
        hunger_rate = 8.0 if current_state!= PetState.SLEEPING else 2.0
        self.hunger = self.clamp(self.hunger + (hunger_rate / 3600.0) * dt)
        
        # Energy recovery while sleeping, drain while awake
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

class Pet:
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
        if self.state == PetState.DEAD:
            return

        now = time.time()
        dt = now - self.last_update
        self.last_update = now
        self.state_timer += 0.05 

        # Stage Check: Hatching
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
        """Procedural drawing system using math for state-based animations."""
        t = self.state_timer
        
        # 1. State-Specific Motion Logic
        if self.state == PetState.SLEEPING:
            bob = 5 * math.sin(t * 1.5)  # Slow breathing
            eye_closed = True
        elif self.state == PetState.DEAD:
            pygame.draw.circle(screen, (80, 80, 80), (cx, cy), 45)
            return
        else:
            bob = 10 * abs(math.sin(t * 4)) # Active bouncing
            eye_closed = (pygame.time.get_ticks() // 100) % 30 == 0 # Natural blinking

        # 2. Body Drawing with Squash & Stretch
        body_width = 45 + (2 * math.sin(t * 4))
        body_height = 45 - (2 * math.sin(t * 4))
        pygame.draw.ellipse(screen, COLOR_PET_BODY, (cx - body_width, cy + bob - body_height, body_width*2, body_height*2))
        
        # 3. Draw Eyes
        eye_y = cy + bob - 10
        if eye_closed or self.state == PetState.SLEEPING:
            pygame.draw.line(screen, COLOR_PET_EYES, (cx-15, eye_y), (cx-5, eye_y), 2)
            pygame.draw.line(screen, COLOR_PET_EYES, (cx+5, eye_y), (cx+15, eye_y), 2)
        else:
            pygame.draw.circle(screen, COLOR_PET_EYES, (cx-12, eye_y), 4)
            pygame.draw.circle(screen, COLOR_PET_EYES, (cx+12, eye_y), 4)

        # 4. Draw Mouth (Mood-based)
        mouth_y = cy + bob + 12
        if self.state == PetState.EATING:
            mouth_size = 6 + (4 * math.sin(t * 10))
            pygame.draw.circle(screen, (0, 0, 0), (cx, mouth_y), mouth_size)
        else:
            happiness = self.stats.happiness
            if happiness > 70:
                pygame.draw.arc(screen, (0, 0, 0), (cx-10, mouth_y-5, 20, 10), math.pi, 2*math.pi, 2)
            elif happiness < 30:
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
            # Map columns correctly (indices 1-9)
            self.stats.hunger = row[1]
            self.stats.happiness = row[2]
            self.stats.energy = row[3]
            self.stats.health = row[4]
            self.is_alive = bool(row[5])
            self.birth_time = row[6]
            self.last_update = row[7]
            self.life_stage = row[8]
            self.state = PetState[row[9]]
            
            # Offline Catch-up Logic
            offline_dt = time.time() - row[7]
            self.stats.tick(offline_dt, self.state)
            self.last_update = time.time()

# --- 3. GAME ENGINE ---
class GameEngine:
    def __init__(self):
        pygame.init()
        if platform.system() == "Linux":
            os.environ = "kmsdrm"
            self.screen = pygame.display.set_mode((SCREEN_WIDTH, SCREEN_HEIGHT), pygame.FULLSCREEN)
        else:
            self.screen = pygame.display.set_mode((SCREEN_WIDTH, SCREEN_HEIGHT), pygame.SCALED | pygame.RESIZABLE)
            
        self.clock = pygame.time.Clock()
        self.font = pygame.font.Font(None, 22)
        
        self.db = DatabaseManager(DB_FILE)
        self.pet = Pet(self.db)
        self.pet.load()

        # UI Hitboxes
        self.btn_feed = pygame.Rect(20, 250, 100, 40)
        self.btn_play = pygame.Rect(135, 250, 100, 40)
        self.btn_sleep = pygame.Rect(250, 250, 100, 40)
        self.btn_quit = pygame.Rect(365, 250, 100, 40)

    def draw_bar(self, x, y, value, color, label):
        self.screen.blit(self.font.render(label, True, (171, 178, 191)), (x, y - 18))
        pygame.draw.rect(self.screen, COLOR_UI_BAR_BG, (x, y, 100, 12), border_radius=6)
        if value > 5:
            pygame.draw.rect(self.screen, color, (x, y, int(value), 12), border_radius=6)

    def run(self):
        running = True
        while running:
            for event in pygame.event.get():
                if event.type == pygame.QUIT: running = False
                if event.type == pygame.MOUSEBUTTONDOWN:
                    if self.btn_feed.collidepoint(event.pos) and self.pet.is_alive:
                        self.pet.stats.hunger = self.pet.stats.clamp(self.pet.stats.hunger - 20)
                        self.pet.transition_to(PetState.EATING)
                    elif self.btn_play.collidepoint(event.pos) and self.pet.is_alive:
                        self.pet.stats.happiness = self.pet.stats.clamp(self.pet.stats.happiness + 20)
                        self.pet.stats.energy = self.pet.stats.clamp(self.pet.stats.energy - 10)
                        self.pet.stats.hunger = self.pet.stats.clamp(self.pet.stats.hunger + 5.0)
                    elif self.btn_sleep.collidepoint(event.pos) and self.pet.is_alive:
                        new_state = PetState.IDLE if self.pet.state == PetState.SLEEPING else PetState.SLEEPING
                        self.pet.transition_to(new_state)
                    elif self.btn_quit.collidepoint(event.pos): running = False

            self.pet.update()
            
            # Reset Eating state automatically
            if self.pet.state == PetState.EATING and self.pet.state_timer > 3.0:
                self.pet.transition_to(PetState.IDLE)

            # RENDER
            self.screen.fill(COLOR_BG)
            self.draw_bar(20, 35, self.pet.stats.health, COLOR_HEALTH, "HEALTH")
            self.draw_bar(135, 35, 100 - self.pet.stats.hunger, COLOR_HUNGER, "FULLNESS")
            self.draw_bar(250, 35, self.pet.stats.happiness, COLOR_HAPPY, "HAPPY")
            self.draw_bar(365, 35, self.pet.stats.energy, COLOR_ENERGY, "ENERGY")

            cx, cy = SCREEN_WIDTH // 2, 160
            if self.pet.life_stage == "EGG":
                pygame.draw.ellipse(self.screen, (245, 245, 210), (cx-25, cy-35, 50, 70))
            else:
                self.pet.draw(self.screen, cx, cy)

            # Dynamic Buttons
            buttons = [
                (self.btn_feed, "FEED"),
                (self.btn_play, "PLAY"),
                (self.btn_sleep, "SLEEP" if self.pet.state != PetState.SLEEPING else "WAKE"),
                (self.btn_quit, "QUIT")
            ]
            for rect, txt in buttons:
                pygame.draw.rect(self.screen, (100, 100, 100), rect, border_radius=8)
                text_surf = self.font.render(txt, True, (255, 255, 255))
                text_rect = text_surf.get_rect(center=rect.center)
                self.screen.blit(text_surf, text_rect)

            pygame.display.flip()
            self.clock.tick(FPS)

        self.pet.save()
        pygame.quit()
        sys.exit()

if __name__ == "__main__":
    game = GameEngine()
    game.run()