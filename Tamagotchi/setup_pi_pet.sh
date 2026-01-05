#!/bin/bash

# --- Script to set up Pocket Pi Pet on Raspberry Pi OS ---

set -e

REPO_URL="https://github.com/Prc292/pocket-pi-pet.git"
CLONE_DIR="pocket-pi-pet"

echo "--- STARTING AUTOMATED SETUP for $CLONE_DIR ---"

# 1. Update package list
echo "1. Updating package list..."
sudo apt update

# 2. Install Python dependencies, Display Server components, and core SQLite library
echo "2. Installing required system libraries (Pygame, SQLite3 C library, git, and X server)..."
# Changed 'python3-sqlite3' to 'sqlite3' which provides the necessary core C library.
sudo apt install -y python3-pygame sqlite3 git xserver-xorg

# 3. Clone or update the repository
echo "3. Cloning/Updating the repository from $REPO_URL..."
cd ~

if [ -d "$CLONE_DIR" ]; then
    echo "Directory '$CLONE_DIR' already exists. Pulling latest changes..."
    cd "$CLONE_DIR"
    git pull origin main
else
    git clone "$REPO_URL"
    cd "$CLONE_DIR"
fi

# 4. Set executable permissions for the main script
echo "4. Setting executable permission for main.py..."
cd ~/pocket-pi-pet/Tamagotchi
chmod +x main.py

echo "--- SETUP COMPLETE ---"
echo "The game is installed in: ~/pocket-pi-pet"
echo ""
echo "TO RUN THE GAME:"
echo "cd ~/pocket-pi-pet/Tamagotchi"
echo "python3 main.py"
