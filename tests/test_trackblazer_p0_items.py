import unittest
from pathlib import Path
import tempfile

from career_bot.items import MantItemManager, DISPLAY_TO_ID


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


class FakeRacePlanner:
    def __init__(self):
        self.base_dir = Path(tempfile.mkdtemp())
        self.program = {}
        self.official_races = {}


def item_row(name, num=1):
    return {"item_id": DISPLAY_TO_ID[name], "num": num}


def shop_row(shop_item_id, name, cost):
    return {
        "shop_item_id": shop_item_id,
        "item_id": DISPLAY_TO_ID[name],
        "coin_num": cost,
        "original_coin_num": cost,
        "item_buy_num": 0,
        "limit_buy_count": 1,
        "limit_turn": 0,
    }


def state(turn=30, vital=50, max_vital=100, motivation=4, owned=None, shop=None, coins=0):
    return {
        "data": {
            "chara_info": {
                "turn": turn,
                "vital": vital,
                "max_vital": max_vital,
                "motivation": motivation,
                "scenario_id": 4,
            },
            "free_data_set": {
                "coin_num": coins,
                "user_item_info_array": [item_row(name, qty) for name, qty in (owned or {}).items()],
                "pick_up_item_info_array": shop or [],
                "item_effect_array": [],
            },
        }
    }


class TrackblazerP0ItemTests(unittest.TestCase):
    def test_shop_buys_critical_race_kit_before_stat_scrolls(self):
        mgr = MantItemManager()
        client = FakeClient()
        shop = [
            shop_row(1, "Speed Scroll", 30),
            shop_row(2, "Good-Luck Charm", 40),
            shop_row(3, "Master Cleat Hammer", 40),
            shop_row(4, "Glow Sticks", 15),
        ]
        st, bought = mgr.buy_shop_items(client, state(turn=30, shop=shop, coins=95), {"mant_config": {}})
        names = {row["name"] for row in mgr.last_buy_selected}
        self.assertEqual(bought, 3)
        self.assertIn("Good-Luck Charm", names)
        self.assertIn("Master Cleat Hammer", names)
        self.assertIn("Glow Sticks", names)
        self.assertNotIn("Speed Scroll", names)

    def test_charm_blocks_energy_items_on_risky_training(self):
        mgr = MantItemManager()
        client = FakeClient()
        best_command = {
            "command_type": 1,
            "command_id": 101,
            "failure_rate": 25,
            "params_inc_dec_info_array": [{"target_type": 1, "value": 25}],
        }
        mgr.use_items(
            client,
            state(turn=30, vital=20, owned={"Good-Luck Charm": 1, "Vita 65": 1}),
            {"mant_config": {}},
            best_command=best_command,
            status={"current_chara": {"motivation": 4}},
        )
        selected = {row["name"] for row in mgr.last_use_selected}
        self.assertIn("Good-Luck Charm", selected)
        self.assertNotIn("Vita 65", selected)

    def test_energy_greedy_reserves_lowest_tier_vita(self):
        mgr = MantItemManager()
        targets = mgr._energy_targets(
            {"turn": 30, "vital": 35, "max_vital": 100, "motivation": 4},
            {"Vita 20": 1, "Vita 65": 1},
            {"mant_config": {}},
        )
        self.assertEqual(targets, [("Vita 65", 1)])

    def test_kale_pairs_with_cupcake_when_safe(self):
        # The kale+cupcake combo is locked to summer turns (2026-06-25). On a
        # summer turn it still pairs kale with a Plain cupcake mood offset.
        mgr = MantItemManager()
        client = FakeClient()
        mgr.use_items(
            client,
            state(turn=38, vital=30, motivation=4, owned={"Royal Kale Juice": 1, "Plain Cupcake": 1}),
            {"mant_config": {}},
        )
        selected = {row["name"] for row in mgr.last_use_selected}
        self.assertIn("Royal Kale Juice", selected)
        self.assertIn("Plain Cupcake", selected)

    def test_kale_locked_outside_summer_mid_career(self):
        # Mid-career, non-summer (turn 30): the combo is held back even when safe.
        mgr = MantItemManager()
        client = FakeClient()
        mgr.use_items(
            client,
            state(turn=30, vital=30, motivation=4, owned={"Royal Kale Juice": 1, "Plain Cupcake": 1}),
            {"mant_config": {}},
        )
        selected = {row["name"] for row in mgr.last_use_selected}
        self.assertNotIn("Royal Kale Juice", selected)

    def test_race_items_spend_before_conservation_and_reserve_finals(self):
        mgr = MantItemManager()
        planner = FakeRacePlanner()
        planner.program[100] = {"grade": "G1", "fans": 30000, "name": "Big G1"}
        pre = mgr._trackblazer_race_item_targets(
            {"Master Cleat Hammer": 1, "Glow Sticks": 1}, 20, 100, {"mant_config": {}}, planner
        )
        self.assertIn(("Master Cleat Hammer", 1), pre)
        self.assertIn(("Glow Sticks", 1), pre)

        reserved = mgr._trackblazer_race_item_targets(
            {"Master Cleat Hammer": 1, "Glow Sticks": 1}, 74, 100, {"mant_config": {}}, planner
        )
        # Master Cleat Hammer still reserves for the final climax (turn 78).
        self.assertNotIn(("Master Cleat Hammer", 1), reserved)
        # Glow Stick now DUMPS in the finale window (turn 74 is a finale turn):
        # per the item-strategy doctrine it is spent on the big finale race rather
        # than trapped by the final-reserve (fixes "not used if bought after 72").
        self.assertIn(("Glow Sticks", 1), reserved)

        final = mgr._trackblazer_race_item_targets(
            {"Master Cleat Hammer": 1, "Glow Sticks": 1}, 78, 100, {"mant_config": {}}, planner
        )
        self.assertIn(("Master Cleat Hammer", 1), final)
        self.assertIn(("Glow Sticks", 1), final)


if __name__ == "__main__":
    unittest.main()
