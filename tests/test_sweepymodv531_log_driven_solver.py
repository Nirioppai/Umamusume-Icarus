import json
import os
import tempfile
import unittest
from pathlib import Path

from career_bot import trackblazer
from career_bot.race_intelligence import record_race_outcome, race_outcome_risk, validate_json_file
from career_bot.report import new_report, write_report


class SweepyModV531LogDrivenSolverTests(unittest.TestCase):
    def setUp(self):
        self.root = Path(tempfile.mkdtemp())
        self.runtime = self.root / "runtime"
        os.environ["UMA_RUNTIME_DIR"] = str(self.runtime)
        data = self.root / "data"
        tb = data / "trackblazer"
        data.mkdir(parents=True)
        tb.mkdir(parents=True)
        (data / "race_map.json").write_text(json.dumps({
            "meta": {
                "1": {"program_id": 101, "turn": 66},
                "2": {"program_id": 102, "turn": 66},
                "3": {"program_id": 103, "turn": 56},
                "4": {"program_id": 104, "turn": 67},
            },
            "program": {
                "101": {"name": "Safe Senior G1", "race_instance_id": 1, "distance": 1800, "grade": "G1", "fans": 28000},
                "102": {"name": "Risky Senior G1", "race_instance_id": 2, "distance": 1800, "grade": "G1", "fans": 30000},
                "103": {"name": "Long Trouble", "race_instance_id": 3, "distance": 3200, "grade": "G1", "fans": 15000},
                "104": {"name": "Senior Followup", "race_instance_id": 4, "distance": 2000, "grade": "G2", "fans": 9000},
            },
            "instance": {},
        }), encoding="utf-8")
        (tb / "races.json").write_text(json.dumps([
            {"name": "Safe Senior G1", "grade": "G1", "distance": "Mile", "surface": "Turf", "fans": 28000},
            {"name": "Risky Senior G1", "grade": "G1", "distance": "Mile", "surface": "Turf", "fans": 30000},
            {"name": "Long Trouble", "grade": "G1", "distance": "Long", "surface": "Turf", "fans": 15000},
            {"name": "Senior Followup", "grade": "G2", "distance": "Medium", "surface": "Turf", "fans": 9000},
        ]), encoding="utf-8")
        (tb / "epithets.json").write_text("[]", encoding="utf-8")
        (tb / "debut_races.json").write_text("[]", encoding="utf-8")
        (data / "android_smart_race_epithets.json").write_text(json.dumps({
            "senior": {
                "name": "Senior Pair",
                "matchers": [{"type": "winAnyOf", "count": 2, "names": ["Safe Senior G1", "Senior Followup"]}],
                "bullet_points": ["Win two senior races", "Reward: 2 random stats +10"],
            }
        }), encoding="utf-8")

    def tearDown(self):
        os.environ.pop("UMA_RUNTIME_DIR", None)

    def test_observed_race_loss_penalizes_future_solver_choice(self):
        for rank in (4, 3, 4):
            record_race_outcome(self.root, {"program_id": 102, "turn": 66, "rank": rank, "name": "Risky Senior G1"})
        risk = race_outcome_risk(self.root, 102)
        self.assertGreater(risk["penalty"], 0)
        plan = trackblazer.make_schedule(
            self.root,
            solver="beam",
            aptitudes={"Mile": "A", "Medium": "A", "Long": "A", "Turf": "A"},
            include_op=True,
            floor=6,
            weights={"fanWeight": 0.0001, "outcomeRiskWeight": 2.0, "trainBias": 0.01},
            current_turn=65,
        )
        names = {row["name"] for row in plan["schedule"]}
        self.assertIn("Safe Senior G1", names)
        self.assertNotIn("Risky Senior G1", names)

    def test_long_distance_stamina_risk_and_epithet_ledger_are_reported(self):
        plan = trackblazer.make_schedule(
            self.root,
            solver="beam",
            aptitudes={"Mile": "A", "Medium": "A", "Long": "A", "Turf": "A"},
            include_op=True,
            floor=6,
            forced_epithets=["Senior Pair"],
            weights={"fanWeight": 0.0, "currentStats": {"stamina": 250}, "trainBias": 0.01},
            current_turn=55,
        )
        self.assertTrue(plan["epithet_ledger"])
        self.assertIn("Senior Pair", plan["projected_epithets"])
        long_rows = [row for row in plan["schedule"] if row["name"] == "Long Trouble"]
        if long_rows:
            self.assertTrue(any("long_distance_stamina_risk" in flag for flag in long_rows[0].get("score_flags", [])))

    def test_report_writer_produces_valid_json(self):
        report = new_report({"name": "Default"}, 4)
        report["turns"].append({"turn": 1, "selected_action": "train"})
        path = write_report(report, self.runtime / "logs")
        self.assertTrue(validate_json_file(path)["valid"])
        self.assertTrue(validate_json_file(self.runtime / "logs" / "latest_career_log.json")["valid"])


if __name__ == "__main__":
    unittest.main()
