import os
import sys
import pygame
from constants import *
from models import PetState
from database import DatabaseManager
from pet_entity import Pet

class GameEngine:
    """Orchestrates the MVC relationship."""
    def __init__(self):
        pygame.init()
        self.screen = pygame.display.set_mode((SCREEN_WIDTH, SCREEN_HEIGHT), pygame.SCALED | pygame.RESIZABLE)
        self.clock, self.font = pygame.time.Clock(), pygame.font.Font(None, 22)
        self.db = DatabaseManager(DB_FILE)
        self.pet = Pet(self.db)
        self.pet.load()

        # UI Hitboxes
        self.btn_feed = pygame.Rect(10, 250, 90, 40)
        self.btn_play = pygame.Rect(105, 250, 90, 40)
        self.btn_train = pygame.Rect(200, 250, 90, 40)
        self.btn_sleep = pygame.Rect(295, 250, 90, 40)
        self.btn_quit = pygame.Rect(390, 250, 80, 40)

    def draw_bar(self, x, y, value, color, label):
        self.screen.blit(self.font.render(label, True, COLOR_TEXT), (x, y - 18))
        pygame.draw.rect(self.screen, COLOR_UI_BAR_BG, (x, y, 90, 12), border_radius=6)
        if value > 5:
            pygame.draw.rect(self.screen, color, (x, y, int(value * 0.9), 12), border_radius=6)

    def run(self):
        running = True
        while running:
            for event in pygame.event.get():
                if event.type == pygame.QUIT: running = False
                if event.type == pygame.MOUSEBUTTONDOWN and self.pet.is_alive:
                    if self.btn_feed.collidepoint(event.pos):
                        self.pet.stats.fullness = self.pet.stats.clamp(self.pet.stats.fullness + 20)
                        self.pet.transition_to(PetState.EATING)
                    elif self.btn_play.collidepoint(event.pos):
                        self.pet.stats.happiness = self.pet.stats.clamp(self.pet.stats.happiness + 20)
                        self.pet.stats.energy = self.pet.stats.clamp(self.pet.stats.energy - 10)
                    elif self.btn_train.collidepoint(event.pos):
                        self.pet.stats.discipline = self.pet.stats.clamp(self.pet.stats.discipline + 15)
                        self.pet.stats.energy = self.pet.stats.clamp(self.pet.stats.energy - 15)
                    elif self.btn_sleep.collidepoint(event.pos):
                        new_state = PetState.IDLE if self.pet.state == PetState.SLEEPING else PetState.SLEEPING
                        self.pet.transition_to(new_state)
                    elif self.btn_quit.collidepoint(event.pos): running = False

            self.pet.update()
            if self.pet.state == PetState.EATING and self.pet.state_timer > 3.0:
                self.pet.transition_to(PetState.IDLE)

            self.screen.fill(COLOR_BG)
            self.draw_bar(10, 35, self.pet.stats.health, COLOR_HEALTH, "HEALTH")
            self.draw_bar(105, 35, self.pet.stats.fullness, COLOR_FULLNESS, "FULL")
            self.draw_bar(200, 35, self.pet.stats.happiness, COLOR_HAPPY, "HAPPY")
            self.draw_bar(295, 35, self.pet.stats.discipline, COLOR_SICK, "TRAIN")
            self.draw_bar(390, 35, self.pet.stats.energy, COLOR_ENERGY, "NRG")

            cx, cy = SCREEN_WIDTH // 2, 160
            self.pet.draw(self.screen, cx, cy)
            
            stage_txt = self.font.render(f"STAGE: {self.pet.life_stage} (Mistakes: {self.pet.stats.care_mistakes})", True, COLOR_TEXT)
            self.screen.blit(stage_txt, (SCREEN_WIDTH//2 - stage_txt.get_width()//2, 210))

            # Dynamic UI Layout
            buttons = [
                (self.btn_feed, "FEED"),
                (self.btn_play, "PLAY"),
                (self.btn_train, "TRAIN"),
                (self.btn_sleep, "SLEEP" if self.pet.state != PetState.SLEEPING else "WAKE"),
                (self.btn_quit, "QUIT")
            ]
            for rect, txt in buttons:
                pygame.draw.rect(self.screen, COLOR_BTN, rect, border_radius=8)
                label = self.font.render(txt, True, (255, 255, 255))
                self.screen.blit(label, label.get_rect(center=rect.center))

            pygame.display.flip()
            self.clock.tick(FPS)

        self.pet.save()
        pygame.quit()
        sys.exit()

if __name__ == "__main__":
    GameEngine().run()