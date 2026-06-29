# -*- coding: utf-8 -*-
"""Stage 3 of the skill-purchase redesign: sheet-driven graded tier + optimization target.

The community "Uma Musume Skills Spreadsheet" (ingested by
tools/spreadsheet_skill_tier_scraper.py -> data/skill_tiers_normalized.json)
gives every skill a Team-Trials rank and a Champions/PvP rank as symbols
(essential -> useless: U+235F > U+25CE > U+25EF > U+25B2 > U+25B3 > U+2715).

The scorer maps that symbol to a heuristic bonus. An `skill_optimization_target`
config picks WHICH rank column weights the bonus:
  career / team_trials -> the Team-Trials column (TT is the best proxy for the
                          value of a skill on a single-mode-built uma)
  champions            -> the Champions/PvP column

`disable_singlemode` skills are dead SP in CAREER (the game disables them in
single mode) but DO work on the finished uma in Team Trials / Champions, so the
penalty is made mode-dependent: hard-drop in career, kept (no penalty) in TT/CM.
"""
import unittest
from pathlib import Path

from career_bot.skills import (
    SkillBuyer,
    _normalize_skill_target,
    DEFAULT_SHEET_TIER_BONUS,
)

ESSENTIAL = "⍟"   # best in the sheet legend
BEST = "◎"        # double circle
GOOD = "◯"        # large circle
SITUATIONAL = "▲" # triangle up
EXCESS = "△"      # triangle outline
USELESS = "✕"     # x


class TestNormalizeTarget(unittest.TestCase):
    def test_default_is_career(self):
        self.assertEqual(_normalize_skill_target(None), "career")
        self.assertEqual(_normalize_skill_target(""), "career")
        self.assertEqual(_normalize_skill_target("garbage"), "career")

    def test_career(self):
        self.assertEqual(_normalize_skill_target("career"), "career")

    def test_team_trials_aliases(self):
        for v in ["team_trials", "Team Trials", "TT", "trials", "team"]:
            self.assertEqual(_normalize_skill_target(v), "team_trials", v)

    def test_champions_aliases(self):
        for v in ["champions", "Champions Meeting", "cm", "CM9", "pvp"]:
            self.assertEqual(_normalize_skill_target(v), "champions", v)


class TestSheetTierScore(unittest.TestCase):
    def _buyer(self):
        b = SkillBuyer.__new__(SkillBuyer)
        b.sheet_tier_by_norm = {
            "frontrunnercorners": {"name": "Front Runner Corners", "tt": BEST, "cm": ESSENTIAL},
            "milematron": {"name": "Mile Matron", "tt": EXCESS, "cm": USELESS},
            "ttonlyskill": {"name": "TT Only Skill", "tt": GOOD, "cm": ""},
        }
        return b

    def test_career_uses_tt_column(self):
        bonus, sym = self._buyer()._sheet_tier_score("Front Runner Corners", "Front Runner Corners", "career")
        self.assertEqual(sym, BEST)
        self.assertEqual(bonus, DEFAULT_SHEET_TIER_BONUS[BEST])

    def test_team_trials_uses_tt_column(self):
        bonus, sym = self._buyer()._sheet_tier_score("Front Runner Corners", "Front Runner Corners", "team_trials")
        self.assertEqual(sym, BEST)

    def test_champions_uses_cm_column(self):
        bonus, sym = self._buyer()._sheet_tier_score("Front Runner Corners", "Front Runner Corners", "champions")
        self.assertEqual(sym, ESSENTIAL)
        self.assertEqual(bonus, DEFAULT_SHEET_TIER_BONUS[ESSENTIAL])

    def test_useless_in_champions_is_penalized(self):
        bonus, sym = self._buyer()._sheet_tier_score("Mile Matron", "Mile Matron", "champions")
        self.assertEqual(sym, USELESS)
        self.assertLess(bonus, 0)

    def test_unknown_skill_returns_zero(self):
        bonus, sym = self._buyer()._sheet_tier_score("Nonexistent", "Nonexistent", "career")
        self.assertEqual((bonus, sym), (0.0, ""))

    def test_champions_falls_back_to_tt_when_cm_empty(self):
        bonus, sym = self._buyer()._sheet_tier_score("TT Only Skill", "TT Only Skill", "champions")
        self.assertEqual(sym, GOOD)

    def test_base_name_lookup_preferred(self):
        # marked variant name should still resolve via base_name
        bonus, sym = self._buyer()._sheet_tier_score("Front Runner Corners ◎", "Front Runner Corners", "career")
        self.assertEqual(sym, BEST)

    def test_preset_multiplier_override(self):
        b = self._buyer()
        bonus, sym = b._sheet_tier_score(
            "Front Runner Corners", "Front Runner Corners", "career",
            {"skill_tier_multipliers": {BEST: 999}},
        )
        self.assertEqual(bonus, 999)


class TestDisableSinglemodeMode(unittest.TestCase):
    def _buyer(self):
        return SkillBuyer.__new__(SkillBuyer)

    def test_no_flag_no_adjustment(self):
        self.assertEqual(self._buyer()._disable_singlemode_adjustment({"disable_singlemode": 0}, "career"), (0.0, None))
        self.assertEqual(self._buyer()._disable_singlemode_adjustment(None, "career"), (0.0, None))

    def test_career_hard_drops(self):
        adj, reason = self._buyer()._disable_singlemode_adjustment({"disable_singlemode": 1}, "career")
        self.assertLessEqual(adj, -9000)
        self.assertIn("disable_singlemode", reason)

    def test_team_trials_keeps(self):
        adj, reason = self._buyer()._disable_singlemode_adjustment({"disable_singlemode": 1}, "team_trials")
        self.assertEqual(adj, 0.0)
        self.assertIn("kept", reason)

    def test_champions_keeps(self):
        adj, reason = self._buyer()._disable_singlemode_adjustment({"disable_singlemode": 1}, "champions")
        self.assertEqual(adj, 0.0)


class TestSheetLoaderIntegration(unittest.TestCase):
    def test_loads_real_json(self):
        b = SkillBuyer.__new__(SkillBuyer)
        b.base_dir = Path(__file__).resolve().parent.parent
        b._load_sheet_tiers()
        self.assertIn("frontrunnercorners", b.sheet_tier_by_norm)
        rec = b.sheet_tier_by_norm["frontrunnercorners"]
        self.assertEqual(rec["tt"], BEST)
        self.assertEqual(rec["cm"], ESSENTIAL)

    def test_missing_file_is_empty(self):
        b = SkillBuyer.__new__(SkillBuyer)
        b.base_dir = Path(__file__).resolve().parent / "does_not_exist_dir"
        b._load_sheet_tiers()
        self.assertEqual(b.sheet_tier_by_norm, {})


if __name__ == "__main__":
    unittest.main()
