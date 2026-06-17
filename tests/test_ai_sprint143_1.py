"""Tests for the v5.43.1 calibration wire-in.

Covers:
  - ``race_program_hint`` and ``hierarchical_race_program_hint`` are no-ops
    when no calibrator JSON is present (the common case for a fresh install).
  - When a calibrator IS present, the live ``adjustment`` uses the
    calibrated LCB and the raw values are preserved under ``raw_*`` keys.
  - ``fit_calibrator`` returns helpful messages on the "not enough data"
    and "no dataset yet" paths instead of stack-tracing.
  - End-to-end: fit a calibrator from deliberately miscalibrated data,
    verify ECE improves and the loader picks up the new file.
  - ``calibration_summary`` returns a sensible payload at every stage
    (no data, data without calibrator, calibrator fitted).
"""

from __future__ import annotations

import json
import os
import random
import tempfile
import unittest
from pathlib import Path

from career_bot.ai_advisor import (
    MIN_PREDICTIONS_FOR_CALIBRATION,
    _CALIBRATOR_CACHE,
    calibration_summary,
    calibrator_path,
    fit_calibrator,
    hierarchical_race_program_hint,
    load_calibrator,
    post_run_advice,
    race_program_hint,
)


def _bust_cache():
    _CALIBRATOR_CACHE.update(path=None, mtime=0.0, instance=None)


class CalibrationWireInBase(unittest.TestCase):
    """Shared scaffolding: temp dir with a uma_runtime/ai/ layout that
    runtime_output_root will resolve via UMA_RUNTIME_DIR."""

    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        self.root = Path(self._tmp.name)
        self.runtime = self.root / "uma_runtime"
        self.ai = self.runtime / "ai"
        self.ai.mkdir(parents=True, exist_ok=True)
        self._prior_env = os.environ.get("UMA_RUNTIME_DIR")
        os.environ["UMA_RUNTIME_DIR"] = str(self.runtime)
        _bust_cache()

    def tearDown(self):
        if self._prior_env is None:
            os.environ.pop("UMA_RUNTIME_DIR", None)
        else:
            os.environ["UMA_RUNTIME_DIR"] = self._prior_env
        _bust_cache()
        self._tmp.cleanup()

    def _write_stats(self, payload):
        (self.ai / "advisor_stats.json").write_text(json.dumps(payload), encoding="utf-8")

    def _write_turn_decisions(self, rows):
        path = self.ai / "turn_decisions.jsonl"
        path.write_text("\n".join(json.dumps(r) for r in rows), encoding="utf-8")
        return path


class HintNoCalibratorTests(CalibrationWireInBase):
    """When no calibrator is fitted, hints behave exactly like v5.43."""

    def test_race_program_hint_marks_calibration_inactive(self):
        self._write_stats({"race_programs": {
            "101": {"starts": 10, "wins": 7, "win_rate": 0.7, "avg_reward": 5.0}
        }})
        hint = race_program_hint(self.root, 101)
        self.assertFalse(hint["calibration_active"])
        # The v5.43 fields are unchanged
        self.assertNotIn("raw_adjustment", hint)
        self.assertNotIn("calibrated_mean", hint)
        # adjustment is the raw LCB-based value
        self.assertGreater(hint["adjustment"], 0)

    def test_hierarchical_hint_no_calibrator_path(self):
        self._write_stats({
            "race_programs": {"101": {"starts": 10, "wins": 7, "win_rate": 0.7, "avg_reward": 5.0}},
            "race_programs_context": {
                "by_program": {"101": {"starts": 10, "wins": 7, "win_rate": 0.7, "avg_reward": 5.0}},
                "by_program_scenario": {},
                "by_program_scenario_preset": {},
                "by_program_scenario_preset_phase": {},
            },
        })
        hint = hierarchical_race_program_hint(self.root, 101)
        self.assertFalse(hint["calibration_active"])
        self.assertEqual(hint["contributed_levels"], ["program"])

    def test_load_calibrator_returns_none_when_missing(self):
        self.assertIsNone(load_calibrator(self.root))


class FitCalibratorMessagesTests(CalibrationWireInBase):
    """``fit_calibrator`` never crashes — it returns user-facing messages
    in every failure mode so the dashboard can render them."""

    def test_no_dataset_returns_friendly_message(self):
        result = fit_calibrator(self.root)
        self.assertFalse(result["success"])
        self.assertEqual(result["reason"], "no_dataset")
        self.assertIn("turn_decisions", result["message"])

    def test_insufficient_data_returns_friendly_message(self):
        # Write just a handful of predictions, well below the minimum.
        rows = [{
            "action": {"type": "race", "program_id": 100 + i},
            "decision_report": {"predicted_win_prob": 0.5},
            "outcome": {"race_result": {"rank": 1 if i % 2 == 0 else 3}},
        } for i in range(5)]
        self._write_turn_decisions(rows)
        result = fit_calibrator(self.root, min_predictions=30)
        self.assertFalse(result["success"])
        self.assertEqual(result["reason"], "insufficient_data")
        self.assertIn("5", result["message"])
        self.assertEqual(result["required"], 30)

    def test_uses_module_default_minimum(self):
        # Confirm the module-level constant is what the dashboard would see.
        self.assertGreaterEqual(MIN_PREDICTIONS_FOR_CALIBRATION, 10)


class FitCalibratorEndToEndTests(CalibrationWireInBase):
    """Fit on deliberately miscalibrated data, verify the calibrator
    improves ECE and gets applied automatically on the next hint call."""

    def _miscalibrated_rows(self, n: int, seed: int = 7):
        """Predictions are systematically overconfident: emit p, true rate p^2."""
        rng = random.Random(seed)
        rows = []
        for i in range(n):
            raw = rng.random()
            true_p = raw ** 2
            won = rng.random() < true_p
            rows.append({
                "action": {"type": "race", "program_id": 100 + (i % 5)},
                "decision_report": {"predicted_win_prob": raw},
                "outcome": {"race_result": {"rank": 1 if won else 5}},
            })
        return rows

    def test_fit_improves_ece_and_persists(self):
        self._write_turn_decisions(self._miscalibrated_rows(200))
        result = fit_calibrator(self.root, min_predictions=30)
        self.assertTrue(result["success"], result.get("message"))
        self.assertGreater(result["ece_before"], result["ece_after"])
        # And the file lands at the expected path
        self.assertTrue(calibrator_path(self.root).exists())

    def test_calibrator_auto_loads_on_next_hint(self):
        """The headline behavior: after fit_calibrator, race_program_hint
        immediately reflects the calibration without any explicit reload."""
        self._write_turn_decisions(self._miscalibrated_rows(200))
        # Stats payload that gives a clean Beta(7,3) posterior.
        self._write_stats({"race_programs": {
            "101": {"starts": 10, "wins": 7, "win_rate": 0.7, "avg_reward": 5.0}
        }})

        before_hint = race_program_hint(self.root, 101)
        self.assertFalse(before_hint["calibration_active"])
        raw_adjustment = before_hint["adjustment"]

        fit_result = fit_calibrator(self.root, min_predictions=30)
        self.assertTrue(fit_result["success"])

        after_hint = race_program_hint(self.root, 101)
        self.assertTrue(after_hint["calibration_active"])
        # Raw v5.43 values preserved
        self.assertAlmostEqual(after_hint["raw_adjustment"], raw_adjustment, places=4)
        self.assertIn("calibrated_mean", after_hint)
        self.assertIn("calibrated_lcb", after_hint)
        # On the systematically-overconfident data, the calibrated estimate
        # at posterior_mean=0.7 should be LOWER than the raw value (the model
        # is overstating win chance), pulling the adjustment down.
        self.assertLess(
            after_hint["calibrated_mean"], after_hint["raw_posterior_mean"]
        )

    def test_hierarchical_hint_picks_up_calibration_too(self):
        self._write_turn_decisions(self._miscalibrated_rows(200))
        self._write_stats({
            "race_programs": {"101": {"starts": 10, "wins": 7, "win_rate": 0.7, "avg_reward": 5.0}},
            "race_programs_context": {
                "by_program": {"101": {"starts": 10, "wins": 7, "win_rate": 0.7, "avg_reward": 5.0}},
                "by_program_scenario": {},
                "by_program_scenario_preset": {},
                "by_program_scenario_preset_phase": {},
            },
        })
        fit_calibrator(self.root, min_predictions=30)
        hint = hierarchical_race_program_hint(self.root, 101)
        self.assertTrue(hint["calibration_active"])
        self.assertIn("calibrated_mean", hint)

    def test_cache_busts_when_calibrator_rewritten(self):
        """A non-developer might re-fit after more data accumulates. The
        loader's mtime cache must reflect the new file, not a stale instance."""
        self._write_stats({"race_programs": {
            "101": {"starts": 10, "wins": 7, "win_rate": 0.7, "avg_reward": 5.0}
        }})
        # First fit
        self._write_turn_decisions(self._miscalibrated_rows(200, seed=1))
        fit_calibrator(self.root, min_predictions=30)
        first = race_program_hint(self.root, 101)["calibrated_mean"]

        # Second fit with different data (different seed -> different mapping)
        # ensures the new file has a different mtime and content.
        import time
        time.sleep(0.05)  # force a different mtime on filesystems with 0.01s resolution
        self._write_turn_decisions(self._miscalibrated_rows(200, seed=2))
        fit_calibrator(self.root, min_predictions=30)
        second = race_program_hint(self.root, 101)["calibrated_mean"]

        # The two fits are on different data; they should not produce
        # bit-identical calibrations.  This guards against a stale cache.
        self.assertNotEqual(first, second)


class CalibrationSummaryTests(CalibrationWireInBase):
    """The dashboard payload should be sensible at every lifecycle stage."""

    def test_summary_with_no_data(self):
        summary = calibration_summary(self.root)
        self.assertEqual(summary["predictions"], 0)
        self.assertIsNone(summary["ece"])
        self.assertFalse(summary["calibrator_present"])
        self.assertEqual(summary["reliability_diagram"], [])
        self.assertIn("Not enough", summary["interpretation"])

    def test_summary_with_data_no_calibrator(self):
        rows = [{
            "action": {"type": "race", "program_id": 100},
            "decision_report": {"predicted_win_prob": 0.5},
            "outcome": {"race_result": {"rank": 1 if i % 2 == 0 else 3}},
        } for i in range(40)]
        self._write_turn_decisions(rows)
        summary = calibration_summary(self.root)
        self.assertEqual(summary["predictions"], 40)
        self.assertIsNotNone(summary["ece"])
        self.assertFalse(summary["calibrator_present"])
        self.assertGreater(len(summary["reliability_diagram"]), 0)

    def test_summary_with_fitted_calibrator(self):
        # Use the same miscalibrated generator
        rng = random.Random(5)
        rows = []
        for i in range(200):
            raw = rng.random()
            won = rng.random() < raw ** 2
            rows.append({
                "action": {"type": "race", "program_id": 100 + (i % 5)},
                "decision_report": {"predicted_win_prob": raw},
                "outcome": {"race_result": {"rank": 1 if won else 5}},
            })
        self._write_turn_decisions(rows)
        fit_calibrator(self.root, min_predictions=30)
        summary = calibration_summary(self.root)
        self.assertTrue(summary["calibrator_present"])
        self.assertIsNotNone(summary["calibrator_fitted_at"])
        self.assertEqual(summary["calibrator_predictions_used"], 200)

    def test_post_run_advice_includes_calibration_block(self):
        """post_run_advice now embeds the summary so existing dashboard
        consumers see calibration without an extra endpoint."""
        self._write_stats({"race_programs": {}})
        advice = post_run_advice(self.root)
        self.assertIn("calibration", advice)
        self.assertIn("predictions", advice["calibration"])
        self.assertIn("interpretation", advice["calibration"])


if __name__ == "__main__":
    unittest.main()
