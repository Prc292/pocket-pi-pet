import pygame
import json
import os

# --- Constants ---
SCREEN_WIDTH = 1280
SCREEN_HEIGHT = 800
ASSET_PALETTE_WIDTH = 200
BG_COLOR = (50, 50, 50)
PALETTE_BG_COLOR = (30, 30, 30)
FONT_COLOR = (255, 255, 255)
SAVE_FILE = "scene.json"

# --- Asset Loading ---
def load_assets():
    """Loads all assets for the editor, handling both individual images and spritesheets."""
    assets = {}
    base_path = os.path.dirname(__file__)
    sprites_dir = os.path.join(base_path, "assets", "sprites")

    for root, _, files in os.walk(sprites_dir):
        for file in files:
            if file.lower().endswith(".png"):
                full_path = os.path.join(root, file)
                relative_path = os.path.relpath(full_path, sprites_dir)
                
                # Check for a corresponding JSON file for spritesheets
                base_name, _ = os.path.splitext(full_path)
                json_path = base_name + ".json"

                # Handle cases where json might not have '-sheet'
                if not os.path.exists(json_path) and '-sheet' in base_name:
                    json_path = base_name.replace('-sheet', '') + ".json"

                if os.path.exists(json_path):
                    try:
                        spritesheet = pygame.image.load(full_path).convert_alpha()
                        with open(json_path, 'r') as f:
                            sprite_data = json.load(f)
                        
                        if "meta" in sprite_data and "slices" in sprite_data["meta"]:
                            for slice_data in sprite_data["meta"]["slices"]:
                                slice_name = slice_data["name"]
                                bounds = slice_data["keys"][0]["bounds"]
                                x, y, w, h = bounds["x"], bounds["y"], bounds["w"], bounds["h"]
                                sub_image = spritesheet.subsurface(pygame.Rect(x, y, w, h))
                                
                                # Use a unique key for sub-sprites
                                asset_key = f"{relative_path}:{slice_name}"
                                assets[asset_key] = sub_image
                        # Handle texture packer format
                        elif "frames" in sprite_data:
                            for frame_name, frame_data in sprite_data["frames"].items():
                                frame = frame_data["frame"]
                                x, y, w, h = frame['x'], frame['y'], frame['w'], frame['h']
                                sub_image = spritesheet.subsurface(pygame.Rect(x, y, w, h))
                                asset_key = f"{relative_path}:{os.path.basename(frame_name)}"
                                assets[asset_key] = sub_image

                    except Exception as e:
                        print(f"Warning: Could not process spritesheet {full_path}: {e}")
                else:
                    # Load as a single image
                    try:
                        image = pygame.image.load(full_path).convert_alpha()
                        assets[relative_path] = image
                    except pygame.error as e:
                        print(f"Warning: Could not load image {full_path}: {e}")
    print("Loaded assets:", list(assets.keys()))
    return assets

# --- Main Editor Class ---
class Editor:
    def __init__(self):
        pygame.init()
        self.screen = pygame.display.set_mode((SCREEN_WIDTH, SCREEN_HEIGHT))
        pygame.display.set_caption("PiPet Level Editor")
        self.clock = pygame.time.Clock()
        self.font = pygame.font.Font(None, 24)

        # Load background
        base_path = os.path.dirname(__file__)
        bg_path = os.path.join(base_path, "assets", "backgrounds", "background.png")
        self.background = pygame.image.load(bg_path).convert()
        self.background = pygame.transform.scale(self.background, (SCREEN_WIDTH, SCREEN_HEIGHT))

        self.assets = load_assets()
        self.placed_objects = []
        self.selected_asset_name = next(iter(self.assets.keys())) if self.assets else None
        
        self.dragging = False
        self.dragging_obj = None
        self.offset_x = 0
        self.offset_y = 0

        self.palette_scroll_y = 0

        self.load_scene()

    def run(self):
        running = True
        while running:
            for event in pygame.event.get():
                if event.type == pygame.QUIT:
                    running = False
                self.handle_event(event)
            
            self.update()
            self.draw()
            
            self.clock.tick(60)

        pygame.quit()

    def handle_event(self, event):
        if event.type == pygame.MOUSEBUTTONDOWN:
            # Handle palette scrolling
            if event.pos[0] > SCREEN_WIDTH - ASSET_PALETTE_WIDTH:
                if event.button == 4:  # Scroll up
                    self.palette_scroll_y = max(0, self.palette_scroll_y - 30)
                elif event.button == 5:  # Scroll down
                    self.palette_scroll_y += 30
            
            if event.button == 1: # Left click
                # Check if clicking on the asset palette
                if event.pos[0] > SCREEN_WIDTH - ASSET_PALETTE_WIDTH:
                    self.handle_palette_click(event.pos)
                else: # Check if clicking on a placed object
                    for obj in reversed(self.placed_objects):
                        if obj['rect'].collidepoint(event.pos):
                            self.dragging = True
                            self.dragging_obj = obj
                            mouse_x, mouse_y = event.pos
                            self.offset_x = obj['rect'].x - mouse_x
                            self.offset_y = obj['rect'].y - mouse_y
                            break

        if event.type == pygame.MOUSEBUTTONUP:
            if event.button == 1: # Left click
                if self.dragging:
                    self.dragging = False
                    self.dragging_obj = None

        if event.type == pygame.MOUSEMOTION:
            if self.dragging and self.dragging_obj:
                mouse_x, mouse_y = event.pos
                self.dragging_obj['rect'].x = mouse_x + self.offset_x
                self.dragging_obj['rect'].y = mouse_y + self.offset_y

        if event.type == pygame.KEYDOWN:
            if event.key == pygame.K_s and pygame.key.get_mods() & pygame.KMOD_CTRL:
                self.save_scene()
            if event.key == pygame.K_l and pygame.key.get_mods() & pygame.KMOD_CTRL:
                self.load_scene()
            if event.key == pygame.K_d: # place asset
                 if self.selected_asset_name:
                    asset_image = self.assets[self.selected_asset_name]
                    new_obj = {
                        "name": self.selected_asset_name,
                        "rect": asset_image.get_rect(center=pygame.mouse.get_pos())
                    }
                    self.placed_objects.append(new_obj)


    def handle_palette_click(self, pos):
        # Adjust for scrolling
        click_y = pos[1] + self.palette_scroll_y - 50 # 50 is the top padding
        
        y_offset = 0
        for name, image in self.assets.items():
            rect = pygame.Rect(10, y_offset, image.get_width(), image.get_height())
            if rect.collidepoint((pos[0] - (SCREEN_WIDTH - ASSET_PALETTE_WIDTH), click_y)):
                self.selected_asset_name = name
                break
            y_offset += image.get_height() + 10

    def update(self):
        pass # Not much to update per-frame that isn't event-driven

    def draw(self):
        self.screen.blit(self.background, (0, 0))
        
        # Draw placed objects
        for obj in self.placed_objects:
            self.screen.blit(self.assets[obj['name']], obj['rect'])

        self.draw_palette()
        
        # Draw selected asset at cursor
        if self.selected_asset_name:
            asset_image = self.assets[self.selected_asset_name]
            cursor_pos = pygame.mouse.get_pos()
            if cursor_pos[0] < SCREEN_WIDTH - ASSET_PALETTE_WIDTH:
                 # Create a copy of the image and set its alpha to make it semi-transparent
                ghost_image = asset_image.copy()
                ghost_image.set_alpha(150)
                self.screen.blit(ghost_image, ghost_image.get_rect(center=cursor_pos))


        pygame.display.flip()

    def draw_palette(self):
        palette_rect = pygame.Rect(SCREEN_WIDTH - ASSET_PALETTE_WIDTH, 0, ASSET_PALETTE_WIDTH, SCREEN_HEIGHT)
        pygame.draw.rect(self.screen, PALETTE_BG_COLOR, palette_rect)

        title_text = self.font.render("Assets", True, FONT_COLOR)
        self.screen.blit(title_text, (SCREEN_WIDTH - ASSET_PALETTE_WIDTH + 10, 10))

        # Create a surface for the palette content
        content_height = 0
        for image in self.assets.values():
            content_height += image.get_height() + 10
        
        palette_content_surface = pygame.Surface((ASSET_PALETTE_WIDTH, content_height), pygame.SRCALPHA)
        palette_content_surface.fill((0, 0, 0, 0)) # Transparent background

        y_offset = 0
        for name, image in self.assets.items():
            rect = pygame.Rect(10, y_offset, image.get_width(), image.get_height())
            
            if name == self.selected_asset_name:
                pygame.draw.rect(palette_content_surface, (0,155,155), rect.inflate(4, 4), 2)

            palette_content_surface.blit(image, rect)
            y_offset += image.get_height() + 10

        # Limit scrolling
        max_scroll = max(0, content_height - SCREEN_HEIGHT + 50) # +50 for title padding
        self.palette_scroll_y = max(0, min(self.palette_scroll_y, max_scroll))

        self.screen.blit(palette_content_surface, (SCREEN_WIDTH - ASSET_PALETTE_WIDTH, 50 - self.palette_scroll_y))
            
    def save_scene(self):
        scene_data = []
        for obj in self.placed_objects:
            scene_data.append({
                "name": obj["name"],
                "pos": [obj["rect"].x, obj["rect"].y]
            })
        
        with open(SAVE_FILE, 'w') as f:
            json.dump(scene_data, f, indent=4)
        print(f"Scene saved to {SAVE_FILE}")

    def load_scene(self):
        try:
            with open(SAVE_FILE, 'r') as f:
                scene_data = json.load(f)
            
            self.placed_objects = []
            for data in scene_data:
                asset_image = self.assets[data["name"]]
                self.placed_objects.append({
                    "name": data["name"],
                    "rect": asset_image.get_rect(topleft=data["pos"])
                })
            print(f"Scene loaded from {SAVE_FILE}")
        except FileNotFoundError:
            print("No save file found.")
        except Exception as e:
            print(f"Error loading scene: {e}")


if __name__ == "__main__":
    Editor().run()
