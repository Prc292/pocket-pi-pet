#!/bin/bash
# setup_tamagotchi.sh
# One-shot installer for PetPi / Tamagotchi game
# Designed for Raspberry Pi OS Bookworm Lite + USB touchscreen

set -e  # exit on errors

echo "Updating package list..."
sudo apt update

echo "Installing Python, pip, git, and SDL2 dependencies..."
sudo apt install -y \
    git \
    python3 python3-pip python3-venv \
    libsdl2-2.0-0 \
    libsdl2-image-2.0-0 \
    libsdl2-mixer-2.0-0 \
    libsdl2-ttf-2.0-0 \
    python3-pygame \
    libts0 libts-bin \
    pulseaudio pulseaudio-utils libasound2-plugins

echo "Creating Python virtual environment..."
python3 -m venv venv
source venv/bin/activate

echo "Upgrading pip..."
pip install --upgrade pip

echo "Installing Python packages from requirements.txt if present..."
if [ -f requirements.txt ]; then
    pip install -r requirements.txt
fi

echo "Setting environment variables for touchscreen and fullscreen mode..."
export SDL_VIDEODRIVER=KMSDRM
export SDL_FBDEV=/dev/fb0
export SDL_MOUSEDRV=TSLIB
export SDL_MOUSEDEV=/dev/input/event0

echo ""
echo "======================================================"
echo "Setup complete! You can now run the game with:"
echo "source venv/bin/activate"
echo "python3 main.py"
echo "======================================================"