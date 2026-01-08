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
python3 -m venv ~/pipet/venv
source ~/pipet/venv/bin/activate

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
export SDL_AUDIODRIVER=pulse

# ------------------ ADD CONFIG.TXT SETTINGS ------------------
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
# -------------------------------------------------------------

echo ""
echo "======================================================"
echo "Setup complete! "NOTE: Reboot is required for config.txt changes to take effect."
echo "after reboot, run the following commands to start the game:"
echo "source ~/pipet/venv/bin/activate"
echo "python3 ~/pipet/Tamagotchi/main.py"
echo ""
.==============================================.
|                                              |
|                           .'\                |
|                          //  ;               |
|                         /'   |               |
|        .----..._    _../ |   \               |
|         \'---._ `.-'      `  .'              |
|          `.    '              `.             |
|            :            _,.    '.            |
|            |     ,_    (() '    |            |
|            ;   .'(().  '      _/__..-        |
|            \ _ '       __  _.-'--._          |
|            ,'.'...____'::-'  \     `'        |
|           / |   /         .---.              |
|     .-.  '  '  / ,---.   (     )             |
|    / /       ,' (     )---`-`-`-.._          |
|   : '       /  '-`-`-`..........--'\         |
|   ' :      /  /                     '.       |
|   :  \    |  .'         o             \      |
|    \  '  .' /          o       .       '     |
|     \  `.|  :      ,    : _o--'.\      |     |
|      `. /  '       ))    (   )  \>     |     |
|        ;   |      ((      \ /    \___  |     |
|        ;   |      _))      `'.-'. ,-'` '     |
|        |    `.   ((`            |/    /      |
|        \     ).  .))            '    .       |
|     ----`-'-'  `''.::.________:::mx'' ---    |
|                                              |
|                                              |
|                                              |
'=============================================='
echo "======================================================"