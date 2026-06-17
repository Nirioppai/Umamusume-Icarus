"""Tests for v6.7.21: "Disable Schedule Re-Plan Upon Race Loss" toggle.

Mirrors the Android bot's racing.disableScheduleReplanOnRaceLoss feature.
Default is OFF (re-planning on loss stays the prior behavior). When ON:
  * the race-result re-solve is skipped on a non-1st finish, and
  * the routine every-turn ("live") re-solve reuses the held plan once the
    run has recorded any loss,
so the original schedule is kept instead of being re-planned. The loss is
still recorded elsewhere (_record_race_result), and the "missing" re-solve
(a planned race that vanished this turn) is never gated.

_history_has_loss is exercised directly. The two gate predicates are mirrored
here as specs, since driving the live runner/solver requires a full harness.
"""
import sys
import unittest
from unittest.mock import MagicMock

sys.modules.setdefault("msgpack", MagicMock())

from career_bot.races import RacePlanner


def _solver_setting(preset, key, default):
    """Faithful copy of RacePlanner._solver_setting precedence used by both gates."""
    mant = (preset or {}).get("mant_config") or {}
    v = mant.get(key)
    if v is not None and v != "":
        return v
    tss = (preset or {}).get("trackblazer_solver_settings") or {}
    v = tss.get(key)
    if v is not None and v != "":
        return v
    return default


# Mirror of the runner race-result gate: skip re-solve when lost AND toggle on.
def _race_result_replan_skipped(preset, rank):
    return int(rank or 99) != 1 and bool(
        _solver_setting(preset, "disable_schedule_replan_on_race_loss", False)
    )


# Mirror of the live (every-turn) gate: reuse plan when toggle on AND a loss exists.
def _live_replan_reuses_plan(preset, reason, force, history):
    if reason != "live" or force:
        return False
    if not bool(_solver_setting(preset, "disable_schedule_replan_on_race_loss", False)):
        return False
    return RacePlanner._history_has_loss(history)


def _preset(toggle=None):
    p = {"trackblazer_solver_settings": {}}
    if toggle is not None:
        p["trackblazer_solver_settings"]["disable_schedule_replan_on_race_loss"] = toggle
    return p


class HistoryHasLossTests(unittest.TestCase):
    def test_detects_loss_via_won_false(self):
        self.assertTrue(RacePlanner._history_has_loss([{"won": True}, {"won": False}]))

    def test_detects_loss_via_rank(self):
        self.assertTrue(RacePlanner._history_has_loss([{"rank": 1}, {"rank": 4}]))

    def test_all_wins_is_no_loss(self):
        self.assertFalse(RacePlanner._history_has_loss([{"won": True}, {"rank": 1}]))

    def test_won_true_overrides_missing_rank(self):
        self.assertFalse(RacePlanner._history_has_loss([{"won": True}]))

    def test_empty_and_malformed(self):
        self.assertFalse(RacePlanner._history_has_loss([]))
        self.assertFalse(RacePlanner._history_has_loss(None))
        self.assertFalse(RacePlanner._history_has_loss(["junk", 42, {"rank": "x"}]))


class RaceResultGateTests(unittest.TestCase):
    def test_default_off_replans_on_loss(self):
        # no setting -> default off -> NOT skipped (prior behavior preserved)
        self.assertFalse(_race_result_replan_skipped(_preset(), rank=5))

    def test_on_skips_replan_on_loss(self):
        self.assertTrue(_race_result_replan_skipped(_preset(True), rank=5))

    def test_on_does_not_skip_on_win(self):
        # a 1st-place finish still re-solves even with the toggle on
        self.assertFalse(_race_result_replan_skipped(_preset(True), rank=1))

    def test_off_does_not_skip_on_loss(self):
        self.assertFalse(_race_result_replan_skipped(_preset(False), rank=3))

    def test_setting_via_mant_config_also_honored(self):
        p = {"mant_config": {"disable_schedule_replan_on_race_loss": True}}
        self.assertTrue(_race_result_replan_skipped(p, rank=6))


class LiveReplanGateTests(unittest.TestCase):
    LOSS = [{"won": False}]
    WINS = [{"won": True}]

    def test_default_off_never_reuses(self):
        self.assertFalse(_live_replan_reuses_plan(_preset(), "live", False, self.LOSS))

    def test_on_reuses_after_a_loss(self):
        self.assertTrue(_live_replan_reuses_plan(_preset(True), "live", False, self.LOSS))

    def test_on_does_not_reuse_without_a_loss(self):
        # toggle on but no loss yet -> normal re-solve proceeds
        self.assertFalse(_live_replan_reuses_plan(_preset(True), "live", False, self.WINS))

    def test_missing_reason_never_gated(self):
        # a vanished planned race must still adapt, even with toggle on + loss
        self.assertFalse(_live_replan_reuses_plan(_preset(True), "missing", True, self.LOSS))

    def test_forced_resolve_never_gated(self):
        self.assertFalse(_live_replan_reuses_plan(_preset(True), "live", True, self.LOSS))


if __name__ == "__main__":
    unittest.main()
