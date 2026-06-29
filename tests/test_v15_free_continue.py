"""Free-continue counter must read the LIVE remaining free-continue balance.

CORRECTED 2026-06-28 (clock-retry investigation). The earlier v1.5 belief was
backwards: it read ``max(available_free_continue_num, free_continue_num)`` on the
theory that ``available_free_continue_num`` (AFCN) was unreliably 0. Forensics over
227 real retry events proved the opposite -- AFCN is the live grantable balance:
every single ``2507`` ("no free continue") happened at AFCN==0 (213/213), and every
successful free continue happened at AFCN>=1. ``free_continue_num`` is a CONSTANT
daily cap (pinned at 3, never decrements), so ``max(...)`` always reported 3,
forced ``continue_type=1`` (free) forever, and the bot never fell back to spending
a standard clock (``continue_type=2``). The counter must surface AFCN only.
"""
import threading
import sys
import unittest
from unittest.mock import MagicMock

for _m in ("msgpack",):
    sys.modules.setdefault(_m, MagicMock())

from career_bot.runner import CareerRunner


def _runner():
    r = CareerRunner.__new__(CareerRunner)
    r.lock = threading.RLock()
    return r


class FreeContinueCountTests(unittest.TestCase):
    def test_empty_pool_reads_zero_despite_constant_cap(self):
        # AFCN=0 with the constant cap at 3 must report 0 (was the core bug: it
        # reported 3, so the bot kept sending free continues that 2507'd).
        r = _runner()
        home = {"available_continue_num": 5, "available_free_continue_num": 0,
                "free_continue_num": 3, "free_continue_time": 123}
        self.assertEqual(r._free_continue_count(home), 0)

    def test_reads_live_balance_not_the_cap(self):
        r = _runner()
        self.assertEqual(r._free_continue_count(
            {"available_free_continue_num": 2, "free_continue_num": 3}), 2)
        self.assertEqual(r._free_continue_count(
            {"available_free_continue_num": 1, "free_continue_num": 4}), 1)
        self.assertEqual(r._free_continue_count(
            {"available_free_continue_num": 3, "free_continue_num": 3}), 3)

    def test_zero_when_missing(self):
        r = _runner()
        self.assertEqual(r._free_continue_count({}), 0)
        self.assertEqual(r._free_continue_count(None), 0)


if __name__ == "__main__":
    unittest.main()
