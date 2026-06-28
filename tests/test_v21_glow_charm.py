"""Bug batch 2026-06-28: Glow Stick fan-gate (#8) + Good-Luck Charm aggressiveness (#12).

#8: glow stick must NOT fire below the fan threshold mid-game (incl. the
    unknown-fan eff_fans==0 bypass), but MUST be dumped past the late/finale
    window (was held back forever by the reserve -> "not used after turn 72").
#12: charm must also fire on HIGH-failure turns even when the main-stat gain is
     modest (was gated out by the >=20 gain requirement -> "fails despite GLC").
"""
import unittest

from career_bot.items import MantItemManager
import career_bot.trackblazer_rules as tb_rules


def _mgr():
    return MantItemManager.__new__(MantItemManager)


CFG = {"trackblazer_glow_stick_min_fans": 20000}  # save_items_lategame defaults False


class TestGlowStick(unittest.TestCase):
    def setUp(self):
        self.m = _mgr()

    def gs(self, turn, fans, qty=3, grade="G1", cfg=None):
        owned = {"Glow Sticks": qty}
        return self.m._should_use_glow_stick(owned, turn, grade, fans, cfg or CFG)

    def test_grade_and_qty_gates(self):
        self.assertFalse(self.gs(50, 25000, grade="OP"))
        self.assertFalse(self.gs(50, 25000, qty=0))

    def test_midgame_below_threshold_known_fans(self):
        self.assertFalse(self.gs(50, 11000))          # 11k < 20k -> no

    def test_midgame_unknown_fans_does_not_fire(self):
        self.assertFalse(self.gs(50, 0))              # eff_fans==0 bypass closed

    def test_midgame_at_threshold_fires(self):
        self.assertTrue(self.gs(50, 25000))           # >= min, reserve ok (qty 3 > 1)

    def test_midgame_reserve_holds_last_one(self):
        self.assertFalse(self.gs(50, 25000, qty=1))   # qty 1 not > reserve 1

    def test_midgame_top_tier_floor_overrides_reserve(self):
        self.assertTrue(self.gs(50, 35000, qty=1))    # >= 30k floor -> use even last one

    def test_late_dump_uses_regardless(self):
        self.assertTrue(self.gs(73, 11000, qty=1))    # past 64 -> dump (fixes "after 72")
        self.assertTrue(self.gs(73, 0, qty=1))        # unknown fans, still dump late

    def test_finale_uses_regardless(self):
        self.assertTrue(self.gs(74, 0, qty=1))        # finale turn

    def test_save_lategame_toggle_honored(self):
        cfg = dict(CFG, save_items_lategame=True)
        self.assertFalse(self.gs(73, 11000, qty=1, cfg=cfg))  # toggle on -> conservation applies

    def test_early_phase_unknown_or_big(self):
        self.assertTrue(self.gs(10, 0))      # early unknown allowed
        self.assertFalse(self.gs(10, 11000)) # early known below threshold
        self.assertTrue(self.gs(10, 25000))  # early big


class TestCharmAggressiveness(unittest.TestCase):
    def setUp(self):
        self.m = _mgr()
        self.m._mant_cfg = lambda preset: (preset or {}).get("mant_config") or {}

    def charm(self, fail, gain, turn=40, owned=2, motivation=3):
        self.m._command_main_stat_gain = lambda cmd: gain
        best = {"command_type": 1, "command_id": 101, "failure_rate": fail}
        owned_map = {"Good-Luck Charm": owned}
        status = {"current_chara": {"motivation": motivation}}
        return self.m._charm_target(best, owned_map, {"mant_config": {}}, status, turn=turn)

    def test_no_charm_owned(self):
        self.assertIsNone(self.charm(45, 25, owned=0))

    def test_not_training_command(self):
        self.m._command_main_stat_gain = lambda cmd: 25
        out = self.m._charm_target({"command_type": 3}, {"Good-Luck Charm": 2}, {"mant_config": {}}, {}, turn=40)
        self.assertIsNone(out)

    def test_moderate_failure_decent_gain_fires(self):
        self.assertEqual(self.charm(25, 25), ("Good-Luck Charm", 1))

    def test_high_failure_low_gain_now_fires(self):
        # The bug: fail 45% but main gain 5 -> old code returned None (gain < 20).
        self.assertEqual(self.charm(45, 5), ("Good-Luck Charm", 1))

    def test_low_failure_low_gain_still_skipped(self):
        self.assertIsNone(self.charm(10, 5))

    def test_default_high_threshold_constant(self):
        self.assertTrue(hasattr(tb_rules, "DEFAULT_CHARM_FAILURE_RATE_HIGH"))


if __name__ == "__main__":
    unittest.main()
