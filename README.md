# Pocket Pi Pet

A Tamagotchi-style virtual pet game for Raspberry Pi.

## Installation

These instructions are for a fresh installation on **Raspberry Pi OS Lite**.

1.  **Run the automated setup script:**

    Open a terminal on your Raspberry Pi and run the following command:

    ```bash
    bash <(curl -s https://raw.githubusercontent.com/Prc292/pipet/main/Tamagotchi/setup_pi_pet.sh)
    ```

    This script will:
    *   Update your system packages.
    *   Install necessary dependencies.
    *   Clone this repository to `~/pipet`.
    *   Set up a Python virtual environment with the required packages.

2.  **Configure display drivers (Optional but Recommended):**

    The included `set_config.sh` script configures the display for KMS/OpenGL, which is recommended for this Pygame application.

    ```bash
    cd ~/pipet/Tamagotchi
    sudo ./set_config.sh
    ```
    You will need to reboot your Raspberry Pi after this step.

## How to Play

1.  Open a terminal.
2.  Activate the virtual environment:
    ```bash
    source ~/pipet/venv/bin/activate
    ```
3.  Run the game:
    ```bash
    python3 ~/pipet/Tamagotchi/main.py
    ```
