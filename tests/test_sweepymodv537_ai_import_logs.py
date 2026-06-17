import json
import os
import tempfile
import unittest
import zipfile
from pathlib import Path

from career_bot import ai_dataset, ai_trainer
from career_bot.report import add_decision, new_report


class RaceDecision:
    action = "race"
    reason = "solver planned"
    payload = {"current_turn": 56, "program_id": 5601}


def make_report(run_id="imported", rank=1):
    report = new_report({"name": "OguriTB"}, 4)
    report["run_id"] = run_id
    state = {"data": {"chara_info": {"turn": 56, "vital": 74, "max_vital": 100, "motivation": 5, "fans": 222222, "speed": 850, "stamina": 430, "power": 820, "guts": 410, "wiz": 700, "skill_point": 250}}}
    add_decision(report, state, RaceDecision())
    report["turns"][0].setdefault("api_calls", []).append({
        "direction": "RES",
        "endpoint": "single_mode_free/race_end",
        "data": {"data": {"race_reward_info": {"result_rank": rank, "gained_fans": 30000 if rank == 1 else 0}, "chara_info": {"turn": 56, "race_program_id": 5601, "fans": 252222, "speed": 850, "stamina": 430, "power": 820, "guts": 410, "wiz": 700, "skill_point": 250}, "race_history": [{"turn": 56, "program_id": 5601, "result_rank": rank}]}}
    })
    report["status"] = "finished"
    report["final_stats"] = {"speed": 850, "stamina": 430, "power": 820, "guts": 410, "wit": 700, "fans": 252222}
    return report


class SweepyModV537AiImportLogsTests(unittest.TestCase):
    def setUp(self):
        self.root = Path(tempfile.mkdtemp())
        self.runtime = self.root / "current" / "uma_runtime" / "default"
        os.environ["UMA_RUNTIME_DIR"] = str(self.runtime)
        self.runtime.mkdir(parents=True, exist_ok=True)
        self.old = self.root / "old_build" / "uma_runtime" / "default"
        (self.old / "bot_logs").mkdir(parents=True, exist_ok=True)
        (self.old / "bot_logs" / "career_log_20260101_000001.json").write_text(json.dumps(make_report("old-1")), encoding="utf-8")
        (self.old / "race_outcomes.json").write_text(json.dumps({"programs": {"5601": {"starts": 2, "wins": 1, "losses": 1, "ranks": [1, 4], "name": "Tenno Sho Spring"}}}), encoding="utf-8")
        (self.old / "events_seen.json").write_text(json.dumps({"events": [{"story_id": "evt1", "choice": 1, "seen_count": 2}]}), encoding="utf-8")

    def tearDown(self):
        os.environ.pop("UMA_RUNTIME_DIR", None)

    def test_import_previous_runtime_folder_rebuilds_and_trains(self):
        result = ai_dataset.import_previous_logs(self.root / "current", str(self.old), rebuild=True, build_version="test")
        self.assertTrue(result["success"])
        self.assertEqual(result["imported_logs"], 1)
        self.assertEqual(result["duplicates"], 0)
        self.assertGreaterEqual(result["rebuild"]["processed"], 1)
        status = ai_dataset.dataset_status(self.root / "current")
        self.assertGreaterEqual(status["files"]["turn_decisions"]["rows"], 1)
        trained = ai_trainer.train_once(self.root / "current", reason="unit", rebuild_stats=True)
        self.assertTrue(trained["success"])
        self.assertGreaterEqual(trained["records"]["turn_decisions"], 1)

    def test_import_is_deduplicated_by_hash(self):
        first = ai_dataset.import_previous_logs(self.root / "current", str(self.old), rebuild=False)
        second = ai_dataset.import_previous_logs(self.root / "current", str(self.old), rebuild=False)
        self.assertEqual(first["imported_logs"], 1)
        self.assertEqual(second["imported_logs"], 0)
        self.assertGreaterEqual(second["duplicates"], 1)

    def test_import_zip_source(self):
        zpath = self.root / "old_logs.zip"
        with zipfile.ZipFile(zpath, "w") as zf:
            zf.write(self.old / "bot_logs" / "career_log_20260101_000001.json", "SweepyModv5.33/uma_runtime/default/bot_logs/career_log_20260101_000001.json")
            zf.write(self.old / "race_outcomes.json", "SweepyModv5.33/uma_runtime/default/race_outcomes.json")
        result = ai_dataset.import_previous_logs(self.root / "current", str(zpath), rebuild=True)
        self.assertTrue(result["success"])
        self.assertEqual(result["imported_logs"], 1)
        self.assertGreaterEqual(result["race_outcomes"]["merged_programs"], 1)

    def test_ui_has_import_previous_logs_controls(self):
        html = Path("public/index.html").read_text(encoding="utf-8")
        js = Path("public/app.js").read_text(encoding="utf-8")
        self.assertIn("v537-ai-import-path", html)
        self.assertIn("v537-ai-import-btn", html)
        self.assertIn("/api/ai/import-logs", js)
        self.assertIn("importPreviousAiLogs", js)


if __name__ == "__main__":
    unittest.main()
