import os
import sys
import pygame
from constants import *
from models import GameState, PetState, PetStats
from database import DatabaseManager
from pet_entity import Pet
from minigames import bouncing_pet_game
import time
import datetime


# --- Day/Night Cycle Colors ---
COLOR_DAY_BG = (135, 206, 235)  # Sky Blue
COLOR_DUSK_BG = (255, 160, 122) # Light Salmon
COLOR_NIGHT_BG = (25, 25, 112)  # Midnight Blue
COLOR_DAWN_BG = (255, 223, 186) # Peach Puff


class GameEngine:
    """Orchestrates the MVC relationship."""
    def __init__(self):
        pygame.init()
        pygame.mixer.init()

        self.screen = pygame.display.set_mode((SCREEN_WIDTH, SCREEN_HEIGHT), pygame.SCALED | pygame.RESIZABLE)
        
        # --- FIX: Separated assignment for robustness ---
        self.clock = pygame.time.Clock()
        self.font = pygame.font.Font(None, 22)
        # -----------------------------------------------

        self.db = DatabaseManager(DB_FILE)
        
        self.pet = Pet(self.db, name="Gizmo") # Initial pet name
        self.pet.load()

        self.stat_flash_timers = {}
        self.prev_stats = PetStats()
        self.update_prev_stats()
        self.game_time = datetime.datetime.now()
        self.game_state = GameState.PET_VIEW

        # --- Load Sounds (with placeholders) ---
        # NOTE: You must create these .wav files in the Tamagotchi folder!
        try:
            base_path = os.path.dirname(__file__)
            self.sound_click = pygame.mixer.Sound(os.path.join(base_path, "click.wav"))
            self.sound_eat = pygame.mixer.Sound(os.path.join(base_path, "eat.wav"))
            self.sound_play = pygame.mixer.Sound(os.path.join(base_path, "play.wav"))
            self.sound_heal = pygame.mixer.Sound(os.path.join(base_path, "heal.wav"))
        except pygame.error as e:
            print(f"Warning: Could not load sound files. Game will be silent. Error: {e}")
            self.sound_click = None
            self.sound_eat = None
            self.sound_play = None
            self.sound_heal = None


        # UI Hitboxes
        self.pet_center_x, self.pet_center_y = SCREEN_WIDTH // 2, 163
        self.pet_click_area = pygame.Rect(
            self.pet_center_x - 40, self.pet_center_y - 40, 80, 80
        )
        
        
        self.btn_feed = pygame.Rect(10, SCREEN_HEIGHT - 60, 70, 40)
        self.btn_play = pygame.Rect(85, SCREEN_HEIGHT - 60, 70, 40)
        self.btn_train = pygame.Rect(160, SCREEN_HEIGHT - 60, 70, 40)
        self.btn_sleep = pygame.Rect(235, SCREEN_HEIGHT - 60, 70, 40)
        self.btn_shop = pygame.Rect(310, SCREEN_HEIGHT - 60, 70, 40)
        self.btn_quit = pygame.Rect(385, SCREEN_HEIGHT - 60, 85, 40)
        

        # Button map for easy access
        self.buttons = [
            (self.btn_feed, "FEED", self.handle_feed),
            (self.btn_play, "PLAY", self.handle_play),
            (self.btn_train, "TRAIN", self.handle_train),
            (self.btn_sleep, "SLEEP", self._toggle_sleep),
            (self.btn_shop, "SHOP", self.handle_shop),
            (self.btn_quit, "QUIT", lambda: sys.exit())
        ]
        self.inventory_buttons = []
        self.shop_buttons = []

    # --- Action Handlers with Sound ---
    def handle_feed(self):
        if self.pet.state == PetState.IDLE:
            self.game_state = GameState.INVENTORY_VIEW

    def handle_shop(self):
        self.game_state = GameState.SHOP_VIEW

    def handle_play(self):
        if self.pet.state == PetState.IDLE:
            if self.sound_play: self.sound_play.play()
            self.play_minigame()

    def handle_train(self):
        if self.pet.state == PetState.IDLE or self.pet.state == PetState.SICK:
            if self.sound_click: self.sound_click.play()
            self.pet.transition_to(PetState.TRAINING)
    
    def handle_heal(self):
        if self.pet.state == PetState.SICK:
            if self.sound_heal: self.sound_heal.play()
            self.pet.heal()

    def _toggle_sleep(self):
        """Logic for the sleep button."""
        if self.sound_click: self.sound_click.play()
        if self.pet.state == PetState.SLEEPING:
            self.pet.transition_to(PetState.IDLE)
        else:
            self.pet.transition_to(PetState.SLEEPING)

    def play_minigame(self):
        score = bouncing_pet_game(self.screen, self.font)
        self.pet.stats.happiness = self.pet.stats.clamp(self.pet.stats.happiness + score)
        self.pet.stats.energy = self.pet.stats.clamp(self.pet.stats.energy - 10)
        self.pet.stats.points += score // 10
        self.pet.action_feedback_text = f"+{score} HAPPY! +{score//10} PTS"
        self.pet.action_feedback_timer = 2.0
        self.pet.transition_to(PetState.IDLE)

    def update_prev_stats(self):
        self.prev_stats.fullness = self.pet.stats.fullness
        self.prev_stats.happiness = self.pet.stats.happiness
        self.prev_stats.energy = self.pet.stats.energy
        self.prev_stats.health = self.pet.stats.health
        self.prev_stats.discipline = self.pet.stats.discipline

    def draw_bar(self, x, y, value, color, label):
        """Draws a progress bar with value text inside the bar."""
        bar_width, bar_height = 80, 16 
        
        bar_color = color
        stat_key = label.lower()
        if stat_key in self.stat_flash_timers:
            if int(self.stat_flash_timers[stat_key] * 10) % 2 == 0:
                bar_color = (255, 255, 255)

        # Label Text
        self.screen.blit(self.font.render(label, True, COLOR_TEXT), (x, y - 18))
        
        # Bar Background
        pygame.draw.rect(self.screen, COLOR_UI_BAR_BG, (x, y, bar_width, bar_height), border_radius=4)
        
        # Bar Fill
        fill_width = (value / 100.0) * bar_width
        pygame.draw.rect(self.screen, bar_color, (x, y, fill_width, bar_height), border_radius=4)
        
        # Percentage Text Overlay (inside the bar)
        val_txt = self.font.render(f"{int(value)}%", True, COLOR_TEXT)
        self.screen.blit(val_txt, (x + bar_width // 2 - val_txt.get_width() // 2, y + bar_height // 2 - val_txt.get_height() // 2))


    def draw_inventory(self):
        self.screen.fill(COLOR_BG)
        title_surf = self.font.render("Inventory", True, COLOR_TEXT)
        self.screen.blit(title_surf, (SCREEN_WIDTH // 2 - title_surf.get_width() // 2, 20))

        inventory = self.db.get_inventory()
        self.inventory_buttons.clear()
        y_offset = 60
        for item in inventory:
            item_name, quantity, _, _, _ = item
            item_text = f"{item_name} (x{quantity})"
            item_surf = self.font.render(item_text, True, COLOR_TEXT)
            item_rect = pygame.Rect(50, y_offset, SCREEN_WIDTH - 100, 40)
            self.inventory_buttons.append((item_rect, item_name))
            pygame.draw.rect(self.screen, COLOR_BTN, item_rect, border_radius=5)
            self.screen.blit(item_surf, (item_rect.x + 10, item_rect.y + 10))
            y_offset += 50

        close_button = pygame.Rect(SCREEN_WIDTH // 2 - 50, SCREEN_HEIGHT - 60, 100, 40)
        self.inventory_buttons.append((close_button, "CLOSE"))
        pygame.draw.rect(self.screen, COLOR_BTN, close_button, border_radius=5)
        close_surf = self.font.render("Close", True, COLOR_TEXT)
        self.screen.blit(close_surf, close_surf.get_rect(center=close_button.center))

    def draw_shop(self):
        self.screen.fill(COLOR_BG)
        title_surf = self.font.render("Shop", True, COLOR_TEXT)
        self.screen.blit(title_surf, (SCREEN_WIDTH // 2 - title_surf.get_width() // 2, 20))
        points_surf = self.font.render(f"Points: {self.pet.stats.points}", True, COLOR_TEXT)
        self.screen.blit(points_surf, (20, 20))

        self.shop_buttons.clear()
        y_offset = 60
        for item_name, price in SHOP_ITEMS.items():
            item_text = f"Buy {item_name} - {price} pts"
            item_surf = self.font.render(item_text, True, COLOR_TEXT)
            item_rect = pygame.Rect(50, y_offset, SCREEN_WIDTH - 100, 40)
            self.shop_buttons.append((item_rect, item_name))
            pygame.draw.rect(self.screen, COLOR_BTN, item_rect, border_radius=5)
            self.screen.blit(item_surf, (item_rect.x + 10, item_rect.y + 10))
            y_offset += 50

        close_button = pygame.Rect(SCREEN_WIDTH // 2 - 50, SCREEN_HEIGHT - 60, 100, 40)
        self.shop_buttons.append((close_button, "CLOSE"))
        pygame.draw.rect(self.screen, COLOR_BTN, close_button, border_radius=5)
        close_surf = self.font.render("Close", True, COLOR_TEXT)
        self.screen.blit(close_surf, close_surf.get_rect(center=close_button.center))

    def handle_inventory_clicks(self, click_pos):
        for rect, name in self.inventory_buttons:
            if rect.collidepoint(click_pos):
                if name == "CLOSE":
                    self.game_state = GameState.PET_VIEW
                else:
                    item = self.db.get_item(name)
                    if item and self.db.remove_item_from_inventory(name):
                        _, _, _, effect_stat, effect_value = item
                        current_value = getattr(self.pet.stats, effect_stat)
                        setattr(self.pet.stats, effect_stat, self.pet.stats.clamp(current_value + effect_value))
                        self.pet.action_feedback_text = f"Used {name}!"
                        self.pet.action_feedback_timer = 2.0
                        self.game_state = GameState.PET_VIEW

    def handle_shop_clicks(self, click_pos):
        for rect, name in self.shop_buttons:
            if rect.collidepoint(click_pos):
                if name == "CLOSE":
                    self.game_state = GameState.PET_VIEW
                else:
                    price = SHOP_ITEMS.get(name)
                    if price and self.pet.stats.points >= price:
                        self.pet.stats.points -= price
                        self.db.add_item_to_inventory(name)
                        self.pet.action_feedback_text = f"Bought {name}!"
                        self.pet.action_feedback_timer = 2.0

    def run(self):
        """Main game loop."""
        running = True
        while running:
            dt = self.clock.tick(FPS) / 1000.0
            
            self.game_time += datetime.timedelta(seconds=dt * TIME_SCALE_FACTOR)
            current_hour = self.game_time.hour
            
            if 6 <= current_hour < 12:
                current_bg_color = COLOR_DAY_BG
            elif 12 <= current_hour < 18:
                current_bg_color = COLOR_DUSK_BG
            elif 18 <= current_hour < 24:
                current_bg_color = COLOR_NIGHT_BG
            else:
                current_bg_color = COLOR_DAWN_BG

            for event in pygame.event.get():
                if event.type == pygame.QUIT:
                    running = False
                    break
                
                click_pos = None
                if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
                    click_pos = event.pos
                elif event.type == pygame.FINGERDOWN:
                    win_w, win_h = self.screen.get_size()
                    click_pos = (int(event.x * win_w), int(event.y * win_h))

                if click_pos:
                    if self.game_state == GameState.PET_VIEW:
                        if self.pet.state != PetState.DEAD:
                            if self.sound_click:
                                is_on_button = any(rect.collidepoint(click_pos) for rect, _, _ in self.buttons)
                                is_on_pet = self.pet_click_area.collidepoint(click_pos)
                                if is_on_button or (self.pet.state == PetState.SICK and is_on_pet):
                                    self.sound_click.play()
                            if self.pet.state == PetState.SICK and self.pet_click_area.collidepoint(click_pos):
                                self.handle_heal()
                            for rect, name, action in self.buttons:
                                if rect.collidepoint(click_pos):
                                    action()
                    elif self.game_state == GameState.INVENTORY_VIEW:
                        self.handle_inventory_clicks(click_pos)
                    elif self.game_state == GameState.SHOP_VIEW:
                        self.handle_shop_clicks(click_pos)

            if self.game_state == GameState.PET_VIEW:
                self.pet.update(dt, current_hour)
                if self.pet.stats.happiness > self.prev_stats.happiness: self.stat_flash_timers['happy'] = 1.5
                if self.pet.stats.fullness > self.prev_stats.fullness: self.stat_flash_timers['full'] = 1.5
                if self.pet.stats.discipline > self.prev_stats.discipline: self.stat_flash_timers['train'] = 1.5
                if self.pet.stats.energy > self.prev_stats.energy: self.stat_flash_timers['nrg'] = 1.5
                if self.pet.stats.health > self.prev_stats.health: self.stat_flash_timers['health'] = 1.5
                for stat_key in list(self.stat_flash_timers.keys()):
                    self.stat_flash_timers[stat_key] -= dt
                    if self.stat_flash_timers[stat_key] <= 0:
                        del self.stat_flash_timers[stat_key]
                self.update_prev_stats()

            if running:
                self.screen.fill(current_bg_color)
                if self.game_state == GameState.PET_VIEW:
                    cx, cy = self.pet_center_x, self.pet_center_y
                    self.pet.draw(self.screen, cx, cy, self.font)
                    self.draw_bar(20, 30, self.pet.stats.happiness, (255, 200, 0), "Happiness")
                    self.draw_bar(110, 30, self.pet.stats.fullness, (0, 255, 0), "Fullness")
                    self.draw_bar(200, 30, self.pet.stats.energy, (0, 0, 255), "Energy")
                    self.draw_bar(290, 30, self.pet.stats.health, (255, 0, 0), "Health")
                    self.draw_bar(380, 30, self.pet.stats.discipline, (255, 0, 255), "Discipline")
                    points_surf = self.font.render(f"Points: {self.pet.stats.points}", True, COLOR_TEXT)
                    self.screen.blit(points_surf, (20, 60))
                    for rect, text, _ in self.buttons:
                        pygame.draw.rect(self.screen, COLOR_BTN, rect, border_radius=5)
                        text_surf = self.font.render(text, True, COLOR_TEXT)
                        text_rect = text_surf.get_rect(center=rect.center)
                        self.screen.blit(text_surf, text_rect)
                elif self.game_state == GameState.INVENTORY_VIEW:
                    self.draw_inventory()
                elif self.game_state == GameState.SHOP_VIEW:
                    self.draw_shop()
                pygame.display.flip()

if __name__ == "__main__":
    engine = GameEngine()
    try:
        engine.run()
    finally:
        pygame.quit()