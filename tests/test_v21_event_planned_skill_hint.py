"""v2.1: skill-aware event-choice picking.

When an event choice grants a HINT for a skill the user explicitly planned to
buy (skill_strategy.forced_skills or manual_skill_tiers, minus blacklist), the
choice scorer adds a MODERATE bonus — enough to outrank a small stat/energy
advantage, but not a big swing. The per-choice hinted skill ids come from the
gametora scrape's raw array (t=='sk', d=skill_id); planned NAMES are resolved to
ids via skill_data.json. Reactive: applied when the event fires, no prediction.
"""
import pathlib
import unittest

from career_bot.events import EventManager

PLANNED_ID = 200242   # "Snowy Days"


def _em(choice2_effect="Stamina +40"):
    em = EventManager(pathlib.Path("."))
    # inject a tiny name->id map so the test doesn't depend on skill_data.json
    em._skill_name_to_ids = {"snowydays": {PLANNED_ID}}
    em._skill_id_to_name = {PLANNED_ID: "Snowy Days"}
    em._planned_cache = (None, set())
    em.scraped_effects = {"ev1": {
        "event_name": "Test Event", "category": "support_card",
        "choices": {
            "1": {"effect": "Skill hint +1", "raw": [{"t": "sk", "d": PLANNED_ID}]},
            "2": {"effect": choice2_effect, "raw": []},
        }}}
    em._scraped_name_index = None
    return em


def _event():
    return {"story_id": "ev1", "event_contents_info": {
        "title": "Test Event",
        "choice_array": [{"select_index": 1}, {"select_index": 2}]}}


class PlannedSkillHintTests(unittest.TestCase):
    def test_no_plan_big_stat_choice_wins(self):
        # planned set empty -> generic hint (25) loses to Stamina +40.
        em = _em()
        self.assertEqual(em.choose(_event(), preset={}), 1)

    def test_planned_hint_flips_a_small_stat_advantage(self):
        # Small stat edge: without a plan the stat choice wins; planning the hinted
        # skill flips the decision to the hint. (Stamina +15 ~= 30 < hint 55.)
        em_noplan = _em(choice2_effect="Stamina +15")
        self.assertEqual(em_noplan.choose(_event(), preset={}), 1)
        em_plan = _em(choice2_effect="Stamina +15")
        preset = {"skill_strategy": {"forced_skills": ["Snowy Days"]}}
        self.assertEqual(em_plan.choose(_event(), preset=preset), 0)

    def test_planned_hint_via_manual_tiers(self):
        em = _em(choice2_effect="Stamina +15")
        preset = {"manual_skill_tiers": {"1": ["Snowy Days"], "2": []}}
        self.assertEqual(em.choose(_event(), preset=preset), 0)

    def test_blacklisted_planned_skill_is_not_chased(self):
        # forced + blacklisted -> excluded from the planned set -> stat wins again.
        em = _em(choice2_effect="Stamina +40")
        preset = {"skill_strategy": {"forced_skills": ["Snowy Days"],
                                     "blacklist": ["Snowy Days"]}}
        self.assertEqual(em.choose(_event(), preset=preset), 1)

    def test_big_swing_still_wins_even_when_planned(self):
        # a huge stat choice beats the planned hint (moderate, not aggressive).
        em = _em(choice2_effect="Speed +300")
        preset = {"skill_strategy": {"forced_skills": ["Snowy Days"]}}
        self.assertEqual(em.choose(_event(), preset=preset), 1)

    def test_planned_skill_ids_resolution(self):
        em = _em()
        ids = em._planned_skill_ids({"skill_strategy": {"forced_skills": ["Snowy Days"]}})
        self.assertIn(PLANNED_ID, ids)
        ids2 = em._planned_skill_ids({"skill_strategy": {"forced_skills": [PLANNED_ID]}})
        self.assertIn(PLANNED_ID, ids2)   # raw id accepted too
        ids3 = em._planned_skill_ids({})
        self.assertEqual(ids3, set())


if __name__ == "__main__":
    unittest.main()
