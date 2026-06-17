import json
import tempfile
import unittest
from pathlib import Path

from career_bot.races import RacePlanner
from career_bot.skills import SkillBuyer
from career_bot.items import load_master_shop_core


class MasterDataExtendedIntegrationTests(unittest.TestCase):
    def setUp(self):
        self.tmp = Path(tempfile.mkdtemp())
        data = self.tmp / "data"
        data.mkdir(parents=True)
        (self.tmp / "public" / "assets" / "data").mkdir(parents=True)

        (data / "race_map.json").write_text(json.dumps({
            "meta": {},
            "program": {"101": {"race_instance_id": 9001, "name": "Old Name", "ground": 1, "distance": 1600}},
            "instance": {"9001": [101]}
        }), encoding="utf-8")
        (data / "race_planner_core.json").write_text(json.dumps([
            {
                "program_id": 101,
                "race_instance_id": 9001,
                "turn": 31,
                "name": "Official Mile",
                "grade": "G1",
                "ground": 1,
                "terrain": "Turf",
                "distance_m": 1600
            }
        ]), encoding="utf-8")

        (data / "skill_data.json").write_text(json.dumps({
            "100": {
                "name": "Test Skill",
                "rarity": 1,
                "group_id": 10,
                "grade_value": 200,
                "need_skill_point": 100,
                "tags": [101],
                "skill_category": 1,
                "icon_id": 2001
            }
        }), encoding="utf-8")
        (data / "skill_weighting_core.json").write_text(json.dumps([
            {
                "skill_id": 100,
                "cost": 100,
                "grade_value": 200,
                "ability_types": [27],
                "conditions": ["phase>=1"],
                "disable_singlemode": 0,
                "is_general_skill": 1
            }
        ]), encoding="utf-8")

        (data / "mant_shop_core.json").write_text(json.dumps({
            "items": [
                {
                    "item_id": 1001,
                    "name": "Speed Notepad",
                    "coin_num": 10,
                    "use_flag": 1,
                    "effect_priority": 0,
                    "effects": [{"effect_type": 1, "effect_value_1": 1, "effect_value_2": 3}]
                }
            ],
            "shops": [{"start_turn": 13, "end_turn": 18}]
        }), encoding="utf-8")

    def test_race_planner_loads_official_core(self):
        planner = RacePlanner(self.tmp)
        self.assertIn(101, planner.official_races)
        self.assertIn("Official Mile", planner.label(101))

    def test_skill_buyer_loads_official_weights(self):
        buyer = SkillBuyer(self.tmp)
        self.assertIn(100, buyer.official_skill_weights)
        score, reasons = buyer._skill_smart_score(
            100, "Test Skill", "Test Skill", 0,
            {"running_style": "front", "primary_distances": [], "secondary_distances": [], "avoid_distances": []},
            preset={}
        )
        self.assertTrue(any("official_master" in r for r in reasons))

    def test_shop_core_loader(self):
        core = load_master_shop_core(self.tmp)
        self.assertIn(1001, core["by_id"])
        self.assertIn("Speed Notepad", core["by_name"])


if __name__ == "__main__":
    unittest.main()
