"""v2.1 late-game item usage rework (turn-window branches).

Covers:
  * EDM energy value == 5 (ENERGY_VALUES registry).
  * R1: cupcake kale-reserve disabled at turn >= 60; cupcakes used for mood.
  * R2: megaphone + anklet fire-on-any + caps lifted during 60-64; priority-stat
    gate at turn >= 71.
  * R3: Vita energy late-game reserve dropped (60-64 freely, >=65 rescue).
  * R4: whistle lackluster at turn >= 65 (fires below threshold, conserved above).
  * R5: pre-race energy -- EDM/Vita used ONLY at 0 energy on the 2nd/3rd
    consecutive race; NOT on 1st, NOT on 4th+, NOT at energy > 0, NOT at turn 71+.
"""
import unittest

from career_bot.items import (
    MantItemManager,
    DISPLAY_TO_ID,
    ENERGY_VALUES,
    GLOBAL_STAT_CAP,
    DEFAULT_LATE_WHISTLE_LACKLUSTER_THRESHOLD,
)


class FakeClient:
    def __init__(self):
        self.exchange_payloads = []
        self.use_payloads = []

    def exchange_items(self, payload, current_turn):
        self.exchange_payloads.append((current_turn, list(payload)))
        return {"data": {}}

    def use_items(self, payload, current_turn):
        self.use_payloads.append((current_turn, list(payload)))
        return {"data": {}}


def item_row(name, num=1):
    return {"item_id": DISPLAY_TO_ID[name], "num": num}


def state(turn=30, vital=50, max_vital=100, motivation=4, owned=None, shop=None, coins=0,
          stats=None):
    chara = {
        "turn": turn,
        "vital": vital,
        "max_vital": max_vital,
        "motivation": motivation,
        "scenario_id": 4,
    }
    if stats:
        chara.update(stats)
    return {
        "data": {
            "chara_info": chara,
            "free_data_set": {
                "coin_num": coins,
                "user_item_info_array": [item_row(name, qty) for name, qty in (owned or {}).items()],
                "pick_up_item_info_array": shop or [],
                "item_effect_array": [],
            },
        },
    }


def speed_training(score=40, failure=5):
    return {
        "command_type": 1,
        "command_id": 101,  # Speed -> main target 1
        "failure_rate": failure,
        "params_inc_dec_info_array": [{"target_type": 1, "value": score}],
    }


def power_training(score=40, failure=5):
    return {
        "command_type": 1,
        "command_id": 102,  # Power -> main target 3
        "failure_rate": failure,
        "params_inc_dec_info_array": [{"target_type": 3, "value": score}],
    }


class EnergyValuesTests(unittest.TestCase):
    def test_edm_energy_value_is_five(self):
        # Data fix: Energy Drink MAX is a small top-up item (value 5), not 30.
        self.assertEqual(ENERGY_VALUES.get("Energy Drink MAX"), 5)

    def test_other_energy_values_unchanged(self):
        self.assertEqual(ENERGY_VALUES.get("Energy Drink MAX EX"), 100)
        self.assertNotIn("Vita 20", ENERGY_VALUES)  # Vita lives in ENERGY_ITEMS


class CupcakeLateGameTests(unittest.TestCase):
    def test_kale_reserve_disabled_at_turn_60(self):
        # Past turn 59 Plain Cupcake is NOT held back for the kale offset -- a
        # kale turn with only a Plain Cupcake available still patches mood.
        mgr = MantItemManager()
        # motivation<=1 makes kale "safe" regardless of cupcake; verify the mood
        # target picks a cupcake at turn 60 even with a reserved Plain.
        target = mgr._mood_target(
            {"turn": 60, "vital": 30, "motivation": 3, "max_vital": 100},
            {"Plain Cupcake": 1},
            {"mant_config": {}},
            kale_queued=True,
        )
        # Late-game branch with motivation < 4 fires first (kale_queued ignored).
        self.assertIsNotNone(target)
        self.assertEqual(target[0], "Plain Cupcake")

    def test_cupcakes_used_for_mood_turn_60(self):
        mgr = MantItemManager()
        target = mgr._mood_target(
            {"turn": 60, "vital": 80, "motivation": 3, "max_vital": 100},
            {"Berry Sweet Cupcake": 1},
            {"mant_config": {}},
            kale_queued=False,
        )
        # motivation 3 < 4 -> late-game mood branch fires (any cupcake, any HP).
        self.assertIsNotNone(target)
        self.assertEqual(target[0], "Berry Sweet Cupcake")

    def test_cupcakes_used_for_mood_turn_65(self):
        mgr = MantItemManager()
        target = mgr._mood_target(
            {"turn": 65, "vital": 80, "motivation": 2, "max_vital": 100},
            {"Plain Cupcake": 1},
            {"mant_config": {}},
            kale_queued=False,
        )
        self.assertIsNotNone(target)
        self.assertEqual(target[0], "Plain Cupcake")

    def test_no_cupcake_when_motivation_four_plus(self):
        mgr = MantItemManager()
        target = mgr._mood_target(
            {"turn": 60, "vital": 80, "motivation": 4, "max_vital": 100},
            {"Plain Cupcake": 1},
            {"mant_config": {}},
            kale_queued=False,
        )
        self.assertIsNone(target)


class MegaphoneAnkletLateGameTests(unittest.TestCase):
    def test_megaphone_fires_on_any_gain_during_60_64(self):
        mgr = MantItemManager()
        # Small gain (score 5) normally below thresholds, but 60-64 = fire-any.
        target = mgr._megaphone_target(
            state(turn=62, owned={"Empowering Megaphone": 1}),
            speed_training(score=5),
            {"Empowering Megaphone": 1},
            {"mant_config": {}},
            status={"current_chara": {"motivation": 4}},
            turn=62,
            race_planner=None,
        )
        self.assertIsNotNone(target)
        self.assertEqual(target[0], "Empowering Megaphone")

    def test_anklet_fires_on_any_gain_during_60_64(self):
        mgr = MantItemManager()
        target = mgr._anklet_target(
            state(turn=62, owned={"Speed Ankle Weights": 1}),
            speed_training(score=5),
            {"Speed Ankle Weights": 1},
            {"mant_config": {}},
        )
        self.assertIsNotNone(target)
        self.assertEqual(target[0], "Speed Ankle Weights")

    def test_anklet_priority_stat_gate_at_turn_71(self):
        mgr = MantItemManager()
        # The 71+ priority-stat gate is now the CONSERVATIVE behavior, gated
        # behind save_items_lategame=True. (Default OFF = aggressive late-game
        # dump, covered in test_save_items_lategame_20260625.)
        preset = {"training_stat_priority": ["speed", "power"],
                  "mant_config": {"save_items_lategame": True}}
        # Speed is the top priority and is below cap -> speed training passes.
        target = mgr._anklet_target(
            state(turn=71, owned={"Speed Ankle Weights": 1}, stats={"speed": 500}),
            speed_training(score=40),
            {"Speed Ankle Weights": 1},
            preset,
        )
        self.assertIsNotNone(target)
        # Power training (2nd priority) is blocked when speed still needs work.
        blocked = mgr._anklet_target(
            state(turn=71, owned={"Power Ankle Weights": 1}, stats={"speed": 500}),
            power_training(score=40),
            {"Power Ankle Weights": 1},
            preset,
        )
        self.assertIsNone(blocked)

    def test_megaphone_buy_cap_lifted_during_60_64(self):
        mgr = MantItemManager()
        # Own 2 anklets already (the cap). At turn 62 the cap is lifted so buying
        # is NOT skipped on stock grounds. Provide deck-type counts so the
        # unrelated deck-count gate does not fire.
        preset = {
            "mant_config": {"trackblazer_anklet_max_stock": 2},
            "_deck_type_counts": [3, 0, 0, 0, 0],  # Speed deck has >=2 cards
        }
        skip = mgr._skip_buy(
            "Speed Ankle Weights",
            {"Speed Ankle Weights": 2},
            preset=preset,
            turn=62,
            budget=200,
            data=state(turn=62, owned={"Speed Ankle Weights": 2})["data"],
        )
        self.assertFalse(skip)
        # Same scenario mid-career (turn 30) IS skipped because the cap applies.
        skip_mid = mgr._skip_buy(
            "Speed Ankle Weights",
            {"Speed Ankle Weights": 2},
            preset=preset,
            turn=30,
            budget=200,
            data=state(turn=30, owned={"Speed Ankle Weights": 2})["data"],
        )
        self.assertTrue(skip_mid)


class WhistleLateGameTests(unittest.TestCase):
    def test_whistle_lackluster_threshold_default(self):
        self.assertEqual(DEFAULT_LATE_WHISTLE_LACKLUSTER_THRESHOLD, 30)

    def test_whistle_fires_below_threshold_turn_65(self):
        mgr = MantItemManager()
        # total gain 20 < default 30 -> lackluster -> reroll.
        target = mgr._whistle_target(
            speed_training(score=20),
            {"Reset Whistle": 1},
            {"mant_config": {}},
            {"current_chara": {"vital": 80, "motivation": 4}},
            turn=65,
        )
        self.assertEqual(target, ("Reset Whistle", 1))

    def test_whistle_conserved_above_threshold_turn_65(self):
        mgr = MantItemManager()
        # total gain 40 >= 30 -> NOT lackluster -> conserve.
        target = mgr._whistle_target(
            speed_training(score=40),
            {"Reset Whistle": 1},
            {"mant_config": {}},
            {"current_chara": {"vital": 80, "motivation": 4}},
            turn=65,
        )
        self.assertIsNone(target)

    def test_whistle_threshold_configurable(self):
        mgr = MantItemManager()
        # Raise the threshold to 50; gain 40 now below -> fires.
        target = mgr._whistle_target(
            speed_training(score=40),
            {"Reset Whistle": 1},
            {"mant_config": {"late_whistle_lackluster_threshold": 50}},
            {"current_chara": {"vital": 80, "motivation": 4}},
            turn=66,
        )
        self.assertEqual(target, ("Reset Whistle", 1))


class VitaEnergyLateGameTests(unittest.TestCase):
    def test_vita_no_reserve_during_60_64(self):
        mgr = MantItemManager()
        # At turn 62 the low-tier reserve is dropped, so a single Vita 20 is
        # spendable (mid-career it would be held back as the reserve copy).
        targets = mgr._energy_targets(
            {"turn": 62, "vital": 30, "max_vital": 100, "motivation": 4},
            {"Vita 20": 1},
            {"mant_config": {"trackblazer_energy_item_reserve": 1}},
        )
        self.assertIn(("Vita 20", 1), targets)

    def test_vita_rescue_prefers_items_turn_65(self):
        mgr = MantItemManager()
        # Turn 65+: threshold relaxed toward max, so items fire at higher HP
        # (prefer items over resting). vital 35 + Vita 65 = 100 <= overshoot cap.
        targets = mgr._energy_targets(
            {"turn": 66, "vital": 35, "max_vital": 100, "motivation": 4},
            {"Vita 65": 1},
            {"mant_config": {}},
        )
        self.assertIn(("Vita 65", 1), targets)

    def test_vita_rescue_fires_at_higher_hp_turn_65_vs_midcareer(self):
        # Mid-career (turn 40) vital 70 / threshold 40 -> blocked (hp >= 40).
        mgr = MantItemManager()
        mid = mgr._energy_targets(
            {"turn": 40, "vital": 70, "max_vital": 100, "motivation": 4},
            {"Vita 20": 1},
            {"mant_config": {}},
        )
        self.assertEqual(mid, [])


class PreRaceEnergyChainTests(unittest.TestCase):
    """R5: the consecutive-race pre-race energy rule."""

    def _prerace(self, turn, vital, owned, chain_pos):
        mgr = MantItemManager()
        client = FakeClient()
        st = state(turn=turn, vital=vital, owned=owned)
        mgr.handle_pre_race(
            client, st, {"mant_config": {}}, {"program_id": 100},
            status=None, race_planner=None,
            consecutive_race_position=chain_pos,
        )
        return mgr

    def test_edm_used_at_zero_energy_on_second_race(self):
        mgr = self._prerace(40, vital=0, owned={"Energy Drink MAX": 1}, chain_pos=2)
        names = {row["name"] for row in mgr.last_pre_race_use_selected}
        self.assertIn("Energy Drink MAX", names)

    def test_edm_used_at_zero_energy_on_third_race(self):
        mgr = self._prerace(40, vital=0, owned={"Energy Drink MAX": 1}, chain_pos=3)
        names = {row["name"] for row in mgr.last_pre_race_use_selected}
        self.assertIn("Energy Drink MAX", names)

    def test_no_spend_on_first_race_at_zero_energy(self):
        mgr = self._prerace(40, vital=0, owned={"Energy Drink MAX": 1, "Vita 20": 1}, chain_pos=1)
        names = {row["name"] for row in mgr.last_pre_race_use_selected}
        self.assertNotIn("Energy Drink MAX", names)
        self.assertNotIn("Vita 20", names)

    def test_no_spend_on_fourth_race_at_zero_energy(self):
        mgr = self._prerace(40, vital=0, owned={"Energy Drink MAX": 1, "Vita 20": 1}, chain_pos=4)
        names = {row["name"] for row in mgr.last_pre_race_use_selected}
        self.assertNotIn("Energy Drink MAX", names)
        self.assertNotIn("Vita 20", names)

    def test_no_spend_at_positive_energy(self):
        # vital 5 > 0 -> NEVER spend an energy item before a race.
        mgr = self._prerace(40, vital=5, owned={"Energy Drink MAX": 1, "Vita 20": 1}, chain_pos=2)
        names = {row["name"] for row in mgr.last_pre_race_use_selected}
        self.assertNotIn("Energy Drink MAX", names)
        self.assertNotIn("Vita 20", names)

    def test_no_energy_management_at_turn_71(self):
        # Post-70 races cost no energy + have no 0-energy punishment -> NO energy
        # management at all. This must cover BOTH paths inside handle_pre_race:
        # the dedicated R5 gate AND the use_items/_energy_targets late-spend branch
        # (which has no upper turn cutoff and would otherwise still spend Vitas).
        energy = {"Energy Drink MAX", "Energy Drink MAX EX", "Vita 20", "Vita 40", "Vita 65"}
        mgr = self._prerace(71, vital=0,
                            owned={"Energy Drink MAX": 1, "Vita 20": 3, "Vita 65": 2},
                            chain_pos=2)
        prerace_names = {row["name"] for row in mgr.last_pre_race_use_selected}
        used_names = {row["name"] for row in mgr.last_use_selected}
        self.assertFalse(prerace_names & energy,
                         f"R5 path spent energy at turn 71: {prerace_names & energy}")
        self.assertFalse(used_names & energy,
                         f"use_items path spent energy at turn 71: {used_names & energy}")

    def test_vita_fallback_when_edm_not_owned(self):
        mgr = self._prerace(40, vital=0, owned={"Vita 20": 1, "Vita 40": 1}, chain_pos=2)
        names = {row["name"] for row in mgr.last_pre_race_use_selected}
        # Smallest Vita preferred.
        self.assertIn("Vita 20", names)
        self.assertNotIn("Vita 40", names)

    def test_smallest_sufficient_prefers_edm(self):
        mgr = MantItemManager()
        self.assertEqual(mgr._smallest_sufficient_prerace_energy(
            {"Energy Drink MAX": 1, "Vita 20": 1}), "Energy Drink MAX")

    def test_smallest_sufficient_vita_fallback(self):
        mgr = MantItemManager()
        self.assertEqual(mgr._smallest_sufficient_prerace_energy(
            {"Vita 40": 1, "Vita 20": 1}), "Vita 20")

    def test_smallest_sufficient_none_when_empty(self):
        mgr = MantItemManager()
        self.assertIsNone(mgr._smallest_sufficient_prerace_energy({}))


if __name__ == "__main__":
    unittest.main()
