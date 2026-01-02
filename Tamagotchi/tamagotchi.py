#!/usr/bin/env python3
import os
import sys
import time
import json
import platform
import pygame
import math

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
    """Handles the biological logic and persistence of the virtual pet.[7, 8]"""
    def __init__(self):
        # Stats Range 0 - 100
        self.hunger = 50.0   # 0 = Full, 100 = Starving
        self.happiness = 100.0
        self.energy = 100.0
        self.health = 100.0
        self.cleanliness = 100.0
        self.is_alive = True
        self.state = "HAPPY" # HAPPY, SAD, SICK, DEAD
        # Life/age tracking for evolution
        self.birth_time = time.time()
        self.life_stage = "BABY"  # BABY, YOUNG, ADULT, ELDER
        self.last_update = time.time()
        # Per-need notified timestamps persisted across sessions so we don't spam notifications
        self.notified_needs = {}
        
    def update(self):
        """Passively decays stats based on real time.[9, 10]"""
        if not self.is_alive:
            self.state = "DEAD"
            return

        now = time.time()
        elapsed = now - self.last_update
        # Limit catch-up to a reasonable maximum and apply time scaling
        elapsed = min(elapsed, MAX_CATCHUP_SECONDS)
        elapsed = elapsed * TIME_SCALE
        self.last_update = now

        # Decay Rates (Units per hour)
        inc_hunger = HUNGER_DECAY_PER_HOUR * (elapsed / 3600)
        self.hunger = min(100.0, self.hunger + inc_hunger)
        self.happiness = max(0.0, self.happiness - (HAPPINESS_DECAY_PER_HOUR * (elapsed / 3600)))
        self.energy = max(0.0, self.energy - (ENERGY_DECAY_PER_HOUR * (elapsed / 3600)))
        # Cleanliness decays over time
        self.cleanliness = max(0.0, self.cleanliness - (CLEANLINESS_DECAY_PER_HOUR * (elapsed / 3600)))

        # Logic for health and state transitions [3]
        if self.hunger > 80 or self.energy < 20:
            self.health = max(0.0, self.health - (HEALTH_DECAY_CONDITIONAL_PER_HOUR * (elapsed / 3600)))
        # Additional health penalty when cleanliness is poor
        if self.cleanliness < 30:
            self.health = max(0.0, self.health - (CLEANLINESS_HEALTH_PENALTY_PER_HOUR * (elapsed / 3600)))

        # Update life stage based on age and care
        age = now - self.birth_time
        prev_stage = self.life_stage
        # Determine candidate stage by age
        if age >= STAGE_ELDER_SECONDS:
            candidate = "ELDER"
        elif age >= STAGE_ADULT_SECONDS:
            candidate = "ADULT"
        elif age >= STAGE_YOUNG_SECONDS:
            candidate = "YOUNG"
        else:
            candidate = "BABY"
        # Evolve only if care (avg of health & happiness) meets threshold when crossing a boundary
        avg_care = (self.health + self.happiness) / 2.0
        if candidate != prev_stage and avg_care >= EVOLUTION_MIN_CARE:
            self.life_stage = candidate
        # Note: if care is insufficient, pet stays in previous stage and may evolve later
        
        if self.health <= 0:
            self.is_alive = False
        elif self.health < 40 or self.hunger > 90:
            self.state = "SICK"
        elif self.happiness < 40:
            self.state = "SAD"
        else:
            self.state = "HAPPY"

    def feed(self):
        if self.is_alive:
            self.hunger = max(0.0, self.hunger - 20.0)
            self.health = min(100.0, self.health + 2.0)
            # Feeding restores some energy as well (gameplay tweak)
            self.energy = min(100.0, self.energy + 10.0)

    def play(self):
        if self.is_alive and self.energy > 10:
            self.happiness = min(100.0, self.happiness + 25.0)
            self.energy = max(0.0, self.energy - 15.0)

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
        self.happiness = min(100.0, self.happiness + 5.0)
    def clean(self):
        """Cleans the pet: restores cleanliness, costs a bit of energy, and increases happiness."""
        if self.is_alive:
            self.cleanliness = min(100.0, self.cleanliness + 30.0)
            self.happiness = min(100.0, self.happiness + 5.0)
            self.energy = max(0.0, self.energy - 5.0)

    def save(self):
        """Persists state to JSON for cross-session survival.[1, 2, 11]

        Uses a simple atomic replace pattern to avoid truncated saves.
        """
        data = {
            "hunger": float(self.hunger),
            "happiness": float(self.happiness),
            "energy": float(self.energy),
            "health": float(self.health),
            "cleanliness": float(self.cleanliness),
            "is_alive": bool(self.is_alive),
            "last_update": time.time(),
            "notified_needs": self.notified_needs
        }
        # Write to a temp file then atomically replace the save file
        tmp = SAVE_FILE + ".tmp"
        with open(tmp, 'w') as f:
            json.dump(data, f)
        os.replace(tmp, SAVE_FILE)

    def load(self):
        """Loads data and handles 'catch-up' logic for elapsed time.[1]

        Defensive: handles missing or malformed files and missing keys.
        """
        defaults = {
            "hunger": 50.0,
            "happiness": 100.0,
            "energy": 100.0,
            "health": 100.0,
            "cleanliness": 100.0,
            "is_alive": True,
            "last_update": time.time()
        }

        if not os.path.exists(SAVE_FILE):
            # No save present; use defaults
            self.hunger = defaults["hunger"]
            self.happiness = defaults["happiness"]
            self.energy = defaults["energy"]
            self.health = defaults["health"]
            self.is_alive = defaults["is_alive"]
            self.last_update = defaults["last_update"]
            return

        try:
            with open(SAVE_FILE, 'r') as f:
                data = json.load(f)
        except (json.JSONDecodeError, OSError) as e:
            print(f"Warning: failed to read save file '{SAVE_FILE}': {e}")
            # fallback to defaults
            data = defaults

        # Validate and apply keys, falling back to defaults when missing or invalid
        def get_num(key):
            v = data.get(key, defaults[key])
            try:
                return float(v)
            except Exception:
                return defaults[key]

        self.hunger = get_num("hunger")
        self.happiness = get_num("happiness")
        self.energy = get_num("energy")
        self.health = get_num("health")
        self.cleanliness = get_num("cleanliness")
        self.is_alive = bool(data.get("is_alive", defaults["is_alive"]))
        self.last_update = float(data.get("last_update", defaults["last_update"]))
        # If saved last_update is in the future (clock skew), clamp to now so
        # subsequent 'missed' detection and catch-up math are reasonable.
        now = time.time()
        if self.last_update > now:
            self.last_update = now
        # Persisted per-need last-notified timestamps so we don't re-notify after restart
        self.notified_needs = data.get("notified_needs", {}) if isinstance(data.get("notified_needs", {}), dict) else {}
        # Backwards-compat: older saves stored the *expiry* timestamp (now + cooldown).
        for k, v in list(self.notified_needs.items()):
            try:
                fv = float(v)
            except Exception:
                fv = 0.0
            if fv > now:
                # If a stored timestamp is somehow in the future (corrupt or from the
                # previous expiry-based scheme), clamp it to 0 so we can re-evaluate
                # needs naturally in this session.
                self.notified_needs[k] = 0.0
            else:
                self.notified_needs[k] = fv
        # Trigger immediate update to account for elapsed real time
        try:
            self.update()
        except Exception as e:
            # Prevent corrupt save data from crashing the app
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
        
        # Menu button (top-right) toggles a popup (kept empty for now)
        self.btn_menu = pygame.Rect(430, 10, 40, 28)
        self.menu_open = False
        # Popup button rects (hidden until menu_open)
        self.popup_clean = pygame.Rect(140, 220, 100, 50)
        self.popup_med = pygame.Rect(260, 220, 100, 50)
        # System control buttons in menu (shutdown / restart)
        self.popup_shutdown = pygame.Rect(140, 280, 100, 40)
        self.popup_restart = pygame.Rect(260, 280, 100, 40)
        # HUD message (transient, centered above pet)
        self.hud_text = None
        self.hud_expiry = 0.0
        # Per-stat actions mapping: label, handler, sound key, icon id (simple), confirm flag and cooldown seconds
        # Use helper methods (defined below) for differentiated effects
        self.stat_actions = {
            "hunger": [
                {"label": "Snack", "handler": self._feed_small, "sound": "feed", "icon": "snack", "confirm": False, "cooldown": 2.0},
                {"label": "Feed", "handler": self._feed_big, "sound": "feed", "icon": "feed", "confirm": False, "cooldown": 6.0},
            ],
            "happiness": [
                {"label": "Play", "handler": self._play_small, "sound": "play", "icon": "play", "confirm": False, "cooldown": 2.0},
                {"label": "Game", "handler": self._play_big, "sound": "play", "icon": "game", "confirm": False, "cooldown": 6.0},
            ],
            "energy": [
                {"label": "Nap", "handler": self._nap_short, "sound": "nap", "icon": "nap", "confirm": False, "cooldown": 10.0},
                {"label": "Rest", "handler": self._nap_long, "sound": "nap", "icon": "rest", "confirm": False, "cooldown": 30.0},
            ],
            "cleanliness": [
                {"label": "Clean", "handler": self.pet.clean, "sound": "clean", "icon": "clean", "confirm": False, "cooldown": 15.0},
                {"label": "Deep Clean", "handler": self._deep_clean, "sound": "clean", "icon": "deepclean", "confirm": True, "cooldown": 20.0},
            ],
            "health": [
                {"label": "Med", "handler": self.pet.give_medicine, "sound": "heal", "icon": "med", "confirm": False, "cooldown": 60.0},
                {"label": "Operation", "handler": self._operation, "sound": "heal", "icon": "op", "confirm": True, "cooldown": 120.0},
            ],
        }
        # Store action rects per stat for input detection and tests
        self.stat_action_rects = {k: [] for k in self.stat_actions}
        # Confirmation state when an expensive action requires confirmation
        self.pending_confirmation = None
        self.confirmation_rects = {}
        # Track per-action cooldowns: keys are (stat_key, action_label) -> seconds remaining
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


    def draw_bar(self, x, y, value, color, label):
        """Renders stat progress bars.[1, 14]"""
        pygame.draw.rect(self.screen, COLOR_UI_BG, (x, y, 100, 15))
        # clamp and convert to integer pixel width (expected 0-100)
        width = max(0, min(100, int(value)))
        pygame.draw.rect(self.screen, color, (x, y, width, 15))
        lbl = self.font.render(label, True, COLOR_TEXT)
        self.screen.blit(lbl, (x, y - 18))

    def show_hud(self, text, duration=1.5):
        """Show a short-lived HUD message (centered).

        Stores start time and duration so rendering can fade the HUD out smoothly.
        """
        self.hud_text = text
        self.hud_start = time.time()
        self.hud_duration = duration
        self.hud_expiry = self.hud_start + duration

    def toggle_stat(self, key):
        """Toggle a top stat's expanded state (testable helper)."""
        if key not in self.stat_anim:
            return
        current_target = self.stat_anim[key]["target"]
        # collapse others, then toggle this key
        for k in self.stat_anim:
            self.stat_anim[k]["target"] = 0.0
        self.stat_anim[key]["target"] = 0.0 if current_target > 0.5 else 1.0

    # Helper gameplay actions (small/big variants and expensive actions)
    def _feed_small(self):
        if not self.pet.is_alive:
            return
        self.pet.hunger = max(0.0, self.pet.hunger - 10.0)
        self.pet.health = min(100.0, self.pet.health + 1.0)

    def _feed_big(self):
        if not self.pet.is_alive:
            return
        self.pet.hunger = max(0.0, self.pet.hunger - 30.0)
        self.pet.energy = min(100.0, self.pet.energy + 10.0)
        self.pet.health = min(100.0, self.pet.health + 2.0)

    def _play_small(self):
        if not self.pet.is_alive or self.pet.energy <= 5:
            return
        self.pet.happiness = min(100.0, self.pet.happiness + 10.0)
        self.pet.energy = max(0.0, self.pet.energy - 5.0)

    def _play_big(self):
        if not self.pet.is_alive or self.pet.energy <= 10:
            return
        self.pet.happiness = min(100.0, self.pet.happiness + 25.0)
        self.pet.energy = max(0.0, self.pet.energy - 20.0)

    def _nap_short(self):
        if not self.pet.is_alive:
            return
        self.pet.energy = min(100.0, self.pet.energy + 20.0)

    def _nap_long(self):
        if not self.pet.is_alive:
            return
        self.pet.energy = min(100.0, self.pet.energy + 40.0)
        self.pet.happiness = min(100.0, self.pet.happiness + 2.0)

    def _deep_clean(self):
        if not self.pet.is_alive:
            return
        self.pet.cleanliness = min(100.0, self.pet.cleanliness + 70.0)
        self.pet.energy = max(0.0, self.pet.energy - 10.0)

    def _operation(self):
        """Expensive operation: large health boost but costs happiness."""
        if not self.pet.is_alive:
            return
        self.pet.health = min(100.0, self.pet.health + 40.0)
        self.pet.happiness = max(0.0, self.pet.happiness - 15.0)

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

    def _update_cooldowns(self, dt):
        """Advance cooldown timers and clear expired entries."""
        to_clear = []
        for k, v in list(self.action_cooldowns.items()):
            v -= dt
            if v <= 0.0:
                to_clear.append(k)
            else:
                self.action_cooldowns[k] = v
        for k in to_clear:
            del self.action_cooldowns[k]

    def is_action_enabled(self, stat, label):
        """Return True if the named action for stat is currently usable (not cooling)."""
        return self.action_cooldowns.get((stat, label), 0.0) <= 0.0

    def get_action_cooldown_remaining(self, stat, label):
        """Return remaining cooldown seconds (0.0 if none)."""
        return max(0.0, float(self.action_cooldowns.get((stat, label), 0.0)))

    def _render_hud(self, center):
        """Render the transient HUD message with fade-out."""
        if not self.hud_text:
            return
        now = time.time()
        if now < self.hud_expiry:
            age = now - self.hud_start
            frac = max(0.0, min(1.0, age / self.hud_duration))
            alpha = int(255 * (1.0 - frac))
            hud_surf = self.font.render(self.hud_text, True, (0, 0, 0))
            hud_w = hud_surf.get_width() + 20
            hud_h = hud_surf.get_height() + 10
            hud_x = SCREEN_WIDTH // 2 - hud_w // 2
            hud_y = center[1] - 90
            # Background with alpha
            bg = pygame.Surface((hud_w, hud_h), pygame.SRCALPHA)
            bg.fill((200, 200, 200, int(200 * (1.0 - frac))))
            self.screen.blit(bg, (hud_x, hud_y))
            # Apply alpha to text surface
            text_s = hud_surf.copy()
            text_s.set_alpha(alpha)
            self.screen.blit(text_s, (hud_x + 10, hud_y + 5))
        else:
            # clear expired hud
            self.hud_text = None

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
            self.show_hud("I'm hungry!")
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
        """Advance blink timer, idle bob phase and decay squish/tail wag values."""
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
        # belly squish decays over time
        if self.belly_squish > 0.0:
            self.belly_squish = max(0.0, self.belly_squish - (dt * 1.5))
        # tail wag - small decay
        if self.tail_wag > 0.0:
            self.tail_wag = max(0.0, self.tail_wag - (dt * 1.5))

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
        """Draw a small representative icon for a stat in the given rect."""
        cx = rect.x + rect.width // 2
        cy = rect.y + rect.height // 2
        if key == "health":
            # simple filled circle for health
            pygame.draw.circle(self.screen, color, (cx, cy), 8)
        elif key == "hunger":
            # small triangle (plate/fork abstract)
            points = [(cx, rect.y + 6), (rect.x + 6, rect.bottom - 6), (rect.right - 6, rect.bottom - 6)]
            pygame.draw.polygon(self.screen, color, points)
        elif key == "happiness":
            # two triangles overlapping to give a star-like shape
            t1 = [(cx, rect.y + 6), (rect.x + 6, rect.bottom - 6), (rect.right - 6, rect.bottom - 6)]
            t2 = [(rect.x + 6, rect.y + 6), (rect.right - 6, rect.y + 6), (cx, rect.bottom - 6)]
            pygame.draw.polygon(self.screen, color, t1)
            pygame.draw.polygon(self.screen, color, t2)
        elif key == "energy":
            # lightning bolt (zig-zag)
            pts = [(rect.x + 8, rect.y + 6), (rect.x + rect.width - 8, cy), (rect.x + 12, cy), (rect.right - 8, rect.bottom - 6)]
            pygame.draw.polygon(self.screen, color, pts)
        elif key == "cleanliness":
            # ring/bubble
            pygame.draw.circle(self.screen, color, (cx, cy), 7)
            inner = pygame.Surface((14, 14), pygame.SRCALPHA)
            inner.fill((0, 0, 0, 0))
            pygame.draw.circle(inner, (255, 255, 255, 180), (7, 7), 4)
            self.screen.blit(inner, (cx - 7, cy - 7))
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
        # Soft shading: draw two overlapping ellipses
        pygame.draw.ellipse(self.screen, self.pet_shade_color, body_rect)
        inner_rect = body_rect.inflate(-8, -8)
        pygame.draw.ellipse(self.screen, self.pet_base_color, inner_rect)

        # Ears / tuft
        pygame.draw.polygon(self.screen, self.pet_base_color, [(cx-30, cy-40), (cx-22, cy-62), (cx-14, cy-38)])
        pygame.draw.polygon(self.screen, self.pet_base_color, [(cx+30, cy-40), (cx+22, cy-62), (cx+14, cy-38)])
        pygame.draw.circle(self.screen, self.pet_shade_color, (cx, cy-56), 6)

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
        else:
            # eyelid: a half-ellipse/line
            pygame.draw.rect(self.screen, self.pet_shade_color, (cx-eye_x_off-eye_r, eye_y-4, eye_r*2, 8), border_radius=6)
            pygame.draw.rect(self.screen, self.pet_shade_color, (cx+eye_x_off-eye_r, eye_y-4, eye_r*2, 8), border_radius=6)

        # Mouth (vary by pet.state and reactions)
        mouth_y = cy + 8
        mouth_w = 28
        mouth_h = 10
        mouth_color = (60, 30, 30)
        mouth_rect = pygame.Rect(cx - mouth_w//2, mouth_y - mouth_h//2, mouth_w, mouth_h)
        # expression overrides
        if self.pet_reaction and self.pet_reaction.get("type") == "hunger" and self.pet_reaction.get("phase") == 1:
            # surprised open mouth (oval)
            pygame.draw.ellipse(self.screen, mouth_color, mouth_rect.inflate(-8, 0))
        elif self.pet.state == "SICK":
            # small frown
            pygame.draw.arc(self.screen, mouth_color, mouth_rect, math.pi*0.25, math.pi*0.75, 3)
        elif self.pet.state == "SAD":
            # downturned slight arc
            pygame.draw.arc(self.screen, mouth_color, mouth_rect, math.pi*0.25, math.pi*0.75, 2)
        else:
            # smile as small curve (filled rect with rounded corners)
            pygame.draw.rect(self.screen, mouth_color, (cx-10, mouth_y, 20, 6), border_radius=4)

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
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                return False
            if event.type == pygame.MOUSEBUTTONDOWN:
                # First, check for action clicks inside expanded stat panels
                handled = False
                for key, expanded in list(self.stat_expanded.items()):
                    if not expanded:
                        continue
                    idx = [x["key"] for x in self.stat_icons].index(key)
                    rect = self.stat_icon_rects[idx]
                    panel_w = 200
                    panel_h = 48
                    panel_x = max(8, rect.centerx - panel_w // 2)
                    panel_y = rect.bottom + 6
                    # If there's a pending confirmation for this stat, check yes/no first
                    if self.pending_confirmation and self.pending_confirmation.get("stat") == key:
                        yes = pygame.Rect(panel_x + panel_w - 92, panel_y + panel_h - 30, 40, 24)
                        no = pygame.Rect(panel_x + panel_w - 44, panel_y + panel_h - 30, 40, 24)
                        self.confirmation_rects[key] = (yes, no)
                        if yes.collidepoint(event.pos):
                            # confirm and execute
                            a = self.pending_confirmation["action"]
                            h = a.get("handler")
                            if h:
                                h()
                                self.show_hud(a.get("label") + "!")
                                snd = a.get("sound")
                                if snd:
                                    self.sounds.play_effect(snd)
                                # start cooldown if configured
                                cd = a.get("cooldown")
                                if cd:
                                    self.action_cooldowns[(key, a.get("label"))] = float(cd)
                            self.pending_confirmation = None
                            handled = True
                            break
                        if no.collidepoint(event.pos):
                            # cancel confirmation
                            self.pending_confirmation = None
                            self.show_hud("Cancelled")
                            handled = True
                            break
                    # Build and store action button rects for this panel
                    actions = self.stat_actions.get(key, [])
                    self.stat_action_rects[key] = []
                    if actions:
                        btn_gap = 8
                        total_gap = btn_gap * (len(actions) - 1)
                        btn_w = max(40, (panel_w - 16 - total_gap) // len(actions))
                        btn_h = 24
                        bx = panel_x + 8
                        by = panel_y + panel_h - btn_h - 6
                        for a in actions:
                            btn = pygame.Rect(bx, by, btn_w, btn_h)
                            self.stat_action_rects[key].append((btn, a))
                            if btn.collidepoint(event.pos):
                                # Respect cooldowns: if action is cooling, do not allow execution
                                if not self.is_action_enabled(key, a.get("label")):
                                    self.show_hud("Cooling...")
                                    handled = True
                                    break
                                # If action requires confirmation, set pending state; otherwise execute
                                if a.get("confirm"):
                                    self.pending_confirmation = {"stat": key, "action": a}
                                    self.show_hud("Confirm " + a.get("label") + "?")
                                else:
                                    h = a.get("handler")
                                    if h:
                                        h()
                                        self.show_hud(a.get("label") + "!")
                                        snd = a.get("sound")
                                        if snd:
                                            self.sounds.play_effect(snd)
                                        # start cooldown if configured
                                        cd = a.get("cooldown")
                                        if cd:
                                            self.action_cooldowns[(key, a.get("label"))] = float(cd)
                                handled = True
                                break
                            bx += btn_w + btn_gap
                        if handled:
                            break

                if handled:
                    continue

                # Next, check for stat icon clicks (toggle expanded)
                clicked_stat = None
                for i, s in enumerate(self.stat_icons):
                    rect = self.stat_icon_rects[i]
                    if rect.collidepoint(event.pos):
                        clicked_stat = s["key"]
                        break
                if clicked_stat is not None:
                    current_target = self.stat_anim[clicked_stat]["target"]
                    new_target = 0.0 if current_target > 0.5 else 1.0
                    for k in self.stat_anim:
                        self.stat_anim[k]["target"] = 0.0
                    self.stat_anim[clicked_stat]["target"] = new_target
                    for k in self.stat_expanded:
                        self.stat_expanded[k] = False
                    self.stat_expanded[clicked_stat] = (new_target > 0.5)
                    continue

                # Menu handling
                if self.btn_menu.collidepoint(event.pos):
                    self.menu_open = not self.menu_open
                elif self.menu_open and hasattr(self, '_ack_rect') and self._ack_rect.collidepoint(event.pos):
                    # Acknowledge pending messages
                    self.pending_messages = []
                    # Mark corresponding notified_needs to now so they aren't re-reported
                    t = time.time()
                    if self.pet.hunger > HUNGER_ALERT:
                        self.pet.notified_needs['hunger'] = t
                    if self.pet.cleanliness < CLEANLINESS_ALERT:
                        self.pet.notified_needs['cleanliness'] = t
                    try:
                        self.pet.save()
                    except Exception:
                        pass
                    self.show_hud("Messages acknowledged")
                elif self.menu_open and self.popup_clean.collidepoint(event.pos):
                    old = self.pet.cleanliness
                    if self.pet.is_alive:
                        self.pet.clean()
                        if self.pet.cleanliness > old:
                            self.show_hud("Cleaned!")
                            self.sounds.play_effect("clean")
                elif self.menu_open and self.popup_med.collidepoint(event.pos):
                    old = self.pet.health
                    if self.pet.is_alive:
                        self.pet.give_medicine()
                        if self.pet.health > old:
                            self.show_hud("Healed!")
                            self.sounds.play_effect("heal")
                elif self.menu_open and self.popup_shutdown.collidepoint(event.pos):
                    # Save state and perform (or simulate) a shutdown
                    try:
                        self.pet.save()
                    except Exception:
                        pass
                    self._perform_system_action("shutdown")
                elif self.menu_open and self.popup_restart.collidepoint(event.pos):
                    try:
                        self.pet.save()
                    except Exception:
                        pass
                    self._perform_system_action("restart")
                elif self.menu_open and hasattr(self, 'btn_quit') and self.btn_quit.collidepoint(event.pos):
                    return False

        # Logic update
        # If a confirmation dialog is pending, pause pet state updates so a user's
        # decision does not get blurred by small time-based state decay during the
        # confirmation interval (keeps tests deterministic and UX consistent).
        if not self.pending_confirmation:
            self.pet.update()
            # Check needs and send notifications + start simple reactions
            self._check_and_notify_needs()
        else:
            # still allow HUD/visuals to show the confirmation; do not advance pet state
            pass

        # Update loop timing
        now = time.time()
        dt = now - getattr(self, "_last_step_time", now)
        self._last_step_time = now
        # Update animations and other time-dependent helpers
        self._update_animations(dt)
        # Update action cooldown timers
        self._update_cooldowns(dt)
        # Update pet reaction state
        self._update_reactions(dt)
        # Pet appearance updates (blinking, bobbing, squish decay)
        self._update_pet_appearance(dt)
        # Update badge pulse animations
        self._update_badge_pulses(dt)

        # Rendering (top horizontal meters removed — icons now represent stats)
        self.screen.fill(COLOR_BG)
        # Life-stage label intentionally hidden; UI focuses on icons and pet.

        # Draw compact stat icons along the top (compute rects if needed)
        if not self.stat_icon_rects:
            gap = SCREEN_WIDTH // (len(self.stat_icons) + 1)
            for i, s in enumerate(self.stat_icons, start=1):
                cx = gap * i
                rect = pygame.Rect(cx - 16, 8, 32, 32)  # small circular icon area
                self.stat_icon_rects.append(rect)

        # Compute currently 'low' needs for persistent icon badges
        low_needs = self._get_low_needs()
        # Expose for tests and UI introspection
        self._last_low_needs = list(sorted(low_needs))

        for i, s in enumerate(self.stat_icons):
            rect = self.stat_icon_rects[i]
            value = getattr(self.pet, s["key"]) if s["key"] != "hunger" else 100 - self.pet.hunger
            # Draw icon background
            pygame.draw.ellipse(self.screen, COLOR_UI_BG, rect)
            # Small filled arc/rect to indicate rough value (simple vertical fill)
            fill_h = max(2, int((value / 100.0) * rect.height))
            fill_rect = pygame.Rect(rect.x + 4, rect.y + rect.height - fill_h, rect.width - 8, fill_h)
            pygame.draw.rect(self.screen, s["color"], fill_rect)
            # Draw a small icon representing the stat
            self.draw_stat_icon(rect, s["key"], s["color"])
            # If this stat is currently low, draw a persistent red badge in the corner
            if s["key"] in low_needs:
                badge_color = (230, 60, 60)
                bx = rect.right - 8
                by = rect.y + 8
                # Pulse factor 0..1
                pulse = self.get_badge_pulse(s["key"])
                base_radius = 6
                r = base_radius + int(BADGE_PULSE_AMPLITUDE * pulse)
                pygame.draw.circle(self.screen, badge_color, (bx, by), r)
                # small white dot to make it more readable (slightly smaller)
                pygame.draw.circle(self.screen, (255,255,255), (bx, by), max(2, r-4))
        center = (SCREEN_WIDTH // 2, SCREEN_HEIGHT // 2)
        if not self.pet.is_alive:
            pygame.draw.circle(self.screen, (100, 100, 100), center, 50)
            txt = self.font.render("RIP", True, (0, 0, 0))
            self.screen.blit(txt, (center[0] - 15, center[1] - 10))
        else:
            color = COLOR_HEALTH if self.pet.state == "HAPPY" else (255, 165, 0)
            if self.pet.state == "SICK": color = (200, 0, 0)
            offset = 10 * abs((pygame.time.get_ticks() % 1000) - 500) / 500
            # Apply reaction-based drawing changes (shake, belly rub, mouth point)
            shake_x = 0
            mouth_open = False
            show_belly = False
            if self.pet_reaction:
                r = self.pet_reaction
                # cleanliness -> head shake
                if r["type"] == "cleanliness":
                    # head shake: small horizontal oscillation using accumulated elapsed time
                    t = r.get("elapsed", 0.0) * 10.0
                    shake_x = int(6.0 * (1 if (int(t) % 2 == 0) else -1))
                # hunger -> belly rub then mouth point
                if r["type"] == "hunger":
                    if r.get("phase", 0) == 0:
                        show_belly = True
                    else:
                        mouth_open = True
            pos = (center[0] + shake_x, center[1] + int(offset))
            # Pet is the visual focus - use cute chibi drawing
            self.draw_pet(pos)
            # Cleanliness smell lines remain for clarity
            if self.pet_reaction and self.pet_reaction.get("type") == "cleanliness":
                sx = pos[0]-40
                sy = pos[1]-10
                pygame.draw.line(self.screen, (200,200,200), (sx, sy), (sx-8, sy-8), 2)
                pygame.draw.line(self.screen, (200,200,200), (sx+6, sy+2), (sx-2, sy-10), 2)

        if self.menu_open:
            # Menu background (taller to accomodate system buttons)
            menu_rect = pygame.Rect(120, 210, 260, 140)
            pygame.draw.rect(self.screen, COLOR_UI_BG, menu_rect, border_radius=8)
            # If there are pending messages, show them and an Acknowledge button
            if self.pending_messages:
                txt_y = menu_rect.y + 8
                for msg in self.pending_messages[:3]:
                    self.screen.blit(self.small_font.render(msg, True, COLOR_TEXT), (menu_rect.x + 8, txt_y))
                    txt_y += 18
                ack = pygame.Rect(menu_rect.x + menu_rect.width - 110, menu_rect.y + menu_rect.height - 50, 100, 24)
                pygame.draw.rect(self.screen, (50,150,200), ack, border_radius=6)
                self.screen.blit(self.small_font.render("Acknowledge", True, COLOR_TEXT), (ack.x+6, ack.y+4))
                # store ack rect for click handling
                self._ack_rect = ack
            else:
                self.screen.blit(self.small_font.render("No messages", True, COLOR_TEXT), (120+8, 210+8))
            # Draw popup quick-actions
            pygame.draw.rect(self.screen, (80,80,80), self.popup_clean, border_radius=6)
            self.screen.blit(self.small_font.render("Clean", True, COLOR_TEXT), (self.popup_clean.x + 10, self.popup_clean.y + 12))
            pygame.draw.rect(self.screen, (80,80,80), self.popup_med, border_radius=6)
            self.screen.blit(self.small_font.render("Med", True, COLOR_TEXT), (self.popup_med.x + 20, self.popup_med.y + 12))
            # System buttons
            pygame.draw.rect(self.screen, (200, 80, 60), self.popup_shutdown, border_radius=6)
            self.screen.blit(self.small_font.render("Shutdown", True, COLOR_TEXT), (self.popup_shutdown.x + 6, self.popup_shutdown.y + 10))
            pygame.draw.rect(self.screen, (200, 120, 60), self.popup_restart, border_radius=6)
            self.screen.blit(self.small_font.render("Restart", True, COLOR_TEXT), (self.popup_restart.x + 10, self.popup_restart.y + 10))

        # Draw expanded stat if any (animated)
        for s in self.stat_icons:
            key = s["key"]
            val_anim = self.stat_anim[key]["value"]
            if val_anim > 0.02:
                # Draw a small animated panel beneath the icon
                idx = [x["key"] for x in self.stat_icons].index(key)
                rect = self.stat_icon_rects[idx]
                panel_w = max(40, int(200 * val_anim))
                panel_h = 48
                panel_x = max(8, rect.centerx - panel_w // 2)
                panel_y = rect.bottom + 6
                # Use an alpha blended surface so the panel fades in/out with animation
                panel_surf = pygame.Surface((panel_w, panel_h), pygame.SRCALPHA)
                bg_color = (*COLOR_UI_BG, int(200 * val_anim))
                pygame.draw.rect(panel_surf, bg_color, (0, 0, panel_w, panel_h), border_radius=8)
                self.screen.blit(panel_surf, (panel_x, panel_y))
                # Draw labelled bar inside
                val = getattr(self.pet, key) if key != "hunger" else 100 - self.pet.hunger
                self.draw_bar(panel_x + 8, panel_y + 6, val, s["color"], key.capitalize())
                # Draw action buttons for this stat, if any
                actions = self.stat_actions.get(key, [])
                self.stat_action_rects[key] = []
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
                        # Draw a small icon on the left side of the button
                        icon_x = bx + 4
                        icon_y = by + 4
                        self._draw_action_icon(a.get("icon"), (icon_x, icon_y))
                        lbl = self.small_font.render(a["label"], True, (0,0,0) if enabled else (180,180,180))
                        self.screen.blit(lbl, (bx + 20, by + (btn_h - lbl.get_height())//2))
                        # If cooling, draw remaining seconds on the right
                        if not enabled:
                            rem = int(self.get_action_cooldown_remaining(key, a.get("label")))
                            cooldown_lbl = self.small_font.render(f"{rem}s", True, (255,255,255))
                            self.screen.blit(cooldown_lbl, (bx + btn_w - cooldown_lbl.get_width() - 6, by + (btn_h - cooldown_lbl.get_height())//2))
                        self.stat_action_rects[key].append((btn, a))
                        bx += btn_w + btn_gap
                    # If a confirmation is pending, show yes/no buttons
                    if self.pending_confirmation and self.pending_confirmation.get("stat") == key:
                        yes = pygame.Rect(panel_x + panel_w - 92, panel_y + panel_h - 30, 40, 24)
                        no = pygame.Rect(panel_x + panel_w - 44, panel_y + panel_h - 30, 40, 24)
                        self.confirmation_rects[key] = (yes, no)
                        pygame.draw.rect(self.screen, (50, 200, 50), yes, border_radius=6)
                        pygame.draw.rect(self.screen, (200, 50, 50), no, border_radius=6)
                        self.screen.blit(self.small_font.render("Yes", True, COLOR_TEXT), (yes.x+8, yes.y+4))
                        self.screen.blit(self.small_font.render("No", True, COLOR_TEXT), (no.x+10, no.y+4))
                # Expand only one at a time
                break

        # HUD rendering (centered above pet)
        self._render_hud(center)

        # Bottom buttons removed — stat-specific actions are in expanded panels
        pygame.draw.rect(self.screen, (100, 100, 100), self.btn_menu, border_radius=6)
        self.screen.blit(self.font.render("MENU", True, COLOR_TEXT), (self.btn_menu.x + 2, self.btn_menu.y + 5))

        # Optionally draw a small quit area (useful for desktop debugging)
        self.btn_quit = pygame.Rect(8, SCREEN_HEIGHT - 36, 80, 28)
        pygame.draw.rect(self.screen, (120,80,80), self.btn_quit, border_radius=6)
        self.screen.blit(self.small_font.render("Quit", True, COLOR_TEXT), (self.btn_quit.x + 8, self.btn_quit.y + 6))

        pygame.display.flip()
        # Use instance FPS (may be reduced on Pi for compatibility)
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