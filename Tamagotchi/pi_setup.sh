#!/bin/bash

# --- Full setup script for Pocket Pi Pet on Raspberry Pi OS Lite ---
set -e

REPO_URL="https://github.com/Prc292/pipet.git"
CLONE_DIR="pipet"
VENV_DIR="$HOME/$CLONE_DIR/venv"

echo "--- STARTING AUTOMATED SETUP for $CLONE_DIR ---"

# 1. Update system
echo "1. Updating system..."
sudo apt update
sudo apt upgrade -y

# 2. Install required system libraries and SDL2 runtime/development packages
echo "2. Installing required system libraries..."
sudo apt install -y python3 python3-pip python3-venv python3-dev python3-setuptools \
    git 

# 3. Clone or update the repository
echo "3. Cloning or updating the repository..."
cd ~
if [ -d "$CLONE_DIR" ]; then
    echo "Directory '$CLONE_DIR' exists, pulling latest changes..."
    cd "$CLONE_DIR"
    git pull origin main
else
    git clone "$REPO_URL"
    cd "$CLONE_DIR"
fi

# 4. Create Python virtual environment and install dependencies
echo "4. Creating Python virtual environment..."
python3 -m venv "$VENV_DIR"
source "$VENV_DIR/bin/activate"
pip install --upgrade pip
pip install -r Tamagotchi/requirements.txt

# 5. Set executable permissions
echo "5. Setting executable permissions for main.py..."
cd Tamagotchi
chmod +x main.py

echo "--- SETUP COMPLETE ---"
echo "The game is installed in: ~/$CLONE_DIR"
echo ""
echo "TO RUN THE GAME:"
echo "  source ~/$CLONE_DIR/venv/bin/activate"
echo "  python3 ~/$CLONE_DIR/Tamagotchi/main.py"
