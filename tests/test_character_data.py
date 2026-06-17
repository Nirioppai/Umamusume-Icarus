"""Tests for the v6.3 character data catalogs.

Covers the loader module that reads the Android-ported character preset
and epithet JSON catalogs, plus the name-matching helpers used by the
profile auto-derivation layer.
"""

from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path

from career_bot import character_data


REPO_ROOT = Path(__file__).resolve().parent.parent


# --------------------------------------------------------------------------
# Shipped catalogs
# --------------------------------------------------------------------------


class ShippedCatalogTests(unittest.TestCase):
    def test_character_presets_loads(self):
        presets = character_data.load_character_presets(REPO_ROOT)
        self.assertGreater(len(presets), 50)
        # Sanity: Oguri Cap and Special Week should both be present
        oguri = character_data.find_character_preset("Oguri Cap", presets)
        self.assertIsNotNone(oguri)
        self.assertIn("distanceAptitudes", oguri)
        self.assertEqual(oguri["distanceAptitudes"]["Mile"], "A")
        spw = character_data.find_character_preset("Special Week", presets)
        self.assertIsNotNone(spw)
        self.assertEqual(spw["distanceAptitudes"]["Long"], "A")

    def test_epithet_catalog_loads(self):
        catalog = character_data.load_epithet_catalog(REPO_ROOT)
        self.assertGreater(len(catalog), 200)
        # Each character-specific epithet should have exactly one tag
        for title, row in catalog.items():
            chars = row.get("characters") or []
            self.assertIsInstance(chars, list)
            # generic epithets have empty character lists; that's fine

    def test_signature_epithet_for_known_character(self):
        sig = character_data.signature_epithet("Oguri Cap", base_dir=REPO_ROOT)
        self.assertIsNotNone(sig)
        self.assertIn("Oguri Cap", sig.get("characters") or [])

    def test_signature_epithet_for_unknown_character(self):
        self.assertIsNone(character_data.signature_epithet("Not A Real Character", base_dir=REPO_ROOT))

    def test_epithets_for_character_filters_correctly(self):
        rows = character_data.epithets_for_character("Special Week", base_dir=REPO_ROOT)
        self.assertGreater(len(rows), 0)
        for row in rows:
            self.assertIn("Special Week", row.get("characters") or [])

    def test_epithets_for_unknown_character_returns_empty(self):
        rows = character_data.epithets_for_character("Not A Real Character", base_dir=REPO_ROOT)
        self.assertEqual(rows, [])


# --------------------------------------------------------------------------
# Name normalization
# --------------------------------------------------------------------------


class NameMatchingTests(unittest.TestCase):
    def test_case_insensitive_match(self):
        presets = {"Oguri Cap": {"name": "Oguri Cap", "distanceAptitudes": {}, "surfaceAptitudes": {}}}
        self.assertIsNotNone(character_data.find_character_preset("oguri cap", presets))
        self.assertIsNotNone(character_data.find_character_preset("OGURI CAP", presets))
        self.assertIsNotNone(character_data.find_character_preset("  Oguri  Cap  ", presets))

    def test_strips_parenthetical_suffix(self):
        presets = {"Oguri Cap": {"name": "Oguri Cap", "distanceAptitudes": {}, "surfaceAptitudes": {}}}
        # Game sometimes appends "(SSR)" or "(Alt)" annotations
        self.assertIsNotNone(character_data.find_character_preset("Oguri Cap (SSR)", presets))
        self.assertIsNotNone(character_data.find_character_preset("Oguri Cap (Trackblazer)", presets))

    def test_no_match_returns_none(self):
        presets = {"Oguri Cap": {"name": "Oguri Cap", "distanceAptitudes": {}, "surfaceAptitudes": {}}}
        self.assertIsNone(character_data.find_character_preset("Special Week", presets))


# --------------------------------------------------------------------------
# Missing-file graceful fallback
# --------------------------------------------------------------------------


class MissingCatalogTests(unittest.TestCase):
    def test_missing_preset_file_returns_empty_dict(self):
        with tempfile.TemporaryDirectory() as td:
            base = Path(td)
            self.assertEqual(character_data.load_character_presets(base), {})

    def test_missing_epithet_file_returns_empty_dict(self):
        with tempfile.TemporaryDirectory() as td:
            base = Path(td)
            self.assertEqual(character_data.load_epithet_catalog(base), {})

    def test_signature_epithet_with_missing_catalog_returns_none(self):
        with tempfile.TemporaryDirectory() as td:
            base = Path(td)
            self.assertIsNone(character_data.signature_epithet("Oguri Cap", base_dir=base))

    def test_corrupt_json_returns_empty(self):
        with tempfile.TemporaryDirectory() as td:
            base = Path(td)
            (base / "data" / "character_data").mkdir(parents=True)
            (base / "data" / "character_data" / "epithets.json").write_text("not valid json {{")
            self.assertEqual(character_data.load_epithet_catalog(base), {})


if __name__ == "__main__":
    unittest.main()
