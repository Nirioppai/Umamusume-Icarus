"""Regression tests for v6.7.11: the Smart Race Solver Settings UI
panel knobs were not being honored by the runtime planner.  This was
the actual root cause of the user's "race count won't climb above ~30"
issue across many releases -- Max Streak (max_races_in_row) was
silently capped at 2 regardless of what the UI showed.

The bug: ``runner.py`` read solver settings via
``preset.mant_config.X``, but the UI panel writes to
``preset.trackblazer_solver_settings.X``.  These are two different
sub-dicts.  The two never overlapped, so every UI knob in the Smart
Race Solver Settings panel silently did nothing -- the runner used
hardcoded defaults.

Fix verified:
  - ``_solver_setting(preset, key, default)`` returns the first
    non-None value from mant_config / trackblazer_solver_settings /
    default, in that order.
  - ``_solver_aptitude_floor`` handles the letter form (C, S, etc)
    that the UI writes.
  - The five UI knobs (max_races_in_row, fan_bonus, include_op,
    min_aptitude_floor, distance_preference_mode) all flow through.
"""
import sys
import unittest
from unittest.mock import MagicMock

sys.modules.setdefault("msgpack", MagicMock())


class SolverSettingPrecedenceTests(unittest.TestCase):
    """``_solver_setting`` is the new helper that unifies the two
    sources.  Verify every precedence case."""

    def setUp(self):
        from career_bot.runner import CareerRunner
        self.runner = CareerRunner.__new__(CareerRunner)

    def test_mant_config_wins_over_ui(self):
        """An explicit per-preset value in mant_config beats the UI."""
        preset = {
            "mant_config": {"max_races_in_row": 5},
            "trackblazer_solver_settings": {"max_races_in_row": 3},
        }
        self.assertEqual(self.runner._solver_setting(preset, "max_races_in_row", 2), 5)

    def test_ui_setting_used_when_mant_config_missing(self):
        """v6.7.11 main fix: UI knob is honored when mant_config has
        no explicit override.  Previously the runner ignored the UI."""
        preset = {
            "mant_config": {},
            "trackblazer_solver_settings": {"max_races_in_row": 5},
        }
        self.assertEqual(self.runner._solver_setting(preset, "max_races_in_row", 2), 5)

    def test_default_when_both_missing(self):
        """Falls back to the supplied default when nothing is set."""
        preset = {"mant_config": {}, "trackblazer_solver_settings": {}}
        self.assertEqual(self.runner._solver_setting(preset, "max_races_in_row", 2), 2)

    def test_default_when_preset_is_none(self):
        """Safe on a missing preset."""
        self.assertEqual(self.runner._solver_setting(None, "max_races_in_row", 2), 2)

    def test_empty_string_treated_as_unset(self):
        """An empty string from a cleared input field falls through."""
        preset = {
            "mant_config": {"distance_preference_mode": ""},
            "trackblazer_solver_settings": {"distance_preference_mode": "preferred_only"},
        }
        self.assertEqual(
            self.runner._solver_setting(preset, "distance_preference_mode", "balanced"),
            "preferred_only",
        )

    def test_zero_is_a_valid_value(self):
        """Numeric zero (the Fan Bonus default) must NOT be treated as
        unset -- it's a valid user choice."""
        preset = {
            "mant_config": {},
            "trackblazer_solver_settings": {"fan_bonus": 0},
        }
        self.assertEqual(self.runner._solver_setting(preset, "fan_bonus", 999), 0)

    def test_false_is_a_valid_value(self):
        """Boolean False must not collapse to default either."""
        preset = {
            "mant_config": {},
            "trackblazer_solver_settings": {"include_op": False},
        }
        self.assertEqual(self.runner._solver_setting(preset, "include_op", True), False)


class AptitudeFloorResolverTests(unittest.TestCase):
    """``_solver_aptitude_floor`` handles both letter ('C') and int
    ('5') forms of the min aptitude setting."""

    def setUp(self):
        from career_bot.runner import CareerRunner
        self.runner = CareerRunner.__new__(CareerRunner)

    def test_letter_C_converts_to_5(self):
        preset = {"trackblazer_solver_settings": {"min_aptitude_floor": "C"}}
        self.assertEqual(self.runner._solver_aptitude_floor(preset, default_int=6), 5)

    def test_letter_S_converts_to_8(self):
        preset = {"trackblazer_solver_settings": {"min_aptitude_floor": "S"}}
        self.assertEqual(self.runner._solver_aptitude_floor(preset, default_int=6), 8)

    def test_letter_G_converts_to_1(self):
        preset = {"trackblazer_solver_settings": {"min_aptitude_floor": "G"}}
        self.assertEqual(self.runner._solver_aptitude_floor(preset, default_int=6), 1)

    def test_integer_passes_through(self):
        preset = {"trackblazer_solver_settings": {"min_aptitude_floor": 6}}
        self.assertEqual(self.runner._solver_aptitude_floor(preset, default_int=4), 6)

    def test_integer_string_passes_through(self):
        preset = {"trackblazer_solver_settings": {"min_aptitude_floor": "6"}}
        self.assertEqual(self.runner._solver_aptitude_floor(preset, default_int=4), 6)

    def test_invalid_value_falls_back_to_default(self):
        """Garbage values must NOT crash the planner -- fall back to
        the default."""
        preset = {"trackblazer_solver_settings": {"min_aptitude_floor": "not a letter or number"}}
        self.assertEqual(self.runner._solver_aptitude_floor(preset, default_int=6), 6)

    def test_missing_falls_back_to_default(self):
        preset = {"mant_config": {}, "trackblazer_solver_settings": {}}
        self.assertEqual(self.runner._solver_aptitude_floor(preset, default_int=6), 6)


class UserScenarioReproductionTests(unittest.TestCase):
    """Reproduces the exact user state from career_log_20260615_212036
    + smart_solver_config.json: UI knob Max Streak=2, no mant_config
    override, fallback default=2.  After the fix the runner uses the
    UI value (which is still 2 here so race count won't immediately
    jump -- but raising the UI to 5 should now work)."""

    def setUp(self):
        from career_bot.runner import CareerRunner
        self.runner = CareerRunner.__new__(CareerRunner)

    def test_user_preset_with_ui_max_streak_2(self):
        """User's current state: UI shows Max Streak=2, mant_config has
        no override.  Should resolve to 2."""
        preset = {
            "mant_config": {
                "race_chain_target": 5,
                "ignore_consecutive_race_warning": True,
                "irregular_training_min_main_gain": 50,
            },
            "trackblazer_solver_settings": {
                "max_races_in_row": 2,
                "fan_bonus": 0,
                "include_op": False,
                "min_aptitude_floor": "C",
                "distance_preference_mode": "balanced",
            },
        }
        self.assertEqual(self.runner._solver_setting(preset, "max_races_in_row", 2), 2)
        self.assertEqual(self.runner._solver_setting(preset, "fan_bonus", 0), 0)
        self.assertEqual(self.runner._solver_setting(preset, "include_op", False), False)
        self.assertEqual(self.runner._solver_aptitude_floor(preset, default_int=6), 5)
        self.assertEqual(
            self.runner._solver_setting(preset, "distance_preference_mode", "balanced"),
            "balanced",
        )

    def test_user_raising_max_streak_to_5_now_takes_effect(self):
        """The whole point of the v6.7.11 fix: raising the UI Max
        Streak to 5 must actually pass through to the planner."""
        preset = {
            "mant_config": {},
            "trackblazer_solver_settings": {"max_races_in_row": 5},
        }
        self.assertEqual(self.runner._solver_setting(preset, "max_races_in_row", 2), 5)


if __name__ == "__main__":
    unittest.main()
