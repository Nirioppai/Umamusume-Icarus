"""Regression tests for v6.7.8: shadow-precision gate on the Live
Policy Assistance recommendation.

Before v6.7.8 the recommendation green-lit enablement based on data
sufficiency alone (turn records, race-result coverage, adjustment
count above confidence gate).  A confidently-wrong model could pass
all those checks while still being right only 19% of the time -- the
user observed exactly this with 3108 turn records, 100% coverage, 80
adjustments above 0.65 confidence, and 19% shadow precision.

v6.7.8 adds a precision floor (default 60%) that gates the
ENABLE recommendation once shadow has evaluated enough hints
(default 100) to be statistically meaningful.
"""
import unittest

from career_bot.ai_trainer import live_policy_recommendation


def _healthy_data():
    """Health/policy/config payload that passes every other gate so
    tests can isolate the precision-gate behavior."""
    config = {
        "enable_live_policy_assistance": False,
        "confidence_threshold": 0.65,
        "min_turn_records": 250,
    }
    health = {
        "race_rows": 1057,
        "race_rows_with_result": 1057,
        "race_result_coverage": 1.0,
        "safe_for_live_policy": True,
    }
    policy = {
        "enabled": True,
        "confidence_threshold": 0.65,
        "races": {f"race_{i}": {"adjustment": -0.1} for i in range(40)},
        "items": {f"item_{i}": {"adjustment": 0.05} for i in range(20)},
        "events": {f"event_{i}": {"adjustment": 0.02} for i in range(20)},
    }
    records = {"turn_decisions": 3108}
    return config, health, policy, records


class ShadowPrecisionGateTests(unittest.TestCase):
    def test_low_precision_blocks_enable(self):
        """The user's actual state: 19% precision over 797 evaluated
        hints.  Recommendation must be KEEP DISABLED, not ENABLE."""
        config, health, policy, records = _healthy_data()
        shadow = {"evaluated_races": 797, "precision": 0.19}
        result = live_policy_recommendation(
            config, health, policy, records=records, shadow=shadow,
        )
        self.assertFalse(
            result["recommend_enable"],
            "19% precision must NOT green-light enablement",
        )
        self.assertEqual(result["status"], "recommended_off")
        self.assertIn("precision", result["message"].lower())
        self.assertIn("19%", result["message"])

    def test_high_precision_allows_enable(self):
        """Same data volume but precision now 75% -- recommendation
        flips to ENABLE."""
        config, health, policy, records = _healthy_data()
        shadow = {"evaluated_races": 797, "precision": 0.75}
        result = live_policy_recommendation(
            config, health, policy, records=records, shadow=shadow,
        )
        self.assertTrue(result["recommend_enable"])
        self.assertEqual(result["status"], "recommended_on")
        # Confirm the precision is surfaced in the ENABLE message
        self.assertIn("75%", result["message"])

    def test_insufficient_evaluations_skips_gate(self):
        """When shadow has evaluated fewer than 100 hints, precision
        is too noisy to use as a signal -- the gate must NOT block
        enablement based on precision alone.  Other gates still apply.
        """
        config, health, policy, records = _healthy_data()
        shadow = {"evaluated_races": 50, "precision": 0.10}  # terrible but too few
        result = live_policy_recommendation(
            config, health, policy, records=records, shadow=shadow,
        )
        # Precision gate should NOT add a reason for this case
        precision_reasons = [r for r in result["reasons"] if "precision" in r.lower()]
        self.assertEqual(
            precision_reasons, [],
            "Below min_shadow_evaluations the precision gate must be silent",
        )

    def test_no_shadow_data_does_not_block(self):
        """Missing shadow data (e.g. first run before any shadow eval)
        must not gate the recommendation -- old behavior preserved."""
        config, health, policy, records = _healthy_data()
        result = live_policy_recommendation(
            config, health, policy, records=records,  # shadow=None
        )
        precision_reasons = [r for r in result["reasons"] if "precision" in r.lower()]
        self.assertEqual(precision_reasons, [])

    def test_threshold_is_configurable(self):
        """A deployment can lower (or raise) the floor via
        ``min_shadow_precision`` in the auto config."""
        config, health, policy, records = _healthy_data()
        config["min_shadow_precision"] = 0.40  # accept 40% as good enough
        shadow = {"evaluated_races": 797, "precision": 0.45}
        result = live_policy_recommendation(
            config, health, policy, records=records, shadow=shadow,
        )
        self.assertTrue(
            result["recommend_enable"],
            "With min_shadow_precision lowered to 40%, 45% should pass",
        )

    def test_min_evaluations_is_configurable(self):
        """A deployment can require more (or fewer) evaluations before
        the precision gate activates."""
        config, health, policy, records = _healthy_data()
        config["min_shadow_evaluations"] = 500
        shadow = {"evaluated_races": 200, "precision": 0.10}  # bad but under floor
        result = live_policy_recommendation(
            config, health, policy, records=records, shadow=shadow,
        )
        precision_reasons = [r for r in result["reasons"] if "precision" in r.lower()]
        self.assertEqual(
            precision_reasons, [],
            "200 evaluations is below the configured 500 floor; gate must be silent",
        )

    def test_returned_payload_includes_precision_fields(self):
        """Dashboard/API consumers need the raw precision data exposed
        so they can render it without re-reading the shadow_mode block."""
        config, health, policy, records = _healthy_data()
        shadow = {"evaluated_races": 797, "precision": 0.19}
        result = live_policy_recommendation(
            config, health, policy, records=records, shadow=shadow,
        )
        self.assertEqual(result["shadow_precision"], 0.19)
        self.assertEqual(result["shadow_evaluated_races"], 797)
        self.assertEqual(result["min_shadow_precision"], 0.60)
        self.assertEqual(result["min_shadow_evaluations"], 100)

    def test_backward_compat_no_shadow_kwarg(self):
        """Old call sites that don't pass shadow= must still work."""
        config, health, policy, records = _healthy_data()
        # Old-style call (positional only, no shadow)
        result = live_policy_recommendation(config, health, policy, records=records)
        self.assertIn("recommend_enable", result)
        self.assertIn("shadow_precision", result)
        # When no shadow data is provided the precision field defaults to 0.0
        self.assertEqual(result["shadow_precision"], 0.0)


if __name__ == "__main__":
    unittest.main()
