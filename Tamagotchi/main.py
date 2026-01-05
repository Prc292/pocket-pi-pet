import os
import sys
import pygame
from constants import *
from models import PetState, PetStats
from database import DatabaseManager
from pet_entity import Pet
import time

class GameEngine:
    """Orchestrates the MVC relationship."""
    def __init__(self):
        pygame.init()
        self.screen = pygame.display.set_mode((SCREEN_WIDTH, SCREEN_HEIGHT), pygame.SCALED | pygame.RESIZABLE)
        self.clock, self.font = pygame.time.Clock(), pygame.font.Font(None, 22)
        self.db = DatabaseManager(DB_FILE)
        
        # Pet initialization must pass the db manager
        self.pet = Pet(self.db) 
        self.pet.load()

        # UI Hitboxes
        self.btn_feed = pygame.Rect(10, 250, 90, 40)
        self.btn_play = pygame.Rect(105, 250, 90, 40)
        self.btn_train = pygame.Rect(200, 250, 90, 40)
        self.btn_sleep = pygame.Rect(295, 250, 90, 40)
        self.btn_quit = pygame.Rect(390, 250, 80, 40)

        # Button map for easy access
        self.buttons = [
            (self.btn_feed, "FEED", lambda: self.pet.transition_to(PetState.EATING)),
            (self.btn_play, "PLAY", lambda: self.pet.transition_to(PetState.PLAYING)),
            (self.btn_train, "TRAIN", lambda: self.pet.transition_to(PetState.TRAINING)),
            (self.btn_sleep, "SLEEP", self._toggle_sleep),
            (self.btn_quit, "QUIT", lambda: sys.exit())
        ]
        
    def _toggle_sleep(self):
        """Logic for the sleep button."""
        if self.pet.state == PetState.SLEEPING:
            self.pet.transition_to(PetState.IDLE)
        else:
            self.pet.transition_to(PetState.SLEEPING)

    def draw_bar(self, x, y, value, color, label):
        """Draws a simple progress bar."""
        bar_width, bar_height = 80, 10
        self.screen.blit(self.font.render(label, True, COLOR_TEXT), (x, y - 18))
        pygame.draw.rect(self.screen, COLOR_UI_BAR_BG, (x, y, bar_width, bar_height), border_radius=2)
        fill_width = (value / 100.0) * bar_width
        pygame.draw.rect(self.screen, color, (x, y, fill_width, bar_height), border_radius=2)
        
        # Draw text overlay
        val_txt = self.font.render(f"{int(value)}%", True, COLOR_TEXT)
        self.screen.blit(val_txt, (x + bar_width // 2 - val_txt.get_width() // 2, y + 15))


    def run(self):
        """Main game loop."""
        running = True
        while running:
            # Delta time in seconds
            dt = self.clock.tick(FPS) / 1000.0 

            for event in pygame.event.get():
                if event.type == pygame.QUIT:
                    running = False
                
                # Input Handling
                if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
                    for rect, _, action in self.buttons:
                        if rect.collidepoint(event.pos):
                            action()
                            
            # --- UPDATE ---
            self.pet.update(dt) # Fix: Call the pet's update method with delta time

            # --- RENDER ---
            self.screen.fill(COLOR_BG)

            # Draw Stats Bars (Fix: Correct attribute access via self.pet.stats)
            self.draw_bar(10, 35, self.pet.stats.health, COLOR_HEALTH, "HEALTH")
            self.draw_bar(105, 35, self.pet.stats.fullness, COLOR_FULLNESS, "FULL")
            self.draw_bar(200, 35, self.pet.stats.happiness, COLOR_HAPPY, "HAPPY")
            self.draw_bar(295, 35, self.pet.stats.discipline, COLOR_SICK, "TRAIN")
            self.draw_bar(390, 35, self.pet.stats.energy, COLOR_ENERGY, "NRG")

            cx, cy = SCREEN_WIDTH // 2, 160
            
            # Draw Pet (Fix: Draw method is now implemented in Pet)
            self.pet.draw(self.screen, cx, cy)
            
            # Display life stage and care mistakes (Fix: Correct attribute access)
            stage_txt = self.font.render(
                f"STAGE: {self.pet.life_stage} (Mistakes: {self.pet.stats.care_mistakes})", 
                True, COLOR_TEXT
            )
            self.screen.blit(stage_txt, (SCREEN_WIDTH//2 - stage_txt.get_width()//2, 210))

            # Dynamic UI Layout (Buttons)
            for rect, txt, _ in self.buttons:
                # Button box
                pygame.draw.rect(self.screen, COLOR_BTN, rect, border_radius=5)
                # Button text
                # Adjust text for sleep button dynamically
                button_text = "WAKE" if txt == "SLEEP" and self.pet.state == PetState.SLEEPING else txt
                
                text_surf = self.font.render(button_text, True, COLOR_TEXT)
                text_rect = text_surf.get_rect(center=rect.center)
                self.screen.blit(text_surf, text_rect)

            pygame.display.flip()

        pygame.quit()
        self.pet.save() # Ensure save on exit

if __name__ == "__main__":
    GameEngine().run()