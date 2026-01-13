"""
Complete integrated game engine with modern-retro UI
Full integration with your existing codebase
Optimized for 1280x800 touchscreen on Raspberry Pi 3B
"""

import os
import sys
import pygame
from ui_components import ModernRetroButton
from typing import Tuple, Optional, Callable # Still needed for other classes in main.py
import datetime
import time

# Import your existing modules
from constants import *
from models import GameState, PetState, PetStats
from database import DatabaseManager
from pet_entity import Pet
from minigames import CatchTheFoodMinigame
from gardening import GardeningGame
from shop import PiPetShop


class PixelStatBar:
    """Retro stat bar with smooth animations"""
    
    def __init__(self, x: int, y: int, width: int, height: int,
                 label: str, icon: str, color: Tuple[int, int, int]):
        self.rect = pygame.Rect(x, y, width, height)
        self.label = label
        self.icon = icon
        self.color = color
        self.target_value = 100
        self.current_value = 100
        self.flash_timer = 0
        
    def set_value(self, value: float):
        self.target_value = max(0, min(100, value))
        
    def update(self, dt: float):
        if abs(self.current_value - self.target_value) > 0.1:
            diff = self.target_value - self.current_value
            self.current_value += diff * 5 * dt
        else:
            self.current_value = self.target_value
            
        if self.flash_timer > 0:
            self.flash_timer -= dt
    
    def flash(self):
        self.flash_timer = 1.0
        
    def draw(self, surface: pygame.Surface, font: pygame.font.Font, small_font: pygame.font.Font):
        # Label
        label_text = f"{self.icon} {self.label}"
        label_surface = small_font.render(label_text, True, RETRO_DARK)
        surface.blit(label_surface, (self.rect.x, self.rect.y - 30))
        
        # Border
        border_rect = self.rect.copy()
        border_rect.inflate_ip(8, 8)
        pygame.draw.rect(surface, RETRO_DARK, border_rect, border_radius=STAT_BAR_BORDER_RADIUS)
        
        # Background
        pygame.draw.rect(surface, RETRO_SHADOW, self.rect, border_radius=STAT_BAR_BORDER_RADIUS - 2) # Slightly smaller radius for inner shadow
        
        # Fill color with flash
        fill_color = self.color
        if self.flash_timer > 0 and int(self.flash_timer * 20) % 2 == 0:
            fill_color = (255, 255, 255)
        
        # Fill bar
        fill_width = int((self.current_value / 100) * (self.rect.width - 8))
        if fill_width > 0:
            fill_rect = pygame.Rect(self.rect.x + 4, self.rect.y + 4, 
                                   fill_width, self.rect.height - 8)
            pygame.draw.rect(surface, fill_color, fill_rect, border_radius=STAT_BAR_FILL_BORDER_RADIUS)
            
            # Chunky pixel pattern
            chunk_size = STAT_BAR_CHUNK_SIZE
            for i in range(0, fill_width, chunk_size * 2):
                chunk_rect = pygame.Rect(self.rect.x + 4 + i, self.rect.y + 4, 
                                        min(chunk_size, fill_width - i), self.rect.height - 8)
                dark_fill = tuple(max(0, c - 20) for c in fill_color)
                pygame.draw.rect(surface, dark_fill, chunk_rect)
        
        # Percentage text with outline
        value_text = f"{int(self.current_value)}%"
        value_surface = font.render(value_text, True, RETRO_DARK)
        
        for offset_x, offset_y in [(-1, -1), (1, -1), (-1, 1), (1, 1)]:
            outline_surface = font.render(value_text, True, RETRO_LIGHT)
            surface.blit(outline_surface, (self.rect.centerx - value_surface.get_width() // 2 + offset_x,
                                       self.rect.centery - value_surface.get_height() // 2 + offset_y))
        
        surface.blit(value_surface, (self.rect.centerx - value_surface.get_width() // 2,
                                 self.rect.centery - value_surface.get_height() // 2))


class MessageBubble:
    """Comic-style speech bubble"""
    
    def __init__(self, x: int, y: int, max_width: int = 400):
        self.x = x
        self.y = y
        self.max_width = max_width
        self.message = ""
        self.timer = 0
        self.duration = 3.0
        
    def show(self, message: str, duration: float = 3.0):
        self.message = message
        self.timer = duration
        self.duration = duration
        
    def update(self, dt: float):
        if self.timer > 0:
            self.timer -= dt
            
    def draw(self, surface: pygame.Surface, font: pygame.font.Font):
        if self.timer <= 0 or not self.message:
            return
            
        # Simple single line for now
        text_surface = font.render(self.message, True, RETRO_DARK)
        padding = 20
        bubble_width = text_surface.get_width() + padding * 2
        bubble_height = text_surface.get_height() + padding * 2        
        bubble_rect = pygame.Rect(self.x - bubble_width // 2, self.y - bubble_height - 30,
                                 bubble_width, bubble_height)
        
        # Fade animation
        alpha = 255
        if self.timer > self.duration - 0.3:
            alpha = int((self.duration - self.timer) / 0.3 * 255)
        elif self.timer < 0.3:
            alpha = int(self.timer / 0.3 * 255)
        
                    # Bubble
        bubble_surface = pygame.Surface((bubble_width, bubble_height), pygame.SRCALPHA)
        pygame.draw.rect(bubble_surface, (*RETRO_LIGHT, alpha), bubble_surface.get_rect(), border_radius=15)
        pygame.draw.rect(bubble_surface, (*RETRO_DARK, alpha), bubble_surface.get_rect(), 4, border_radius=15)
        
        surface.blit(bubble_surface, bubble_rect)
        
        # Text
        text_surface.set_alpha(alpha)
        surface.blit(text_surface, (bubble_rect.x + padding, bubble_rect.y + padding))


class ModernMessageLog:
    """Message log UI"""
    
    def __init__(self, x: int, y: int, width: int, height: int):
        self.rect = pygame.Rect(x, y, width, height)
        self.minimized_rect = pygame.Rect(x, y, width, 60)
        self.messages = []
        self.is_minimized = True
        self.unread_count = 0
        
    def add_message(self, text: str):
        timestamp = datetime.datetime.now().strftime("%H:%M")
        self.messages.append({"text": text, "time": timestamp})
        self.unread_count += 1
        
    def toggle(self):
        self.is_minimized = not self.is_minimized
        if not self.is_minimized:
            self.unread_count = 0
    
    def draw(self, surface: pygame.Surface, font: pygame.font.Font, small_font: pygame.font.Font):
        if self.is_minimized:
            tab_surface = pygame.Surface((self.minimized_rect.width, self.minimized_rect.height), 
                                     pygame.SRCALPHA)
            tab_surface.fill((*RETRO_PURPLE, 200))
            pygame.draw.rect(tab_surface, RETRO_DARK, tab_surface.get_rect(), 3, border_radius=8)
            
            text = f"📨 Messages"
            if self.unread_count > 0:
                text += f" ({self.unread_count})"
            text_surface = font.render(text, True, RETRO_LIGHT)
            tab_surface.blit(text_surface, (self.minimized_rect.width // 2 - text_surface.get_width() // 2,
                                     self.minimized_rect.height // 2 - text_surface.get_height() // 2))
            
            surface.blit(tab_surface, self.minimized_rect)
        else:
            log_surface = pygame.Surface((self.rect.width, self.rect.height), pygame.SRCALPHA)
            log_surface.fill((*RETRO_LIGHT, 240))
            pygame.draw.rect(log_surface, RETRO_DARK, log_surface.get_rect(), 4, border_radius=10)
            
            header_surface = small_font.render("MESSAGE LOG", True, RETRO_DARK)
            log_surface.blit(header_surface, (10, 10))
            
            close_surface = small_font.render("[TAP TO CLOSE]", True, RETRO_PURPLE)
            log_surface.blit(close_surface, (self.rect.width - close_surface.get_width() - 10, 10))
            
            y_offset = 50
            visible_messages = self.messages[-12:]
            
            for msg in visible_messages:
                msg_text = f"[{msg['time']}] {msg['text']}"
                msg_surface = small_font.render(msg_text, True, RETRO_DARK)
                
                if msg_surface.get_width() > self.rect.width - 20:
                    msg_text = msg_text[:60] + "..."
                    msg_surface = small_font.render(msg_text, True, RETRO_DARK)
                
                log_surface.blit(msg_surface, (10, y_offset))
                y_offset += 35
                
                if y_offset > self.rect.height - 20:
                    break
            
            surface.blit(log_surface, self.rect)


# ==================== GAME ENGINE ====================

class GameEngine:
    """Enhanced game engine with modern-retro UI"""
    
    def add_game_message(self, message_data):
        """Add message to log"""
        if isinstance(message_data, str):
            text = message_data
        else:
            text = message_data.get("text", "")
        
        if text:
            self.message_log.add_message(text)
    
    def __init__(self):
        pygame.init()
        pygame.mixer.init()
        
        self.screen = pygame.display.set_mode((SCREEN_WIDTH, SCREEN_HEIGHT))
        pygame.display.set_caption("PiPet - Retro Edition")
        
        self.clock = pygame.time.Clock()
        
        # Fonts - larger for 1280x800
        self.font_large = pygame.font.Font(None, 48)
        self.font_medium = pygame.font.Font(None, 36)
        self.font_small = pygame.font.Font(None, 24)
        
        # Database
        self.db = DatabaseManager(DB_FILE)

        # Message log
        self.message_log = ModernMessageLog(MESSAGE_LOG_X, MESSAGE_LOG_Y, MESSAGE_LOG_WIDTH, MESSAGE_LOG_HEIGHT)

        # Pet
        self.pet = Pet(self.db, name="Bobo", message_callback=self.add_game_message)
        self.pet.load()

        # Game state
        self.game_time = datetime.datetime.now()
        self.game_state = GameState.PET_VIEW
        self.minigame = None
        self.last_save_time = time.time()
        
        # Pet position
        self.pet_center_x = PET_CENTER_X
        self.pet_center_y = PET_CENTER_Y
        self.pet_click_area = pygame.Rect(self.pet_center_x - PET_CLICK_AREA_WIDTH // 2, self.pet_center_y - PET_CLICK_AREA_HEIGHT // 2, PET_CLICK_AREA_WIDTH, PET_CLICK_AREA_HEIGHT)
        
        # UI Components
        self.stat_bars = [
            PixelStatBar(50, 50, STAT_BAR_WIDTH, STAT_BAR_HEIGHT, "Happy", "😊", RETRO_YELLOW),
            PixelStatBar(300, 50, STAT_BAR_WIDTH, STAT_BAR_HEIGHT, "Full", "🍔", RETRO_GREEN),
            PixelStatBar(550, 50, STAT_BAR_WIDTH, STAT_BAR_HEIGHT, "Energy", "⚡", RETRO_BLUE),
            PixelStatBar(800, 50, STAT_BAR_WIDTH, STAT_BAR_HEIGHT, "Health", "❤️", RETRO_PINK),
            PixelStatBar(1050, 50, STAT_BAR_WIDTH, STAT_BAR_HEIGHT, "Disc", "💪", RETRO_PURPLE),
        ]
        
        self.buttons = [
            ModernRetroButton(50, BUTTON_Y, BUTTON_WIDTH, BUTTON_HEIGHT, "FEED", RETRO_GREEN, "🍔", self.handle_feed),
            ModernRetroButton(250, BUTTON_Y, BUTTON_WIDTH, BUTTON_HEIGHT, "PLAY", RETRO_BLUE, "🎮", self.handle_activities),
            ModernRetroButton(450, BUTTON_Y, BUTTON_WIDTH, BUTTON_HEIGHT, "TRAIN", RETRO_PURPLE, "💪", self.handle_train),
            ModernRetroButton(650, BUTTON_Y, BUTTON_WIDTH, BUTTON_HEIGHT, "SLEEP", RETRO_ORANGE, "😴", self._toggle_sleep),
            ModernRetroButton(850, BUTTON_Y, BUTTON_WIDTH, BUTTON_HEIGHT, "SHOP", RETRO_YELLOW, "🛒", self.handle_shop),
            ModernRetroButton(1050, BUTTON_Y, BUTTON_WIDTH, BUTTON_HEIGHT, "QUIT", RETRO_PINK, "❌", lambda: sys.exit()),
        ]
        
        self.bubble = MessageBubble(640, 500)
        
        # Inventory buttons
        self.inventory_buttons = []
        self.activities_buttons = []
        self._create_inventory_buttons()
        self._create_activities_buttons()
        
        # Track stat changes for flashing
        self.prev_stats = PetStats()
        self.update_prev_stats()
        
        # Load sounds
        base_path = os.path.dirname(__file__)
        try:
            self.sound_click = pygame.mixer.Sound(os.path.join(base_path, "assets", "audio", "click.wav"))
            self.sound_eat = pygame.mixer.Sound(os.path.join(base_path, "assets", "audio", "eat.wav"))
            self.sound_play = pygame.mixer.Sound(os.path.join(base_path, "assets", "audio", "play.wav"))
            self.sound_heal = pygame.mixer.Sound(os.path.join(base_path, "assets", "audio", "heal.wav"))
        except pygame.error as e:
            print(f"Warning: Could not load sound files. Error: {e}")
            self.sound_click = self.sound_eat = self.sound_play = self.sound_heal = None
    
    def update_prev_stats(self):
        self.prev_stats.fullness = self.pet.stats.fullness
        self.prev_stats.happiness = self.pet.stats.happiness
        self.prev_stats.energy = self.pet.stats.energy
        self.prev_stats.health = self.pet.stats.health
        self.prev_stats.discipline = self.pet.stats.discipline
    
    # ===== Event Handlers =====
    
    def _use_item(self, item_name: str, is_free_item: bool = False):
        item = self.db.get_item(item_name)
        if item:
            _, _, _, effect_stat, effect_value = item
            current_value = getattr(self.pet.stats, effect_stat)
            setattr(self.pet.stats, effect_stat, self.pet.stats.clamp(current_value + effect_value))
            
            if not is_free_item:
                self.db.remove_item_from_inventory(item_name, 1)
                
            self.add_game_message(f"Used {item_name}!")
            self.bubble.show(f"Thanks! 😊")
            
            if self.sound_eat:
                self.sound_eat.play()
            
            # Flash appropriate stat bar
            stat_index = {"happiness": 0, "fullness": 1, "energy": 2, "health": 3, "discipline": 4}
            if effect_stat in stat_index:
                self.stat_bars[stat_index[effect_stat]].flash()

    def _create_inventory_buttons(self):
        buttons = []
        # Free snack
        snack_rect = pygame.Rect(360, 350, 560, 60)
        buttons.append((snack_rect, "Snack"))

        # Inventory items
        inventory_items = self.db.get_inventory()
        y_pos = 430
        for item_name, quantity, _, _, _ in inventory_items:
            item_rect = pygame.Rect(360, y_pos, 560, 60)
            buttons.append((item_rect, item_name, quantity))
            y_pos += 70
        
        # Close button
        close_rect = pygame.Rect(490, 620, 300, 50)
        buttons.append((close_rect, "CLOSE"))
        
        self.inventory_buttons = buttons
    
    def _create_activities_buttons(self):
        buttons = []
        
        # Catch the Food
        catch_rect = pygame.Rect(360, 320, 560, 60)
        buttons.append((catch_rect, "Catch the Food"))
        
        # Gardening
        garden_rect = pygame.Rect(360, 400, 560, 60)
        buttons.append((garden_rect, "Gardening"))
        
        # Close
        close_rect = pygame.Rect(490, 520, 300, 50)
        buttons.append((close_rect, "CLOSE"))
        
        self.activities_buttons = buttons

    def handle_feed(self):
        if self.pet.state == PetState.IDLE:
            if self.sound_click:
                self.sound_click.play()
            self.game_state = GameState.INVENTORY_VIEW
    
    def handle_activities(self):
        if self.pet.state == PetState.IDLE:
            if self.sound_click:
                self.sound_click.play()
            self.game_state = GameState.ACTIVITIES_VIEW
    
    def handle_train(self):
        if self.pet.state == PetState.IDLE or self.pet.state == PetState.SICK:
            if self.sound_click:
                self.sound_click.play()
            self.pet.transition_to(PetState.TRAINING)
            self.bubble.show("Training hard! 💪")
    
    def _toggle_sleep(self):
        if self.sound_click:
            self.sound_click.play()
        if self.pet.state == PetState.SLEEPING:
            self.pet.transition_to(PetState.IDLE)
            self.bubble.show("Yawn... Time to play!")
        else:
            self.pet.transition_to(PetState.SLEEPING)
            self.bubble.show("Zzzzz...")
    
    def handle_shop(self):
        if self.sound_click:
            self.sound_click.play()
        shop = PiPetShop()
        shop.run()
    
    def handle_heal(self):
        if self.pet.state == PetState.SICK:
            if self.sound_heal:
                self.sound_heal.play()
            self.pet.heal()
            self.bubble.show("All better! 😊")
    
    def handle_inventory_clicks(self, click_pos):
        for rect, name in self.inventory_buttons:
            if rect.collidepoint(click_pos):
                if name == "CLOSE":
                    self.game_state = GameState.PET_VIEW
                elif name == "Snack":
                    self._use_item(name, is_free_item=True)
                    self.game_state = GameState.PET_VIEW
                else:
                    self._use_item(name)
                    self.game_state = GameState.PET_VIEW
    
    def handle_activities_clicks(self, click_pos):
        for rect, name in self.activities_buttons:
            if rect.collidepoint(click_pos):
                if name == "CLOSE":
                    self.game_state = GameState.PET_VIEW
                elif name == "Catch the Food":
                    self.minigame = CatchTheFoodMinigame(self.font_medium)
                    self.game_state = GameState.CATCH_THE_FOOD_MINIGAME
                elif name == "Gardening":
                    self.minigame = GardeningGame(self.font_medium, self.db)
                    self.game_state = GameState.GARDENING_MINIGAME
    
    # ===== Drawing Methods =====
    
    def draw_main_view(self):
        """Draw main pet view"""
        # Pet
        self.pet.draw(self.screen, self.pet_center_x, self.pet_center_y, self.font_large)
        
        # Thought bubble
        self.bubble.draw(self.screen, self.font_small)
        
        # Stat bars
        stats = [self.pet.stats.happiness, self.pet.stats.fullness, self.pet.stats.energy,
                self.pet.stats.health, self.pet.stats.discipline]
        for i, bar in enumerate(self.stat_bars):
            bar.set_value(stats[i])
            bar.draw(self.screen, self.font_medium, self.font_small)
        
        # Coins
        coins_surface = self.font_medium.render(f"💰 {self.pet.stats.coins}", True, RETRO_DARK)
        self.screen.blit(coins_surface, (50, 130))
        
        # Buttons
        for button in self.buttons:
            button.draw(self.screen, self.font_medium)
        
        # Message log
        self.message_log.draw(self.screen, self.font_medium, self.font_small)
    
    def draw_inventory(self):
        """Draw inventory screen"""
        # Background panel (moved down by 100px)
        panel = pygame.Rect(340, 250, 600, 500)
        pygame.draw.rect(self.screen, RETRO_LIGHT, panel, border_radius=15)
        pygame.draw.rect(self.screen, RETRO_DARK, panel, 5, border_radius=15)
        
        # Title ("CART" instead of "INVENTORY"), moved down by 100px
        title_surface = self.font_large.render("CART", True, RETRO_DARK)
        self.screen.blit(title_surface, (640 - title_surface.get_width() // 2, 280))
        
        # Display buttons based on pre-generated list
        if not self.inventory_buttons: # Check if inventory is empty
            empty_message = self.font_small.render("Empty! Buy items from the shop.", True, RETRO_DARK)
            self.screen.blit(empty_message, (640 - empty_message.get_width() // 2, 430 + 30))
        
        for button_data in self.inventory_buttons:
            rect, name = button_data[0], button_data[1] # Unpack rect and name
            quantity = button_data[2] if len(button_data) > 2 else 1 # Get quantity if available

            if name == "CLOSE":
                close_surface = self.font_small.render("Close", True, RETRO_DARK)
                pygame.draw.rect(self.screen, RETRO_PINK, rect, border_radius=8)
                pygame.draw.rect(self.screen, RETRO_DARK, rect, 4, border_radius=8)
                self.screen.blit(close_surface, (rect.centerx - close_surface.get_width() // 2,
                                            rect.centery - close_surface.get_height() // 2))
            elif name == "Snack":
                snack_surface = self.font_medium.render("🍪 Snack (Free)", True, RETRO_DARK)
                pygame.draw.rect(self.screen, RETRO_YELLOW, rect, border_radius=8)
                pygame.draw.rect(self.screen, RETRO_DARK, rect, 4, border_radius=8)
                self.screen.blit(snack_surface, (rect.centerx - snack_surface.get_width() // 2,
                                            rect.centery - snack_surface.get_height() // 2))
            else:
                item_surface = self.font_medium.render(f"{name} (x{quantity})", True, RETRO_DARK)
                pygame.draw.rect(self.screen, RETRO_BLUE, rect, border_radius=8)
                pygame.draw.rect(self.screen, RETRO_DARK, rect, 4, border_radius=8)
                self.screen.blit(item_surface, (rect.x + 20, rect.centery - item_surface.get_height() // 2))

    def draw_activities(self):
        """Draw activities screen"""
        panel = pygame.Rect(340, 200, 600, 400)
        pygame.draw.rect(self.screen, RETRO_LIGHT, panel, border_radius=15)
        pygame.draw.rect(self.screen, RETRO_DARK, panel, 5, border_radius=15)
        
        title_surface = self.font_large.render("ACTIVITIES", True, RETRO_DARK)
        self.screen.blit(title_surface, (640 - title_surface.get_width() // 2, 230))
        
        # Display buttons based on pre-generated list
        for rect, name in self.activities_buttons:
            if name == "CLOSE":
                close_surface = self.font_small.render("Close", True, RETRO_DARK)
                pygame.draw.rect(self.screen, RETRO_PINK, rect, border_radius=8)
                pygame.draw.rect(self.screen, RETRO_DARK, rect, 4, border_radius=8)
                self.screen.blit(close_surface, (rect.centerx - close_surface.get_width() // 2,
                                            rect.centery - close_surface.get_height() // 2))
            elif name == "Catch the Food":
                catch_surface = self.font_medium.render("🍎 Catch the Food", True, RETRO_DARK)
                pygame.draw.rect(self.screen, RETRO_GREEN, rect, border_radius=8)
                pygame.draw.rect(self.screen, RETRO_DARK, rect, 4, border_radius=8)
                self.screen.blit(catch_surface, (rect.centerx - catch_surface.get_width() // 2,
                                            rect.centery - catch_surface.get_height() // 2))
            elif name == "Gardening":
                garden_surface = self.font_medium.render("🌱 Gardening", True, RETRO_DARK)
                pygame.draw.rect(self.screen, RETRO_ORANGE, rect, border_radius=8)
                pygame.draw.rect(self.screen, RETRO_DARK, rect, 4, border_radius=8)
                self.screen.blit(garden_surface, (rect.centerx - garden_surface.get_width() // 2,
                                            rect.centery - garden_surface.get_height() // 2))
    
    # ===== Main Loop =====
    
    def run(self):
        """Main game loop"""
        running = True
        last_time = time.time()
        
        while running:
            # Delta time
            current_time = time.time()
            dt = current_time - last_time
            last_time = current_time
            dt = min(dt, 0.1)  # Cap dt to avoid large jumps
            
            # Update game time
            self.game_time += datetime.timedelta(seconds=dt * TIME_SCALE_FACTOR)
            current_hour = self.game_time.hour
            
            # Background color based on time
            if 6 <= current_hour < 18:
                bg_color = COLOR_DAY_BG
            elif 18 <= current_hour < 22:
                bg_color = COLOR_DUSK_BG
            elif 5 <= current_hour < 6:
                bg_color = COLOR_DAWN_BG
            else:
                bg_color = COLOR_NIGHT_BG
            
            # Pointer position for minigames
            current_pointer_position = pygame.mouse.get_pos()
            
            # Event handling
            for event in pygame.event.get():
                if event.type == pygame.QUIT:
                    running = False
                
                # Handle minigame events
                if self.game_state == GameState.CATCH_THE_FOOD_MINIGAME and event.type in [pygame.MOUSEBUTTONDOWN, pygame.MOUSEBUTTONUP]:
                    self.minigame.handle_event(event, current_pointer_position)
                elif self.game_state == GameState.GARDENING_MINIGAME and event.type in [pygame.MOUSEBUTTONDOWN, pygame.MOUSEBUTTONUP]:
                    self.minigame.handle_event(event, current_pointer_position)
                
                # Touch/click events
                if event.type == pygame.MOUSEBUTTONUP:
                    pos = pygame.mouse.get_pos()
                    
                    if self.game_state == GameState.PET_VIEW:
                        # Check message log toggle
                        if self.message_log.is_minimized:
                            if self.message_log.minimized_rect.collidepoint(pos):
                                self.message_log.toggle()
                                if self.sound_click:
                                    self.sound_click.play()
                        else:
                            if self.message_log.rect.collidepoint(pos):
                                self.message_log.toggle()
                                if self.sound_click:
                                    self.sound_click.play()
                        
                        # Check pet click (for healing)
                        if self.pet.state == PetState.SICK:
                            if self.pet_click_area.collidepoint(pos):
                                self.handle_heal()
                        
                        # Check buttons
                        for button in self.buttons:
                            button.handle_event(pos, event.type)
                    
                    elif self.game_state == GameState.INVENTORY_VIEW:
                        self.handle_inventory_clicks(pos)
                    
                    elif self.game_state == GameState.ACTIVITIES_VIEW:
                        self.handle_activities_clicks(pos)
                
                # Button press events
                if event.type == pygame.MOUSEBUTTONDOWN:
                    pos = pygame.mouse.get_pos()
                    if self.game_state == GameState.PET_VIEW:
                        for button in self.buttons:
                            button.handle_event(pos, event.type)
            
            # Update minigames
            if self.game_state == GameState.CATCH_THE_FOOD_MINIGAME:
                self.minigame.update(current_pointer_pos)
                if self.minigame.game_over_acknowledged:
                    score = self.minigame.score
                    self.pet.stats.happiness = self.pet.stats.clamp(self.pet.stats.happiness + score // 2)
                    coins_earned = score // 5
                    self.pet.stats.coins += coins_earned
                    self.add_game_message(f"Earned {coins_earned} coins! Score: {score}")
                    self.stat_bars[0].flash()
                    self.game_state = GameState.PET_VIEW
                    self.minigame = None
            
            elif self.game_state == GameState.GARDENING_MINIGAME:
                self.minigame.update()
                if self.minigame.is_over:
                    self.game_state = GameState.PET_VIEW
                    self.minigame = None
            
            # Update pet and UI
            if self.game_state == GameState.PET_VIEW:
                self.pet.update(dt, current_hour)
                
                # Check for stat increases and flash
                if self.pet.stats.happiness > self.prev_stats.happiness:
                    self.stat_bars[0].flash()
                if self.pet.stats.fullness > self.prev_stats.fullness:
                    self.stat_bars[1].flash()
                if self.pet.stats.energy > self.prev_stats.energy:
                    self.stat_bars[2].flash()
                if self.pet.stats.health > self.prev_stats.health:
                    self.stat_bars[3].flash()
                if self.pet.stats.discipline > self.prev_stats.discipline:
                    self.stat_bars[4].flash()
                
                self.update_prev_stats()
            
            # Update UI components
            for bar in self.stat_bars:
                bar.update(dt)
            self.bubble.update(dt)
            
            # Auto-save logic
            if current_time - self.last_save_time > SAVE_INTERVAL:
                self.pet.save()
                self.last_save_time = current_time
                self.add_game_message("Game saved!")
            
            # Draw
            self.screen.fill(bg_color)
            
            if self.game_state == GameState.PET_VIEW:
                self.draw_main_view()
            elif self.game_state == GameState.INVENTORY_VIEW:
                self.draw_inventory()
            elif self.game_state == GameState.ACTIVITIES_VIEW:
                self.draw_activities()
            elif self.game_state == GameState.CATCH_THE_FOOD_MINIGAME:
                self.minigame.draw(self.screen)
            elif self.game_state == GameState.GARDENING_MINIGAME:
                self.minigame.draw(self.screen)
            
            pygame.display.flip()
            self.clock.tick(FPS)
        
        pygame.quit()


# ==================== MAIN ====================

if __name__ == "__main__":
    print("Starting PiPet - Retro Edition...")
    engine = GameEngine()
    try:
        engine.run()
    except Exception as e:
        import traceback
        print(f"Error: {e}")
        traceback.print_exc()
    finally:
        pygame.quit()