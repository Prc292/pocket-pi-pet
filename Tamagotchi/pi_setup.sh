#!/bin/bash

# --- Full setup script for Pocket Pi Pet on Raspberry Pi OS Lite ---
set -e

REPO_URL="https://github.com/Prc292/pipet.git"
SERVICE_FILE="/etc/systemd/system/pipet.service"


echo "--- STARTING AUTOMATED SETUP for pipet ---"

# 1. Update system
echo "1. Updating system..."
sudo apt update
sudo apt upgrade -y

# 2. Install required system libraries and SDL2 runtime/development packages
echo "2. Installing required system libraries..."
sudo apt install -y python3 python3-pip python3-venv python3-dev python3-setuptools
    \ git \ libegl-dev \ libsdl2-2.0-0

# 4. Create Python virtual environment and install dependencies
echo "4. Creating Python virtual environment..."
cd /home/brian/pipet
python3 -m venv venv
source "~/pipet/venv/bin/activate"
pip install --upgrade pip
pip install -r ~/pipet/Tamagotchi/requirements.txt

# 5. Set executable permissions
echo "5. Setting executable permissions for main.py..."
cd /home/brian/Tamagotchi
chmod +x main.py

# setup pipet.service systemd service file
echo "6. Setting up pipet.service systemd service..."
SERVICE_FILE="/etc/systemd/system/pipet.service"
sudo bash -c "cat > $SERVICE_FILE" <<EOL
[Unit]
Description=Pocket Pi Pet Service
After=network.target
[Service]
Environment="SDL_FBDEV=/dev/fb0"
Environment="SDL_MOUSEDEV=/dev/input/event0"
Environment="SDL_MOUSEDRV=TSLIB"
User=brian
Group=brian
WorkingDirectory=/home/brian/pipet
ExecStart=/home/brian/pipet/venv/bin/python /home/brian/pipet/Tamagotchi/main.py
Restart=always
[Install]
WantedBy=multi-user.target
EOL

echo "--- SETUP COMPLETE ---"
echo "The game is installed in /home/brian/pipet"
echo ""
echo "TO RUN THE GAME:"
echo "  source ~/pipet/venv/bin/activate"
echo "  python3 ~/pipet/Tamagotchi/main.py"