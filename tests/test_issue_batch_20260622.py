"""Issue batch 2026-06-22 — verified fixes for 5 tester-reported issues.

1. Energy items / rest guard exempt year-end races (Hopeful Stakes/Arima/finale).
2. Shop blacklist no longer scrolls to top on toggle (frontend wiring).
3. Guest parents: login no longer seeds random umas via the broad heuristic.
4. New run after a manual finish: resume branch self-heals instead of crashing.
5. Per-race running-style overrides (stamina-gated, revert next race, manual-safe).
"""
import unittest
from pathlib import Path

from career_bot import trackblazer_rules as tb
from career_bot.trackblazer_rules import VITA_GAINS
from career_bot.items import MantItemManager
from career_bot.runner import CareerRunner
from career_bot.career_start_recovery import resume_career_fields

ROOT = Path(__file__).resolve().parents[1]
MAIN = (ROOT / "main.py").read_text(encoding="utf-8")
APP = (ROOT / "public" / "app.js").read_text(encoding="utf-8")
RUNNER = (ROOT / "career_bot" / "runner.py").read_text(encoding="utf-8")
INDEX = (ROOT / "public" / "index.html").read_text(encoding="utf-8")


# ---------------------------------------------------------------- #3 energy
class YearEndTurnHelpersTests(unittest.TestCase):
    def test_rest_exempt_set(self):
        for t in (23, 24, 47, 48, 71, 72, 73, 74, 77, 90):
            self.assertTrue(tb.is_year_end_rest_exempt(t), t)
        for t in (1, 22, 25, 46, 49, 70):
            self.assertFalse(tb.is_year_end_rest_exempt(t), t)

    def test_energy_waste_set_excludes_early_dec_halves(self):
        # Only the LAST training turn of each year (+ finale) is "energy waste".
        for t in (24, 48, 72, 73, 78):
            self.assertTrue(tb.is_year_end_energy_waste_turn(t), t)
        # 23/47/71 are EXCLUDED -- the next turn is still a real training turn.
        for t in (23, 47, 71, 22, 25, 46):
            self.assertFalse(tb.is_year_end_energy_waste_turn(t), t)


class EnergyItemSkipTests(unittest.TestCase):
    def _mgr(self):
        return MantItemManager()

    def test_energy_targets_skipped_when_flag_set(self):
        mgr = self._mgr()
        vita = max(VITA_GAINS, key=VITA_GAINS.get)
        chara = {"vital": 5, "max_vital": 100, "turn": 72, "motivation": 3}
        owned = {vita: 5}
        preset = {"mant_config": {}}
        # Control: with the pre-race skip OFF, low vital + owned vitas -> queues.
        mgr._skip_energy_items = False
        self.assertTrue(len(mgr._energy_targets(chara, owned, preset)) > 0)
        # With the pre-race skip ON (year-end race turn), nothing is queued.
        mgr._skip_energy_items = True
        self.assertEqual(mgr._energy_targets(chara, owned, preset), [])

    def test_skip_defaults_off_for_per_turn_path(self):
        # handle() resets the flag so per-turn training energy is never suppressed.
        mgr = self._mgr()
        self.assertFalse(getattr(mgr, "_skip_energy_items", False))


# ---------------------------------------------------------------- #5 per-race style
class _StubPlanner:
    def __init__(self, names):
        self._names = {int(k): v for k, v in names.items()}

    def _program_info(self, pid):
        return {"name": self._names.get(int(pid or 0), "")}

    def _distance_bucket(self, pid):
        return None


def _runner(planner):
    r = CareerRunner.__new__(CareerRunner)
    r.race_planner = planner
    return r


class PerRaceStyleOverrideTests(unittest.TestCase):
    def setUp(self):
        self.planner = _StubPlanner({168: "Kikuka Sho", 76: "Tenno Sho (Autumn)"})
        self.runner = _runner(self.planner)
        self.preset = {"running_style": 2, "mant_config": {"per_race_style_overrides": [
            {"match": "Kikuka Sho", "stamina_below": 450, "style": 3},
            {"match": "Tenno Sho (Spring)", "stamina_below": 630, "style": 3},
        ]}}

    def test_override_fires_below_threshold(self):
        self.assertEqual(self.runner._per_race_style_override(self.preset, 168, {"stamina": 400}), 3)

    def test_override_skipped_at_or_above_threshold(self):
        self.assertIsNone(self.runner._per_race_style_override(self.preset, 168, {"stamina": 500}))

    def test_name_disambiguation_spring_does_not_match_autumn(self):
        # A "Tenno Sho (Spring)" rule must NOT fire for "Tenno Sho (Autumn)".
        self.assertIsNone(self.runner._per_race_style_override(self.preset, 76, {"stamina": 100}))

    def test_resolve_applies_override_with_concrete_base(self):
        self.assertEqual(self.runner._running_style_for_race(self.preset, 168, 68, chara={"stamina": 400}), 3)
        # Above threshold -> falls back to the concrete base style (2).
        self.assertEqual(self.runner._running_style_for_race(self.preset, 168, 68, chara={"stamina": 900}), 2)

    def test_auto_base_suppresses_override_no_leak(self):
        # If the base is "auto" (0) the bot doesn't manage style, so an override
        # would leak (no reset call). It must be suppressed -> returns 0.
        auto = {"running_style": "auto", "mant_config": {"per_race_style_overrides": [
            {"match": "Kikuka Sho", "style": 3},
        ]}}
        self.assertEqual(self.runner._running_style_for_race(auto, 168, 68, chara={"stamina": 100}), 0)

    def test_unconditional_override_without_threshold(self):
        preset = {"running_style": 1, "mant_config": {"per_race_style_overrides": [
            {"match": "Kikuka Sho", "style": 4},
        ]}}
        self.assertEqual(self.runner._running_style_for_race(preset, 168, 68, chara={"stamina": 1}), 4)


# ---------------------------------------------------------------- #2/#4 main.py wiring
class MainWiringTests(unittest.TestCase):
    def test_guest_parents_strict_param_and_login_use(self):
        self.assertIn("def normalize_guest_parents(data, strict=False):", MAIN)
        self.assertIn("normalize_guest_parents(d, strict=True)", MAIN)  # login path
        self.assertIn("normalize_guest_parents(active_dashboard_data, strict=True)", MAIN)  # cache fallback
        # The broad heuristic is gated behind `not strict`.
        self.assertIn("if not strict else []", MAIN)

    def test_new_run_resume_self_heal(self):
        self.assertIn("from career_bot.career_start_recovery import resume_career_fields", MAIN)
        self.assertIn("fields = resume_career_fields(career_status)", MAIN)
        self.assertIn("except Exception as resume_exc:", MAIN)
        self.assertIn("_clear_finished_career_setup_state(clear_selection=False)", MAIN)
        self.assertIn("if result is None:", MAIN)


class ResumeCareerFieldsTests(unittest.TestCase):
    """Behavioral test for the crash-prone resume coercion (issue #4). The bug
    was TypeError: int(None) on a stale/incomplete active career, forcing a bot
    restart. The helper now raises ValueError (-> caller self-heals to a fresh
    start) on a missing card_id, and 0-safe coerces nullable numeric fields."""

    def test_missing_card_id_raises(self):
        for cs in ({"deck_id": 1}, {"card_id": None}, {"card_id": ""}, None):
            with self.assertRaises(ValueError):
                resume_career_fields(cs)

    def test_nullable_numeric_fields_coerce_to_zero_not_crash(self):
        # The exact original crash: int(None) on deck_id / friend / parent ids.
        f = resume_career_fields({"card_id": 1001})
        self.assertEqual(f["deck_id"], 0)
        self.assertEqual(f["friend_viewer_id"], 0)
        self.assertEqual(f["parent_id_1"], 0)
        self.assertEqual(f["card_id"], 1001)
        # Explicit None must not raise.
        f2 = resume_career_fields({"card_id": 1001, "deck_id": None, "friend_viewer_id": None})
        self.assertEqual(f2["deck_id"], 0)

    def test_valid_fields_coerced(self):
        f = resume_career_fields({"card_id": "1001", "deck_id": "3", "friend_viewer_id": 5, "support_card_ids": [1, 2]})
        self.assertEqual(f["card_id"], 1001)
        self.assertEqual(f["deck_id"], 3)
        self.assertEqual(f["support_card_ids"], [1, 2])


# ---------------------------------------------------------------- #1/#3/#5 app.js wiring
class FrontendWiringTests(unittest.TestCase):
    def test_shop_scroll_refreshui_flag(self):
        self.assertIn("async function saveSettingsPreset(current, { refreshUI = true } = {})", APP)
        self.assertIn("if (refreshUI) populatePresetUI();", APP)
        self.assertIn("await saveSettingsPreset(current, { refreshUI: false });", APP)

    def test_energy_toggle_present(self):
        self.assertIn("'skip_energy_items_year_end'", APP)

    def test_per_race_style_ui(self):
        self.assertIn("function perRaceStyleRows(current)", APP)
        self.assertIn("${perRaceStyleRows(current)}", APP)
        self.assertIn("c.per_race_style_overrides = list;", APP)
        self.assertIn("data-control=\"per-race-style\"", APP)


class FinalizeSingleRunsToggleTests(unittest.TestCase):
    """Navbar toggle for the turn-77 finalize fix (#4 follow-up). When ON, single
    (non-loop) runs finish the career instead of self-terminating at turn 77."""

    def test_runner_guard_respects_toggle(self):
        self.assertIn("finalize_single_runs=False", RUNNER)  # start() signature
        self.assertIn("self.finalize_single_runs = bool(finalize_single_runs)", RUNNER)
        self.assertIn('not getattr(self, "finalize_single_runs", False)', RUNNER)
        # Default OFF -> a runner with no flag set keeps the original turn-77 stop.
        r = CareerRunner.__new__(CareerRunner)
        self.assertFalse(getattr(r, "finalize_single_runs", False))

    def test_main_wires_toggle(self):
        self.assertIn("finalize_single_runs: bool = False", MAIN)
        self.assertIn('finalize_single_runs=getattr(req, "finalize_single_runs", False)', MAIN)

    def test_frontend_navbar_toggle(self):
        self.assertIn('id="finalize-runs-btn"', INDEX)
        self.assertIn("function setFinalizeSingleRuns", APP)
        self.assertIn("finalize_single_runs: !!state.finalizeSingleRuns", APP)


if __name__ == "__main__":
    unittest.main()
