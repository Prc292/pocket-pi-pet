"""
Complete integrated game engine with modern-retro UI
Full integration with your existing codebase
Optimized for 1280x800 touchscreen on Raspberry Pi 3B
"""

import os
import sys
import pygame
from typing import Tuple, Optional, Callable
import datetime
import time

# Import your existing modules
from constants import *
from models import GameState, PetState, PetStats
from database import DatabaseManager
from pet_entity import Pet
from minigames import CatchTheFoodMinigame
from gardening import GardeningGame
from shop import TamagotchiShop

# Override screen dimensions for 1280x800
SCREEN_WIDTH = 1280
SCREEN_HEIGHT = 800

# Retro Color Palette
RETRO_PINK = (255, 111, 145)
RETRO_BLUE = (78, 205, 196)
RETRO_YELLOW = (255, 209, 102)
RETRO_PURPLE = (162, 155, 254)
RETRO_GREEN = (119, 221, 119)
RETRO_ORANGE = (255, 159, 67)
RETRO_DARK = (44, 47, 51)
RETRO_LIGHT = (247, 241, 227)
RETRO_SHADOW = (30, 30, 35)

# Day/Night colors
COLOR_DAY_BG = (135, 206, 235)
COLOR_DUSK_BG = (255, 165, 0)
COLOR_NIGHT_BG = (25, 25, 112)
COLOR_DAWN_BG = (255, 223, 186)


# ==================== UI COMPONENTS ====================

class ModernRetroButton:
    """Touch-friendly button with retro pixel aesthetic"""
    
    def __init__(self, x: int, y: int, width: int, height: int, 
                 text: str, color: Tuple[int, int, int],
                 icon: Optional[str] = None,
                 on_click: Optional[Callable] = None):
        self.rect = pygame.Rect(x, y, width, height)
        self.text = text
        self.color = color
        self.icon = icon
        self.on_click = on_click
        self.pressed = False
        
    def draw(self, surface: pygame.Surface, font: pygame.font.Font):
        """Draw button with retro-modern style"""
        # Shadow
        shadow_rect = self.rect.copy()
        shadow_rect.x += 6
        shadow_rect.y += 6
        pygame.draw.rect(surface, RETRO_SHADOW, shadow_rect, border_radius=8)
        
        # Button press offset
        offset = 3 if self.pressed else 0
        draw_rect = self.rect.copy()
        draw_rect.x += offset
        draw_rect.y += offset
        
        # Dark base
        dark_color = tuple(max(0, c - 30) for c in self.color)
        pygame.draw.rect(surface, dark_color, draw_rect, border_radius=8)
        
        # Light top gradient
        gradient_rect = draw_rect.copy()
        gradient_rect.height //= 2
        light_color = tuple(min(255, c + 20) for c in self.color)
        pygame.draw.rect(surface, light_color, gradient_rect, border_radius=8)
        
        # Glass overlay
        glass_surf = pygame.Surface((draw_rect.width - 8, draw_rect.height // 3), pygame.SRCALPHA)
        glass_surf.fill((255, 255, 255, 40))
        surface.blit(glass_surf, (draw_rect.x + 4, draw_rect.y + 4))
        
        # Border
        pygame.draw.rect(surface, RETRO_DARK, draw_rect, 4, border_radius=8)
        
        # Text rendering
        if self.icon:
            full_text = f"{self.icon} {self.text}"
        else:
            full_text = self.text
            
        text_surf = font.render(full_text, True, RETRO_DARK)
        text_rect = text_surf.get_rect(center=draw_rect.center)
        surface.blit(text_surf, text_rect)
    
    def handle_event(self, pos: Tuple[int, int], event_type: int) -> bool:
        """Handle touch events"""
        if event_type == pygame.MOUSEBUTTONDOWN:
            if self.rect.collidepoint(pos):
                self.pressed = True
                return False
        elif event_type == pygame.MOUSEBUTTONUP:
            if self.pressed and self.rect.collidepoint(pos):
                self.pressed = False
                if self.on_click:
                    self.on_click()
                return True
            self.pressed = False
        return False


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
        label_surf = small_font.render(label_text, True, RETRO_DARK)
        surface.blit(label_surf, (self.rect.x, self.rect.y - 30))
        
        # Border
        border_rect = self.rect.copy()
        border_rect.inflate_ip(8, 8)
        pygame.draw.rect(surface, RETRO_DARK, border_rect, border_radius=6)
        
        # Background
        pygame.draw.rect(surface, RETRO_SHADOW, self.rect, border_radius=4)
        
        # Fill color with flash
        fill_color = self.color
        if self.flash_timer > 0 and int(self.flash_timer * 20) % 2 == 0:
            fill_color = (255, 255, 255)
        
        # Fill bar
        fill_width = int((self.current_value / 100) * (self.rect.width - 8))
        if fill_width > 0:
            fill_rect = pygame.Rect(self.rect.x + 4, self.rect.y + 4, 
                                   fill_width, self.rect.height - 8)
            pygame.draw.rect(surface, fill_color, fill_rect, border_radius=3)
            
            # Chunky pixel pattern
            chunk_size = 8
            for i in range(0, fill_width, chunk_size * 2):
                chunk_rect = pygame.Rect(self.rect.x + 4 + i, self.rect.y + 4, 
                                        min(chunk_size, fill_width - i), self.rect.height - 8)
                dark_fill = tuple(max(0, c - 20) for c in fill_color)
                pygame.draw.rect(surface, dark_fill, chunk_rect)
        
        # Percentage text with outline
        value_text = f"{int(self.current_value)}%"
        value_surf = font.render(value_text, True, RETRO_DARK)
        
        for offset_x, offset_y in [(-1, -1), (1, -1), (-1, 1), (1, 1)]:
            outline_surf = font.render(value_text, True, RETRO_LIGHT)
            surface.blit(outline_surf, (self.rect.centerx - value_surf.get_width() // 2 + offset_x,
                                       self.rect.centery - value_surf.get_height() // 2 + offset_y))
        
        surface.blit(value_surf, (self.rect.centerx - value_surf.get_width() // 2,
                                 self.rect.centery - value_surf.get_height() // 2))


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
        text_surf = font.render(self.message, True, RETRO_DARK)
        padding = 20
        bubble_width = text_surf.get_width() + padding * 2
        bubble_height = text_surf.get_height() + padding * 2
        
        bubble_rect = pygame.Rect(self.x - bubble_width // 2, self.y - bubble_height - 30,
                                 bubble_width, bubble_height)
        
        # Fade animation
        alpha = 255
        if self.timer > self.duration - 0.3:
            alpha = int((self.duration - self.timer) / 0.3 * 255)
        elif self.timer < 0.3:
            alpha = int(self.timer / 0.3 * 255)
        
        # Bubble
        bubble_surf = pygame.Surface((bubble_width, bubble_height), pygame.SRCALPHA)
        pygame.draw.rect(bubble_surf, (*RETRO_LIGHT, alpha), bubble_surf.get_rect(), border_radius=15)
        pygame.draw.rect(bubble_surf, (*RETRO_DARK, alpha), bubble_surf.get_rect(), 4, border_radius=15)
        
        surface.blit(bubble_surf, bubble_rect)
        
        # Text
        text_surf.set_alpha(alpha)
        surface.blit(text_surf, (bubble_rect.x + padding, bubble_rect.y + padding))


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
            tab_surf = pygame.Surface((self.minimized_rect.width, self.minimized_rect.height), 
                                     pygame.SRCALPHA)
            tab_surf.fill((*RETRO_PURPLE, 200))
            pygame.draw.rect(tab_surf, RETRO_DARK, tab_surf.get_rect(), 3, border_radius=8)
            
            text = f"📨 Messages"
            if self.unread_count > 0:
                text += f" ({self.unread_count})"
            text_surf = font.render(text, True, RETRO_LIGHT)
            tab_surf.blit(text_surf, (self.minimized_rect.width // 2 - text_surf.get_width() // 2,
                                     self.minimized_rect.height // 2 - text_surf.get_height() // 2))
            
            surface.blit(tab_surf, self.minimized_rect)
        else:
            log_surf = pygame.Surface((self.rect.width, self.rect.height), pygame.SRCALPHA)
            log_surf.fill((*RETRO_LIGHT, 240))
            pygame.draw.rect(log_surf, RETRO_DARK, log_surf.get_rect(), 4, border_radius=10)
            
            header_surf = small_font.render("MESSAGE LOG", True, RETRO_DARK)
            log_surf.blit(header_surf, (10, 10))
            
            close_text = small_font.render("[TAP TO CLOSE]", True, RETRO_PURPLE)
            log_surf.blit(close_text, (self.rect.width - close_text.get_width() - 10, 10))
            
            y_offset = 50
            visible_messages = self.messages[-12:]
            
            for msg in visible_messages:
                msg_text = f"[{msg['time']}] {msg['text']}"
                msg_surf = small_font.render(msg_text, True, RETRO_DARK)
                
                if msg_surf.get_width() > self.rect.width - 20:
                    msg_text = msg_text[:60] + "..."
                    msg_surf = small_font.render(msg_text, True, RETRO_DARK)
                
                log_surf.blit(msg_surf, (10, y_offset))
                y_offset += 35
                
                if y_offset > self.rect.height - 20:
                    break
            
            surface.blit(log_surf, self.rect)


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
        pygame.display.set_caption("Tamagotchi - Retro Edition")
        
        self.clock = pygame.time.Clock()
        
        # Fonts - larger for 1280x800
        self.font_large = pygame.font.Font(None, 48)
        self.font_medium = pygame.font.Font(None, 36)
        self.font_small = pygame.font.Font(None, 24)
        
        # Database
        self.db = DatabaseManager(DB_FILE)

        # Message log
        self.message_log = ModernMessageLog(950, 120, 300, 500)

        # Pet
        self.pet = Pet(self.db, name="Bobo", message_callback=self.add_game_message)
        self.pet.load()

        # Game state
        self.game_time = datetime.datetime.now()
        self.game_state = GameState.PET_VIEW
        self.minigame = None
        
        # Pet position
        self.pet_center_x = SCREEN_WIDTH // 2
        self.pet_center_y = SCREEN_HEIGHT // 2 + 50
        self.pet_click_area = pygame.Rect(self.pet_center_x - 100, self.pet_center_y - 100, 200, 200)
        
        # UI Components
        self.stat_bars = [
            PixelStatBar(50, 50, 220, 40, "Happy", "😊", RETRO_YELLOW),
            PixelStatBar(300, 50, 220, 40, "Full", "🍔", RETRO_GREEN),
            PixelStatBar(550, 50, 220, 40, "Energy", "⚡", RETRO_BLUE),
            PixelStatBar(800, 50, 220, 40, "Health", "❤️", RETRO_PINK),
            PixelStatBar(1050, 50, 220, 40, "Disc", "💪", RETRO_PURPLE),
        ]
        
        self.buttons = [
            ModernRetroButton(50, 700, 180, 70, "FEED", RETRO_GREEN, "🍔", self.handle_feed),
            ModernRetroButton(250, 700, 180, 70, "PLAY", RETRO_BLUE, "🎮", self.handle_activities),
            ModernRetroButton(450, 700, 180, 70, "TRAIN", RETRO_PURPLE, "💪", self.handle_train),
            ModernRetroButton(650, 700, 180, 70, "SLEEP", RETRO_ORANGE, "😴", self._toggle_sleep),
            ModernRetroButton(850, 700, 180, 70, "SHOP", RETRO_YELLOW, "🛒", self.handle_shop),
            ModernRetroButton(1050, 700, 180, 70, "QUIT", RETRO_PINK, "❌", lambda: sys.exit()),
        ]
        
        self.bubble = MessageBubble(640, 500)
        
        # Inventory buttons
        self.inventory_buttons = []
        self.activities_buttons = []
        
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
        shop = TamagotchiShop()
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
                    item = self.db.get_item("Snack")
                    if item:
                        _, _, _, effect_stat, effect_value = item
                        current_value = getattr(self.pet.stats, effect_stat)
                        setattr(self.pet.stats, effect_stat, self.pet.stats.clamp(current_value + effect_value))
                        self.add_game_message("Fed Bobo a snack!")
                        self.bubble.show("Yummy! 🍪")
                        self.game_state = GameState.PET_VIEW
                        if self.sound_eat:
                            self.sound_eat.play()
                        # Flash the appropriate stat
                        if effect_stat == "fullness":
                            self.stat_bars[1].flash()
                else:
                    # Use inventory item
                    item = self.db.get_item(name)
                    if item:
                        _, _, _, effect_stat, effect_value = item
                        current_value = getattr(self.pet.stats, effect_stat)
                        setattr(self.pet.stats, effect_stat, self.pet.stats.clamp(current_value + effect_value))
                        self.db.update_inventory(name, -1)
                        self.add_game_message(f"Used {name}!")
                        self.bubble.show(f"Thanks! 😊")
                        self.game_state = GameState.PET_VIEW
                        if self.sound_eat:
                            self.sound_eat.play()
                        # Flash appropriate stat
                        stat_index = {"happiness": 0, "fullness": 1, "energy": 2, "health": 3, "discipline": 4}
                        if effect_stat in stat_index:
                            self.stat_bars[stat_index[effect_stat]].flash()
    
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
        coins_surf = self.font_medium.render(f"💰 {self.pet.stats.coins}", True, RETRO_DARK)
        self.screen.blit(coins_surf, (50, 130))
        
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
        title_surf = self.font_large.render("CART", True, RETRO_DARK)
        self.screen.blit(title_surf, (640 - title_surf.get_width() // 2, 280))
        
        self.inventory_buttons.clear()
        
        # Free snack (y=350 instead of 250)
        snack_rect = pygame.Rect(360, 350, 560, 60)
        self.inventory_buttons.append((snack_rect, "Snack"))
        pygame.draw.rect(self.screen, RETRO_YELLOW, snack_rect, border_radius=8)
        pygame.draw.rect(self.screen, RETRO_DARK, snack_rect, 4, border_radius=8)
        snack_text = self.font_medium.render("🍪 Snack (Free)", True, RETRO_DARK)
        self.screen.blit(snack_text, (snack_rect.centerx - snack_text.get_width() // 2,
                                     snack_rect.centery - snack_text.get_height() // 2))
        
        # Inventory items (y_pos starts at 430 instead of 330)
        inventory_items = self.db.get_inventory()
        y_pos = 430
        
        if not inventory_items:
            empty_msg = self.font_small.render("Empty! Buy items from the shop.", True, RETRO_DARK)
            self.screen.blit(empty_msg, (640 - empty_msg.get_width() // 2, y_pos + 30))
        
        for item_name, quantity, _, _, _ in inventory_items:
            item_rect = pygame.Rect(360, y_pos, 560, 60)
            self.inventory_buttons.append((item_rect, item_name))
            pygame.draw.rect(self.screen, RETRO_BLUE, item_rect, border_radius=8)
            pygame.draw.rect(self.screen, RETRO_DARK, item_rect, 4, border_radius=8)
            item_text = self.font_medium.render(f"{item_name} (x{quantity})", True, RETRO_DARK)
            self.screen.blit(item_text, (item_rect.x + 20, item_rect.centery - item_text.get_height() // 2))
            y_pos += 70
        
        # Close (y=620 instead of 520)
        close_rect = pygame.Rect(490, 620, 300, 50)
        self.activities_buttons.append((close_rect, "CLOSE"))
        pygame.draw.rect(self.screen, RETRO_PINK, close_rect, border_radius=8)
        pygame.draw.rect(self.screen, RETRO_DARK, close_rect, 4, border_radius=8)
        close_text = self.font_small.render("Close", True, RETRO_DARK)
        self.screen.blit(close_text, (close_rect.centerx - close_text.get_width() // 2,
                                     close_rect.centery - close_text.get_height() // 2))

    def draw_activities(self):
        """Draw activities screen"""
        panel = pygame.Rect(340, 200, 600, 400)
        pygame.draw.rect(self.screen, RETRO_LIGHT, panel, border_radius=15)
        pygame.draw.rect(self.screen, RETRO_DARK, panel, 5, border_radius=15)
        
        title_surf = self.font_large.render("ACTIVITIES", True, RETRO_DARK)
        self.screen.blit(title_surf, (640 - title_surf.get_width() // 2, 230))
        
        self.activities_buttons.clear()
        
        # Catch the Food
        catch_rect = pygame.Rect(360, 320, 560, 60)
        self.activities_buttons.append((catch_rect, "Catch the Food"))
        pygame.draw.rect(self.screen, RETRO_GREEN, catch_rect, border_radius=8)
        pygame.draw.rect(self.screen, RETRO_DARK, catch_rect, 4, border_radius=8)
        catch_text = self.font_medium.render("🍎 Catch the Food", True, RETRO_DARK)
        self.screen.blit(catch_text, (catch_rect.centerx - catch_text.get_width() // 2,
                                     catch_rect.centery - catch_text.get_height() // 2))
        
        # Gardening
        garden_rect = pygame.Rect(360, 400, 560, 60)
        self.activities_buttons.append((garden_rect, "Gardening"))
        pygame.draw.rect(self.screen, RETRO_ORANGE, garden_rect, border_radius=8)
        pygame.draw.rect(self.screen, RETRO_DARK, garden_rect, 4, border_radius=8)
        garden_text = self.font_medium.render("🌱 Gardening", True, RETRO_DARK)
        self.screen.blit(garden_text, (garden_rect.centerx - garden_text.get_width() // 2,
                                      garden_rect.centery - garden_text.get_height() // 2))
        
        # Close
        close_rect = pygame.Rect(490, 520, 300, 50)
        self.activities_buttons.append((close_rect, "CLOSE"))
        pygame.draw.rect(self.screen, RETRO_PINK, close_rect, border_radius=8)
        pygame.draw.rect(self.screen, RETRO_DARK, close_rect, 4, border_radius=8)
        close_text = self.font_small.render("Close", True, RETRO_DARK)
        self.screen.blit(close_text, (close_rect.centerx - close_text.get_width() // 2,
                                     close_rect.centery - close_text.get_height() // 2))
    
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
            current_pointer_pos = pygame.mouse.get_pos()
            
            # Event handling
            for event in pygame.event.get():
                if event.type == pygame.QUIT:
                    running = False
                
                # Handle minigame events
                if self.game_state == GameState.CATCH_THE_FOOD_MINIGAME and event.type in [pygame.MOUSEBUTTONDOWN, pygame.MOUSEBUTTONUP]:
                    self.minigame.handle_event(event, current_pointer_pos)
                elif self.game_state == GameState.GARDENING_MINIGAME and event.type in [pygame.MOUSEBUTTONDOWN, pygame.MOUSEBUTTONUP]:
                    self.minigame.handle_event(event, current_pointer_pos)
                
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
    print("Starting Tamagotchi - Retro Edition...")
    engine = GameEngine()
    try:
        engine.run()
    except Exception as e:
        import traceback
        print(f"Error: {e}")
        traceback.print_exc()
    finally:
        pygame.quit()