import json
import tempfile
import unittest
from pathlib import Path

from career_bot import master_data
from career_bot.skills import SkillBuyer


class SweepyModV514MasterP2Tests(unittest.TestCase):
    def _master_data(self):
        return {
            "tables": {
                "skill_data": [
                    {
                        "id": 200512, "rarity": 1, "group_id": 20051, "group_rate": 1,
                        "filter_switch": 0, "grade_value": 120, "skill_category": 2,
                        "tag_id": "202", "icon_id": 2001, "activate_lot": 1,
                        "precondition_1": "", "condition_1": "distance_type==2",
                        "ability_type_1_1": 27, "ability_value_usage_1_1": 1,
                        "ability_value_level_usage_1_1": 1, "float_ability_value_1_1": 1500,
                        "target_type_1_1": 1, "target_value_1_1": 0,
                        "ability_type_1_2": 0, "ability_type_1_3": 0,
                        "precondition_2": "", "condition_2": "",
                        "ability_type_2_1": 0, "ability_type_2_2": 0, "ability_type_2_3": 0,
                        "disable_singlemode": 0, "is_general_skill": 0,
                    },
                    {
                        "id": 200513, "rarity": 2, "group_id": 20051, "group_rate": 1,
                        "filter_switch": 0, "grade_value": 220, "skill_category": 2,
                        "tag_id": "202", "icon_id": 2001, "activate_lot": 1,
                        "precondition_1": "", "condition_1": "distance_type==2",
                        "ability_type_1_1": 27, "ability_value_usage_1_1": 1,
                        "ability_value_level_usage_1_1": 1, "float_ability_value_1_1": 2500,
                        "target_type_1_1": 1, "target_value_1_1": 0,
                        "ability_type_1_2": 0, "ability_type_1_3": 0,
                        "precondition_2": "", "condition_2": "",
                        "ability_type_2_1": 0, "ability_type_2_2": 0, "ability_type_2_3": 0,
                        "disable_singlemode": 0, "is_general_skill": 0,
                    },
                ],
                "single_mode_skill_need_point": [
                    {"id": 200512, "need_skill_point": 120},
                    {"id": 200513, "need_skill_point": 180},
                ],
                "skill_level_value": [
                    {"id": 1, "ability_type": 27, "level": 1, "float_ability_value_coef": 10000},
                    {"id": 2, "ability_type": 27, "level": 2, "float_ability_value_coef": 11000},
                ],
                "skill_rarity": [{"id": 1, "value": 1}, {"id": 2, "value": 2}],
                "available_skill_set": [
                    {"id": 1, "available_skill_set_id": 100101, "skill_id": 200512, "need_rank": 0},
                ],
                "skill_set": [
                    {"id": 9081001, "skill_id1": 200512, "skill_level1": 1, "skill_id2": 200513, "skill_level2": 1},
                ],
                "card_data": [
                    {"id": 100101, "chara_id": 1001, "available_skill_set_id": 100101},
                ],
                "support_card_data": [
                    {"id": 30001, "rarity": 3, "command_id": 101, "support_card_type": 1, "skill_set_id": 9081001, "effect_table_id": 30001, "unique_effect_id": 40001, "outing_max": 0},
                ],
                "support_card_effect_table": [
                    {"id": 30001, "type": 1, "init": 5, "limit_lv5": -1, "limit_lv10": 10, "limit_lv15": -1, "limit_lv20": -1, "limit_lv25": -1, "limit_lv30": -1, "limit_lv35": 15, "limit_lv40": -1, "limit_lv45": -1, "limit_lv50": -1},
                    {"id": 30001, "type": 17, "init": 10, "limit_lv5": -1, "limit_lv10": -1, "limit_lv15": -1, "limit_lv20": 20, "limit_lv25": -1, "limit_lv30": -1, "limit_lv35": -1, "limit_lv40": -1, "limit_lv45": -1, "limit_lv50": -1},
                ],
                "support_card_unique_effect": [
                    {"id": 40001, "lv": 30, "type_0": 14, "value_0": 5, "value_0_1": 0, "value_0_2": 0, "value_0_3": 0, "value_0_4": 0, "type_1": 15, "value_1": 10, "value_1_1": 0, "value_1_2": 0, "value_1_3": 0, "value_1_4": 0},
                ],
                "support_card_level": [
                    {"id": 3001, "rarity": 3, "level": 1, "total_exp": 0},
                    {"id": 3002, "rarity": 3, "level": 2, "total_exp": 10},
                ],
                "single_mode_hint_gain": [
                    {"id": 1, "hint_id": 9001, "support_card_id": 30001, "hint_group": 1, "hint_gain_type": 0, "hint_value_1": 200512, "hint_value_2": 1},
                ],
            },
            "text": {
                "cat_47_text": [
                    {"index": 200512, "text": "Mile Skill ○"},
                    {"index": 200513, "text": "Mile Skill ◎"},
                ],
                "cat_4_text": [
                    {"index": 100101, "text": "Sample Trainee"},
                ],
                "cat_75_text": [
                    {"index": 30001, "text": "Sample Support"},
                ],
            },
        }

    def test_p2_master_exports_skill_support_data(self):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            (root / "data").mkdir()
            md = self._master_data()
            cond = master_data.synthesize_skill_condition_core(root, md)
            groups = master_data.synthesize_skill_upgrade_groups_core(root, md)
            sources = master_data.synthesize_skill_sources_core(root, md)
            hints = master_data.synthesize_support_hint_sources_core(root, md)
            support = master_data.synthesize_support_effects_resolved_core(root, md)
            self.assertEqual(cond["rows"], 2)
            self.assertEqual(groups["rows"], 1)
            self.assertEqual(sources["support_sources"], 1)
            self.assertEqual(hints["hints"], 1)
            self.assertEqual(support["support_cards"], 1)
            conditions = json.loads((root / "data" / "skill_condition_core.json").read_text())
            self.assertEqual(conditions[0]["conditions"], ["distance_type==2"])
            self.assertEqual(conditions[0]["effect_blocks"][0]["ability_type"], 27)
            source_payload = json.loads((root / "data" / "skill_sources_core.json").read_text())
            self.assertIn("200512", source_payload["skill_to_sources"])
            effect_payload = json.loads((root / "data" / "support_effects_resolved_core.json").read_text())
            row = effect_payload["support_cards"][0]
            self.assertEqual(row["effect_values_by_level"]["10"]["friendship_bonus"], 10)
            self.assertEqual(row["effect_values_by_level"]["35"]["friendship_bonus"], 15)
            self.assertEqual(row["hint_skill_count"], 1)

    def test_skill_buyer_uses_p2_sources_for_scoring_reasons(self):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            (root / "data").mkdir()
            md = self._master_data()
            master_data.synthesize_skill_data(root, md)
            master_data.synthesize_skill_weighting_core(root, md)
            master_data.synthesize_skill_condition_core(root, md)
            master_data.synthesize_skill_sources_core(root, md)
            buyer = SkillBuyer(root)
            score, reasons = buyer._skill_smart_score(
                200512,
                "Mile Skill ○",
                "Mile Skill",
                1,
                {"primary_distances": ["mile"], "running_style": "front", "track": "turf"},
                {"skill_strategy": {"weights": {"distance": 75}}},
            )
            self.assertGreater(score, 0)
            self.assertTrue(any(reason.startswith("support_sources:") for reason in reasons))
            self.assertTrue(any(reason.startswith("trainee_sources:") for reason in reasons))


if __name__ == "__main__":
    unittest.main()
