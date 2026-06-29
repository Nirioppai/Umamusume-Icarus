"""v1.5 Phase 3 — fans + race count.

  * glow sticks now fire on G2/G3 (not G1-only) above the effective-fan floor;
  * the irregular-training heuristic no longer hijacks a race the smart solver
    explicitly planned for this turn (android's "if a race is planned, run it").
"""
import unittest

from career_bot.items import MantItemManager


class GlowStickGradeTests(unittest.TestCase):
    def setUp(self):
        self.m = MantItemManager.__new__(MantItemManager)
        self.owned = {"Glow Sticks": 2}
        self.cfg = {"glow_stick_fan_multiplier": 2.0,
                    "trackblazer_glow_stick_min_fans": 20000,
                    "trackblazer_glow_stick_final_reserve": 1}

    def test_big_g2_now_fires(self):
        # 13k base -> 26k effective >= 20k. Was blocked by the G1-only gate.
        self.assertTrue(self.m._should_use_glow_stick(self.owned, 42, "G2", 13000, self.cfg))

    def test_big_g3_now_fires(self):
        self.assertTrue(self.m._should_use_glow_stick(self.owned, 42, "G3", 11000, self.cfg))

    def test_small_g2_still_skipped(self):
        # 5k base -> 10k effective < 20k floor.
        self.assertFalse(self.m._should_use_glow_stick(self.owned, 42, "G2", 5000, self.cfg))

    def test_op_never_fires(self):
        self.assertFalse(self.m._should_use_glow_stick(self.owned, 42, "OP", 30000, self.cfg))


if __name__ == "__main__":
    unittest.main()
