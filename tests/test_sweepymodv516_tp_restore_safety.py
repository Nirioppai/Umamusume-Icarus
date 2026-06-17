import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
MAIN = (ROOT / "main.py").read_text(encoding="utf-8")
APP = (ROOT / "public" / "app.js").read_text(encoding="utf-8")
CLIENT = (ROOT / "uma_api" / "client.py").read_text(encoding="utf-8")


class SweepyModV516TpRecoveryReplacementTests(unittest.TestCase):
    def test_tp_recovery_modes_are_persisted_in_settings_json(self):
        self.assertIn('TP_RECOVERY_MODES = ("potion_first", "potion_only", "jewels_only")', MAIN)
        self.assertIn('def load_tp_recovery_mode()', MAIN)
        self.assertIn('def set_tp_recovery_mode(mode)', MAIN)
        self.assertIn('@app.get("/api/settings/tp-recovery")', MAIN)
        self.assertIn('@app.post("/api/settings/tp-recovery")', MAIN)

    def test_umabot_item_recovery_replaces_toughness_selector_flow(self):
        self.assertIn('active_client.use_recovery_item(item_num=1)', MAIN)
        self.assertIn('for attempt in range(20)', MAIN)
        self.assertIn('active_client.recovery_tp(needed)', MAIN)
        self.assertIn('"potion_first", "jewels_only"', MAIN)
        self.assertNotIn('requested_restore_currency = str', MAIN)
        self.assertNotIn('restore_modes = [requested_restore_currency]', MAIN)
        self.assertNotIn('toughness_213_rejected = True', MAIN)

    def test_ui_exposes_tp_items_and_recovery_mode_select(self):
        self.assertIn('TP POTIONS', APP)
        self.assertIn('tp-recovery-mode-select', APP)
        self.assertIn('/api/settings/tp-recovery', APP)
        self.assertIn('sweepy_tp_recovery_mode', APP)
        self.assertNotIn('Use Carats if Toughness 30 fails', APP)
        self.assertNotIn('v545-tp-toughness-btn', APP)

    def test_client_uses_umabot_payload_shapes(self):
        self.assertIn('def recovery_tp(self, count=1):', CLIENT)
        self.assertIn('"client_own_num": total_jewels', CLIENT)
        self.assertIn('def use_recovery_item(self, item_num=1, item_id=None):', CLIENT)
        self.assertIn('self.call("item/use_recovery_item"', CLIENT)


if __name__ == "__main__":
    unittest.main()
