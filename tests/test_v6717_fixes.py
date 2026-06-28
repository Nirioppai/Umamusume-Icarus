"""Regression tests for v6.7.17: the decision-reasoning panel was
displaying the wrong stat priority.

The bug: the actual training STRATEGY reads ``preset.training_stat_priority``
(the Training Settings panel), but the reasoning DISPLAY read the
character profile's separate ``training_scorer_overrides.stat_priority``.
A user who reordered priorities in the panel (e.g. moved Stamina above
Wit) saw the bot train with their new order but the reasoning kept
showing the profile's OLD order -- making it look like the change
didn't take effect.

Fix: the reasoning now shows the priority that ACTUALLY drove the
decision:
  * hint / disabled mode -> preset.training_stat_priority (strategy decides)
  * authoritative mode    -> profile stat_priority (scorer decides)
"""
import sys
import threading
import unittest
from types import SimpleNamespace
from unittest.mock import MagicMock

sys.modules.setdefault("msgpack", MagicMock())


class PriorityDisplayTests(unittest.TestCase):
    def setUp(self):
        from career_bot.runner import CareerRunner
        self.r = CareerRunner.__new__(CareerRunner)
        self.r.status = {}
        self.r.lock = threading.Lock()
        self.r.item_manager = SimpleNamespace(
            last_use_selected=[], last_use_result={}, use_attempt_events=[]
        )

    def _stats(self):
        return {"hp": 73, "max_hp": 100, "motivation": 5,
                "speed": 253, "stamina": 96, "power": 234, "guts": 140, "wit": 218}

    def _decision(self, turn=15):
        return SimpleNamespace(
            action="command",
            payload={"current_turn": turn, "command_type": 1, "command_id": 101},
            reason="Train Speed",
        )

    def _reason_text(self):
        lines = self.r._decision_reasoning(
            "train", "Train Speed", "", self._stats(),
            self._decision(), self._decision().payload,
        )
        return "\n".join(lines)

    def test_hint_mode_shows_preset_priority(self):
        """The user's exact case: panel = Stamina #3, profile = Wit #3,
        hint mode.  The reasoning must show the PANEL order."""
        self.r.status["preset_training_stat_priority"] = [
            "speed", "power", "stamina", "wit", "guts"]
        self.r.status["active_character_profile"] = {
            "training_scorer_mode": "hint",
            "training_scorer_overrides": {
                "stat_priority": ["speed", "power", "wit", "stamina", "guts"]},
        }
        text = self._reason_text()
        self.assertIn("speed > power > stamina > wit > guts", text)
        self.assertNotIn("wit > stamina", text)

    def test_disabled_mode_shows_preset_priority(self):
        """Disabled scorer mode -> strategy drives -> preset priority."""
        self.r.status["preset_training_stat_priority"] = [
            "speed", "stamina", "power", "wit", "guts"]
        self.r.status["active_character_profile"] = {
            "training_scorer_mode": "disabled",
            "training_scorer_overrides": {
                "stat_priority": ["speed", "power", "wit", "stamina", "guts"]},
        }
        text = self._reason_text()
        self.assertIn("speed > stamina > power > wit > guts", text)

    def test_preset_priority_used_with_no_profile(self):
        """No character profile but a preset priority is set -> use it."""
        self.r.status["preset_training_stat_priority"] = [
            "speed", "stamina", "power", "guts", "wit"]
        text = self._reason_text()
        self.assertIn("speed > stamina > power > guts > wit", text)


if __name__ == "__main__":
    unittest.main()
