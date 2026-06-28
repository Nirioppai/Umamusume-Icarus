import tempfile
import unittest
from pathlib import Path

from career_bot.races import RacePlanner
from career_bot.scenarios.mant import MantStrategy


def training(command_id=101, gain=40, failure=0, partners=None, level=None):
    main_target = {101: 1, 105: 2, 102: 3, 103: 4, 106: 5}.get(command_id, 1)
    row = {
        "command_type": 1,
        "command_id": command_id,
        "command_group_id": 0,
        "select_id": 0,
        "is_enable": 1,
        "failure_rate": failure,
        "training_partner_array": partners or [],
        "params_inc_dec_info_array": [{"target_type": main_target, "value": gain}],
    }
    if level is not None:
        row["training_level"] = level
    return row


def chara(turn=30, bonds=None):
    return {
        "turn": turn,
        "vital": 80,
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
        "evaluation_info_array": [
            {"target_id": int(pid), "evaluation": int(value)}
            for pid, value in (bonds or {}).items()
        ],
    }


def state_for_races(turn=30, available=None, rivals=None):
    return {
        "data": {
            "chara_info": chara(turn=turn),
            "home_info": {"command_info_array": [{"command_type": 4, "command_id": 401, "is_enable": 1}]},
            "race_condition_array": [{"program_id": pid} for pid in (available or [])],
            "free_data_set": {
                "rival_race_info_array": [
                    {"program_id": pid, "chara_id": 900000 + i}
                    for i, pid in enumerate(rivals or [])
                ]
            },
        }
    }


class TrackblazerP2RacePlannerTests(unittest.TestCase):
    def planner(self):
        tmp = Path(tempfile.mkdtemp())
        (tmp / "data").mkdir()
        planner = RacePlanner(tmp)
        planner.program = {
            100: {"name": "Preferred G3", "grade": "G3", "distance": 1200, "ground": 1, "fans": 10000},
            200: {"name": "Nonpreferred G1", "grade": "G1", "distance": 2000, "ground": 1, "fans": 20000},
            300: {"name": "Preferred G1", "grade": "G1", "distance": 1600, "ground": 1, "fans": 18000},
        }
        return planner

    def test_preferred_distance_sorts_before_grade_inside_trackblazer_plan(self):
        planner = self.planner()
        st = state_for_races(available=[100, 200])
        chosen = planner.choose(st, {
            "extra_race_list": [200, 100],
            "mant_config": {"preferred_distances": ["short"]},
        })
        self.assertEqual(chosen, 100)

    def test_rival_race_has_top_priority(self):
        planner = self.planner()
        st = state_for_races(available=[100, 200], rivals=[100])
        chosen = planner.choose(st, {"extra_race_list": [200, 100], "mant_config": {}})
        self.assertEqual(chosen, 100)

    def test_smart_solver_train_turn_blocks_fallback_race(self):
        planner = self.planner()
        st = state_for_races(available=[300], rivals=[])
        chosen = planner.choose(st, {
            "extra_race_list": [300],
            "trackblazer_last_plan": {"decisions": {"30": {"type": "train"}}},
            "mant_config": {},
        })
        self.assertEqual(chosen, 0)


if __name__ == "__main__":
    unittest.main()
