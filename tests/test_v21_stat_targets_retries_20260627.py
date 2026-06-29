"""v2.1 (2026-06-27): global stat targets + retries-modal controls.

Feature 1 — global stat target overrides per-distance targets in
MantTrackblazerCore._phase_targets when enable_global_stat_target is on.

Feature 3 — runner retry policy honors two runtime controls:
  * clocks_g1_debut_only: when True, only Debut + G1 + CLIMAX races may retry
    (G2/G3/OP and grade-unknown extra races are blocked, overriding the
    extra-race/mandatory rescue branches).
  * max_retries_per_race: runtime cap (>=0 wins over the preset; 0 = no
    retries; -1 sentinel = "not set, use preset/default 5").
"""
import threading
import sys
import unittest
from unittest.mock import MagicMock

for _m in ("msgpack",):
    sys.modules.setdefault(_m, MagicMock())

from career_bot.runner import CareerRunner
from career_bot.scenarios.mant import MantStrategy
from career_bot.scenarios.mant_trackblazer import STAT_CAP, DEFAULT_TARGETS


# ---------------------------------------------------------------------------
# Feature 1: global stat targets
# ---------------------------------------------------------------------------
def _core():
    return MantStrategy()._trackblazer_core()


def _chara_mile():
    # highest aptitude = mile
    return {
        "proper_distance_short": 1,
        "proper_distance_mile": 7,
        "proper_distance_middle": 1,
        "proper_distance_long": 1,
    }


class GlobalStatTargetTests(unittest.TestCase):
    def test_global_target_overrides_distance_when_enabled(self):
        core = _core()
        preset = {"mant_config": {
            "enable_global_stat_target": True,
            "global_stat_target": [1100, 1100, 1100, 1100, 1100],
            "stat_targets_by_distance": {"mile": [900, 900, 900, 900, 900]},
        }}
        # year 2 = no milestone phasing -> base returned verbatim
        self.assertEqual(core._phase_targets(_chara_mile(), preset, 2),
                         [1100, 1100, 1100, 1100, 1100])

    def test_distance_target_used_when_global_disabled(self):
        core = _core()
        preset = {"mant_config": {
            "enable_global_stat_target": False,
            "global_stat_target": [1100, 1100, 1100, 1100, 1100],
            "stat_targets_by_distance": {"mile": [900, 900, 900, 900, 900]},
        }}
        self.assertEqual(core._phase_targets(_chara_mile(), preset, 2),
                         [900, 900, 900, 900, 900])

    def test_global_target_respects_milestone_phasing(self):
        core = _core()
        preset = {"mant_config": {
            "enable_global_stat_target": True,
            "global_stat_target": [1000, 1000, 1000, 1000, 1000],
            "classic_year_milestone_pct": 50,
        }}
        # year 0 = classic -> 50% of the global target
        self.assertEqual(core._phase_targets(_chara_mile(), preset, 0),
                         [500, 500, 500, 500, 500])

    def test_disable_stat_targets_still_wins_over_global(self):
        core = _core()
        preset = {"mant_config": {
            "enable_global_stat_target": True,
            "global_stat_target": [800, 800, 800, 800, 800],
            "disable_stat_targets": True,
        }}
        self.assertEqual(core._phase_targets(_chara_mile(), preset, 2),
                         [STAT_CAP] * 5)

    def test_invalid_global_target_falls_back_to_distance(self):
        core = _core()
        preset = {"mant_config": {
            "enable_global_stat_target": True,
            "global_stat_target": [1100, 1100],  # wrong length -> ignored
        }}
        # falls back to DEFAULT_TARGETS[mile] (no per-distance override given)
        self.assertEqual(core._phase_targets(_chara_mile(), preset, 2),
                         list(DEFAULT_TARGETS["mile"]))


# ---------------------------------------------------------------------------
# Feature 3: retries policy controls
# ---------------------------------------------------------------------------
def _runner(*, burn=True, g1_only=False, max_per_race=-1, grade="G1", debut=False):
    r = CareerRunner.__new__(CareerRunner)
    r.lock = threading.RLock()
    r.burn_clocks = burn
    r.clocks_g1_debut_only = g1_only
    r.max_retries_per_race = max_per_race
    r._race_grade_for_retry = lambda pid: grade
    r._is_debut_race = lambda pid, turn: debut
    r._load_non_retryable = lambda: set()
    return r


class G1DebutOnlyToggleTests(unittest.TestCase):
    def test_off_allows_unknown_grade_extra_race(self):
        # grade unknown ("") + retry_extra_races default True -> retries today
        r = _runner(g1_only=False, grade="")
        pol = r._race_retry_policy({}, 100, 30, 0)
        self.assertTrue(pol["enabled"])

    def test_on_blocks_unknown_grade_extra_race(self):
        r = _runner(g1_only=True, grade="")
        pol = r._race_retry_policy({}, 100, 30, 0)
        self.assertFalse(pol["enabled"])
        self.assertEqual(pol["disabled_reason"], "clocks_g1_debut_only")

    def test_on_blocks_g2(self):
        r = _runner(g1_only=True, grade="G2")
        pol = r._race_retry_policy({}, 100, 30, 0)
        self.assertFalse(pol["enabled"])

    def test_on_allows_g1(self):
        r = _runner(g1_only=True, grade="G1")
        pol = r._race_retry_policy({}, 100, 30, 0)
        self.assertTrue(pol["enabled"])

    def test_on_keeps_climax_finale_retryable(self):
        r = _runner(g1_only=True, grade="CLIMAX")
        pol = r._race_retry_policy({}, 100, 30, 0)
        self.assertTrue(pol["enabled"])

    def test_on_allows_debut_regardless_of_grade(self):
        r = _runner(g1_only=True, grade="", debut=True)
        pol = r._race_retry_policy({}, 100, 30, 0)
        self.assertTrue(pol["enabled"])


class MaxRetriesPerRaceTests(unittest.TestCase):
    def test_runtime_zero_means_no_retries(self):
        r = _runner(max_per_race=0, grade="G1")
        pol = r._race_retry_policy({}, 100, 30, 0)
        self.assertFalse(pol["enabled"])
        self.assertEqual(pol["disabled_reason"], "max_retries_reached")

    def test_runtime_cap_blocks_at_limit(self):
        r = _runner(max_per_race=2, grade="G1")
        self.assertTrue(r._race_retry_policy({}, 100, 30, 1)["enabled"])
        self.assertFalse(r._race_retry_policy({}, 100, 30, 2)["enabled"])

    def test_sentinel_falls_back_to_default_five(self):
        r = _runner(max_per_race=-1, grade="G1")
        self.assertTrue(r._race_retry_policy({}, 100, 30, 4)["enabled"])
        self.assertFalse(r._race_retry_policy({}, 100, 30, 5)["enabled"])

    def test_preset_value_used_when_no_runtime_override(self):
        r = _runner(max_per_race=-1, grade="G1")
        pol = r._race_retry_policy({"mant_config": {"max_retries_per_race": 1}}, 100, 30, 1)
        self.assertFalse(pol["enabled"])


if __name__ == "__main__":
    unittest.main()
