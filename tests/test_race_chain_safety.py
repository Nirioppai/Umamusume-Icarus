"""Regression tests for ``_guide_race_chain_break``.

History of this test module:

v6.7.3 added an aggressive HP-safety layer that fired at chain_count >=
legacy_target (2) regardless of the user's "Consecutive Races Limit"
slider, plus a hard cap that forced a break at chain_count >= target
even with full HP.

v6.7.7 reverted that change per user request.  The user already has the
"Ignore Low Energy Racing Block" toggle in Racing Settings and wants
that toggle to be the sole HP authority -- not a separate code-level
HP gate.  Under v6.7.7's contract:

  * Below chain_count == target: the chain-break function does NOT
    intervene regardless of HP.  Whether the bot races at low HP is
    governed entirely by the "Ignore Low Energy Racing Block" toggle.
  * At or above chain_count == target with low HP: the legacy HP-low
    / HP-critical gates fire only when "Ignore Low Energy Racing
    Block" is OFF.
  * At or above chain_count == target with full HP: the function
    returns None (the chain target is a SOFT preference, not a hard
    cap), so the race may proceed if other checks allow.
  * Existing escape hatches (ignore_consecutive_race_warning,
    enable_game8_race_chain_break=False) still bypass the function
    entirely.

If the user wants HP=0 races prevented they set the toggle OFF; if
they want Android-style throughput they set it ON.  This module
verifies those contracts.
"""
import unittest
from typing import Any, Dict, List

from career_bot.scenarios.mant import MantStrategy


def _history(*turns_actions) -> List[Dict[str, Any]]:
    """Build an action_history list from (turn, action) pairs."""
    return [{"turn": t, "action": a} for t, a in turns_actions]


def _state(action_history, vital, *, enabled_commands=None):
    """Minimal state dict the strategy reads in this code path."""
    return {
        "data": {
            "action_history": action_history,
            "home_info": {"command_info_array": enabled_commands or _default_commands()},
        },
    }


def _default_commands():
    """A baseline command pool with rest (701) and recreation (301) enabled.

    Avoids any training that could pass the chain-break training-bypass
    gate (failure_rate forced to 99 keeps the bypass dormant so the test
    isolates the HP gates).
    """
    return [
        {"command_type": 7, "command_id": 701, "is_enable": 1},        # Rest
        {"command_type": 3, "command_id": 301, "command_group_id": 301, "is_enable": 1},  # Recreation
        {"command_type": 1, "command_id": 101, "is_enable": 1, "failure_rate": 99,
         "params_inc_dec_info_array": [{"target_type": 1, "value": 5}]},  # unviable training
    ]


class GuideRaceChainSafetyTests(unittest.TestCase):
    def setUp(self):
        # Bare strategy instance with a permissive preset and no race
        # planner -- we hit ``_guide_race_chain_break`` directly.
        self.strategy = MantStrategy(race_planner=None)
        self.strategy.trackblazer_guide = {}
        self.preset = {"mant_config": {"race_chain_target": 5}}

    def _chara(self, turn, vital):
        return {"turn": turn, "vital": vital}

    # ----- The bug the user reported ---------------------------------------

    def test_chain_count_below_target_does_not_fire_with_hp_low(self):
        """v6.7.7 revert: when target=5 and chain_count=2 with low HP, the
        function does NOT intervene -- the user's "Consecutive Races Limit"
        slider is the gate, and HP safety only fires once that limit is
        approached.  The user explicitly asked for this behavior so the
        "Ignore Low Energy Racing Block" toggle is the sole HP authority.

        (Pre-v6.7.3 behavior; v6.7.3 added an aggressive HP gate that
        fired at chain_count>=2 regardless of target.  v6.7.7 reverts
        that change.)
        """
        history = _history(
            (15, "train"), (16, "train"), (17, "race"),
            (18, "rest"), (19, "race"), (20, "race"),
        )
        state = _state(history, vital=0)
        decision = self.strategy._guide_race_chain_break(
            state["data"], self._chara(21, 0), self.preset, program_id=1234,
        )
        self.assertIsNone(
            decision,
            "With target=5 and chain_count=2, the v6.7.7 contract is to "
            "let the race proceed -- the toggle is the sole HP authority.",
        )

    # ----- HP gate at user-set target -------------------------------------

    def test_hp_critical_fires_only_at_user_target(self):
        """When chain_count reaches the user's target and HP is critical,
        the chain-break fires -- but only at target, not earlier."""
        # Five prior races, target=5, HP=5 (critical).
        history = _history(
            (15, "rest"),
            (16, "race"), (17, "race"), (18, "race"),
            (19, "race"), (20, "race"),
        )
        state = _state(history, vital=5)
        decision = self.strategy._guide_race_chain_break(
            state["data"], self._chara(21, 5), self.preset, program_id=1234,
        )
        self.assertIsNotNone(decision)
        self.assertIn("critical HP", decision.reason)

    def test_no_hp_gate_below_user_target(self):
        """Two prior races with HP=5 (critical) but target=5: the v6.7.7
        contract is to let the race proceed.  Toggle is the user's
        knob if they want HP=0 protection across the whole streak."""
        history = _history((18, "rest"), (19, "race"), (20, "race"))
        state = _state(history, vital=5)
        decision = self.strategy._guide_race_chain_break(
            state["data"], self._chara(21, 5), self.preset, program_id=1234,
        )
        self.assertIsNone(decision)

    # ----- No hard cap (chain limit is a soft preference) ------------------

    def test_chain_target_is_soft_when_hp_is_fine(self):
        """v6.7.7 revert: when chain_count >= target but HP is fine and
        not unsafe-grade, the function returns None and the race
        proceeds.  The chain target is a soft preference, not a hard
        cap -- aligning with pre-v6.7.3 behavior and the Android
        bot's equivalent setting.
        """
        history = _history(
            (15, "rest"),
            (16, "race"), (17, "race"), (18, "race"),
            (19, "race"), (20, "race"),
        )
        state = _state(history, vital=80)  # full HP, target met
        decision = self.strategy._guide_race_chain_break(
            state["data"], self._chara(21, 80), self.preset, program_id=1234,
        )
        self.assertIsNone(
            decision,
            "v6.7.7: with HP fine the chain target is a soft preference, "
            "the race must proceed.",
        )

    # ----- Escape hatches still work ---------------------------------------

    def test_ignore_low_energy_disables_hp_gate(self):
        history = _history((18, "rest"), (19, "race"), (20, "race"))
        preset = {"mant_config": {"race_chain_target": 5, "ignore_low_energy_racing_block": True}}
        state = _state(history, vital=0)
        decision = self.strategy._guide_race_chain_break(
            state["data"], self._chara(21, 0), preset, program_id=1234,
        )
        # With ignore_low_energy on AND chain_count below target, we
        # should fall through to None (no break).
        self.assertIsNone(decision)

    def test_ignore_consecutive_warning_disables_everything(self):
        history = _history((18, "race"), (19, "race"), (20, "race"))
        preset = {"mant_config": {"race_chain_target": 5, "ignore_consecutive_race_warning": True}}
        state = _state(history, vital=0)
        decision = self.strategy._guide_race_chain_break(
            state["data"], self._chara(21, 0), preset, program_id=1234,
        )
        self.assertIsNone(decision)

    def test_disable_game8_chain_break_returns_none(self):
        history = _history((18, "race"), (19, "race"), (20, "race"))
        preset = {"mant_config": {"race_chain_target": 5, "enable_game8_race_chain_break": False}}
        state = _state(history, vital=0)
        decision = self.strategy._guide_race_chain_break(
            state["data"], self._chara(21, 0), preset, program_id=1234,
        )
        self.assertIsNone(decision)

    # ----- Year-end / Finale carve-outs preserved --------------------------

    def test_finale_window_remains_permissive(self):
        """Turn 73+ is intentionally permissive even at HP=0."""
        history = _history((71, "race"), (72, "race"))
        state = _state(history, vital=0)
        decision = self.strategy._guide_race_chain_break(
            state["data"], self._chara(73, 0), self.preset, program_id=1234,
        )
        self.assertIsNone(decision)


if __name__ == "__main__":
    unittest.main()
