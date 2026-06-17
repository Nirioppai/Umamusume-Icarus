import json
import tempfile
import unittest
from pathlib import Path

from career_bot import trackblazer


class SweepyModV530AndroidSmartSolverTests(unittest.TestCase):
    def setUp(self):
        self.root = Path(tempfile.mkdtemp())
        data = self.root / "data"
        tb = data / "trackblazer"
        data.mkdir(parents=True)
        tb.mkdir(parents=True)
        (data / "race_map.json").write_text(json.dumps({
            "meta": {
                "1": {"program_id": 101, "turn": 14},
                "2": {"program_id": 102, "turn": 15},
                "3": {"program_id": 103, "turn": 16},
                "4": {"program_id": 104, "turn": 17},
            },
            "program": {
                "101": {"name": "Mile Jackpot", "race_instance_id": 1},
                "102": {"name": "Medium Starter", "race_instance_id": 2},
                "103": {"name": "Medium Crown", "race_instance_id": 3},
                "104": {"name": "Dependency Race", "race_instance_id": 4},
            },
            "instance": {},
        }), encoding="utf-8")
        (tb / "races.json").write_text(json.dumps([
            {"name": "Mile Jackpot", "grade": "G1", "distance": "Mile", "surface": "Turf", "fans": 55000},
            {"name": "Medium Starter", "grade": "G2", "distance": "Medium", "surface": "Turf", "fans": 6000},
            {"name": "Medium Crown", "grade": "G2", "distance": "Medium", "surface": "Turf", "fans": 6000},
            {"name": "Dependency Race", "grade": "G1", "distance": "Long", "surface": "Turf", "fans": 12000},
        ]), encoding="utf-8")
        (tb / "epithets.json").write_text("[]", encoding="utf-8")
        (tb / "debut_races.json").write_text("[]", encoding="utf-8")
        (data / "android_smart_race_epithets.json").write_text(json.dumps({
            "mediumPair": {
                "name": "Medium Pair",
                "bullet_points": ["Win 2 Medium races", "Reward: 2 random stats +10"],
                "matchers": [{"type": "winCount", "count": 2, "filter": {"distanceTypes": ["Medium"]}}],
            },
            "base": {
                "name": "Base Win",
                "bullet_points": ["Win the Dependency Race", "Reward: Homestretch Haste hint +1"],
                "matchers": [{"type": "winRace", "name": "Dependency Race"}],
            },
            "combo": {
                "name": "Dependency Combo",
                "bullet_points": ["Get Base Win", "Reward: 2 random stats +10"],
                "matchers": [{"type": "epithetAll", "names": ["Base Win"]}],
            },
        }), encoding="utf-8")

    def test_strict_distance_preference_excludes_off_preference_g1(self):
        plan = trackblazer.make_schedule(
            self.root,
            solver="beam",
            aptitudes={"Mile": "A", "Medium": "A", "Long": "A", "Turf": "A"},
            include_op=True,
            floor=6,
            preferred_distances=["Medium"],
            distance_preference_mode="strict",
            weights={"fanWeight": 0.01, "trainBias": 0.01},
        )
        names = {row["name"] for row in plan["schedule"]}
        self.assertNotIn("Mile Jackpot", names)
        self.assertTrue(all(row.get("distance") == "Medium" for row in plan["schedule"]))
        self.assertEqual(plan["distance_preference_mode"], "strict")

    def test_forced_structured_epithet_requires_multi_race_completion(self):
        plan = trackblazer.make_schedule(
            self.root,
            solver="beam",
            aptitudes={"Mile": "A", "Medium": "A", "Long": "A", "Turf": "A"},
            include_op=True,
            floor=6,
            forced_epithets=["Medium Pair"],
            preferred_distances=["Medium"],
            distance_preference_mode="balanced",
            weights={"fanWeight": 0.0, "epithetValue": 5, "trainBias": 0.01},
        )
        names = {row["name"] for row in plan["schedule"]}
        self.assertIn("Medium Starter", names)
        self.assertIn("Medium Crown", names)
        self.assertIn("Medium Pair", plan["projected_epithets"])

    def test_dependency_epithet_uses_beam_fallback_and_projects_completion(self):
        plan = trackblazer.make_schedule(
            self.root,
            solver="smart",
            aptitudes={"Mile": "A", "Medium": "A", "Long": "A", "Turf": "A"},
            include_op=True,
            floor=6,
            forced_epithets=["Dependency Combo"],
            weights={"fanWeight": 0.0, "epithetValue": 5, "trainBias": 0.01},
        )
        names = {row["name"] for row in plan["schedule"]}
        self.assertIn("Dependency Race", names)
        self.assertIn("Dependency Combo", plan["projected_epithets"])
        self.assertIn(plan["solver"], {"smart-race-solver-beam", "smart-race-solver-beam-fallback"})


if __name__ == "__main__":
    unittest.main()
