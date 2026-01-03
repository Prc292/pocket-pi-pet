#!/bin/bash
# Pi-Pet Automated Setup Script
# Usage: bash pi_setup.sh
set -e

# 1. Update system
sudo apt-get update && sudo apt-get upgrade -y

# 2. Install system dependencies
sudo apt-get install -y python3 python3-pip python3-venv git unclutter-fixes x11-xserver-utils xorg libatlas-base-dev libsdl2-dev libsdl2-image-dev libsdl2-mixer-dev libsdl2-ttf-dev libportmidi-dev libfreetype6-dev libjpeg-dev libpng-dev

# 3. Clone the repository (if not already cloned)
if [ ! -d "$HOME/pocket-pi-pet" ]; then
  git clone https://github.com/Prc292/pocket-pi-pet.git "$HOME/pocket-pi-pet"
fi
cd "$HOME/pocket-pi-pet/Tamagotchi"

# 4. Set up Python virtual environment
python3 -m venv venv
source venv/bin/activate

# 5. Install Python dependencies
pip install --upgrade pip
pip install -r requirements.txt

# 6. Optional: Hide mouse cursor on touchscreen
if ! grep -q 'unclutter' ~/.xinitrc 2>/dev/null; then
  echo 'unclutter --timeout 0 &' >> ~/.xinitrc
fi

# 7. Done
clear
echo "\n[Pi-Pet] Setup complete! To run:"
echo "cd ~/pocket-pi-pet/Tamagotchi && source venv/bin/activate && python3 tamagotchi.py"
