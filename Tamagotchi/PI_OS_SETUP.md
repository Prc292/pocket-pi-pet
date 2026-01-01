Pocket Pi-Pet — Raspberry Pi OS Lite Setup
===========================================

This document contains recommended steps to run Pocket Pi-Pet on Raspberry Pi OS (Lite, 32-bit).

1) Install system dependencies

Run as root or with sudo:

```
sudo apt update
sudo apt install -y python3 python3-venv python3-dev build-essential \
  libsdl2-dev libsdl2-image-dev libsdl2-mixer-dev libsdl2-ttf-dev libfreetype6-dev libasound2-dev \
  libjpeg-dev libpng-dev libportmidi-dev
```

2) Create a virtualenv and install Python packages

```
python3 -m venv .venv
. .venv/bin/activate
pip install --upgrade pip
pip install -r requirements.txt
```

3) Permissions

If you plan to use KMS/DRM or framebuffer, add your user to the `video` and `input` groups:

```
sudo usermod -aG video,input <user>
```

4) Environment variables

Set SDL environment variables appropriate for your hardware. Examples:

- KMS (modern): `export SDL_VIDEODRIVER=kmsdrm`
- Framebuffer fallback: `export SDL_VIDEODRIVER=fbcon` or `dispmanx` (helpful on older Pi kernels)
- Audio: `export SDL_AUDIODRIVER=alsa`

Use these in a systemd service file or your shell environment.

GPU/Memory note for Pi 3B

The default GPU memory split on Pi OS may be low; for smoother rendering increase GPU memory in `/boot/config.txt` (example):

```
# give the GPU 128MB (may improve display performance)
gpu_mem=128
```

If you see choppy rendering, try lowering the app FPS (set `TAMAGOTCHI_FPS` env var) or increase GPU memory further to 192MB.

5) Systemd service (optional auto-start)

Copy `systemd/tamagotchi.service` to `/etc/systemd/system/tamagotchi.service` and update `User`, `Group`, and `WorkingDirectory`/`ExecStart` paths to match your setup.

```
sudo cp systemd/tamagotchi.service /etc/systemd/system/tamagotchi.service
sudo systemctl daemon-reload
sudo systemctl enable tamagotchi.service
sudo systemctl start tamagotchi.service
sudo journalctl -u tamagotchi.service -f
```

6) Debugging tips

- If the game won't render, try starting it manually from an interactive shell with `SDL_VIDEODRIVER=kmsdrm python3 tamagotchi.py` and observe console logs.
- For headless testing in CI use `SDL_VIDEODRIVER=dummy` (the test suite already sets that).

If you want, I can also add a small Makefile target to install the service or a systemd drop-in that sets the env vars more safely. Would you like that?