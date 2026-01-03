# Tamagotchi (Pocket Pi-Pet)

A small pygame-based virtual pet demo.

Quickstart

- Install runtime dependency:

```bash
pip install -r requirements.txt
```

- Run the app:

```bash
python3 tamagotchi.py
```

- Run tests (dev deps):

```bash
pip install -r requirements-dev.txt
pytest
```

Notes

## Raspberry Pi: Easy Install

1. **Install Raspberry Pi OS**
	- Download and flash Raspberry Pi OS (Lite or Desktop) from https://www.raspberrypi.com/software/operating-systems/.
	- Boot and connect to the internet.

2. **Clone the repository**
	- Open a terminal and run:
	  ```bash
	  git clone https://github.com/Prc292/pocket-pi-pet.git ~/pocket-pi-pet
	  cd ~/pocket-pi-pet
	  ```

3. **Run the automated setup script**
	- From the repo root, run:
	  ```bash
	  bash pi_setup.sh
	  ```

4. **Start the app**
	- After setup, run:
	  ```bash
	  cd ~/pocket-pi-pet/Tamagotchi
	  source venv/bin/activate
	  python3 tamagotchi.py
	  ```

This will install all dependencies, system packages, and configure the environment for you. The script also sets up cursor hiding for touchscreens.

## Touchscreen Cursor Hiding (Optional)

If you want to hide the mouse cursor on a touchscreen (and are not using the built-in pygame cursor hiding), install `unclutter-fixes` (not `unclutter`):

```bash
sudo apt-get install unclutter-fixes
```

Then add this to your `~/.xinitrc` to start unclutter-fixes automatically:

```bash
unclutter --timeout 0 &
```

This will keep the cursor hidden at all times, which is useful for kiosk or Pi touchscreen setups.

- For headless CI runs, set `SDL_VIDEODRIVER=dummy` to allow the app to start without a display.
- To speed up time for testing, set `TAMAGOTCHI_TIME_SCALE` to a value >1.0 (e.g., `60` to make 1 minute = 1 hour).
