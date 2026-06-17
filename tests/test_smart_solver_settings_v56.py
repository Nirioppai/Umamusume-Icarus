import tempfile
import unittest
from pathlib import Path

from career_bot import trackblazer
from career_bot.presets import PresetStore


class SmartSolverSettingsV56Tests(unittest.TestCase):
    def test_presets_preserve_solver_settings(self):
        with tempfile.TemporaryDirectory() as td:
            store = PresetStore(td)
            preset = {
                "name": "solver settings",
                "trackblazer_solver_settings": {"include_op": True, "min_aptitude_floor": "C"},
                "trackblazer_manual_aptitudes": {"Mile": "S"},
                "trackblazer_weights": {"fanWeight": 0.001, "epithetValue": 3},
                "trackblazer_target_epithets": ["Mile a Minute"],
                "trackblazer_forced_epithets": ["Dirt G1 Dominator"],
            }
            store.write(preset)
            loaded = store.read_one("solver settings")
            self.assertEqual(loaded["trackblazer_solver_settings"]["min_aptitude_floor"], "C")
            self.assertEqual(loaded["trackblazer_manual_aptitudes"]["Mile"], "S")
            self.assertEqual(loaded["trackblazer_weights"]["epithetValue"], 3)
            self.assertEqual(loaded["trackblazer_target_epithets"], ["Mile a Minute"])
            self.assertEqual(loaded["trackblazer_forced_epithets"], ["Dirt G1 Dominator"])

    def test_target_epithet_bias_marks_matching_races(self):
        base = Path(__file__).resolve().parents[1]
        rows = trackblazer._candidate_rows(
            base,
            aptitudes={"Sprint": "A", "Mile": "A", "Medium": "A", "Long": "A", "Turf": "A", "Dirt": "A"},
            include_op=False,
            floor=5,
        )
        annotated = trackblazer._annotate_epithet_hits(base, rows, target_epithets=["Dirt G1 Dominator"])
        hits = [row for row in annotated if row.get("target_epithet_hits")]
        self.assertTrue(hits)
        self.assertTrue(all(str(row.get("surface")).lower() == "dirt" for row in hits[:5]))

    def test_schedule_accepts_target_epithets(self):
        base = Path(__file__).resolve().parents[1]
        plan = trackblazer.make_schedule(
            base,
            aptitudes={"Sprint": "A", "Mile": "A", "Medium": "A", "Long": "A", "Turf": "A", "Dirt": "A"},
            solver="beam",
            include_op=False,
            floor=5,
            target_epithets=["Dirt G1 Dominator"],
            weights={"epithetValue": 5, "fanWeight": 0.001},
        )
        self.assertTrue(plan["success"])
        self.assertIn("schedule", plan)


if __name__ == "__main__":
    unittest.main()
