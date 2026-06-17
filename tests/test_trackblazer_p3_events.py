import json
import tempfile
import unittest
from pathlib import Path

from career_bot.events import EventManager
from career_bot.presets import serialize_preset


def choice_event(story_id="900001", count=2):
    return {
        "story_id": story_id,
        "event_id": int(story_id),
        "event_contents_info": {
            "choice_array": [
                {"select_index": idx + 1} for idx in range(count)
            ]
        },
    }


class TrackblazerP3EventScoringTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.base = Path(self.tmp.name)
        (self.base / "data").mkdir()

    def tearDown(self):
        self.tmp.cleanup()

    def manager_with_outcomes(self, outcomes):
        (self.base / "data" / "event_outcomes.json").write_text(json.dumps(outcomes), encoding="utf-8")
        return EventManager(self.base)

    def test_event_choice_stat_priority_overrides_training_priority(self):
        manager = self.manager_with_outcomes({
            "900001": {
                "outcomes": {"1": "", "2": ""},
                "details": {
                    "1": {"params_inc_dec_info_array": [{"target_type": 1, "value": 10}]},
                    "2": {"params_inc_dec_info_array": [{"target_type": 2, "value": 10}]},
                },
            }
        })
        preset = {
            "training_stat_priority": ["speed", "stamina"],
            "event_choice_stat_priority": ["stamina", "speed"],
        }
        self.assertEqual(manager.choose(choice_event(), preset, 25, {"vital": 80, "motivation": 5}), 1)
        trace = manager.last_choice_trace
        self.assertEqual(trace["event_priority"][:2], ["stamina", "speed"])
        self.assertIn("stat_stamina", trace["scores"][1]["reason"])

    def test_prioritize_event_energy_can_beat_good_label(self):
        manager = self.manager_with_outcomes({
            "900001": {
                "outcomes": {"1": "good", "2": ""},
                "details": {
                    "1": {"skill_point": 5},
                    "2": {"vital": 5},
                },
            }
        })
        preset = {"prioritize_event_energy": True}
        self.assertEqual(manager.choose(choice_event(), preset, 25, {"vital": 20, "motivation": 5}), 1)
        self.assertTrue(manager.last_choice_trace["energy_priority"])

    def test_full_energy_reward_is_ignored_without_priority_mode(self):
        manager = self.manager_with_outcomes({
            "900001": {
                "outcomes": {"1": "", "2": ""},
                "details": {
                    "1": {"vital": 30},
                    "2": {"skill_point": 10},
                },
            }
        })
        self.assertEqual(manager.choose(choice_event(), {}, 25, {"vital": 100, "max_vital": 100, "motivation": 5}), 1)

    def test_mood_loss_and_chain_end_are_penalized(self):
        manager = self.manager_with_outcomes({
            "900001": {
                "outcomes": {"1": "event chain ended", "2": "mood up"},
                "details": {
                    "1": {"speed": 50},
                    "2": {"motivation": 1},
                },
            }
        })
        self.assertEqual(manager.choose(choice_event(), {}, 25, {"vital": 50, "motivation": 2}), 1)
        reasons = [row["reason"] for row in manager.last_choice_trace["scores"]]
        self.assertIn("ends_chain", reasons[0])
        self.assertIn("mood", reasons[1])

    def test_preset_serialization_preserves_p3_event_fields(self):
        serialized = serialize_preset({
            "name": "event config",
            "event_choice_stat_priority": ["stamina", "power"],
            "event_overrides": {"123": 2},
            "prioritize_event_energy": True,
            "event_energy_priority_multiplier": 80,
            "event_stat_priority_bonus_by_rank": [60, 45, 30],
        })
        self.assertEqual(serialized["event_choice_stat_priority"], ["stamina", "power"])
        self.assertEqual(serialized["event_overrides"], {"123": 2})
        self.assertTrue(serialized["prioritize_event_energy"])
        self.assertEqual(serialized["event_energy_priority_multiplier"], 80)
        self.assertEqual(serialized["event_stat_priority_bonus_by_rank"], [60, 45, 30])


if __name__ == "__main__":
    unittest.main()
