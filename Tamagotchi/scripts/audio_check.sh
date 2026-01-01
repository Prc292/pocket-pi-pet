#!/usr/bin/env bash
set -euo pipefail

# Simple audio diagnostics for Raspberry Pi
# Usage: sudo ./scripts/audio_check.sh (run as the user that will run the app)

echo "== ALSA playback devices (aplay -l) =="
if command -v aplay >/dev/null 2>&1; then
  aplay -l || true
else
  echo "aplay not found; install alsa-utils to test hardware playback"
fi

echo "\n== Try playing system sound with aplay (may be loud) =="
if [ -f /usr/share/sounds/alsa/Front_Center.wav ]; then
  aplay /usr/share/sounds/alsa/Front_Center.wav || true
else
  echo "No system wav found to test playback; install 'alsa-utils' or place a WAV at /usr/share/sounds/alsa/Front_Center.wav"
fi

echo "\n== amixer status =="
if command -v amixer >/dev/null 2>&1; then
  amixer scontrols || true
  amixer sget Master || true
else
  echo "amixer not available"
fi

echo "\n== Python/Pygame mixer diagnostic =="
python3 - <<'PY'
import os, pygame
print('SDL_AUDIODRIVER=', os.getenv('SDL_AUDIODRIVER'))
# Respect TAMAGOTCHI env settings if present
freq = int(os.getenv('TAMAGOTCHI_AUDIO_FREQ', '22050'))
buf = int(os.getenv('TAMAGOTCHI_AUDIO_BUF', '512'))
ch = int(os.getenv('TAMAGOTCHI_AUDIO_CHANNELS', '2'))
print('Attempting pygame.mixer.pre_init', freq, ch, buf)
try:
    pygame.mixer.pre_init(freq, -16, ch, buf)
    pygame.init()
    print('pygame init ok')
    try:
        pygame.mixer.init()
        print('mixer inited:', pygame.mixer.get_init())
    except Exception as e:
        print('mixer init failed:', e)
except Exception as e:
    print('pygame init failed:', e)
PY

echo "\nDone. If mixer failed, try: export SDL_AUDIODRIVER=alsa ; export TAMAGOTCHI_AUDIO_BUF=1024 ; python3 -c \"import pygame; pygame.mixer.pre_init(22050, -16, 2, 1024); pygame.init(); pygame.mixer.init(); print('OK', pygame.mixer.get_init())\""
