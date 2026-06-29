"""save_items_lategame toggle + cupcake/kale summer lock + two one-liners (2026-06-25).

User doctrine (see memory icarus-item-strategy-rules):
  * After turn 64 there is no more summer and finale races pay ZERO coins, so
    every remaining item MUST be dumped on any slightly-useful training to avoid
    waste.  New scenario-override toggle `mant_config.save_items_lategame`
    (default False = aggressive dump; True = old conservative behavior).
  * Cupcake + Royal Kale Juice combo is locked to summer turns; AFTER turn 64
    leftover kale is used as recovery instead of resting EVEN WITH NO CUPCAKE.
  * One-liner #1: `_finale_bonus` gated behind turn >= 73 (no career-wide cap
    shrink).
  * One-liner #2: irregular-training fallback threshold 50 -> 30.

These tests are written test-first; they fail against the pre-change code.
"""
import unittest

from career_bot.items import MantItemManager, DISPLAY_TO_ID
from career_bot.scenarios.mant import MantStrategy
from career_bot.scenarios.mant_trackblazer import MantTrackblazerCore


# --------------------------------------------------------------------------- #
# Item-manager test fixtures (mirrors test_late_game_items_20260624 patterns).
# --------------------------------------------------------------------------- #
def item_row(name, num=1):
    return {"item_id": DISPLAY_TO_ID[name], "num": num}


def istate(turn=30, vital=50, max_vital=100, motivation=4, owned=None, stats=None):
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
                "coin_num": 0,
                "user_item_info_array": [item_row(n, q) for n, q in (owned or {}).items()],
                "pick_up_item_info_array": [],
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


class FakeClient:
    def __init__(self):
        self.use_payloads = []

    def use_items(self, payload, current_turn):
        self.use_payloads.append((current_turn, list(payload)))
        return {"data": {}}

    def exchange_items(self, payload, current_turn):
        return {"data": {}}


PRIORITY_PRESET = {"training_stat_priority": ["speed", "power"], "mant_config": {}}
PRIORITY_PRESET_SAVE = {"training_stat_priority": ["speed", "power"],
                        "mant_config": {"save_items_lategame": True}}


# --------------------------------------------------------------------------- #
# 1. Megaphone dump in the finale window (turn >= 71).
# --------------------------------------------------------------------------- #
class MegaphoneFinaleDumpTests(unittest.TestCase):
    def test_megaphone_dumps_on_offpriority_training_at_73_by_default(self):
        # Power training (2nd priority) while Speed is still uncapped: the 71+
        # priority-stat gate would normally hoard the megaphone. Default dump
        # mode spends it anyway.
        mgr = MantItemManager()
        target = mgr._megaphone_target(
            istate(turn=73, owned={"Empowering Megaphone": 1}, stats={"speed": 500}),
            power_training(score=40),
            {"Empowering Megaphone": 1},
            PRIORITY_PRESET,
            status={"current_chara": {"motivation": 4}},
            turn=73,
            race_planner=None,
        )
        self.assertEqual(target, ("Empowering Megaphone", 1))

    def test_megaphone_conserved_on_offpriority_at_73_when_save_on(self):
        mgr = MantItemManager()
        target = mgr._megaphone_target(
            istate(turn=73, owned={"Empowering Megaphone": 1}, stats={"speed": 500}),
            power_training(score=40),
            {"Empowering Megaphone": 1},
            PRIORITY_PRESET_SAVE,
            status={"current_chara": {"motivation": 4}},
            turn=73,
            race_planner=None,
        )
        self.assertIsNone(target)


# --------------------------------------------------------------------------- #
# 2. Anklet dump in the finale window (turn >= 71).
# --------------------------------------------------------------------------- #
class AnkletFinaleDumpTests(unittest.TestCase):
    def test_anklet_dumps_on_offpriority_at_73_by_default(self):
        mgr = MantItemManager()
        target = mgr._anklet_target(
            istate(turn=73, owned={"Power Ankle Weights": 1}, stats={"speed": 500}),
            power_training(score=40),
            {"Power Ankle Weights": 1},
            PRIORITY_PRESET,
        )
        self.assertEqual(target, ("Power Ankle Weights", 1))

    def test_anklet_conserved_on_offpriority_at_73_when_save_on(self):
        mgr = MantItemManager()
        target = mgr._anklet_target(
            istate(turn=73, owned={"Power Ankle Weights": 1}, stats={"speed": 500}),
            power_training(score=40),
            {"Power Ankle Weights": 1},
            PRIORITY_PRESET_SAVE,
        )
        self.assertIsNone(target)


# --------------------------------------------------------------------------- #
# 3. Charm dump after turn 64 (low-failure / low-gain trainings).
# --------------------------------------------------------------------------- #
class CharmLateDumpTests(unittest.TestCase):
    def test_charm_fires_on_low_failure_low_gain_at_73_by_default(self):
        mgr = MantItemManager()
        target = mgr._charm_target(
            speed_training(score=10, failure=5),  # below the normal 20/20 floors
            {"Good-Luck Charm": 1},
            {"mant_config": {}},
            {"current_chara": {"motivation": 4}},
            turn=73,
        )
        self.assertEqual(target, ("Good-Luck Charm", 1))

    def test_charm_conserved_on_low_failure_at_73_when_save_on(self):
        mgr = MantItemManager()
        target = mgr._charm_target(
            speed_training(score=10, failure=5),
            {"Good-Luck Charm": 1},
            {"mant_config": {"save_items_lategame": True}},
            {"current_chara": {"motivation": 4}},
            turn=73,
        )
        self.assertIsNone(target)

    def test_charm_skips_truly_pointless_training_even_in_dump(self):
        # 0% failure AND 0 gain -> a charm does nothing useful; floor of 1 holds.
        mgr = MantItemManager()
        target = mgr._charm_target(
            speed_training(score=0, failure=0),
            {"Good-Luck Charm": 1},
            {"mant_config": {}},
            {"current_chara": {"motivation": 4}},
            turn=73,
        )
        self.assertIsNone(target)


# --------------------------------------------------------------------------- #
# 4. Cupcake dump after turn 64 (fire up to GREAT mood).
# --------------------------------------------------------------------------- #
class CupcakeLateDumpTests(unittest.TestCase):
    def test_cupcake_fires_at_motivation_four_at_73_by_default(self):
        mgr = MantItemManager()
        target = mgr._mood_target(
            {"turn": 73, "vital": 80, "motivation": 4, "max_vital": 100},
            {"Plain Cupcake": 1},
            {"mant_config": {}},
            kale_queued=False,
        )
        self.assertIsNotNone(target)
        self.assertEqual(target[0], "Plain Cupcake")

    def test_cupcake_conserved_at_motivation_four_at_73_when_save_on(self):
        mgr = MantItemManager()
        target = mgr._mood_target(
            {"turn": 73, "vital": 80, "motivation": 4, "max_vital": 100},
            {"Plain Cupcake": 1},
            {"mant_config": {"save_items_lategame": True}},
            kale_queued=False,
        )
        self.assertIsNone(target)

    def test_cupcake_skips_at_max_mood_even_in_dump(self):
        mgr = MantItemManager()
        target = mgr._mood_target(
            {"turn": 73, "vital": 80, "motivation": 5, "max_vital": 100},
            {"Plain Cupcake": 1},
            {"mant_config": {}},
            kale_queued=False,
        )
        self.assertIsNone(target)


# --------------------------------------------------------------------------- #
# 5. Energy (Vita) dump after turn 64 (gap<20 no longer blocks).
# --------------------------------------------------------------------------- #
class EnergyLateDumpTests(unittest.TestCase):
    def test_vita_fires_when_gap_under_20_at_73_by_default(self):
        mgr = MantItemManager()
        targets = mgr._energy_targets(
            {"turn": 73, "vital": 85, "max_vital": 100, "motivation": 4},
            {"Vita 20": 1},
            {"mant_config": {}},
        )
        self.assertIn(("Vita 20", 1), targets)

    def test_vita_held_when_gap_under_20_at_73_when_save_on(self):
        mgr = MantItemManager()
        targets = mgr._energy_targets(
            {"turn": 73, "vital": 85, "max_vital": 100, "motivation": 4},
            {"Vita 20": 1},
            {"mant_config": {"save_items_lategame": True}},
        )
        self.assertEqual(targets, [])


# --------------------------------------------------------------------------- #
# 6. Cupcake + Kale summer lock (+ post-64 dump).
# --------------------------------------------------------------------------- #
class KaleSummerLockTests(unittest.TestCase):
    def test_kale_dumped_post64_without_cupcake_by_default(self):
        # Turn 70, no cupcake, GOOD mood (not safe_mood), not critical HP:
        # old logic refuses kale; dump mode uses it as recovery instead of rest.
        mgr = MantItemManager()
        targets = mgr._energy_targets(
            {"turn": 70, "vital": 50, "max_vital": 100, "motivation": 4},
            {"Royal Kale Juice": 1},
            {"mant_config": {}},
        )
        self.assertIn(("Royal Kale Juice", 1), targets)

    def test_kale_locked_mid_career_outside_summer(self):
        # Turn 50 is NOT a summer turn and NOT late game; even with safe mood
        # (motivation 1) and low energy (recovery warranted) the combo is locked,
        # so no kale is queued.
        mgr = MantItemManager()
        targets = mgr._energy_targets(
            {"turn": 50, "vital": 30, "max_vital": 100, "motivation": 1},
            {"Royal Kale Juice": 1},
            {"mant_config": {}},
        )
        self.assertNotIn(("Royal Kale Juice", 1), targets)

    def test_kale_still_fires_in_summer(self):
        # Regression guard: summer (turn 62) with low energy + safe mood keeps
        # using the combo.
        mgr = MantItemManager()
        targets = mgr._energy_targets(
            {"turn": 62, "vital": 30, "max_vital": 100, "motivation": 1},
            {"Royal Kale Juice": 1},
            {"mant_config": {}},
        )
        self.assertIn(("Royal Kale Juice", 1), targets)


# --------------------------------------------------------------------------- #
# 6b. Charm + energy on the same turn in dump mode (don't strip energy).
# --------------------------------------------------------------------------- #
class CharmEnergyDumpTests(unittest.TestCase):
    def test_charm_and_vita_both_used_post64_by_default(self):
        # Dump mode: a charm and a Vita on the same turn is fine (goal: empty the
        # inventory), so the save_energy_under_charm strip must not suppress the
        # energy dump.
        mgr = MantItemManager()
        mgr.use_items(
            FakeClient(),
            istate(turn=70, vital=50, motivation=4,
                   owned={"Good-Luck Charm": 1, "Vita 20": 1}),
            {"mant_config": {}},
            best_command=speed_training(score=40, failure=10),
            status={"current_chara": {"motivation": 4}},
        )
        selected = {row["name"] for row in mgr.last_use_selected}
        self.assertIn("Good-Luck Charm", selected)
        self.assertIn("Vita 20", selected)

    def test_charm_strips_energy_when_save_on(self):
        # save_items_lategame ON -> old behavior: energy reserved under a charm.
        # (failure 30 >= the conservative 20 floor so the charm still fires.)
        mgr = MantItemManager()
        mgr.use_items(
            FakeClient(),
            istate(turn=70, vital=50, motivation=4,
                   owned={"Good-Luck Charm": 1, "Vita 20": 1}),
            {"mant_config": {"save_items_lategame": True}},
            best_command=speed_training(score=40, failure=30),
            status={"current_chara": {"motivation": 4}},
        )
        selected = {row["name"] for row in mgr.last_use_selected}
        self.assertIn("Good-Luck Charm", selected)
        self.assertNotIn("Vita 20", selected)


# --------------------------------------------------------------------------- #
# 7. Buy gates: lift conservation caps after turn 64 in dump mode.
# --------------------------------------------------------------------------- #
class LateBuyDumpTests(unittest.TestCase):
    def _preset(self, save=False):
        mc = {"trackblazer_anklet_max_stock": 2}
        if save:
            mc["save_items_lategame"] = True
        return {"mant_config": mc, "_deck_type_counts": [3, 0, 0, 0, 0]}

    def test_anklet_buy_cap_lifted_at_66_by_default(self):
        mgr = MantItemManager()
        skip = mgr._skip_buy(
            "Speed Ankle Weights",
            {"Speed Ankle Weights": 2},
            preset=self._preset(save=False),
            turn=66,
            budget=200,
            data=istate(turn=66, owned={"Speed Ankle Weights": 2})["data"],
        )
        self.assertFalse(skip)

    def test_anklet_buy_cap_kept_at_66_when_save_on(self):
        mgr = MantItemManager()
        skip = mgr._skip_buy(
            "Speed Ankle Weights",
            {"Speed Ankle Weights": 2},
            preset=self._preset(save=True),
            turn=66,
            budget=200,
            data=istate(turn=66, owned={"Speed Ankle Weights": 2})["data"],
        )
        self.assertTrue(skip)


# --------------------------------------------------------------------------- #
# 8. Coin reserve: don't hoard 150 for finals in dump mode (protect the
#    Master Cleat Hammer must-buy only).
# --------------------------------------------------------------------------- #
class CoinReserveDumpTests(unittest.TestCase):
    def test_coin_reserve_reduced_in_dump_by_default(self):
        mgr = MantItemManager()
        self.assertLessEqual(mgr._coin_reserve(70, 500, {}), 60)

    def test_coin_reserve_full_when_save_on(self):
        mgr = MantItemManager()
        self.assertEqual(mgr._coin_reserve(70, 500, {"save_items_lategame": True}), 150)


# --------------------------------------------------------------------------- #
# 9. One-liner #1: finale-bonus gated behind turn >= 73.
# --------------------------------------------------------------------------- #
class FinaleBonusGateTests(unittest.TestCase):
    def setUp(self):
        self.core = MantTrackblazerCore(None)

    def test_no_finale_bonus_before_73(self):
        self.assertEqual(self.core._finale_bonus(50), 0)
        self.assertEqual(self.core._finale_bonus(72), 0)

    def test_finale_bonus_active_from_73(self):
        self.assertEqual(self.core._finale_bonus(73), 30)
        self.assertEqual(self.core._finale_bonus(74), 15)
        self.assertEqual(self.core._finale_bonus(75), 0)


# --------------------------------------------------------------------------- #
# 10. One-liner #2: irregular-training fallback threshold 50 -> 30.
# --------------------------------------------------------------------------- #
class FakeRacePlanner:
    def __init__(self):
        from pathlib import Path
        import tempfile
        self.base_dir = Path(tempfile.mkdtemp())
        self.program = {100: {"grade": "G1", "fans": 30000, "name": "Target G1"}}
        self.official_races = {}

    def label(self, program_id):
        return self.program.get(int(program_id), {}).get("name", str(program_id))

    def forced_program(self, state):
        return None

    def choose(self, state, preset):
        return 100


def dtraining(command_id=101, gain=90, failure=0):
    main_target = {101: 1, 105: 2, 102: 3, 103: 4, 106: 5}.get(command_id, 1)
    return {
        "command_type": 1,
        "command_id": command_id,
        "command_group_id": 0,
        "select_id": 0,
        "is_enable": 1,
        "failure_rate": failure,
        "training_partner_array": [],
        "params_inc_dec_info_array": [{"target_type": main_target, "value": gain}],
    }


def dstate(turn=50, vital=70, motivation=4, commands=None):
    return {
        "data": {
            "chara_info": {
                "turn": turn, "vital": vital, "max_vital": 100, "motivation": motivation,
                "speed": 300, "stamina": 300, "power": 300, "guts": 300, "wiz": 300,
                "skill_point": 0,
            },
            "home_info": {"command_info_array": commands or []},
            "free_data_set": {
                "coin_num": 0, "user_item_info_array": [],
                "pick_up_item_info_array": [], "item_effect_array": [],
            },
            "action_history": [],
        }
    }


class IrregularTrainingThresholdTests(unittest.TestCase):
    def test_irregular_training_fires_at_gain_35_in_year_two(self):
        # Year 2 (turn 50), best training main gain 35: above the intended 30 but
        # below the old hardcoded 50, so it must now hijack the planned race.
        strategy = MantStrategy(FakeRacePlanner())
        st = dstate(turn=50, commands=[dtraining(gain=35, failure=0)])
        decision = strategy.next_decision(st, {"mant_config": {}, "compensate_failure": False})
        self.assertEqual(decision.action, "command")
        self.assertIn("irregular training", decision.reason)


if __name__ == "__main__":
    unittest.main()
