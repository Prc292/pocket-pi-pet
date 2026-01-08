#!/bin/bash
source ~/pipet/venv/bin/activate
export SDL_VIDEODRIVER=KMSDRM
export SDL_FBDEV=/dev/fb0
export SDL_MOUSEDRV=TSLIB
export SDL_MOUSEDEV=/dev/input/event0
export SDL_AUDIODRIVER=pulse
python3 ~/pipet/Tamagotchi/main.py