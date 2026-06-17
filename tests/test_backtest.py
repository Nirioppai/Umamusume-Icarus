"""Tests for the v6.5 training-scorer backtest script.

Verifies the extraction and alignment logic against a synthetic career log
plus the two real career logs from /tmp (if present)."""

from __future__ import annotations

import sys
import unittest
from collections import Counter
from pathlib import Path

# Add scripts/ to path so we can import the backtest module
REPO_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO_ROOT / "scripts"))

import backtest_training_scorer as bt  # noqa: E402


class ExpectedDistributionTests(unittest.TestCase):
    def test_priority_order_produces_decaying_weights(self):
        priority = ["speed", "stamina", "power", "guts", "wit"]
        dist = bt._expected_distribution(priority, 30)
        # Speed (top) > Wit (bottom)
        self.assertGreater(dist["speed"], dist["wit"])
        # Sums to ~total
        self.assertAlmostEqual(sum(dist.values()), 30.0, places=1)
        # Speed gets 5/15 weight
        self.assertAlmostEqual(dist["speed"], 30 * 5 / 15, places=1)

    def test_zero_total_returns_zeros(self):
        dist = bt._expected_distribution(["speed", "stamina"], 0)
        self.assertEqual(sum(dist.values()), 0.0)

    def test_empty_priority_returns_zeros(self):
        dist = bt._expected_distribution([], 30)
        self.assertEqual(sum(dist.values()), 0.0)


class AlignmentTests(unittest.TestCase):
    def test_perfect_alignment(self):
        priority = ["speed", "stamina", "power", "guts", "wit"]
        # Distribution matching expected
        actual = Counter({"speed": 10, "stamina": 8, "power": 6, "guts": 4, "wit": 2})
        expected = bt._expected_distribution(priority, sum(actual.values()))
        score, over, under = bt._alignment(actual, expected)
        self.assertGreater(score, 0.95)
        self.assertEqual(over, [])
        self.assertEqual(under, [])

    def test_over_under_detection(self):
        priority = ["speed", "stamina", "power", "guts", "wit"]
        # Lots of wit, little stamina -- inverted from priority
        actual = Counter({"speed": 10, "stamina": 0, "power": 4, "guts": 0, "wit": 15})
        expected = bt._expected_distribution(priority, sum(actual.values()))
        score, over, under = bt._alignment(actual, expected)
        self.assertLess(score, 0.85)
        self.assertIn("wit", over)


class ExtractionTests(unittest.TestCase):
    def test_command_id_extraction_from_payload(self):
        """Production career_log shape: data.payload.command_id"""
        turns = [
            {"turn": 5, "api_calls": [
                {"direction": "REQ", "endpoint": "single_mode_free/exec_command",
                 "data": {"payload": {"command_type": 1, "command_id": 103}}},
            ]},
            {"turn": 6, "api_calls": [
                {"direction": "REQ", "endpoint": "single_mode_free/exec_command",
                 "data": {"payload": {"command_type": 7, "command_id": 701}}},  # race, not training
            ]},
        ]
        ids = bt._extract_command_ids_executed(turns)
        self.assertEqual(ids, [(5, 103)])

    def test_command_id_extraction_legacy_shape(self):
        """Fallback for hypothetical logs without the payload wrapper."""
        turns = [
            {"turn": 5, "api_calls": [
                {"direction": "REQ", "endpoint": "single_mode_free/exec_command",
                 "data": {"command_type": 1, "command_id": 106}},  # 106 = Wit
            ]},
        ]
        ids = bt._extract_command_ids_executed(turns)
        self.assertEqual(ids, [(5, 106)])

    def test_trainee_extraction(self):
        turns = [
            {"turn": 1, "api_calls": [
                {"direction": "RES", "endpoint": "single_mode_free/check_event",
                 "data": {"response": {"chara_info": {
                     "card_id": 100601, "chara_id": 1006,
                     "trained_chara_name": "Oguri Cap",
                 }}}},
            ]},
        ]
        cid, chid, name = bt._extract_trainee_from_api_calls(turns)
        self.assertEqual(cid, 100601)
        self.assertEqual(chid, 1006)
        self.assertEqual(name, "Oguri Cap")

    def test_final_stats_extraction(self):
        turns = [
            {"turn": 1, "stats": {"speed": 100, "stamina": 50}},
            {"turn": 2, "stats": {"speed": 200, "stamina": 100, "power": 150,
                                  "guts": 80, "wit": 120, "rating": 5500, "fans": 1200}},
        ]
        stats, rating, fans = bt._final_stats(turns)
        self.assertEqual(stats["speed"], 200)
        self.assertEqual(stats["wit"], 120)
        self.assertEqual(rating, 5500)
        self.assertEqual(fans, 1200)


class IntegrationTests(unittest.TestCase):
    def test_backtest_runs_against_real_log_if_present(self):
        """Smoke test against the bot_logs in /tmp if they exist."""
        log_dir = Path("/tmp/uma_runtime/default/bot_logs")
        if not log_dir.exists():
            self.skipTest("No real career_log files available at /tmp")
        log_files = list(log_dir.glob("career_log_*.json"))
        if not log_files:
            self.skipTest("Log directory exists but no career_log_*.json files")
        summary = bt.backtest_one_log(log_files[0], REPO_ROOT)
        self.assertIsNotNone(summary)
        self.assertGreaterEqual(summary.total_trainings, 0)
        self.assertIn(summary.profile_id, ["default", "oguri_cap", "special_week", "tokai_teio", "daiwa_scarlet", "sakura_bakushin_o"])


if __name__ == "__main__":
    unittest.main()
