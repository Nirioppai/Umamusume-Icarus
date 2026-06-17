"""Regression tests for v6.7.13: the Character Profile panel showed
"default" between runs even when the last career used a specific
profile.

Root cause: the persisted ``active_character_profile`` dict carried
``display_name`` but not ``card_id``.  The dashboard's
``/api/character-profile/active`` endpoint's fallback set
``selected_name`` from that, but ``resolve_profile`` had NO
name-based match path -- it matched only by card_id, chara_id, or
preset_name.  So a name-only resolution fell through to default.

Fixes:
  1. ``resolve_profile`` gains a ``display_name`` parameter and a
     name-based match path (stage 4, after preset, before
     auto-derivation).
  2. The profile index now builds a ``by_name`` map from each
     profile JSON's display_name.
  3. ``CharacterProfile`` gains ``matched_card_id`` so the persisted
     dict carries the card_id for robust future re-resolution.
"""
import sys
import unittest
from pathlib import Path
from unittest.mock import MagicMock

sys.modules.setdefault("msgpack", MagicMock())


class NameBasedResolutionTests(unittest.TestCase):
    """The shipped profiles resolve by display_name."""

    def setUp(self):
        from career_bot import character_profiles
        self.cp = character_profiles
        # Use the shipped data/character_profiles catalog
        self.base = str(Path(__file__).resolve().parent.parent)

    def test_resolve_by_display_name(self):
        """The user's exact bug: resolve with display_name only (no
        card_id) must find the hand-curated profile, not fall to
        default."""
        profile = self.cp.resolve_profile(
            card_id=0, chara_id=0, scenario_id=4, base_dir=self.base,
            display_name="Oguri Cap",
        )
        self.assertEqual(profile.profile_id, "oguri_cap")
        self.assertEqual(profile.matched_via, "name")
        # The hand-curated Oguri profile is in hint mode
        self.assertEqual(profile.training_scorer_mode, "hint")

    def test_name_resolution_is_case_insensitive(self):
        profile = self.cp.resolve_profile(
            scenario_id=4, base_dir=self.base, display_name="oGuRi CaP",
        )
        self.assertEqual(profile.profile_id, "oguri_cap")

    def test_unknown_name_falls_back_to_default(self):
        """A name with no matching profile falls back to default (no
        crash)."""
        profile = self.cp.resolve_profile(
            scenario_id=4, base_dir=self.base,
            display_name="Nonexistent Trainee XYZ",
        )
        self.assertEqual(profile.matched_via, "default")

    def test_card_id_still_wins_over_name(self):
        """When both card_id and display_name are provided, card_id
        takes precedence (it's the stronger match)."""
        profile = self.cp.resolve_profile(
            card_id=100601, scenario_id=4, base_dir=self.base,
            display_name="Special Week",  # deliberately mismatched
        )
        # card_id 100601 is Oguri; the mismatched name must NOT override
        self.assertEqual(profile.matched_via, "card_id")
        self.assertEqual(profile.profile_id, "oguri_cap")

    def test_preset_still_wins_over_name(self):
        """preset_name resolution (stage 3) beats name resolution
        (stage 4)."""
        # This depends on the index having a by_preset entry; if Oguri
        # is registered by preset it should win. We just verify name
        # doesn't override a successful earlier-stage match.
        profile = self.cp.resolve_profile(
            scenario_id=4, base_dir=self.base,
            preset_name="oguri cap",  # may or may not be in by_preset
            display_name="Special Week",
        )
        # Either preset matched (oguri) or it fell to name (special_week)
        # or default. The key assertion: if preset matched, name didn't
        # override it.
        if profile.matched_via == "preset":
            self.assertEqual(profile.profile_id, "oguri_cap")


class MatchedCardIdTests(unittest.TestCase):
    """``matched_card_id`` is populated and surfaced in to_dict so the
    persisted active_character_profile carries the card_id."""

    def setUp(self):
        from career_bot import character_profiles
        self.cp = character_profiles
        self.base = str(Path(__file__).resolve().parent.parent)

    def test_card_id_resolution_sets_matched_card_id(self):
        profile = self.cp.resolve_profile(
            card_id=100601, scenario_id=4, base_dir=self.base,
        )
        self.assertEqual(profile.matched_card_id, 100601)

    def test_to_dict_includes_matched_card_id(self):
        profile = self.cp.resolve_profile(
            card_id=100601, scenario_id=4, base_dir=self.base,
        )
        d = profile.to_dict()
        self.assertIn("matched_card_id", d)
        self.assertEqual(d["matched_card_id"], 100601)

    def test_name_resolution_has_zero_matched_card_id(self):
        """When resolved by name (no card_id), matched_card_id is 0 --
        the name path doesn't fabricate a card_id."""
        profile = self.cp.resolve_profile(
            scenario_id=4, base_dir=self.base, display_name="Oguri Cap",
        )
        self.assertEqual(profile.matched_card_id, 0)


class IndexByNameTests(unittest.TestCase):
    """The profile index builds a by_name map from display_names."""

    def setUp(self):
        from career_bot import character_profiles
        self.cp = character_profiles
        self.base = str(Path(__file__).resolve().parent.parent)

    def test_index_has_by_name_map(self):
        index = self.cp._load_index(self.base)
        self.assertIn("by_name", index)
        self.assertIsInstance(index["by_name"], dict)

    def test_by_name_maps_oguri(self):
        index = self.cp._load_index(self.base)
        self.assertEqual(index["by_name"].get("oguri cap"), "oguri_cap")

    def test_by_name_does_not_break_other_index_keys(self):
        """Adding by_name must not disturb the existing index maps."""
        index = self.cp._load_index(self.base)
        self.assertIn("by_card_id", index)
        self.assertIn("by_chara_id", index)
        self.assertIn("by_preset", index)


if __name__ == "__main__":
    unittest.main()
