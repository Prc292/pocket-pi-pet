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
        
        # --- FIX: Separated assignment for robustness ---
        self.clock = pygame.time.Clock()
        self.font = pygame.font.Font(None, 22)
        # -----------------------------------------------

        self.db = DatabaseManager(DB_FILE)
        
        self.pet = Pet(self.db, name="Gizmo") # Initial pet name
        self.pet.load()

        # UI Hitboxes
        self.pet_center_x, self.pet_center_y = SCREEN_WIDTH // 2, 160
        self.pet_click_area = pygame.Rect(
            self.pet_center_x - 40, self.pet_center_y - 40, 80, 80
        )
        
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
        """Draws a progress bar with value text inside the bar."""
        bar_width, bar_height = 80, 16 
        
        # Label Text
        self.screen.blit(self.font.render(label, True, COLOR_TEXT), (x, y - 18))
        
        # Bar Background
        pygame.draw.rect(self.screen, COLOR_UI_BAR_BG, (x, y, bar_width, bar_height), border_radius=4)
        
        # Bar Fill
        fill_width = (value / 100.0) * bar_width
        pygame.draw.rect(self.screen, color, (x, y, fill_width, bar_height), border_radius=4)
        
        # Percentage Text Overlay (inside the bar)
        val_txt = self.font.render(f"{int(value)}%", True, COLOR_TEXT)
        self.screen.blit(val_txt, (x + bar_width // 2 - val_txt.get_width() // 2, y + bar_height // 2 - val_txt.get_height() // 2))


    def run(self):
        """Main game loop."""
        running = True
        while running:
            # Delta time in seconds (where the original error occurred)
            dt = self.clock.tick(FPS) / 1000.0 

            for event in pygame.event.get():
                if event.type == pygame.QUIT:
                    running = False
                
                # Handle mouse clicks AND touchscreen input
                click_pos = None

                if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
                    click_pos = event.pos

                elif event.type == pygame.FINGERDOWN:
                    win_w, win_h = self.screen.get_size()
                    click_pos = (
                        int(event.x * win_w),
                        int(event.y * win_h)
                    )

                if click_pos:
                    if self.pet.state == PetState.DEAD:
                        continue

                    # Check for clicks on the Pet itself (for healing)
                    if self.pet.state == PetState.SICK and self.pet_click_area.collidepoint(click_pos):
                        self.pet.heal()

                    # Check for button clicks
                    current_state = self.pet.state
                    for rect, _, action in self.buttons:
                        if rect.collidepoint(click_pos):
                            if action == self._toggle_sleep:
                                action()
                            elif current_state == PetState.IDLE:
                                action()
                            # Allow training from sick state
                            elif current_state == PetState.SICK and rect == self.btn_train:
                                self.pet.transition_to(PetState.TRAINING)


            # --- UPDATE ---
            self.pet.update(dt) 

            # --- RENDER ---
            self.screen.fill(COLOR_BG)

            # Draw Stats Bars
            bar_y = 35
            self.draw_bar(10, bar_y, self.pet.stats.health, COLOR_HEALTH, "HEALTH")
            self.draw_bar(105, bar_y, self.pet.stats.fullness, COLOR_FULLNESS, "FULL")
            self.draw_bar(200, bar_y, self.pet.stats.happiness, COLOR_HAPPY, "HAPPY")
            self.draw_bar(295, bar_y, self.pet.stats.discipline, COLOR_SICK, "TRAIN")
            self.draw_bar(390, bar_y, self.pet.stats.energy, COLOR_ENERGY, "NRG")

            cx, cy = self.pet_center_x, self.pet_center_y
            
            # Draw Pet
            self.pet.draw(self.screen, cx, cy, self.font)
            
            # Display Name, Life Stage, and Care Mistakes
            name_text = self.font.render(f"NAME: {self.pet.name}", True, COLOR_TEXT)
            self.screen.blit(name_text, (SCREEN_WIDTH//2 - name_text.get_width()//2, 100))
            
            stage_txt = self.font.render(
                f"STAGE: {self.pet.life_stage} (Mistakes: {self.pet.stats.care_mistakes})", 
                True, COLOR_TEXT
            )
            self.screen.blit(stage_txt, (SCREEN_WIDTH//2 - stage_txt.get_width()//2, 210))
            
            # Display current state
            state_text_color = COLOR_TEXT
            if self.pet.state == PetState.DEAD: state_text_color = (255, 0, 0)
            state_txt = self.font.render(f"STATE: {self.pet.state.name}", True, state_text_color)
            self.screen.blit(state_txt, (SCREEN_WIDTH//2 - state_txt.get_width()//2, 230))

            # Dynamic UI Layout (Buttons)
            for rect, txt, _ in self.buttons:
                button_color = COLOR_BTN
                
                # Highlight active state button
                if self.pet.state != PetState.DEAD:
                    if txt == "SLEEP" and self.pet.state == PetState.SLEEPING:
                        button_color = COLOR_ENERGY
                    elif self.pet.state.name == txt:
                         button_color = COLOR_HAPPY 
                         
                pygame.draw.rect(self.screen, button_color, rect, border_radius=5)
                
                # Draw small action timer indicator for active actions
                if self.pet.state.name == txt and self.pet.action_timer > 0:
                    timer_ratio = self.pet.action_timer / self.pet.action_duration
                    indicator_width = rect.width * timer_ratio
                    # Draw a small, bright bar at the bottom of the button
                    pygame.draw.rect(self.screen, (255, 255, 255), (rect.x, rect.bottom - 3, indicator_width, 3))
                
                # Button text
                button_text = "WAKE" if txt == "SLEEP" and self.pet.state == PetState.SLEEPING else "QUIT" if txt == "QUIT" else txt
                text_surf = self.font.render(button_text, True, COLOR_TEXT)
                text_rect = text_surf.get_rect(center=rect.center)
                self.screen.blit(text_surf, text_rect)
            
            # Draw Status Alert/Prompt
            if self.pet.state == PetState.SICK:
                alert_text = self.font.render("PET IS SICK! CLICK PET TO HEAL", True, (255, 0, 0))
                self.screen.blit(alert_text, alert_text.get_rect(center=(SCREEN_WIDTH//2, 298)))
            elif self.pet.state == PetState.DEAD:
                alert_text = self.font.render("GAME OVER. R.I.P.", True, (255, 0, 0))
                self.screen.blit(alert_text, alert_text.get_rect(center=(SCREEN_WIDTH//2, 298)))


            pygame.display.flip()

        pygame.quit()
        self.pet.save() 

if __name__ == "__main__":
    GameEngine().run()