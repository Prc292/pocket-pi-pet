#!/usr/bin/env python3
import os
import sys
import time
import json
import platform
import pygame
import math

# --- CONFIGURATION ---
SCREEN_WIDTH = 480
SCREEN_HEIGHT = 320
FPS = 30
SAVE_FILE = os.path.join(os.path.dirname(__file__), ".pet_save.json")

# Retro UI Palette
COLOR_BG = (40, 44, 52)
COLOR_PET_BODY = (171, 220, 255)
COLOR_PET_EYES = (33, 37, 43)
COLOR_UI_BAR_BG = (62, 68, 81)
COLOR_HEALTH = (152, 195, 121)
COLOR_HUNGER = (224, 108, 117)
COLOR_HAPPY = (229, 192, 123)
COLOR_ENERGY = (97, 175, 239)

# --- VIRTUAL PET LOGIC ---
class Pet:
    def __init__(self):
        self.hunger = 50.0   # 0 = Full, 100 = Starving
        self.happiness = 100.0
        self.energy = 100.0
        self.health = 100.0
        self.is_alive = True
        self.birth_time = time.time()
        self.last_update = time.time()
        self.life_stage = "EGG"
        self.state = "IDLE"

    def update(self):
        if not self.is_alive: return
        now = time.time()
        elapsed = now - self.last_update
        self.last_update = now

        if self.life_stage == "EGG":
            if now - self.birth_time > 30: self.life_stage = "BABY"
            return 

        # Passive Decay Logic (Units per hour)
        self.hunger = min(100.0, self.hunger + (8.0 * (elapsed / 3600)))
        self.happiness = max(0.0, self.happiness - (6.0 * (elapsed / 3600)))
        self.energy = max(0.0, self.energy - (4.0 * (elapsed / 3600)))

        # Health decay if neglected
        if self.hunger > 80 or self.energy < 20:
            self.health = max(0.0, self.health - (10.0 * (elapsed / 3600)))
        # Health regeneration if well cared for
        elif self.hunger < 70 and self.energy > 50 and self.health < 100:
            self.health = min(100.0, self.health + (5.0 * (elapsed / 3600)))
        
        if self.health <= 0: self.is_alive = False

    def feed(self):
        if self.is_alive and self.life_stage!= "EGG":
            self.hunger = max(0.0, self.hunger - 20.0)
            self.state = "EATING"

    def play(self):
        if self.is_alive and self.life_stage!= "EGG":
            self.happiness = min(100.0, self.happiness + 20.0)
            self.energy = max(0.0, self.energy - 10.0)
            self.hunger = min(100.0, self.hunger + 5.0)  # small fullness decrease

    def save(self):
        data = {
            "hunger": self.hunger, "happiness": self.happiness,
            "energy": self.energy, "health": self.health,
            "is_alive": self.is_alive, "birth_time": self.birth_time,
            "last_update": time.time(), "life_stage": self.life_stage
        }
        with open(SAVE_FILE, 'w') as f:
            json.dump(data, f)

    def load(self):
        if os.path.exists(SAVE_FILE):
            with open(SAVE_FILE, 'r') as f:
                data = json.load(f)
                self.hunger = data.get("hunger", 50.0)
                self.happiness = data.get("happiness", 100.0)
                self.energy = data.get("energy", 100.0)
                self.health = data.get("health", 100.0)
                self.is_alive = data.get("is_alive", True)
                self.life_stage = data.get("life_stage", "EGG")
                self.birth_time = data.get("birth_time", time.time())
                self.last_update = data.get("last_update", time.time())

# --- GAME ENGINE ---
class GameEngine:
    def __init__(self):
        pygame.init()
        if platform.system() == "Linux":
            os.environ["SDL_VIDEODRIVER"] = "kmsdrm"
            self.screen = pygame.display.set_mode((SCREEN_WIDTH, SCREEN_HEIGHT), pygame.FULLSCREEN)
        else:
            self.screen = pygame.display.set_mode((SCREEN_WIDTH, SCREEN_HEIGHT), pygame.SCALED | pygame.RESIZABLE)

        self.clock = pygame.time.Clock()
        self.font = pygame.font.Font(None, 22)
        self.pet = Pet()
        self.pet.load()

        # UI Hitboxes
        self.btn_feed = pygame.Rect(20, 250, 100, 40)
        self.btn_play = pygame.Rect(135, 250, 100, 40)
        self.btn_sleep = pygame.Rect(250, 250, 100, 40)  # new Sleep button
        self.btn_quit = pygame.Rect(365, 250, 100, 40)

    def draw_bar(self, x, y, value, color, label):
        self.screen.blit(self.font.render(label, True, (171, 178, 191)), (x, y - 18))
        pygame.draw.rect(self.screen, COLOR_UI_BAR_BG, (x, y, 100, 12), border_radius=6)
        if value > 5:
            pygame.draw.rect(self.screen, color, (x, y, int(value), 12), border_radius=6)

    def draw_pet_face(self, x, y, size):
        # Body
        pygame.draw.circle(self.screen, COLOR_PET_BODY, (x, y), size)
        pygame.draw.circle(self.screen, (255, 255, 255), (x-size//3, y-size//3), size//5)
        
        # Ears
        pygame.draw.polygon(self.screen, COLOR_PET_BODY, [(x-size, y-10), (x-size//2, y-size-5), (x-20, y-20)])
        pygame.draw.polygon(self.screen, COLOR_PET_BODY, [(x+size, y-10), (x+size//2, y-size-5), (x+20, y-20)])

        # Eyes
        eye_y = y - 10
        if (pygame.time.get_ticks() // 100) % 30 == 0:
            pygame.draw.line(self.screen, COLOR_PET_EYES, (x-15, eye_y), (x-5, eye_y), 2)
            pygame.draw.line(self.screen, COLOR_PET_EYES, (x+5, eye_y), (x+15, eye_y), 2)
        else:
            pygame.draw.circle(self.screen, COLOR_PET_EYES, (x-12, eye_y), 4)
            pygame.draw.circle(self.screen, COLOR_PET_EYES, (x+12, eye_y), 4)

        # Mouth
        m_rect = (x-10, y+5, 20, 10)
        if self.pet.state == "EATING":
            pygame.draw.circle(self.screen, (200, 50, 50), (x, y+12), 6)
        elif self.pet.health < 50 or self.pet.energy < 20:
            pygame.draw.arc(self.screen, COLOR_PET_EYES, m_rect, 0, 3.14, 2)  # sad mouth
        else:
            pygame.draw.arc(self.screen, COLOR_PET_EYES, m_rect, 3.14, 0, 2)   # smile

    def run(self):
        running = True
        while running:
            for event in pygame.event.get():
                if event.type == pygame.QUIT: running = False
                if event.type == pygame.MOUSEBUTTONDOWN:
                    # Feeding always reduces hunger, but only boosts energy if FULLNESS <= 80%
                    if self.btn_feed.collidepoint(event.pos) and self.pet.hunger > 0:
                        # Only boost energy if fullness is <= 80%
                        if (100 - self.pet.hunger) <= 80:
                            self.pet.energy = min(80, self.pet.energy + 5)
                        self.pet.feed()
                    elif self.btn_play.collidepoint(event.pos) and self.pet.energy < 100: self.pet.play()
                    elif self.btn_sleep.collidepoint(event.pos):
                        if self.pet.energy < 100:
                            self.pet.energy = min(100, self.pet.energy + 30)
                            if self.pet.energy <= 90:
                                self.pet.hunger = min(100.0, self.pet.hunger + 5.0)  # small fullness decrease
                    elif self.btn_quit.collidepoint(event.pos): running = False

            self.pet.update()
            self.screen.fill(COLOR_BG)
            pygame.draw.line(self.screen, (60, 64, 72), (0, 210), (480, 210), 2)

            self.draw_bar(20, 35, self.pet.health, COLOR_HEALTH, "HEALTH")
            self.draw_bar(135, 35, 100 - self.pet.hunger, COLOR_HUNGER, "FULLNESS")
            self.draw_bar(250, 35, self.pet.happiness, COLOR_HAPPY, "HAPPY")
            self.draw_bar(365, 35, self.pet.energy, COLOR_ENERGY, "ENERGY")

            cx, cy = SCREEN_WIDTH // 2, 160
            if self.pet.life_stage == "EGG":
                # Egg shake timing
                cycle_time = 5.5  # total cycle: 5s still + 0.5s shake
                t = time.time() % cycle_time
                if t < 5.0:
                    angle = 0  # still
                else:
                    # quick shake
                    angle = 15 * math.sin(20 * (t-5.0) * math.pi)

                # Draw egg surface
                egg_surf = pygame.Surface((50, 70), pygame.SRCALPHA)
                pygame.draw.ellipse(egg_surf, (245, 245, 210), (0, 0, 50, 70))

                # Draw cracks progressively
                hatch_progress = min(1.0, (time.time() - self.pet.birth_time) / 30.0)
                if hatch_progress > 0:
                    num_cracks = int(5 * hatch_progress)
                    for i in range(num_cracks):
                        offset = i * 8 - 16
                        points = [
                            (25, 20+offset),
                            (15, 30+offset),
                            (35, 40+offset),
                            (15, 50+offset),
                            (35, 55+offset)
                        ]
                        pygame.draw.lines(egg_surf, (180, 180, 160), False, points, 2)

                rotated_egg = pygame.transform.rotate(egg_surf, angle)
                rect = rotated_egg.get_rect(center=(cx, cy))
                self.screen.blit(rotated_egg, rect.topleft)
            elif not self.pet.is_alive:
                pygame.draw.circle(self.screen, (80, 80, 80), (cx, cy), 45)
                self.screen.blit(self.font.render("RIP", True, (200, 200, 200)), (cx-12, cy-8))
            else:
                bounce = 10 * abs(math.sin(time.time() * 4))
                self.draw_pet_face(cx, cy + int(bounce), 45)
                # Low Hunger Notification
                if self.pet.hunger > 80 and self.pet.is_alive:
                    notif_text = self.font.render("Your pet is hungry!", True, (255, 120, 50))
                    self.screen.blit(notif_text, (SCREEN_WIDTH//2 - notif_text.get_width()//2, 40))
                # Low Energy Notification
                if self.pet.energy < 20 and self.pet.is_alive:
                    notif_text = self.font.render("Your pet is exhausted!", True, (255, 100, 50))
                    self.screen.blit(notif_text, (SCREEN_WIDTH//2 - notif_text.get_width()//2, 60))
                # Low Happiness Notification
                if self.pet.happiness < 30 and self.pet.is_alive:
                    notif_text = self.font.render("Your pet is unhappy!", True, (255, 200, 50))
                    self.screen.blit(notif_text, (SCREEN_WIDTH//2 - notif_text.get_width()//2, 80))
                if self.pet.state == "EATING" and (pygame.time.get_ticks() % 1000 < 50):
                    self.pet.state = "IDLE"

            # FIXED BUTTON LIST
            buttons = [
                (self.btn_feed, "Feed", (180, 120, 80)),
                (self.btn_play, "Play", (100, 200, 120)),
                (self.btn_sleep, "Sleep", (120, 180, 255)),
                (self.btn_quit, "Quit", (200, 50, 50))
            ]
            for btn, txt, col in buttons:
                pygame.draw.rect(self.screen, col, btn, border_radius=12)
                label = self.font.render(txt, True, (255, 255, 255))
                self.screen.blit(label, (btn.centerx - label.get_width()//2, btn.centery - 8))

            pygame.display.flip()
            self.clock.tick(FPS)

        self.pet.save()
        pygame.quit()
        sys.exit()

if __name__ == "__main__":
    game = GameEngine()
    game.run()