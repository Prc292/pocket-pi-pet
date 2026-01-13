import pygame
from typing import Tuple, Optional, Callable
from constants import RETRO_SHADOW, RETRO_DARK, RETRO_PINK, RETRO_LIGHT, BUTTON_SHADOW_OFFSET, BUTTON_BORDER_RADIUS, BUTTON_GLASS_ALPHA, BUTTON_BORDER_WIDTH

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
        shadow_rect.x += BUTTON_SHADOW_OFFSET
        shadow_rect.y += BUTTON_SHADOW_OFFSET
        pygame.draw.rect(surface, RETRO_SHADOW, shadow_rect, border_radius=BUTTON_BORDER_RADIUS)
        
        # Button press offset
        offset = 3 if self.pressed else 0
        draw_rect = self.rect.copy()
        draw_rect.x += offset
        draw_rect.y += offset
        
        # Dark base
        dark_colour = tuple(max(0, c - 30) for c in self.color)
        pygame.draw.rect(surface, dark_colour, draw_rect, border_radius=BUTTON_BORDER_RADIUS)
        
        # Light top gradient
        gradient_rect = draw_rect.copy()
        gradient_rect.height //= 2
        light_colour = tuple(min(255, c + 20) for c in self.color)
        pygame.draw.rect(surface, light_colour, gradient_rect, border_radius=BUTTON_BORDER_RADIUS)
        
        # Glass overlay
        glass_surface = pygame.Surface((draw_rect.width - 8, draw_rect.height // 3), pygame.SRCALPHA)
        glass_surface.fill((255, 255, 255, BUTTON_GLASS_ALPHA))
        surface.blit(glass_surface, (draw_rect.x + 4, draw_rect.y + 4))
        
        # Border
        pygame.draw.rect(surface, RETRO_DARK, draw_rect, BUTTON_BORDER_WIDTH, border_radius=BUTTON_BORDER_RADIUS)
        
        # Text rendering
        if self.icon:
            full_text = f"{self.icon} {self.text}"
        else:
            full_text = self.text
            
        text_surface = font.render(full_text, True, RETRO_DARK)
        text_rect = text_surface.get_rect(center=draw_rect.center)
        surface.blit(text_surface, text_rect)
    
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
