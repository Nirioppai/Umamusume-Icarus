"""v2.1 v3 UI: per-trainee theme colours.

The dashboard recolours its accent to the active trainee's `ui_colors`
(from data/trainee_profiles_core.json). The frontend fetches the palette
once from GET /api/character-profile/colors, which maps card_id -> the
{main, sub, border} hex triple (NOT deduped by name, so the active card
resolves to its own colours).
"""
import re
import unittest


HEX6 = re.compile(r"^[0-9a-fA-F]{6}$")


class TraineeColorsEndpointTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        import main
        cls.main = main
        cls.resp = main.api_character_profile_colors()

    def test_success_envelope(self):
        self.assertTrue(self.resp.get("success"))
        self.assertIsInstance(self.resp.get("colors"), dict)

    def test_non_empty(self):
        # the data file ships 289 cards; every card with a main colour appears.
        self.assertGreater(len(self.resp["colors"]), 50)

    def test_keys_are_card_id_strings(self):
        for k in self.resp["colors"]:
            self.assertIsInstance(k, str)
            self.assertTrue(k.isdigit(), f"key {k!r} is not a card_id string")

    def test_each_entry_has_clean_hex_triple(self):
        for cid, c in self.resp["colors"].items():
            for field in ("main", "sub", "border"):
                self.assertIn(field, c, f"{cid} missing {field}")
                self.assertFalse(c[field].startswith("#"), f"{cid}.{field} keeps the # prefix")
                self.assertTrue(HEX6.match(c[field]), f"{cid}.{field}={c[field]!r} not 6-hex")

    def test_known_card_resolves(self):
        # Admire Vega (card_id 103301) -> main 3865A1 (from the data file).
        c = self.resp["colors"].get("103301")
        self.assertIsNotNone(c)
        self.assertEqual(c["main"].lower(), "3865a1")


if __name__ == "__main__":
    unittest.main()
