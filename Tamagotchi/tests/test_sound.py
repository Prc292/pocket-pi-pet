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


def test_sound_manager_records_last_played():
    eng = tamagotchi.GameEngine()
    eng.sounds.play_effect("feed")
    assert eng.sounds.last_played == "feed"


def test_feed_action_triggers_sound():
    eng = tamagotchi.GameEngine()
    eng.pet.hunger = 50.0
    # Open hunger panel and click feed action
    eng.toggle_stat("hunger")
    eng._last_step_time = time.time() - 1.0
    eng.step()
    btn, a = eng.stat_action_rects["hunger"][0]
    evt = tamagotchi.pygame.event.Event(tamagotchi.pygame.MOUSEBUTTONDOWN, {"pos": btn.center, "button": 1})
    tamagotchi.pygame.event.post(evt)
    eng.step()
    assert eng.sounds.last_played == "feed"


def test_sound_manager_check_output_dummy():
    # Force dummy audio driver (headless) to simulate Pi-lite with no audio
    os.environ['SDL_AUDIODRIVER'] = 'dummy'
    eng = tamagotchi.GameEngine()
    ok, info = eng.sounds.check_output()
    # Even if mixer failed to init, check_output should return clean info
    assert isinstance(ok, bool)
    assert 'mixer_init' in info
    del os.environ['SDL_AUDIODRIVER']