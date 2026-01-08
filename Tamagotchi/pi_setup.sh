#!/bin/bash

# --- Full setup script for Pocket Pi Pet on Raspberry Pi OS Lite ---
set -e

REPO_URL="https://github.com/Prc292/pipet.git"



echo "--- STARTING AUTOMATED SETUP for pipet ---"

# 1. Update system
echo "1. Updating system..."
sudo apt update
sudo apt upgrade -y

# 2. Install required system libraries and SDL2 runtime/development packages
echo "2. Installing required system libraries..."
sudo apt install -y python3 python3-pip python3-venv python3-dev python3-setuptools
    \ git \ libSDL2-2.0-0 
    \ libSDL2-dev libSDL2-image-2.0-0 
    \ libsdl2-image-dev \ libsdl2-mixer-dev 
    \ libsdl2-ttf-dev \ libportmidi-dev 
    \ libfreetype6-dev \ libjpeg-dev 
    \ libbz2-dev \ libpng-dev \ libopenal-dev 
    \ libudev-dev \ build-essential

# 4. Create Python virtual environment and install dependencies
echo "4. Creating Python virtual environment..."
python3 -m venv ~/pipet/venv
source "~/pipet/venv/bin/activate"
pip install --upgrade pip
pip install -r ~/pipet/Tamagotchi/requirements.txt

# 5. Set executable permissions
echo "5. Setting executable permissions for main.py..."
cd Tamagotchi
chmod +x main.py

echo "--- SETUP COMPLETE ---"
echo "The game is installed in ~/pipet
echo ""
echo "TO RUN THE GAME:"
echo "  source ~/pipet/venv/bin/activate"
echo "  python3 ~/pipet/Tamagotchi/main.py"