import json
import os
import tempfile
import unittest
from pathlib import Path

from career_bot.ai_dataset import (
    dataset_status,
    export_report_ai_datasets,
    rebuild_from_career_logs,
    turn_decision_records,
)
from career_bot.ai_advisor import post_run_advice, race_program_hint
from career_bot.report import new_report, add_decision, write_report


class DummyDecision:
    action = "race"
    reason = "solver-planned race"
    payload = {"current_turn": 56, "program_id": 99901}


class SweepyModV532AiDatasetTests(unittest.TestCase):
    def setUp(self):
        self.root = Path(tempfile.mkdtemp())
        self.runtime = self.root / "uma_runtime"
        os.environ["UMA_RUNTIME_DIR"] = str(self.runtime)

    def tearDown(self):
        os.environ.pop("UMA_RUNTIME_DIR", None)

    def _sample_report(self):
        report = new_report({"name": "OguriTB"}, 4)
        report["run_id"] = "unit-run"
        state = {
            "data": {
                "chara_info": {
                    "turn": 56,
                    "vital": 72,
                    "max_vital": 100,
                    "motivation": 4,
                    "fans": 200000,
                    "speed": 800,
                    "stamina": 420,
                    "power": 790,
                    "guts": 300,
                    "wiz": 600,
                    "skill_point": 300,
                }
            }
        }
        add_decision(report, state, DummyDecision())
        report["race_results"] = [
            {"turn": 56, "program_id": 99901, "rank": 4, "name": "Long Trouble", "race_type": "solver_planned"}
        ]
        report["status"] = "finished"
        report["ended_at"] = "2026-06-14T00:00:00"
        return report

    def test_turn_decision_records_include_reward_and_race_result(self):
        rows = turn_decision_records(self._sample_report(), build_version="test")
        self.assertEqual(len(rows), 1)
        self.assertEqual(rows[0]["action"]["type"], "race")
        self.assertEqual(rows[0]["outcome"]["race_result"]["rank"], 4)
        self.assertLess(rows[0]["outcome"]["reward"], 0)

    def test_export_writes_ai_jsonl_and_advisor_stats(self):
        manifest = export_report_ai_datasets(self._sample_report(), self.runtime / "bot_logs", build_version="test")
        self.assertEqual(manifest["counts"]["turn_decisions"], 1)
        status = dataset_status(self.root)
        self.assertEqual(status["files"]["turn_decisions"]["rows"], 1)
        self.assertTrue((self.runtime / "ai" / "advisor_stats.json").exists())
        hint = race_program_hint(self.root, 99901)
        self.assertGreaterEqual(hint["starts"], 1)

    def test_report_writer_exports_ai_dataset_best_effort(self):
        report = self._sample_report()
        path = write_report(report, self.runtime / "bot_logs")
        self.assertTrue(path.exists())
        status = dataset_status(self.root)
        self.assertGreaterEqual(status["files"]["career_summaries"]["rows"], 1)

    def test_rebuild_from_existing_logs_and_post_run_advice(self):
        report = self._sample_report()
        logs = self.runtime / "bot_logs"
        logs.mkdir(parents=True)
        (logs / "career_log_20260614_000000.json").write_text(json.dumps(report), encoding="utf-8")
        rebuilt = rebuild_from_career_logs(self.root, build_version="test")
        self.assertEqual(rebuilt["processed"], 1)
        advice = post_run_advice(self.root)
        self.assertTrue(advice["success"])
        self.assertTrue(advice["tips"])


if __name__ == "__main__":
    unittest.main()
