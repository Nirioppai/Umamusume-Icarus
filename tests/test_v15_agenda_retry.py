"""v1.5: debut-only free retries.

- Debut-only free retries: _is_debut_race detects the Make Debut / Maiden race
  by name so free continues can be reserved for it.

NOTE: The "in-game agenda" feature (use_ingame_agenda / reading
chara_info.reserve_race_program_id to override the solver's race choice) was
removed from the codebase. The corresponding InGameAgendaTests were dropped
because RacePlanner.choose no longer honors a reserved race -- the smart solver
owns extra-race decisions. The debut-race detection tests below remain live.
"""
import tempfile
import unittest
from pathlib import Path

from career_bot.races import RacePlanner
from career_bot.runner import CareerRunner


def _planner():
    tmp = Path(tempfile.mkdtemp())
    (tmp / "data").mkdir()
    p = RacePlanner(tmp)
    p.program = {
        100: {"name": "Make Debut", "grade": "Pre-OP", "distance": 1600, "ground": 1, "fans": 1000},
        200: {"name": "Tokyo Cup G1", "grade": "G1", "distance": 1600, "ground": 1, "fans": 20000},
        300: {"name": "Mile Trophy", "grade": "G2", "distance": 1600, "ground": 1, "fans": 15000},
    }
    p._replan_smart_schedule = lambda *a, **k: None
    return p


class DebutRaceDetectionTests(unittest.TestCase):
    def _runner(self):
        r = CareerRunner.__new__(CareerRunner)
        r.race_planner = _planner()
        return r

    def test_detects_make_debut(self):
        self.assertTrue(self._runner()._is_debut_race(100))

    def test_non_debut_race_is_false(self):
        r = self._runner()
        self.assertFalse(r._is_debut_race(200))
        self.assertFalse(r._is_debut_race(300))

    def test_missing_program_safe(self):
        self.assertFalse(self._runner()._is_debut_race(0))


if __name__ == "__main__":
    unittest.main()
