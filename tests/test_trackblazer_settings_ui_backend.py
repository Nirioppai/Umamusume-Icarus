import tempfile
import unittest
from pathlib import Path

from career_bot.presets import hydrate_preset, serialize_preset
from career_bot.races import RacePlanner
from career_bot.scenarios.mant import MantStrategy


def training(command_id=101, gain=40, failure=0):
    main_target = {101: 1, 105: 2, 102: 3, 103: 4, 106: 5}.get(command_id, 1)
    return {
        "command_type": 1,
        "command_id": command_id,
        "command_group_id": 0,
        "select_id": 0,
        "is_enable": 1,
        "failure_rate": failure,
        "training_partner_array": [],
        "params_inc_dec_info_array": [{"target_type": main_target, "value": gain}],
    }


def rest():
    return {"command_type": 7, "command_id": 701, "command_group_id": 0, "is_enable": 1}


def chara(turn=30, vital=80):
    return {
        "turn": turn,
        "vital": vital,
        "max_vital": 100,
        "motivation": 4,
        "scenario_id": 4,
        "speed": 300,
        "stamina": 300,
        "power": 300,
        "guts": 300,
        "wiz": 300,
        "skill_point": 0,
        "proper_distance_short": 8,
        "proper_distance_mile": 8,
        "proper_distance_middle": 8,
        "proper_distance_long": 8,
        "proper_ground_turf": 8,
        "proper_ground_dirt": 8,
        "evaluation_info_array": [],
    }


class SettingsBackendTests(unittest.TestCase):
    def test_preset_preserves_mant_config(self):
        raw = {
            "name": "settings-test",
            "mant_config": {
                "maximum_failure_chance": 12,
                "enable_farming_fans": True,
                "preferred_distances": ["mile"],
            },
        }
        serialized = serialize_preset(raw)
        hydrated = hydrate_preset(serialized)
        self.assertEqual(hydrated["mant_config"]["maximum_failure_chance"], 12)
        self.assertTrue(hydrated["mant_config"]["enable_farming_fans"])
        self.assertEqual(hydrated["mant_config"]["preferred_distances"], ["mile"])

    def test_training_blacklist_and_failure_settings_are_enforced(self):
        strategy = MantStrategy()
        data = {"home_info": {"command_info_array": [training(101, gain=100), training(105, gain=10)]}}
        best = strategy._best_command(data, chara(), {"compensate_failure": False, "mant_config": {"training_blacklist": ["speed"]}})
        self.assertEqual(best["command_id"], 105)

        risky = {"home_info": {"command_info_array": [training(101, gain=100, failure=45), training(105, gain=10, failure=0)]}}
        no_risky = strategy._best_command(risky, chara(), {"compensate_failure": False, "mant_config": {"maximum_failure_chance": 20}})
        self.assertEqual(no_risky["command_id"], 105)
        yes_risky = strategy._best_command(risky, chara(), {"compensate_failure": False, "mant_config": {"maximum_failure_chance": 20, "enable_risky_training": True, "risky_training_min_stat_gain": 50, "risky_training_max_failure_chance": 50}})
        self.assertEqual(yes_risky["command_id"], 101)

    def test_force_train_energy_floor_recovers_in_summer(self):
        strategy = MantStrategy()
        data = {"home_info": {"command_info_array": [training(101, gain=100), rest()]}}
        best = strategy._best_command(data, chara(turn=37, vital=15), {"compensate_failure": False, "mant_config": {"force_train_energy_floor": 20}})
        self.assertEqual(best["command_type"], 7)

    def test_farming_and_force_racing_choose_available_race(self):
        with tempfile.TemporaryDirectory() as td:
            base = Path(td)
            (base / "data").mkdir()
            (base / "data" / "race_map.json").write_text('{"program":{"100":{"name":"Test G1","grade":"G1","distance":1600,"ground":1}},"meta":{},"instance":{}}', encoding="utf-8")
            planner = RacePlanner(base)
            state = {
                "data": {
                    "chara_info": chara(turn=30),
                    "home_info": {"command_info_array": [{"command_type": 4, "command_id": 401, "is_enable": 1}]},
                    "race_condition_array": [{"program_id": 100}],
                    "free_data_set": {},
                }
            }
            self.assertEqual(planner.choose(state, {"mant_config": {"enable_farming_fans": True, "days_to_run_extra_races": 5}}), 100)
            state["data"]["chara_info"]["turn"] = 31
            self.assertEqual(planner.choose(state, {"mant_config": {"force_racing": True}}), 100)


if __name__ == "__main__":
    unittest.main()
