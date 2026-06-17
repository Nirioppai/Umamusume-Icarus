"""Tests for v6.7.22: Android-style event-driven re-planning + carry-in streak.

Two fixes, both aimed at the "raced 12 in a row with Max Streak 5" bug:

  1. Carry-in streak seeding. A forward-only re-solve used to reset its streak
     counter to 0, so races already run just before the re-solve weren't counted
     and consecutive races piled up past max_races_in_row. The solver now counts
     the carry-in and keeps the streak correct across the re-solve boundary
     (MILP boundary constraint + beam seed).

  2. Event-driven re-planning (default ON). The routine every-turn "live"
     re-solve is skipped (plan solved once and reused); a WON race no longer
     triggers a re-solve. Only a loss (unless suppressed) or a vanished planned
     race re-solves -- matching the Android bot.

The carry-in is verified functionally against the real solver (base_dir=".").
The event-driven gates are mirrored as specs.
"""
import sys
import unittest
from unittest.mock import MagicMock

sys.modules.setdefault("msgpack", MagicMock())

from career_bot import trackblazer as tb
from career_bot.races import RacePlanner


APT = {"turf": "A", "dirt": "A", "sprint": "A", "mile": "A", "medium": "A",
       "long": "A", "front": "A", "pace": "A", "late": "A", "end": "A"}


class CarryInHelperTests(unittest.TestCase):
    def test_counts_consecutive_races_before_start(self):
        hist = [{"turn": t} for t in (45, 46, 47, 48, 49)]
        self.assertEqual(tb._carry_in_race_streak(hist, 50), 5)

    def test_stops_at_a_gap(self):
        # raced 47,48,49 but NOT 46 -> carry-in into turn 50 is 3
        hist = [{"turn": t} for t in (44, 47, 48, 49)]
        self.assertEqual(tb._carry_in_race_streak(hist, 50), 3)

    def test_zero_when_prev_turn_not_raced(self):
        hist = [{"turn": t} for t in (45, 46, 47)]  # last race T47, gap at T48/49
        self.assertEqual(tb._carry_in_race_streak(hist, 50), 0)

    def test_empty_and_malformed(self):
        self.assertEqual(tb._carry_in_race_streak([], 50), 0)
        self.assertEqual(tb._carry_in_race_streak(None, 50), 0)
        self.assertEqual(tb._carry_in_race_streak([{"x": 1}, "junk"], 50), 0)

    def test_accepts_turnNumber_key(self):
        hist = [{"turnNumber": t} for t in (48, 49)]
        self.assertEqual(tb._carry_in_race_streak(hist, 50), 2)


def _longest_streak(plan, carry_turns):
    sched = plan.get("schedule") or []
    start = min(carry_turns) if carry_turns else 50
    race_turns = set(int(r["turn"]) for r in sched if int(r.get("turn") or 0) >= 50)
    allt = set(carry_turns) | race_turns
    longest = run = 0
    for t in range(start, 73):
        run = run + 1 if t in allt else 0
        longest = max(longest, run)
    return longest


class CarryInSolverTests(unittest.TestCase):
    """End-to-end: the real solver must not exceed max_races_in_row across the
    re-solve boundary once carry-in is accounted for."""

    def _solve(self, backend, hist, start=50, streak=5):
        return tb.make_schedule(".", aptitudes=APT, max_races_in_row=streak,
                                solver=backend, current_turn=start, race_history=hist,
                                weights={"currentTurn": start, "allowSummerRacing": True})

    def test_milp_respects_carry_in(self):
        hist = [{"turn": t, "won": True} for t in range(45, 50)]  # carry-in 5
        plan = self._solve("smart", hist)
        self.assertLessEqual(_longest_streak(plan, range(45, 50)), 5)

    def test_beam_respects_carry_in(self):
        hist = [{"turn": t, "won": True} for t in range(45, 50)]
        plan = self._solve("beam", hist)
        self.assertLessEqual(_longest_streak(plan, range(45, 50)), 5)

    def test_partial_carry_in_still_allows_some_races(self):
        # carry-in of 2 -> may race up to 3 more before a break
        hist = [{"turn": t, "won": True} for t in (48, 49)]
        plan = self._solve("smart", hist)
        self.assertLessEqual(_longest_streak(plan, (48, 49)), 5)

    def test_no_carry_in_unaffected(self):
        plan = self._solve("smart", [])
        self.assertLessEqual(_longest_streak(plan, []), 5)


# ---- Event-driven gate specs (mirror races.py / runner.py predicates) ----
def _solver_setting(preset, key, default):
    mant = (preset or {}).get("mant_config") or {}
    v = mant.get(key)
    if v is not None and v != "":
        return v
    tss = (preset or {}).get("trackblazer_solver_settings") or {}
    v = tss.get(key)
    if v is not None and v != "":
        return v
    return default


def _live_reuses_plan(preset, reason, force, has_plan):
    if reason != "live" or force:
        return False
    if not bool(_solver_setting(preset, "replan_on_events_only", True)):
        return False
    return bool(has_plan)


def _win_resolve_skipped(preset, rank):
    return int(rank or 99) == 1 and bool(_solver_setting(preset, "replan_on_events_only", True))


def _preset(events_only=None):
    p = {"trackblazer_solver_settings": {}}
    if events_only is not None:
        p["trackblazer_solver_settings"]["replan_on_events_only"] = events_only
    return p


class EventDrivenLiveGateTests(unittest.TestCase):
    def test_default_on_reuses_plan_on_live(self):
        self.assertTrue(_live_reuses_plan(_preset(), "live", False, has_plan=True))

    def test_no_reuse_when_no_plan_yet(self):
        # first solve must still happen
        self.assertFalse(_live_reuses_plan(_preset(), "live", False, has_plan=False))

    def test_off_does_not_reuse(self):
        self.assertFalse(_live_reuses_plan(_preset(False), "live", False, has_plan=True))

    def test_missing_reason_never_gated(self):
        self.assertFalse(_live_reuses_plan(_preset(True), "missing", True, has_plan=True))


class EventDrivenWinGateTests(unittest.TestCase):
    def test_default_on_skips_resolve_on_win(self):
        self.assertTrue(_win_resolve_skipped(_preset(), rank=1))

    def test_does_not_skip_on_loss(self):
        self.assertFalse(_win_resolve_skipped(_preset(), rank=5))

    def test_off_does_not_skip_on_win(self):
        self.assertFalse(_win_resolve_skipped(_preset(False), rank=1))


if __name__ == "__main__":
    unittest.main()
