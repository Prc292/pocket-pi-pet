import pygame
import sys

# Initialize Pygame
pygame.init()

# Constants
SCREEN_WIDTH = 1280
SCREEN_HEIGHT = 800
FPS = 30


# Main UI color scheme (imported from main game claude.py)
RETRO_DARK = (32, 36, 44)
RETRO_LIGHT = (249, 245, 255)
RETRO_PINK = (255, 105, 180)
RETRO_GREEN = (0, 210, 110)
RETRO_ORANGE = (255, 163, 72)
RETRO_BLUE = (56, 130, 255)
RETRO_DARKER = (20, 22, 28)
RETRO_HEADER = (44, 48, 60)
RETRO_CARD = (240, 232, 255)
RETRO_BORDER = (94, 96, 110)
RETRO_WHITE = (255, 255, 255)
RETRO_BLACK = (0, 0, 0)
RETRO_GOLD = (255, 215, 0)
RETRO_DARK_GOLD = (218, 165, 32)
RETRO_GRAY = (203, 213, 224)
RETRO_DARK_GRAY = (74, 85, 104)

# For compatibility with old variable names in logic
DARK_BG = RETRO_DARK
DARKER_BG = RETRO_DARKER
HEADER_BG = RETRO_HEADER
CONTENT_BG = RETRO_LIGHT
LIGHT_BG = RETRO_CARD
CARD_BG = RETRO_CARD
WHITE = RETRO_WHITE
BLACK = RETRO_BLACK
GOLD = RETRO_GOLD
DARK_GOLD = RETRO_DARK_GOLD
PINK = RETRO_PINK
ORANGE = RETRO_ORANGE
BLUE = RETRO_BLUE
GREEN = RETRO_GREEN
DARK_GREEN = RETRO_GREEN
GRAY = RETRO_GRAY
DARK_GRAY = RETRO_DARK_GRAY
BORDER_GRAY = RETRO_BORDER

# Shop items database
SHOP_ITEMS = {
    'snacks': [
        {'id': 'cookie', 'name': 'Cookie', 'price': 5, 'emoji': '🍪', 'hunger': 10, 'energy': 5, 'happiness': 5},
        {'id': 'candy', 'name': 'Candy', 'price': 3, 'emoji': '🍬', 'hunger': 5, 'energy': 3, 'happiness': 10},
        {'id': 'chocolate', 'name': 'Chocolate', 'price': 8, 'emoji': '🍫', 'hunger': 12, 'energy': 8, 'happiness': 15},
        {'id': 'lollipop', 'name': 'Lollipop', 'price': 4, 'emoji': '🍭', 'hunger': 5, 'energy': 2, 'happiness': 8},
        {'id': 'donut', 'name': 'Donut', 'price': 7, 'emoji': '🍩', 'hunger': 15, 'energy': 5, 'happiness': 12},
        {'id': 'ice_cream', 'name': 'Ice Cream', 'price': 10, 'emoji': '🍦', 'hunger': 18, 'energy': 5, 'happiness': 20},
        {'id': 'popcorn', 'name': 'Popcorn', 'price': 6, 'emoji': '🍿', 'hunger': 8, 'energy': 3, 'happiness': 7},
        {'id': 'chips', 'name': 'Chips', 'price': 5, 'emoji': '🥔', 'hunger': 10, 'energy': 4, 'happiness': 6},
    ],
    'foods': [
        {'id': 'apple', 'name': 'Apple', 'price': 5, 'emoji': '🍎', 'hunger': 15, 'energy': 8, 'health': 5},
        {'id': 'banana', 'name': 'Banana', 'price': 4, 'emoji': '🍌', 'hunger': 12, 'energy': 10, 'health': 3},
        {'id': 'burger', 'name': 'Burger', 'price': 15, 'emoji': '🍔', 'hunger': 35, 'energy': 15, 'happiness': 10},
        {'id': 'pizza', 'name': 'Pizza', 'price': 12, 'emoji': '🍕', 'hunger': 30, 'energy': 12, 'happiness': 15},
        {'id': 'sandwich', 'name': 'Sandwich', 'price': 10, 'emoji': '🥪', 'hunger': 25, 'energy': 10, 'health': 5},
        {'id': 'rice', 'name': 'Rice Bowl', 'price': 8, 'emoji': '🍚', 'hunger': 20, 'energy': 12, 'health': 8},
        {'id': 'noodles', 'name': 'Noodles', 'price': 9, 'emoji': '🍜', 'hunger': 22, 'energy': 10, 'happiness': 8},
        {'id': 'sushi', 'name': 'Sushi', 'price': 18, 'emoji': '🍣', 'hunger': 28, 'energy': 15, 'health': 10},
    ],
    'drinks': [
        {'id': 'water', 'name': 'Water', 'price': 2, 'emoji': '💧', 'hunger': 5, 'energy': 3, 'health': 5},
        {'id': 'juice', 'name': 'Juice', 'price': 6, 'emoji': '🧃', 'hunger': 10, 'energy': 8, 'happiness': 5},
        {'id': 'soda', 'name': 'Soda', 'price': 5, 'emoji': '🥤', 'hunger': 8, 'energy': 5, 'happiness': 10},
        {'id': 'milk', 'name': 'Milk', 'price': 4, 'emoji': '🥛', 'hunger': 12, 'energy': 5, 'health': 8},
        {'id': 'tea', 'name': 'Tea', 'price': 5, 'emoji': '🍵', 'hunger': 5, 'energy': 10, 'health': 5},
        {'id': 'smoothie', 'name': 'Smoothie', 'price': 10, 'emoji': '🥤', 'hunger': 15, 'energy': 12, 'health': 10},
    ],
    'energy': [
        {'id': 'energy_red', 'name': 'Red Bull', 'price': 15, 'emoji': '⚡', 'hunger': 5, 'energy': 30, 'happiness': 5},
        {'id': 'energy_blue', 'name': 'Blue Energy', 'price': 15, 'emoji': '💙', 'hunger': 5, 'energy': 30, 'happiness': 5},
        {'id': 'energy_green', 'name': 'Green Power', 'price': 15, 'emoji': '💚', 'hunger': 5, 'energy': 30, 'happiness': 5},
        {'id': 'sports_drink', 'name': 'Sports Drink', 'price': 12, 'emoji': '🥤', 'hunger': 8, 'energy': 25, 'health': 5},
        {'id': 'protein', 'name': 'Protein Shake', 'price': 18, 'emoji': '🥤', 'hunger': 20, 'energy': 20, 'health': 10},
    ],
}

CATEGORIES = [
    {'id': 'snacks', 'name': '🍪 SNACKS', 'color': RETRO_PINK},
    {'id': 'foods', 'name': '🍔 FOODS', 'color': RETRO_ORANGE},
    {'id': 'drinks', 'name': '🥤 DRINKS', 'color': RETRO_BLUE},
    {'id': 'energy', 'name': '⚡ ENERGY', 'color': RETRO_GREEN},
]


class Button:
    def __init__(self, x, y, width, height, text, color, text_color=RETRO_WHITE):
        self.rect = pygame.Rect(x, y, width, height)
        self.text = text
        self.color = color
        self.original_color = color
        self.text_color = text_color
        self.hover = False

    def draw(self, screen, font):
        # Main UI button style: border RETRO_DARK, hover brightening
        if self.hover:
            color = tuple(min(c + 32, 255) for c in self.color)
        else:
            color = self.color
        pygame.draw.rect(screen, color, self.rect, border_radius=10)
        pygame.draw.rect(screen, RETRO_DARK, self.rect, 3, border_radius=10)
        text_surface = font.render(self.text, True, self.text_color)
        text_rect = text_surface.get_rect(center=self.rect.center)
        screen.blit(text_surface, text_rect)

    def update_hover(self, pos):
        self.hover = self.rect.collidepoint(pos)

    def is_clicked(self, pos):
        return self.rect.collidepoint(pos)


class ItemCard:
    def __init__(self, item, x, y, width, height):
        self.item = item
        self.rect = pygame.Rect(x, y, width, height)
        self.hover = False
        # Buy button positioned at bottom of card
        self.buy_button = Button(
            x + 10,
            y + height - 35,
            width - 20,
            28,
            f"💰 {item['price']}",
            RETRO_GREEN,
            text_color=RETRO_WHITE
        )

    def draw(self, screen, font, small_font, emoji_font):
        # Card background with hover effect
        if self.hover:
            bg_color = tuple(min(c + 16, 255) for c in RETRO_CARD)
        else:
            bg_color = RETRO_CARD
        pygame.draw.rect(screen, bg_color, self.rect, border_radius=14)
        pygame.draw.rect(screen, RETRO_BORDER, self.rect, 3, border_radius=14)

        # Icon area (64x64) - centered at top
        icon_x = self.rect.centerx - 32
        icon_y = self.rect.y + 10
        icon_rect = pygame.Rect(icon_x, icon_y, 64, 64)
        pygame.draw.rect(screen, RETRO_GRAY, icon_rect, border_radius=8)
        pygame.draw.rect(screen, RETRO_BORDER, icon_rect, 2, border_radius=8)

        # Draw emoji in icon area
        emoji_surface = emoji_font.render(self.item['emoji'], True, RETRO_DARK)
        emoji_rect = emoji_surface.get_rect(center=icon_rect.center)
        screen.blit(emoji_surface, emoji_rect)

        # Item name
        name_surface = font.render(self.item['name'], True, RETRO_DARK)
        name_rect = name_surface.get_rect(centerx=self.rect.centerx, y=self.rect.y + 82)
        screen.blit(name_surface, name_rect)

        # Stats
        y_offset = 102
        stats = []
        if 'hunger' in self.item and self.item['hunger']:
            stats.append(f"🍖+{self.item['hunger']}")
        if 'energy' in self.item and self.item['energy']:
            stats.append(f"⚡+{self.item['energy']}")
        if 'happiness' in self.item and self.item['happiness']:
            stats.append(f"😊+{self.item['happiness']}")
        if 'health' in self.item and self.item['health']:
            stats.append(f"❤️+{self.item['health']}")

        stats_text = ' '.join(stats)
        stat_surface = small_font.render(stats_text, True, RETRO_DARK_GRAY)
        stat_rect = stat_surface.get_rect(centerx=self.rect.centerx, y=self.rect.y + y_offset)
        screen.blit(stat_surface, stat_rect)

        # Buy button (RETRO_GREEN for positive, hover brightens)
        self.buy_button.draw(screen, small_font)

    def update_hover(self, pos):
        self.hover = self.rect.collidepoint(pos)
        self.buy_button.update_hover(pos)

    def is_buy_clicked(self, pos):
        return self.buy_button.is_clicked(pos)


class PiPetShop:
    def __init__(self):
        self.screen = pygame.display.set_mode((SCREEN_WIDTH, SCREEN_HEIGHT))
        pygame.display.set_caption("🏪 PiPet Shop")
        self.clock = pygame.time.Clock()

        # Main UI fonts (match claude.py)
        self.font_large = pygame.font.Font(None, 44)
        self.font_medium = pygame.font.Font(None, 28)
        self.font_small = pygame.font.Font(None, 18)
        self.emoji_font = pygame.font.Font(None, 52)
        self.coin_font = pygame.font.Font(None, 34)

        # For compatibility with old variable names
        self.title_font = self.font_large
        self.font = self.font_medium
        self.small_font = self.font_small

        # Game state
        self.coins = 100
        self.inventory = []
        self.message = "Welcome to the shop!"
        self.message_timer = 0
        self.selected_category = 'snacks'

        # Scroll
        self.scroll_offset = 0
        self.max_scroll = 0

        # UI elements
        self.category_buttons = []
        self.item_cards = []

        # Close button
        self.close_button = Button(
            SCREEN_WIDTH // 2 - 150,  # center
            SCREEN_HEIGHT - 80,       # 80px from bottom
            300,
            50,
            "CLOSE",
            RETRO_PINK,
            text_color=RETRO_DARK
        )

        self.setup_ui()
    def draw_close_button(self):
        self.close_button.draw(self.screen, self.font_small)

    def handle_close_button(self, pos):
        if self.close_button.is_clicked(pos):
            return True
        return False

    def setup_ui(self):
        # Create category buttons
        button_width = 180
        button_height = 40
        start_x = 20
        gap = 10
        
        for i, cat in enumerate(CATEGORIES):
            x = start_x + i * (button_width + gap)
            btn = Button(x, 90, button_width, button_height, cat['name'], cat['color'])
            btn.category_id = cat['id']
            self.category_buttons.append(btn)

        self.update_item_cards()

    def update_item_cards(self):
        self.item_cards = []
        items = SHOP_ITEMS[self.selected_category]
        
        card_width = 170
        card_height = 180
        cards_per_row = 4
        margin = 20
        start_x = 30
        start_y = 150

        for i, item in enumerate(items):
            row = i // cards_per_row
            col = i % cards_per_row
            x = start_x + col * (card_width + margin)
            y = start_y + row * (card_height + margin)
            
            card = ItemCard(item, x, y, card_width, card_height)
            self.item_cards.append(card)
        
        # Calculate max scroll
        total_rows = (len(items) + cards_per_row - 1) // cards_per_row
        content_height = total_rows * (card_height + margin)
        visible_height = 340
        self.max_scroll = max(0, content_height - visible_height)

    def buy_item(self, item):
        if self.coins >= item['price']:
            self.coins -= item['price']
            self.inventory.append(item)
            self.message = f"Bought {item['name']} for {item['price']} coins! 🎉"
            self.message_timer = 120  # Show for 2 seconds at 60 FPS
        else:
            self.message = f"Not enough coins! Need {item['price'] - self.coins} more."
            self.message_timer = 120

    def draw_header(self):
        # Header background
        header_rect = pygame.Rect(0, 0, SCREEN_WIDTH, 80)
        pygame.draw.rect(self.screen, RETRO_HEADER, header_rect)
        pygame.draw.rect(self.screen, RETRO_DARK, (0, 77, SCREEN_WIDTH, 3))

        # Shop title
        title = self.font_large.render("🏪 PET SHOP", True, RETRO_GOLD)
        self.screen.blit(title, (30, 25))

        # Coins display
        coin_rect = pygame.Rect(SCREEN_WIDTH - 200, 20, 170, 45)
        pygame.draw.rect(self.screen, RETRO_GOLD, coin_rect, border_radius=25)
        pygame.draw.rect(self.screen, RETRO_DARK_GOLD, coin_rect, 3, border_radius=25)

        coin_text = self.coin_font.render(f"💰 {self.coins}", True, RETRO_DARK)
        coin_text_rect = coin_text.get_rect(center=coin_rect.center)
        self.screen.blit(coin_text, coin_text_rect)

    def draw_message(self):
        if self.message_timer > 0:
            msg_rect = pygame.Rect(200, 90, 400, 35)
            pygame.draw.rect(self.screen, RETRO_BLUE, msg_rect, border_radius=10)
            pygame.draw.rect(self.screen, RETRO_DARK, msg_rect, 2, border_radius=10)
            msg_surface = self.font_medium.render(self.message, True, RETRO_WHITE)
            msg_rect_center = msg_surface.get_rect(center=msg_rect.center)
            self.screen.blit(msg_surface, msg_rect_center)
            self.message_timer -= 1

    def draw_category_tabs(self):
        # Tabs background
        tabs_rect = pygame.Rect(0, 80, SCREEN_WIDTH, 60)
        pygame.draw.rect(self.screen, RETRO_DARKER, tabs_rect)
        pygame.draw.rect(self.screen, RETRO_DARK, (0, 137, SCREEN_WIDTH, 2))
        # Draw buttons
        for btn in self.category_buttons:
            if btn.category_id == self.selected_category:
                btn.color = btn.original_color
            else:
                btn.color = RETRO_DARK_GRAY
            btn.draw(self.screen, self.font_medium)

    def draw_main_content(self):
        # Content background
        content_rect = pygame.Rect(0, 140, SCREEN_WIDTH, 340)
        pygame.draw.rect(self.screen, RETRO_LIGHT, content_rect)
        # Create clipping region for scroll
        clip_rect = pygame.Rect(0, 140, SCREEN_WIDTH, 340)
        self.screen.set_clip(clip_rect)
        # Draw item cards with scroll offset
        for card in self.item_cards:
            adjusted_rect = card.rect.copy()
            adjusted_rect.y -= self.scroll_offset
            # Only draw if visible
            if adjusted_rect.bottom > 140 and adjusted_rect.top < 480:
                # Temporarily adjust card position for drawing
                original_y = card.rect.y
                card.rect.y = adjusted_rect.y
                card.buy_button.rect.y = adjusted_rect.y + card.rect.height - 35
                card.draw(self.screen, self.font_medium, self.font_small, self.emoji_font)
                # Restore original position
                card.rect.y = original_y
                card.buy_button.rect.y = original_y + card.rect.height - 35
        self.screen.set_clip(None)

    def draw_inventory(self):
        # Inventory background
        inv_rect = pygame.Rect(0, 480, SCREEN_WIDTH, 120)
        pygame.draw.rect(self.screen, RETRO_DARKER, inv_rect)
        pygame.draw.rect(self.screen, RETRO_DARK, (0, 477, SCREEN_WIDTH, 3))
        # Inner panel
        panel_rect = pygame.Rect(20, 495, SCREEN_WIDTH - 40, 90)
        pygame.draw.rect(self.screen, RETRO_DARK, panel_rect, border_radius=10)
        pygame.draw.rect(self.screen, RETRO_DARK_GRAY, panel_rect, 2, border_radius=10)
        # Inventory title
        inv_title = self.font_medium.render(f"🎒 INVENTORY ({len(self.inventory)} items)", True, RETRO_GOLD)
        self.screen.blit(inv_title, (30, 500))
        # Inventory items
        if not self.inventory:
            empty_text = self.font_small.render("No items yet. Start shopping!", True, RETRO_GRAY)
            self.screen.blit(empty_text, (30, 530))
        else:
            start_x = 30
            start_y = 530
            for i, item in enumerate(self.inventory[-15:]):  # Show last 15 items
                item_rect = pygame.Rect(start_x + i * 48, start_y, 40, 40)
                pygame.draw.rect(self.screen, RETRO_DARK_GRAY, item_rect, border_radius=8)
                pygame.draw.rect(self.screen, RETRO_GRAY, item_rect, 2, border_radius=8)
                emoji_surface = self.font_small.render(item['emoji'], True, RETRO_WHITE)
                emoji_rect = emoji_surface.get_rect(center=item_rect.center)
                self.screen.blit(emoji_surface, emoji_rect)

    def draw(self):
        self.screen.fill(RETRO_DARK)
        self.draw_header()
        self.draw_category_tabs()
        self.draw_main_content()
        self.draw_inventory()
        self.draw_message()
        self.draw_close_button()
        pygame.display.flip()

    def handle_events(self):
        mouse_pos = pygame.mouse.get_pos()
        
        # Update hover states
        for btn in self.category_buttons:
            btn.update_hover(mouse_pos)
        self.close_button.update_hover(mouse_pos)
        
        # Adjust mouse position for scrolled content
        adjusted_mouse_pos = (mouse_pos[0], mouse_pos[1] + self.scroll_offset)
        for card in self.item_cards:
            card.update_hover(adjusted_mouse_pos)

        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                return False

            if event.type == pygame.MOUSEBUTTONDOWN:
                if event.button == 1:  # Left click
                    # Check close button first
                    if self.handle_close_button(mouse_pos):
                        return False

                    # Check category buttons
                    for btn in self.category_buttons:
                        if btn.is_clicked(mouse_pos):
                            self.selected_category = btn.category_id
                            self.scroll_offset = 0
                            self.update_item_cards()
                            self.message = f"Browsing {btn.text}"
                            self.message_timer = 60

                    # Check item buy buttons
                    for card in self.item_cards:
                        if card.is_buy_clicked(adjusted_mouse_pos):
                            self.buy_item(card.item)
                
                # Scroll wheel
                elif event.button == 4:  # Scroll up
                    self.scroll_offset = max(0, self.scroll_offset - 30)
                elif event.button == 5:  # Scroll down
                    self.scroll_offset = min(self.max_scroll, self.scroll_offset + 30)

        return True

    def run(self):
        running = True
        while running:
            running = self.handle_events()
            self.draw()
            self.clock.tick(FPS)


if __name__ == "__main__":
    shop = PiPetShop()
    shop.run()