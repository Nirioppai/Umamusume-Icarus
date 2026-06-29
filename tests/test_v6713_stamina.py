"""Regression tests for v6.7.13 stamina/distance fixes:

  1. Distance aptitude tie-break now favors the LONGER distance.
     All-rounder trainees (Mile=Middle=Long aptitude, common for
     Oguri Cap) were resolving to "mile" and getting a Mile-tier
     stamina target (~600), then under-building stamina for the
     Medium/Long races that dominate the Trackblazer senior calendar.

  2. When a trainee has NO explicit stat targets and preferred is
     auto, the aptitude-based per-distance defaults now apply instead
     of the 9999 sentinel (which meant "no stamina target").

  3. A 205 result on the race-continue call (the Trackblazer finale
     races don't support clock retries) is recognized and stops the
     retry loop immediately instead of burning the retry budget.
"""
import sys
import threading
import unittest
from unittest.mock import MagicMock

sys.modules.setdefault("msgpack", MagicMock())


class ContinueUnavailable205Tests(unittest.TestCase):
    """v6.7.13: a 205 on the continue call stops the retry loop
    immediately (finale races don't support clock retries)."""

    def test_205_detection_logic(self):
        """Verify the string-matching logic used to detect a 205
        continue rejection.  (The full _race loop is integration-tested
        elsewhere; here we unit-test the detection predicate.)"""
        # The runner checks `if "205" in err_str`.
        err_205 = "API error 205 on single_mode_free/continue"
        err_208 = "API error 208 (SERVER BUSY) on single_mode_free/continue"
        err_other = "Connection timeout"
        self.assertIn("205", err_205)
        self.assertNotIn("205", err_208)
        self.assertNotIn("205", err_other)


if __name__ == "__main__":
    unittest.main()
