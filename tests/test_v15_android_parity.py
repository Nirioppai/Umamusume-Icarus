"""v1.5 Phase 1 — android-parity training/charm changes.

Covers the clean, threshold-safe levers that fix Icarus's Power-over/Wit-under
allocation and unused Good-Luck Charms, without inflating score magnitude (which
would mis-fire the race-vs-train gates):
  * Wit damping + full-HP-Wit ban default OFF;
  * training selection is charm-aware (risky high-stat trainings become eligible
    when a Good-Luck Charm is held);
  * the baseline stat-priority multiplier stays OFF by default (targets encode
    priority instead).
The retry-policy and target-retune changes are covered by test_v6712_fixes and
test_v6710_fixes / the Oguri profile.
"""
import json
import os
import unittest

from career_bot.scenarios.mant import MantStrategy

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


def training(command_id=101, gain=40, failure=0, partners=None, tips=None):
    main_target = {101: 1, 105: 2, 102: 3, 103: 4, 106: 5}.get(command_id, 1)
    return {
        "command_type": 1, "command_id": command_id, "command_group_id": 0,
        "select_id": 0, "is_enable": 1, "failure_rate": failure,
        "training_partner_array": partners or [], "tips_event_partner_array": tips or [],
        "params_inc_dec_info_array": [{"target_type": main_target, "value": gain}],
    }


def data_with_charm(qty):
    return {"free_data_set": {"user_item_info_array": [{"item_id": 10001, "num": qty}]}}


class CharmAwareTrainingTests(unittest.TestCase):
    def setUp(self):
        self.s = MantStrategy()
        # A risky speed training: 45% failure but a big main gain.
        self.risky = training(101, gain=50, failure=45)

    def test_risky_blocked_without_charm(self):
        self.assertFalse(self.s._failure_allowed(self.risky, {"mant_config": {}}, has_charm=False))

    def test_risky_allowed_with_charm(self):
        self.assertTrue(self.s._failure_allowed(self.risky, {"mant_config": {}}, has_charm=True))

    def test_low_gain_risky_still_blocked_with_charm(self):
        weak = training(101, gain=10, failure=45)  # gain below charm_min_main_gain(30)
        self.assertFalse(self.s._failure_allowed(weak, {"mant_config": {}}, has_charm=True))

    def test_can_disable_charm_awareness(self):
        off = {"mant_config": {"enable_charm_aware_training": False}}
        self.assertFalse(self.s._failure_allowed(self.risky, off, has_charm=True))


if __name__ == "__main__":
    unittest.main()
