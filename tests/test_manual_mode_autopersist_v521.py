"""v2.1 — Manual race-selection now persists by default and survives reloads.

Root cause of the tester report ("Smart race solver took over even though the
schedule was right there, while on Manual Selection"): the manual/smart authority
key ``extra_race_list_source`` was never persisted -- ``serialize_preset`` rebuilds
presets from an allowlist that omitted it, so every ConfigStore write dropped it and
``read_one`` always returned empty. Manual mode therefore lived only in ephemeral
browser state (``racePlannerMode`` in localStorage) sent at career start; any reload
reset it to "smart" and the solver took over.

These tests lock in:
  - the backend round-trip (extra_race_list_source survives write -> read_one), which
    also re-arms the career-start defense-in-depth backstop in main.py;
  - no leak into the solver-config surface (avoids round-trip pollution);
  - the frontend wiring: manual picks/mode auto-persist, and the planner mode is
    restored from the persisted source on load.
"""
import tempfile
import unittest
from pathlib import Path

from career_bot.config_store import ConfigStore, SETTING_PRESET_KEYS, SMART_SOLVER_KEYS

ROOT = Path(__file__).resolve().parents[1]
APP = (ROOT / "public" / "app.js").read_text(encoding="utf-8")
MAIN = (ROOT / "main.py").read_text(encoding="utf-8")


class ManualSourcePersistenceTests(unittest.TestCase):
    def test_source_is_a_recognized_settings_key(self):
        # It must live in the settings surface (so write persists it + read_one
        # returns it), NOT the solver-config surface (so the frontend's
        # smart-solver config round-trip can't overwrite it with a stale copy).
        self.assertIn("extra_race_list_source", SETTING_PRESET_KEYS)
        self.assertNotIn("extra_race_list_source", SMART_SOLVER_KEYS)

    def test_source_survives_write_read_round_trip(self):
        with tempfile.TemporaryDirectory() as tmp:
            store = ConfigStore(Path(tmp))
            store.write({
                "name": "ManualPreset",
                "extra_race_list": [101, 102],
                "extra_race_list_source": "manual",
                "mant_config": {},
            })
            got = store.read_one("ManualPreset")
            self.assertEqual(str(got.get("extra_race_list_source") or "").lower(), "manual")
            self.assertEqual([int(x) for x in got.get("extra_race_list") or []], [101, 102])
            # No pollution of the solver-config surface.
            self.assertNotIn("extra_race_list_source", store.read_solver_config("ManualPreset"))

    def test_smart_source_also_round_trips(self):
        with tempfile.TemporaryDirectory() as tmp:
            store = ConfigStore(Path(tmp))
            store.write({"name": "SmartPreset", "extra_race_list_source": "smart", "mant_config": {}})
            self.assertEqual(str(store.read_one("SmartPreset").get("extra_race_list_source") or "").lower(), "smart")


class ManualModeFrontendWiringTests(unittest.TestCase):
    def test_autosave_no_longer_bails_in_manual_mode(self):
        # The early-return that kept manual picks "staged until Apply Manual" is gone.
        self.assertNotIn("if (state.racePlannerMode === 'manual' && !force) return;", APP)
        # The saved source still tracks the visible mode.
        self.assertIn("source: state.racePlannerMode === 'manual' ? 'manual' : 'smart'", APP)

    def test_picking_a_race_auto_persists(self):
        self.assertIn("autoSaveRaces().catch(() => {}); // v2.1 auto-persist manual pick", APP)

    def test_mode_buttons_persist_source_on_switch(self):
        self.assertIn(
            "els.v47ManualModeBtn?.addEventListener('click', () => { setRacePlannerMode('manual'); autoSaveRaces().catch(() => {}); });",
            APP,
        )
        self.assertIn(
            "els.v47SmartModeBtn?.addEventListener('click', () => { setRacePlannerMode('smart'); autoSaveRaces().catch(() => {}); });",
            APP,
        )

    def test_mode_is_restored_from_persisted_source_on_load(self):
        self.assertIn("const savedSource = String(res.source || '').trim().toLowerCase();", APP)
        self.assertIn("setRacePlannerMode(savedSource, { persist: true, render: false });", APP)

    def test_backend_endpoint_returns_saved_source(self):
        self.assertIn('saved = preset_store.read_one(preset or None) or {}', MAIN)
        self.assertIn('source = str(saved.get("extra_race_list_source") or "").strip().lower()', MAIN)
        self.assertIn('"source": source', MAIN)


if __name__ == "__main__":
    unittest.main()
