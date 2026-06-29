"""Team Sirius + Heirs to the Throne group-card outings (v2).

Covers BOTH modes from STEAL_THE_MOOON.md, adapted to Icarus (knobs in mant_config):
- shared: deck detection, strategy-mode resolver, state readers, outing plan,
  the 390-skip recreation guard, camp-turn-set parity.
- scheduled (Mode A): goal-driven _scheduled_recreation (earliest-due, catch-up,
  card steps, blackout, opt-out, block-flag isolation).
- free (Mode B): _free_outing_select_id + _free_group_outing.
- summer all-out: _can_rescue_training camp gate (scheduled mode + group deck only).
"""
import sys
import unittest
from unittest.mock import MagicMock

for _m in ("msgpack",):
    sys.modules.setdefault(_m, MagicMock())

from career_bot.scenarios.mant import (
    MantStrategy, GROUP_OUTING_COMMAND_ID, CARD_SIGNATURE_CHARA, GOOD_LUCK_CHARM_ID,
    RECREATION_BLACKOUT_TURNS, RACE_VALUE_CAMP_TURNS, SIRIUS_THRONE_RECREATION_SCHEDULE,
)
from career_bot.items import SUMMER_TRAINING_TURNS

S = MantStrategy()
ALL_CHARS = [1002, 1016, 1017, 1030, 1001, 1003, 1013, 1073, 1035]


def chara(turn=18, deck=(30081, 30067), chars=None, cards=None):
    chars = chars or {}
    cards = cards or {}
    pos = {sid: 5 + i for i, sid in enumerate(deck)}
    sca = [{"support_card_id": sid, "position": pos[sid]} for sid in deck]
    goa = [{"chara_id": cid, "is_outing": io, "story_step": ss} for cid, (io, ss) in chars.items()]
    eva = [{"target_id": 0, "group_outing_info_array": goa}]
    for sid, (io, ss) in cards.items():
        eva.append({"target_id": pos[sid], "is_outing": io, "story_step": ss})
    return {"turn": turn, "support_card_array": sca, "evaluation_info_array": eva}


def cmds(with_390=True, with_301=True, with_train=True):
    c = []
    if with_train:
        c.append({"command_type": 1, "command_id": 101, "is_enable": 1})
    if with_390:
        c.append({"command_type": 3, "command_id": 390, "is_enable": 1})
    if with_301:
        c.append({"command_type": 3, "command_id": 301, "is_enable": 1})
    return c


def preset(**mant):
    return {"mant_config": dict(mant)}


def all_chars_done():
    return {cid: (1, 1) for cid in ALL_CHARS}


class DeckDetection(unittest.TestCase):
    def test_detects_team_sirius(self):
        self.assertTrue(S._deck_has_group_cards(chara(deck=(30081,))))

    def test_detects_throne(self):
        self.assertTrue(S._deck_has_group_cards(chara(deck=(30067,))))

    def test_plain_deck_not_detected(self):
        self.assertFalse(S._deck_has_group_cards(chara(deck=(20001, 20002))))


class StrategyMode(unittest.TestCase):
    def test_explicit_values(self):
        for m in ("scheduled", "free", "off"):
            self.assertEqual(S._strategy_mode(chara(), preset(sirius_throne_strategy=m)), m)

    def test_auto_group_deck_is_scheduled(self):
        self.assertEqual(S._strategy_mode(chara(deck=(30081,)), preset()), "scheduled")

    def test_auto_plain_deck_is_off(self):
        self.assertEqual(S._strategy_mode(chara(deck=(20001,)), preset()), "off")

    def test_blank_resolves_like_auto(self):
        self.assertEqual(S._strategy_mode(chara(deck=(30081,)), preset(sirius_throne_strategy="")), "scheduled")


class Readers(unittest.TestCase):
    def test_char_outing_state(self):
        c = chara(chars={1002: (1, 0), 1016: (1, 1)})
        self.assertEqual(S._char_outing_state(c, 1002), (1, 0))
        self.assertEqual(S._char_outing_state(c, 1016), (1, 1))
        self.assertEqual(S._char_outing_state(c, 9999), (0, 0))

    def test_card_row_state(self):
        c = chara(cards={30067: (1, 1)})
        self.assertEqual(S._card_row_state(c, 30067), (1, 1))
        self.assertEqual(S._card_row_state(c, 30081), (0, 0))

    def test_group_card_slots(self):
        self.assertEqual(set(S._group_card_slots(chara(deck=(30081, 30067)))), {5, 6})


class OutingPlan(unittest.TestCase):
    def test_outing_plan_has_correct_card_steps(self):
        plan = S._outing_plan()
        self.assertEqual(len(plan), 12)
        cards = [s for s in plan if s["kind"] == "card"]
        self.assertEqual(len([s for s in cards if s["support_id"] == 30067]), 2)
        self.assertEqual(len([s for s in cards if s["support_id"] == 30081]), 1)
        self.assertEqual([s["turn"] for s in plan], sorted(s["turn"] for s in plan))


class Scheduled(unittest.TestCase):
    def test_fires_first_due_character(self):
        d = S._scheduled_recreation(cmds(), 18, chara(18, chars={1002: (1, 0)}), preset())
        self.assertIsNotNone(d)
        self.assertEqual(d["select_id"], 1002)
        self.assertFalse(S._pending_outing_is_card)

    def test_does_earliest_pending_character_first(self):
        c = chara(26, chars={cid: (1, 0) for cid in ALL_CHARS})
        self.assertEqual(S._scheduled_recreation(cmds(), 26, c, preset())["select_id"], 1002)

    def test_fires_scheduled_character_when_priors_done(self):
        c = chara(26, chars={1002: (1, 1), 1016: (1, 1), 1017: (1, 0)})
        self.assertEqual(S._scheduled_recreation(cmds(), 26, c, preset())["select_id"], 1017)

    def test_skips_locked_character_and_trains(self):
        c = chara(26, chars={1002: (1, 1), 1016: (1, 1), 1017: (0, 0)})
        self.assertIsNone(S._scheduled_recreation(cmds(), 26, c, preset()))

    def test_catches_up_late_unlocked_character(self):
        chars = all_chars_done()
        chars[1017] = (1, 0)
        self.assertEqual(S._scheduled_recreation(cmds(), 50, chara(50, chars=chars), preset())["select_id"], 1017)

    def test_card_step_fires_when_signature_done(self):
        c = chara(58, chars=all_chars_done(), cards={30067: (1, 1), 30081: (1, 0)})
        d = S._scheduled_recreation(cmds(), 58, c, preset())
        self.assertEqual(d["select_id"], 1001)
        self.assertTrue(S._pending_outing_is_card)

    def test_throne_card_step_one(self):
        c = chara(51, chars=all_chars_done(), cards={30067: (1, 0)})
        self.assertEqual(S._scheduled_recreation(cmds(), 51, c, preset())["select_id"], 1017)

    def test_throne_card_step_two(self):
        c = chara(59, chars=all_chars_done(), cards={30067: (1, 1)})
        self.assertEqual(S._scheduled_recreation(cmds(), 59, c, preset())["select_id"], 1017)

    def test_card_step_skipped_when_maxed(self):
        c = chara(59, chars=all_chars_done(), cards={30067: (1, 2), 30081: (1, 1)})
        self.assertIsNone(S._scheduled_recreation(cmds(), 59, c, preset()))

    def test_card_step_skipped_when_card_locked(self):
        c = chara(51, chars=all_chars_done(), cards={30067: (0, 0)})
        self.assertIsNone(S._scheduled_recreation(cmds(), 51, c, preset()))

    def test_card_step_skipped_when_signature_not_done(self):
        # t58 Sirius card, but 1001 (Special Week) NOT done -> 1001 char fires first
        chars = all_chars_done()
        chars[1001] = (1, 0)
        c = chara(58, chars=chars, cards={30067: (1, 1), 30081: (1, 0)})
        d = S._scheduled_recreation(cmds(), 58, c, preset())
        self.assertEqual(d["select_id"], 1001)
        self.assertFalse(S._pending_outing_is_card)

    def test_no_fire_in_summer_camp(self):
        self.assertIsNone(S._scheduled_recreation(cmds(), 37, chara(37, chars={1002: (1, 0)}), preset()))

    def test_no_fire_without_outing_command(self):
        self.assertIsNone(S._scheduled_recreation(cmds(with_390=False), 18, chara(18, chars={1002: (1, 0)}), preset()))

    def test_card_outing_opt_out(self):
        c = chara(51, chars=all_chars_done(), cards={30067: (1, 0)})
        self.assertIsNone(S._scheduled_recreation(cmds(), 51, c, preset(sirius_throne_card_outing=False)))

    def test_outing_blocked_flag_disables_firing(self):
        s2 = MantStrategy()
        s2._scheduled_outing_blocked = True
        self.assertIsNone(s2._scheduled_recreation(cmds(), 18, chara(18, chars={1002: (1, 0)}), preset()))

    def test_card_block_skips_card_only(self):
        s2 = MantStrategy()
        s2._card_outing_blocked = True
        c = chara(58, chars=all_chars_done(), cards={30067: (1, 1), 30081: (1, 0)})
        self.assertIsNone(s2._scheduled_recreation(cmds(), 58, c, preset()))

    def test_card_block_chars_still_fire(self):
        s2 = MantStrategy()
        s2._card_outing_blocked = True
        chars = all_chars_done()
        chars[1035] = (1, 0)
        c = chara(58, chars=chars, cards={30067: (1, 1), 30081: (1, 0)})
        self.assertEqual(s2._scheduled_recreation(cmds(), 58, c, preset())["select_id"], 1035)


class FreeMode(unittest.TestCase):
    def test_select_first_unlocked_undone(self):
        c = chara(chars={1002: (1, 1), 1016: (1, 0), 1017: (1, 0)})
        self.assertEqual(S._free_outing_select_id(c), 1016)

    def test_select_zero_when_all_done(self):
        self.assertEqual(S._free_outing_select_id(chara(chars={1002: (1, 1), 1016: (1, 1)})), 0)

    def test_free_outing_fires(self):
        d = S._free_group_outing(cmds(), 20, chara(20, chars={1002: (1, 0)}))
        self.assertIsNotNone(d)
        self.assertEqual(d["select_id"], 1002)
        self.assertFalse(S._pending_outing_is_card)

    def test_free_skips_summer_camp(self):
        self.assertIsNone(S._free_group_outing(cmds(), 37, chara(37, chars={1002: (1, 0)})))

    def test_free_skips_non_group_deck(self):
        self.assertIsNone(S._free_group_outing(cmds(), 20, chara(20, deck=(20001,))))

    def test_free_skips_without_390(self):
        self.assertIsNone(S._free_group_outing(cmds(with_390=False), 20, chara(20, chars={1002: (1, 0)})))

    def test_free_skips_when_blocked(self):
        s2 = MantStrategy()
        s2._scheduled_outing_blocked = True
        self.assertIsNone(s2._free_group_outing(cmds(), 20, chara(20, chars={1002: (1, 0)})))


class RecreationGuard(unittest.TestCase):
    def test_recreation_command_skips_390(self):
        self.assertIsNone(S._recreation_command([{"command_type": 3, "command_id": GROUP_OUTING_COMMAND_ID}]))

    def test_recreation_command_returns_301(self):
        c = [{"command_type": 3, "command_id": 390}, {"command_type": 3, "command_id": 301}]
        self.assertEqual(S._recreation_command(c)["command_id"], 301)


class CampSets(unittest.TestCase):
    def test_camp_turn_sets_match_across_modules(self):
        self.assertEqual(set(RACE_VALUE_CAMP_TURNS), set(SUMMER_TRAINING_TURNS))


class CampAllOut(unittest.TestCase):
    """_can_rescue_training: a weak (low-score) camp turn is rescued only for a
    group deck in scheduled mode with summer_all_out on."""
    def _charm_data(self):
        return {"free_data_set": {"user_item_info_array": [{"item_id": GOOD_LUCK_CHARM_ID, "num": 1}]}}

    def _train(self):
        return {"command_type": 1, "command_id": 101, "training_partner_array": []}

    def _call(self, c, p):
        # vital 30 > rest_threshold 20 (skip the vital branch); failure 40 (>=35) -> charm path
        return S._can_rescue_training(self._charm_data(), c, p, self._train(), 0.3, 30, 40, 20)

    def test_rescues_weak_camp_under_all_out(self):
        c = chara(37, deck=(30081, 30067))
        self.assertTrue(self._call(c, preset(summer_all_out=True, sirius_throne_strategy="scheduled")))

    def test_skips_weak_camp_for_non_group(self):
        c = chara(37, deck=(20001, 20002))
        self.assertFalse(self._call(c, preset(summer_all_out=True)))

    def test_skips_weak_camp_when_all_out_disabled(self):
        c = chara(37, deck=(30081, 30067))
        self.assertFalse(self._call(c, preset(summer_all_out=False, sirius_throne_strategy="scheduled")))

    def test_skips_weak_camp_in_free_mode(self):
        c = chara(37, deck=(30081, 30067))
        self.assertFalse(self._call(c, preset(summer_all_out=True, sirius_throne_strategy="free")))


if __name__ == "__main__":
    unittest.main()
