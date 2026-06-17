"""Regression tests for v6.7.15: the training-target distance is now
derived from the solver's ACTUAL scheduled race list, not from the
trainee's aptitude.

Motivation: a trainee can have Long aptitude A (e.g. Oguri Cap after a
parent Long spark) yet race only Mile/Medium because that's what the
solver scheduled for fans/epithets. v6.7.14's aptitude tie-break
resolved such a trainee to "long" and built a Long stamina target
(~1000) it never used, wasting training turns. v6.7.15 reads the
scheduled races instead: 14 Mile + 12 Medium -> "middle" (stamina
~800), never "long" since no Long races are scheduled.

The aptitude tie-break remains the fallback when no schedule is
available (manual mode / before first solve).
"""
import sys
import unittest
from unittest.mock import MagicMock

sys.modules.setdefault("msgpack", MagicMock())


def _fake_planner(bucket_fn):
    """Build a stand-in race_planner exposing just _distance_bucket."""
    class _RP:
        def _distance_bucket(self, pid):
            return bucket_fn(int(pid))
    return _RP()


class ScheduledDistanceTargetTests(unittest.TestCase):
    """``_scheduled_distance_target`` picks the longest meaningfully
    represented distance from the scheduled race list."""

    def setUp(self):
        from career_bot.scenarios.mant import MantStrategy
        self.strat = MantStrategy()

    def test_mile_and_medium_schedule_resolves_to_middle(self):
        """The user's exact case: 14 Mile + 12 Medium, zero Long.
        Must resolve to 'middle', not 'long'."""
        self.strat.race_planner = _fake_planner(
            lambda pid: "mile" if pid < 200 else "middle"
        )
        preset = {"extra_race_list": list(range(100, 114)) + list(range(200, 212))}
        self.assertEqual(self.strat._scheduled_distance_target(preset), "middle")

    def test_no_schedule_returns_none(self):
        """No extra_race_list -> None (caller falls back to aptitude)."""
        self.strat.race_planner = _fake_planner(lambda pid: "mile")
        self.assertIsNone(self.strat._scheduled_distance_target({"extra_race_list": []}))
        self.assertIsNone(self.strat._scheduled_distance_target({}))

    def test_no_planner_returns_none(self):
        """No race_planner -> None."""
        self.strat.race_planner = None
        self.assertIsNone(
            self.strat._scheduled_distance_target({"extra_race_list": [1, 2, 3]})
        )

    def test_substantial_long_block_resolves_to_long(self):
        """8 Medium + 6 Long: the Long block crosses the threshold, so
        the target rises to Long."""
        self.strat.race_planner = _fake_planner(
            lambda pid: "middle" if pid < 300 else "long"
        )
        preset = {"extra_race_list": list(range(200, 208)) + list(range(300, 306))}
        self.assertEqual(self.strat._scheduled_distance_target(preset), "long")

    def test_single_outlier_long_does_not_drag_target(self):
        """20 Mile + 1 Long: the lone Long race is below threshold, so
        the target stays Mile (don't over-build for one outlier)."""
        self.strat.race_planner = _fake_planner(
            lambda pid: "long" if pid == 999 else "mile"
        )
        preset = {"extra_race_list": list(range(100, 120)) + [999]}
        self.assertEqual(self.strat._scheduled_distance_target(preset), "mile")

    def test_three_medium_meets_minimum_threshold(self):
        """Exactly 3 of a distance meets the floor (>=3), even if below
        20%."""
        self.strat.race_planner = _fake_planner(
            lambda pid: "middle" if pid >= 200 else "mile"
        )
        # 5 mile + 3 medium = 8 total; 20% = 1.6 -> floor max(3, 1) = 3
        preset = {"extra_race_list": list(range(100, 105)) + list(range(200, 203))}
        # Longest bucket with >=3: middle has exactly 3
        self.assertEqual(self.strat._scheduled_distance_target(preset), "middle")

    def test_sprint_alias_normalized_to_short(self):
        """A planner returning 'sprint' is normalized to 'short'."""
        self.strat.race_planner = _fake_planner(lambda pid: "sprint")
        preset = {"extra_race_list": list(range(100, 105))}
        self.assertEqual(self.strat._scheduled_distance_target(preset), "short")


class TrainingTargetsUsesScheduleTests(unittest.TestCase):
    """End-to-end: ``_training_targets`` uses the schedule-derived
    distance, overriding the aptitude tie-break."""

    def setUp(self):
        from career_bot.scenarios.mant import MantStrategy
        self.strat = MantStrategy()

    def _tied_apt_chara(self, turn=60):
        # Mile = Middle = Long all A (7) -- the all-rounder case
        return {
            "turn": turn,
            "proper_distance_short": 3,
            "proper_distance_mile": 7,
            "proper_distance_middle": 7,
            "proper_distance_long": 7,
        }

    def test_schedule_overrides_aptitude_tie_break(self):
        """Tied A aptitude (would tie-break to Long) but a Mile/Medium
        schedule -> Medium stamina target (800), NOT Long (1000)."""
        self.strat.race_planner = _fake_planner(
            lambda pid: "mile" if pid < 200 else "middle"
        )
        preset = {
            "mant_config": {"preferred_distance": "auto"},
            "extra_race_list": list(range(100, 114)) + list(range(200, 212)),
        }
        targets = self.strat._training_targets(preset, self._tied_apt_chara())
        self.assertEqual(targets[1], 800, "should use Medium target from schedule")
        self.assertNotEqual(targets[1], 1000, "must NOT use Long target from aptitude")

    def test_no_schedule_falls_back_to_aptitude(self):
        """Without a schedule, the aptitude tie-break still applies
        (tied A -> Long)."""
        self.strat.race_planner = _fake_planner(lambda pid: "")
        preset = {"mant_config": {"preferred_distance": "auto"}}  # no extra_race_list
        targets = self.strat._training_targets(preset, self._tied_apt_chara())
        self.assertEqual(targets[1], 1000, "aptitude fallback: tied -> Long")

    def test_explicit_preset_target_still_wins_over_schedule(self):
        """An explicit stat_targets_by_distance entry for the scheduled
        distance still takes precedence over the default."""
        self.strat.race_planner = _fake_planner(
            lambda pid: "mile" if pid < 200 else "middle"
        )
        preset = {
            "mant_config": {
                "preferred_distance": "auto",
                "stat_targets_by_distance": {"medium": [1150, 900, 1050, 400, 1000]},
            },
            "extra_race_list": list(range(100, 114)) + list(range(200, 212)),
        }
        targets = self.strat._training_targets(preset, self._tied_apt_chara())
        # Schedule -> middle; explicit medium target stamina 900 wins
        self.assertEqual(targets[1], 900)


if __name__ == "__main__":
    unittest.main()
