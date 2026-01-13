import pygame
import time
from constants import *
from ui_components import ModernRetroButton

class GardeningGame:
    def __init__(self, font, db):
        self.font = font
        self.db = db
        self.is_over = False
        
        plots_dict = {}
        db_plots = self.db.get_garden_plots()
        for plot in db_plots:
            plots_dict[plot[0]] = plot

        for i in range(1, 5):
            if i not in plots_dict:
                self.db.plant_seed(i, None)
                new_plot = self.db.conn.execute("SELECT * FROM garden_plots WHERE plot_id = ?", (i,)).fetchone()
                plots_dict[i] = new_plot
        
        self.plots = [plots_dict[i] for i in sorted(plots_dict.keys())]
            
        self.plot_rects = [
            pygame.Rect(50, 80, 150, 150),
            pygame.Rect(280, 80, 150, 150),
            pygame.Rect(50, 250, 150, 150),
            pygame.Rect(280, 250, 150, 150),
        ]
        self.selected_plot = None

        # Close button using ModernRetroButton
        self.close_button = ModernRetroButton(
            x=SCREEN_WIDTH // 2 - BUTTON_WIDTH // 2,
            y=SCREEN_HEIGHT - BUTTON_HEIGHT - 20,
            width=BUTTON_WIDTH,
            height=BUTTON_HEIGHT,
            text="CLOSE",
            color=RETRO_PINK,
            icon="❌",
            on_click=self.on_close_click
        )

    def on_close_click(self):
        self.is_over = True

    def handle_event(self, event, raw_pos):
        # Handle close button click events
        if self.close_button.handle_event(raw_pos, event.type):
            return # Event handled by button, minigame will close
        
        # Now handle other click interactions, only if a mouse button was pressed
        click_pos = None
        if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
            click_pos = raw_pos
        elif event.type == pygame.FINGERDOWN:
            click_pos = raw_pos

        if click_pos:
            for i, rect in enumerate(self.plot_rects):
                if rect.collidepoint(click_pos):
                    self.selected_plot = i + 1
                    return
            
            if self.selected_plot:
                if not self.plots[self.selected_plot - 1][1]:
                    if self.db.remove_item_from_inventory("Normal Seed"):
                        self.db.plant_seed(self.selected_plot, "Berry Bush")
                        self.plots = [self.db.get_garden_plots()[i] for i in sorted(self.db.get_garden_plots().keys())]

                else:
                    self.db.water_plant(self.selected_plot)
                    self.plots = [self.db.get_garden_plots()[i] for i in sorted(self.db.get_garden_plots().keys())]
            
            self.selected_plot = None

    def update(self):
        for i, plot in enumerate(self.plots):
            plot_id, plant_id, plant_time, last_watered_time = plot
            if plant_id:
                plant_info = self.db.get_plant(plant_id)
                if plant_info:
                    growth_time_seconds = plant_info[3]
                    if time.time() - plant_time > growth_time_seconds:
                        reward_item = plant_info[4]
                        reward_quantity = plant_info[5]
                        self.db.add_item_to_inventory(reward_item, reward_quantity)
                        self.db.plant_seed(plot_id, None)
                        self.plots = [self.db.get_garden_plots()[i] for i in sorted(self.db.get_garden_plots().keys())]

    def draw(self, surface):
        surface.fill(COLOR_BG)
        title_surf = self.font.render("Gardening", False, COLOR_TEXT)
        surface.blit(title_surf, (SCREEN_WIDTH // 2 - title_surf.get_width() // 2, 20))

        for i, rect in enumerate(self.plot_rects):
            pygame.draw.rect(surface, COLOR_UI_BAR_BG, rect, border_radius=10)
            plot_id, plant_id, plant_time, last_watered_time = self.plots[i]
            
            if plant_id:
                plant_info = self.db.get_plant(plant_id)
                if plant_info:
                    plant_name = plant_info[1]
                    growth_time_seconds = plant_info[3]
                    time_passed = time.time() - plant_time
                    growth_percentage = min(1, time_passed / growth_time_seconds)
                    
                    plant_surf = self.font.render(plant_name, False, COLOR_TEXT)
                    surface.blit(plant_surf, (rect.x + 10, rect.y + 10))
                    
                    bar_width = rect.width - 20
                    bar_height = 10
                    fill_width = bar_width * growth_percentage
                    pygame.draw.rect(surface, (0, 255, 0), (rect.x + 10, rect.y + 40, fill_width, bar_height))
                    
                    if time.time() - last_watered_time > 3600: # 1 hour
                        water_surf = self.font.render("Needs water!", False, (255, 0, 0))
                        surface.blit(water_surf, (rect.x + 10, rect.y + 60))

            else:
                plant_surf = self.font.render("Empty", False, COLOR_TEXT)
                surface.blit(plant_surf, (rect.x + 10, rect.y + 10))
                
        if self.selected_plot:
            rect = self.plot_rects[self.selected_plot - 1]
            pygame.draw.rect(surface, (255, 255, 0), rect, 2, border_radius=10)
            
            if not self.plots[self.selected_plot - 1][1]:
                option_surf = self.font.render("Plant Seed", False, COLOR_TEXT)
                surface.blit(option_surf, (rect.x + 10, rect.y + 80))
            else:
                option_surf = self.font.render("Water Plant", False, COLOR_TEXT)
                surface.blit(option_surf, (rect.x + 10, rect.y + 80))
        
        # Draw the ModernRetroButton
        self.close_button.draw(surface, self.font)
