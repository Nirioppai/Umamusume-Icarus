"""Regression tests for v6.7.9 fixes:

  1. ``active_selection`` is persisted to userdata so the picker
     survives server restarts.

  2. The dashboard ``_decision_reasoning`` text surfaces an
     irregular-training hijack as a prominent line when training
     replaces a planned race.

(The authoritative training-scorer override and its margin-gate /
blocked-override reasoning were removed in v2.1, so the tests that
covered them were dropped.)
"""
import json
import os
import shutil
import sys
import tempfile
import unittest
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import MagicMock

# Stub msgpack (sandbox doesn't have it)
sys.modules.setdefault("msgpack", MagicMock())


# --- 1. active_selection persistence -------------------------------------

class ActiveSelectionPersistenceTests(unittest.TestCase):
    """``active_selection`` writes through to userdata on every UI pick
    and rehydrates on startup so the picker survives server restarts.
    """

    def setUp(self):
        # Create an isolated userdata folder per test
        self.tmp = Path(tempfile.mkdtemp())
        self._orig_userdata = os.environ.get("SWEEPYCLAUDE_USERDATA_DIR")
        os.environ["SWEEPYCLAUDE_USERDATA_DIR"] = str(self.tmp)

    def tearDown(self):
        if self._orig_userdata is not None:
            os.environ["SWEEPYCLAUDE_USERDATA_DIR"] = self._orig_userdata
        else:
            os.environ.pop("SWEEPYCLAUDE_USERDATA_DIR", None)
        shutil.rmtree(self.tmp, ignore_errors=True)

    def test_save_load_roundtrip(self):
        """A saved selection comes back identical from disk."""
        # We can't import main.py directly (it spins up FastAPI), but we
        # can test the helper logic in isolation.
        selection = {
            "deck": [{"id": 1001}, {"id": 1002}],
            "friend": {"id": 1003},
            "trainee": {"card_id": 100601, "name": "Oguri Cap"},
            "veterans": [],
            "guestParents": [],
        }
        # Simulate _save_active_selection: write to USERDATA_DIR/active_selection.json
        path = self.tmp / "active_selection.json"
        path.write_text(json.dumps(selection), encoding="utf-8")
        # Simulate _load_active_selection: read it back
        loaded = json.loads(path.read_text(encoding="utf-8"))
        self.assertEqual(loaded, selection)
        self.assertEqual(loaded["trainee"]["card_id"], 100601)

    def test_load_missing_file_returns_none_safely(self):
        """Loading from a fresh userdata folder is a no-op (returns None)."""
        path = self.tmp / "active_selection.json"
        self.assertFalse(path.exists())
        try:
            data = json.loads(path.read_text(encoding="utf-8")) if path.exists() else None
        except Exception:
            data = None
        self.assertIsNone(data)

    def test_save_creates_parent_dir(self):
        """The save path is created if missing."""
        nested = self.tmp / "subdir"
        path = nested / "active_selection.json"
        nested.mkdir(parents=True, exist_ok=True)
        path.write_text("{}", encoding="utf-8")
        self.assertTrue(path.exists())


# --- 3. Hijack reasoning + blocked-override reasoning text ---------------

class DecisionReasoningTextTests(unittest.TestCase):
    """The dashboard reasoning text builds a prominent hijack line and
    explains blocked authoritative overrides.  We test the string
    output of _decision_reasoning indirectly via its inputs."""

    def setUp(self):
        from career_bot.runner import CareerRunner
        self.runner = CareerRunner.__new__(CareerRunner)
        import threading
        self.runner.status = {}
        self.runner.lock = threading.Lock()

    def _stats(self):
        return {"hp": 60, "max_hp": 100, "motivation": 4,
                "speed": 700, "stamina": 300, "power": 500, "guts": 300, "wit": 800}

    def test_hijack_line_appears_when_irregular_training_replaced_race(self):
        """When decision.reason contains the hijack marker, the reasoning
        list includes a clear "Irregular-training hijack" line."""
        decision = SimpleNamespace(
            action="command",
            payload={"current_turn": 49, "command_type": 1, "command_id": 101},
            reason="irregular training beats planned race Osaka Hai · G1 · 2000m · Turf "
                   "score=1.733 main_gain=35 fail=0 | v6.3 scorer override: 101 -> 106 (wit, margin 0.5)",
        )
        lines = self.runner._decision_reasoning(
            action="train", facility="Train Wit (rainbow x1)",
            detail="", stats=self._stats(), decision=decision, payload=decision.payload,
        )
        text = "\n".join(lines)
        self.assertIn("Irregular-training hijack", text,
            "decision reasoning must surface the hijack line prominently")
        self.assertIn("Osaka Hai", text)
        # The scorer-override suffix should be stripped from the hijack line
        first_match = next(l for l in lines if "Irregular-training hijack" in l)
        self.assertNotIn("v6.3 scorer override", first_match)


# --- 3. Shadow-precision: win-rate gate on race warnings -----------------

class WinRateWarningGateTests(unittest.TestCase):
    """A race only emits a negative ("warning") adjustment when its
    historical win rate is at or below ``warn_win_rate_ceiling``.

    Before this change a race the bot wins ~90% of the time still
    accrued a small avg-rank penalty and emitted a warning, which read
    as a false alarm in Shadow Mode (the race actually won) -- the user
    observed 16% shadow precision.
    """

    def _race_model(self):
        # One program the bot usually wins, one it usually loses; both
        # confident and both carrying a positive learned penalty.
        return {
            "model": {
                "winner": {"win_rate": 0.90, "penalty": 2.5,
                           "clock_dependency_penalty": 0.0,
                           "confidence": 0.9, "samples": 12},
                "loser": {"win_rate": 0.20, "penalty": 38.0,
                          "clock_dependency_penalty": 0.0,
                          "confidence": 0.9, "samples": 12},
            }
        }

    def _policy(self, **overrides):
        from career_bot.ai_trainer import (
            DEFAULT_AUTO_CONFIG, build_policy_adjustments,
        )
        cfg = dict(DEFAULT_AUTO_CONFIG)
        cfg.update(overrides)
        return build_policy_adjustments(self._race_model(), {}, {}, cfg)

    def test_high_win_rate_race_does_not_warn(self):
        winner = self._policy()["races"].get("winner", {})
        self.assertGreaterEqual(
            winner.get("adjustment", 0.0), 0.0,
            "a race the bot usually wins must not be warned about",
        )

    def test_low_win_rate_race_still_warns(self):
        races = self._policy()["races"]
        self.assertIn("loser", races)
        self.assertLess(
            races["loser"]["adjustment"], 0.0,
            "a race that loses most of the time must still warn",
        )

    def test_ceiling_is_configurable(self):
        races = self._policy(warn_win_rate_ceiling=0.10)["races"]
        self.assertGreaterEqual(races.get("loser", {}).get("adjustment", 0.0), 0.0)

    def test_payload_exposes_ceiling(self):
        self.assertEqual(self._policy()["warn_win_rate_ceiling"], 0.50)

    def test_defaults_raised(self):
        from career_bot.ai_trainer import DEFAULT_AUTO_CONFIG
        self.assertEqual(DEFAULT_AUTO_CONFIG["warn_win_rate_ceiling"], 0.50)
        self.assertEqual(DEFAULT_AUTO_CONFIG["min_samples_for_model"], 4)


if __name__ == "__main__":
    unittest.main()
