# Project Advancement Plan

This document outlines the steps to incorporate new features and improvements into the Tamagotchi Python project, aiming to make it more fun, addictive, and compelling.

## Phase 1: Core Gameplay Enhancements

This phase focuses on strengthening the existing game mechanics and making the core experience more engaging.

### 1. Implement Branching Evolution
*   **Description:** Modify the pet's evolution to be based on its stats and care, leading to different forms.
*   **Status:** Completed
*   **Details:**
    *   **Modify `models.py`:** Define new `PetState` enums for at least two evolution paths (e.g., `ROYAL_CHILD`, `WILD_CHILD`, `ROYAL_ADULT`, `WILD_ADULT`).
    *   **Modify `pet_entity.py`:** Update the evolution logic in the `update` method to check pet stats (e.g., `discipline > 75` or `happiness` levels) at the point of evolution to determine the path. Create or use placeholder visual assets for new forms.

### 2. Introduce a Simple Mini-Game
*   **Status:** Completed
*   **Details:**
    *   **Create `minigames.py`:** Implement a basic game (e.g., clicking the pet to keep it bouncing). The game should return a score.
    *   **Modify `main.py`:** When "PLAY" is clicked, launch the mini-game. Increase pet's `happiness` based on the mini-game score.

### 3. Improve UI and Animations
*   **Status:** Completed
*   **Details:**
    *   **Modify `pet_entity.py`:** Add more animation frames for common states (e.g., "idle," "eating," "happy," "sad").
    *   **Modify `main.py`:**
        *   Implement visual feedback for stat changes (e.g., bar flashing).
        *   Integrate `pygame.mixer` for simple sound effects for button clicks and basic interactions.

## Phase 2: Expanding the World

This phase will make the game feel larger and more persistent.

### 1. Implement a Day/Night Cycle
*   **Status:** Completed
*   **Details:**
    *   **Modify `main.py`:** Get current system time in the game loop. Change `COLOR_BG` based on the hour.
    *   **Modify `pet_entity.py` (or `main.py`):** Slightly increase pet's energy decay at night if not sleeping to encourage player interaction.

### 2. Add a Collectible System
*   **Description:** Introduce different food items with varying effects and an inventory system.
*   **Status:** Pending
*   **Details:**
    *   **Modify `database.py`:** Add a new table for player inventory.
    *   **Modify `constants.py`:** Define a list of food items with names and effects on stats.
    *   **Modify `main.py`:** Add a "shop" for buying food with points. The "Feed" button should open an inventory menu.



## Phase 3: Long-Term Engagement and Polish

This final phase adds features to keep players invested for the long run.

### 1. Create an Achievement System
*   **Description:** Reward players for reaching specific milestones and goals.
*   **Status:** Pending
*   **Details:**
    *   **Create `achievements.py`:** Define a dictionary of achievements with names, descriptions, and unlock conditions.
    *   **Modify `main.py`:** Check for achievement conditions in the game loop. Display notifications when unlocked. Add an "Achievements" screen to the UI.

### 2. Expand the Mini-Game Collection
*   **Description:** Offer more variety in interactive play options.
*   **Status:** Pending
*   **Details:**
    *   **Modify `minigames.py`:** Implement 1-2 new mini-games (e.g., a memory game, a simple reflex game).
    *   **Modify `main.py`:** Allow players to select from available mini-games when clicking the "Play" button.

