import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
APP = (ROOT / "public" / "app.js").read_text(encoding="utf-8")
MAIN = (ROOT / "main.py").read_text(encoding="utf-8")
CLIENT = (ROOT / "uma_api" / "client.py").read_text(encoding="utf-8")


class SweepyModV518GuestParentStartTests(unittest.TestCase):
    def test_guest_parent_slot_uses_combined_parent_lineup(self):
        self.assertIn("function selectedParentLineup()", APP)
        self.assertIn("_selectionKind: 'guest'", APP)
        self.assertIn("const parentSlots = selectedParentLineup();", APP)
        self.assertIn("Guest ${rankMap[parent.rank]", APP)
        self.assertIn("`, action, actionIdx, 'select parent')", APP)

    def test_guest_parent_start_payload_uses_rental_fields(self):
        self.assertIn("function selectedParentStartPayload()", APP)
        self.assertIn("parent_selection_mode: 'own_guest'", APP)
        self.assertIn("rental_viewer_id: Number(guest.viewer_id || 0)", APP)
        self.assertIn("rental_trained_chara_id: Number(guest.instance_id || guest.id || 0)", APP)
        self.assertIn("parent_id_2: 0", APP)
        self.assertIn("rental_viewer_id: parentPayload.rental_viewer_id", APP)
        self.assertIn("rental_trained_chara_id: parentPayload.rental_trained_chara_id", APP)

    def test_backend_request_accepts_rental_parent_fields(self):
        self.assertIn("rental_viewer_id: int = 0", MAIN)
        self.assertIn("rental_trained_chara_id: int = 0", MAIN)
        self.assertIn("rental_card_id: int = 0", MAIN)
        self.assertIn("Guest parent requires one owned parent", MAIN)
        self.assertIn("Guest parent cannot be combined with two owned parents", MAIN)
        self.assertIn("rental_viewer_id=getattr(req, \"rental_viewer_id\", 0)", MAIN)
        self.assertIn("rental_trained_chara_id=getattr(req, \"rental_trained_chara_id\", 0)", MAIN)

    def test_uma_client_start_payload_contains_rental_object(self):
        self.assertIn("rental_viewer_id=0, rental_trained_chara_id=0", CLIENT)
        self.assertIn("'succession_trained_chara_id_1': parent_id_1", CLIENT)
        self.assertIn("'succession_trained_chara_id_2': parent_id_2", CLIENT)
        self.assertIn("'rental_succession_trained_chara':", CLIENT)
        self.assertIn("'viewer_id': rental_viewer_id", CLIENT)
        self.assertIn("'trained_chara_id': rental_trained_chara_id", CLIENT)


if __name__ == "__main__":
    unittest.main()
