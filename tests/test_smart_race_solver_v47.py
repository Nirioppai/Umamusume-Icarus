import json
import tempfile
import unittest
from pathlib import Path

from career_bot import trackblazer


class SmartRaceSolverV47Tests(unittest.TestCase):
    def setUp(self):
        self.root = Path(tempfile.mkdtemp())
        data_dir = self.root / "data"
        tb_dir = data_dir / "trackblazer"
        data_dir.mkdir(parents=True)
        tb_dir.mkdir(parents=True)
        # race_map maps public race names to Sweepy program IDs/turns.
        (data_dir / "race_map.json").write_text(json.dumps({
            "meta": {
                "1": {"program_id": 101, "turn": 14},
                "2": {"program_id": 102, "turn": 15},
                "3": {"program_id": 103, "turn": 16}
            },
            "program": {
                "101": {"name": "Good Mile", "race_instance_id": 1},
                "102": {"name": "Bad Dirt", "race_instance_id": 2},
                "103": {"name": "Manual Race", "race_instance_id": 3}
            },
            "instance": {}
        }), encoding="utf-8")
        (tb_dir / "races.json").write_text(json.dumps([
            {"name": "Good Mile", "grade": "G1", "distance": "Mile", "surface": "Turf", "fans": 10000},
            {"name": "Bad Dirt", "grade": "G1", "distance": "Long", "surface": "Dirt", "fans": 20000},
            {"name": "Manual Race", "grade": "G2", "distance": "Mile", "surface": "Turf", "fans": 6000}
        ]), encoding="utf-8")
        (tb_dir / "epithets.json").write_text("[]", encoding="utf-8")
        (tb_dir / "debut_races.json").write_text("[]", encoding="utf-8")

    def test_smart_solver_uses_aptitudes(self):
        plan = trackblazer.make_schedule(
            self.root,
            solver="smart",
            aptitudes={"Mile": "A", "Turf": "A", "Long": "G", "Dirt": "G"},
            include_op=True,
            floor=6,
        )
        self.assertTrue(plan["success"])
        self.assertIn(101, plan["extra_race_list"])
        self.assertNotIn(102, plan["extra_race_list"])
        self.assertIn(plan["solver"], {"smart-race-solver-beam", "smart-race-solver-milp"})

    def test_manual_lock_is_honored(self):
        plan = trackblazer.make_schedule(
            self.root,
            solver="smart",
            aptitudes={"Mile": "A", "Turf": "A"},
            include_op=True,
            floor=6,
            manual_locks={"16": 103},
        )
        self.assertIn(103, plan["extra_race_list"])


if __name__ == "__main__":
    unittest.main()
