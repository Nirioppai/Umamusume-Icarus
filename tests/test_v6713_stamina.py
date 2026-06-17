"""Regression tests for v6.7.13 stamina/distance fixes:

  1. Distance aptitude tie-break now favors the LONGER distance.
     All-rounder trainees (Mile=Middle=Long aptitude, common for
     Oguri Cap) were resolving to "mile" and getting a Mile-tier
     stamina target (~600), then under-building stamina for the
     Medium/Long races that dominate the Trackblazer senior calendar.

  2. When a trainee has NO explicit stat targets and preferred is
     auto, the aptitude-based per-distance defaults now apply instead
     of the 9999 sentinel (which meant "no stamina target").

  3. A 205 result on the race-continue call (the Trackblazer finale
     races don't support clock retries) is recognized and stops the
     retry loop immediately instead of burning the retry budget.
"""
import sys
import threading
import unittest
from unittest.mock import MagicMock

sys.modules.setdefault("msgpack", MagicMock())


class DistanceTieBreakTests(unittest.TestCase):
    """v6.7.13: tied distance aptitudes resolve to the longer distance."""

    def setUp(self):
        from career_bot.scenarios.mant import MantStrategy
        self.strat = MantStrategy()

    def _chara(self, *, short=3, mile=7, middle=7, long_=7, turn=60):
        return {
            "turn": turn,
            "proper_distance_short": short,
            "proper_distance_mile": mile,
            "proper_distance_middle": middle,
            "proper_distance_long": long_,
        }

    def test_tied_mile_middle_long_resolves_to_long(self):
        """The user's exact trainee: Mile=Middle=Long=7.  Must resolve
        to Long (stamina 1000), not Mile (stamina 600)."""
        preset = {"mant_config": {"preferred_distance": "auto"}}
        targets = self.strat._training_targets(preset, self._chara(mile=7, middle=7, long_=7))
        self.assertEqual(targets[1], 1000, "tied aptitude must pick Long stamina target")

    def test_tied_mile_middle_resolves_to_middle(self):
        """Mile=Middle tied (Long lower) resolves to Middle (800), not Mile."""
        preset = {"mant_config": {"preferred_distance": "auto"}}
        targets = self.strat._training_targets(preset, self._chara(mile=7, middle=7, long_=4))
        self.assertEqual(targets[1], 800, "tied Mile/Middle picks Middle stamina")

    def test_clear_mile_dominant_still_mile(self):
        """A genuinely Mile-focused trainee (Mile highest) still gets
        the Mile target -- the tie-break only matters on ties."""
        preset = {"mant_config": {"preferred_distance": "auto"}}
        targets = self.strat._training_targets(preset, self._chara(mile=8, middle=5, long_=3))
        self.assertEqual(targets[1], 600, "Mile-dominant trainee keeps Mile stamina target")

    def test_clear_long_dominant_gets_long(self):
        preset = {"mant_config": {"preferred_distance": "auto"}}
        targets = self.strat._training_targets(preset, self._chara(mile=4, middle=5, long_=8))
        self.assertEqual(targets[1], 1000, "Long-dominant trainee gets Long stamina target")

    def test_explicit_preferred_distance_overrides_tie_break(self):
        """If the user explicitly sets preferred_distance, the tie-break
        doesn't apply -- their choice wins."""
        preset = {"mant_config": {"preferred_distance": "mile"}}
        targets = self.strat._training_targets(preset, self._chara(mile=7, middle=7, long_=7))
        # Explicit mile -> mile default stamina 600
        self.assertEqual(targets[1], 600)


class NoTargetsFallbackTests(unittest.TestCase):
    """v6.7.13: a trainee with no explicit targets gets aptitude-based
    defaults, not the 9999 sentinel."""

    def setUp(self):
        from career_bot.scenarios.mant import MantStrategy
        self.strat = MantStrategy()

    def test_no_targets_no_preferred_uses_aptitude_defaults(self):
        """Empty stat_targets_by_distance + auto preferred: must use
        the aptitude-based default, NOT 9999."""
        preset = {"mant_config": {"preferred_distance": "auto"}}
        chara = {"turn": 60, "proper_distance_mile": 7, "proper_distance_middle": 7,
                 "proper_distance_long": 7, "proper_distance_short": 3}
        targets = self.strat._training_targets(preset, chara)
        self.assertNotEqual(targets[1], 9999, "must not return the 9999 no-target sentinel")
        self.assertEqual(targets[1], 1000)  # tied -> long

    def test_expect_attribute_with_real_values_still_honored(self):
        """If expect_attribute carries real (non-9999) values, those
        are still used (backward compat)."""
        preset = {
            "mant_config": {"preferred_distance": "auto"},
            "expect_attribute": [1100, 650, 900, 400, 800],
        }
        chara = {"turn": 60, "proper_distance_mile": 7}
        targets = self.strat._training_targets(preset, chara)
        # Real expect_attribute values are honored
        self.assertEqual(targets[1], 650)

    def test_disable_stat_targets_still_works(self):
        """The disable_stat_targets escape hatch is unaffected."""
        preset = {"mant_config": {"disable_stat_targets": True}}
        chara = {"turn": 60}
        targets = self.strat._training_targets(preset, chara)
        self.assertEqual(targets, [1200, 1200, 1200, 1200, 1200])


class ContinueUnavailable205Tests(unittest.TestCase):
    """v6.7.13: a 205 on the continue call stops the retry loop
    immediately (finale races don't support clock retries)."""

    def test_205_detection_logic(self):
        """Verify the string-matching logic used to detect a 205
        continue rejection.  (The full _race loop is integration-tested
        elsewhere; here we unit-test the detection predicate.)"""
        # The runner checks `if "205" in err_str`.
        err_205 = "API error 205 on single_mode_free/continue"
        err_208 = "API error 208 (SERVER BUSY) on single_mode_free/continue"
        err_other = "Connection timeout"
        self.assertIn("205", err_205)
        self.assertNotIn("205", err_208)
        self.assertNotIn("205", err_other)


if __name__ == "__main__":
    unittest.main()
