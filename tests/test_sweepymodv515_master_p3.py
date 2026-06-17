import contextlib
import io
import json
import tempfile
import unittest
from pathlib import Path

from career_bot import master_data
from career_bot.events import EventManager
from career_bot.runner import CareerRunner


class FakeStrategy:
    def next_decision(self, state, preset=None):
        return type("Decision", (), {"kind": "train", "payload": {}})()


class FakeClient214AtRaceEntry:
    def __init__(self):
        self.load_career_calls = 0

    def race_entry(self, **kwargs):
        raise Exception('API error 214 on single_mode_free/race_entry: {"result_code": 214}')

    def load_career(self):
        self.load_career_calls += 1
        return {"data": {"chara_info": {"turn": 12}, "home_info": {}}}


class SweepyModV515MasterP3Tests(unittest.TestCase):
    def _master_data(self):
        return {
            "tables": {
                "succession_initial_factor": [
                    {"id": 1, "factor_type": 1, "value_1": 1, "value_2": 0, "add_point": 5},
                    {"id": 2, "factor_type": 1, "value_1": 2, "value_2": 0, "add_point": 12},
                    {"id": 4, "factor_type": 2, "value_1": 1, "value_2": 3, "add_point": 1},
                ],
                "succession_relation_rank": [
                    {"relation_rank": 1, "rank_value_min": 0, "rank_value_max": 50},
                    {"relation_rank": 2, "rank_value_min": 51, "rank_value_max": 150},
                ],
                "succession_relation": [
                    {"relation_type": 101, "relation_point": 2},
                ],
                "single_mode_chara_grade": [
                    {"id": 1, "win_num": 0, "run_num": 0, "need_fan_count": 0},
                    {"id": 4, "win_num": 1, "run_num": 1, "need_fan_count": 5000},
                    {"id": 10, "win_num": 1, "run_num": 1, "need_fan_count": 320000},
                ],
                "single_mode_event_choice_reward": [
                    {"id": 1, "disp_type": 0, "effect_value_type_0": 2, "effect_value_type_1": 1, "effect_value_type_2": 0},
                ],
                "single_mode_event_item_detail": [
                    {"id": 1, "event_category_id": 177, "item_id": 1, "name_index": 180001},
                ],
                "single_mode_event_cr_priority": [
                    {"id": 7, "display_id": 1, "effect_value_condition_0": 11, "effect_value_condition_1": 0, "effect_value_condition_2": 0, "priority": 20},
                ],
                "single_mode_event_production": [
                    {"story_id": 400001017, "event_category_id": 180, "max_item_id": 1, "item_dir": "Rival", "item_name": "utx_ico_rival_item_{0:D2}"},
                ],
                "single_mode_event_conclusion": [
                    {"id": 1, "chara_id": 1001, "chara_motion_set_id": 40000},
                ],
            },
            "text": {
                "cat_180_text": [{"index": 180001, "text": "Hot Spring Ticket"}],
                "cat_181_text": [{"index": 400001017, "text": "A Three-Legged Race"}],
                "cat_182_text": [{"index": 1001, "text": "Special Week"}],
                "cat_177_text": [],
                "cat_178_text": [],
                "cat_179_text": [],
                "cat_23_text": [],
                "cat_225_text": [],
            },
        }

    def test_p3_master_exports_succession_career_event_data(self):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            (root / "data").mkdir()
            md = self._master_data()
            succession = master_data.synthesize_succession_scoring_core(root, md)
            career = master_data.synthesize_career_progression_core(root, md)
            event = master_data.synthesize_event_reward_display_core(root, md)
            self.assertEqual(succession["initial_factors"], 3)
            self.assertEqual(succession["relation_ranks"], 2)
            self.assertEqual(career["grades"], 3)
            self.assertEqual(event["choice_rewards"], 1)
            scoring = json.loads((root / "data" / "succession_scoring_core.json").read_text())
            self.assertEqual(scoring["initial_factors"][1]["add_point"], 12)
            progression = json.loads((root / "data" / "career_progression_core.json").read_text())
            self.assertEqual(progression["grades"][-1]["need_fan_count"], 320000)
            display = json.loads((root / "data" / "event_reward_display_core.json").read_text())
            self.assertEqual(display["choice_rewards"][0]["effect_value_labels"], ["stamina", "speed", "none"])
            self.assertEqual(display["item_details"][0]["name"], "Hot Spring Ticket")

    def test_event_manager_uses_official_display_labels_in_trace_reason(self):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            (root / "data").mkdir()
            master_data.synthesize_event_reward_display_core(root, self._master_data())
            manager = EventManager(root)
            score, reason = manager._score_outcome(
                None,
                {"display_id": 1, "params_inc_dec_info_array": [{"target_type": 1, "value": 5}]},
                {},
                {"vital": 80},
            )
            self.assertGreater(score, 0)
            self.assertIn("official_stamina", reason)
            self.assertIn("official_speed", reason)

    def test_race_entry_214_recovery_is_structured_not_printed(self):
        runner = CareerRunner(str(Path.cwd()))
        client = FakeClient214AtRaceEntry()
        state = {"data": {"home_info": {}, "chara_info": {"turn": 11}}}
        payload = {"program_id": 100, "current_turn": 11, "_strategy": FakeStrategy()}
        buf = io.StringIO()
        with contextlib.redirect_stdout(buf):
            recovered = runner._race(client, state, {"scenario_id": 1}, payload)
        self.assertEqual((recovered.get("data") or {}).get("chara_info", {}).get("turn"), 12)
        self.assertNotIn("Race Entry Error", buf.getvalue())


if __name__ == "__main__":
    unittest.main()
