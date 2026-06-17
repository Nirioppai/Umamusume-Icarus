"""Regression tests for the v6.7.5 scorer-override-placement fix.

The bug: ``_apply_authoritative_scorer_override`` was called against the
pre-event decision object on line 602, then the strategy was immediately
re-invoked on line 615, producing a NEW decision object that overwrote
the mutated one.  The override's effect on the executed command was
discarded but ``last_scorer_override`` was already written to status, so
the dashboard's Decision Reasoning panel would show contradictory rows:

  "T29 Wit -- Trained Wit ... scorer override fired: strategy picked 106,
   swapped to speed (margin 7.3435)"

Where the row header says Wit (correctly -- Wit actually ran) but the
override message says Speed (a swap that never reached execution).

The fix moves the override to the actual execution branch, just before
``_record_action`` and ``exec_command``, AND clears stale entries from
prior turns so the dashboard never sees a leftover override for a turn
where it didn't fire.
"""
import unittest
import threading
import sys
from types import SimpleNamespace
from unittest.mock import MagicMock, patch

# Stub out optional native deps that runner.py imports at module load
# but doesn't actually use in the override path under test.
for _modname in ("msgpack",):
    if _modname not in sys.modules:
        sys.modules[_modname] = MagicMock()

from career_bot.runner import CareerRunner


def _make_runner_with_status(status):
    """Create a CareerRunner-like object with just enough state to call
    ``_apply_authoritative_scorer_override`` directly.  We bypass __init__
    because it does a lot of disk I/O for fixtures and event managers."""
    r = CareerRunner.__new__(CareerRunner)
    r.lock = threading.RLock()
    r.status = dict(status)
    r.base_dir = "."
    return r


class StaleOverrideClearTests(unittest.TestCase):
    """The fix must clear ``last_scorer_override`` at the start of a new
    turn if it was inherited from a previous turn where the override
    no longer applies."""

    def test_stale_override_from_previous_turn_is_cleared(self):
        """T15 override entry must not leak into T29."""
        runner = _make_runner_with_status({
            "last_scorer_override": {
                "turn": 15,
                "profile_id": "oguri_cap",
                "from_command_id": 106,
                "to_command_id": 101,
                "to_stat": "speed",
                "margin": 7.34,
            },
        })
        # Build a decision for T29 with a non-training command_type so
        # the override returns early after the clear pass.
        decision = SimpleNamespace(
            action="command",
            payload={"current_turn": 29, "command_type": 7, "command_id": 701},
            reason="Rest",
        )
        runner._apply_authoritative_scorer_override(state={"data": {}}, decision=decision)
        self.assertIsNone(
            runner.status.get("last_scorer_override"),
            "Stale override from T15 must be cleared when T29's override evaluation runs.",
        )

    def test_current_turn_override_is_preserved(self):
        """An override entry that matches the current turn must NOT be
        cleared during evaluation (it's still the truth for this turn)."""
        runner = _make_runner_with_status({
            "last_scorer_override": {
                "turn": 29,
                "profile_id": "oguri_cap",
                "from_command_id": 106,
                "to_command_id": 101,
                "to_stat": "speed",
                "margin": 7.34,
            },
        })
        # Use a non-training command_type to avoid the scorer running
        decision = SimpleNamespace(
            action="command",
            payload={"current_turn": 29, "command_type": 7, "command_id": 701},
            reason="Rest",
        )
        runner._apply_authoritative_scorer_override(state={"data": {}}, decision=decision)
        # Override from T29 must still be present (the early-return path
        # for non-training shouldn't touch a matching-turn entry).
        self.assertIsNotNone(runner.status.get("last_scorer_override"))
        self.assertEqual(runner.status["last_scorer_override"]["turn"], 29)


class OverridePlacementTests(unittest.TestCase):
    """The override is now applied at the actual execution branch.  This
    test mocks the strategy + scorer to confirm that when the override
    swaps Wit -> Speed, ``decision.payload["command_id"]`` reflects
    Speed at the point of execution (which is what ``_record_action``
    will see)."""

    def test_override_mutates_final_decision_payload(self):
        runner = _make_runner_with_status({"scenario_id": 4, "preset_name": "Oguri Cap"})

        # Fake decision that the strategy would produce: Wit training.
        decision = SimpleNamespace(
            action="command",
            payload={
                "current_turn": 29,
                "command_type": 1,
                "command_id": 106,   # Wit
                "command_group_id": 0,
            },
            reason="Train Wit",
        )

        # Mock the profile to be in authoritative mode
        # v6.7.9: profile now needs training_scorer_overrides for the
        # configurable margin gate (override_margin_pct, _floor).
        fake_profile = SimpleNamespace(
            profile_id="oguri_cap",
            training_scorer_mode="authoritative",
            training_scorer_overrides={},  # empty dict -> use default gate
            training_scorer_config=lambda: {},
        )

        # Mock the scorer to return Speed as top pick with a high score
        fake_scorer_pick = SimpleNamespace(
            command_id=101,
            stat_name="speed",
            score=37.21,
        )
        fake_strategy_pick = SimpleNamespace(
            command_id=106,
            stat_name="wit",
            score=29.87,
        )

        state = {
            "data": {
                "chara_info": {"card_id": 100601, "chara_id": 1006, "turn": 29},
                "home_info": {"command_info_array": [
                    {"command_type": 1, "command_id": 106, "is_enable": 1},
                    {"command_type": 1, "command_id": 101, "is_enable": 1},
                ]},
            },
        }

        with patch("career_bot.character_profiles.resolve_profile", return_value=fake_profile), \
             patch("career_bot.training_scorer.score_trainings", return_value=[fake_scorer_pick, fake_strategy_pick]):
            runner._apply_authoritative_scorer_override(state, decision)

        # After the override fires, the decision's payload command_id
        # must now be Speed (101), NOT Wit (106).  This is the critical
        # assertion -- if this fails, the override is being applied to
        # the wrong decision object again.
        self.assertEqual(
            decision.payload["command_id"], 101,
            "Override must mutate the final decision payload (Wit -> Speed).",
        )

        # The override status must be recorded for the current turn.
        self.assertIsNotNone(runner.status.get("last_scorer_override"))
        self.assertEqual(runner.status["last_scorer_override"]["turn"], 29)
        self.assertEqual(runner.status["last_scorer_override"]["from_command_id"], 106)
        self.assertEqual(runner.status["last_scorer_override"]["to_command_id"], 101)
        self.assertEqual(runner.status["last_scorer_override"]["to_stat"], "speed")

    def test_hint_mode_does_not_override(self):
        """When the profile is in hint mode (the default for v6.x), no
        mutation happens and no status entry is written."""
        runner = _make_runner_with_status({"scenario_id": 4, "preset_name": "Oguri Cap"})

        decision = SimpleNamespace(
            action="command",
            payload={
                "current_turn": 29,
                "command_type": 1,
                "command_id": 106,
                "command_group_id": 0,
            },
            reason="Train Wit",
        )

        fake_profile = SimpleNamespace(
            profile_id="oguri_cap",
            training_scorer_mode="hint",  # NOT authoritative
            training_scorer_config=lambda: {},
        )

        state = {"data": {"chara_info": {"turn": 29}}}

        with patch("career_bot.character_profiles.resolve_profile", return_value=fake_profile):
            runner._apply_authoritative_scorer_override(state, decision)

        # No mutation, no status write
        self.assertEqual(decision.payload["command_id"], 106)
        self.assertIsNone(runner.status.get("last_scorer_override"))


if __name__ == "__main__":
    unittest.main()
