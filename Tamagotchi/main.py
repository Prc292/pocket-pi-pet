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


class Button:
    def __init__(self, x, y, width, height, text, color, text_color=WHITE):
        self.rect = pygame.Rect(x, y, width, height)
        self.text = text
        self.color = color
        self.text_color = text_color
        self.hover = False

    def draw(self, screen, font, color_override=None):
        draw_color = color_override if color_override else (tuple(min(c + 20, 255) for c in self.color) if self.hover else self.color)
        pygame.draw.rect(screen, draw_color, self.rect, border_radius=10)
        pygame.draw.rect(screen, BLACK, self.rect, 2, border_radius=10)
        
        text_surface = font.render(self.text, True, self.text_color)
        text_rect = text_surface.get_rect(center=self.rect.center)
        screen.blit(text_surface, text_rect)

    def is_clicked(self, pos):
        return self.rect.collidepoint(pos)

    def update_hover(self, pos):
        self.hover = self.rect.collidepoint(pos)


class ItemCard:
    def __init__(self, item, x, y, width, height):
        self.item = item
        self.rect = pygame.Rect(x, y, width, height)
        # Adjusted buy button position and size
        self.buy_button = Button(x + 5, y + height - 30, width - 10, 25, 
                                 f"💰 {item['price']}", GREEN, WHITE)
        self.hover = False

        # Load icon image
        self.icon_image = None
        if 'icon_path' in item:
            full_icon_path = os.path.join(ASSETS_PATH, "shop_icons", item['icon_path'])
            try:
                original_icon = pygame.image.load(full_icon_path).convert_alpha()
                icon_size = 48 # Match size used in draw method
                self.icon_image = pygame.transform.scale(original_icon, (icon_size, icon_size))
            except pygame.error as e:
                print(f"Warning: Could not load icon for {item['name']} from {full_icon_path}. Error: {e}")
                self.icon_image = None

    def draw(self, screen, font, small_font):
        # Card background
        color = LIGHT_GRAY if not self.hover else (250, 250, 250)
        pygame.draw.rect(screen, color, self.rect, border_radius=10)
        pygame.draw.rect(screen, DARK_GRAY, self.rect, 2, border_radius=10)

        # Icon
        icon_size = 48
        icon_rect = pygame.Rect(self.rect.x + (self.rect.width - icon_size) // 2, self.rect.y + 5, icon_size, icon_size)
        
        if self.icon_image:
            screen.blit(self.icon_image, icon_rect)
        else:
            pygame.draw.rect(screen, GRAY, icon_rect, border_radius=5)
            # Fallback text if icon fails to load
            icon_text = small_font.render(f"{self.item['id']}.png", True, DARK_GRAY)
            icon_text_rect = icon_text.get_rect(center=icon_rect.center)
            screen.blit(icon_text, icon_text_rect)

        # Item name (centered)
        name_surface = font.render(self.item['name'], True, BLACK)
        name_rect = name_surface.get_rect(centerx=self.rect.centerx, y=self.rect.y + icon_size + 12)
        screen.blit(name_surface, name_rect)

        # Stats (centered)
        y_offset = self.rect.y + icon_size + 12 + name_surface.get_height() + 8
        stats = []
        if 'hunger' in self.item and self.item['hunger']:
            stats.append(f"🍖 H:+{self.item['hunger']}") # Abbreviated for space
        if 'energy' in self.item and self.item['energy']:
            stats.append(f"⚡ E:+{self.item['energy']}") # Abbreviated for space
        if 'happiness' in self.item and self.item['happiness']:
            stats.append(f"😊 HP:+{self.item['happiness']}") # Abbreviated for space
        if 'health' in self.item and self.item['health']:
            stats.append(f"❤️ HL:+{self.item['health']}") # Abbreviated for space

        for stat in stats:
            stat_surface = small_font.render(stat, True, DARK_GRAY)
            stat_rect = stat_surface.get_rect(centerx=self.rect.centerx, y=y_offset)
            screen.blit(stat_surface, stat_rect)
            y_offset += 15 # Reduced spacing
        
        # Buy button
        self.buy_button.draw(screen, small_font)

    def update_hover(self, pos):
        self.hover = self.rect.collidepoint(pos)
        self.buy_button.update_hover(pos)

    def is_buy_clicked(self, pos):
        return self.buy_button.is_clicked(pos)


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

        # Shop UI State
        self.shop_category_buttons = []
        self.shop_item_cards_by_category = {}
        self.shop_content_heights = {}
        self.shop_scroll_offsets = {}
        self.selected_shop_category = 'snacks'
        # Adjusted shop_view_rect to give more vertical space
        self.shop_view_rect = pygame.Rect(20, 100, SCREEN_WIDTH - 40, SCREEN_HEIGHT - 100 - 40) 
        self._setup_shop_ui() # Initialize shop UI
    
    def _setup_shop_ui(self):
        # Category buttons
        button_width = 100
        button_height = 30
        margin_between_buttons = 5
        
        total_buttons_width = (button_width * len(CATEGORIES)) + (margin_between_buttons * (len(CATEGORIES) - 1))
        start_x = (SCREEN_WIDTH - total_buttons_width) // 2
        
        self.shop_category_buttons.clear()
        for i, cat in enumerate(CATEGORIES):
            btn = Button(start_x + i * (button_width + margin_between_buttons), 60, # Centered, adjusted y
                        button_width, button_height, cat['name'], cat['color'])
            btn.category_id = cat['id']
            self.shop_category_buttons.append(btn)
        
        # Initialize scroll offsets for each category
        self.shop_scroll_offsets = {btn.category_id: 0 for btn in self.shop_category_buttons}

        self._update_shop_item_cards()

    def _update_shop_item_cards(self):
        # Store cards per category for independent scrolling
        self.shop_item_cards_by_category = {} 
        self.shop_content_heights = {} # Store content height per category
        
        card_width = 80 # Adjusted for smaller screen
        card_height = 120 # Adjusted for smaller screen
        cards_per_row = 1 # Now 1 card per column
        margin = 10 # Margin between cards vertically

        # Determine start_y for cards relative to the shop_view_rect
        start_y_cards = 0
        
        for category_btn in self.shop_category_buttons:
            category_id = category_btn.category_id
            items = SHOP_ITEMS.get(category_id, [])
            
            # Calculate total width for cards in this column, assuming 1 card per row for vertical stacking
            total_cards_width_for_col = card_width 

            # Calculate start_x for cards to center them under their category button
            start_x_cards_for_col = category_btn.rect.x + (category_btn.rect.width - card_width) // 2
            
            current_category_cards = []
            max_rows = 0
            if items:
                max_rows = len(items) # Each item is a new row in its column

            for i, item in enumerate(items):
                row = i
                col = 0 # Always the first column in its category's vertical stack
                
                # Position relative to the top-left of the shop_view_rect
                x = category_btn.rect.x + (category_btn.rect.width - card_width) // 2
                y = start_y_cards + row * (card_height + margin) + self.shop_view_rect.y
                
                card = ItemCard(item, x, y, card_width, card_height)
                current_category_cards.append(card)
            
            self.shop_item_cards_by_category[category_id] = current_category_cards
            
            # Recalculate shop_content_height for this category
            if items:
                self.shop_content_heights[category_id] = max_rows * (card_height + margin) - margin
            else:
                self.shop_content_heights[category_id] = 0

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
        self.native_surface.fill((230, 230, 250)) # Light background

        # Title
        title = self.font.render("🏪 Pet Shop", True, BLACK)
        self.native_surface.blit(title, (50, 30))

        # Coins display
        coins_bg = pygame.Rect(SCREEN_WIDTH - 120, 10, 100, 30) # Adjusted size and position
        pygame.draw.rect(self.native_surface, YELLOW, coins_bg, border_radius=15)
        pygame.draw.rect(self.native_surface, BLACK, coins_bg, 2, border_radius=15)
        coins_text = self.font.render(f"💰 {self.pet.stats.coins}", True, BLACK)
        coins_rect = coins_text.get_rect(center=coins_bg.center)
        self.native_surface.blit(coins_text, coins_rect)

        # Message box (using existing add_game_message functionality)
        # The message will be displayed as a pop-up by the GameEngine's run loop

        # Category buttons
        mouse_pos = pygame.mouse.get_pos()
        scaled_mouse_pos = (mouse_pos[0] / (self.screen.get_width() / self.native_surface.get_width()),
                            mouse_pos[1] / (self.screen.get_height() / self.native_surface.get_height()))
        
        for category_btn in self.shop_category_buttons:
            category_btn.update_hover(scaled_mouse_pos)
            # Highlight selected category
            btn_color = category_btn.color
            if category_btn.category_id == self.selected_shop_category:
                btn_color = tuple(min(c + 50, 255) for c in btn_color) # Brighter if selected
            category_btn.draw(self.native_surface, self.font, color_override=btn_color)

        
        # Item cards - drawn onto scrollable surfaces, one for each category
        # Get mouse position for hover effects
        # scaled_mouse_pos is already calculated in the main run loop.

        for category_btn in self.shop_category_buttons:
            category_id = category_btn.category_id
            cards_in_category = self.shop_item_cards_by_category.get(category_id, [])
            category_content_height = self.shop_content_heights.get(category_id, 0)

            # Define the visible area for this category's items
            # The top of the items starts just below the category buttons
            column_view_rect = pygame.Rect(category_btn.rect.x, category_btn.rect.bottom + 5, # 5px margin below button
                                          category_btn.rect.width, SCREEN_HEIGHT - category_btn.rect.bottom - 5 - 30) # 30px for inventory/bottom UI
            
            # Ensure column_view_rect height is not negative
            if column_view_rect.height < 0:
                column_view_rect.height = 0

            # Create a dedicated surface for this category's scrollable content
            # The height of this surface is its VIEWABLE height, not total content height
            category_scroll_surface = pygame.Surface((column_view_rect.width, column_view_rect.height), pygame.SRCALPHA)
            category_scroll_surface.fill((230, 230, 250, 0)) # Transparent background

            # Get this category's scroll offset
            current_scroll_offset = self.shop_scroll_offsets.get(category_id, 0)

            for card in cards_in_category:
                # Adjust card's y-position relative to the category_scroll_surface
                # The card's original y is relative to native_surface. We need its y relative to the top of its column.
                # We need to consider the column_view_rect.y as the offset for cards' y position
                card_y_relative_to_column_top = card.rect.y - column_view_rect.y 
                
                # Draw card onto the category_scroll_surface
                # The card's x-position needs to be relative to the category_scroll_surface's top-left
                temp_card = ItemCard(card.item, card.rect.x - column_view_rect.x, card_y_relative_to_column_top - current_scroll_offset, card.rect.width, card.rect.height)
                
                # Check if card is visible within the column_view_rect for hover detection
                if column_view_rect.collidepoint(scaled_mouse_pos):
                    # Adjust mouse_pos for hover detection relative to the card's position on the scrollable surface
                    adjusted_mouse_pos_for_hover = (scaled_mouse_pos[0] - column_view_rect.x, scaled_mouse_pos[1] - column_view_rect.y + current_scroll_offset)
                    temp_card.update_hover(adjusted_mouse_pos_for_hover)
                else:
                    temp_card.hover = False

                temp_card.draw(category_scroll_surface, self.font, self.message_box.small_font)
            
            # Blit the visible part of the category_scroll_surface onto the native_surface
            self.native_surface.blit(category_scroll_surface, column_view_rect.topleft)

            # Draw Scroll bar for this column
            if category_content_height > column_view_rect.height:
                scrollbar_track_rect = pygame.Rect(column_view_rect.right + 2, column_view_rect.top, 8, column_view_rect.height)
                pygame.draw.rect(self.native_surface, DARK_GRAY, scrollbar_track_rect, border_radius=4)

                thumb_height = max(10, column_view_rect.height * column_view_rect.height // category_content_height)
                scroll_range = category_content_height - column_view_rect.height
                
                thumb_y_pos = 0
                if scroll_range > 0: # Avoid division by zero
                    thumb_y_pos = (current_scroll_offset * (column_view_rect.height - thumb_height) // scroll_range)

                scrollbar_thumb_rect = pygame.Rect(scrollbar_track_rect.x, column_view_rect.top + thumb_y_pos, scrollbar_track_rect.width, thumb_height)
                pygame.draw.rect(self.native_surface, GRAY, scrollbar_thumb_rect, border_radius=4)

        # Inventory preview - simplified for now
        inv_title = self.font.render(f"🎒 Your Inventory", True, BLACK)
        self.native_surface.blit(inv_title, (50, SCREEN_HEIGHT - 30))

    def _buy_shop_item(self, item):
        if self.pet.stats.coins >= item['price']:
            self.pet.stats.coins -= item['price']
            # Add item to inventory (you'll need to implement a proper inventory system)
            # For now, let's just use the existing db.add_item_to_inventory if applicable
            # Or directly apply effects if items are consumed immediately
            
            # Example: Apply immediate effects
            for stat_effect in ['hunger', 'energy', 'happiness', 'health']:
                if stat_effect in item:
                    current_value = getattr(self.pet.stats, stat_effect)
                    setattr(self.pet.stats, stat_effect, self.pet.stats.clamp(current_value + item[stat_effect]))

            self.add_game_message({"text": f"You bought {item['name']} for {item['price']} coins! 🎉", "notify": True})
            self.db.add_item_to_inventory(item['name']) # Add to generic inventory
        else:
            self.add_game_message({"text": f"Not enough coins! Need {item['price'] - self.pet.stats.coins} more.", "notify": True})

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
        # Click detection for category buttons
        for btn in self.shop_category_buttons:
            if btn.is_clicked(click_pos):
                self.selected_shop_category = btn.category_id
                self._update_shop_item_cards() # Re-layout cards for new category
                self.shop_scroll_offsets[self.selected_shop_category] = 0 # Reset scroll for new category
                self.add_game_message({"text": f"Browsing {btn.text}", "notify": False})
                return # Category button click handled

        # Click detection for item cards in the currently selected category
        cards_in_selected_category = self.shop_item_cards_by_category.get(self.selected_shop_category, [])
        
        # Find the currently selected category button
        selected_category_btn = None
        for btn in self.shop_category_buttons:
            if btn.category_id == self.selected_shop_category:
                selected_category_btn = btn
                break

        if selected_category_btn:
            # Define the visible area for this category's items
            column_view_rect = pygame.Rect(selected_category_btn.rect.x, selected_category_btn.rect.bottom + 5,
                                          selected_category_btn.rect.width, SCREEN_HEIGHT - selected_category_btn.rect.bottom - 5 - 30)
            
            # Adjust click_pos to be relative to the scrollable surface for accurate card collision
            # Adjusted click_pos to be relative to the column_view_rect's top-left for internal card collision checks
            relative_click_pos = (click_pos[0] - column_view_rect.x, click_pos[1] - column_view_rect.y + self.shop_scroll_offsets[self.selected_shop_category])
            
            for card in cards_in_selected_category:
                # Check if the raw click is within the column_view_rect (visible area)
                if column_view_rect.collidepoint(click_pos):
                    # Now, check if the buy button of the card (adjusted for scroll and relative to column) was clicked
                    # The card's rect is already in absolute screen coordinates, so we need to adjust the click_pos
                    # to be relative to the card for its internal is_buy_clicked method.
                    
                    # Create a temporary rect for the card in column_view_rect's coordinate system, adjusted for scroll
                    card_in_column_coords = pygame.Rect(card.rect.x - column_view_rect.x, card.rect.y - column_view_rect.y - self.shop_scroll_offsets[self.selected_shop_category], card.rect.width, card.rect.height);

                    if card_in_column_coords.collidepoint(relative_click_pos) and card.is_buy_clicked(relative_click_pos):
                        self._buy_shop_item(card.item)
                        return # Item buy handled


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
            # Calculate scaled_mouse_pos once per frame
            mouse_pos = pygame.mouse.get_pos()
            scale_x = self.screen.get_width() / self.native_surface.get_width()
            scale_y = self.screen.get_height() / self.native_surface.get_height()
            scaled_mouse_pos = (mouse_pos[0] / scale_x, mouse_pos[1] / scale_y)

            current_pointer_pos = (self.pet_center_x, SCREEN_HEIGHT - 50) # Initialize with a reasonable default
            for event in pygame.event.get():
                if event.type == pygame.QUIT: running = False
                
                if event.type == pygame.MOUSEWHEEL:
                    if self.message_box.state == 'maximized':
                        self.message_box.handle_scroll(event)
                    elif self.game_state == GameState.SHOP_VIEW:
                        # Determine which category column the mouse is over
                        mouse_x, mouse_y = scaled_mouse_pos
                        
                        hovered_category_btn = None
                        for category_btn in self.shop_category_buttons:
                            # Define a simplified rect for hover detection over the column's visible area
                            # This needs to include the button itself and the items area below it.
                            temp_column_area_rect = pygame.Rect(category_btn.rect.x, category_btn.rect.y,
                                                               category_btn.rect.width, SCREEN_HEIGHT - category_btn.rect.y)
                            
                            if temp_column_area_rect.collidepoint(mouse_x, mouse_y):
                                hovered_category_btn = category_btn
                                break
                        
                        if hovered_category_btn:
                            category_id = hovered_category_btn.category_id
                            # Define the visible area for this category's items (same as in draw_shop)
                            column_view_rect = pygame.Rect(hovered_category_btn.rect.x, hovered_category_btn.rect.bottom + 5,
                                                          hovered_category_btn.rect.width, SCREEN_HEIGHT - hovered_category_btn.rect.bottom - 5 - 30)
                            
                            if column_view_rect.height < 0:
                                column_view_rect.height = 0

                            current_scroll_offset = self.shop_scroll_offsets.get(category_id, 0)
                            category_content_height = self.shop_content_heights.get(category_id, 0)

                            new_scroll_offset = current_scroll_offset - event.y * 10 # Scroll faster
                            self.shop_scroll_offsets[category_id] = max(0, min(new_scroll_offset, category_content_height - column_view_rect.height))

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
        import traceback
        print(f"Error during run loop: {e}")
        traceback.print_exc()
    finally:
        print("Exiting game. Pygame quit.")
        pygame.quit()