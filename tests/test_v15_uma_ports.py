"""v1.5: ports from UmaAuto's MANT scenario.

Covers the energy-rescue helpers (``_rescue_energy_value`` and
``_can_rescue_training``) that the Trackblazer engine delegates to via
``self.ref._can_rescue_training``.  The junior bond-rush and capped hint-bonus
tests that exercised the now-removed dormant Classic scorer (``_best_command`` /
``_score_command``) were deleted along with that scorer.
"""
import unittest

from career_bot.scenarios.mant import MantStrategy


def training(command_id=101, gain=40, failure=0, partners=None, tips=None):
    main_target = {101: 1, 105: 2, 102: 3, 103: 4, 106: 5}.get(command_id, 1)
    return {
        "command_type": 1,
        "command_id": command_id,
        "command_group_id": 0,
        "select_id": 0,
        "is_enable": 1,
        "failure_rate": failure,
        "training_partner_array": partners or [],
        "tips_event_partner_array": tips or [],
        "params_inc_dec_info_array": [{"target_type": main_target, "value": gain}],
    }


def rest_cmd():
    return {"command_type": 7, "command_id": 701, "is_enable": 1}


def chara(turn=30, vital=80, bonds=None):
    return {
        "turn": turn,
        "vital": vital,
        "max_vital": 100,
        "motivation": 4,
        "scenario_id": 4,
        "speed": 300, "stamina": 300, "power": 300, "guts": 300, "wiz": 300,
        "skill_point": 0,
        "evaluation_info_array": [
            {"target_id": int(pid), "evaluation": int(value)}
            for pid, value in (bonds or {}).items()
        ],
    }


def data_with(commands, owned=None):
    return {
        "home_info": {"command_info_array": commands},
        "free_data_set": {
            "user_item_info_array": [
                {"item_id": int(iid), "num": int(qty)}
                for iid, qty in (owned or {}).items()
            ]
        },
    }


PRESET = {"compensate_failure": False, "mant_config": {}}


class RescueEnergyValueTests(unittest.TestCase):
    def test_picks_smallest_sufficient_item(self):
        s = MantStrategy()
        # vital 40, rest 48, margin 12 -> need to clear 60. Vita 20 -> 60 (not >),
        # Vita 40 -> 80 (sufficient). Owns both; should choose Vita 40 (40), not 65.
        data = data_with([], owned={2001: 3, 2002: 2, 2003: 1})
        self.assertEqual(s._rescue_energy_value(data, vital=40, rest_threshold=48, margin=12), 40)

    def test_none_when_nothing_sufficient(self):
        s = MantStrategy()
        data = data_with([], owned={2001: 5})  # Vita 20 only: 40+20=60, not > 60
        self.assertIsNone(s._rescue_energy_value(data, vital=40, rest_threshold=48, margin=12))

    def test_none_when_no_energy_items(self):
        s = MantStrategy()
        self.assertIsNone(MantStrategy()._rescue_energy_value(data_with([]), 40, 48, 12))


class CanRescueTrainingTests(unittest.TestCase):
    def setUp(self):
        self.s = MantStrategy()
        self.rainbow = training(101, gain=40, failure=0, partners=[1])
        self.ch = chara(vital=40, bonds={1: 80})  # rainbow partner

    def test_rescue_fires_for_rainbow_at_low_vital_with_energy(self):
        data = data_with([], owned={2003: 2})  # Vita 65 above the 1-item reserve
        self.assertTrue(self.s._can_rescue_training(
            data, self.ch, PRESET, self.rainbow, 0.6, vital=40, failure=0, rest_threshold=48))

    def test_no_rescue_without_item_or_charm(self):
        data = data_with([])  # nothing owned
        self.assertFalse(self.s._can_rescue_training(
            data, self.ch, PRESET, self.rainbow, 0.6, vital=40, failure=0, rest_threshold=48))

    def test_no_rescue_for_weak_non_rainbow(self):
        weak = training(101, gain=10, failure=0, partners=[])  # no rainbow, low score
        data = data_with([], owned={2003: 2})
        self.assertFalse(self.s._can_rescue_training(
            data, chara(vital=40), PRESET, weak, 0.10, vital=40, failure=0, rest_threshold=48))

    def test_high_failure_needs_charm(self):
        data_charm = data_with([], owned={10001: 1})
        data_energy = data_with([], owned={2003: 2})
        # failure above hard cap (50) -> only a charm rescues
        self.assertTrue(self.s._can_rescue_training(
            data_charm, self.ch, PRESET, self.rainbow, 0.6, vital=60, failure=55, rest_threshold=48))
        self.assertFalse(self.s._can_rescue_training(
            data_energy, self.ch, PRESET, self.rainbow, 0.6, vital=60, failure=55, rest_threshold=48))

    def test_disabled_via_preset(self):
        data = data_with([], owned={2003: 2})
        off = {"compensate_failure": False, "mant_config": {"rescue_good_training": False}}
        self.assertFalse(self.s._can_rescue_training(
            data, self.ch, off, self.rainbow, 0.6, vital=40, failure=0, rest_threshold=48))


if __name__ == "__main__":
    unittest.main()
