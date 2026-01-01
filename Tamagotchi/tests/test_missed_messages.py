import os
import time
import importlib.util

os.environ.setdefault("SDL_VIDEODRIVER", "dummy")
spec = importlib.util.spec_from_file_location(
    "tamagotchi",
    os.path.join(os.path.dirname(__file__), os.pardir, "tamagotchi.py"),
)
_tmodule = importlib.util.module_from_spec(spec)
spec.loader.exec_module(_tmodule)
tamagotchi = _tmodule


def test_detects_missed_message_on_startup_and_acknowledge():
    # Simulate a pet that was saved earlier and is now very hungry
    eng = tamagotchi.GameEngine()
    # Simulate older saved state where last_update was some time ago
    old_time = time.time() - 3600
    eng.pet.last_update = old_time
    eng.pet.hunger = 95.0
    # Clear any prior notified state so detection counts as missed
    eng.pet.notified_needs = {}
    # Run detection explicitly (normally called during __init__)
    eng._detect_missed_messages()
    assert eng.pending_messages and any("hungry" in m.lower() for m in eng.pending_messages)
    # Simulate opening menu and clicking ack
    eng.menu_open = True
    # Render once to create ack rect
    eng._last_step_time = time.time() - 1.0
    eng.step()
    assert hasattr(eng, '_ack_rect')
    # Click the ack rect
    evt = tamagotchi.pygame.event.Event(tamagotchi.pygame.MOUSEBUTTONDOWN, {"pos": eng._ack_rect.center, "button": 1})
    tamagotchi.pygame.event.post(evt)
    eng.step()
    assert eng.pending_messages == []


def test_detects_cleanliness_missed_message():
    eng = tamagotchi.GameEngine()
    old_time = time.time() - 3600
    eng.pet.last_update = old_time
    eng.pet.cleanliness = 10.0
    eng.pet.notified_needs = {}
    eng._detect_missed_messages()
    assert eng.pending_messages and any("bath" in m.lower() for m in eng.pending_messages)