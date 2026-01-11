# --- GLOBAL CONFIGURATION ---
SCREEN_WIDTH = 480          
SCREEN_HEIGHT = 320
FPS = 30
DB_FILE = "pet_life.db"
TIME_SCALE_FACTOR = 1 # 1 = real time, 10 = 10x faster!
POINTS_PER_WIN = 10

# --- SHOP (Prices in Coins) ---
SHOP_ITEMS = {
    'snacks': [
        {'id': 'cookie', 'name': 'Cookie', 'price': 5, 'hunger': 10, 'energy': 5, 'happiness': 5, 'icon_path': 'delapouite/cookie.png'},
        {'id': 'candy', 'name': 'Candy', 'price': 3, 'hunger': 5, 'energy': 3, 'happiness': 10, 'icon_path': 'delapouite/candy.png'},
        {'id': 'chocolate', 'name': 'Chocolate', 'price': 8, 'hunger': 12, 'energy': 8, 'happiness': 15, 'icon_path': 'rihlsul/chocolate-bar.png'},
        {'id': 'lollipop', 'name': 'Lollipop', 'price': 4, 'hunger': 5, 'energy': 2, 'happiness': 8, 'icon_path': 'delapouite/spiral-lollipop.png'},
        {'id': 'donut', 'name': 'Donut', 'price': 7, 'hunger': 15, 'energy': 5, 'happiness': 12, 'icon_path': 'delapouite/donut.png'},
        {'id': 'ice_cream', 'name': 'Ice Cream', 'price': 10, 'hunger': 18, 'energy': 5, 'happiness': 20, 'icon_path': 'delapouite/ice-cream-cone.png'},
        {'id': 'popcorn', 'name': 'Popcorn', 'price': 6, 'hunger': 8, 'energy': 3, 'happiness': 7, 'icon_path': 'delapouite/popcorn.png'},
        {'id': 'chips', 'name': 'Chips', 'price': 5, 'hunger': 10, 'energy': 4, 'happiness': 6, 'icon_path': 'delapouite/chips-bag.png'},
    ],
    'foods': [
        {'id': 'apple', 'name': 'Apple', 'price': 5, 'hunger': 15, 'energy': 8, 'health': 5, 'icon_path': 'delapouite/apple.png'},
        {'id': 'banana', 'name': 'Banana', 'price': 4, 'hunger': 12, 'energy': 10, 'health': 3, 'icon_path': 'delapouite/banana.png'},
        {'id': 'burger', 'name': 'Burger', 'price': 15, 'hunger': 35, 'energy': 15, 'happiness': 10, 'icon_path': 'delapouite/hamburger.png'},
        {'id': 'pizza', 'name': 'Pizza', 'price': 12, 'hunger': 30, 'energy': 12, 'happiness': 15, 'icon_path': 'delapouite/full-pizza.png'},
        {'id': 'sandwich', 'name': 'Sandwich', 'price': 10, 'hunger': 25, 'energy': 10, 'health': 5, 'icon_path': 'delapouite/sandwich.png'},
        {'id': 'rice', 'name': 'Rice Bowl', 'price': 8, 'hunger': 20, 'energy': 12, 'health': 8, 'icon_path': 'caro-asercion/bowl-of-rice.png'},
        {'id': 'noodles', 'name': 'Noodles', 'price': 9, 'hunger': 22, 'energy': 10, 'happiness': 8, 'icon_path': 'delapouite/noodles.png'},
        {'id': 'sushi', 'name': 'Sushi', 'price': 18, 'hunger': 28, 'energy': 15, 'health': 10, 'icon_path': 'delapouite/sushis.png'},
    ],
    'drinks': [
        {'id': 'water', 'name': 'Water', 'price': 2, 'hunger': 5, 'energy': 3, 'health': 5, 'icon_path': 'caro-asercion/soda-bottle.png'}, # Generic bottle
        {'id': 'juice', 'name': 'Juice', 'price': 6, 'hunger': 10, 'energy': 8, 'happiness': 5, 'icon_path': 'caro-asercion/soda-bottle.png'}, # Generic bottle
        {'id': 'soda', 'name': 'Soda', 'price': 5, 'hunger': 8, 'energy': 5, 'happiness': 10, 'icon_path': 'guard13007/soda-can.png'},
        {'id': 'milk', 'name': 'Milk', 'price': 4, 'hunger': 12, 'energy': 5, 'health': 8, 'icon_path': 'rihlsul/milk-carton.png'},
        {'id': 'tea', 'name': 'Tea', 'price': 5, 'hunger': 5, 'energy': 10, 'health': 5, 'icon_path': 'lorc/teapot.png'},
        {'id': 'smoothie', 'name': 'Smoothie', 'price': 10, 'hunger': 15, 'energy': 12, 'health': 10, 'icon_path': 'caro-asercion/soda-bottle.png'}, # Generic bottle
    ],
    'energy': [
        {'id': 'energy_red', 'name': 'Red Bull', 'price': 15, 'hunger': 5, 'energy': 30, 'happiness': 5, 'icon_path': 'guard13007/soda-can.png'},
        {'id': 'energy_blue', 'name': 'Blue Energy', 'price': 15, 'hunger': 5, 'energy': 30, 'happiness': 5, 'icon_path': 'guard13007/soda-can.png'},
        {'id': 'energy_green', 'name': 'Green Power', 'price': 15, 'hunger': 5, 'energy': 30, 'happiness': 5, 'icon_path': 'guard13007/soda-can.png'},
        {'id': 'sports_drink', 'name': 'Sports Drink', 'price': 12, 'hunger': 8, 'energy': 25, 'health': 5, 'icon_path': 'caro-asercion/soda-bottle.png'},
        {'id': 'protein', 'name': 'Protein Shake', 'price': 18, 'hunger': 20, 'energy': 20, 'health': 10, 'icon_path': 'caro-asercion/soda-bottle.png'},
    ],
}

# Category info
CATEGORIES = [
    {'id': 'snacks', 'name': '🍪 Snacks', 'color': (255, 182, 193)}, # PINK
    {'id': 'foods', 'name': '🍔 Foods', 'color': (255, 165, 0)}, # ORANGE
    {'id': 'drinks', 'name': '🥤 Drinks', 'color': (100, 149, 237)}, # BLUE
    {'id': 'energy', 'name': '⚡ Energy', 'color': (50, 205, 50)}, # GREEN
]

# --- RETRO UI PALETTE ---
COLOR_BG = (40, 44, 52)
COLOR_PET_BODY = (171, 220, 255)
COLOR_PET_EYES = (33, 37, 43)
COLOR_UI_BAR_BG = (62, 68, 81)
COLOR_HEALTH = (152, 195, 121)
COLOR_FULLNESS = (224, 108, 117)
COLOR_HAPPY = (229, 192, 123)
COLOR_ENERGY = (97, 175, 239)
COLOR_TEXT = (171, 178, 191)
COLOR_BTN = (100, 100, 100)
COLOR_SICK = (198, 120, 221)
COLOR_MESSAGE_BOX_BG = (50, 50, 50, 128) # Semi-transparent dark grey

# --- COMMON COLORS ---
BLACK = (0, 0, 0)
WHITE = (255, 255, 255)
GREEN = (0, 255, 0)
RED = (255, 0, 0)
GRAY = (200, 200, 200)
LIGHT_GRAY = (240, 240, 240)
DARK_GRAY = (100, 100, 100)
PINK = (255, 182, 193)
ORANGE = (255, 165, 0)
BLUE = (100, 149, 237)
YELLOW = (255, 215, 0)