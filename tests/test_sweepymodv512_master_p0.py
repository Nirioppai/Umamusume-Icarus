import json
import tempfile
import unittest
from pathlib import Path

from career_bot import master_data, trackblazer
from career_bot.races import RacePlanner


class SweepyModV512MasterP0Tests(unittest.TestCase):
    def _master_data(self):
        return {
            "tables": {
                "single_mode_program": [
                    {"id": 10, "race_instance_id": 1000, "month": 5, "half": 1, "race_permission": 3, "fan_set_id": 1, "need_fan_count": 0, "reward_set_id": 500},
                    {"id": 20, "race_instance_id": 2000, "month": 5, "half": 1, "race_permission": 3, "fan_set_id": 2, "need_fan_count": 0, "reward_set_id": 501},
                ],
                "race_instance": [
                    {"id": 1000, "race_id": 100},
                    {"id": 2000, "race_id": 200},
                ],
                "race": [
                    {"id": 100, "grade": 100, "course_set": 1},
                    {"id": 200, "grade": 300, "course_set": 2},
                ],
                "race_course_set": [
                    {"id": 1, "ground": 1, "distance": 1600, "race_track_id": 10006},
                    {"id": 2, "ground": 2, "distance": 1200, "race_track_id": 10101},
                ],
                "single_mode_fan_count": [
                    {"fan_set_id": 1, "order": 1, "fan_count": 10000},
                    {"fan_set_id": 2, "order": 1, "fan_count": 2500},
                ],
                "single_mode_route": [
                    {"id": 1, "scenario_id": 0, "chara_id": 1001, "race_set_id": 77, "condition_set_id": 0, "priority": 0},
                ],
                "single_mode_route_race": [
                    {"id": 1, "race_set_id": 77, "target_type": 1, "sort_id": 1, "turn": 33, "race_type": 0, "condition_type": 1, "condition_id": 10, "condition_value_1": 0, "condition_value_2": 0, "determine_race": 1, "determine_race_flag": 0},
                ],
                "single_mode_route_condition": [],
                "single_mode_rival": [
                    {"id": 1, "chara_id": 1001, "turn": 33, "race_program_id": 10, "rival_flag_id": 0, "condition_type": 1, "rival_chara_id": 1002, "single_mode_npc_id": 10020, "frame_order": 0},
                ],
                "single_mode_free_coin_race": [
                    {"grade": 100, "order_min": 1, "order_max": 1, "coin_num": 100},
                    {"grade": 300, "order_min": 1, "order_max": 1, "coin_num": 40},
                ],
                "single_mode_free_win_point": [
                    {"race_group_id": 0, "grade": 100, "order_min": 1, "order_max": 1, "point_num": 100},
                    {"race_group_id": 0, "grade": 300, "order_min": 1, "order_max": 1, "point_num": 40},
                ],
                "single_mode_reward_set": [
                    {"reward_set_id": 500, "order_min": 1, "order_max": 1, "reward_type": 1, "bonus": 0, "odds": 1000000, "item_category": 91, "item_id": 59, "item_num": 400},
                ],
                "single_mode_race_group": [
                    {"race_group_id": 9, "race_program_id": 10},
                ],
                "race_proper_distance_rate": [
                    {"id": 7, "proper_rate_speed": 10000, "proper_rate_power": 10000},
                    {"id": 1, "proper_rate_speed": 1000, "proper_rate_power": 4000},
                ],
                "race_proper_ground_rate": [
                    {"id": 7, "proper_rate": 10000},
                    {"id": 1, "proper_rate": 1000},
                ],
                "race_proper_runningstyle_rate": [
                    {"id": 7, "proper_rate": 10000},
                ],
                "race_motivation_rate": [
                    {"id": 3, "motivation_rate": 10000},
                ],
                "race_course_set_status": [
                    {"course_set_status_id": 1, "target_status_1": 1, "target_status_2": 0},
                ],
                "race_popularity_proper_value": [
                    {"id": 1, "proper_type": 1, "proper_grade": 7, "value": 45},
                ],
            },
            "text": {
                "cat_28_text": [
                    {"index": 1000, "text": "Sample Mile Cup"},
                    {"index": 2000, "text": "Sample Dirt Sprint"},
                ],
                "cat_4_text": [
                    {"index": 100201, "text": "Rival Girl"},
                ],
            },
        }

    def test_p0_master_exports_are_generated(self):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            (root / "data").mkdir()
            md = self._master_data()
            route = master_data.synthesize_chara_route_core(root, md)
            rivals = master_data.synthesize_rival_races_core(root, md)
            rewards = master_data.synthesize_trackblazer_race_rewards_core(root, md)
            rates = master_data.synthesize_race_performance_rates_core(root, md)
            self.assertEqual(route["rows"], 1)
            self.assertEqual(rivals["rows"], 1)
            self.assertEqual(rewards["rows"], 2)
            self.assertEqual(rates["distance"], 2)
            route_rows = json.loads((root / "data" / "chara_route_core.json").read_text())
            self.assertEqual(route_rows[0]["candidate_program_ids"], [10])
            reward_rows = json.loads((root / "data" / "trackblazer_race_rewards_core.json").read_text())
            row10 = next(r for r in reward_rows if r["program_id"] == 10)
            self.assertEqual(row10["fans_first"], 10000)
            self.assertEqual(row10["coin_rewards"][0]["coin_num"], 100)
            self.assertEqual(row10["win_point_rewards"][0]["point_num"], 100)

    def test_race_planner_uses_static_rival_and_reward_score(self):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            (root / "data").mkdir()
            (root / "public" / "assets" / "data").mkdir(parents=True)
            md = self._master_data()
            master_data.synthesize_race_map(root, md)
            master_data.synthesize_race_planner_core(root, md)
            master_data.synthesize_rival_races_core(root, md)
            master_data.synthesize_trackblazer_race_rewards_core(root, md)
            planner = RacePlanner(root)
            state = {"data": {"chara_info": {"chara_id": 1001, "turn": 33, "scenario_id": 4, "proper_distance_mile": 7, "proper_distance_short": 7, "proper_ground_turf": 7, "proper_ground_dirt": 7}}}
            self.assertIn(10, planner.get_rival_race_map(state))
            self.assertGreater(planner._trackblazer_reward_score(10), planner._trackblazer_reward_score(20))
            self.assertEqual(planner._sort_races_for_trackblazer([20, 10], state, {}), [10, 20])

    def test_trackblazer_candidates_include_official_rewards_and_rates(self):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            (root / "data").mkdir()
            (root / "data" / "trackblazer").mkdir()
            (root / "public" / "assets" / "data").mkdir(parents=True)
            md = self._master_data()
            master_data.synthesize_race_map(root, md)
            master_data.synthesize_race_planner_core(root, md)
            master_data.synthesize_trackblazer_race_rewards_core(root, md)
            master_data.synthesize_race_performance_rates_core(root, md)
            (root / "data" / "trackblazer" / "races.json").write_text(json.dumps([
                {"name": "Sample Mile Cup", "grade": "G1", "distance": "Mile", "surface": "Turf", "fans": 0},
            ]), encoding="utf-8")
            (root / "data" / "trackblazer" / "epithets.json").write_text("[]", encoding="utf-8")
            (root / "data" / "trackblazer" / "debut_races.json").write_text("[]", encoding="utf-8")
            rows = trackblazer._candidate_rows(root, aptitudes={"Mile": "A", "Turf": "A"}, include_op=True, floor=1)
            self.assertEqual(len(rows), 1)
            self.assertEqual(rows[0]["program_id"], 10)
            self.assertEqual(rows[0]["fans"], 10000)
            self.assertEqual(rows[0]["coin_reward"], 100)
            self.assertEqual(rows[0]["win_points"], 100)
            self.assertGreaterEqual(rows[0]["performance_rate"], 1.0)
            self.assertGreater(trackblazer._smart_race_score(rows[0], {"trackblazerRewardWeight": 0.2}), 0)


if __name__ == "__main__":
    unittest.main()
