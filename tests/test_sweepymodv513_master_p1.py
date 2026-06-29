import json
import tempfile
import unittest
from pathlib import Path
from types import SimpleNamespace

from career_bot import master_data, trackblazer
from career_bot.scenarios.mant import MantStrategy


class SweepyModV513MasterP1Tests(unittest.TestCase):
    def _master_data(self):
        return {
            "tables": {
                "single_mode_training": [
                    {"id": 1, "command_id": 101, "base_command_id": 101, "command_level": 1, "command_type": 1, "failure_rate": 520, "max_chara_num": 2},
                    {"id": 2, "command_id": 105, "base_command_id": 105, "command_level": 1, "command_type": 1, "failure_rate": 520, "max_chara_num": 2},
                ],
                "single_mode_training_effect": [
                    {"id": 1, "command_id": 101, "sub_id": 1, "result_state": 2, "target_type": 1, "effect_value": 10, "scenario_id": 4},
                    {"id": 2, "command_id": 101, "sub_id": 1, "result_state": 2, "target_type": 3, "effect_value": 5, "scenario_id": 4},
                    {"id": 3, "command_id": 101, "sub_id": 1, "result_state": 2, "target_type": 30, "effect_value": 2, "scenario_id": 4},
                    {"id": 4, "command_id": 101, "sub_id": 1, "result_state": 2, "target_type": 10, "effect_value": -21, "scenario_id": 4},
                    {"id": 5, "command_id": 105, "sub_id": 1, "result_state": 2, "target_type": 2, "effect_value": 9, "scenario_id": 4},
                ],
                "single_mode_free_training_plate": [
                    {"id": 1, "condition_type": 1, "value_min": 110, "value_max": 150},
                ],
                "single_mode_scenario": [
                    {"id": 4, "sort_id": 3, "turn_set_id": 4, "chara_program_change_flag": 1},
                ],
                "single_mode_turn": [
                    {"id": 1, "turn_set_id": 4, "turn": 36, "year": 2, "month": 6, "half": 2, "period": 0, "training_set_id": 1, "outing_set_id": 1, "race_entry_type": 1, "unique_command": 1, "rest_type": 1, "health_room_type": 1},
                    {"id": 2, "turn_set_id": 4, "turn": 37, "year": 2, "month": 7, "half": 1, "period": 2, "training_set_id": 2, "outing_set_id": 1, "race_entry_type": 1, "unique_command": 1, "rest_type": 1, "health_room_type": 1},
                    {"id": 3, "turn_set_id": 4, "turn": 61, "year": 3, "month": 7, "half": 1, "period": 2, "training_set_id": 2, "outing_set_id": 1, "race_entry_type": 1, "unique_command": 1, "rest_type": 1, "health_room_type": 1},
                    {"id": 4, "turn_set_id": 4, "turn": 74, "year": 4, "month": 1, "half": 2, "period": 3, "training_set_id": 1, "outing_set_id": 1, "race_entry_type": 1, "unique_command": 1, "rest_type": 1, "health_room_type": 1},
                ],
            },
            "text": {},
        }

    def test_training_effects_and_scenario_turns_exports(self):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            (root / "data").mkdir()
            md = self._master_data()
            training = master_data.synthesize_training_effects_core(root, md)
            turns = master_data.synthesize_scenario_turns_core(root, md)
            self.assertEqual(training["rows"], 2)
            self.assertEqual(training["plates"], 1)
            self.assertEqual(turns["rows"], 4)
            payload = json.loads((root / "data" / "training_effects_core.json").read_text())
            speed = next(row for row in payload["training_effects"] if row["command_id"] == 101)
            self.assertEqual(speed["by_target"]["speed"], 10)
            self.assertEqual(speed["by_target"]["power"], 5)
            self.assertEqual(speed["skill_points"], 2)
            self.assertEqual(speed["energy_delta"], -21)
            calendar = json.loads((root / "data" / "scenario_turns_core.json").read_text())
            self.assertTrue(next(row for row in calendar if row["turn"] == 37)["is_summer"])
            self.assertTrue(next(row for row in calendar if row["turn"] == 74)["is_finale"])

    def test_mant_strategy_reads_official_baseline_when_payload_is_sparse(self):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            (root / "data").mkdir()
            master_data.synthesize_training_effects_core(root, self._master_data())
            strategy = MantStrategy(SimpleNamespace(base_dir=root))
            command = {"command_type": 1, "command_id": 101, "training_level": 1, "failure_rate": 0, "is_enable": 1}
            # The legacy _score_command / _official_training_summary were removed
            # along with the dormant Classic scorer; the shared official-baseline
            # lookup that feeds _command_main_stat_gain is still here.  Verify it
            # resolves the synthesized effect row and surfaces the speed/power/
            # skill-point/energy deltas.
            items = strategy._official_training_effect_items(command)
            by_target = {int(it["target_type"]): int(it["value"]) for it in items}
            self.assertEqual(by_target.get(1), 10)   # speed
            self.assertEqual(by_target.get(3), 5)    # power
            self.assertEqual(by_target.get(10), -21) # energy_delta

    def test_trackblazer_uses_official_scenario_summer_turns(self):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            (root / "data").mkdir()
            master_data.synthesize_scenario_turns_core(root, self._master_data())
            self.assertIn(37, trackblazer._scenario_summer_turns(root))
            self.assertIn(61, trackblazer._scenario_summer_turns(root))
            self.assertNotIn(36, trackblazer._scenario_summer_turns(root))


if __name__ == "__main__":
    unittest.main()
