# Project Overview

This is a Tamagotchi-style virtual pet game written in Python using the Pygame library. The application simulates a virtual pet that the user can interact with. The pet has stats such as fullness, happiness, energy, health, and discipline, which decay over time. The user can perform actions like feeding, playing with, training, and putting the pet to sleep. The pet's state is saved to a SQLite database file (`pet_life.db`).

The application is designed to be run on a Raspberry Pi, as indicated by the `set_config.sh` and `setup_pi_pet.sh` scripts, which configure the Raspberry Pi environment.

## Key Files

*   `Tamagotchi/main.py`: The main entry point of the application. It contains the game loop, event handling, and rendering logic.
*   `Tamagotchi/pet_entity.py`: Defines the `Pet` class, which encapsulates the pet's logic, including state transitions, stat updates, and drawing.
*   `Tamagotchi/models.py`: Defines the data structures for the pet's state (`PetState`) and stats (`PetStats`).
*   `Tamagotchi/database.py`: Handles the persistence of the pet's state to a SQLite database.
*   `Tamagotchi/constants.py`: Contains global configuration variables and UI color definitions.
*   `Tamagotchi/set_config.sh`: A script to configure the Raspberry Pi's `config.txt` file for KMS/OpenGL.
*   `Tamagotchi/setup_pi_pet.sh`: A script to set up the application on a Raspberry Pi, including installing dependencies and cloning the repository.

## Building and Running

The project is intended to be run on a Raspberry Pi. The `setup_pi_pet.sh` script provides the necessary steps to set up the environment.

**To run the application:**

1.  **Set up the environment:** Run the `Tamagotchi/setup_pi_pet.sh` script on your Raspberry Pi. This will install dependencies, create a virtual environment, and clone the repository.
2.  **Configure the Raspberry Pi:** Run the `Tamagotchi/set_config.sh` script to configure the display drivers.
3.  **Activate the virtual environment:** `source ~/tamago-venv/bin/activate`
4.  **Run the game:** `python3 ~/pocket-pi-pet/Tamagotchi/main.py`

## Development Conventions

*   The project uses a virtual environment for dependency management.
*   The code is structured into classes and modules with clear responsibilities.
*   The database schema is defined in `database.py`.
*   The application uses a state machine to manage the pet's behavior.
*   The UI is built with Pygame.
