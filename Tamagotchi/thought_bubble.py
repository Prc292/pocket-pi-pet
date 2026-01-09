import pygame

class ThoughtBubble:
    def __init__(self, screen, font, get_pet_pos_func):
        self.screen = screen
        self.font = font
        self.get_pet_pos = get_pet_pos_func
        self.active = False
        self.message = ""
        self.timer = 0
        self.duration = 3 # seconds
        self.color = (255, 255, 255) # White
        self.text_color = (0, 0, 0) # Black
        self.padding = 5
        self.border_radius = 5

    def show_message(self, message, duration=3):
        self.message = message
        self.active = True
        self.timer = duration
        self.duration = duration

    def update(self, dt):
        if self.active:
            self.timer -= dt
            if self.timer <= 0:
                self.active = False

    def draw(self):
        if self.active:
            pet_x, pet_y = self.get_pet_pos()
            
            text_surf = self.font.render(self.message, True, self.text_color)
            text_rect = text_surf.get_rect()

            # Bubble size and position
            bubble_width = text_rect.width + 2 * self.padding
            bubble_height = text_rect.height + 2 * self.padding
            
            # Position above pet
            bubble_x = pet_x - bubble_width // 2
            bubble_y = pet_y - bubble_height - 30 # 30 pixels above pet

            bubble_rect = pygame.Rect(bubble_x, bubble_y, bubble_width, bubble_height)
            
            # Draw bubble background
            pygame.draw.rect(self.screen, self.color, bubble_rect, border_radius=self.border_radius)
            
            # Draw text
            self.screen.blit(text_surf, (bubble_x + self.padding, bubble_y + self.padding))

            # Draw thought bubble "tail" (a simple triangle)
            tail_base_left = (pet_x - 10, pet_y - 30 + 5)
            tail_base_right = (pet_x + 10, pet_y - 30 + 5)
            tail_point = (pet_x, pet_y - 5)
            pygame.draw.polygon(self.screen, self.color, [tail_base_left, tail_base_right, tail_point])
