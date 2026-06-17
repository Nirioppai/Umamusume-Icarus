import json
import tempfile
import unittest
from pathlib import Path

from career_bot.races import RacePlanner

ROOT = Path(__file__).resolve().parents[1]
APP = (ROOT / "public" / "app.js").read_text(encoding="utf-8")
MAIN = (ROOT / "main.py").read_text(encoding="utf-8")
RACES = (ROOT / "career_bot" / "races.py").read_text(encoding="utf-8")
MANT = (ROOT / "career_bot" / "scenarios" / "mant.py").read_text(encoding="utf-8")


class SweepyModV521SetupAndManualRaceTests(unittest.TestCase):
    def test_frontend_clears_finished_setup_lock(self):
        self.assertIn("function clearFinishedSetupState", APP)
        self.assertIn("dashData.account = { ...dashData.account, career: null }", APP)
        self.assertIn("resetSelection();", APP)
        self.assertIn("syncSelectionToServer();", APP)
        self.assertIn("Career finished. Setup unlocked", APP)
        self.assertIn("data.selection_cleared", APP)

    def test_backend_clears_finished_session_state(self):
        self.assertIn("def _clear_finished_career_setup_state", MAIN)
        self.assertIn('active_account["career"] = None', MAIN)
        self.assertIn("active_selection = _empty_ui_selection()", MAIN)
        self.assertIn("selection_cleared", MAIN)
        self.assertIn("extra = _clear_finished_career_setup_state(clear_selection=True)", MAIN)

    def test_start_saves_manual_races_before_autoplan(self):
        self.assertIn("Applying manual race selection", APP)
        self.assertIn("await autoSaveRaces({ force: true });", APP)
        self.assertIn("} else if (!activeCareer && state.autoPlanBeforeRun) {", APP)
        self.assertIn("race_planner_mode: state.racePlannerMode || 'smart'", APP)
        self.assertIn("manual_race_ids", APP)
        self.assertIn("source: state.racePlannerMode === 'manual' ? 'manual' : 'smart'", APP)

    def test_backend_runtime_preset_marks_manual_source(self):
        self.assertIn("race_planner_mode: str = \"smart\"", MAIN)
        self.assertIn("manual_race_ids: list[int] = []", MAIN)
        self.assertIn('runtime_preset["extra_race_list_source"] = race_mode', MAIN)
        self.assertIn('runtime_preset["extra_race_list"] = manual_ids', MAIN)
        self.assertIn('preset["extra_race_list_source"] = source', MAIN)

    def test_manual_race_list_beats_force_racing(self):
        with tempfile.TemporaryDirectory() as tmp:
            base = Path(tmp)
            data = base / "data"
            data.mkdir()
            (data / "race_map.json").write_text(json.dumps({
                "meta": {},
                "program": {
                    "1": {"program_id": 1, "turn": 20, "distance": 1200, "ground": 1, "grade": "G1", "fans": 10000},
                    "2": {"program_id": 2, "turn": 20, "distance": 3200, "ground": 2, "grade": "OP", "fans": 1}
                },
                "instance": {}
            }), encoding="utf-8")
            planner = RacePlanner(base)
            state = {
                "data": {
                    "chara_info": {
                        "turn": 20,
                        "scenario_id": 4,
                        "proper_ground_turf": 8,
                        "proper_ground_dirt": 1,
                        "proper_distance_short": 8,
                        "proper_distance_long": 1,
                    },
                    "home_info": {"command_info_array": [{"command_type": 4, "command_id": 401, "is_enable": 1}]},
                    "race_condition_array": [{"program_id": 1}, {"program_id": 2}],
                }
            }
            preset = {
                "extra_race_list": [2],
                "extra_race_list_source": "manual",
                "mant_config": {"force_racing": True},
            }
            self.assertEqual(planner.choose(state, preset), 2)

    def test_irregular_training_does_not_hijack_manual_races(self):
        self.assertIn('extra_race_list_source") or "").strip().lower() == "manual"', MANT)
        self.assertLess(
            MANT.index('extra_race_list_source") or "").strip().lower() == "manual"'),
            MANT.index('if not cfg.get("enable_irregular_training", True):')
        )
        self.assertIn("is_manual_race_list", RACES)
        self.assertIn("if valid_wanted and is_manual_race_list", RACES)


if __name__ == "__main__":
    unittest.main()
