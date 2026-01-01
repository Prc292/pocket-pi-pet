import os
import importlib.util

os.environ.setdefault("SDL_VIDEODRIVER", "dummy")
spec = importlib.util.spec_from_file_location(
    "tamagotchi",
    os.path.join(os.path.dirname(__file__), os.pardir, "tamagotchi.py"),
)
_tmodule = importlib.util.module_from_spec(spec)
spec.loader.exec_module(_tmodule)
tamagotchi = _tmodule


def test_force_pi_env_flag():
    os.environ["TAMAGOTCHI_FORCE_PI"] = "1"
    assert tamagotchi.is_raspberry_pi() is True
    del os.environ["TAMAGOTCHI_FORCE_PI"]


def test_default_detection_returns_bool():
    # Ensure function always returns a boolean (no crash on CI)
    assert isinstance(tamagotchi.is_raspberry_pi(), bool)