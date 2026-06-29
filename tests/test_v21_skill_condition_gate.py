"""Stage 1 of the skill-purchase redesign: schedule-aware activation-condition gate.

A skill only activates when its conditions hold. Some conditions are
TRAINEE-DETERMINABLE up front (running_style, distance_type) — if they can never
be satisfied by THIS trainee/schedule the skill is a dead SP sink. Dynamic,
in-race conditions (order_rate, distance_rate, corner, phase, ...) are NOT gated
(they can happen during any race) to avoid false positives.

evaluate_skill_conditions(conditions, style_id, distance_keys) -> can_fire:bool
  conditions: list of strings; "@" = OR of alternative groups, "&" = AND of
  predicates. The skill can fire if AT LEAST ONE @-group has no determinable
  predicate that is provably unsatisfiable. running_style ids: front1/pace2/late3/end4.
  distance_type ids: 1 sprint / 2 mile / 3 medium / 4 long.
"""
import unittest

from career_bot.skills import evaluate_skill_conditions as ev


class TestConditionFeasibility(unittest.TestCase):
    def test_no_conditions_can_fire(self):
        self.assertTrue(ev([], 1, {"mile"}))
        self.assertTrue(ev(None, 1, {"mile"}))

    def test_running_style_match(self):
        self.assertTrue(ev(["running_style==1"], 1, {"mile"}))   # front skill on front
        self.assertFalse(ev(["running_style==3"], 1, {"mile"}))  # late skill on front -> dead
        self.assertTrue(ev(["running_style==3"], 3, {"mile"}))   # late skill on late

    def test_running_style_unknown_does_not_block(self):
        self.assertTrue(ev(["running_style==3"], None, {"mile"}))  # style unknown -> don't gate

    def test_running_style_not_equal(self):
        self.assertFalse(ev(["running_style!=1"], 1, {"mile"}))  # "!=front" can't fire for a front runner
        self.assertTrue(ev(["running_style!=1"], 2, {"mile"}))

    def test_or_groups(self):
        # second @-group is satisfiable -> can fire
        self.assertTrue(ev(["running_style==1@running_style==3"], 3, {"mile"}))
        # both groups blocked -> dead
        self.assertFalse(ev(["running_style==1@running_style==2"], 4, {"mile"}))

    def test_distance_type(self):
        self.assertTrue(ev(["distance_type==1"], 1, {"sprint"}))         # sprint skill, races sprint
        self.assertFalse(ev(["distance_type==1"], 1, {"long"}))          # sprint skill, only long -> dead
        self.assertTrue(ev(["distance_type==4"], 3, {"long", "medium"}))  # long skill, races long
        self.assertTrue(ev(["distance_type==1"], 1, set()))              # distances unknown -> don't gate

    def test_and_group_blocked_by_either(self):
        # front+sprint skill on a front runner who only races long -> distance blocks
        self.assertFalse(ev(["running_style==1&distance_type==1"], 1, {"long"}))
        self.assertTrue(ev(["running_style==1&distance_type==1"], 1, {"sprint"}))

    def test_dynamic_only_conditions_never_gated(self):
        # order_rate / distance_rate / corner are in-race dynamic -> always feasible
        self.assertTrue(ev(["order_rate>50&corner==1"], 1, {"mile"}))
        self.assertTrue(ev(["distance_rate>=50&distance_rate<=60&order_rate>50"], 1, {"mile"}))
        self.assertTrue(ev(["is_finalcorner==1&order>=3"], 1, {"sprint"}))

    def test_similar_key_not_confused_with_running_style(self):
        # 'running_style_count_same' is a different (dynamic) key, must not be gated
        self.assertTrue(ev(["running_style_count_same<=1"], 1, {"mile"}))

    def test_mixed_all_groups_blocked(self):
        self.assertFalse(ev(["running_style==3&order_rate>50@distance_type==2"], 1, {"long"}))

    def test_mixed_one_group_ok(self):
        self.assertTrue(ev(["running_style==3@distance_type==4"], 1, {"long"}))  # 2nd group ok


class TestCanFireWiring(unittest.TestCase):
    def _buyer(self):
        from career_bot.skills import SkillBuyer
        b = SkillBuyer.__new__(SkillBuyer)
        b.official_skill_conditions = {
            500: {"conditions": ["running_style==3"]},  # late-surger skill
            501: {"conditions": []},                     # unconditional
            502: {"conditions": ["distance_type==1"]},   # sprint-only skill
        }
        b._selected_style_key = lambda preset, profile: "front"   # style id 1
        b._trainee_distance_keys = lambda profile, preset: {"mile", "medium"}
        return b

    def test_late_skill_on_front_runner_cannot_fire(self):
        self.assertFalse(self._buyer()._skill_condition_can_fire(500, {}, {}))

    def test_unconditional_skill_can_fire(self):
        self.assertTrue(self._buyer()._skill_condition_can_fire(501, {}, {}))

    def test_sprint_skill_when_no_sprints_cannot_fire(self):
        self.assertFalse(self._buyer()._skill_condition_can_fire(502, {}, {}))

    def test_unknown_skill_id_is_conservative_true(self):
        self.assertTrue(self._buyer()._skill_condition_can_fire(9999, {}, {}))


if __name__ == "__main__":
    unittest.main()
