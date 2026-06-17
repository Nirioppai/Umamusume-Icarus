import json
import tempfile
import unittest
from pathlib import Path

from career_bot import trackblazer


class SmartRaceSolverV48MilpTests(unittest.TestCase):
    def setUp(self):
        self.root = Path(tempfile.mkdtemp())
        data_dir = self.root / "data"
        tb_dir = data_dir / "trackblazer"
        data_dir.mkdir(parents=True)
        tb_dir.mkdir(parents=True)
        (data_dir / "race_map.json").write_text(json.dumps({
            "meta": {
                "1": {"program_id": 101, "turn": 14},
                "2": {"program_id": 102, "turn": 15},
                "3": {"program_id": 103, "turn": 16},
                "4": {"program_id": 104, "turn": 17}
            },
            "program": {
                "101": {"name": "Good Mile", "race_instance_id": 1},
                "102": {"name": "Good Mile Two", "race_instance_id": 2},
                "103": {"name": "Manual Race", "race_instance_id": 3},
                "104": {"name": "Fourth Race", "race_instance_id": 4}
            },
            "instance": {}
        }), encoding="utf-8")
        (tb_dir / "races.json").write_text(json.dumps([
            {"name": "Good Mile", "grade": "G1", "distance": "Mile", "surface": "Turf", "fans": 10000},
            {"name": "Good Mile Two", "grade": "G1", "distance": "Mile", "surface": "Turf", "fans": 9000},
            {"name": "Manual Race", "grade": "G2", "distance": "Mile", "surface": "Turf", "fans": 6000},
            {"name": "Fourth Race", "grade": "G3", "distance": "Mile", "surface": "Turf", "fans": 5000}
        ]), encoding="utf-8")
        (tb_dir / "epithets.json").write_text("[]", encoding="utf-8")
        (tb_dir / "debut_races.json").write_text("[]", encoding="utf-8")

    def test_milp_or_fallback_returns_smart_schedule(self):
        plan = trackblazer.make_schedule(
            self.root,
            solver="smart",
            aptitudes={"Mile": "A", "Turf": "A"},
            include_op=True,
            floor=6,
            max_races_in_row=2,
            weights={"fanWeight": 0.01},
        )
        self.assertTrue(plan["success"])
        self.assertIn(plan["solver"], {"smart-race-solver-milp", "smart-race-solver-beam-fallback"})
        self.assertLessEqual(len(plan["extra_race_list"]), 3)

    def test_hard_manual_train_lock_blocks_turn(self):
        plan = trackblazer.make_schedule(
            self.root,
            solver="smart",
            aptitudes={"Mile": "A", "Turf": "A"},
            include_op=True,
            floor=6,
            max_races_in_row=2,
            manual_locks={"14": "train"},
            weights={"fanWeight": 0.01},
        )
        self.assertNotIn(101, plan["extra_race_list"])


if __name__ == "__main__":
    unittest.main()
