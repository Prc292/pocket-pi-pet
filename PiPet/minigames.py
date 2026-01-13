import pygame
import random
import time
from constants import SCREEN_WIDTH, SCREEN_HEIGHT, BLACK, WHITE, GREEN, RED

class CatchTheFoodMinigame:
    """
    A mini-game where the player moves a character to catch falling food items.
    """
    def __init__(self, font):
        self.font = font
        self.score = 0
        self.game_duration = 20.0
        self.start_time = time.time()
        
        self.player_rect = pygame.Rect(SCREEN_WIDTH // 2 - 25, SCREEN_HEIGHT - 50, 50, 20)
        
        self.good_foods = []
        self.bad_foods = []
        self.food_speed = 4
        self.food_spawn_timer = 0
        self.food_spawn_interval = 0.4

        self.is_over = False
        self.game_over_acknowledged = False

    def handle_event(self, event, raw_pos):
        if self.is_over:
            if (event.type == pygame.MOUSEBUTTONDOWN and event.button == 1) or (event.type == pygame.FINGERDOWN):
                self.game_over_acknowledged = True

    def update(self, mouse_pos):
        if self.is_over:
            return

        # Player movement
        self.player_rect.centerx = mouse_pos[0]

        # Clamp player position to screen bounds
        if self.player_rect.left < 0:
            self.player_rect.left = 0
        if self.player_rect.right > SCREEN_WIDTH:
            self.player_rect.right = SCREEN_WIDTH

        # Spawn food
        self.food_spawn_timer += 1/30.0 # Assuming 30 FPS from main loop
        if self.food_spawn_timer > self.food_spawn_interval:
            self.food_spawn_timer = 0
            self.spawn_food()

        # Update good food
        for food in self.good_foods[:]:
            food.y += self.food_speed
            if self.player_rect.colliderect(food):
                self.good_foods.remove(food)
                self.score += 1
            elif food.y > SCREEN_HEIGHT:
                self.good_foods.remove(food)

        # Update bad food
        for food in self.bad_foods[:]:
            food.y += self.food_speed
            if self.player_rect.colliderect(food):
                self.bad_foods.remove(food)
                self.score = max(0, self.score - 2) # Penalty for catching bad food
            elif food.y > SCREEN_HEIGHT:
                self.bad_foods.remove(food)

        # Check for game over
        if time.time() - self.start_time >= self.game_duration:
            self.is_over = True
            
    def spawn_food(self):
        x = random.randint(0, SCREEN_WIDTH - 20)
        item_rect = pygame.Rect(x, -20, 20, 20)
        if random.random() > 0.3: # 70% chance of good food
            self.good_foods.append(item_rect)
        else:
            self.bad_foods.append(item_rect)

    def draw(self, surface):
        surface.fill(BLACK)
        
        # Draw player
        pygame.draw.rect(surface, GREEN, self.player_rect)

        # Draw foods
        for food in self.good_foods:
            pygame.draw.rect(surface, GREEN, food)
        for food in self.bad_foods:
            pygame.draw.rect(surface, RED, food)
        
        # Draw UI
        score_text = self.font.render(f"Score: {self.score}", False, WHITE)
        surface.blit(score_text, (10, 10))
        
        time_left = self.game_duration - (time.time() - self.start_time)
        timer_text = self.font.render(f"Time: {int(max(0, time_left))}", False, WHITE)
        surface.blit(timer_text, (SCREEN_WIDTH - timer_text.get_width() - 10, 10))

        if self.is_over:
            game_over_font = pygame.font.Font(None, 40)
            game_over_text = game_over_font.render("Game Over", False, RED)
            score_display_text = self.font.render(f"Final Score: {self.score}", False, WHITE)
            
            game_over_rect = game_over_text.get_rect(center=(SCREEN_WIDTH / 2, SCREEN_HEIGHT / 2 - 20))
            score_rect = score_display_text.get_rect(center=(SCREEN_WIDTH / 2, SCREEN_HEIGHT / 2 + 20))

            surface.blit(game_over_text, game_over_rect)
            surface.blit(score_display_text, score_rect)