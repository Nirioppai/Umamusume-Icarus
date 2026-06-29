"""Bug #1 follow-up: per-year-independent manual race selection via occurrence_id.

The v3 race picker now keys selections by race occurrence_id (year_key*100000 +
program_id) instead of bare program_id, so picking a recurring race in the Senior
cell does NOT also select its Classic counterpart. This works because the engine's
RacePlanner.wanted_programs turn-scopes occurrence ids via meta[occ].turn, while
bare program_ids stay turn-blind (backward compatible with old presets).

Grounded on real data: Arima Kinen pid 81 -> occ 200081 (turn 48, Classic) and
300081 (turn 72, Senior).
"""
import os
import unittest

from career_bot.races import RacePlanner

DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


class TestOccurrenceTurnScoping(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.rp = RacePlanner(DIR)

    def _wanted(self, race_list, turn):
        return self.rp.wanted_programs({"extra_race_list": race_list}, turn=turn)

    def test_data_loaded(self):
        # meta must carry the two Arima occurrences (else the data regenerated wrong).
        self.assertIn(200081, self.rp.meta)
        self.assertIn(300081, self.rp.meta)

    def test_classic_occurrence_only_fires_classic_turn(self):
        self.assertIn(81, self._wanted([200081], 48))   # Classic Arima at its turn
        self.assertNotIn(81, self._wanted([200081], 72)) # NOT at the Senior turn

    def test_senior_occurrence_only_fires_senior_turn(self):
        self.assertIn(81, self._wanted([300081], 72))   # Senior Arima at its turn
        self.assertNotIn(81, self._wanted([300081], 48)) # NOT at the Classic turn

    def test_two_occurrences_are_independent(self):
        # Selecting ONLY the Senior occurrence must not pull in the Classic one.
        self.assertEqual(self._wanted([300081], 48), [])
        self.assertIn(81, self._wanted([300081], 72))

    def test_bare_program_id_stays_turn_blind(self):
        # Old presets store bare program_ids -> raced whenever offered (both years).
        self.assertIn(81, self._wanted([81], 48))
        self.assertIn(81, self._wanted([81], 72))


if __name__ == "__main__":
    unittest.main()
