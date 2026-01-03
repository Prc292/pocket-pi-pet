import os
import importlib.util
import time
import json
import tempfile

def import_tamagotchi():
    spec = importlib.util.spec_from_file_location(
        "tamagotchi",
        os.path.join(os.path.dirname(__file__), os.pardir, "tamagotchi.py"),
    )
    tamagotchi = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(tamagotchi)
    return tamagotchi

def test_egg_state_and_hatching(tmp_path):
    tamagotchi = import_tamagotchi()
    tamagotchi.SAVE_FILE = str(tmp_path / "pet_save.json")
    # Start new pet, should be in EGG life_stage
    p = tamagotchi.Pet()
    assert p.life_stage == tamagotchi.Pet.STAGE_EGG
    # Simulate time passing to just before hatching
    p.birth_time -= (p.EGG_HATCH_SECONDS - 1)
    p.update()
    assert p.life_stage == tamagotchi.Pet.STAGE_EGG
    # Simulate time passing to after hatching
    p.birth_time -= 2
    p.update()
    assert p.life_stage == tamagotchi.Pet.STAGE_BABY
    # Save and reload, should persist life_stage
    p.save()
    p2 = tamagotchi.Pet()
    p2.load()
    assert p2.life_stage == tamagotchi.Pet.STAGE_BABY
