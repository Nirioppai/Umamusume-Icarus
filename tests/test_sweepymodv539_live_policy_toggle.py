import os
import tempfile
import unittest
from pathlib import Path

from career_bot import ai_trainer
from career_bot.ai_dataset import export_report_ai_datasets
from career_bot.report import add_decision, new_report


class RaceDecision:
    action = "race"
    reason = "solver planned"
    payload = {"current_turn": 56, "program_id": 5601}


class SweepyModV539LivePolicyToggleTests(unittest.TestCase):
    def setUp(self):
        self.root = Path(tempfile.mkdtemp())
        self.runtime = self.root / "uma_runtime" / "default"
        os.environ["UMA_RUNTIME_DIR"] = str(self.runtime)
        self.runtime.mkdir(parents=True, exist_ok=True)

    def tearDown(self):
        os.environ.pop("UMA_RUNTIME_DIR", None)

    def _report(self, rank=4, run_id="v539"):
        report = new_report({"name": "OguriTB"}, 4)
        report["run_id"] = run_id
        state = {"data": {"chara_info": {"turn": 56, "vital": 74, "max_vital": 100, "motivation": 5, "fans": 222222, "speed": 850, "stamina": 430, "power": 820, "guts": 410, "wiz": 700, "skill_point": 250}}}
        add_decision(report, state, RaceDecision())
        report["turns"][0].setdefault("api_calls", []).append({
            "direction": "RES",
            "endpoint": "single_mode_free/race_end",
            "data": {"data": {"race_reward_info": {"result_rank": rank, "gained_fans": 0 if rank != 1 else 30000}, "chara_info": {"turn": 56, "race_program_id": 5601, "fans": 222222, "speed": 850, "stamina": 430, "power": 820, "guts": 410, "wiz": 700, "skill_point": 250}, "race_history": [{"turn": 56, "program_id": 5601, "result_rank": rank}]}}
        })
        report["status"] = "finished"
        report["final_stats"] = {"speed": 850, "stamina": 430, "power": 820, "guts": 410, "wit": 700, "fans": 222222}
        return report

    def test_live_policy_config_toggle_is_persisted_and_reported(self):
        cfg = ai_trainer.save_auto_config(self.root, {"enable_live_policy_assistance": True})
        self.assertTrue(cfg["enable_live_policy_assistance"])
        status = ai_trainer.trainer_status(self.root)
        self.assertTrue(status["live_policy"]["requested_enabled"])
        self.assertIn("recommendation", status["live_policy"])

        cfg = ai_trainer.save_auto_config(self.root, {"enable_live_policy_assistance": False})
        self.assertFalse(cfg["enable_live_policy_assistance"])
        status = ai_trainer.trainer_status(self.root)
        self.assertFalse(status["live_policy"]["requested_enabled"])

    def test_recommendation_warns_when_data_is_not_ready(self):
        rec = ai_trainer.live_policy_recommendation(
            {"enable_live_policy_assistance": False, "confidence_threshold": 0.65},
            {"safe_for_live_policy": True, "race_rows": 0, "race_rows_with_result": 0, "race_result_coverage": 0},
            {"enabled": True, "races": {}},
            records={"turn_decisions": 0},
            confidence="low",
        )
        self.assertFalse(rec["recommend_enable"])
        self.assertEqual(rec["status"], "recommended_off")

    def test_dashboard_contains_live_policy_recommendation(self):
        for idx in range(3):
            export_report_ai_datasets(self._report(rank=4, run_id=f"v539-{idx}"), self.runtime / "bot_logs", build_version="test")
        ai_trainer.save_auto_config(self.root, {"confidence_threshold": 0.1, "enable_live_policy_assistance": True})
        ai_trainer.train_once(self.root, reason="unit", rebuild_stats=True)
        dashboard = ai_trainer.latest_dashboard(self.root)
        self.assertTrue(dashboard["success"])
        self.assertIn("recommendation", dashboard["live_policy"])
        self.assertIn("message", dashboard["live_policy"]["recommendation"])

    def test_ui_contains_live_policy_toggle(self):
        html = Path("public/index.html").read_text(encoding="utf-8")
        app = Path("public/app.js").read_text(encoding="utf-8")
        self.assertIn('id="v539-ai-live-policy-toggle"', html)
        self.assertIn("toggleAiLivePolicyAssistance", app)
        self.assertIn("enable_live_policy_assistance", app)


if __name__ == "__main__":
    unittest.main()
