import pygame
import time
from constants import *

class GardeningGame:
    def __init__(self, screen, font, db):
        self.screen = screen
        self.font = font
        self.db = db
        self.running = True
        
        # Ensure 4 plots exist, creating new ones if necessary
        plots_dict = {}
        db_plots = self.db.get_garden_plots()
        for plot in db_plots:
            plots_dict[plot[0]] = plot

        for i in range(1, 5): # Plot IDs from 1 to 4
            if i not in plots_dict:
                self.db.plant_seed(i, None) # plant_seed handles INSERT OR REPLACE
                new_plot = self.db.conn.execute("SELECT * FROM garden_plots WHERE plot_id = ?", (i,)).fetchone()
                plots_dict[i] = new_plot
        
        # Convert dictionary to a sorted list for consistent iteration
        self.plots = [plots_dict[i] for i in sorted(plots_dict.keys())]
            
        self.plot_rects = [
            pygame.Rect(50, 80, 150, 150),
            pygame.Rect(280, 80, 150, 150),
            pygame.Rect(50, 250, 150, 150),
            pygame.Rect(280, 250, 150, 150),
        ]
        self.selected_plot = None

    def run(self):
        while self.running:
            for event in pygame.event.get():
                if event.type == pygame.QUIT:
                    self.running = False
                if event.type == pygame.KEYDOWN:
                    if event.key == pygame.K_ESCAPE:
                        self.running = False
                if event.type == pygame.MOUSEBUTTONDOWN:
                    self.handle_click(event.pos)
            
            self.update()
            self.draw()
            pygame.display.flip()

    def handle_click(self, pos):
        for i, rect in enumerate(self.plot_rects):
            if rect.collidepoint(pos):
                self.selected_plot = i + 1
                return
        
        if self.selected_plot:
            # Plant seed if plot is empty and player has seeds
            if not self.plots[self.selected_plot - 1][1]:
                if self.db.remove_item_from_inventory("Normal Seed"):
                    self.db.plant_seed(self.selected_plot, "Berry Bush")
                    self.plots = self.db.get_garden_plots()
            # Water plant
            else:
                self.db.water_plant(self.selected_plot)
                self.plots = self.db.get_garden_plots()
        
        self.selected_plot = None

    def update(self):
        for i, plot in enumerate(self.plots):
            plot_id, plant_id, plant_time, last_watered_time = plot
            if plant_id:
                plant_info = self.db.get_plant(plant_id)
                if plant_info:
                    growth_time_seconds = plant_info[3]
                    if time.time() - plant_time > growth_time_seconds:
                        # Harvest
                        reward_item = plant_info[4]
                        reward_quantity = plant_info[5]
                        self.db.add_item_to_inventory(reward_item, reward_quantity)
                        self.db.plant_seed(plot_id, None)
                        self.plots = self.db.get_garden_plots()

    def draw(self):
        self.screen.fill(COLOR_BG)
        title_surf = self.font.render("Gardening", True, COLOR_TEXT)
        self.screen.blit(title_surf, (SCREEN_WIDTH // 2 - title_surf.get_width() // 2, 20))

        for i, rect in enumerate(self.plot_rects):
            pygame.draw.rect(self.screen, COLOR_UI_BAR_BG, rect, border_radius=10)
            plot_id, plant_id, plant_time, last_watered_time = self.plots[i]
            
            if plant_id:
                plant_info = self.db.get_plant(plant_id)
                if plant_info:
                    plant_name = plant_info[1]
                    growth_time_seconds = plant_info[3]
                    time_passed = time.time() - plant_time
                    growth_percentage = min(1, time_passed / growth_time_seconds)
                    
                    plant_surf = self.font.render(plant_name, True, COLOR_TEXT)
                    self.screen.blit(plant_surf, (rect.x + 10, rect.y + 10))
                    
                    # Growth bar
                    bar_width = rect.width - 20
                    bar_height = 10
                    fill_width = bar_width * growth_percentage
                    pygame.draw.rect(self.screen, (0, 255, 0), (rect.x + 10, rect.y + 40, fill_width, bar_height))
                    
                    # Water status
                    if time.time() - last_watered_time > 3600: # 1 hour
                        water_surf = self.font.render("Needs water!", True, (255, 0, 0))
                        self.screen.blit(water_surf, (rect.x + 10, rect.y + 60))

            else:
                plant_surf = self.font.render("Empty", True, COLOR_TEXT)
                self.screen.blit(plant_surf, (rect.x + 10, rect.y + 10))
                
        if self.selected_plot:
            rect = self.plot_rects[self.selected_plot - 1]
            pygame.draw.rect(self.screen, (255, 255, 0), rect, 2, border_radius=10)
            
            # Display options
            if not self.plots[self.selected_plot - 1][1]:
                option_surf = self.font.render("Plant Seed", True, COLOR_TEXT)
                self.screen.blit(option_surf, (rect.x + 10, rect.y + 80))
            else:
                option_surf = self.font.render("Water Plant", True, COLOR_TEXT)
                self.screen.blit(option_surf, (rect.x + 10, rect.y + 80))
