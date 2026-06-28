"""2026-06-22 batch 2: dashboard live-status, shop coin spend-down, log slimming."""
import unittest
from pathlib import Path

from career_bot.items import MantItemManager
from career_bot.report import _slim_api_event
from career_bot.ai_dataset import _race_result_from_api_calls, _api_context_from_turn

ROOT = Path(__file__).resolve().parents[1]
APP = (ROOT / "public" / "app.js").read_text(encoding="utf-8")


# ---------------------------------------------------------------- #1 dashboard
class DashboardLivePollTests(unittest.TestCase):
    def test_poll_no_longer_self_terminates(self):
        # The old "kill the timer on a not-running snapshot" block is gone.
        self.assertNotIn("state.runnerTimer = 0;", APP)
        self.assertIn("do NOT stop polling when a snapshot reports not-running", APP)

    def test_visibility_focus_rearm(self):
        self.assertIn("function ensureRunnerPolling()", APP)
        self.assertIn("addEventListener('visibilitychange'", APP)
        self.assertIn("window.addEventListener('focus', ensureRunnerPolling)", APP)
        self.assertIn("window.addEventListener('pageshow', ensureRunnerPolling)", APP)

    def test_finished_branch_one_shot_latch(self):
        # The always-on poll must not re-fire clearFinishedSetupState every tick.
        self.assertIn("!state.finishHandledForRun", APP)
        self.assertIn("state.finishHandledForRun = true;", APP)
        self.assertIn("state.finishHandledForRun = false;", APP)  # reset on new run


# ---------------------------------------------------------------- #2 shop coins
class ShopSpendDownTests(unittest.TestCase):
    def setUp(self):
        self.mgr = MantItemManager()

    def test_notepad_skipped_when_low_coins_but_bought_when_flush(self):
        preset = {"mant_config": {}}
        # Low coins -> skip the tiny +3 notepad (default behavior).
        self.assertTrue(self.mgr._skip_buy("Speed Notepad", {}, preset=preset, turn=50, budget=100))
        # Flush (>= 250 default) -> no longer skipped, so surplus coins buy stats.
        self.assertFalse(self.mgr._skip_buy("Speed Notepad", {}, preset=preset, turn=50, budget=300))

    def test_notepad_flush_threshold_is_configurable(self):
        preset = {"mant_config": {"trackblazer_notepad_flush_coin": 600}}
        self.assertTrue(self.mgr._skip_buy("Speed Notepad", {}, preset=preset, turn=50, budget=300))
        self.assertFalse(self.mgr._skip_buy("Speed Notepad", {}, preset=preset, turn=50, budget=650))

    def test_finale_reserve_default_lowered_to_150(self):
        # In the finale window the conservative reserve is 150 (guide value), 0
        # mid-career. As of 2026-06-25 the 150 hoard only applies when
        # save_items_lategame=True; the default (dump mode) keeps just the
        # ~60-coin Master Cleat Hammer floor so surplus coins convert to items.
        self.assertEqual(self.mgr._coin_reserve(70, 500, {"save_items_lategame": True}), 150)
        self.assertEqual(self.mgr._coin_reserve(40, 500, {"save_items_lategame": True}), 0)
        self.assertEqual(self.mgr._coin_reserve(70, 500, {}), 60)
        self.assertEqual(self.mgr._coin_reserve(40, 500, {}), 0)


# ---------------------------------------------------------------- #3 log slimming
def _race_end_event():
    return {
        "ts": 1, "direction": "RES", "endpoint": "single_mode_free/race_end",
        "req_id": "x", "turn": 40,
        "data": {"data": {
            "race_reward_info": {"gained_fans": 1000, "result_rank": 1},
            "chara_info": {"fans": 5000, "race_program_id": 101, "race_running_style": 3, "name": "Oguri", "card_id": 1001},
            "race_history": [{"turn": 40, "result_rank": 1, "weather": 1, "ground_condition": 1, "running_style": 3, "program_id": 101}],
            "runner_context": {"big": "x" * 100000},   # bot-injected bloat
            "action_history": [1, 2, 3],               # bot-injected bloat
            "support_card_list": [{"junk": 1}],        # large game array, unread
        }},
    }


def _state_event():
    return {
        "direction": "RES", "endpoint": "single_mode/load", "turn": 40,
        "data": {"data": {
            "home_info": {"available_continue_num": 1},
            "free_data_set": {"coin_num": 300},
            "race_condition_array": [{"program_id": 5}, {"program_id": 6}],
            "unchecked_event_array": [],
            "race_history": [{"junk": "x" * 100000}],  # bot-injected on a NON-race_end -> drop
            "runner_context": {"big": 1},
        }},
    }


class LogSlimTests(unittest.TestCase):
    def test_race_end_keeps_consumer_keys_drops_bloat(self):
        inner = _slim_api_event(_race_end_event())["data"]["data"]
        for k in ("race_reward_info", "chara_info", "race_history"):
            self.assertIn(k, inner)
        for k in ("runner_context", "action_history", "support_card_list"):
            self.assertNotIn(k, inner)

    def test_non_race_end_drops_race_history_and_bloat(self):
        inner = _slim_api_event(_state_event())["data"]["data"]
        for k in ("home_info", "free_data_set", "race_condition_array"):
            self.assertIn(k, inner)
        self.assertNotIn("race_history", inner)   # only kept on race_end
        self.assertNotIn("runner_context", inner)

    def test_ai_dataset_race_result_parity_after_slim(self):
        turn = {"turn": 40, "api_calls": [_slim_api_event(_race_end_event())]}
        row = _race_result_from_api_calls(turn, program_id=101)
        self.assertIsNotNone(row)
        self.assertEqual(row["rank"], 1)
        self.assertEqual(row["program_id"], 101)
        self.assertEqual(row["fans_gained"], 1000)
        self.assertEqual(row["running_style"], 3)

    def test_err_call_keeps_error_text(self):
        slim = _slim_api_event({"direction": "ERR", "endpoint": "x", "turn": 5, "data": {"error": "boom"}})
        self.assertEqual(slim.get("error"), "boom")

    def test_ai_dataset_context_parity_after_slim(self):
        turn = {"turn": 40, "api_calls": [_slim_api_event(_state_event())]}
        ctx = _api_context_from_turn(turn)
        self.assertEqual(ctx["coin_num"], 300)
        self.assertEqual(ctx["available_race_count"], 2)
        self.assertEqual(sorted(ctx["available_race_program_ids"]), [5, 6])


if __name__ == "__main__":
    unittest.main()
