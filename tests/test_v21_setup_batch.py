"""v2.1 Setup batch — backend pieces.

#5 race schedule: senior-year cells that recur from Classic under the same
   program_id were dropped by a global program_id dedup; /api/trackblazer/races
   now dedups per calendar occurrence (program_id + turn), so those cells appear.
#7 trainee versions: data/card_names_core.json maps card_id -> versioned name
   ("Air Shakur (unsigned)"); main.card_names_map drives the trainee picker name.
"""
import unittest


class SeniorRaceCellsTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        import main
        cls.races = main.api_trackblazer_races()["races"]

    def _senior_dates(self):
        out = {}
        for r in self.races:
            d = str(r.get("date") or "")
            if d.startswith("Senior Year"):
                out.setdefault(d.replace("Senior Year", "").strip(), []).append(r)
        return out

    def test_previously_dropped_senior_cells_now_present(self):
        sen = self._senior_dates()
        for cell in ("Early Sep", "Late Sep", "Early Oct", "Early Nov", "Early Dec"):
            self.assertTrue(sen.get(cell), f"Senior {cell} should have selectable races")

    def test_recurring_race_appears_in_both_years(self):
        # A race that recurs (same program_id in Classic + Senior) must now appear
        # in BOTH years' calendar (the dedup no longer collapses cross-year).
        by_pid = {}
        for r in self.races:
            by_pid.setdefault(r["id"], set()).add(str(r.get("date") or "").split(" ")[0])
        recurring = [pid for pid, yrs in by_pid.items() if len(yrs) > 1]
        self.assertTrue(recurring, "expected at least one race recurring across years")


class VersionedCardNamesTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        import main
        cls.main = main

    def test_card_names_map_loaded(self):
        self.assertGreater(len(self.main.card_names_map), 50)

    def test_air_shakur_version_name(self):
        self.assertEqual(self.main.card_names_map.get("103601"), "Air Shakur (unsigned)")

    def test_names_are_name_paren_version(self):
        # every entry is "Name (Version)" (reordered from the game's "[Version] Name")
        bad = [v for v in self.main.card_names_map.values() if not (v.endswith(")") and "(" in v)]
        self.assertEqual(bad, [], f"unexpected name format: {bad[:3]}")


if __name__ == "__main__":
    unittest.main()
