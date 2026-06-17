import json
import os
import tempfile
import unittest
from pathlib import Path

from career_bot import ai_trainer
from career_bot.ai_dataset import career_summary_record, dataset_status, export_report_ai_datasets, turn_decision_records
from career_bot.report import new_report, add_decision


class RaceDecision:
    action = "race"
    reason = "solver planned"
    payload = {"current_turn": 12, "program_id": 1070}


class UnknownRaceDecision:
    action = "race"
    reason = "missing result"
    payload = {"current_turn": 12, "program_id": 9999}


class SweepyModV534AiTrainingRepairTests(unittest.TestCase):
    def setUp(self):
        self.root = Path(tempfile.mkdtemp())
        self.runtime = self.root / "uma_runtime" / "default"
        os.environ["UMA_RUNTIME_DIR"] = str(self.runtime)
        self.runtime.mkdir(parents=True, exist_ok=True)

    def tearDown(self):
        os.environ.pop("UMA_RUNTIME_DIR", None)

    def _report_with_race_end_api(self):
        report = new_report({"name": "OguriTB"}, 4)
        report["run_id"] = "v534-race-end"
        state = {"data": {"chara_info": {"turn": 12, "vital": 90, "max_vital": 100, "motivation": 5, "fans": 1, "speed": 250, "stamina": 80, "power": 200, "guts": 100, "wiz": 180, "skill_point": 120}}}
        add_decision(report, state, RaceDecision())
        turn = report["turns"][0]
        turn.setdefault("api_calls", []).append({
            "direction": "RES",
            "endpoint": "single_mode_free/race_end",
            "turn": 12,
            "data": {
                "response_code": 1,
                "data": {
                    "race_reward_info": {"result_rank": 1, "gained_fans": 1463},
                    "chara_info": {"turn": 12, "race_program_id": 1070, "fans": 1464, "speed": 270, "stamina": 85, "power": 218, "guts": 125, "wiz": 237, "skill_point": 191, "vital": 92, "max_vital": 100, "motivation": 5},
                    "race_history": [{"turn": 12, "program_id": 1070, "result_rank": 1, "weather": 1, "ground_condition": 2, "running_style": 3}],
                },
            },
        })
        report["status"] = "finished"
        return report

    def test_race_end_api_response_becomes_ai_race_result(self):
        rows = turn_decision_records(self._report_with_race_end_api(), build_version="test")
        self.assertEqual(rows[0]["outcome"]["race_result"]["result_rank"], 1)
        self.assertEqual(rows[0]["outcome"]["race_result"]["program_id"], 1070)
        self.assertGreater(rows[0]["outcome"]["reward"], 0)

    def test_career_summary_uses_last_turn_api_stats_and_race_results(self):
        summary = career_summary_record(self._report_with_race_end_api(), build_version="test")
        self.assertEqual(summary["final_stats"]["fans"], 1464)
        self.assertEqual(summary["race_count"], 1)
        self.assertEqual(summary["race_wins"], 1)

    def test_item_event_flattening_and_prompt_manifest_overwrite(self):
        report = self._report_with_race_end_api()
        turn = report["turns"][0]
        turn.setdefault("item_usage_attempts", []).append({"event": "items_use_attempt", "selected": [{"item_id": 1001, "name": "Speed Notepad"}], "attempt": [{"item_id": 1001, "use_num": 1}]})
        (self.runtime / "events_seen.json").write_text(json.dumps({"evt-1": {"event_id": "evt-1", "choice": "2", "title": "Unit Event"}}), encoding="utf-8")
        export_report_ai_datasets(report, self.runtime / "bot_logs", build_version="test")
        result1 = ai_trainer.train_once(self.root, reason="unit", rebuild_stats=True)
        result2 = ai_trainer.train_once(self.root, reason="unit2", rebuild_stats=True)
        ai_root = self.runtime / "ai"
        items = json.loads((ai_root / "item_effectiveness_table.json").read_text(encoding="utf-8"))["items"]
        events = json.loads((ai_root / "event_outcome_table.json").read_text(encoding="utf-8"))["events"]
        self.assertIn("1001", items)
        self.assertIn("evt-1", events)
        manifest = json.loads((ai_root / "llm_advisor" / "latest_prompt_pack_manifest.json").read_text(encoding="utf-8"))
        line_count = sum(1 for _ in (ai_root / "llm_advisor" / "latest_prompt_pack.jsonl").open("r", encoding="utf-8"))
        self.assertEqual(manifest["prompt_count"], line_count)
        self.assertEqual(result1["success"], True)
        self.assertEqual(result2["success"], True)

    def test_unhealthy_race_rows_auto_disable_live_policy(self):
        report = new_report({"name": "OguriTB"}, 4)
        report["run_id"] = "bad-data"
        state = {"data": {"chara_info": {"turn": 12, "vital": 90, "max_vital": 100, "motivation": 5, "fans": 1}}}
        add_decision(report, state, UnknownRaceDecision())
        report["status"] = "finished"
        ai_trainer.save_auto_config(self.root, {"enable_live_policy_assistance": True, "confidence_threshold": 0.1})
        export_report_ai_datasets(report, self.runtime / "bot_logs", build_version="test")
        result = ai_trainer.train_once(self.root, reason="unit", rebuild_stats=True)
        self.assertFalse(result["live_policy_enabled"])
        self.assertFalse(result["data_health"]["safe_for_live_policy"])
        self.assertFalse(ai_trainer.load_auto_config(self.root)["enable_live_policy_assistance"])

    def test_dataset_status_health_and_safe_debug_bundle(self):
        export_report_ai_datasets(self._report_with_race_end_api(), self.runtime / "bot_logs", build_version="test")
        ai_trainer.train_once(self.root, reason="unit", rebuild_stats=True)
        status = dataset_status(self.root)
        self.assertTrue(status["health"]["safe_for_live_policy"])
        bundle = ai_trainer.create_safe_debug_bundle(self.root)
        self.assertTrue(bundle.exists())
        import zipfile
        with zipfile.ZipFile(bundle) as zf:
            names = set(zf.namelist())
        self.assertIn("ai/ai_data_health.json", names)
        self.assertNotIn("uma_runtime/default/auth_config.json", names)


if __name__ == "__main__":
    unittest.main()
