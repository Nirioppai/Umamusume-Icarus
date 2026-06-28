"""v2.1 skill-point rework: stop-after-recommended (auto), manual auto-fallback
toggle, and owned-by-name exclusion (kills the phantom 're-bought one skill'
spend log)."""
import unittest
from pathlib import Path

from career_bot.skills import SkillBuyer, norm, strip_mark
from career_bot.config_store import SKILL_CONFIG_KEYS, _default_skill_config

ROOT = Path(__file__).resolve().parent.parent


class SkillV21ReworkTests(unittest.TestCase):
    def test_new_defaults(self):
        c = _default_skill_config()
        # 2026-06-26: default OFF. The old default-ON discarded ALL good, on-profile
        # candidates on any turn where none happened to be a top-tier "recommended"
        # skill, so the bot bought ~nothing and hoarded SP (2030 unspent). The smart
        # scorer (style/distance/min-score) already filters quality, so buy good
        # skills by default; stop-after-recommended is now opt-in.
        self.assertFalse(c["skill_stop_after_recommended"])
        # Manual auto-fallback toggle defaults OFF (buy only listed, then stop).
        self.assertFalse(c["skill_manual_auto_fallback"])
        # Legacy toggle still defaults to "stop after listed".
        self.assertTrue(c["manual_skill_tiers_dont_spend_extra"])

    def test_new_keys_round_trip_via_allowlist(self):
        # Without these in SKILL_CONFIG_KEYS the toggles would never persist.
        for k in ("skill_stop_after_recommended", "skill_manual_auto_fallback",
                  "manual_skill_tiers_dont_spend_extra"):
            self.assertIn(k, SKILL_CONFIG_KEYS)

    def test_recommended_set_is_preferred_plus_top_tiers(self):
        buyer = SkillBuyer(ROOT)
        rec = buyer._recommended_skill_names({}, {"preferred_skill_names": ["Fast-Paced", "Mile Maven"]})
        self.assertIn(norm("Fast-Paced"), rec)
        self.assertIn(norm("Mile Maven"), rec)
        # Community SS-tier names feed the "best skills" set too.
        for n in (buyer.community_tiers.get("SS") or [])[:3]:
            self.assertIn(norm(strip_mark(n)), rec)

    def test_owned_skill_is_not_re_selected_by_name(self):
        # A skill already owned (by base name) must never come back as a
        # candidate, even if a tip for its group reappears next turn. This is
        # the backstop that prevents a single-purchase skill from being logged
        # as bought turn after turn (the "1,890 SP on one skill" symptom).
        buyer = SkillBuyer(ROOT)
        sid = next((s for s in buyer.skill_names if buyer.skill_names.get(s)), None)
        self.assertIsNotNone(sid)
        owned_name = buyer.skill_names[sid]
        group = buyer.skill_to_group_id.get(sid, sid // 10)
        chara = {
            "turn": 10,
            "skill_array": [{"skill_id": sid}],
            "skill_tips_array": [{"group_id": group, "rarity": 0, "level": 0}],
        }
        cands = buyer._candidates(chara, {})
        for c in cands:
            self.assertNotEqual(
                norm(strip_mark(c.get("name", ""))),
                norm(strip_mark(owned_name)),
                f"owned skill {owned_name!r} leaked back into candidates",
            )


if __name__ == "__main__":
    unittest.main()
