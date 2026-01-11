import os
import sys
import pygame
from constants import *
from models import GameState, PetState, PetStats
from database import DatabaseManager
from pet_entity import Pet
from minigames import CatchTheFoodMinigame
from gardening import GardeningGame

import time
import datetime


class MessageBox:
    def __init__(self, screen, font, x, y, width, height, small_font_size=28, duration=3):
        self.screen = screen
        self.font = font
        self.small_font = pygame.font.Font(None, small_font_size)
        
        self.maximized_height = height
        self.minimized_height = 30
        
        self.rect = pygame.Rect(x, y, width, self.maximized_height) # Maximized rect
        self.min_rect = pygame.Rect(x, y, width, self.minimized_height)

        self.messages = []
        self.padding = 5
        self.state = 'minimized' # 'minimized', 'maximized'
        self.scroll_offset = 0
        self.all_lines = []
        self.duration = duration # Initialize duration
        self.current_pop_up_message = "" # Initialize pop-up message

    def _wrap_text(self, text, font, max_width):
        words = text.split(' ')
        lines = []
        current_line = []
        for word in words:
            test_line = ' '.join(current_line + [word])
            if font.size(test_line)[0] <= max_width:
                current_line.append(word)
            else:
                lines.append(' '.join(current_line))
                current_line = [word]
        lines.append(' '.join(current_line))
        return lines

    def add_message(self, text):
        timestamp = datetime.datetime.now().strftime("%H:%M")
        full_message = f"[{timestamp}] {text}"
        self.messages.append(full_message)
        new_lines = self._wrap_text(full_message, self.font, self.rect.width - 2 * self.padding)
        self.all_lines.extend(new_lines)
        # When a new message is added, make it active and set the timer for pop-up
        self.active = True
        self.timer = self.duration
        self.current_pop_up_message = text # Store the message to be displayed as pop-up

    def update(self, dt):
        if self.active:
            self.timer -= dt
            if self.timer <= 0:
                self.active = False
                self.current_pop_up_message = "" # Clear the pop-up message

    def toggle_state(self, clear_unread_callback):
        if self.state == 'minimized':
            self.state = 'maximized'
            self.scroll_offset = 0
            clear_unread_callback()
        elif self.state == 'maximized':
            self.state = 'minimized'

    def get_pop_up_info(self):
        """Returns (message, is_active) for the temporary pop-up."""
        if self.current_pop_up_message and self.active and self.state == 'minimized':
            return self.current_pop_up_message, True
        return None, False

    def draw(self):
        # Then draw the message box normally (minimized or maximized)
        if self.state == 'minimized':
            self.draw_minimized()
        elif self.state == 'maximized':
            self.draw_maximized()

    def draw_minimized(self):
        s = pygame.Surface((self.min_rect.width, self.min_rect.height), pygame.SRCALPHA)
        s.fill((50, 50, 50, 150)) # A bit of background
        self.screen.blit(s, self.min_rect.topleft)

        display_text = "Messages"
        text_surf = self.small_font.render(display_text, False, COLOR_TEXT)
        # Center the text
        text_x = self.min_rect.x + (self.min_rect.width - text_surf.get_width()) // 2
        text_y = self.min_rect.y + (self.min_rect.height - text_surf.get_height()) // 2
        self.screen.blit(text_surf, (text_x, text_y))

    def draw_maximized(self):
        s = pygame.Surface((self.rect.width, self.rect.height), pygame.SRCALPHA)
        s.fill(COLOR_MESSAGE_BOX_BG)
        self.screen.blit(s, (self.rect.x, self.rect.y))
        y_offset = self.padding
        start_index = len(self.all_lines) - 1 - self.scroll_offset
        for i in range(start_index, -1, -1):
            line = self.all_lines[i]
            text_surface = self.font.render(line, False, COLOR_TEXT)
            line_height = text_surface.get_height()
            if self.rect.height - y_offset - line_height < 0:
                break
            self.screen.blit(text_surface, (self.rect.x + self.padding, self.rect.y + self.rect.height - y_offset - line_height))
            y_offset += line_height + self.padding



# --- Day/Night Cycle Colors ---
COLOR_DAY_BG = (135, 206, 235)  # Sky Blue
COLOR_DUSK_BG = (255, 165, 0)   # Orange
COLOR_NIGHT_BG = (25, 25, 112)  # Midnight Blue
COLOR_DAWN_BG = (255, 223, 186) # Peach Puff


class GameEngine:
    """Orchestrates the MVC relationship."""
    def add_game_message(self, message_data):
        if isinstance(message_data, str):
            text = message_data
            with_notification = True
        else:
            text = message_data.get("text", "")
            with_notification = message_data.get("notify", True)

        if not text: return

        self.message_box.add_message(text)
        if with_notification:
            self.unread_messages_count += 1

    def __init__(self):
        pygame.init()
        pygame.mixer.init()

        # The native resolution of the game
        self.native_surface = pygame.Surface((SCREEN_WIDTH, SCREEN_HEIGHT))
        # The window screen, which will be scaled
        self.screen = pygame.display.set_mode((SCREEN_WIDTH * 2, SCREEN_HEIGHT * 2), pygame.RESIZABLE)
        
        # Load background image
        base_path = os.path.dirname(__file__)
        background_path = os.path.join(base_path, "assets", "backgrounds", "background.png")
        self.background_image = pygame.image.load(background_path).convert_alpha()
        self.background_image = pygame.transform.scale(self.background_image, (SCREEN_WIDTH, SCREEN_HEIGHT))
        
        self.clock = pygame.time.Clock()
        self.font = pygame.font.Font(None, 16)

        self.db = DatabaseManager(DB_FILE)

        self.message_box = MessageBox(self.native_surface, self.font, 290, 50, 170, 150)
        self.unread_messages_count = 0
        # Initial message will now be handled by the Pet's loading/initialization
        # self.message_box.add_message("Welcome!")
        
        self.pet = Pet(self.db, name="Bobo", message_callback=self.add_game_message)
        self.pet.load()

        self.stat_flash_timers = {}
        self.prev_stats = PetStats()
        self.update_prev_stats()
        self.game_time = datetime.datetime.now()
        self.game_state = GameState.PET_VIEW

        # --- Load Sounds and Music ---
        base_path = os.path.dirname(__file__)
        try:
            self.sound_click = pygame.mixer.Sound(os.path.join(base_path, "assets", "audio", "click.wav"))
            self.sound_eat = pygame.mixer.Sound(os.path.join(base_path, "assets", "audio", "eat.wav"))
            self.sound_play = pygame.mixer.Sound(os.path.join(base_path, "assets", "audio", "play.wav"))
            self.sound_heal = pygame.mixer.Sound(os.path.join(base_path, "assets", "audio", "heal.wav"))
        except pygame.error as e:
            print(f"Warning: Could not load sound files. Game will be silent. Error: {e}")
            self.sound_click, self.sound_eat, self.sound_play, self.sound_heal = None, None, None, None


        self.pet_center_x, self.pet_center_y = SCREEN_WIDTH // 2, SCREEN_HEIGHT - 80 # Adjusted Y position to move pet lower
        self.pet_click_area = pygame.Rect(self.pet_center_x - 40, self.pet_center_y - 40, 80, 80)

        # UI Hitboxes - Buttons are now half as tall (20 pixels) and positioned lower, and adjusted width for new button
        self.btn_feed = pygame.Rect(48, SCREEN_HEIGHT - 25, 60, 20)
        self.btn_activities = pygame.Rect(113, SCREEN_HEIGHT - 25, 60, 20)
        self.btn_train = pygame.Rect(178, SCREEN_HEIGHT - 25, 60, 20)
        self.btn_sleep = pygame.Rect(243, SCREEN_HEIGHT - 25, 60, 20)
        self.btn_shop = pygame.Rect(308, SCREEN_HEIGHT - 25, 60, 20)
        self.btn_quit = pygame.Rect(373, SCREEN_HEIGHT - 25, 60, 20) # Adjusted Quit button
        
        self.buttons = [
            (self.btn_feed, "FEED", self.handle_feed),
            (self.btn_activities, "PLAY", self.handle_activities),
            (self.btn_train, "TRAIN", self.handle_train),
            (self.btn_sleep, "SLEEP", self._toggle_sleep),
            (self.btn_shop, "SHOP", self.handle_shop),
            (self.btn_quit, "QUIT", lambda: sys.exit()),
        ]
        self.inventory_buttons, self.shop_buttons, self.activities_buttons = [], [], []
        self.minigame = None








    def handle_feed(self):
        print(f"handle_feed called. Current pet state: {self.pet.state}")
        if self.pet.state == PetState.IDLE:
            self.game_state = GameState.INVENTORY_VIEW

    def handle_shop(self):
                    self.game_state = GameState.SHOP_VIEW

    def handle_activities(self):
        if self.pet.state == PetState.IDLE:
            self.game_state = GameState.ACTIVITIES_VIEW

    def handle_train(self):
        if self.pet.state == PetState.IDLE or self.pet.state == PetState.SICK:
            if self.sound_click: self.sound_click.play()
            self.pet.transition_to(PetState.TRAINING)
    
    def handle_heal(self):
        if self.pet.state == PetState.SICK:
            if self.sound_heal: self.sound_heal.play()
            self.pet.heal()

    def _toggle_sleep(self):
        if self.sound_click: self.sound_click.play()
        if self.pet.state == PetState.SLEEPING:
            self.pet.transition_to(PetState.IDLE)
        else:
            self.pet.transition_to(PetState.SLEEPING)

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
        self.native_surface.blit(self.font.render(label, False, COLOR_TEXT), (x, y - 18))
        
        # Bar Background
        pygame.draw.rect(self.native_surface, COLOR_UI_BAR_BG, (x, y, bar_width, bar_height), border_radius=4)
        
        # Bar Fill
        fill_width = (value / 100.0) * bar_width
        pygame.draw.rect(self.native_surface, bar_color, (x, y, fill_width, bar_height), border_radius=4)
        
        # Percentage Text Overlay (inside the bar)
        val_txt = self.font.render(f"{int(value)}%", False, COLOR_TEXT)
        self.native_surface.blit(val_txt, (x + bar_width // 2 - val_txt.get_width() // 2, y + bar_height // 2 - val_txt.get_height() // 2))

    def draw_inventory(self):
        self.native_surface.fill(COLOR_BG)
        title_surf = self.font.render("Inventory", False, COLOR_TEXT)
        self.native_surface.blit(title_surf, (SCREEN_WIDTH // 2 - title_surf.get_width() // 2, 20))

        self.inventory_buttons.clear()

        # Add Snack button
        snack_rect = pygame.Rect(50, 60, SCREEN_WIDTH - 100, 20) # Half height
        self.inventory_buttons.append((snack_rect, "Snack"))
        pygame.draw.rect(self.native_surface, COLOR_BTN, snack_rect, border_radius=5)
        self.native_surface.blit(self.font.render("Snack (Free)", False, COLOR_TEXT), (snack_rect.x + 10, snack_rect.y + 2)) # Adjusted text y to center

        inventory_items = self.db.get_inventory()
        start_y = 90 # Adjusted start_y for next button, previous was 110. (60 + 20 + 10 padding = 90)

        if not inventory_items:
            empty_msg = self.font.render("Your inventory is empty! Buy items from the shop.", False, COLOR_TEXT)
            self.native_surface.blit(empty_msg, empty_msg.get_rect(center=(SCREEN_WIDTH // 2, start_y + 30))) # Adjusted y for message
        
        for i, item in enumerate(inventory_items):
            item_name, quantity, _, _, _ = item
            item_text = f"{item_name} (x{quantity})"
            item_rect = pygame.Rect(50, start_y + i * 25, SCREEN_WIDTH - 100, 20) # Half height, proportional spacing
            self.inventory_buttons.append((item_rect, item_name))
            pygame.draw.rect(self.native_surface, COLOR_BTN, item_rect, border_radius=5)
            self.native_surface.blit(self.font.render(item_text, False, COLOR_TEXT), (item_rect.x + 10, item_rect.y + 2)) # Adjusted text y to center

        close_button = pygame.Rect(SCREEN_WIDTH // 2 - 50, SCREEN_HEIGHT - 40, 100, 20) # Half height, adjusted y
        self.inventory_buttons.append((close_button, "CLOSE"))
        pygame.draw.rect(self.native_surface, COLOR_BTN, close_button, border_radius=5)
        self.native_surface.blit(self.font.render("Close", False, COLOR_TEXT), (close_button.centerx - self.font.render("Close", False, COLOR_TEXT).get_width() // 2, close_button.y + 2)) # Adjusted text y to center
    
    def draw_activities(self):
        self.native_surface.fill(COLOR_BG)
        title_surf = self.font.render("Activities", False, COLOR_TEXT)
        self.native_surface.blit(title_surf, (SCREEN_WIDTH // 2 - title_surf.get_width() // 2, 20))

        self.activities_buttons.clear()
        
        bouncing_pet_button = pygame.Rect(50, 60, SCREEN_WIDTH - 100, 20) # Half height
        self.activities_buttons.append((bouncing_pet_button, "Catch the Food"))
        pygame.draw.rect(self.native_surface, COLOR_BTN, bouncing_pet_button, border_radius=5)
        self.native_surface.blit(self.font.render("Catch the Food", False, COLOR_TEXT), (bouncing_pet_button.x + 10, bouncing_pet_button.y + 2)) # Adjusted text y to center

        gardening_button = pygame.Rect(50, 85, SCREEN_WIDTH - 100, 20) # Half height, adjusted y
        self.activities_buttons.append((gardening_button, "Gardening"))
        pygame.draw.rect(self.native_surface, COLOR_BTN, gardening_button, border_radius=5)
        self.native_surface.blit(self.font.render("Gardening (WIP)", False, COLOR_TEXT), (gardening_button.x + 10, gardening_button.y + 2)) # Adjusted text y to center
        
        close_button = pygame.Rect(SCREEN_WIDTH // 2 - 50, SCREEN_HEIGHT - 40, 100, 20) # Half height, adjusted y
        self.activities_buttons.append((close_button, "CLOSE"))
        pygame.draw.rect(self.native_surface, COLOR_BTN, close_button, border_radius=5)
        self.native_surface.blit(self.font.render("Close", False, COLOR_TEXT), (close_button.centerx - self.font.render("Close", False, COLOR_TEXT).get_width() // 2, close_button.y + 2)) # Adjusted text y to center

    def draw_shop(self):
        self.native_surface.fill(COLOR_BG)
        title_surf = self.font.render("Shop", False, COLOR_TEXT)
        self.native_surface.blit(title_surf, (SCREEN_WIDTH // 2 - title_surf.get_width() // 2, 20))
        points_surf = self.font.render(f"Coins: {self.pet.stats.coins}", False, COLOR_TEXT)
        self.native_surface.blit(points_surf, (20, 20))

        self.shop_buttons.clear()
        for i, (item_name, price) in enumerate(SHOP_ITEMS.items()):
            item_text = f"Buy {item_name} - {price} pts"
            item_rect = pygame.Rect(50, 60 + i * 25, SCREEN_WIDTH - 100, 20) # Half height, proportional spacing
            self.shop_buttons.append((item_rect, item_name))
            pygame.draw.rect(self.native_surface, COLOR_BTN, item_rect, border_radius=5)
            self.native_surface.blit(self.font.render(item_text, False, COLOR_TEXT), (item_rect.x + 10, item_rect.y + 2)) # Adjusted text y to center

        close_button = pygame.Rect(SCREEN_WIDTH // 2 - 50, SCREEN_HEIGHT - 40, 100, 20) # Half height, adjusted y
        self.shop_buttons.append((close_button, "CLOSE"))
        pygame.draw.rect(self.native_surface, COLOR_BTN, close_button, border_radius=5)
        self.native_surface.blit(self.font.render("Close", False, COLOR_TEXT), (close_button.centerx - self.font.render("Close", False, COLOR_TEXT).get_width() // 2, close_button.y + 2)) # Adjusted text y to center

    def handle_inventory_clicks(self, click_pos):
        for rect, name in self.inventory_buttons:
            if rect.collidepoint(click_pos):
                if name == "CLOSE":
                    self.game_state = GameState.PET_VIEW
                elif name == "Snack":
                    item = self.db.get_item("Snack") # Get snack details from db

                    if item:
                        _, _, _, effect_stat, effect_value = item
                        current_value = getattr(self.pet.stats, effect_stat)
                        setattr(self.pet.stats, effect_stat, self.pet.stats.clamp(current_value + effect_value))
                        self.add_game_message({"text": f"You fed {self.pet.name} a snack.", "notify": False})
                        self.game_state = GameState.PET_VIEW
                        if self.sound_eat: self.sound_eat.play()


    def handle_activities_clicks(self, click_pos):
        for rect, name in self.activities_buttons:
            if rect.collidepoint(click_pos):
                if name == "CLOSE":
                    self.game_state = GameState.PET_VIEW
                elif name == "Catch the Food":
                    self.minigame = CatchTheFoodMinigame(self.font)
                    self.game_state = GameState.CATCH_THE_FOOD_MINIGAME
                elif name == "Gardening":
                    self.minigame = GardeningGame(self.font, self.db)
                    self.game_state = GameState.GARDENING_MINIGAME

    def handle_shop_clicks(self, click_pos):
        for rect, name in self.shop_buttons:
            if rect.collidepoint(click_pos):
                if name == "CLOSE":
                    self.game_state = GameState.PET_VIEW
                else:
                    price = SHOP_ITEMS.get(name)
                    if price and self.pet.stats.coins >= price:
                        self.pet.stats.coins -= price
                        self.db.add_item_to_inventory(name)
                        self.add_game_message({"text": f"You bought a {name}!", "notify": False})
                    else:
                        self.add_game_message({"text": "Not enough coins!", "notify": True})

    def run(self):
        running = True
        while running:
            dt = self.clock.tick(FPS) / 1000.0
            self.message_box.update(dt)
            
            self.game_time += datetime.timedelta(seconds=dt * TIME_SCALE_FACTOR)
            current_hour = self.game_time.hour
            
            if 6 <= current_hour < 18: current_bg_color = COLOR_DAY_BG
            elif 18 <= current_hour < 22: current_bg_color = COLOR_DUSK_BG
            elif 5 <= current_hour < 6: current_bg_color =COLOR_DAWN_BG
            else: current_bg_color = COLOR_NIGHT_BG            
            click_pos = None
            current_pointer_pos = (self.pet_center_x, SCREEN_HEIGHT - 50) # Initialize with a reasonable default
            for event in pygame.event.get():
                if event.type == pygame.QUIT: running = False
                
                if event.type == pygame.MOUSEWHEEL:
                    if self.message_box.state == 'maximized':
                        self.message_box.handle_scroll(event)

                if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
                    scale_x = self.screen.get_width() / self.native_surface.get_width()
                    scale_y = self.screen.get_height() / self.native_surface.get_height()
                    click_pos = (event.pos[0] / scale_x, event.pos[1] / scale_y)
                elif event.type == pygame.MOUSEMOTION:
                    scale_x = self.screen.get_width() / self.native_surface.get_width()
                    scale_y = self.screen.get_height() / self.native_surface.get_height()
                    current_pointer_pos = (event.pos[0] / scale_x, event.pos[1] / scale_y)
                elif event.type == pygame.FINGERDOWN:
                    win_w, win_h = self.native_surface.get_size()
                    click_pos = (int(event.x * win_w), int(event.y * win_h))
                elif event.type == pygame.FINGERMOTION:
                    win_w, win_h = self.native_surface.get_size()
                    current_pointer_pos = (int(event.x * win_w), int(event.y * win_h))
                
                if self.game_state == GameState.CATCH_THE_FOOD_MINIGAME and click_pos:
                    self.minigame.handle_event(event, click_pos)
                elif self.game_state == GameState.GARDENING_MINIGAME and click_pos:
                    self.minigame.handle_event(event, click_pos)

            if self.game_state == GameState.CATCH_THE_FOOD_MINIGAME:
                self.minigame.update(current_pointer_pos)
                self.minigame.draw(self.native_surface)
                if self.minigame.game_over_acknowledged:
                    score = self.minigame.score
                    # Process score and rewards from Catch the Food
                    self.pet.stats.happiness = self.pet.stats.clamp(self.pet.stats.happiness + score // 2) # Example reward
                    coins_earned = score // 5
                    self.pet.stats.coins += coins_earned
                    self.add_game_message({"text": f"You earned {coins_earned} coins from Catch the Food! Score: {score}", "notify": False})
                    self.game_state = GameState.PET_VIEW
                    self.minigame = None
            elif self.game_state == GameState.GARDENING_MINIGAME:
                self.minigame.update()
                if self.minigame.is_over:
                    self.game_state = GameState.PET_VIEW
                    self.minigame = None
                else:
                    self.minigame.draw(self.native_surface)
            else:
                if click_pos:
                    if self.game_state == GameState.PET_VIEW:
                        is_maximized_box_click = self.message_box.state == 'maximized' and self.message_box.rect.collidepoint(click_pos)
                        is_minimized_box_click = self.message_box.state == 'minimized' and self.message_box.min_rect.collidepoint(click_pos)

                        if is_maximized_box_click or is_minimized_box_click:
                            self.message_box.toggle_state(lambda: setattr(self, 'unread_messages_count', 0))
                            if self.sound_click: self.sound_click.play()
                        
                        elif self.pet.state != PetState.DEAD:
                            if self.sound_click:
                                if any(rect.collidepoint(click_pos) for rect, _, _ in self.buttons):
                                    self.sound_click.play()
                            if self.pet.state == PetState.SICK and self.pet_click_area.collidepoint(click_pos): self.handle_heal()
                            for rect, name, action in self.buttons:
                                if rect.collidepoint(click_pos): action()
                    elif self.game_state == GameState.INVENTORY_VIEW: self.handle_inventory_clicks(click_pos)
                    elif self.game_state == GameState.SHOP_VIEW: self.handle_shop_clicks(click_pos)
                    elif self.game_state == GameState.ACTIVITIES_VIEW: self.handle_activities_clicks(click_pos)
            
                if self.game_state == GameState.PET_VIEW:
                    self.pet.update(dt, current_hour)
                    
                    for stat in ['happiness', 'fullness', 'discipline', 'energy', 'health']:
                        if getattr(self.pet.stats, stat) > getattr(self.prev_stats, stat):
                            self.stat_flash_timers[stat[:5]] = 1.5
                    for key in list(self.stat_flash_timers.keys()):
                        self.stat_flash_timers[key] -= dt
                        if self.stat_flash_timers[key] <= 0: del self.stat_flash_timers[key]
                    self.update_prev_stats()

                if self.game_state == GameState.PET_VIEW:
                    self.native_surface.fill(current_bg_color)
                    self.native_surface.blit(self.background_image, (0, 0))
                else:
                    self.native_surface.fill(current_bg_color)

                if self.game_state == GameState.PET_VIEW:
                        cx, cy = self.pet_center_x, self.pet_center_y
                        self.pet.draw(self.native_surface, cx, cy, self.font)
                        
                        self.draw_bar(20, 30, self.pet.stats.happiness, (255, 200, 0), "Happiness")
                        self.draw_bar(110, 30, self.pet.stats.fullness, (0, 255, 0), "Fullness")
                        self.draw_bar(200, 30, self.pet.stats.energy, (0, 0, 255), "Energy")
                        self.draw_bar(290, 30, self.pet.stats.health, (255, 0, 0), "Health")
                        self.draw_bar(380, 30, self.pet.stats.discipline, (255, 0, 255), "Discipline")
                        
                        self.message_box.draw()
                        
                        points_surf = self.font.render(f"Coins: {self.pet.stats.coins}", False, COLOR_TEXT)
                        self.native_surface.blit(points_surf, (20, 60))
                        
                        for rect, text, _ in self.buttons:
                            pygame.draw.rect(self.native_surface, COLOR_BTN, rect, border_radius=5)
                            text_surf = self.font.render(text, False, COLOR_TEXT)
                            self.native_surface.blit(text_surf, text_surf.get_rect(center=rect.center))

                elif self.game_state == GameState.INVENTORY_VIEW:
                        self.draw_inventory()
                elif self.game_state == GameState.SHOP_VIEW:
                        self.draw_shop()
                elif self.game_state == GameState.ACTIVITIES_VIEW:
                        self.draw_activities()
                
            scaled_surface = pygame.transform.smoothscale(self.native_surface, self.screen.get_size())
            self.screen.blit(scaled_surface, (0, 0))

            # Draw pop-up message last to ensure it's on top
            pop_up_message, is_pop_up_active = self.message_box.get_pop_up_info()
            if is_pop_up_active:
                pop_up_surf = self.message_box.small_font.render(pop_up_message, True, COLOR_TEXT)
                # Position pop-up relative to the scaled screen for accurate placement
                pop_up_rect = pop_up_surf.get_rect(center=(self.screen.get_width() // 2, 20)) 
                pygame.draw.rect(self.screen, (0, 0, 0, 180), pop_up_rect.inflate(10, 5), border_radius=5)
                self.screen.blit(pop_up_surf, pop_up_rect)
            
            pygame.display.flip()

if __name__ == "__main__":
    print("Initializing GameEngine...")
    engine = GameEngine()
    print("GameEngine initialized. Starting run loop...")
    try:
        engine.run()
    except Exception as e:
        print(f"Error during run loop: {e}")
    finally:
        print("Exiting game. Pygame quit.")
        pygame.quit()