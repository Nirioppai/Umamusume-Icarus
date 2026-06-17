import json
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


class SweepyModV536AiDashboardTests(unittest.TestCase):
    def setUp(self):
        self.root = Path(tempfile.mkdtemp())
        self.runtime = self.root / "uma_runtime" / "default"
        os.environ["UMA_RUNTIME_DIR"] = str(self.runtime)
        self.runtime.mkdir(parents=True, exist_ok=True)

    def tearDown(self):
        os.environ.pop("UMA_RUNTIME_DIR", None)

    def _report(self, rank=4):
        report = new_report({"name": "OguriTB"}, 4)
        report["run_id"] = f"v536-{rank}"
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

    def test_dashboard_shadow_backtest_and_confidence_artifacts_are_written(self):
        for _ in range(3):
            export_report_ai_datasets(self._report(rank=4), self.runtime / "bot_logs", build_version="test")
        ai_trainer.save_auto_config(self.root, {"confidence_threshold": 0.5, "enable_live_policy_assistance": True})
        result = ai_trainer.train_once(self.root, reason="unit", rebuild_stats=True)
        self.assertTrue(result["success"])
        ai_root = self.runtime / "ai"
        for name in ["ai_dashboard.json", "shadow_policy_report.json", "backtest_report.json", "epithet_confidence.json", "preset_trainee_confidence.json"]:
            self.assertTrue((ai_root / name).exists(), name)
        dashboard = ai_trainer.latest_dashboard(self.root)
        self.assertTrue(dashboard["success"])
        self.assertIn(dashboard["confidence"], {"low", "medium", "high"})
        self.assertGreaterEqual(dashboard["records"]["race_programs"], 1)
        self.assertGreaterEqual(dashboard["backtest"]["failed_races_captured"], 1)
        self.assertGreaterEqual(dashboard["shadow_mode"]["useful_warnings"], 1)

    def test_safe_bundle_includes_new_dashboard_artifacts(self):
        export_report_ai_datasets(self._report(rank=1), self.runtime / "bot_logs", build_version="test")
        ai_trainer.train_once(self.root, reason="unit", rebuild_stats=True)
        bundle = ai_trainer.create_safe_debug_bundle(self.root)
        import zipfile
        with zipfile.ZipFile(bundle) as zf:
            names = set(zf.namelist())
        self.assertIn("ai/ai_dashboard.json", names)
        self.assertIn("ai/backtest_report.json", names)
        self.assertIn("ai/shadow_policy_report.json", names)


if __name__ == "__main__":
    unittest.main()
