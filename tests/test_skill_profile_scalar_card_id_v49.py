import json
import tempfile
import unittest
from pathlib import Path

from career_bot.skills import SkillBuyer


class SkillProfileScalarCardIdTests(unittest.TestCase):
    def test_infer_skill_profile_accepts_scalar_card_id(self):
        base = Path(tempfile.mkdtemp())
        data = base / "data"
        data.mkdir(parents=True, exist_ok=True)
        (data / "trainee_skill_profiles.generated.json").write_text(json.dumps({
            "Scalar Profile": {
                "name": "Scalar Profile",
                "card_id": 100101,
                "running_style": "front",
                "primary_distances": ["mile"],
                "track": "turf",
                "match_names": ["Scalar Profile"]
            }
        }), encoding="utf-8")
        buyer = SkillBuyer(base)
        profile = buyer._infer_skill_profile({"card_id": 100101}, {})
        self.assertEqual(profile.get("name"), "Scalar Profile")


if __name__ == "__main__":
    unittest.main()
