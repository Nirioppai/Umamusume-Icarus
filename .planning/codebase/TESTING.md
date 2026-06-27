# Testing Patterns

**Analysis Date:** 2026-06-27

## Test Framework

**Runner:**
- Both `unittest.TestCase` and bare `pytest`-style functions are used side by side
- pytest is the de facto runner (supports both styles)
- No `pytest.ini`, `conftest.py`, `pyproject.toml`, or `setup.cfg` test configuration exists
- No dedicated test configuration file detected

**Assertion Library:**
- `unittest.TestCase` assertions: `assertEqual`, `assertTrue`, `assertIn`, `assertAlmostEqual`, `assertGreater`, `assertIsNotNone`, `assertIsNone`, `assertLess`
- Plain `assert` statements in pytest-style tests: `assert result['success'] is True`, `assert len(rows) == 2`
- No third-party assertion library (no `pytest-assume`, `assertpy`, etc.)

**Run Commands:**
```bash
python -m pytest tests/              # Run all tests
python -m pytest tests/ -v           # Verbose output
python -m pytest tests/test_training_scorer.py  # Single file
python -m unittest tests/test_training_scorer.py  # Also works (files have __main__ guard)
```

## Test File Organization

**Location:**
- All tests in a dedicated `tests/` directory at the project root
- Tests are NOT co-located with source files
- No subdirectories within `tests/`

**Naming:**
- `test_<feature>.py` -- general feature tests (e.g., `test_training_scorer.py`, `test_character_data.py`)
- `test_v<version>_<feature>.py` -- version-tagged regression tests (e.g., `test_v15_mood.py`, `test_v679_fixes.py`, `test_v6720_fixes.py`)
- `test_sweepymodv<sprint>_<feature>.py` -- sprint-tagged feature tests (e.g., `test_sweepymodv544_event_outcomes.py`, `test_sweepymodv532_ai_dataset.py`)
- 97 test files total, ~13,537 lines of test code

**Structure:**
```
tests/
├── test_training_scorer.py          # Unit tests for scorer module
├── test_character_data.py           # Data catalog tests
├── test_crash_scenario.py           # Integration crash regression
├── test_regret_replay.py            # Counterfactual analysis tests
├── test_trackblazer_p0_items.py     # Item management tests
├── test_v15_mood.py                 # Version-specific feature test
├── test_sweepymodv544_event_outcomes.py  # Sprint feature test
├── test_ui_contract.py              # Static HTML/JS contract checks
└── ...                              # 89 more test files
```

## Test Structure

**unittest.TestCase Suite Organization (dominant pattern, ~89 files):**
```python
"""Tests for the v6.1 SweepyCL training scorer.

Covers:
  - score_trainings end-to-end on realistic command_info_array shapes
  - Each component in isolation via _score_one_command
  - Edge cases: missing fields, disabled commands
"""
from __future__ import annotations
import unittest
from career_bot.training_scorer import score_trainings, TrainingScorerConfig

class StatBreakdownTests(unittest.TestCase):
    def test_typical_command(self):
        cmd = make_training_cmd(stat_gains={"speed": 12, "power": 3})
        gains, sp = _stat_gain_breakdown(cmd)
        self.assertEqual(gains["speed"], 12)
        self.assertEqual(sp, 4)

    def test_handles_malformed_entries_gracefully(self):
        cmd = {"params_inc_dec_info_array": [{"target_type": "junk", "value": 5}]}
        gains, sp = _stat_gain_breakdown(cmd)
        self.assertEqual(gains["speed"], 0)
```
See `tests/test_training_scorer.py` lines 100-133.

**pytest-style Function Organization (15 files):**
```python
def test_runner_pause_resume_snapshot(tmp_path):
    runner = CareerRunner(tmp_path)
    runner.status.update({"running": True, "turn": 12})
    runner.pause()
    snap = runner.snapshot()
    assert snap["paused"] is True

def test_runtime_event_override_wins_and_seen_log_is_written(tmp_path):
    runtime = tmp_path / "uma_runtime"
    runtime.mkdir()
    (runtime / "event_overrides.json").write_text(json.dumps({"12345": 0}))
    mgr = EventManager(tmp_path)
    assert mgr.choose(event, preset={}, current_turn=1, chara={}) == 0
```
See `tests/test_sweepymodv526_operator_controls.py` lines 8-26.

**Patterns:**
- `setUp()` used sparingly (mainly for creating `CareerRunner` or strategy instances)
- `tearDown()` used for environment variable cleanup: `os.environ.pop("UMA_RUNTIME_DIR", None)`
- Most tests are self-contained -- fixture data is built inline per test method
- Module-level docstrings describe what the test file covers (consistent across all files)

## Mocking

**Framework:** Primarily hand-rolled fakes. `unittest.mock` used occasionally.

**Fake Client Pattern (dominant):**
```python
class FakeClient:
    api_jitter = 0.0
    def __init__(self):
        self.loads = 0
        self.entry_calls = 0
    def wait_turn_delay(self):
        pass
    def race_entry(self, **kwargs):
        self.entry_calls += 1
        raise Exception("API error 208 on single_mode_free/race_entry")
    def load_career(self):
        self.loads += 1
        return st(60, 2, {"race_start_info": {"program_id": 7}})
```
See `tests/test_crash_scenario.py` lines 48-69.

**Fake Strategy Pattern:**
```python
class FakeStrategy:
    def __init__(self):
        self.steps = 0
    def next_decision(self, state, preset):
        self.steps += 1
        return Decision("idle", {}, "test done")
```
See `tests/test_crash_scenario.py` lines 71-86.

**Delay Stubbing Pattern:** Tests that invoke `CareerRunner._run()` must stub delays to avoid real `time.sleep()` calls. This is done at module level before importing the runner:
```python
import career_bot.delay as delay
delay.dna_sleep = lambda *a, **k: None
```
See `tests/test_crash_scenario.py` lines 9-11.

**sys.modules Stubbing for Missing Dependencies:** Tests that need `uma_api.client` (which requires `curl_cffi` and `Crypto`) stub those modules at import time:
```python
import sys, types
if "curl_cffi" not in sys.modules:
    module = types.ModuleType("curl_cffi")
    module.requests = types.SimpleNamespace(...)
    sys.modules["curl_cffi"] = module

if "Crypto" not in sys.modules:
    crypto = types.ModuleType("Crypto")
    # ... stub AES, padding, etc.
    sys.modules.update({...})
```
See `tests/test_tp_recovery.py` lines 4-28.

**MagicMock for Module Stubs:**
```python
from unittest.mock import MagicMock
sys.modules.setdefault("msgpack", MagicMock())
```
See `tests/test_v679_fixes.py` line 32.

**monkeypatch (pytest fixtures):**
```python
def test_normalize_dumper_outcomes(tmp_path, monkeypatch):
    monkeypatch.setenv('UMA_RUNTIME_DIR', str(tmp_path / 'uma_runtime'))
    ...
```
Used in 8 test files, primarily for environment variable and function injection. See `tests/test_sweepymodv544_event_outcomes.py`.

**Monkey-patching runner internals:**
```python
runner._buy_skills = lambda c, s, p, f: s
runner._handle_items = lambda c, s, p, b, d=None: s
runner.item_manager.handle_pre_race = lambda c, s, p, pl, st_, rp: (s, 0)
```
See `tests/test_crash_scenario.py` lines 92-95.

**What to Mock:**
- API client methods (`call`, `race_entry`, `load_career`) -- always mock, never call real API
- Delay functions (`dna_sleep`, `simulate_delay`) -- always stub to avoid sleeping
- Heavy dependencies (`curl_cffi`, `Crypto`, `msgpack`, `frida`) -- stub at sys.modules level when not installed in test env
- Runner side-effect methods (`_buy_skills`, `_handle_items`) -- stub when testing a specific code path

**What NOT to Mock:**
- Game logic functions (`score_trainings`, `analyze_regret`, `choose`) -- test the real implementation
- Data loading (`load_character_presets`, `load_epithet_catalog`) -- test against real shipped JSON files
- Scoring algorithms (`training_scorer`, `policy_guards`) -- test real math

## Fixtures and Factories

**Test Data Factories (module-level helper functions):**
```python
def make_training_cmd(*, command_id=101, stat_gains=None, skill_point=2,
                      partners=None, failure_rate=0, level=1, is_enable=1):
    """Build a realistic training command dict matching API shape."""
    type_for_stat = {"speed": 1, "stamina": 2, "power": 3, "guts": 4, "wit": 5}
    arr = []
    for name, value in (stat_gains or {}).items():
        tt = type_for_stat.get(name)
        if tt:
            arr.append({"target_type": tt, "value": value})
    return {"command_type": 1, "command_id": command_id, ...}

def make_chara(stats=None, bonds=None, distance_aptitudes=None):
    """Build a realistic chara_info dict."""
    base_stats = {"speed": 200, "stamina": 200, ...}
    ...
```
See `tests/test_training_scorer.py` lines 41-93.

**State Builder Pattern:**
```python
def st(turn, playing_state=1, extra=None):
    data = {
        "chara_info": {"turn": turn, "playing_state": playing_state, "vital": 50, ...},
        "home_info": {"command_info_array": []},
    }
    if extra:
        data.update(extra)
    return {"data": data}

def state(turn=30, vital=50, max_vital=100, motivation=4, owned=None, shop=None, coins=0):
    return {"data": {"chara_info": {...}, "free_data_set": {...}}}
```
See `tests/test_crash_scenario.py` lines 25-45, `tests/test_trackblazer_p0_items.py` lines 45-62.

**Location:**
- Factory functions are defined at the top of each test file (no shared fixtures module)
- Each test file builds its own domain-specific helpers
- `REPO_ROOT = Path(__file__).resolve().parent.parent` is the standard way to reference the project root
- `tmp_path` (pytest built-in fixture) used for tests that write files

## Coverage

**Requirements:** No coverage target enforced. No coverage configuration detected.

**View Coverage:**
```bash
python -m pytest tests/ --cov=career_bot --cov-report=term  # If pytest-cov is installed
```

## Test Types

**Unit Tests (majority):**
- Pure function testing: `score_trainings()`, `analyze_regret()`, `_stat_gain_breakdown()`
- Class method testing: `MantStrategy._should_recreate()`, `MantItemManager.buy_shop_items()`
- Data validation: shipped JSON catalogs load correctly, character name matching works
- ~90% of tests fall in this category

**Integration Tests:**
- Runner execution with fake clients: tests that call `runner._run()` with `FakeClient` + `FakeStrategy` to verify the full decision loop handles edge cases
- API endpoint tests using `fastapi.testclient.TestClient` (see `tests/test_sweepymodv544_event_outcomes.py`)
- File I/O integration: tests that write JSON to `tmp_path` and verify the module reads it back correctly

**Source Code Contract Tests (unique pattern):**
- Tests that read source code and assert structural properties using string matching:
  ```python
  RUNNER_SOURCE = (ROOT / "career_bot" / "runner.py").read_text(encoding="utf-8")

  def test_client_retries_temporary_gateway_statuses_inside_post_loop(self):
      self.assertIn("retryable_http_statuses = {500, 502, 503, 504}", CLIENT_SOURCE)
      self.assertIn("while True:", CLIENT_SOURCE)
  ```
  See `tests/test_sweepymodv520_http_gateway_recovery.py` lines 26-48, `tests/test_sweepymodv525_umabot_stability.py` lines 70-75.
- UI contract tests verify that HTML IDs referenced in `app.js` exist in `index.html`:
  ```python
  def test_static_appjs_ids_exist_in_index_html():
      needed = set(re.findall(r"getElementById\(['\"]([\w-]+)['\"]\)", APP_JS)) - DYNAMIC_IDS
      missing = needed - html_ids()
      assert not missing
  ```
  See `tests/test_ui_contract.py` lines 80-83.

**E2E Tests:**
- Not present. No browser automation, no Selenium/Playwright.

## Common Patterns

**Async Testing:**
- Not used. All tests are synchronous. FastAPI's `TestClient` handles async endpoints synchronously.

**Error Testing:**
```python
def test_handles_malformed_entries_gracefully(self):
    cmd = {"params_inc_dec_info_array": [{"target_type": "junk", "value": 5}]}
    gains, sp = _stat_gain_breakdown(cmd)
    self.assertEqual(gains["speed"], 0)  # No crash, graceful fallback

def test_missing_preset_file_returns_empty_dict(self):
    with tempfile.TemporaryDirectory() as td:
        self.assertEqual(character_data.load_character_presets(Path(td)), {})

def test_corrupt_json_returns_empty(self):
    with tempfile.TemporaryDirectory() as td:
        base = Path(td)
        (base / "data" / "character_data").mkdir(parents=True)
        (base / "data" / "character_data" / "epithets.json").write_text("not valid json {{")
        self.assertEqual(character_data.load_epithet_catalog(base), {})
```
See `tests/test_character_data.py` lines 95-117.

**Numeric Precision Testing:**
```python
self.assertAlmostEqual(report.decision_regret_total, 20.0)
self.assertAlmostEqual(report.decision_regret_total, 0.20, places=6)
```
See `tests/test_regret_replay.py` lines 49, 113.

**Behavioral Regression Testing:**
```python
def test_full_crash_sequence_survives_chara_less_race_out():
    runner = CareerRunner(str(ROOT))
    runner.status["running"] = True
    client = FakeClient()
    runner._run(client, {"name": "t", "scenario_id": 4}, st(60), FakeStrategy(), max_steps=10)
    assert runner.status["last_error"] == "", runner.status["last_error"]
    assert client.entry_calls == 1
    assert client.loads >= 2
```
See `tests/test_crash_scenario.py` lines 88-99.

## Writing New Tests

**When to use unittest.TestCase:**
- For grouped related assertions on the same module (e.g., "all scorer component tests")
- When you want `setUp()`/`tearDown()` lifecycle
- When assertions benefit from `self.assertAlmostEqual`, `self.assertIn`, `self.assertIsNotNone`

**When to use bare pytest functions:**
- For integration tests that need `tmp_path` or `monkeypatch` fixtures
- For concise single-assertion tests
- For tests involving FastAPI `TestClient`

**New test file checklist:**
1. Add module-level docstring explaining what's tested
2. Place in `tests/` directory
3. Name as `test_<feature>.py` or `test_v<version>_<feature>.py`
4. Import the module under test directly
5. Build fixture data inline using factory functions
6. If testing runner/client code: stub delays and heavy dependencies
7. Add `if __name__ == "__main__": unittest.main()` guard for unittest-based files

---

*Testing analysis: 2026-06-27*
