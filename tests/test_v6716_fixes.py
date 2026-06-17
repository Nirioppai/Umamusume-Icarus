"""Regression tests for v6.7.16: the RUNTIME RE-SOLVE path
(``RacePlanner._replan_smart_schedule``) was reading solver settings
from ``preset.mant_config`` only, defaulting Max Streak back to 2 after
every race.

This was the real cause of the persistent low race count. The v6.7.11
fix patched the INITIAL-plan path in runner.py (so the manual solve and
first plan showed the correct ~37 races at Max Streak 5), but the
re-solve in races.py -- which fires after EVERY race -- still used the
buggy ``cfg.get("max_races_in_row") or 2``. So:

  * Initial plan: Max Streak 5 -> 37 races
  * After race 1: re-solve drops to Max Streak 2 -> ~28-32 races
  * Career finishes at ~28 races regardless of the UI setting

The fix gives RacePlanner the same ``_solver_setting`` /
``_solver_aptitude_floor`` precedence helpers as the runner, so the
re-solve honors the Smart Race Solver Settings UI panel.
"""
import sys
import unittest
from unittest.mock import MagicMock

sys.modules.setdefault("msgpack", MagicMock())


class ReSolveSolverSettingTests(unittest.TestCase):
    def setUp(self):
        from career_bot.races import RacePlanner
        self.rp = RacePlanner.__new__(RacePlanner)

    def test_ui_max_streak_honored_in_resolve(self):
        """The user's exact config: Max Streak 5 set via the UI panel
        (trackblazer_solver_settings), mant_config empty.  The re-solve
        must read 5, NOT default to 2."""
        preset = {
            "mant_config": {},
            "trackblazer_solver_settings": {"max_races_in_row": 5},
        }
        self.assertEqual(self.rp._solver_setting(preset, "max_races_in_row", 2), 5)

    def test_resolve_defaults_to_2_only_when_truly_unset(self):
        """When neither source has it, the default (2) applies."""
        preset = {"mant_config": {}, "trackblazer_solver_settings": {}}
        self.assertEqual(self.rp._solver_setting(preset, "max_races_in_row", 2), 2)

    def test_mant_config_override_wins_in_resolve(self):
        """An explicit mant_config value beats the UI panel."""
        preset = {
            "mant_config": {"max_races_in_row": 8},
            "trackblazer_solver_settings": {"max_races_in_row": 5},
        }
        self.assertEqual(self.rp._solver_setting(preset, "max_races_in_row", 2), 8)

    def test_include_op_honored_in_resolve(self):
        preset = {
            "mant_config": {},
            "trackblazer_solver_settings": {"include_op": True},
        }
        self.assertTrue(self.rp._solver_setting(preset, "include_op", False))

    def test_aptitude_floor_letter_honored_in_resolve(self):
        """The UI saves the floor as a letter ('C'); the re-solve must
        convert it to 5, not default to 6 (B) which is stricter and
        filters more races."""
        preset = {
            "mant_config": {},
            "trackblazer_solver_settings": {"min_aptitude_floor": "C"},
        }
        self.assertEqual(self.rp._solver_aptitude_floor(preset, 6), 5)

    def test_aptitude_floor_falls_back_on_garbage(self):
        preset = {"trackblazer_solver_settings": {"min_aptitude_floor": "???"}}
        self.assertEqual(self.rp._solver_aptitude_floor(preset, 6), 6)

    def test_zero_and_false_are_valid_in_resolve(self):
        """fan_bonus 0 / include_op False must not collapse to default."""
        preset = {"trackblazer_solver_settings": {"fan_bonus": 0, "include_op": False}}
        self.assertEqual(self.rp._solver_setting(preset, "fan_bonus", 99), 0)
        self.assertEqual(self.rp._solver_setting(preset, "include_op", True), False)

    def test_none_preset_safe(self):
        self.assertEqual(self.rp._solver_setting(None, "max_races_in_row", 2), 2)
        self.assertEqual(self.rp._solver_aptitude_floor(None, 6), 6)


class ReSolveParityWithRunnerTests(unittest.TestCase):
    """The re-solve (races.py) and the initial plan (runner.py) must
    now resolve solver settings IDENTICALLY, so the plan doesn't shrink
    after the first race."""

    def setUp(self):
        from career_bot.races import RacePlanner
        from career_bot.runner import CareerRunner
        self.rp = RacePlanner.__new__(RacePlanner)
        self.runner = CareerRunner.__new__(CareerRunner)

    def test_both_paths_agree_on_max_streak(self):
        preset = {
            "mant_config": {},
            "trackblazer_solver_settings": {"max_races_in_row": 5},
        }
        runner_val = self.runner._solver_setting(preset, "max_races_in_row", 2)
        replan_val = self.rp._solver_setting(preset, "max_races_in_row", 2)
        self.assertEqual(runner_val, replan_val)
        self.assertEqual(runner_val, 5)

    def test_both_paths_agree_on_aptitude_floor(self):
        preset = {
            "mant_config": {},
            "trackblazer_solver_settings": {"min_aptitude_floor": "C"},
        }
        self.assertEqual(
            self.runner._solver_aptitude_floor(preset, 6),
            self.rp._solver_aptitude_floor(preset, 6),
        )


if __name__ == "__main__":
    unittest.main()
