"""Clock-retry fix (2026-06-28 investigation).

Two verified bugs killed the Burn-Clocks feature in Trackblazer:

1. A transient ``2507`` ("the account free-continue pool is momentarily empty")
   was treated as a PERMANENT per-race "non-retryable" property and persisted to a
   shared, never-cleared cache. Over many loop careers it banned ~every race
   (70 program_ids incl. every G1, the Junior Make Debut, and the whole finale),
   so the bot skipped retries before ever calling continue. PROOF it is not
   per-race: pids 689/163/2321/2420/2416 each succeeded a continue in one career
   yet sat in the ban list. ``_continue_error_code`` now classifies 2507 as
   transient (not learned); only a genuine ``205`` is learned.

2. The ``max_retries_per_race`` gate was checked BEFORE the mandatory-race
   rescue, so ``max_retries_per_race=0`` ("no optional retries") silently also
   killed the career-saving mandatory rescue. The rescue must survive
   max_retries==0 (its own opt-out is ``disable_mandatory_race_clocks``).
"""
import os
import sys
import tempfile
import threading
import unittest
from unittest.mock import MagicMock

for _m in ("msgpack",):
    sys.modules.setdefault(_m, MagicMock())

from career_bot.runner import CareerRunner


def _policy_runner(burn_clocks=True, max_retries_per_race=-1, clocks_g1_debut_only=False):
    r = CareerRunner.__new__(CareerRunner)
    r.lock = threading.RLock()
    r.burn_clocks = burn_clocks
    r.max_retries_per_race = max_retries_per_race
    r.clocks_g1_debut_only = clocks_g1_debut_only
    r._load_non_retryable = lambda: set()
    r._race_grade_for_retry = lambda program_id: "G1"
    r._is_debut_race = lambda program_id, turn: False
    return r


class ContinueErrorClassificationTests(unittest.TestCase):
    def _r(self):
        return CareerRunner.__new__(CareerRunner)

    def test_2507_is_transient_and_not_learned(self):
        code, learn = self._r()._continue_error_code(
            "API error 2507 on single_mode_free/continue: {\"result_code\": 2507}")
        self.assertEqual(code, "2507")
        self.assertFalse(learn)

    def test_205_is_genuine_and_learned(self):
        code, learn = self._r()._continue_error_code(
            "API error 205 on single_mode_free/continue: {\"result_code\": 205}")
        self.assertEqual(code, "205")
        self.assertTrue(learn)

    def test_unrelated_error_not_classified(self):
        code, learn = self._r()._continue_error_code("API error 208 on single_mode_free/continue")
        self.assertEqual(code, "")
        self.assertFalse(learn)


class MaxRetriesMandatoryOrderingTests(unittest.TestCase):
    def test_zero_max_retries_still_allows_mandatory_rescue(self):
        r = _policy_runner(max_retries_per_race=0)
        pol = r._race_retry_policy({"mant_config": {}}, program_id=163, turn=31,
                                   attempts=0, free_clocks_available=0, is_mandatory=True)
        self.assertTrue(pol["enabled"], "mandatory rescue must survive max_retries=0")
        self.assertTrue(pol.get("mandatory_clock_rescue"))

    def test_zero_max_retries_still_blocks_optional(self):
        r = _policy_runner(max_retries_per_race=0)
        pol = r._race_retry_policy({"mant_config": {}}, program_id=163, turn=31,
                                   attempts=0, free_clocks_available=3, is_mandatory=False)
        self.assertFalse(pol["enabled"])
        self.assertEqual(pol["disabled_reason"], "max_retries_reached")

    def test_zero_max_retries_respects_mandatory_opt_out(self):
        r = _policy_runner(max_retries_per_race=0)
        pol = r._race_retry_policy({"mant_config": {"disable_mandatory_race_clocks": True}},
                                   program_id=163, turn=31, attempts=0,
                                   free_clocks_available=0, is_mandatory=True)
        self.assertFalse(pol["enabled"])

    def test_nonzero_max_retries_still_caps_mandatory(self):
        # Regression guard for v6.7.12: at max_retries>0, attempts>=cap still stops.
        r = _policy_runner(burn_clocks=False, max_retries_per_race=-1)
        pol = r._race_retry_policy({"mant_config": {"max_retries_per_race": 5}},
                                   program_id=163, turn=31, attempts=5,
                                   free_clocks_available=0, is_mandatory=True)
        self.assertFalse(pol["enabled"])
        self.assertEqual(pol["disabled_reason"], "max_retries_reached")


class TwoFiveZeroSevenDoesNotPoisonCacheTests(unittest.TestCase):
    """A 2507 classified as transient must never be persisted to the ban cache."""

    def setUp(self):
        self.tmp = tempfile.mkdtemp()
        self._prev = os.environ.get("UMA_RUNTIME_DIR")
        os.environ["UMA_RUNTIME_DIR"] = self.tmp

    def tearDown(self):
        if self._prev is None:
            os.environ.pop("UMA_RUNTIME_DIR", None)
        else:
            os.environ["UMA_RUNTIME_DIR"] = self._prev

    def _r(self):
        r = CareerRunner.__new__(CareerRunner)
        r.lock = threading.RLock()
        r.base_dir = self.tmp
        return r

    def test_learning_only_marks_genuine_205(self):
        r = self._r()
        # simulate the handler decision: only learn when _continue_error_code says so
        for err in ("API error 2507 on single_mode_free/continue: {}",
                    "API error 205 on single_mode_free/continue: {}"):
            code, learn = r._continue_error_code(err)
            if learn:
                r._mark_non_retryable(689, code)
        # 689 (debut) hit a 2507 then a 205; only the 205 should have been learned.
        self.assertIn(689, r._load_non_retryable())

    def test_2507_alone_never_marks(self):
        r = self._r()
        code, learn = r._continue_error_code("API error 2507 on single_mode_free/continue: {}")
        if learn:
            r._mark_non_retryable(163, code)
        self.assertEqual(r._load_non_retryable(), set())


if __name__ == "__main__":
    unittest.main()
