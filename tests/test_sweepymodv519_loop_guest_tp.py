import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
MAIN = (ROOT / "main.py").read_text(encoding="utf-8")


class SweepyModV519LoopGuestTpTests(unittest.TestCase):
    def test_guest_parent_is_refreshed_before_each_start(self):
        self.assertIn("def _refresh_guest_parent_for_start", MAIN)
        self.assertIn("Selected guest parent is no longer available in the fresh pre-start", MAIN)
        self.assertIn("req.rental_trained_chara_id = trained_id", MAIN)
        self.assertIn("req.parent_id_2 = 0", MAIN)
        self.assertIn("pre_start = _pre_start_refresh(req)", MAIN)

    def test_guest_start_501_is_fatal_for_loop(self):
        self.assertIn("The game rejected the guest parent start request after refresh", MAIN)
        self.assertIn('"fatal_start": True', MAIN)
        self.assertIn("career loop stopped before next start", MAIN)
        self.assertIn("return", MAIN[MAIN.index("career loop stopped before next start") : MAIN.index("career loop stopped before next start") + 220])

    def test_loop_start_uses_shared_tp_recovery_policy(self):
        self.assertIn("tp_mode = load_tp_recovery_mode()", MAIN)
        self.assertIn('active_start_state["tp_restore_reasoning"] = restore_reasoning', MAIN)
        self.assertIn('result["_tp_restore_reasoning"] = restore_reasoning', MAIN)
        self.assertNotIn("toughness_restore_rejected_until", MAIN)


if __name__ == "__main__":
    unittest.main()
