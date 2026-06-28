"""Regression tests for v6.7.12:

  1. Mandatory race loss no longer crashes the runner.  Finale races
     (turn >= 73) complete the career gracefully; non-finale mandatory
     losses set a clean stop reason instead of raising.

  2. Mandatory races may use paid clocks even when burn_clocks is off
     (a finale loss is catastrophic).  Opt out with
     disable_mandatory_race_clocks.

  3. Stat-target fallback: when the preset's stat_targets_by_distance
     doesn't cover the trainee's race distance, the built-in
     per-distance defaults are used (Medium 800 / Long 1000 stamina)
     instead of the meaningless 9999 sentinel.  This was the cause of
     trainees under-building stamina for Medium/Long races.
"""
import sys
import threading
import unittest
from unittest.mock import MagicMock

sys.modules.setdefault("msgpack", MagicMock())


# --- 1. Mandatory clock rescue -------------------------------------------

class MandatoryClockRescueTests(unittest.TestCase):
    """v6.7.12: a mandatory race may spend paid clocks to avoid a
    catastrophic career-ending loss, even when burn_clocks is off."""

    def _runner(self, *, burn_clocks):
        from career_bot.runner import CareerRunner
        r = CareerRunner.__new__(CareerRunner)
        r.burn_clocks = burn_clocks
        r._race_grade_for_retry = lambda program_id: "G1"
        return r

    def test_mandatory_race_uses_paid_clocks_with_burn_off(self):
        """The user's exact crash scenario: burn_clocks=False, finale
        race lost, 5 paid clocks available.  v6.7.12: the policy must
        now ENABLE the retry (paid-clock rescue) instead of leaving
        the loss to crash the career."""
        runner = self._runner(burn_clocks=False)
        policy = runner._race_retry_policy(
            {"mant_config": {}}, program_id=2510, turn=78, attempts=0,
            free_clocks_available=0,  # no free clocks, but...
            is_mandatory=True,        # mandatory race
        )
        self.assertTrue(policy["enabled"], "mandatory race must enable paid-clock rescue")
        self.assertTrue(policy.get("mandatory_clock_rescue"))
        self.assertEqual(policy["disabled_reason"], "paid_clocks_via_mandatory_rescue")

    def test_optional_graded_race_retries_by_default(self):
        """v1.5: graded optional extra races now retry by default (android
        parity), decoupled from the Burn Clocks toggle, to lift win rate."""
        runner = self._runner(burn_clocks=False)
        policy = runner._race_retry_policy(
            {"mant_config": {}}, program_id=1234, turn=40, attempts=0,
            free_clocks_available=0,
            is_mandatory=False,
        )
        self.assertTrue(policy["enabled"])
        self.assertTrue(policy.get("extra_race_retry"))

    def test_optional_race_blocked_when_extra_retry_disabled(self):
        """Setting retry_extra_races=false restores the old burn_clocks-gated
        behaviour: an optional race with burn off and no free clocks is blocked."""
        runner = self._runner(burn_clocks=False)
        policy = runner._race_retry_policy(
            {"mant_config": {"retry_extra_races": False}}, program_id=1234, turn=40,
            attempts=0, free_clocks_available=0, is_mandatory=False,
        )
        self.assertFalse(policy["enabled"])
        self.assertEqual(policy["disabled_reason"], "burn_clocks_disabled_by_user")

    def test_mandatory_rescue_can_be_disabled(self):
        """Users who never want paid clocks spent can opt out via
        disable_mandatory_race_clocks."""
        runner = self._runner(burn_clocks=False)
        policy = runner._race_retry_policy(
            {"mant_config": {"disable_mandatory_race_clocks": True}},
            program_id=2510, turn=78, attempts=0,
            free_clocks_available=0, is_mandatory=True,
        )
        self.assertFalse(policy["enabled"])

    def test_mandatory_race_respects_grade_filter(self):
        """v2.1 (#30 retry-gating): the grade filter now applies to
        mandatory races too.  A mandatory race whose grade is NOT in
        retry_race_grades is no longer auto-retried -- eligibility gates
        everything, including mandatory races.  (Previously mandatory
        races bypassed the grade filter; that bypass was removed.)"""
        runner = self._runner(burn_clocks=True)
        runner._is_debut_race = lambda program_id, turn: False
        runner._race_grade_for_retry = lambda program_id: "OP"  # not in retry_race_grades
        policy = runner._race_retry_policy(
            {"mant_config": {"retry_race_grades": ["G1"]}},
            program_id=2510, turn=78, attempts=0,
            free_clocks_available=0, is_mandatory=True,
        )
        self.assertFalse(policy["enabled"], "mandatory race outside allowed grades is not retried")
        self.assertEqual(policy["disabled_reason"], "grade_not_allowed")

    def test_mandatory_race_of_allowed_grade_gets_rescue(self):
        """v2.1: a mandatory race WHOSE grade is allowed still gets the
        paid-clock rescue (the live behaviour after #30 retry-gating)."""
        runner = self._runner(burn_clocks=True)
        runner._is_debut_race = lambda program_id, turn: False
        runner._race_grade_for_retry = lambda program_id: "G1"  # in retry_race_grades
        policy = runner._race_retry_policy(
            {"mant_config": {"retry_race_grades": ["G1"]}},
            program_id=2510, turn=78, attempts=0,
            free_clocks_available=0, is_mandatory=True,
        )
        self.assertTrue(policy["enabled"], "mandatory race of an allowed grade is retried")
        self.assertTrue(policy.get("mandatory_clock_rescue"))

    def test_mandatory_rescue_respects_max_retries(self):
        """Even mandatory rescue stops at the per-race retry cap."""
        runner = self._runner(burn_clocks=False)
        policy = runner._race_retry_policy(
            {"mant_config": {"max_retries_per_race": 5}},
            program_id=2510, turn=78, attempts=5,
            free_clocks_available=0, is_mandatory=True,
        )
        self.assertFalse(policy["enabled"])
        self.assertEqual(policy["disabled_reason"], "max_retries_reached")


if __name__ == "__main__":
    unittest.main()
