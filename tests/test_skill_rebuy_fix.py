"""Regression for the skill re-buy bug.

chara_info.skill_array is a PARTIAL rotating view (a handful of skills), NOT the
full owned set, and there is no fuller owned-skills field. So SkillBuyer must
accumulate a career-persistent acquired set: a skill seen owned once must never be
re-bought, even after it rotates out of the partial view. (Fast-Paced / 200542 was
sent to gain_skills 15x in one career despite being owned early on.)
"""
import unittest
from pathlib import Path

from career_bot.skills import SkillBuyer

BASE = Path(__file__).resolve().parents[1]


def chara(skill_array_ids, turn=30, skill_point=500):
    return {
        "turn": turn,
        "skill_point": skill_point,
        "speed": 400, "stamina": 300, "power": 400, "guts": 300, "wiz": 300,
        "proper_distance_short": 4, "proper_distance_mile": 5,
        "proper_distance_middle": 4, "proper_distance_long": 1,
        "proper_ground_turf": 5, "proper_ground_dirt": 1,
        "skill_array": [{"skill_id": sid} for sid in skill_array_ids],
        "skill_tips_array": [],
    }


class AcquiredSkillSetTests(unittest.TestCase):
    def setUp(self):
        self.b = SkillBuyer(BASE)

    def test_seen_owned_skill_is_remembered_after_it_leaves_skill_array(self):
        # Early turn: the partial skill_array includes 200542.
        self.b._candidates(chara([200542, 200111], turn=12), {})
        self.assertIn(200542, self.b._acquired_skill_ids)
        # Many turns later: the partial view rotated; 200542 is gone but must persist.
        self.b._candidates(chara([200111, 200222], turn=55), {})
        self.assertIn(200542, self.b._acquired_skill_ids,
                      "acquired set must remember 200542 after it left the partial skill_array")
        self.assertIn(200222, self.b._acquired_skill_ids)

    def test_acquired_set_is_per_instance(self):
        # Each career gets a fresh SkillBuyer (runner recreates it in start()), so the
        # acquired set must not leak across careers.
        b2 = SkillBuyer(BASE)
        self.b._acquired_skill_ids.add(200542)
        self.assertNotIn(200542, b2._acquired_skill_ids)


if __name__ == "__main__":
    unittest.main()
