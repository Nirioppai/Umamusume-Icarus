import json
import os
import tempfile
import unittest
import zipfile
from pathlib import Path

from career_bot import ai_dataset


DEFAULT_PRESET = {
    "active": "Default",
    "presets": [
        {
            "name": "Default",
            "scenario_id": 4,
            "training_stat_priority": ["speed", "power", "wit", "stamina", "guts"],
            "event_choice_stat_priority": ["speed", "power", "wit", "stamina", "guts"],
            "summer_stat_priority": ["speed", "power", "wit", "stamina", "guts"],
            "running_style": 2,
            "race_strategy_by_distance": {},
            "preferred_distances": [],
            "preferred_surfaces": [],
            "event_overrides": {},
            "mant_config": {},
            "selection": {},
        }
    ],
}


class SweepyModV538AiImportPresetsTests(unittest.TestCase):
    def setUp(self):
        self.root = Path(tempfile.mkdtemp())
        self.base = self.root / "current"
        (self.base / "data").mkdir(parents=True)
        (self.base / "data" / "settings_presets.json").write_text(json.dumps(DEFAULT_PRESET), encoding="utf-8")
        self.runtime = self.root / "runtime"
        os.environ["UMA_RUNTIME_DIR"] = str(self.runtime)
        self.source = self.root / "old_build"
        (self.source / "data").mkdir(parents=True)
        (self.source / "data" / "settings_presets.json").write_text(
            json.dumps(
                {
                    "active": "Oguri Imported Source",
                    "presets": [
                        {
                            "name": "Oguri Imported Source",
                            "scenario_id": 4,
                            "training_stat_priority": ["power", "speed", "wit", "stamina", "guts"],
                            "event_choice_stat_priority": ["power", "speed", "wit", "stamina", "guts"],
                            "summer_stat_priority": ["wit", "speed", "power", "stamina", "guts"],
                            "running_style": 2,
                            "preferred_distances": ["medium", "long"],
                            "preferred_surfaces": ["turf"],
                            "mant_config": {"maximum_failure_chance": 20},
                            "selection": {"deck_id": 9, "trainee_id": 100101},
                        }
                    ],
                }
            ),
            encoding="utf-8",
        )

    def tearDown(self):
        os.environ.pop("UMA_RUNTIME_DIR", None)

    def _presets(self):
        return json.loads((self.base / "data" / "settings_presets.json").read_text(encoding="utf-8"))

    def test_import_previous_build_imports_settings_presets(self):
        result = ai_dataset.import_previous_logs(self.base, str(self.source), rebuild=False)
        self.assertTrue(result["success"])
        self.assertEqual(result["presets"]["imported_presets"], 1)
        payload = self._presets()
        names = {row["name"] for row in payload["presets"]}
        self.assertIn("Oguri Imported Source", names)
        self.assertEqual(payload["active"], "Oguri Imported Source")

    def test_import_same_preset_twice_deduplicates(self):
        first = ai_dataset.import_previous_logs(self.base, str(self.source), rebuild=False)
        second = ai_dataset.import_previous_logs(self.base, str(self.source), rebuild=False)
        self.assertEqual(first["presets"]["imported_presets"], 1)
        self.assertEqual(second["presets"]["imported_presets"], 0)
        self.assertGreaterEqual(second["duplicates"], 1)

    def test_same_name_different_content_gets_imported_suffix(self):
        ai_dataset.import_previous_logs(self.base, str(self.source), rebuild=False)
        # Change imported source content without changing the preset name.
        (self.source / "data" / "settings_presets.json").write_text(
            json.dumps({"active": "Oguri Imported Source", "presets": [{"name": "Oguri Imported Source", "running_style": 3, "selection": {"deck_id": 10}}]}),
            encoding="utf-8",
        )
        result = ai_dataset.import_previous_logs(self.base, str(self.source), rebuild=False)
        self.assertEqual(result["presets"]["imported_presets"], 1)
        names = {row["name"] for row in self._presets()["presets"]}
        self.assertIn("Oguri Imported Source Imported", names)

    def test_zip_import_imports_presets(self):
        zpath = self.root / "old_build.zip"
        with zipfile.ZipFile(zpath, "w") as zf:
            zf.write(self.source / "data" / "settings_presets.json", "SweepyModv5.33/data/settings_presets.json")
        result = ai_dataset.import_previous_logs(self.base, str(zpath), rebuild=False)
        self.assertEqual(result["presets"]["imported_presets"], 1)

    def test_ui_copy_mentions_presets(self):
        html = Path("public/index.html").read_text(encoding="utf-8")
        js = Path("public/app.js").read_text(encoding="utf-8")
        self.assertIn("Import Previous Logs & Presets", html)
        self.assertIn("IMPORT DATA", html)
        self.assertIn("import_presets", js)


if __name__ == "__main__":
    unittest.main()
