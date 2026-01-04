import os
import sys
import time
import sqlite3
import pygame
import math
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
    """Enforces valid states for the pet."""
    EGG = auto()
    BABY = auto()
    IDLE = auto()
    EATING = auto()
    SLEEPING = auto()
    DEAD = auto()

@dataclass
class PetStats:
    hunger: float = 50.0
    happiness: float = 100.0
    energy: float = 100.0
    health: float = 100.0

    def clamp(self, value):
        return max(0.0, min(100.0, value))

    def tick(self, dt: float, current_state: PetState):
        """Dynamic decay rates based on the current state."""
        # Hunger increases faster if not sleeping
        hunger_rate = 8.0 if current_state!= PetState.SLEEPING else 2.0
        self.hunger = self.clamp(self.hunger + (hunger_rate / 3600.0) * dt)
        
        # Energy logic
        if current_state == PetState.SLEEPING:
            self.energy = self.clamp(self.energy + (30.0 / 3600.0) * dt)
        else:
            self.energy = self.clamp(self.energy - (4.0 / 3600.0) * dt)

        # Happiness decay
        self.happiness = self.clamp(self.happiness - (6.0 / 3600.0) * dt)

        # Health logic
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

    def update(self):
        if self.state == PetState.DEAD:
            return

        now = time.time()
        dt = now - self.last_update
        self.last_update = now

        # State-specific logic (The Brain of the FSM)
        if self.state == PetState.EGG:
            if now - self.birth_time > 10: # Fast hatch for testing
                self.transition_to(PetState.IDLE)
                self.life_stage = "BABY"
            return

        self.stats.tick(dt, self.state)

        # Death Transition
        if self.stats.health <= 0:
            self.transition_to(PetState.DEAD)
            self.is_alive = False

    def transition_to(self, new_state: PetState):
        """Handles Enter/Exit logic for states."""
        if self.state == new_state: return
        print(f"Transitioning from {self.state.name} to {new_state.name}")
        self.state = new_state

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
            # row structure based on create_tables: 
            # (id, hunger, happiness, energy, health, is_alive, birth_time, last_update, life_stage, state)
            self.stats.hunger = row[1]
            self.stats.happiness = row[2]
            self.stats.energy = row[3]
            self.stats.health = row[4]
            self.is_alive = bool(row[5])
            self.birth_time = row[6]
            # Offline Progress Catch-up
            offline_dt = time.time() - row[7]
            self.stats.tick(offline_dt, PetState[row[8]])
            self.life_stage = row[9]
            self.state = PetState[row[8]]
            self.last_update = time.time()

# --- 3. GAME ENGINE (Updated to handle FSM/DB) ---
class GameEngine:
    def __init__(self):
        pygame.init()
        self.screen = pygame.display.set_mode((SCREEN_WIDTH, SCREEN_HEIGHT), pygame.SCALED | pygame.RESIZABLE)
        self.clock = pygame.time.Clock()
        self.font = pygame.font.Font(None, 22)
        
        self.db = DatabaseManager(DB_FILE)
        self.pet = Pet(self.db)
        self.pet.load()

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
                    if self.btn_feed.collidepoint(event.pos):
                        self.pet.stats.hunger = self.pet.stats.clamp(self.pet.stats.hunger - 20)
                        self.pet.transition_to(PetState.EATING)
                    elif self.btn_sleep.collidepoint(event.pos):
                        new_state = PetState.IDLE if self.pet.state == PetState.SLEEPING else PetState.SLEEPING
                        self.pet.transition_to(new_state)
                    elif self.btn_quit.collidepoint(event.pos): running = False

            self.pet.update()
            
            # Reset Eating to IDLE automatically
            if self.pet.state == PetState.EATING and (pygame.time.get_ticks() % 2000 < 50):
                self.pet.transition_to(PetState.IDLE)

            # RENDER
            self.screen.fill(COLOR_BG)
            
            # 1. Draw Stat Bars
            self.draw_bar(20, 35, self.pet.stats.health, COLOR_HEALTH, "HEALTH")
            self.draw_bar(135, 35, 100 - self.pet.stats.hunger, COLOR_HUNGER, "FULLNESS")
            self.draw_bar(250, 35, self.pet.stats.happiness, COLOR_HAPPY, "HAPPY")
            self.draw_bar(365, 35, self.pet.stats.energy, COLOR_ENERGY, "ENERGY")

            # 2. Draw Dynamic Buttons based on State
            # This uses your logic to toggle between SLEEP and WAKE labels
            buttons = [
                (self.btn_feed, "FEED"),
                (self.btn_play, "PLAY"),
                (self.btn_sleep, "WAKE" if self.pet.state == PetState.SLEEPING else "SLEEP"),
                (self.btn_quit, "QUIT")
            ]

            for rect, txt in buttons:
                # Draw the button background
                pygame.draw.rect(self.screen, (100, 100, 100), rect, border_radius=8)
                
                # Center the text within the button rect [2]
                text_surf = self.font.render(txt, True, (255, 255, 255))
                text_rect = text_surf.get_rect(center=rect.center)
                self.screen.blit(text_surf, text_rect)

            pygame.display.flip()
            self.clock.tick(FPS)

        self.pet.save()
        pygame.quit()

if __name__ == "__main__":
    game = GameEngine()
    game.run()