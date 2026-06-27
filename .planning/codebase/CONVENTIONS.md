# Coding Conventions

**Analysis Date:** 2026-06-27

## Naming Patterns

**Files:**
- Use `snake_case.py` for all Python modules: `training_scorer.py`, `career_recovery.py`, `race_intelligence.py`
- Test files use `test_` prefix with descriptive suffixes: `test_training_scorer.py`, `test_v679_fixes.py`, `test_sweepymodv544_event_outcomes.py`
- Version-tagged test files encode the feature version: `test_sweepymodv5XX_<feature>.py`, `test_vXX_<feature>.py`

**Functions:**
- Use `snake_case` for all functions and methods: `score_trainings()`, `load_career()`, `pre_summer_action()`
- Private/internal functions use leading underscore: `_bond_map_from_chara()`, `_load_training_effects()`, `_score_one_command()`
- Module-level helpers often use `_` prefix for internal use: `_load_json()`, `_read_json()`, `_push_replan_log()`
- Short abbreviation suffixes are acceptable: `_apt_to_rank()`, `_ece_interpretation()`

**Variables:**
- Use `snake_case` for all variables: `race_planner`, `event_manager`, `training_effects`
- Constants use `UPPER_SNAKE_CASE`: `STAT_KEYS`, `SUMMER_CAMP_TURNS`, `BASE_URL`, `RAINBOW_BOND_THRESHOLD_DEFAULT`
- Dict-style constants for game data mappings: `TRAINING_COMMANDS = {101: 0, 105: 1, ...}`, `STAT_TARGETS = {1: 0, 2: 1, ...}`

**Classes:**
- Use `PascalCase`: `CareerRunner`, `MantStrategy`, `TrainingScorerConfig`, `EventManager`
- Dataclasses for value objects: `Decision`, `TrainingScore`, `PolicyGuardConfig`, `BetaPosterior`
- Strategy pattern uses `ScenarioStrategy` base class with `scenario_id` class attribute
- Exception classes follow standard naming: `StateRecoveryError(Exception)`

**Types:**
- Type hints from `typing` module: `Dict[str, Any]`, `Optional[int]`, `Mapping[str, Any]`
- Use `from __future__ import annotations` in modules with complex type hints (20 of 32 career_bot modules)
- `Any` is the dominant type for game-API payloads (nested dicts from msgpack)

## Code Style

**Formatting:**
- No automated formatter configured (no `.prettierrc`, `pyproject.toml`, `.flake8`, `setup.cfg`, `.editorconfig` detected)
- 4-space indentation (Python standard)
- Consistent single-blank-line separation between methods within classes
- Double-blank-line separation between top-level definitions
- Line length is flexible; lines up to ~120 characters appear regularly

**Linting:**
- No linter configuration detected
- Code is clean with zero TODO/FIXME/HACK/XXX comments across the entire `career_bot/` package
- Imports are generally well-organized but no enforced sort order

## Import Organization

**Order:**
1. Standard library imports (`json`, `os`, `time`, `threading`, `math`, `pathlib`)
2. Third-party imports (`fastapi`, `pydantic`, `frida`, `msgpack`, `requests`, `curl_cffi`)
3. Local/project imports (`from career_bot.runner import CareerRunner`, `from uma_api.client import UmaClient`)

**Style:**
- Module-level imports preferred: `from career_bot import trackblazer`, `from career_bot import event_outcomes as event_kb`
- Named imports for specific symbols: `from career_bot.scenarios.base import Decision, ScenarioStrategy`
- Relative imports within `career_bot/` package: `from .presets import hydrate_preset, serialize_preset, slugify` (in `config_store.py`)
- No barrel files (`__init__.py` files not present in any package)

**Path Aliases:**
- None configured. All imports use full dotted paths.

**Guarded Imports:**
- Some modules guard optional imports with try/except for test-harness safety:
  ```python
  try:
      from career_bot.ai_trainer import after_career_export
  except Exception:
      after_career_export = None
  ```
  See `career_bot/report.py` line 9-12.

## Error Handling

**Patterns:**

1. **Broad bare `except Exception` for resilience:** The dominant pattern across the codebase (277 occurrences). Game-API data is unpredictable, so most JSON parsing, data access, and file I/O wraps in `try/except Exception` with a safe fallback (empty dict, empty list, `None`, default value):
   ```python
   try:
       data = json.loads(path.read_text(encoding="utf-8"))
       return data if isinstance(data, dict) else {}
   except Exception:
       return {}
   ```
   This pattern appears in `career_bot/events.py`, `career_bot/races.py`, `career_bot/master_data.py`, `career_bot/config_store.py`, and many others.

2. **Specific exceptions for network/API errors:** The API client (`uma_api/client.py`) uses specific exception types for recoverable vs fatal errors:
   ```python
   except (urllib.error.URLError, TimeoutError, json.JSONDecodeError, OSError) as exc:
   ```
   See `manager.py` line 253.

3. **Custom exceptions are rare:** Only `StateRecoveryError` in `uma_api/client.py` line 21. Most error signaling uses standard `Exception` with descriptive messages.

4. **`raise SystemExit()` for startup validation failures:**
   ```python
   raise RuntimeError("Missing Python dependencies: ...")
   raise SystemExit("accounts.json must be a list of account objects")
   ```
   See `main.py` lines 27-29, `manager.py` line 78.

5. **Best-effort operations never crash:** File writes, telemetry, diagnostics, and metric exports are wrapped to silently fail. The pattern `try: ... except Exception: pass` is common for optional side-effects.

## Logging

**Framework:** `print()` with `flush=True` for console output. No `logging` module used anywhere.

**Patterns:**
- `print(f"...", flush=True)` in `career_bot/delay.py` for timing telemetry
- `print(f"...")` in `manager.py` for process lifecycle events
- Status dict (`self.status["log"]`) used as an in-memory log buffer in `CareerRunner` for dashboard display
- `DiscordCareerLogger` (`career_bot/discord_logger.py`) for webhook-based telemetry export
- Bot decisions are traced via the `report` system (`career_bot/report.py`) and written to JSON career logs

## Comments

**When to Comment:**
- Module-level docstrings explain the purpose, API surface, and design rationale for every module with complex logic. These are extensive and high-quality. Example from `career_bot/training_scorer.py`:
  ```python
  """SweepyCL training scorer (v6.1).
  Reimplements the Trackblazer training-scoring formula: ...
  API surface intentionally small:
    - ``TrainingScorerConfig`` -- dataclass holding all tunables.
    - ``TrainingScore``        -- per-command output with components + diagnostics.
  No new dependencies.  Pure standard library.
  """
  ```
- Inline comments explain game-specific constants and version-tagged behavior changes:
  ```python
  # v7.6.2: native event-outcome capture. SweepyCL already receives
  # chara_info before/after every event choice...
  ```
- Version references (e.g., `# v6.7.20:`, `# v1.5:`, `# #6 --`) annotate when features were added

**Docstrings:**
- Module-level docstrings on ~21 of 32 `career_bot/` modules (65%)
- Method docstrings used for non-obvious logic; ~310 method/function docstrings across `career_bot/`
- Docstring style: plain text descriptions, sometimes with RST-style double-backtick references to symbols. No structured parameter documentation (no `:param:`, no Google/Numpy style)

## Function Design

**Size:** Functions range widely. Most are 10-50 lines. A few critical methods in `career_bot/runner.py` and `career_bot/scenarios/mant.py` are longer (the `_run()` loop in runner.py is several hundred lines).

**Parameters:** Keyword arguments preferred for complex functions. Game state is passed as raw dicts (`state`, `chara_info`, `home_info`) rather than typed objects:
```python
def score_trainings(home_info, chara_info, config=None, context="training", ...)
```

**Return Values:**
- Functions return dicts for complex results (matching JSON API shapes)
- `None` for "not found" fallbacks
- Dataclasses for structured scoring/analysis results: `TrainingScore`, `RegretReport`, `GuardDecision`

## Module Design

**Exports:**
- `__all__` defined in 6 modules: `career_bot/character_data.py`, `career_bot/ai_modeling.py`, `career_bot/calibration.py`, `career_bot/character_profiles.py`, `career_bot/policy_guards.py`, `career_bot/training_scorer.py`
- Most modules export everything at module level without `__all__`

**Barrel Files:** Not used. No `__init__.py` files exist in any package directory.

**Module Responsibilities:** Each module owns a single domain concern:
- `career_bot/runner.py` (4049 lines) -- career execution loop, the largest module
- `career_bot/races.py` -- race scheduling and planning
- `career_bot/events.py` -- event choice logic
- `career_bot/skills.py` -- skill purchase logic
- `career_bot/items.py` -- item management
- `career_bot/training_scorer.py` -- training scoring algorithm
- `career_bot/scenarios/mant.py` -- MANT scenario strategy

## Data Handling Conventions

**JSON I/O pattern:** Atomic writes using tmp-then-replace to prevent corruption:
```python
def atomic_write_json(path: Path, data):
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(path.suffix + ".tmp")
    tmp.write_text(json.dumps(data, indent=2, ensure_ascii=False), encoding="utf-8")
    tmp.replace(path)
```
See `manager.py` lines 86-90, `career_bot/runner.py` line 148-150.

**Encoding:** Always specify `encoding="utf-8"` on file reads/writes.

**Path handling:** Use `pathlib.Path` throughout. `Path(__file__).resolve().parent` for module-relative paths. `REPO_ROOT` or `base_dir` pattern for test/runtime path resolution.

**Game data access:** Defensive `.get()` chaining on nested dicts with fallbacks:
```python
chara = data.get("chara_info") or {}
turn = int(chara.get("turn") or 0)
```

## Concurrency Patterns

- `threading.Lock()` for shared state protection in `CareerRunner` and `EventManager`
- `threading.Thread` for background career execution
- No async/await in bot logic (FastAPI handles async at the API layer only)
- Thread-local storage via `threading.local()` in `GateKeeper` (`career_bot/delay.py`)

---

*Convention analysis: 2026-06-27*
