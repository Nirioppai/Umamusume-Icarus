import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from career_bot import trackblazer
from career_bot.presets import PresetStore, hydrate_preset


class SweepyModV57AuditCompletionTests(unittest.TestCase):
    def setUp(self):
        self.base = Path(__file__).resolve().parents[1]
        self.good_aptitudes = {"Sprint": "A", "Mile": "A", "Medium": "A", "Long": "A", "Turf": "A", "Dirt": "A"}

    def test_summer_racing_disabled_blocks_summer_turns_in_beam(self):
        plan = trackblazer.make_schedule(
            self.base,
            aptitudes=self.good_aptitudes,
            solver="beam",
            include_op=False,
            floor=5,
            weights={"allowSummerRacing": False, "fanWeight": 0.002},
        )
        self.assertTrue(plan["success"])
        summer_turns = {37, 38, 39, 40, 61, 62, 63, 64}
        self.assertFalse(any(int(row.get("turn") or 0) in summer_turns for row in plan.get("schedule") or []))

    def test_target_epithet_marks_matching_race_without_hard_completion_requirement(self):
        plan = trackblazer.make_schedule(
            self.base,
            aptitudes=self.good_aptitudes,
            solver="beam",
            include_op=False,
            floor=5,
            target_epithets=["Dirt G1 Dominator"],
            weights={"fanWeight": 0.001},
        )
        self.assertTrue(plan["success"])
        target_hit_rows = [row for row in plan.get("schedule") or [] if "Dirt G1 Dominator" in (row.get("target_epithet_hits") or [])]
        self.assertTrue(target_hit_rows)

    def test_forced_epithet_reports_infeasible_when_filters_remove_matches(self):
        bad_aptitudes = {"Sprint": "S", "Mile": "S", "Medium": "S", "Long": "S", "Turf": "S", "Dirt": "G"}
        with self.assertRaises(RuntimeError):
            trackblazer.make_schedule(
                self.base,
                aptitudes=bad_aptitudes,
                solver="beam",
                include_op=False,
                floor=8,
                forced_epithets=["Dirt G1 Dominator"],
            )

    def test_solver_defaults_can_load_from_checked_in_json(self):
        defaults = trackblazer.solver_defaults(self.base)
        self.assertEqual(defaults["raceValue"], 1.0)
        self.assertGreaterEqual(defaults["forcedEpithetValue"], 100)

    def test_partial_trackblazer_cache_is_repaired(self):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            cache = root / "data" / "trackblazer"
            cache.mkdir(parents=True)
            (cache / "races.json").write_text("[]", encoding="utf-8")

            def fake_download(base_dir, force=False, timeout=20):
                out = Path(base_dir) / "data" / "trackblazer"
                out.mkdir(parents=True, exist_ok=True)
                for name in trackblazer.DATASETS:
                    (out / f"{name}.json").write_text("[]", encoding="utf-8")
                return {"success": True}

            with patch.object(trackblazer, "download_scheduler_data", side_effect=fake_download):
                data = trackblazer.load_or_download(root)
            self.assertIn("races", data)
            self.assertIn("epithets", data)
            self.assertIn("debut_races", data)

    def test_preset_preserves_per_trainee_manual_aptitudes_and_no_list_aliasing(self):
        with tempfile.TemporaryDirectory() as td:
            store = PresetStore(td)
            preset = {
                "name": "aptitudes",
                "trackblazer_manual_aptitudes_by_trainee": {
                    "1|Taiki Shuttle": {"Mile": "S"},
                    "2|Vodka": {"Mile": "A"},
                },
            }
            store.write(preset)
            loaded = store.read_one("aptitudes")
            self.assertEqual(loaded["trackblazer_manual_aptitudes_by_trainee"]["1|Taiki Shuttle"]["Mile"], "S")

        hydrated = hydrate_preset({"name": "alias check"})
        hydrated["extra_weight"][0][0] = 99
        hydrated["spirit_explosion"][0][0] = 99
        self.assertNotEqual(hydrated["extra_weight"][1][0], 99)
        self.assertNotEqual(hydrated["spirit_explosion"][1][0], 99)


if __name__ == "__main__":
    unittest.main()
