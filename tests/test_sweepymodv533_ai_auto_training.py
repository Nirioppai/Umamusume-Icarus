import json
import os
import tempfile
import time
import unittest
from pathlib import Path

from career_bot import ai_trainer
from career_bot.ai_dataset import export_report_ai_datasets
from career_bot.report import new_report, add_decision


class DummyRaceDecision:
    action = "race"
    reason = "solver-planned race"
    payload = {"current_turn": 56, "program_id": 98765}


class DummyRestDecision:
    action = "rest"
    reason = "low hp"
    payload = {"current_turn": 57, "command_id": 701}


class SweepyModV533AiAutoTrainingTests(unittest.TestCase):
    def setUp(self):
        self.root = Path(tempfile.mkdtemp())
        self.runtime = self.root / "uma_runtime"
        os.environ["UMA_RUNTIME_DIR"] = str(self.runtime)

    def tearDown(self):
        os.environ.pop("UMA_RUNTIME_DIR", None)

    def _report(self):
        report = new_report({"name": "OguriTB"}, 4)
        report["run_id"] = "v533-unit"
        state = {
            "data": {
                "chara_info": {
                    "turn": 56,
                    "vital": 70,
                    "max_vital": 100,
                    "motivation": 4,
                    "fans": 220000,
                    "speed": 850,
                    "stamina": 420,
                    "power": 800,
                    "guts": 320,
                    "wiz": 640,
                    "skill_point": 333,
                }
            }
        }
        add_decision(report, state, DummyRaceDecision())
        turn = report["turns"][0]
        turn.setdefault("item_usage_attempts", []).append({"item_id": 1, "name": "Vita 65", "success": True})
        turn.setdefault("events", []).append({"event_id": "evt-1", "choice": "2", "success": True})
        state["data"]["chara_info"]["turn"] = 57
        state["data"]["chara_info"]["fans"] = 220000
        add_decision(report, state, DummyRestDecision())
        report["race_results"] = [
            {"turn": 56, "program_id": 98765, "rank": 4, "name": "Risky Long", "race_type": "solver_planned"}
        ]
        report["status"] = "finished"
        return report

    def test_train_once_builds_local_analytics_models_and_policy(self):
        export_report_ai_datasets(self._report(), self.runtime / "bot_logs", build_version="test")
        result = ai_trainer.train_once(self.root, reason="unit", rebuild_stats=True)
        self.assertTrue(result["success"])
        ai_root = self.runtime / "ai"
        for name in (
            "race_outcome_table.json",
            "item_effectiveness_table.json",
            "event_outcome_table.json",
            "race_risk_model.json",
            "item_value_model.json",
            "event_value_model.json",
            "policy_adjustments.json",
            "suggested_config_tuning.json",
        ):
            self.assertTrue((ai_root / name).exists(), name)
        policy = json.loads((ai_root / "policy_adjustments.json").read_text(encoding="utf-8"))
        self.assertIn("races", policy)

    def test_auto_config_and_live_race_policy_hint_are_confidence_gated(self):
        ai_trainer.save_auto_config(self.root, {"confidence_threshold": 0.1, "enable_live_policy_assistance": True})
        export_report_ai_datasets(self._report(), self.runtime / "bot_logs", build_version="test")
        ai_trainer.train_once(self.root, reason="unit", rebuild_stats=True)
        hint = ai_trainer.race_policy_adjustment(self.root, 98765, threshold=0.1)
        self.assertTrue(hint["enabled"])
        self.assertLessEqual(hint["adjustment"], 0)

    def test_after_career_export_schedules_background_training_when_enabled(self):
        ai_trainer.save_auto_config(self.runtime, {"enabled": True, "train_after_completed_careers": 1, "confidence_threshold": 0.1})
        manifest = export_report_ai_datasets(self._report(), self.runtime / "bot_logs", build_version="test")
        scheduled = ai_trainer.after_career_export(self.runtime / "bot_logs", manifest=manifest, build_version="test")
        self.assertTrue(scheduled["scheduled"])
        deadline = time.time() + 5
        while time.time() < deadline and not (self.runtime / "ai" / "latest_training_run.json").exists():
            time.sleep(0.05)
        self.assertTrue((self.runtime / "ai" / "latest_training_run.json").exists())


if __name__ == "__main__":
    unittest.main()
