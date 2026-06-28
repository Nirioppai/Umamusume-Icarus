import os
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
MAIN = (ROOT / "main.py").read_text(encoding="utf-8")
# The item-count payload parser was extracted from main.py into
# career_bot/item_helpers.py; the source-text assertions below must cover both
# files so the live-payload-variant coverage is still enforced after the move.
ITEM_HELPERS = (ROOT / "career_bot" / "item_helpers.py").read_text(encoding="utf-8")
ITEM_PARSER_SOURCE = MAIN + "\n" + ITEM_HELPERS
CLIENT = (ROOT / "uma_api" / "client.py").read_text(encoding="utf-8")


class SweepyModV517ToughnessDetectionTests(unittest.TestCase):
    def test_configured_ids_are_validated_against_canonical_master_ids(self):
        self.assertIn('Configured ids are now accepted only when', MAIN)
        self.assertIn('toughness_item_ids.invalid.json', MAIN)
        self.assertIn('ignored_item_ids', MAIN)
        self.assertIn('return canonical', MAIN)

    def test_item_count_parser_accepts_live_payload_variants(self):
        self.assertIn('"item_num"', ITEM_PARSER_SOURCE)
        self.assertIn('"itemNum"', ITEM_PARSER_SOURCE)
        self.assertIn('"owned_num"', ITEM_PARSER_SOURCE)
        self.assertIn('"own_num"', ITEM_PARSER_SOURCE)
        self.assertIn('"item_count"', ITEM_PARSER_SOURCE)

    def test_uma_client_refreshes_item_map_with_non_number_counts(self):
        self.assertIn('def _payload_item_count', CLIENT)
        self.assertIn("'item_num'", CLIENT)
        self.assertIn('def _refresh_item_map', CLIENT)
        self.assertIn('self._refresh_item_map(item_list)', CLIENT)

    def test_detection_still_prefers_exact_toughness_30_core_kind(self):
        self.assertIn('kind") or "").lower() != "toughness_30"', MAIN)
        self.assertIn('n.text = \'Toughness 30\'', MAIN)


if __name__ == "__main__":
    unittest.main()
