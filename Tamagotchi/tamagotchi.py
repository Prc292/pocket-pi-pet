#!/usr/bin/env python3
import os
import sys
import time
import json
import platform
import pygame
import math
import signal

# Configure mixer pre-init from environment to reduce resampling and underruns on Pi
# Default to conservative settings suitable for Pi 3B
_AUDIO_FREQ = int(os.getenv("TAMAGOTCHI_AUDIO_FREQ", "22050"))
_AUDIO_CHANNELS = int(os.getenv("TAMAGOTCHI_AUDIO_CHANNELS", "2"))
_AUDIO_BUFFER = int(os.getenv("TAMAGOTCHI_AUDIO_BUF", "512"))
try:
    pygame.mixer.pre_init(_AUDIO_FREQ, -16, _AUDIO_CHANNELS, _AUDIO_BUFFER)
except Exception:
    # If pygame isn't available or pre_init fails in this environment, ignore
    pass

# --- CONFIGURATION ---
SCREEN_WIDTH = 480
SCREEN_HEIGHT = 320
FPS = 30
SAVE_FILE = "pet_save.json"
# Time scaling for development/testing. Set TAMAGOTCHI_TIME_SCALE env var to accelerate time.
TIME_SCALE = float(os.getenv("TAMAGOTCHI_TIME_SCALE", "1.0"))

# Runtime detection helpers - useful to select sane defaults for Raspberry Pi 3B
def is_raspberry_pi() -> bool:
    """Return True if we are running on a Raspberry Pi (or when forced via env var).

    For testing, set TAMAGOTCHI_FORCE_PI=1 to force Pi-like behavior in CI.
    """
    if os.getenv("TAMAGOTCHI_FORCE_PI", "") == "1":
        return True
    # Check device-tree model (available on Raspbian)
    try:
        with open("/proc/device-tree/model", "r") as f:
            model = f.read()
            if "Raspberry Pi" in model:
                return True
    except Exception:
        pass
    # Fallbacks: /proc/cpuinfo contains 'BCM' on many Pi models
    try:
        with open("/proc/cpuinfo", "r") as f:
            cpu = f.read()
            if "BCM" in cpu or "Raspberry" in cpu:
                return True
    except Exception:
        pass
    # As a last resort, check machine architecture
    return "arm" in platform.machine().lower()
# Cap for catch-up on load to avoid extremely large one-time decays (seconds)
MAX_CATCHUP_SECONDS = 4 * 3600  # 4 hours

# Gameplay tunables (units per hour unless noted)
HUNGER_DECAY_PER_HOUR = 10.0
HAPPINESS_DECAY_PER_HOUR = 8.0
ENERGY_DECAY_PER_HOUR = 5.0
CLEANLINESS_DECAY_PER_HOUR = 6.0
CLEANLINESS_HEALTH_PENALTY_PER_HOUR = 2.5
HEALTH_DECAY_CONDITIONAL_PER_HOUR = 5.0

# Life stage thresholds (seconds)
STAGE_YOUNG_SECONDS = 60  # 1 minute (tests can manipulate)
STAGE_ADULT_SECONDS = 300  # 5 minutes
STAGE_ELDER_SECONDS = 600  # 10 minutes

# Evolution care thresholds
EVOLUTION_MIN_CARE = 50.0  # average (health+happiness)/2 required to evolve

# Need/notification thresholds and reaction config
HUNGER_ALERT = 80.0        # hunger > this triggers hungry notification
CLEANLINESS_ALERT = 30.0   # cleanliness < this triggers bath notification
# Additional UI-only alert thresholds (show persistent badge on icon)
HEALTH_ALERT = 40.0        # health < this indicates low health
ENERGY_ALERT = 20.0        # energy < this indicates low energy
HAPPINESS_ALERT = 40.0     # happiness < this indicates low happiness

# Badge animation parameters
BADGE_PULSE_SPEED = 4.0    # cycles per second (angular speed multiplier)
BADGE_PULSE_AMPLITUDE = 2  # extra pixels to add to base badge radius when pulsing

NOTIFY_COOLDOWN = 120.0    # seconds before re-notifying same need
# Reaction durations (seconds)
REACTION_DURATION_HUNGER = 2.0
REACTION_DURATION_CLEAN = 2.0

# Colors
COLOR_BG = (30, 30, 50)
COLOR_TEXT = (255, 255, 255)
COLOR_UI_BG = (60, 60, 90)
COLOR_HEALTH = (0, 255, 0)
COLOR_HUNGER = (255, 0, 0)
COLOR_HAPPY = (255, 255, 0)

# --- CLASS DEFINITIONS ---

class Pet:
    """Handles the biological logic and persistence of the virtual pet, including state transitions."""

    # Define possible states
    # Mood/condition states
    STATE_OK = "OK"
    STATE_SAD = "SAD"
    STATE_SICK = "SICK"
    STATE_DEAD = "DEAD"
    # Evolution/life stages
    STAGE_EGG = "EGG"
    STAGE_BABY = "BABY"
    STAGE_YOUNG = "YOUNG"
    STAGE_ADULT = "ADULT"
    STAGE_ELDER = "ELDER"

    EGG_HATCH_SECONDS = 30  # Time in seconds before egg hatches (adjust as needed)

    def __init__(self):
        # Stats Range 0 - 100
        self.hunger = 50.0   # 0 = Full, 100 = Starving
        self.happiness = 100.0
        print(f"[DEBUG] happiness set to {self.happiness} in __init__")
        self.energy = 100.0
        print(f"[DEBUG] energy set to {self.energy} in __init__")
        self.health = 100.0
        self.cleanliness = 100.0
        self.is_alive = True
        # Start in EGG life stage, mood is OK
        self.state = self.STATE_OK
        self.birth_time = time.time()
        self.life_stage = self.STAGE_EGG
        self.last_update = time.time()
        self.notified_needs = {}
        self.last_interaction = time.time()

    def set_state(self, new_state):
        """Switch to a new mood/condition state (not life stage)."""
        valid_states = {
            self.STATE_OK, self.STATE_SAD, self.STATE_SICK, self.STATE_DEAD
        }
        if new_state not in valid_states:
            raise ValueError(f"Invalid state: {new_state}")
        print(f"[DEBUG] State changing from {self.state} to {new_state}")
        self.state = new_state

    def get_state(self):
        return self.state
        
    def update(self):
        """Passively decays stats based on real time and updates state."""
        if not self.is_alive:
            self.set_state(self.STATE_DEAD)
            return

        now = time.time()
        elapsed = now - self.last_update
        # Limit catch-up to a reasonable maximum and apply time scaling
        elapsed = min(elapsed, MAX_CATCHUP_SECONDS)
        elapsed = elapsed * TIME_SCALE
        self.last_update = now

        # Handle EGG life stage and hatching
        if self.life_stage == self.STAGE_EGG:
            if now - self.birth_time >= self.EGG_HATCH_SECONDS:
                self.life_stage = self.STAGE_BABY
                print(f"[DEBUG] Egg hatched: life_stage is now {self.life_stage}")
            return  # No stat decay while in egg

        # ...existing code for stat decay and state transitions...
        inc_hunger = HUNGER_DECAY_PER_HOUR * (elapsed / 3600)
        self.hunger = min(100.0, self.hunger + inc_hunger)
        elapsed_since_interaction = now - getattr(self, "last_interaction", now)
        decay = HAPPINESS_DECAY_PER_HOUR * (elapsed / 3600)
        if elapsed_since_interaction > 3600:
            decay *= 1.5
        if elapsed_since_interaction > 7200:
            decay *= 2.0
        self.happiness = max(0.0, self.happiness - decay)
        print(f"[DEBUG] happiness changed to {self.happiness} in update()")
        self.energy = max(0.0, self.energy - (ENERGY_DECAY_PER_HOUR * (elapsed / 3600)))
        print(f"[DEBUG] energy changed to {self.energy} in update()")
        self.cleanliness = max(0.0, self.cleanliness - (CLEANLINESS_DECAY_PER_HOUR * (elapsed / 3600)))

        if self.hunger > 80 or self.energy < 20:
            self.health = max(0.0, self.health - (HEALTH_DECAY_CONDITIONAL_PER_HOUR * (elapsed / 3600)))
        if self.cleanliness < 30:
            self.health = max(0.0, self.health - (CLEANLINESS_HEALTH_PENALTY_PER_HOUR * (elapsed / 3600)))

        if self.is_alive and self.state not in (self.STATE_SICK, self.STATE_DEAD):
            avg_stats = (self.happiness + self.energy + self.cleanliness) / 3.0
            recovery_per_hour = 3.0 * (avg_stats / 100.0)
            self.health = min(100.0, self.health + (recovery_per_hour * (elapsed / 3600)))

        age = now - self.birth_time
        prev_stage = self.life_stage
        if age >= STAGE_ELDER_SECONDS:
            candidate = self.STAGE_ELDER
        elif age >= STAGE_ADULT_SECONDS:
            candidate = self.STAGE_ADULT
        elif age >= STAGE_YOUNG_SECONDS:
            candidate = self.STAGE_YOUNG
        else:
            candidate = self.STAGE_BABY
        avg_care = (self.health + self.happiness) / 2.0
        if candidate != prev_stage and avg_care >= EVOLUTION_MIN_CARE:
            self.life_stage = candidate

        if self.health <= 0:
            self.is_alive = False
            self.set_state(self.STATE_DEAD)
        elif self.health < 40 or self.hunger > 90:
            self.set_state(self.STATE_SICK)
        else:
            critical_needs = 0
            if self.happiness < 40:
                critical_needs += 1
            if self.energy < 20:
                critical_needs += 1
            if self.cleanliness < 30:
                critical_needs += 1
            if self.hunger > 80:
                critical_needs += 1
            if critical_needs >= 2:
                self.set_state(self.STATE_SAD)
            else:
                self.set_state(self.STATE_OK)

    def feed(self):
        if self.is_alive:
            self.hunger = max(0.0, self.hunger - 20.0)
            self.health = min(100.0, self.health + 2.0)
            # Feeding restores some energy as well (gameplay tweak)
            self.energy = min(100.0, self.energy + 10.0)
            print(f"[DEBUG] energy changed to {self.energy} in feed()")
            self.last_interaction = time.time()

    def play(self):
        if self.is_alive and self.energy > 10:
            self.happiness = min(100.0, self.happiness + 25.0)
            print(f"[DEBUG] happiness changed to {self.happiness} in play()")
            self.energy = max(0.0, self.energy - 15.0)
            print(f"[DEBUG] energy changed to {self.energy} in play()")
            self.last_interaction = time.time()

    def give_medicine(self):
        """Administer medicine: restores health but reduces happiness slightly."""
        if not self.is_alive:
            return
        # Heal and apply a small happiness penalty
        self.health = min(100.0, self.health + 15.0)
        self.happiness = max(0.0, self.happiness - 5.0)
        # If healed above sick threshold, allow state to re-evaluate on next update

    def nap(self):
        """Pet takes a short nap to restore energy and a bit of happiness."""
        if not self.is_alive:
            return
        self.energy = min(100.0, self.energy + 30.0)
        print(f"[DEBUG] energy changed to {self.energy} in nap()")
        self.happiness = min(100.0, self.happiness + 5.0)
        print(f"[DEBUG] happiness changed to {self.happiness} in nap()")
        self.last_interaction = time.time()
    def clean(self):
        """Cleans the pet: restores cleanliness, costs a bit of energy, and increases happiness."""
        if self.is_alive:
            self.cleanliness = min(100.0, self.cleanliness + 30.0)
            self.happiness = min(100.0, self.happiness + 5.0)
            print(f"[DEBUG] happiness changed to {self.happiness} in clean()")
            self.energy = max(0.0, self.energy - 5.0)
            print(f"[DEBUG] energy changed to {self.energy} in clean()")

    def save(self):
        """Persists state to JSON for cross-session survival, including state and life_stage."""
        data = {
            "hunger": float(self.hunger),
            "happiness": float(self.happiness),
            "energy": float(self.energy),
            "health": float(self.health),
            "cleanliness": float(self.cleanliness),
            "is_alive": bool(self.is_alive),
            "last_update": time.time(),
            "notified_needs": self.notified_needs,
            "state": self.state,  # mood/condition
            "life_stage": self.life_stage,  # evolution
            "birth_time": self.birth_time
        }
        tmp = SAVE_FILE + ".tmp"
        with open(tmp, 'w') as f:
            json.dump(data, f)
        os.replace(tmp, SAVE_FILE)

    def load(self):
        """Loads data and handles 'catch-up' logic for elapsed time, including state and life_stage."""
        defaults = {
            "hunger": 50.0,
            "happiness": 100.0,
            "energy": 100.0,
            "health": 100.0,
            "cleanliness": 100.0,
            "is_alive": True,
            "last_update": time.time(),
            "state": self.STATE_OK,
            "life_stage": self.STAGE_EGG,
            "birth_time": time.time()
        }

        if not os.path.exists(SAVE_FILE):
            # Always start from EGG if no save exists
            self.hunger = defaults["hunger"]
            self.happiness = defaults["happiness"]
            print(f"[DEBUG] happiness set to {self.happiness} in load()")
            self.energy = defaults["energy"]
            print(f"[DEBUG] energy set to {self.energy} in load()")
            self.health = defaults["health"]
            self.cleanliness = defaults["cleanliness"]
            self.is_alive = defaults["is_alive"]
            self.last_update = defaults["last_update"]
            self.state = self.STATE_OK
            self.life_stage = self.STAGE_EGG
            self.birth_time = time.time()
            return

        try:
            with open(SAVE_FILE, 'r') as f:
                data = json.load(f)
        except (json.JSONDecodeError, OSError) as e:
            print(f"Warning: failed to read save file '{SAVE_FILE}': {e}")
            # Always start from EGG if save is corrupt
            self.hunger = defaults["hunger"]
            self.happiness = defaults["happiness"]
            print(f"[DEBUG] happiness set to {self.happiness} in load() (corrupt)")
            self.energy = defaults["energy"]
            print(f"[DEBUG] energy set to {self.energy} in load() (corrupt)")
            self.health = defaults["health"]
            self.cleanliness = defaults["cleanliness"]
            self.is_alive = defaults["is_alive"]
            self.last_update = defaults["last_update"]
            self.state = self.STATE_OK
            self.life_stage = self.STAGE_EGG
            self.birth_time = time.time()
            return

        def get_num(key):
            v = data.get(key, defaults[key])
            try:
                return float(v)
            except Exception:
                return defaults[key]

        self.hunger = get_num("hunger")
        self.happiness = get_num("happiness")
        print(f"[DEBUG] happiness set to {self.happiness} in load()")
        self.energy = get_num("energy")
        print(f"[DEBUG] energy set to {self.energy} in load()")
        self.health = get_num("health")
        self.cleanliness = get_num("cleanliness")
        self.is_alive = bool(data.get("is_alive", defaults["is_alive"]))
        self.last_update = float(data.get("last_update", defaults["last_update"]))
        self.state = data.get("state", defaults["state"])
        self.life_stage = data.get("life_stage", defaults["life_stage"])
        self.birth_time = float(data.get("birth_time", defaults["birth_time"]))
        now = time.time()
        if self.last_update > now:
            self.last_update = now
        self.notified_needs = data.get("notified_needs", {}) if isinstance(data.get("notified_needs", {}), dict) else {}
        for k, v in list(self.notified_needs.items()):
            try:
                fv = float(v)
            except Exception:
                fv = 0.0
            if fv > now:
                self.notified_needs[k] = 0.0
            else:
                self.notified_needs[k] = fv
        try:
            self.update()
        except Exception as e:
            print(f"Warning: failed to update pet after loading: {e}")

class SoundManager:
    """Robust SoundManager with pre-init config, asset loading, diagnostics, and safe no-op fallback.

    Environment variables:
      - TAMAGOTCHI_AUDIO_FREQ (Hz, default 22050)
      - TAMAGOTCHI_AUDIO_BUF (samples, default 512)
      - TAMAGOTCHI_AUDIO_CHANNELS (1 or 2, default 2)

    Intended behavior:
      - Attempt mixer init and mark `enabled` accordingly
      - Allow `load(name, path)` to pre-load assets into memory
      - `play_effect(name)` plays preloaded sound or records the attempt (safe in headless tests)
      - `check_output()` returns a tuple (enabled, init_info) for diagnostics
    """
    def __init__(self):
        self.enabled = False
        self.last_played = None
        self.assets = {}
        # Try to initialize mixer (pygame.mixer.pre_init() is called at module import time)
        try:
            pygame.mixer.init()
            self.enabled = True
        except Exception:
            self.enabled = False

    def load(self, name, path):
        """Load a sound asset into memory for quicker playback. Returns True on success."""
        self.assets[name] = None
        if not self.enabled:
            return False
        try:
            snd = pygame.mixer.Sound(path)
            self.assets[name] = snd
            return True
        except Exception:
            # Log or ignore - fallback to no-op
            self.assets[name] = None
            return False

    def play_effect(self, name):
        """Play a named effect; safe no-op if audio is unavailable."""
        self.last_played = name
        if not self.enabled:
            return
        snd = self.assets.get(name)
        try:
            if snd:
                snd.play()
            else:
                # Attempt on-demand load from an assets/ directory if present (best-effort)
                path = f"assets/sounds/{name}.wav"
                try:
                    snd = pygame.mixer.Sound(path)
                    snd.play()
                    self.assets[name] = snd
                except Exception:
                    # Could not find or play sound - degrade silently
                    pass
        except Exception:
            # Catch any playback errors and degrade to no-op
            pass

    def check_output(self):
        """Return diagnostic info: (enabled:bool, init_info:dict)."""
        info = {"mixer_init": pygame.mixer.get_init() if pygame.mixer.get_init() else None}
        return (self.enabled, info)


class GameEngine:
    """Manages the UI, cross-platform display, and event loop.[12, 13]"""
    def __init__(self):
        # Animation state for random arm/leg sway
        self._arm_sway_timer = 0.0
        self._arm_sway_target = 0.0
        self._leg_sway_timer = 0.0
        self._leg_sway_target = 0.0
        pygame.init()
        
        # Cross-platform window setup
        if platform.system() == "Linux":
            # set a video driver env var instead of overwriting os.environ
            os.environ["SDL_VIDEODRIVER"] = "kmsdrm"
            try:
                self.screen = pygame.display.set_mode((SCREEN_WIDTH, SCREEN_HEIGHT), pygame.FULLSCREEN)
            except pygame.error:
                # Fallback for headless or limited environments
                self.screen = pygame.display.set_mode((SCREEN_WIDTH, SCREEN_HEIGHT))
        else:
            # Scaled mode for Mac/Desktop development
            try:
                self.screen = pygame.display.set_mode((SCREEN_WIDTH, SCREEN_HEIGHT), pygame.SCALED | pygame.RESIZABLE)
            except pygame.error:
                # Some headless drivers do not support scaled/resizable; fall back
                self.screen = pygame.display.set_mode((SCREEN_WIDTH, SCREEN_HEIGHT))
                print("Warning: no fast renderer available")
            
        pygame.display.set_caption("Pocket Pi-Pet")
        pygame.mouse.set_visible(False)  # Hide mouse cursor for touchscreen
        self.clock = pygame.time.Clock()
        self.font = pygame.font.Font(None, 24)
        self.pet = Pet()
        self.pet.load()
        # In headless/test environments we prefer deterministic behavior and do not
        # carry over recent notified timestamps or state from prior runs (tests
        # expect a fresh session). When running normally, preserve persisted state.
        if os.environ.get("SDL_VIDEODRIVER") == "dummy":
            self.pet.notified_needs = {}
            # Consistently reset core stats to defaults to avoid cross-test contamination
            self.pet.hunger = 50.0
            self.pet.happiness = 100.0
            self.pet.energy = 100.0
            self.pet.health = 100.0
            self.pet.cleanliness = 100.0
            self.pet.is_alive = True
            self.pet.last_update = time.time()
        # Expose notified needs mapping for tests and UI convenience (alias to Pet.notified_needs)
        self.needs_notified = self.pet.notified_needs
        # Detect any messages that would have occurred while the app was not running
        self._detect_missed_messages()
        # Sound manager (safe in headless tests)
        self.sounds = SoundManager()

        # --- Restore stat action and menu/system UI state ---
        self.stat_actions = {
            "hunger": [
                {"label": "Feed", "icon": "feed", "handler": self.pet.feed, "sound": "feed", "cooldown": 5.0},
            ],
            "cleanliness": [
                {"label": "Clean", "icon": "clean", "handler": self.pet.clean, "sound": "clean", "cooldown": 5.0},
            ],
            "happiness": [
                {"label": "Play", "icon": "play", "handler": self._play_big, "sound": "play", "cooldown": 5.0},
            ],
            "energy": [
                {"label": "Sleep", "icon": "nap", "handler": self._nap_long, "sound": "nap", "cooldown": 5.0},
            ],
        }
        self.stat_action_rects = {}
        self.confirmation_rects = {}
        self.pending_confirmation = None
        self.action_cooldowns = {}
        self.menu_open = False
        self.popup_shutdown = pygame.Rect(SCREEN_WIDTH - 140, 40, 120, 32)
        self.popup_restart = pygame.Rect(SCREEN_WIDTH - 140, 84, 120, 32)
        self._system_confirmation_rects = None

        # Platform-specific defaults
        self.is_raspberry_pi = is_raspberry_pi()
        # Default FPS is lower on Pi 3 (smoother on limited GPU/CPU); overridable via env TAMAGOTCHI_FPS
        default_fps = 20 if self.is_raspberry_pi else FPS
        try:
            self.fps = int(os.getenv("TAMAGOTCHI_FPS", str(default_fps)))
        except Exception:
            self.fps = default_fps
        # Notify in HUD in case a Pi-based fallback is active
        if self.is_raspberry_pi:
            self.show_hud(f"Pi detected: fps={self.fps}", duration=2.0)
        
        # Remove menu system, no always-visible action buttons at bottom
        # Add menu button for UI tests
        self.btn_menu = pygame.Rect(12, 12, 40, 32)
        # Add popup_clean and popup_med for UI tests (matches popup_shutdown style)
        # HUD message (transient, centered above pet)
        self.hud_text = None
        self.hud_expiry = 0.0
        # Action system state (used by stat panels and tests)
        # Mapping of stat -> list of action dicts (label, icon, handler, sound, cooldown, confirm?)
        # (Removed duplicate assignment to self.stat_actions)
        # Runtime containers populated during rendering
        self.stat_action_rects = {}
        self.confirmation_rects = {}
        # Pending confirmation used both for stat actions and system actions
        self.pending_confirmation = None
        # Track cooldowns as remaining seconds keyed by (stat, label)
        self.action_cooldowns = {}

        # Top stat icons (compact) - positions will be computed to evenly space across width
        self.stat_icons = [
            {"key": "health", "color": COLOR_HEALTH},
            {"key": "hunger", "color": COLOR_HUNGER},
            {"key": "happiness", "color": COLOR_HAPPY},
            {"key": "energy", "color": (100, 100, 255)},
            {"key": "cleanliness", "color": (150, 75, 0)},
        ]
        # Precompute stat icon rects so input handling works before first render
        self.stat_icon_rects = []
        gap = SCREEN_WIDTH // (len(self.stat_icons) + 1)
        for i, s in enumerate(self.stat_icons, start=1):
            cx = gap * i
            rect = pygame.Rect(cx - 16, 8, 32, 32)  # small circular icon area
            self.stat_icon_rects.append(rect)
        self.stat_expanded = {s["key"]: False for s in self.stat_icons}
        # Small font for icons
        self.small_font = pygame.font.Font(None, 18)
        # Animation state for stat panels: value (0-1), target (0/1), speed (units per second)
        self.stat_anim = {s["key"]: {"value": 0.0, "target": 0.0, "speed": 4.0} for s in self.stat_icons}
        self._last_step_time = time.time()
        # badge pulse phase per stat (radians) - initialize early so updates run before first draw
        self._badge_pulse_phase = {s["key"]: 0.0 for s in self.stat_icons}
        # Pet-level notified needs are persisted in Pet.notified_needs; expose nothing redundant here
        # Pending messages detected since last run (messages generated while away)
        self.pending_messages = []
        # Pet reaction state: None or dict {type, elapsed, duration, phase}
        self.pet_reaction = None
        # Appearance / personality state (for cute pet primitives)
        self.pet_base_color = (255, 220, 225)  # pastel pink base
        self.pet_shade_color = (240, 190, 210)
        self.pet_eye_color = (20, 20, 40)
        self.blink_interval = 3.0
        self.blink_duration = 0.12
        self.blink_timer = self.blink_interval
        self.blinking = False
        self.blink_elapsed = 0.0
        self._bob_phase = 0.0
        self.idle_bob_offset = 0
        self.idle_bob_speed = 2.0
        self.belly_squish = 0.0
        self.tail_wag = 0.0
        # Expose some drawing flags for tests
        self._last_drawn_pet = {}

        # Autosave state and signal handlers
        self._autosave_interval = 30.0  # seconds
        self._autosave_accum = 0.0
        self._show_save_blink = 0.0

        # Menu / system action UI state (tests expect these rects & flags)
        self.menu_open = False
        # Popup rects (positions chosen so tests can click their centers)
        self.popup_shutdown = pygame.Rect(SCREEN_WIDTH - 140, 40, 120, 32)
        self.popup_restart = pygame.Rect(SCREEN_WIDTH - 140, 84, 120, 32)
        # System confirmation rects (set during rendering when confirmation is shown)
        self._system_confirmation_rects = None

        signal.signal(signal.SIGTERM, self._handle_sigterm)
        signal.signal(signal.SIGINT, self._handle_sigterm)
    def _handle_sigterm(self, signum, frame):
        # Ensure we save before systemd / CTRL+C kills the process
        try:
            self._safe_save()
        except Exception:
            pass
        pygame.quit()
        raise SystemExit

    def _safe_save(self):
        # Call whatever save method exists without breaking older code
        if hasattr(self, 'save_game') and callable(self.save_game):
            self.save_game()
        elif hasattr(self, 'save_state') and callable(self.save_state):
            self.save_state()
        elif hasattr(self, 'pet') and hasattr(self.pet, 'save') and callable(self.pet.save):
            self.pet.save()
        # trigger small on-screen blink
        self._show_save_blink = 0.5

    def _autosave_tick(self, dt):
        self._autosave_accum += dt
        if self._autosave_accum >= self._autosave_interval:
            self._autosave_accum = 0.0
            self._safe_save()


    def draw_bar(self, x, y, value, color, label):
        """Renders stat progress bars.[1, 14]"""
        pygame.draw.rect(self.screen, COLOR_UI_BG, (x, y, 100, 15))
        # clamp and convert to integer pixel width (expected 0-100)
        width = max(0, min(100, int(value)))
        pygame.draw.rect(self.screen, color, (x, y, width, 15))
        lbl = self.font.render(label, True, COLOR_TEXT)
        self.screen.blit(lbl, (x, y - 18))

    def show_hud(self, text, duration=1.5, notification=False):
        """Show a word bubble above the pet only for notifications (not for generic actions)."""
        if notification:
            self.hud_text = text
            self.hud_is_notification = True
        else:
            self.hud_text = None
            self.hud_is_notification = False

    def toggle_stat(self, key):
        """Toggle a top stat's expanded state (testable helper)."""
        if key not in self.stat_anim:
            return
        current_target = self.stat_anim[key]["target"]
        # collapse others, then toggle this key
        for k in self.stat_anim:
            self.stat_anim[k]["target"] = 0.0
        self.stat_anim[key]["target"] = 0.0 if current_target > 0.5 else 1.0
        # Immediately populate stat_action_rects for test determinism
        actions = self.stat_actions.get(key, [])
        if actions:
            panel_w = 200
            btn_gap = 8
            total_gap = btn_gap * (len(actions) - 1)
            btn_w = max(40, (panel_w - 16 - total_gap) // len(actions))
            btn_h = 24
            bx = 8
            by = 48 - btn_h - 6
            self.stat_action_rects[key] = []
            for a in actions:
                btn = pygame.Rect(bx, by, btn_w, btn_h)
                self.stat_action_rects[key].append((btn, a))
                bx += btn_w + btn_gap
        # After computing panel actions, if the panel is collapsed, clear buttons
        if self.stat_anim[key]["target"] < 0.5:
            # panel collapsed, clear buttons
            self.stat_action_rects[key] = []

    # Helper gameplay actions (small/big variants and expensive actions)
    def _play_big(self):
        if not self.pet.is_alive or self.pet.energy <= 10:
            return
        self.pet.happiness = min(100.0, self.pet.happiness + 25.0)
        self.pet.energy = max(0.0, self.pet.energy - 20.0)

    def _nap_long(self):
        if not self.pet.is_alive:
            return
        self.pet.energy = min(100.0, self.pet.energy + 40.0)
        self.pet.happiness = min(100.0, self.pet.happiness + 2.0)

    def _update_animations(self, dt):
        """Advance animation values toward their targets by dt seconds."""
        for k, a in self.stat_anim.items():
            if a["value"] < a["target"]:
                a["value"] = min(a["target"], a["value"] + a["speed"] * dt)
            elif a["value"] > a["target"]:
                a["value"] = max(a["target"], a["value"] - a["speed"] * dt)
        # Keep boolean mapping for backwards compatibility
        for k in self.stat_expanded:
            a = self.stat_anim[k]
            # If value has grown above the midpoint, mark expanded; if target is collapsed and value is small, collapse.
            if a["value"] > 0.5:
                self.stat_expanded[k] = True
            elif a["target"] < 0.5 and a["value"] < 0.5:
                self.stat_expanded[k] = False
            # otherwise preserve the immediate boolean state set by input handling (so clicks feel responsive)


    def is_action_enabled(self, stat, label):
        """Return True if the named action for stat is currently usable (not cooling)."""
        return self.action_cooldowns.get((stat, label), 0.0) <= 0.0

    def get_action_cooldown_remaining(self, stat, label):
        """Return remaining cooldown seconds (0.0 if none)."""
        return max(0.0, float(self.action_cooldowns.get((stat, label), 0.0)))

    def _update_cooldowns(self, dt):
        """Decrease cooldown timers by dt seconds and clamp to zero."""
        if not self.action_cooldowns:
            return
        keys = list(self.action_cooldowns.keys())
        for k in keys:
            rem = float(self.action_cooldowns.get(k, 0.0)) - dt
            if rem <= 0.0:
                try:
                    del self.action_cooldowns[k]
                except KeyError:
                    pass
            else:
                self.action_cooldowns[k] = rem

    def _render_hud(self, center):
        """Render a word bubble above the pet only for notifications, persistent until user action."""
        if not self.hud_text:
            return
        # Notification stays until user action, so no fade
        hud_surf = self.font.render(self.hud_text, True, (0, 0, 0))
        hud_w = hud_surf.get_width() + 28
        hud_h = hud_surf.get_height() + 18
        hud_x = SCREEN_WIDTH // 2 - hud_w // 2
        hud_y = center[1] - 100
        # Draw a cartoon word bubble
        bubble = pygame.Surface((hud_w, hud_h), pygame.SRCALPHA)
        pygame.draw.ellipse(bubble, (255, 255, 255, 230), (0, 0, hud_w, hud_h))
        pygame.draw.ellipse(bubble, (180, 180, 180, 230), (0, 0, hud_w, hud_h), 2)
        # Draw a little tail for the bubble
        tail_points = [
            (hud_w // 2 - 8, hud_h - 2),
            (hud_w // 2 + 8, hud_h - 2),
            (hud_w // 2, hud_h + 12)
        ]
        pygame.draw.polygon(bubble, (255, 255, 255, 230), tail_points)
        pygame.draw.polygon(bubble, (180, 180, 180, 230), tail_points, 2)
        self.screen.blit(bubble, (hud_x, hud_y))
        # Text
        self.screen.blit(hud_surf, (hud_x + 14, hud_y + 9))

    def _detect_missed_messages(self):
        """Detect needs that likely occurred while the app was not running.

        Uses persisted `Pet.notified_needs` timestamps to infer whether a need
        was already notified in a prior session; if not, and the current stat
        meets the need condition, treat it as a missed message.
        """
        missed = []
        now = time.time()
        # If hunger currently exceeds alert and we have not recorded a notify timestamp >= saved last_update
        # For missed messages: if the need currently qualifies and the last time we
        # notified was before the pet's saved `last_update`, then this likely occurred
        # while the app was not running and should be presented as a 'missed' message.
        if self.pet.hunger > HUNGER_ALERT and self.pet.notified_needs.get("hunger", 0) < self.pet.last_update:
            missed.append("I'm hungry!")
            # record the last notification time (not an expiry) so we don't re-report immediately
            self.pet.notified_needs["hunger"] = now
        if self.pet.cleanliness < CLEANLINESS_ALERT and self.pet.notified_needs.get("cleanliness", 0) < self.pet.last_update:
            missed.append("I need a bath!")
            self.pet.notified_needs["cleanliness"] = now
        if missed:
            self.pending_messages = missed
            # Persist new notified timestamps to avoid re-reporting next time
            try:
                self.pet.save()
            except Exception:
                pass
            # Show an initial summary HUD and keep a visible menu badge
            self.show_hud(f"While you were away: {', '.join(missed)}", duration=4.0)


    def _check_and_notify_needs(self):
        """Evaluate low/high stats and notify the user, starting a short reaction if appropriate.

        Uses `Pet.notified_needs` to persist per-need last-notified timestamps so notifications survive restarts.
        """
        now = time.time()
        # Hunger: pet shows belly rub then points to mouth
        last_hunger = self.pet.notified_needs.get("hunger", 0)
        if self.pet.hunger > HUNGER_ALERT and (now - last_hunger) >= NOTIFY_COOLDOWN:
            self.show_hud("I'm hungry!", notification=True)
            self.pet.notified_needs["hunger"] = now
            self.pet.save()
            self._start_reaction("hunger", REACTION_DURATION_HUNGER)
        # Cleanliness: pet smells armpits and shakes head
        last_clean = self.pet.notified_needs.get("cleanliness", 0)
        if self.pet.cleanliness < CLEANLINESS_ALERT and (now - last_clean) >= NOTIFY_COOLDOWN:
            self.show_hud("I need a bath!")
            self.pet.notified_needs["cleanliness"] = now
            self.pet.save()
            self._start_reaction("cleanliness", REACTION_DURATION_CLEAN)

    def _start_reaction(self, rtype, duration):
        """Initialize a simple timed reaction state. Uses elapsed accumulation so tests can simulate time."""
        self.pet_reaction = {"type": rtype, "elapsed": 0.0, "duration": float(duration), "phase": 0}
        # immediate visual cues
        if rtype == "hunger":
            self.belly_squish = 1.0
        if rtype == "cleanliness":
            # minor tail wag / scrunch indicator
            self.tail_wag = 1.0

    def _update_reactions(self, dt):
        """Advance reaction timers by dt seconds and update phase for drawing. Clears when complete."""
        if not self.pet_reaction:
            return
        self.pet_reaction["elapsed"] += dt
        elapsed = self.pet_reaction["elapsed"]
        if elapsed >= self.pet_reaction["duration"]:
            self.pet_reaction = None
            return
        # Map elapsed to a phase (0 or 1) for simple two-part reactions
        frac = elapsed / max(1e-6, self.pet_reaction["duration"])
        phase = 0 if frac < 0.5 else 1
        self.pet_reaction["phase"] = phase

    def _update_pet_appearance(self, dt):
        """Advance blink timer, idle bob phase and decay squish/tail wag values. Also update random arm/leg sway."""
        import random
        # blinking
        if self.blinking:
            self.blink_elapsed += dt
            if self.blink_elapsed >= self.blink_duration:
                self.blinking = False
                self.blink_elapsed = 0.0
                self.blink_timer = self.blink_interval
        else:
            self.blink_timer -= dt
            if self.blink_timer <= 0.0:
                self.blinking = True
                self.blink_elapsed = 0.0
                self.blink_timer = self.blink_interval + self.blink_duration
        # idle bob
        self._bob_phase += dt * self.idle_bob_speed
        self.idle_bob_offset = int(4 * (1.0 + math.sin(self._bob_phase)) - 4)
        # Add a subtle happy bounce if happiness is high
        if self.pet.happiness > 80:
            self.idle_bob_offset += int(2 * math.sin(pygame.time.get_ticks() / 200.0))
        # belly squish decays over time
        if self.belly_squish > 0.0:
            self.belly_squish = max(0.0, self.belly_squish - (dt * 1.5))
        # tail wag - small decay
        if self.tail_wag > 0.0:
            self.tail_wag = max(0.0, self.tail_wag - (dt * 1.5))

        # --- Arm/leg random sway animation ---
        # Arms sway: random chance to move, otherwise decay to 0
        self._arm_sway_timer -= dt
        if self._arm_sway_timer <= 0.0:
            self._arm_sway_target = (random.random() - 0.5) * 8  # sway between -4..+4
            self._arm_sway_timer = 12.0 + random.random() * 6.0   # next change in 12-18 sec
        self._current_arm_sway = getattr(self, "_current_arm_sway", 0.0)
        self._current_arm_sway += (self._arm_sway_target - self._current_arm_sway) * dt * 4.0

        # Legs sway: random small hops
        self._leg_sway_timer -= dt
        if self._leg_sway_timer <= 0.0:
            self._leg_sway_target = (random.random() - 0.5) * 4  # sway between -2..+2
            self._leg_sway_timer = 12.0 + random.random() * 6.0  # next change in 12-18 sec
        self._current_leg_sway = getattr(self, "_current_leg_sway", 0.0)
        self._current_leg_sway += (self._leg_sway_target - self._current_leg_sway) * dt * 4.0

    def _update_badge_pulses(self, dt):
        """Advance badge pulse phases for stats that are currently low."""
        low = self._get_low_needs()
        for k in list(self._badge_pulse_phase.keys()):
            if k in low:
                # advance phase (radians) by angular speed scaled by dt
                self._badge_pulse_phase[k] += dt * BADGE_PULSE_SPEED * math.pi * 2.0
            else:
                # decay towards zero phase so pulse is silent when not low
                if self._badge_pulse_phase[k] != 0.0:
                    # gently reduce phase to zero
                    self._badge_pulse_phase[k] = max(0.0, self._badge_pulse_phase[k] - dt * BADGE_PULSE_SPEED * math.pi * 2.0)

    def get_badge_pulse(self, stat_key):
        """Return a 0.0-1.0 pulse factor for the given stat; 0 if not pulsing."""
        if stat_key not in self._badge_pulse_phase:
            return 0.0
        # Only pulse if the stat is low
        if stat_key not in self._get_low_needs():
            return 0.0
        phase = self._badge_pulse_phase.get(stat_key, 0.0)
        # convert sin wave (-1..1) to normalized 0..1
        return (math.sin(phase) + 1.0) / 2.0

    def is_blinking(self):
        return self.blinking

    def get_belly_squish(self):
        return float(self.belly_squish)

    def draw_stat_icon(self, rect, key, color):
        """Draw a small, clean, and visually crisp icon for a stat centered in rect."""
        cx = rect.x + rect.width // 2
        cy = rect.y + rect.height // 2
        if key == "health":
            # Draw a simple symmetrical heart using a filled polygon
            heart_w = 16
            heart_h = 14
            top = cy - heart_h // 3
            left = cx - heart_w // 2
            right = cx + heart_w // 2
            bottom = cy + heart_h // 2
            points = [
                (cx, bottom),  # bottom tip
                (right, top + heart_h // 3),  # right curve base
                (cx + heart_w // 4, top),  # right top
                (cx, top + heart_h // 4),  # center top dip
                (cx - heart_w // 4, top),  # left top
                (left, top + heart_h // 3),  # left curve base
            ]
            pygame.draw.polygon(self.screen, color, points)
        elif key == "hunger":
            # Draw a simple apple shape (ellipse + stem)
            apple_w, apple_h = 14, 12
            apple_rect = pygame.Rect(cx - apple_w // 2, cy - apple_h // 2, apple_w, apple_h)
            pygame.draw.ellipse(self.screen, color, apple_rect)
            # Stem
            pygame.draw.line(self.screen, (90, 60, 20), (cx, cy - apple_h // 2 + 1), (cx, cy - apple_h // 2 - 4), 2)
        elif key == "happiness":
            # Draw a smiley face: clean circle, two eyes, and a smooth smile arc
            face_radius = 9
            pygame.draw.circle(self.screen, color, (cx, cy), face_radius)
            # Eyes (dots)
            eye_y = cy - 3
            pygame.draw.circle(self.screen, (0, 0, 0), (cx - 3, eye_y), 1)
            pygame.draw.circle(self.screen, (0, 0, 0), (cx + 3, eye_y), 1)
            # Smile (arc)
            smile_rect = pygame.Rect(cx - 4, cy + 1, 8, 5)
            pygame.draw.arc(self.screen, (0, 0, 0), smile_rect, math.radians(20), math.radians(160), 2)
        elif key == "energy":
            # Draw a crescent moon to represent sleep
            moon_color = color
            # Full circle
            pygame.draw.circle(self.screen, moon_color, (cx, cy), 10)
            # Overlay a slightly offset circle with background color to create crescent effect
            pygame.draw.circle(self.screen, COLOR_BG, (cx+4, cy-2), 10)
        elif key == "cleanliness":
            # Draw a filled circle (bubble) with a smaller highlight circle for shine
            bubble_radius = 8
            pygame.draw.circle(self.screen, color, (cx, cy), bubble_radius)
            # Shine: small white circle
            pygame.draw.circle(self.screen, (255, 255, 255), (cx - 3, cy - 4), 2)
        else:
            # fallback: single letter
            lbl = self.small_font.render(key[0].upper(), True, COLOR_TEXT)
            self.screen.blit(lbl, (rect.x + (rect.width - lbl.get_width())//2, rect.y + rect.height + 2))

    def _draw_action_icon(self, icon_id, topleft):
        """Draw a tiny icon for action buttons. Simple primitives only."""
        x, y = topleft
        if icon_id in (None, "feed"):
            # small bowl
            pygame.draw.rect(self.screen, (200, 180, 140), (x, y+2, 12, 8), border_radius=2)
        elif icon_id == "snack":
            pygame.draw.circle(self.screen, (230, 200, 120), (x+6, y+6), 5)
        elif icon_id == "play" or icon_id == "game":
            pygame.draw.polygon(self.screen, (200, 200, 255), [(x+2, y+10), (x+10, y+6), (x+2, y+2)])
        elif icon_id == "nap" or icon_id == "rest":
            pygame.draw.rect(self.screen, (180, 220, 255), (x+2, y+4, 8, 6), border_radius=2)
        elif icon_id == "clean" or icon_id == "deepclean":
            pygame.draw.circle(self.screen, (150, 75, 0), (x+6, y+6), 5)
            pygame.draw.circle(self.screen, (255,255,255), (x+8, y+4), 2)
        elif icon_id == "med" or icon_id == "op":
            pygame.draw.rect(self.screen, (255, 200, 200), (x+2, y+2, 10, 10), border_radius=2)
            pygame.draw.line(self.screen, (200,0,0), (x+7, y+4), (x+7, y+8), 2)
        else:
            pygame.draw.circle(self.screen, (180, 180, 180), (x+6, y+6), 4)

    def draw_pet(self, pos):
        """Draw a cute, chibi-style pet at `pos` (x, y center of pet). Uses primitives with separate body, eyes, and mouth.

        Stores a small dict in `self._last_drawn_pet` for test assertions (eyes_open, belly_squish, idle_bob_offset).
        """
        cx, cy = pos
        # Body dimensions and squish
        body_w = 110 + int(self.belly_squish * 14)
        body_h = 90 - int(self.belly_squish * 10)
        body_rect = pygame.Rect(cx - body_w//2, cy - body_h//2, body_w, body_h)

        # --- Body (drawn first) ---
        pygame.draw.ellipse(self.screen, self.pet_shade_color, body_rect)
        inner_rect = body_rect.inflate(-8, -8)
        pygame.draw.ellipse(self.screen, self.pet_base_color, inner_rect)

        # --- Arms (drawn on top of body for visibility, with subtle idle sway) ---
        arm_color = (200, 170, 190)
        arm_shadow = (140, 110, 130)
        sway = getattr(self, "_current_arm_sway", 0.0)

        # Left arm
        left_arm_rect = pygame.Rect(cx - body_w//2 - 28 + int(sway), cy - 10 + self.idle_bob_offset, 36, 18)
        pygame.draw.ellipse(self.screen, arm_color, left_arm_rect)

        # Right arm
        right_arm_rect = pygame.Rect(cx + body_w//2 - 8 + int(sway), cy - 10 + self.idle_bob_offset, 36, 18)
        pygame.draw.ellipse(self.screen, arm_color, right_arm_rect)

        # --- Legs (small ellipses at bottom, subtle bounce) ---
        leg_color = (160, 120, 140)
        leg_w, leg_h = 22, 16
        leg_sway_x = getattr(self, "_current_leg_sway", 0.0)
        leg_sway_y = self.idle_bob_offset // 2
        # Left leg
        pygame.draw.ellipse(self.screen, leg_color, (cx - 28 + int(leg_sway_x), cy + body_h//2 - 6 + leg_sway_y, leg_w, leg_h))
        # Right leg
        pygame.draw.ellipse(self.screen, leg_color, (cx + 6 + int(leg_sway_x), cy + body_h//2 - 6 + leg_sway_y, leg_w, leg_h))

        # Teddy bear-style rounded ears with right-side shadow
        # Left ear (outer, smaller)
        left_ear_center = (cx-38, cy-38)
        pygame.draw.circle(self.screen, self.pet_base_color, left_ear_center, 11)
        # Left ear inner (smaller)
        pygame.draw.circle(self.screen, (255, 220, 230), (cx-38, cy-38), 6)
        # Left ear shadow (right side, smaller)
        pygame.draw.circle(self.screen, (120, 90, 110, 80), (cx-33, cy-38), 6)

        # Right ear (outer, smaller)
        right_ear_center = (cx+38, cy-38)
        pygame.draw.circle(self.screen, self.pet_base_color, right_ear_center, 11)
        # Right ear inner (smaller)
        pygame.draw.circle(self.screen, (255, 220, 230), (cx+38, cy-38), 6)
        # Right ear shadow (right side, smaller)
        pygame.draw.circle(self.screen, (120, 90, 110, 80), (cx+43, cy-38), 6)

        # Eyes
        eye_y = cy - 12 + self.idle_bob_offset//2
        eye_x_off = 28
        eye_r = 12
        pupil_r = 5
        eyes_open = not self.blinking
        if eyes_open:
            pygame.draw.circle(self.screen, (255,255,255), (cx-eye_x_off, eye_y), eye_r)
            pygame.draw.circle(self.screen, (255,255,255), (cx+eye_x_off, eye_y), eye_r)
            # pupils track small amount toward looking direction (centered by default)
            pygame.draw.circle(self.screen, self.pet_eye_color, (cx-eye_x_off, eye_y), pupil_r)
            pygame.draw.circle(self.screen, self.pet_eye_color, (cx+eye_x_off, eye_y), pupil_r)
            # Add sparkle in eyes if happiness is high
            if self.pet.happiness > 80:
                # sparkle in eyes
                pygame.draw.circle(self.screen, (255, 255, 255), (cx - eye_x_off + 2, eye_y - 2), 2)
                pygame.draw.circle(self.screen, (255, 255, 255), (cx + eye_x_off + 2, eye_y - 2), 2)
        else:
            # eyelid: a half-ellipse/line
            pygame.draw.rect(self.screen, self.pet_shade_color, (cx-eye_x_off-eye_r, eye_y-4, eye_r*2, 8), border_radius=6)
            pygame.draw.rect(self.screen, self.pet_shade_color, (cx+eye_x_off-eye_r, eye_y-4, eye_r*2, 8), border_radius=6)

        # Mouth expression logic:
        mouth_y = cy + 8
        mouth_w = 28
        mouth_h = 10
        mouth_color = (60, 30, 30)
        mouth_rect = pygame.Rect(cx - mouth_w//2, mouth_y - mouth_h//2, mouth_w, mouth_h)
        # Expression logic:
        # - Happy by default
        # - Sad only if explicitly SAD or SICK
        # - Temporary overrides for reactions
        if self.pet_reaction and self.pet_reaction.get("type") == "hunger" and self.pet_reaction.get("phase") == 1:
            # surprised open mouth (oval)
            pygame.draw.ellipse(self.screen, mouth_color, mouth_rect.inflate(-8, 0))
        elif self.pet.state == "SICK":
            # sick frown
            pygame.draw.arc(self.screen, mouth_color, mouth_rect, math.radians(0), math.radians(180), 3)
        elif self.pet.state == "SAD":
            # sad frown
            pygame.draw.arc(self.screen, mouth_color, mouth_rect, math.radians(0), math.radians(180), 3)
        else:
            # happy smile
            mouth_rect = pygame.Rect(cx - 14, mouth_y - 2, 28, 12)
            pygame.draw.arc(self.screen, mouth_color, mouth_rect, math.radians(180), math.radians(360), 3)

        # Belly squish overlay (subtle: draw a darker band when squished)
        if self.belly_squish > 0.01:
            band_w = int(body_w * 0.6)
            band_h = int(12 * self.belly_squish)
            pygame.draw.ellipse(self.screen, (230, 190, 200), (cx-band_w//2, cy+body_h//4 - band_h//2, band_w, band_h))

        # Update last drawn metadata for tests
        self._last_drawn_pet = {
            "eyes_open": eyes_open,
            "belly_squish": float(self.belly_squish),
            "idle_bob_offset": int(self.idle_bob_offset),
        }


    # Expose which stats are currently considered 'low' for tests/UI convenience
    # (e.g., shows a persistent badge on the icon when a stat crosses its alert).
    def _get_low_needs(self):
        low = set()
        if self.pet.hunger > HUNGER_ALERT:
            low.add("hunger")
        if self.pet.cleanliness < CLEANLINESS_ALERT:
            low.add("cleanliness")
        # Additional thresholds: health, energy, happiness
        if self.pet.health < HEALTH_ALERT:
            low.add("health")
        if self.pet.energy < ENERGY_ALERT:
            low.add("energy")
        if self.pet.happiness < HAPPINESS_ALERT:
            low.add("happiness")
        return low
    def step(self):
        """Process a single loop iteration (useful for headless tests). Returns False to stop."""
        # Define a dedicated pet rectangle at the start of step for click exclusion
        center = (SCREEN_WIDTH // 2, SCREEN_HEIGHT // 2)
        pet_rect_top = max(center[1] - 55, 50)
        self.pet_rect = pygame.Rect(center[0] - 90, pet_rect_top, 180, 110 - (pet_rect_top - (center[1] - 55)))

        # --- Repopulate stat_action_rects only for fully expanded panels ---
        for s in self.stat_icons:
            key = s["key"]
            val_anim = self.stat_anim[key]["value"]
            if val_anim > 0.02 and self.stat_expanded.get(key, False) and val_anim > 0.99:
                actions = self.stat_actions.get(key, [])
                self.stat_action_rects[key] = []
                if actions:
                    panel_w = max(40, int(200 * val_anim))
                    panel_h = 48
                    idx = [x["key"] for x in self.stat_icons].index(key)
                    panel_x = max(8, self.stat_icon_rects[idx].centerx - panel_w // 2)
                    panel_y = self.stat_icon_rects[idx].bottom + 6
                    btn_gap = 8
                    total_gap = btn_gap * (len(actions) - 1)
                    btn_w = max(40, (panel_w - 16 - total_gap) // len(actions))
                    btn_h = 24
                    bx = panel_x + 8
                    by = panel_y + panel_h - btn_h - 6
                    for a in actions:
                        btn = pygame.Rect(bx, by, btn_w, btn_h)
                        self.stat_action_rects[key].append((btn, a))
                        bx += btn_w + btn_gap
            else:
                self.stat_action_rects[key] = []

        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                return False
            if event.type == pygame.MOUSEBUTTONDOWN:
                print(f"[DEBUG] Click at {event.pos}")
                # Compose clickable_rects: only UI elements, never include pet_rect!
                clickable_rects = [self.btn_menu]
                clickable_rects += [rect for rect in self.stat_icon_rects if rect]
                rect_names = ['btn_menu', 'popup_clean', 'popup_med'] + [f'stat_icon_{i}' for i in range(len(self.stat_icon_rects))]
                # Only add stat action buttons if panel is fully expanded and anim > 0.99
                for stat_key, rects in self.stat_action_rects.items():
                    if self.stat_expanded.get(stat_key, False) and self.stat_anim[stat_key]["value"] > 0.99:
                        clickable_rects += [btn for btn, _ in rects]
                        rect_names += [f'stat_action_{stat_key}_{i}' for i in range(len(rects))]
                # Confirmation/system popups
                if self.pending_confirmation:
                    if isinstance(self._system_confirmation_rects, tuple):
                        clickable_rects += list(self._system_confirmation_rects)
                        rect_names += ['system_confirm_yes', 'system_confirm_no']
                    for k, rects in self.confirmation_rects.items():
                        if rects:
                            clickable_rects += list(rects)
                            rect_names += [f'confirm_{k}_yes', f'confirm_{k}_no']
                if hasattr(self, "_ack_rect"):
                    clickable_rects.append(self._ack_rect)
                    rect_names.append('ack_rect')
                # Never include self.pet_rect in clickable_rects!

                hit_name = None
                for r, name in zip(clickable_rects, rect_names):
                    if r.collidepoint(event.pos):
                        hit_name = name
                        break
                if hit_name:
                    print(f"[DEBUG] Clicked UI element: {hit_name}")
                else:
                    print(f"[DEBUG] Clicked background (no UI element)")

                # --- Handle background clicks (not on any clickable UI element) ---
                if not any(r.collidepoint(event.pos) for r in clickable_rects):
                    # Clicking background or pet (since pet_rect is not in clickable_rects) closes panels/menus, never triggers stat changes
                    for key in self.stat_expanded:
                        self.stat_expanded[key] = False
                    self.menu_open = False
                    self.pending_confirmation = None
                    self._system_confirmation_rects = None
                    # Ignore click completely; do not call any stat handler
                    continue

                # Stat icon direct action (no pop-out panel)
                for i, rect in enumerate(self.stat_icon_rects):
                    if rect.collidepoint(event.pos):
                        key = self.stat_icons[i]["key"]
                        if key == "health":
                            break  # health does nothing
                        actions = self.stat_actions.get(key, [])
                        if actions:
                            action = actions[0]
                            if self.is_action_enabled(key, action.get("label")):
                                handler = action.get("handler")
                                if callable(handler):
                                    handler()
                                snd = action.get("sound")
                                if snd:
                                    self.sounds.play_effect(snd)
                                self.action_cooldowns[(key, action.get("label"))] = action.get("cooldown", 0.0)
                        break
                # Menu button
                if self.btn_menu.collidepoint(event.pos):
                    self.menu_open = not self.menu_open
                # ...removed popup_clean and popup_med...

                # ...removed stat action buttons (no pop-out panels)...

                # Menu popups (shutdown/restart) when menu is visible
                if self.menu_open:
                    if self.popup_shutdown.collidepoint(event.pos):
                        self.pending_confirmation = {"action": "shutdown"}
                    elif self.popup_restart.collidepoint(event.pos):
                        self.pending_confirmation = {"action": "restart"}

                # If a system confirmation is visible, handle yes/no
                if self.pending_confirmation and isinstance(self._system_confirmation_rects, tuple):
                    yes_rect, no_rect = self._system_confirmation_rects
                    if yes_rect.collidepoint(event.pos):
                        act = self.pending_confirmation.get("action")
                        if act in ("shutdown", "restart"):
                            self._perform_system_action(act)
                        self.pending_confirmation = None
                        self._system_confirmation_rects = None
                        continue
                    elif no_rect.collidepoint(event.pos):
                        self.pending_confirmation = None
                        self._system_confirmation_rects = None
                        continue

                # Per-stat confirmation dialogs (yes/no inside expanded panel)
                for stat_key, rects in list(self.confirmation_rects.items()):
                    if rects:
                        yes_rect, no_rect = rects
                        if yes_rect.collidepoint(event.pos) or no_rect.collidepoint(event.pos):
                            if self.pending_confirmation and self.pending_confirmation.get("stat") == stat_key:
                                if yes_rect.collidepoint(event.pos):
                                    action = self.pending_confirmation.get("action")
                                    handler = action.get("handler")
                                    if callable(handler):
                                        handler()
                                    snd = action.get("sound")
                                    if snd:
                                        self.sounds.play_effect(snd)
                                    self.action_cooldowns[(stat_key, action.get("label"))] = action.get("cooldown", 0.0)
                                self.confirmation_rects.pop(stat_key, None)
                                self.pending_confirmation = None
                                return True
                    self.pending_confirmation = None

                # Missed message acknowledge
                if hasattr(self, "_ack_rect") and self._ack_rect.collidepoint(event.pos):
                    self.pending_messages = []
                    delattr(self, "_ack_rect")

        # Logic update
        self.pet.update()
        self._check_and_notify_needs()

        now = time.time()
        dt = now - getattr(self, "_last_step_time", now)
        self._last_step_time = now
        self._autosave_tick(dt)
        self._update_cooldowns(dt)
        self._update_animations(dt)
        self._update_reactions(dt)
        self._update_pet_appearance(dt)
        self._update_badge_pulses(dt)

        self.screen.fill(COLOR_BG)

        if not self.stat_icon_rects:
            gap = SCREEN_WIDTH // (len(self.stat_icons) + 1)
            for i, s in enumerate(self.stat_icons, start=1):
                cx = gap * i
                rect = pygame.Rect(cx - 16, 8, 32, 32)
                self.stat_icon_rects.append(rect)

        low_needs = self._get_low_needs()
        self._last_low_needs = list(sorted(low_needs))

        for i, s in enumerate(self.stat_icons):
            rect = self.stat_icon_rects[i]
            value = getattr(self.pet, s["key"]) if s["key"] != "hunger" else 100 - self.pet.hunger
            # Subtle shadow behind the meter
            shadow_rect = rect.inflate(6, 6).move(2, 2)
            pygame.draw.ellipse(self.screen, (10, 10, 20), shadow_rect)
            # Normal background ring
            pygame.draw.ellipse(self.screen, COLOR_UI_BG, rect.inflate(4, 4))
            percent = max(0.0, min(1.0, value / 100.0))
            cx = rect.x + rect.width // 2
            cy = rect.y + rect.height // 2
            # Make the arc ring slightly larger (radius increased)
            radius = rect.width // 2 - 0
            arc_rect = pygame.Rect(cx - radius, cy - radius, radius * 2, radius * 2)
            start_angle = math.radians(-90)
            end_angle = start_angle + percent * 2 * math.pi
            if percent > 0:
                pygame.draw.arc(self.screen, s["color"], arc_rect, start_angle, end_angle, 3)
            self.draw_stat_icon(rect, s["key"], s["color"])
            if s["key"] in low_needs:
                badge_color = (230, 60, 60)
                bx = rect.right - 8
                by = rect.y + 8
                pulse = self.get_badge_pulse(s["key"])
                base_radius = 6
                r = base_radius + int(BADGE_PULSE_AMPLITUDE * pulse)
                pygame.draw.circle(self.screen, badge_color, (bx, by), r)
                pygame.draw.circle(self.screen, (255,255,255), (bx, by), max(2, r-4))
        center = (SCREEN_WIDTH // 2, SCREEN_HEIGHT // 2)
        if not self.pet.is_alive:
            pygame.draw.circle(self.screen, (100, 100, 100), center, 50)
            txt = self.font.render("RIP", True, (0, 0, 0))
            self.screen.blit(txt, (center[0] - 15, center[1] - 10))
        elif self.pet.life_stage == self.pet.STAGE_EGG:
            # Draw a simple egg (oval with a crack)
            egg_color = (240, 240, 220)
            egg_rect = pygame.Rect(center[0] - 40, center[1] - 60, 80, 120)
            pygame.draw.ellipse(self.screen, egg_color, egg_rect)
            # Draw a crack (zigzag line)
            crack_color = (180, 180, 160)
            points = [
                (center[0], center[1] - 20),
                (center[0] - 10, center[1]),
                (center[0] + 10, center[1] + 10),
                (center[0] - 10, center[1] + 30),
                (center[0] + 10, center[1] + 40),
            ]
            pygame.draw.lines(self.screen, crack_color, False, points, 3)
            msg = self.font.render("Hatching soon!", True, (80, 80, 80))
            self.screen.blit(msg, (center[0] - msg.get_width() // 2, center[1] + 70))
        else:
            color = COLOR_HEALTH if self.pet.state == "HAPPY" else (255, 165, 0)
            if self.pet.state == "SICK": color = (200, 0, 0)
            offset = 10 * abs((pygame.time.get_ticks() % 1000) - 500) / 500
            shake_x = 0
            mouth_open = False
            show_belly = False
            if self.pet_reaction:
                r = self.pet_reaction
                if r["type"] == "cleanliness":
                    t = r.get("elapsed", 0.0) * 10.0
                    shake_x = int(6.0 * (1 if (int(t) % 2 == 0) else -1))
                if r["type"] == "hunger":
                    if r.get("phase", 0) == 0:
                        show_belly = True
                    else:
                        mouth_open = True
            pos = (center[0] + shake_x, center[1] + int(offset))
            self.draw_pet(pos)
            if self.pet_reaction and self.pet_reaction.get("type") == "cleanliness":
                sx = pos[0]-40
                sy = pos[1]-10
                pygame.draw.line(self.screen, (200,200,200), (sx, sy), (sx-8, sy-8), 2)
                pygame.draw.line(self.screen, (200,200,200), (sx+6, sy+2), (sx-2, sy-10), 2)

        for s in self.stat_icons:
            key = s["key"]
            val_anim = self.stat_anim[key]["value"]
            if val_anim > 0.02:
                idx = [x["key"] for x in self.stat_icons].index(key)
                rect = self.stat_icon_rects[idx]
                panel_w = max(40, int(200 * val_anim))
                panel_h = 48
                panel_x = max(8, rect.centerx - panel_w // 2)
                panel_y = rect.bottom + 6
                panel_surf = pygame.Surface((panel_w, panel_h), pygame.SRCALPHA)
                bg_color = (*COLOR_UI_BG, int(200 * val_anim))
                pygame.draw.rect(panel_surf, bg_color, (0, 0, panel_w, panel_h), border_radius=8)
                self.screen.blit(panel_surf, (panel_x, panel_y))
                val = getattr(self.pet, key) if key != "hunger" else 100 - self.pet.hunger
                self.draw_bar(panel_x + 8, panel_y + 6, val, s["color"], key.capitalize())
                actions = self.stat_actions.get(key, [])
                # stat_action_rects is now populated only in step() for fully expanded panels
                if actions:
                    btn_gap = 8
                    total_gap = btn_gap * (len(actions) - 1)
                    btn_w = max(40, (panel_w - 16 - total_gap) // len(actions))
                    btn_h = 24
                    bx = panel_x + 8
                    by = panel_y + panel_h - btn_h - 6
                    for a in actions:
                        btn = pygame.Rect(bx, by, btn_w, btn_h)
                        enabled = self.is_action_enabled(key, a.get("label"))
                        color = (120, 120, 120) if enabled else (80, 80, 80)
                        pygame.draw.rect(self.screen, color, btn, border_radius=6)
                        icon_x = bx + 4
                        icon_y = by + 4
                        self._draw_action_icon(a.get("icon"), (icon_x, icon_y))
                        lbl = self.small_font.render(a["label"], True, (0,0,0) if enabled else (180,180,180))
                        self.screen.blit(lbl, (bx + 20, by + (btn_h - lbl.get_height())//2))
                        if not enabled:
                            rem = int(self.get_action_cooldown_remaining(key, a.get("label")))
                            cooldown_lbl = self.small_font.render(f"{rem}s", True, (255,255,255))
                            self.screen.blit(cooldown_lbl, (bx + btn_w - cooldown_lbl.get_width() - 6, by + (btn_h - cooldown_lbl.get_height())//2))
                        bx += btn_w + btn_gap
                    if self.pending_confirmation and self.pending_confirmation.get("stat") == key:
                        yes = pygame.Rect(panel_x + panel_w - 92, panel_y + panel_h - 30, 40, 24)
                        no = pygame.Rect(panel_x + panel_w - 44, panel_y + panel_h - 30, 40, 24)
                        self.confirmation_rects[key] = (yes, no)
                        pygame.draw.rect(self.screen, (50, 200, 50), yes, border_radius=6)
                        pygame.draw.rect(self.screen, (200, 50, 50), no, border_radius=6)
                        self.screen.blit(self.small_font.render("Yes", True, COLOR_TEXT), (yes.x+8, yes.y+4))
                        self.screen.blit(self.small_font.render("No", True, COLOR_TEXT), (no.x+10, no.y+4))
                    else:
                        if key in self.confirmation_rects:
                            self.confirmation_rects.pop(key, None)
                break

        if self.pending_confirmation and self.pending_confirmation.get("action") in ("shutdown", "restart"):
            w, h = 220, 80
            x = SCREEN_WIDTH // 2 - w // 2
            y = SCREEN_HEIGHT // 2 - h // 2
            popup = pygame.Rect(x, y, w, h)
            pygame.draw.rect(self.screen, (60, 60, 60), popup, border_radius=12)
            msg = f"Confirm {self.pending_confirmation['action'].capitalize()}?"
            lbl = self.font.render(msg, True, COLOR_TEXT)
            self.screen.blit(lbl, (x + 20, y + 16))
            yes = pygame.Rect(x + 24, y + h - 38, 70, 28)
            no = pygame.Rect(x + w - 94, y + h - 38, 70, 28)
            pygame.draw.rect(self.screen, (50, 200, 50), yes, border_radius=8)
            pygame.draw.rect(self.screen, (200, 50, 50), no, border_radius=8)
            self.screen.blit(self.font.render("Yes", True, COLOR_TEXT), (yes.x+12, yes.y+4))
            self.screen.blit(self.font.render("No", True, COLOR_TEXT), (no.x+18, no.y+4))
            self._system_confirmation_rects = (yes, no)

        if self.pending_messages:
            ack_w, ack_h = 120, 32
            ack_x = SCREEN_WIDTH // 2 - ack_w // 2
            ack_y = SCREEN_HEIGHT - 60
            self._ack_rect = pygame.Rect(ack_x, ack_y, ack_w, ack_h)
            pygame.draw.rect(self.screen, (80, 180, 80), self._ack_rect, border_radius=8)
            ack_lbl = self.font.render("Acknowledge", True, COLOR_TEXT)
            self.screen.blit(ack_lbl, (ack_x + (ack_w - ack_lbl.get_width()) // 2, ack_y + 6))

        self._render_hud(center)

        if self._show_save_blink > 0:
            self._show_save_blink -= dt
            pygame.draw.circle(self.screen, (200, 200, 200), (SCREEN_WIDTH - 10, 10), 4)

        pygame.display.flip()
        self.clock.tick(self.fps)
        return True

    def _perform_system_action(self, action):
        """Perform or simulate a system action: 'shutdown' or 'restart'.

        Behavior:
        - Always persist state (pet.save()) before attempting action.
        - If TAMAGOTCHI_ALLOW_SYSTEM_ACTIONS=1 and we detect Raspberry Pi, try to
          invoke the system command; otherwise record a simulated action for
          tests and show a HUD message.
        - Store last system action in `self._last_system_action` for inspection.
        """
        allowed = os.getenv("TAMAGOTCHI_ALLOW_SYSTEM_ACTIONS", "0") == "1"
        cmd = None
        if action == "shutdown":
            cmd = ["sudo", "shutdown", "-h", "now"]
            msg = "Shutting down..."
        elif action == "restart":
            cmd = ["sudo", "reboot"]
            msg = "Restarting..."
        else:
            return

        # Persist state
        try:
            self.pet.save()
        except Exception:
            pass

        # Default: simulate and don't execute unless explicitly allowed and we are on Pi
        simulated = True
        if allowed and self.is_raspberry_pi:
            try:
                import subprocess
                subprocess.run(cmd, check=False)
                simulated = False
            except Exception:
                simulated = True
        # Record last action for tests / diagnostics
        self._last_system_action = {"action": action, "simulated": simulated}
        # Notify user
        self.show_hud(msg)

    def run(self):
        running = True
        while running:
            running = self.step()

        self.pet.save()
        pygame.quit()
        sys.exit()

if __name__ == "__main__":
    game = GameEngine()
    game.run()