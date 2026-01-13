<!-- Purpose: guidance for AI coding agents working on this project -->
# Copilot / AI Agent Instructions

Quick start
- Entrypoint: `pipet.py` (single-file app). Key classes: `Pet` (game state & persistence) and `GameEngine` (UI & event loop).
- Run locally: `python3 pipet.py` (or `python3 -m pdb pipet.py` for debugging).
- Install deps: `pip install -r requirements.txt` and dev deps `pip install -r requirements-dev.txt` for tests.

Important constants & env vars
- `SAVE_FILE` (default: `pet_save.json`): file written/read by `Pet.save()`/`Pet.load()`.
- `TIME_SCALE` / env `PIPET_TIME_SCALE`: multiplies elapsed seconds (useful to accelerate time in tests/debugging).
- `MAX_CATCHUP_SECONDS`: cap for how much elapsed time `load()` will apply to avoid large sudden decays.
- `SDL_VIDEODRIVER`: set to `dummy` in CI/headless runs (tests set it to `dummy`); Linux code sets `kmsdrm` for fullscreen by default.

New gameplay stat: `cleanliness` (0-100)
- Decays at ~6 units/hour. Cleaning restores 30 cleanliness, increases happiness by +5 and costs -5 energy.
- If `cleanliness` < 30 the pet suffers an additional health decay (~2.5 units/hour).
- Add `clean()` method to `Pet` and a `CLEAN` popup button in the UI; tests for cleaning live in `PiPet/tests/test_cleanliness.py`.

New actions: `give_medicine()` and `MENU` popup
- `give_medicine()` heals +15 health, reduces happiness by -5, no effect if dead; tests in `PiPet/tests/test_medicine.py`.
- Small-screen UI: a compact `MENU` toggle (top-right) opens a popup with `CLEAN` and `MED` actions to save screen space on 480x320 displays. Use `GameEngine.step()` in headless tests to simulate clicks (see `PiPet/tests/test_ui.py`).

Life stages & evolution
- `Pet` tracks `birth_time` and `life_stage` (BABY, YOUNG, ADULT, ELDER).
- Stages change when age crosses thresholds (`STAGE_YOUNG_SECONDS`, `STAGE_ADULT_SECONDS`, `STAGE_ELDER_SECONDS`) only if average care `(health + happiness)/2` >= `EVOLUTION_MIN_CARE`.
- Tests for evolution are in `PiPet/tests/test_medicine.py`.

Balance & testing
- Gameplay tunables are exposed as constants at the top of `pipet.py` (e.g., `HUNGER_DECAY_PER_HOUR`) so automated balance sweeps and tests can adjust them easily.
- Integration/UI tests use `SDL_VIDEODRIVER=dummy` and `GameEngine.step()` to simulate UI events in headless CI.


Persistence & safety patterns
- Saves use an *atomic replace* pattern: write to `SAVE_FILE + ".tmp"` then `os.replace()` to avoid truncated files.
- Save JSON keys: `hunger`, `happiness`, `energy`, `health`, `is_alive`, `last_update`.
- `Pet.load()` is defensive: it validates numeric keys (via local `get_num()`), falls back to defaults, and calls `self.update()` to apply catch-up (bounded by `MAX_CATCHUP_SECONDS`).

Architecture & code style
- Single-file, procedural style. Keep logic (decay, state transitions, persistence) in `Pet` and UI/OS-specific code in `GameEngine`.
- Prefer small, localized edits over large refactors.

How to add a new persistent stat (explicit)
1. Add attribute in `Pet.__init__` with a sensible default.
2. Include it in `Pet.save()` JSON payload.
3. Restore it in `Pet.load()` (validate/fallback to default).
4. Call `self.update()` in `load()` (already done) so catch-up applies.
5. Add a `draw_bar()` (or equivalent) in `GameEngine.run()` to show it.

Testing & CI notes (concrete examples)
- Tests live under `tests/` (and a duplicate under `PiPet/tests/` in this workspace).
- Tests import the module by filepath (see tests using `importlib.util.spec_from_file_location`), so avoid relying on PYTHONPATH changes.
- Run tests: `pip install -r requirements-dev.txt && pytest`.
- Headless smoke tests use `SDL_VIDEODRIVER=dummy` and may spawn the script in a subprocess; see `tests/test_engine_smoke.py` for example.
- Use `PIPET_TIME_SCALE` to speed time-related tests (see `tests/test_time_scaling.py`).

UI polish & testing
- Small UI improvements (stat icon animations, HUD fade, icons instead of letters) should include tests which drive time forward (manipulating `engine._last_step_time` or `time.time()` in tests) or use helpers like `GameEngine.toggle_stat` and `GameEngine.show_hud` to keep tests reliable.
- Sound should be routed through a `SoundManager` abstraction that is a safe no-op in headless CI and exposes `last_played` for assertions.
- A GitHub Actions workflow (`.github/workflows/ci.yml`) is included to run headless tests using `SDL_VIDEODRIVER=dummy`.

Common bug hotspots & checks
- Save/load mismatch: ensure keys written in `save()` match what `load()` expects (and validate types).
- Catch-up math: `update()` multiplies elapsed by `TIME_SCALE` and applies `MAX_CATCHUP_SECONDS` cap—tests cover both behaviors.
- Platform window flags: Linux path sets `SDL_VIDEODRIVER=kmsdrm` and `pygame.FULLSCREEN`; macOS uses `pygame.SCALED|pygame.RESIZABLE`.

Files to inspect first
- `pipet.py` — read `Pet` and `GameEngine` implementations first.
- `tests/test_pet.py`, `tests/test_engine_smoke.py`, `tests/test_time_scaling.py` — show how functionality and edge cases are validated.

If you edit behavior: add/adjust unit tests that reproduce the intended behavior (tests are small and focused). Ask for clarification if you need broader refactor permission.

If anything here is unclear or you'd like additional examples (CI config, packaging, or contributor workflow), tell me which sections to expand.
