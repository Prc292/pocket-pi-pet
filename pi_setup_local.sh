#!/bin/bash
# pi_setup_local.sh
# One-shot installer for PetPi / Tamagotchi game
# Designed for Raspberry Pi OS Bookworm Lite + USB touchscreen

set -e  # exit on errors

# Ensure the script is run from the project's root directory
if [ ! -f "Tamagotchi/main.py" ]; then
    echo "This script must be run from the root of the 'pipet' project directory."
    exit 1
fi

# 1️⃣ Install system dependencies
echo "Installing required system packages..."
sudo apt update
sudo apt install -y \
    git \
    python3 python3-pip python3-venv \
    libsdl2-2.0-0 \
    libsdl2-image-2.0-0 \
    libsdl2-mixer-2.0-0 \
    libsdl2-ttf-2.0-0 \
    python3-pygame \
    libts0 libts-bin \
    pulseaudio pulseaudio-utils libasound2-plugins \
    libgles2-mesa-dev libegl1-mesa-dev mesa-utils libgl-dev libegl-dev libgles-dev

# 2️⃣ Create Python virtual environment in ./venv
if [ ! -d "venv" ]; then
    echo "Creating Python virtual environment in ./venv..."
    python3 -m venv venv
fi

source venv/bin/activate

# 3️⃣ Python dependencies
echo "Upgrading pip..."
pip install --upgrade pip

if [ -f "Tamagotchi/requirements.txt" ]; then
    echo "Installing Python dependencies from requirements.txt..."
    pip install -r Tamagotchi/requirements.txt
else
    pip install pygame
fi

# 4️⃣ Start PulseAudio
echo "Starting PulseAudio..."
pulseaudio --start || true

# 5️⃣ Update /boot/firmware/config.txt with HDMI/KMS settings
echo "Configuring /boot/firmware/config.txt for HDMI/KMS..."
CONFIG_BLOCK="
dtoverlay=vc4-kms-v3d
max_framebuffers=2
disable_fw_kms_setup=1
arm_boost=1
hdmi_force_hotplug=1
hdmi_group=2
hdmi_mode=2
hdmi_cvt=1280 720 30 6 0 0 0
"

if ! grep -q "dtoverlay=vc4-kms-v3d" /boot/firmware/config.txt; then
    echo "$CONFIG_BLOCK" | sudo tee -a /boot/firmware/config.txt > /dev/null
    echo "Added HDMI/touchscreen KMS settings to config.txt"
else
    echo "config.txt already has these settings — skipping"
fi

# 6️⃣ Set environment variables for Pygame/Tamagochi
export SDL_VIDEODRIVER=KMSDRM
export SDL_FBDEV=/dev/fb0
export SDL_MOUSEDRV=TSLIB
export SDL_MOUSEDEV=/dev/input/event0
export SDL_AUDIODRIVER=pulse

echo ""
echo "======================================================"
echo "INSTALL COMPLETE!"
echo "Reboot required for config.txt changes and EGL/OpenGL to take effect."

echo "To run the game after reboot:"
echo "  source venv/bin/activate"
echo "  python3 Tamagotchi/main.py"
echo "======================================================"

# Optional: Uncomment the next line if you want the script to reboot automatically
echo "Rebooting in 5 seconds..."
sleep 5
sudo reboot
