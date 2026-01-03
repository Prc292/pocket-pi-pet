## Purpose
Concise, practical guidance for AI coding agents working on this project. Focus on what a contributor needs to be productive: where to look, how to run and test, and project-specific conventions.

## Quick start
- Entrypoint: `tamagotchi.py` (single-file app). Key classes: `Pet` (game state & persistence) and `GameEngine` (UI/event loop).
- Run locally: `python3 tamagotchi.py` (or `python3 -m pdb tamagotchi.py`). Install deps: `pip install -r requirements.txt` and dev deps with `pip install -r requirements-dev.txt`.

## Key patterns & constants (be explicit)
- SAVE_FILE (`pet_save.json`) — `Pet.save()` writes JSON via an atomic replace (write to `SAVE_FILE + ".tmp"` then `os.replace()`).
- TIME_SCALE / env `TAMAGOTCHI_TIME_SCALE` — multiplies elapsed seconds (tests set this to speed decays).
- MAX_CATCHUP_SECONDS — `Pet.load()` clamps catch-up to this cap to avoid huge one-time decays.
- Headless CI: tests set `SDL_VIDEODRIVER=dummy` (see `tests/*` and `.github/workflows/ci.yml`).

## Testing conventions (concrete examples)
- Tests import the app by file path — see this pattern used across tests:
	```py
	import importlib.util, os
	spec = importlib.util.spec_from_file_location("tamagotchi", os.path.join(os.path.dirname(__file__), os.pardir, "tamagotchi.py"))
	tamagotchi = importlib.util.module_from_spec(spec); spec.loader.exec_module(tamagotchi)
	```
- Tests commonly mutate module-level constants (e.g., `tamagotchi.SAVE_FILE = str(tmp_path / "pet_save.json")` or `tamagotchi.TIME_SCALE = 60.0`) rather than relying on PYTHONPATH.
- For UI/headless checks, tests set `SDL_VIDEODRIVER=dummy` via `monkeypatch.setenv()` or `os.environ.setdefault()` and use `GameEngine.step()`/helpers to drive UI logic in-process, or spawn a subprocess for smoke tests (`tests/test_engine_smoke.py`).

## How to add a persistent stat
1. Add attribute in `Pet.__init__` with a sensible default.
2. Add it to the JSON payload in `Pet.save()`.
3. Restore/validate it in `Pet.load()` (fall back to a default when invalid/missing).
4. Ensure `load()` calls `self.update()` (already in code) so catch-up applies.
5. Add any UI drawing in `GameEngine.run()` (e.g., `draw_bar()` or similar) and test it.

## Platform & integration notes
- Raspberry Pi detection: `is_raspberry_pi()` honors `TAMAGOTCHI_FORCE_PI=1` for CI tests that need Pi behavior.
- Audio: `SoundManager` handles mixer init and is a safe no-op in headless tests; audio env vars are `TAMAGOTCHI_AUDIO_FREQ`, `TAMAGOTCHI_AUDIO_CHANNELS`, and `TAMAGOTCHI_AUDIO_BUF`.
- Systemd service: `systemd/tamagotchi.service` and Pi setup scripts live at the repo root.

## Common pitfalls to watch for
- Save/load mismatches — tests cover this; ensure keys you add to `save()` are restored by `load()` with validation.
- Catch-up math — `update()` applies `TIME_SCALE` and clamps elapsed by `MAX_CATCHUP_SECONDS` (tests exist for both behaviors).

## Where to look first
- `tamagotchi.py` — `Pet`, `GameEngine`, `SoundManager`.
- `Tamagotchi/tests/` — lots of focused, concrete tests demonstrating expected behavior and testing patterns.
- `.github/workflows/ci.yml` — how CI runs headless tests (Python 3.11, `SDL_VIDEODRIVER=dummy`).

If anything here is unclear or you'd like additional examples (CI config, packaging, or contributor workflow), tell me which section to expand. 

