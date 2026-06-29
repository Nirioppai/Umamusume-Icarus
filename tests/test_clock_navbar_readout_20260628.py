"""Free-continue navbar readout (2026-06-28).

_update_clocks_left must expose the free/standard clock breakdown + the
free_continue_time refresh epoch on the runner status so the v3 navbar can show
a "free clocks (+ refresh estimate)" readout. (free_continue_count itself now
reads the live available_free_continue_num — see test_v15_free_continue.)
"""
import sys
import threading
import unittest
from unittest.mock import MagicMock

for _m in ("msgpack",):
    sys.modules.setdefault(_m, MagicMock())

from career_bot.runner import CareerRunner


def _runner():
    r = CareerRunner.__new__(CareerRunner)
    r.lock = threading.RLock()
    r.status = {}
    return r


class ClockReadoutTests(unittest.TestCase):
    def test_breakdown_and_refresh_stored(self):
        r = _runner()
        state = {"data": {"home_info": {
            "available_continue_num": 5,
            "available_free_continue_num": 2,
            "free_continue_num": 3,           # constant cap — must be ignored for the live free count
            "free_continue_time": 1782667759,
        }}}
        r._update_clocks_left(state)
        self.assertEqual(r.status["standard_clocks"], 5)
        self.assertEqual(r.status["free_clocks"], 2)            # live AFCN, not the cap
        self.assertEqual(r.status["free_continue_time"], 1782667759)
        self.assertEqual(r.status["clocks_left"], 7)           # std + free

    def test_empty_free_pool(self):
        r = _runner()
        state = {"data": {"home_info": {
            "available_continue_num": 5, "available_free_continue_num": 0,
            "free_continue_num": 3, "free_continue_time": 1782667759,
        }}}
        r._update_clocks_left(state)
        self.assertEqual(r.status["free_clocks"], 0)
        self.assertEqual(r.status["standard_clocks"], 5)

    def test_no_home_info_is_noop(self):
        r = _runner()
        r._update_clocks_left({"data": {}})
        self.assertNotIn("free_clocks", r.status)


if __name__ == "__main__":
    unittest.main()
