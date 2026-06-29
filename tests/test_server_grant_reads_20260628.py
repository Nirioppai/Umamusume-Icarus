"""Three read-only server-data wins (2026-06-28) — fields the bot already receives
but ignored:

F3 cap-aware training  — _live_stat_cap reads the LIVE per-stat ceiling
   (chara_info.max_speed/.../max_wiz) so training stops at the real cap, not a
   hardcoded 1200. Identical when the live cap == 1200.
F2 server-driven short race — _race_short_mode reads home_info.shortened_race_state
   to choose is_short instead of hardcoding 1; default stays 1 (the working value).
F1 route-race awareness — _route_info reads chara_info.route_id + route_race_id_array
   for finale/soft-lock context.
"""
import sys
import unittest
from unittest.mock import MagicMock

for _m in ("msgpack",):
    sys.modules.setdefault(_m, MagicMock())

from career_bot.scenarios.mant_trackblazer import MantTrackblazerCore, STAT_CAP
from career_bot.runner import CareerRunner


class LiveStatCapTests(unittest.TestCase):
    def _eng(self):
        return MantTrackblazerCore.__new__(MantTrackblazerCore)

    def test_reads_live_ceiling(self):
        e = self._eng()
        chara = {"max_speed": 1100, "max_stamina": 1400, "max_wiz": 1200}
        self.assertEqual(e._live_stat_cap(chara, 0), 1100)   # speed (lowered)
        self.assertEqual(e._live_stat_cap(chara, 1), 1400)   # stamina (raised by effects)
        self.assertEqual(e._live_stat_cap(chara, 4), 1200)   # wiz

    def test_missing_falls_back_to_static(self):
        e = self._eng()
        self.assertEqual(e._live_stat_cap({}, 0), STAT_CAP)
        self.assertEqual(e._live_stat_cap({"max_speed": 0}, 0), STAT_CAP)
        self.assertEqual(e._live_stat_cap(None, 2), STAT_CAP)


class RaceShortModeTests(unittest.TestCase):
    def _r(self):
        return CareerRunner.__new__(CareerRunner)

    def test_skip_when_unlocked(self):
        s, f = self._r()._race_short_mode({"data": {
            "home_info": {"shortened_race_state": 4, "race_entry_restriction": 1},
            "chara_info": {"is_short_race": 0}}})
        self.assertEqual(s, 1)
        self.assertEqual(f["shortened_race_state"], 4)
        self.assertEqual(f["race_entry_restriction"], 1)

    def test_full_race_when_skip_locked(self):
        s, _ = self._r()._race_short_mode({"data": {"home_info": {"shortened_race_state": 0}, "chara_info": {}}})
        self.assertEqual(s, 0)

    def test_default_skip_when_flag_absent(self):
        # No flag -> keep the working default (skip), never regress.
        self.assertEqual(self._r()._race_short_mode({"data": {"home_info": {}, "chara_info": {}}})[0], 1)
        self.assertEqual(self._r()._race_short_mode({})[0], 1)


class RouteInfoTests(unittest.TestCase):
    def _r(self):
        return CareerRunner.__new__(CareerRunner)

    def test_parses_route(self):
        info = self._r()._route_info({"route_id": 10004, "route_race_id_array": [730, 40022, 40023]})
        self.assertEqual(info["route_id"], 10004)
        self.assertEqual(info["route_race_ids"], [730, 40022, 40023])
        self.assertEqual(info["route_race_count"], 3)

    def test_empty(self):
        self.assertEqual(self._r()._route_info({}),
                         {"route_id": 0, "route_race_ids": [], "route_race_count": 0})
        self.assertEqual(self._r()._route_info(None)["route_race_count"], 0)


if __name__ == "__main__":
    unittest.main()
