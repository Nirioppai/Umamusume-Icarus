"""Tests for Sprint 2 — hierarchical race-program advisor.

Covers:
  - ``ai_dataset.rebuild_advisor_stats`` now writes ``race_programs_context``
    with four levels of nesting, while keeping v1 ``race_programs`` intact.
  - ``ai_dataset._turn_phase`` boundary semantics.
  - ``ai_advisor.hierarchical_race_program_hint``:
      * full context -> uses the deepest level that has data
      * partial context -> walks as far as the context allows
      * no context buckets in stats -> falls back to v1 ``race_program_hint``
        with identical return-key contract
      * sparse leaf inherits from a rich parent (the whole point of the
        hierarchical pooling)
"""

from __future__ import annotations

import json
import os
import tempfile
import unittest
from pathlib import Path

from career_bot.ai_dataset import (
    DATASET_FILES,
    SCHEMA_VERSION,
    _turn_phase,
    rebuild_advisor_stats,
)


def _write_jsonl(path: Path, rows):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("\n".join(json.dumps(r) for r in rows), encoding="utf-8")


def _race_row(
    program_id: int,
    scenario_id: int,
    preset_name: str,
    turn: int,
    rank: int,
    reward: float = 5.0,
):
    """Single race-action turn record matching the schema written by
    ``turn_decision_records``."""
    return {
        "schema_version": SCHEMA_VERSION,
        "dataset": "turn_decisions",
        "run_id": f"run-{program_id}-{turn}",
        "preset_name": preset_name,
        "scenario_id": scenario_id,
        "turn": turn,
        "action": {"type": "race", "program_id": program_id},
        "outcome": {"reward": reward, "race_result": {"rank": rank}},
    }


# ---------------------------------------------------------------------------
# _turn_phase boundaries
# ---------------------------------------------------------------------------


class TurnPhaseTests(unittest.TestCase):
    def test_boundary_inclusivity(self):
        # Boundaries match the existing turn_bands aggregation: <25, <49, <73.
        self.assertEqual(_turn_phase(0), "early")
        self.assertEqual(_turn_phase(24), "early")
        self.assertEqual(_turn_phase(25), "classic")
        self.assertEqual(_turn_phase(48), "classic")
        self.assertEqual(_turn_phase(49), "senior")
        self.assertEqual(_turn_phase(72), "senior")
        self.assertEqual(_turn_phase(73), "finale")
        self.assertEqual(_turn_phase(99), "finale")


# ---------------------------------------------------------------------------
# rebuild_advisor_stats writes hierarchical buckets
# ---------------------------------------------------------------------------


class HierarchicalRebuildTests(unittest.TestCase):
    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        self.ai_root = Path(self._tmp.name) / "ai"
        self.ai_root.mkdir(parents=True, exist_ok=True)

    def tearDown(self):
        self._tmp.cleanup()

    def test_writes_v1_and_v2_sections(self):
        rows = [
            _race_row(101, scenario_id=4, preset_name="Goldship-Build-A", turn=30, rank=1),
            _race_row(101, scenario_id=4, preset_name="Goldship-Build-A", turn=50, rank=3),
            _race_row(101, scenario_id=4, preset_name="Goldship-Build-B", turn=30, rank=1),
        ]
        _write_jsonl(self.ai_root / DATASET_FILES["turn_decisions"], rows)

        payload = rebuild_advisor_stats(self.ai_root)

        # v1 section unchanged
        self.assertIn("race_programs", payload)
        self.assertIn("101", payload["race_programs"])
        self.assertEqual(payload["race_programs"]["101"]["starts"], 3)
        self.assertEqual(payload["race_programs"]["101"]["wins"], 2)

        # v2 section present with all four levels
        ctx = payload["race_programs_context"]
        self.assertIn("by_program", ctx)
        self.assertIn("by_program_scenario", ctx)
        self.assertIn("by_program_scenario_preset", ctx)
        self.assertIn("by_program_scenario_preset_phase", ctx)

        # Most specific key for the first row
        leaf_key = "101:4:Goldship-Build-A:classic"  # turn 30 -> classic phase
        self.assertIn(leaf_key, ctx["by_program_scenario_preset_phase"])
        self.assertEqual(
            ctx["by_program_scenario_preset_phase"][leaf_key]["starts"], 1
        )
        self.assertEqual(
            ctx["by_program_scenario_preset_phase"][leaf_key]["wins"], 1
        )

        # Parent level aggregates both Build-A rows for this scenario
        self.assertEqual(
            ctx["by_program_scenario_preset"]["101:4:Goldship-Build-A"]["starts"], 2
        )

    def test_unknown_preset_falls_back_to_placeholder(self):
        rows = [_race_row(200, scenario_id=4, preset_name="", turn=10, rank=2)]
        _write_jsonl(self.ai_root / DATASET_FILES["turn_decisions"], rows)
        payload = rebuild_advisor_stats(self.ai_root)
        self.assertIn(
            "200:4:_unknown",
            payload["race_programs_context"]["by_program_scenario_preset"],
        )


# ---------------------------------------------------------------------------
# hierarchical_race_program_hint
# ---------------------------------------------------------------------------


class HierarchicalHintTests(unittest.TestCase):
    LEGACY_FIELDS = {
        "program_id", "confidence", "starts", "win_rate",
        "avg_reward", "adjustment", "reason",
    }
    V2_FIELDS = {
        "posterior_mean", "lcb", "ucb", "variance", "alpha", "beta",
        "contributed_levels", "levels",
    }

    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        self.root = Path(self._tmp.name)
        self.runtime = self.root / "uma_runtime"
        self.ai = self.runtime / "ai"
        self.ai.mkdir(parents=True, exist_ok=True)
        self._prior_env = os.environ.get("UMA_RUNTIME_DIR")
        os.environ["UMA_RUNTIME_DIR"] = str(self.runtime)

    def tearDown(self):
        if self._prior_env is None:
            os.environ.pop("UMA_RUNTIME_DIR", None)
        else:
            os.environ["UMA_RUNTIME_DIR"] = self._prior_env
        self._tmp.cleanup()

    def _write_stats(self, payload):
        (self.ai / "advisor_stats.json").write_text(
            json.dumps(payload), encoding="utf-8"
        )

    def test_falls_back_when_v2_context_missing(self):
        """Old advisor_stats.json files without race_programs_context still
        produce a valid hint via the v1 code path."""
        from career_bot.ai_advisor import hierarchical_race_program_hint
        self._write_stats({"race_programs": {
            "101": {"starts": 10, "wins": 7, "win_rate": 0.7, "avg_reward": 5.0}
        }})
        hint = hierarchical_race_program_hint(self.root, 101, scenario_id=4)
        # All legacy + v2 fields present (v2 fields populated by the fall-through
        # call which itself goes through the v2 race_program_hint).
        for key in self.LEGACY_FIELDS:
            self.assertIn(key, hint)
        self.assertEqual(hint["contributed_levels"], ["program"])
        self.assertEqual(hint["levels"], [])

    def test_full_context_uses_deepest_level(self):
        from career_bot.ai_advisor import hierarchical_race_program_hint
        self._write_stats({
            "race_programs": {
                "101": {"starts": 50, "wins": 30, "win_rate": 0.6, "avg_reward": 4.0}
            },
            "race_programs_context": {
                "by_program": {
                    "101": {"starts": 50, "wins": 30, "win_rate": 0.6, "avg_reward": 4.0}
                },
                "by_program_scenario": {
                    "101:4": {"starts": 30, "wins": 20, "win_rate": 0.667, "avg_reward": 4.5}
                },
                "by_program_scenario_preset": {
                    "101:4:Goldship-Build-A": {
                        "starts": 15, "wins": 12, "win_rate": 0.8, "avg_reward": 6.0
                    }
                },
                "by_program_scenario_preset_phase": {
                    "101:4:Goldship-Build-A:classic": {
                        "starts": 8, "wins": 7, "win_rate": 0.875, "avg_reward": 7.0
                    }
                },
            },
        })
        hint = hierarchical_race_program_hint(
            self.root, 101, scenario_id=4,
            preset_name="Goldship-Build-A", turn=30,
        )
        # All four levels contributed
        self.assertEqual(
            hint["contributed_levels"],
            ["program", "program_scenario",
             "program_scenario_preset", "program_scenario_preset_phase"],
        )
        # avg_reward comes from the deepest contributing level
        self.assertEqual(hint["avg_reward"], 7.0)
        # Posterior mean is pulled upward toward 0.875 by the leaf
        self.assertGreater(hint["posterior_mean"], 0.7)
        # Variance components are populated
        for key in self.V2_FIELDS:
            self.assertIn(key, hint)

    def test_partial_context_only_walks_supplied_levels(self):
        from career_bot.ai_advisor import hierarchical_race_program_hint
        self._write_stats({
            "race_programs": {"101": {"starts": 5, "wins": 3, "win_rate": 0.6, "avg_reward": 4.0}},
            "race_programs_context": {
                "by_program": {"101": {"starts": 5, "wins": 3, "win_rate": 0.6, "avg_reward": 4.0}},
                "by_program_scenario": {},
                "by_program_scenario_preset": {},
                "by_program_scenario_preset_phase": {},
            },
        })
        # No scenario -> only the "program" level can match
        hint = hierarchical_race_program_hint(self.root, 101)
        self.assertEqual(hint["contributed_levels"], ["program"])

    def test_sparse_leaf_inherits_from_rich_parent(self):
        """The headline behavior: a sparse leaf with 1 start gets pulled
        toward its scenario-level posterior instead of producing a wild
        estimate."""
        from career_bot.ai_advisor import hierarchical_race_program_hint
        self._write_stats({
            "race_programs": {"101": {"starts": 51, "wins": 35, "win_rate": 0.686, "avg_reward": 5.0}},
            "race_programs_context": {
                "by_program": {"101": {"starts": 51, "wins": 35, "win_rate": 0.686, "avg_reward": 5.0}},
                "by_program_scenario": {
                    "101:4": {"starts": 50, "wins": 35, "win_rate": 0.7, "avg_reward": 5.0}
                },
                "by_program_scenario_preset": {
                    "101:4:NewBuild": {"starts": 1, "wins": 0, "win_rate": 0.0, "avg_reward": 0.0}
                },
                "by_program_scenario_preset_phase": {},
            },
        })
        hint = hierarchical_race_program_hint(
            self.root, 101, scenario_id=4, preset_name="NewBuild",
        )
        # Despite the leaf being 0/1, the posterior mean should sit well
        # above 0.0 because the parent's 35/50 is doing the heavy lifting.
        self.assertGreater(hint["posterior_mean"], 0.4)
        # And it shouldn't naively equal the parent's mean either — the
        # leaf observation should pull it down a bit.
        self.assertLess(hint["posterior_mean"], 0.7)


if __name__ == "__main__":
    unittest.main()
