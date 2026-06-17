import unittest
from pathlib import Path

from career_bot.runner import CareerRunner

ROOT = Path(__file__).resolve().parents[1]
MAIN = (ROOT / "main.py").read_text(encoding="utf-8")
CLIENT = (ROOT / "uma_api" / "client.py").read_text(encoding="utf-8")
APP = (ROOT / "public" / "app.js").read_text(encoding="utf-8")


class SweepyModV510HistoryTpTests(unittest.TestCase):
    def test_runner_extracts_nested_finish_rating_fields(self):
        runner = CareerRunner(".")
        state = {
            "data": {
                "finish_result": {
                    "trained_chara": {
                        "card_id": 100401,
                        "evaluation_point": 12999,
                        "race_count": 40,
                        "win_count": 33,
                        "speed": 826,
                        "stamina": 478,
                        "power": 599,
                        "guts": 403,
                        "wiz": 928,
                    }
                }
            }
        }
        payload = runner._extract_final_chara_payload(state, {"card_id": 100401})
        summary = runner._compact_final_chara(payload)
        self.assertEqual(int(summary["rating"]), 12999)
        self.assertEqual(int(summary["race_count"]), 40)
        self.assertEqual(int(summary["win_count"]), 33)

    def test_runner_records_race_result_ledger(self):
        runner = CareerRunner(".")
        runner.status = {"race_results": []}
        row = runner._record_race_result(12345, rank=1, turn=16)
        self.assertEqual(row["program_id"], 12345)
        self.assertEqual(row["rank"], 1)
        self.assertTrue(row["won"])
        self.assertEqual(len(runner.status["race_results"]), 1)

    def test_history_fallback_counts_use_race_actions_and_race_results(self):
        self.assertIn('str(row.get("action") or "") in {"race", "race_entry"}', MAIN)
        self.assertIn('race_count = len(race_results)', MAIN)
        self.assertIn('wins = sum(1 for row in race_results', MAIN)
        self.assertIn('"race_results": deepcopy(race_results)', MAIN)

    def test_tp_recovery_uses_umabot_item_mode(self):
        self.assertIn('/api/settings/tp-recovery', MAIN)
        self.assertIn('TP_RECOVERY_MODES = ("potion_first", "potion_only", "jewels_only")', MAIN)
        self.assertIn('active_client.use_recovery_item(item_num=1)', MAIN)
        self.assertIn('active_client.recovery_tp(needed)', MAIN)
        self.assertIn('def recovery_tp(self, count=1):', CLIENT)
        self.assertIn('def use_recovery_item(self, item_num=1, item_id=None):', CLIENT)
        self.assertIn('TP POTIONS', APP)
        self.assertIn('tp-recovery-mode-select', APP)


if __name__ == "__main__":
    unittest.main()
