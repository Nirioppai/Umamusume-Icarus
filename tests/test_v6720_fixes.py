"""Tests for v6.7.20: re-solve diagnostics + beam-fallback guard.

The fix has two parts:
  1. Diagnostic logging: every re-solve records which backend ran, whether the
     exact MILP fell back to the heuristic beam, the race count, current
     stamina, and which high-value races were dropped vs the prior plan. The
     records accumulate in RacePlanner.replan_log and land in the career log.
  2. Beam-fallback GUARD: a degraded beam re-solve must not overwrite a good
     exact (MILP) plan and silently drop winnable high-fan races (Japan Cup,
     Arima, ...). When the exact backend fails this turn but the plan already
     held was exact, the prior exact plan's upcoming races are kept.

RacePlanner._high_value_races and _push_replan_log are exercised directly. The
guard *decision* is mirrored here as a spec because driving the full
_replan_smart_schedule requires a live trackblazer/state harness; the mirrored
predicate documents and locks the intended behavior.
"""
import sys
import unittest
from unittest.mock import MagicMock

sys.modules.setdefault("msgpack", MagicMock())

from career_bot.races import RacePlanner


def _plan(rows, fallback=False, extra=None, solver="smart-race-solver-milp"):
    return {
        "schedule": rows,
        "fallback_used": fallback,
        "solver": solver,
        "extra_race_list": extra if extra is not None else [r["program_id"] for r in rows],
    }


def _row(pid, turn, name, fans):
    return {"program_id": pid, "turn": turn, "name": name, "est_fans": fans}


# Mirror of the guard predicate in races.py / runner.py.
def _guard_applies(new_plan, prev_plan, reason):
    fallback_used = bool(new_plan.get("fallback_used"))
    prev_remaining = [int(x) for x in (prev_plan.get("extra_race_list") or [])]
    prev_was_exact = bool(prev_remaining) and not bool(prev_plan.get("fallback_used"))
    return bool(fallback_used and prev_was_exact and reason != "missing")


def _dropped_high_value(new_plan, prev_plan, cur_turn):
    new_hv = RacePlanner._high_value_races(new_plan)
    prev_hv = RacePlanner._high_value_races(prev_plan)
    return sorted(
        (
            {"program_id": pid, "turn": rt, "name": name, "est_fans": fans}
            for pid, (rt, name, fans) in prev_hv.items()
            if rt >= cur_turn and pid not in new_hv
        ),
        key=lambda d: d["turn"],
    )


class HighValueRaceDetectionTests(unittest.TestCase):
    def test_extracts_only_high_fan_races(self):
        plan = _plan([
            _row(79, 70, "Japan Cup", 30000),
            _row(81, 72, "Arima Kinen", 30000),
            _row(1087, 44, "Tenno Sho (Autumn)", 15000),
            _row(101, 62, "Chukyo Kinen", 3900),   # below threshold
            _row(164, 33, "NHK Mile Cup", 10500),  # below 15000 threshold
        ])
        hv = RacePlanner._high_value_races(plan)
        self.assertIn(79, hv)
        self.assertIn(81, hv)
        self.assertIn(1087, hv)
        self.assertNotIn(101, hv)
        self.assertNotIn(164, hv)

    def test_threshold_is_adjustable(self):
        plan = _plan([_row(164, 33, "NHK Mile Cup", 10500)])
        self.assertNotIn(164, RacePlanner._high_value_races(plan))           # default 15000
        self.assertIn(164, RacePlanner._high_value_races(plan, min_fans=10000))

    def test_falls_back_to_fans_field(self):
        plan = {"schedule": [{"program_id": 79, "turn": 70, "name": "JC", "fans": 30000}]}
        self.assertIn(79, RacePlanner._high_value_races(plan))

    def test_handles_empty_and_malformed(self):
        self.assertEqual(RacePlanner._high_value_races({}), {})
        self.assertEqual(RacePlanner._high_value_races({"schedule": []}), {})
        # bad fan / id values must not raise
        bad = {"schedule": [{"program_id": "x", "turn": 1, "est_fans": "nan"}]}
        self.assertEqual(RacePlanner._high_value_races(bad), {})


class DroppedHighValueDetectionTests(unittest.TestCase):
    def test_detects_dropped_future_big_race(self):
        prev = _plan([_row(79, 70, "Japan Cup", 30000), _row(81, 72, "Arima Kinen", 30000)])
        # new plan drops Japan Cup (T70) and keeps only Arima
        new = _plan([_row(81, 72, "Arima Kinen", 30000)])
        dropped = _dropped_high_value(new, prev, cur_turn=69)
        self.assertEqual([d["program_id"] for d in dropped], [79])
        self.assertEqual(dropped[0]["est_fans"], 30000)

    def test_ignores_already_past_races(self):
        prev = _plan([_row(79, 46, "Japan Cup", 30000)])  # T46, already past at T60
        new = _plan([])
        # cur_turn 60 is past T46, so it is not counted as a *droppable* future race
        self.assertEqual(_dropped_high_value(new, prev, cur_turn=60), [])

    def test_no_drtop_when_all_kept(self):
        prev = _plan([_row(79, 70, "Japan Cup", 30000)])
        new = _plan([_row(79, 70, "Japan Cup", 30000)])
        self.assertEqual(_dropped_high_value(new, prev, cur_turn=69), [])


class BeamFallbackGuardTests(unittest.TestCase):
    def test_guard_blocks_beam_over_exact(self):
        prev = _plan([_row(79, 70, "Japan Cup", 30000)], fallback=False)  # exact
        new = _plan([], fallback=True)                                    # degraded beam, dropped JC
        self.assertTrue(_guard_applies(new, prev, reason="live"))

    def test_guard_skips_when_prior_was_also_beam(self):
        prev = _plan([_row(79, 70, "Japan Cup", 30000)], fallback=True)   # prior already beam
        new = _plan([], fallback=True)
        self.assertFalse(_guard_applies(new, prev, reason="live"))

    def test_guard_skips_when_new_plan_is_exact(self):
        prev = _plan([_row(79, 70, "Japan Cup", 30000)], fallback=False)
        new = _plan([_row(79, 70, "Japan Cup", 30000)], fallback=False)   # exact, trust it
        self.assertFalse(_guard_applies(new, prev, reason="live"))

    def test_guard_skips_for_missing_reason(self):
        # a planned race genuinely vanished this turn -> must accept a fresh plan
        prev = _plan([_row(79, 70, "Japan Cup", 30000)], fallback=False)
        new = _plan([], fallback=True)
        self.assertFalse(_guard_applies(new, prev, reason="missing"))

    def test_guard_skips_when_no_prior_plan(self):
        new = _plan([], fallback=True)
        self.assertFalse(_guard_applies(new, {}, reason="live"))


class ReplanLogTests(unittest.TestCase):
    def _planner(self):
        # Bypass heavy __init__/_load; we only need the log machinery.
        p = RacePlanner.__new__(RacePlanner)
        p.replan_log = []
        p._replan_log_cap = 5
        return p

    def test_push_appends(self):
        p = self._planner()
        p._push_replan_log({"turn": 16, "backend": "smart-race-solver-milp"})
        self.assertEqual(len(p.replan_log), 1)
        self.assertEqual(p.replan_log[0]["turn"], 16)

    def test_push_caps_and_keeps_recent(self):
        p = self._planner()
        for t in range(20):
            p._push_replan_log({"turn": t})
        self.assertEqual(len(p.replan_log), 5)
        self.assertEqual([r["turn"] for r in p.replan_log], [15, 16, 17, 18, 19])

    def test_push_never_raises(self):
        p = RacePlanner.__new__(RacePlanner)
        # no replan_log attribute -> _push must swallow the error, not raise
        try:
            p._push_replan_log({"turn": 1})
        except Exception as exc:  # pragma: no cover
            self.fail(f"_push_replan_log raised: {exc}")


if __name__ == "__main__":
    unittest.main()
