import tempfile
import unittest
from pathlib import Path

from career_bot.events import EventManager
from career_bot.presets import serialize_preset


def choice_event(rewards, story_id="900001"):
    """Build a choice event whose options carry inline rewards (the form
    _inline_choice_rewards reads from the live event payload). ``rewards`` is a
    list, one entry per choice, of a ``params_inc_dec_info_array`` list (or None
    for a choice with no reward). The event_outcomes KB was removed, so effect
    data must come through the payload (or the game8 scrape fallback)."""
    return {
        "story_id": story_id,
        "event_id": int(story_id),
        "event_contents_info": {
            "choice_array": [
                {**{"select_index": idx + 1}, **({"params_inc_dec_info_array": r} if r else {})}
                for idx, r in enumerate(rewards)
            ]
        },
    }


class TrackblazerP3EventScoringTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.base = Path(self.tmp.name)

    def tearDown(self):
        self.tmp.cleanup()

    def test_event_choice_stat_priority_overrides_training_priority(self):
        manager = EventManager(self.base)
        event = choice_event([
            [{"target_type": 1, "value": 10}],   # choice 1: Speed
            [{"target_type": 2, "value": 10}],   # choice 2: Stamina
        ])
        preset = {
            "training_stat_priority": ["speed", "stamina"],
            "event_choice_stat_priority": ["stamina", "speed"],
        }
        self.assertEqual(manager.choose(event, preset, 25, {"vital": 80, "motivation": 5}), 1)
        trace = manager.last_choice_trace
        self.assertEqual(trace["event_priority"][:2], ["stamina", "speed"])
        self.assertIn("stat_stamina", trace["scores"][1]["reason"])

    def test_prioritize_event_energy_beats_skill_points(self):
        manager = EventManager(self.base)
        event = choice_event([
            [{"target_type": 30, "value": 5}],   # choice 1: Skill points +5
            [{"target_type": 10, "value": 5}],   # choice 2: Vital +5
        ])
        preset = {"prioritize_event_energy": True}
        self.assertEqual(manager.choose(event, preset, 25, {"vital": 20, "motivation": 5}), 1)
        self.assertTrue(manager.last_choice_trace["energy_priority"])

    def test_full_energy_reward_is_ignored_without_priority_mode(self):
        manager = EventManager(self.base)
        event = choice_event([
            [{"target_type": 10, "value": 30}],  # choice 1: Vital +30 (energy already full)
            [{"target_type": 30, "value": 10}],  # choice 2: Skill points +10
        ])
        self.assertEqual(manager.choose(event, {}, 25, {"vital": 100, "max_vital": 100, "motivation": 5}), 1)

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
