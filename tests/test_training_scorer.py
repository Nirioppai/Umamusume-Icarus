"""Tests for the v6.1 SweepyClaude training scorer.

Covers:
  - score_trainings end-to-end on realistic command_info_array shapes
  - Each component (stat efficiency, relationship, misc, rainbow,
    level multiplier) in isolation via _score_one_command
  - Filter gates: failure_too_high, stat_capped
  - Rainbow detection: real (bond >= threshold + partner present),
    anticipatory (below threshold but >= min_fill), none
  - Per-context priority lists (training / event / summer)
  - Per-distance stat targets
  - Pre-summer prep helper
  - Edge cases: missing fields, disabled commands, the older flat field
    layout
"""

from __future__ import annotations

import unittest
from typing import Any, Dict, List

from career_bot.training_scorer import (
    TrainingScore,
    TrainingScorerConfig,
    _bond_map_from_chara,
    _current_stats,
    _infer_distance,
    _level_multiplier,
    _priority_for_context,
    _stat_gain_breakdown,
    pre_summer_action,
    score_trainings,
)


# --------------------------------------------------------------------------
# Test fixtures: realistic shapes from the actual API
# --------------------------------------------------------------------------


def make_training_cmd(
    *,
    command_id: int = 101,
    stat_gains: Dict[str, int] | None = None,
    skill_point: int = 2,
    partners: List[int] | None = None,
    tips_partners: List[int] | None = None,
    failure_rate: int = 0,
    level: int = 1,
    is_enable: int = 1,
) -> Dict[str, Any]:
    type_for_stat = {"speed": 1, "stamina": 2, "power": 3, "guts": 4, "wit": 5}
    arr = []
    for name, value in (stat_gains or {}).items():
        tt = type_for_stat.get(name)
        if tt:
            arr.append({"target_type": tt, "value": value})
    if skill_point:
        arr.append({"target_type": 30, "value": skill_point})
    return {
        "command_type": 1,
        "command_id": command_id,
        "is_enable": is_enable,
        "training_partner_array": list(partners or []),
        "tips_event_partner_array": list(tips_partners or []),
        "params_inc_dec_info_array": arr,
        "failure_rate": failure_rate,
        "level": level,
    }


def make_chara(
    stats: Dict[str, int] | None = None,
    bonds: Dict[int, int] | None = None,
    distance_aptitudes: Dict[str, str] | None = None,
) -> Dict[str, Any]:
    base_stats = {"speed": 200, "stamina": 200, "power": 200, "guts": 200, "wit": 200}
    if stats:
        base_stats.update(stats)
    apt = {"sprint": "C", "mile": "A", "medium": "A", "long": "B"}
    if distance_aptitudes:
        apt.update(distance_aptitudes)
    return {
        **{k if k != "wit" else "wiz": v for k, v in base_stats.items()},
        "evaluation_info_array": [
            {"support_card_id": cid, "evaluation": bond}
            for cid, bond in (bonds or {}).items()
        ],
        "proper_distance_short": apt["sprint"],
        "proper_distance_mile": apt["mile"],
        "proper_distance_middle": apt["medium"],
        "proper_distance_long": apt["long"],
    }


# --------------------------------------------------------------------------
# Helper tests
# --------------------------------------------------------------------------


class StatBreakdownTests(unittest.TestCase):
    def test_typical_command(self):
        cmd = make_training_cmd(stat_gains={"speed": 12, "power": 3}, skill_point=4)
        gains, sp = _stat_gain_breakdown(cmd)
        self.assertEqual(gains["speed"], 12)
        self.assertEqual(gains["power"], 3)
        self.assertEqual(sp, 4)

    def test_falls_back_to_flat_fields(self):
        # Older payload shape: stats as top-level fields, no array.
        cmd = {
            "command_id": 101,
            "command_type": 1,
            "speed": 9,
            "stamina": 2,
            "lp": 3,
        }
        gains, sp = _stat_gain_breakdown(cmd)
        self.assertEqual(gains["speed"], 9)
        self.assertEqual(gains["stamina"], 2)
        self.assertEqual(sp, 3)

    def test_handles_malformed_entries_gracefully(self):
        cmd = {
            "params_inc_dec_info_array": [
                {"target_type": "junk", "value": 5},  # bad type
                {"target_type": 1, "value": "junk"},  # bad value
                {"target_type": 1, "value": 10},      # valid
            ],
        }
        gains, sp = _stat_gain_breakdown(cmd)
        self.assertEqual(gains["speed"], 10)
        self.assertEqual(sp, 0)


class BondMapTests(unittest.TestCase):
    def test_extracts_bonds(self):
        chara = make_chara(bonds={4: 85, 7: 60, 2: 95})
        bonds = _bond_map_from_chara(chara)
        self.assertEqual(bonds[4], 85)
        self.assertEqual(bonds[7], 60)
        self.assertEqual(bonds[2], 95)

    def test_handles_missing_array(self):
        self.assertEqual(_bond_map_from_chara({}), {})


class DistanceInferenceTests(unittest.TestCase):
    def test_picks_best_aptitude(self):
        chara = make_chara(distance_aptitudes={"sprint": "S", "mile": "A", "medium": "B", "long": "C"})
        self.assertEqual(_infer_distance(chara), "sprint")

    def test_falls_back_to_mile_with_no_aptitudes(self):
        self.assertEqual(_infer_distance({}), "mile")


class LevelMultiplierTests(unittest.TestCase):
    def test_level_one_returns_one(self):
        cfg = TrainingScorerConfig()
        m = _level_multiplier(cfg, "speed", cfg.stat_priority, facility_level=1)
        self.assertEqual(m, 1.0)

    def test_top_priority_at_level_five(self):
        cfg = TrainingScorerConfig()
        # speed is rank 0 -> ceiling 1.75 at level 5
        m = _level_multiplier(cfg, "speed", cfg.stat_priority, facility_level=5)
        self.assertAlmostEqual(m, 1.75, places=4)

    def test_outside_top_n_returns_one(self):
        cfg = TrainingScorerConfig(level_weighted_top_n=3)
        # guts is rank 3 in default priority -- not in top 3
        m = _level_multiplier(cfg, "guts", cfg.stat_priority, facility_level=5)
        self.assertEqual(m, 1.0)

    def test_fades_linearly_levels_one_to_five(self):
        cfg = TrainingScorerConfig()
        m1 = _level_multiplier(cfg, "speed", cfg.stat_priority, 1)
        m3 = _level_multiplier(cfg, "speed", cfg.stat_priority, 3)
        m5 = _level_multiplier(cfg, "speed", cfg.stat_priority, 5)
        self.assertEqual(m1, 1.0)
        self.assertGreater(m3, m1)
        self.assertGreater(m5, m3)
        # Level 3 should be the midpoint between 1.0 and 1.75
        self.assertAlmostEqual(m3, 1.0 + (1.75 - 1.0) * 0.5, places=4)


class PriorityContextTests(unittest.TestCase):
    def test_event_context_uses_separate_list_when_set(self):
        cfg = TrainingScorerConfig(
            stat_priority=["speed", "stamina", "power", "guts", "wit"],
            event_stat_priority=["stamina", "wit", "speed", "power", "guts"],
        )
        self.assertEqual(_priority_for_context(cfg, "event")[0], "stamina")
        self.assertEqual(_priority_for_context(cfg, "training")[0], "speed")

    def test_summer_falls_back_to_training_when_unset(self):
        cfg = TrainingScorerConfig(stat_priority=["wit", "speed", "stamina", "power", "guts"])
        self.assertEqual(_priority_for_context(cfg, "summer")[0], "wit")


# --------------------------------------------------------------------------
# Full scorer tests
# --------------------------------------------------------------------------


class ScoreTrainingsTests(unittest.TestCase):
    def test_basic_scoring_produces_sensible_order(self):
        chara = make_chara(stats={"speed": 300, "stamina": 200}, bonds={4: 90, 7: 60})
        home_info = {
            "command_info_array": [
                make_training_cmd(command_id=101, stat_gains={"speed": 12}, partners=[4]),    # rainbow speed
                make_training_cmd(command_id=105, stat_gains={"stamina": 8}, partners=[7]),   # near-rainbow stamina
                make_training_cmd(command_id=109, stat_gains={"wit": 5}, partners=[]),        # solo wit
            ]
        }
        scores = score_trainings(home_info, chara)
        self.assertEqual(len(scores), 3)
        # All non-zero
        for s in scores:
            self.assertGreater(s.score, 0)
        # Rainbow speed should win
        self.assertEqual(scores[0].command_id, 101)

    def test_failure_too_high_sets_skipped(self):
        chara = make_chara()
        home_info = {
            "command_info_array": [
                make_training_cmd(command_id=101, stat_gains={"speed": 12}, failure_rate=35),
                make_training_cmd(command_id=105, stat_gains={"stamina": 8}, failure_rate=0),
            ]
        }
        cfg = TrainingScorerConfig(max_failure_chance=20)
        scores = score_trainings(home_info, chara, config=cfg)
        speed = next(s for s in scores if s.command_id == 101)
        stam = next(s for s in scores if s.command_id == 105)
        self.assertEqual(speed.skipped_reason, "failure_too_high")
        self.assertEqual(speed.score, 0)
        self.assertIsNone(stam.skipped_reason)
        # Stamina sorts above the filtered speed
        self.assertEqual(scores[0].command_id, 105)

    def test_stat_capped_sets_skipped(self):
        chara = make_chara(stats={"speed": 1180})  # within buffer of 1200 cap
        home_info = {
            "command_info_array": [
                make_training_cmd(command_id=101, stat_gains={"speed": 12}, partners=[4]),
            ]
        }
        scores = score_trainings(home_info, chara)
        self.assertEqual(scores[0].skipped_reason, "stat_capped")
        self.assertEqual(scores[0].score, 0)

    def test_disabled_commands_are_skipped_entirely(self):
        chara = make_chara()
        home_info = {
            "command_info_array": [
                make_training_cmd(command_id=101, stat_gains={"speed": 12}, is_enable=0),
                make_training_cmd(command_id=105, stat_gains={"stamina": 8}),
            ]
        }
        scores = score_trainings(home_info, chara)
        self.assertEqual(len(scores), 1)
        self.assertEqual(scores[0].command_id, 105)

    def test_rainbow_outranks_higher_raw_gain_without_rainbow(self):
        """The whole point of the rainbow multiplier."""
        chara = make_chara(stats={"speed": 200, "stamina": 200}, bonds={4: 95})
        home_info = {
            "command_info_array": [
                # 7 raw + rainbow partner
                make_training_cmd(command_id=101, stat_gains={"speed": 7}, partners=[4]),
                # 15 raw, no partners
                make_training_cmd(command_id=105, stat_gains={"stamina": 15}, partners=[]),
            ]
        }
        scores = score_trainings(home_info, chara)
        self.assertEqual(scores[0].command_id, 101)
        self.assertGreaterEqual(scores[0].rainbow_multiplier, 1.5)

    def test_real_rainbow_outranks_anticipatory(self):
        chara = make_chara(bonds={4: 95, 7: 50})  # 4 is rainbow, 7 is near
        home_info = {
            "command_info_array": [
                make_training_cmd(command_id=101, stat_gains={"speed": 10}, partners=[4]),    # real rainbow
                make_training_cmd(command_id=105, stat_gains={"speed": 10}, partners=[7]),    # anticipatory
            ]
        }
        scores = score_trainings(home_info, chara)
        real = next(s for s in scores if s.command_id == 101)
        antic = next(s for s in scores if s.command_id == 105)
        self.assertGreater(real.rainbow_multiplier, antic.rainbow_multiplier)
        # Real rainbow is 1.5 by default; anticipatory cap is 1.6 but limited
        # by partner fill -- with one near-rainbow at 0.625 fill the bonus is
        # 0.125, multiplier ~1.125.
        self.assertGreaterEqual(real.rainbow_multiplier, 1.5)

    def test_level_weighting_boosts_top_priority(self):
        chara = make_chara()
        home_info = {
            "command_info_array": [
                # Speed at facility level 5 (top priority -> 1.75x)
                make_training_cmd(command_id=101, stat_gains={"speed": 10}, level=5),
                # Wit at facility level 5 (rank 4 -> no boost)
                make_training_cmd(command_id=109, stat_gains={"wit": 10}, level=5),
            ]
        }
        scores = score_trainings(home_info, chara)
        speed = next(s for s in scores if s.command_id == 101)
        wit = next(s for s in scores if s.command_id == 109)
        self.assertGreater(speed.level_multiplier, wit.level_multiplier)
        self.assertEqual(wit.level_multiplier, 1.0)

    def test_no_partners_uses_no_rel_weights(self):
        """When no support cards are present, relationship weight collapses
        into stat efficiency.  Sanity check that no division-by-zero or
        weight mismatch occurs."""
        chara = make_chara()
        cmd = make_training_cmd(command_id=101, stat_gains={"speed": 10}, partners=[])
        scores = score_trainings({"command_info_array": [cmd]}, chara)
        self.assertEqual(len(scores), 1)
        self.assertGreater(scores[0].score, 0)
        self.assertEqual(scores[0].training_partners, 0)

    def test_per_distance_stat_targets_change_efficiency(self):
        """Same stat gain scores differently for sprint vs long because the
        stamina target is much higher for long."""
        chara = make_chara(stats={"stamina": 150})
        cmd = make_training_cmd(command_id=105, stat_gains={"stamina": 12}, partners=[4])
        chara_with_card = {**chara, "evaluation_info_array": [{"support_card_id": 4, "evaluation": 50}]}
        sprint_scores = score_trainings({"command_info_array": [cmd]}, chara_with_card, distance_label="sprint")
        long_scores = score_trainings({"command_info_array": [cmd]}, chara_with_card, distance_label="long")
        # Long needs much more stamina -> higher efficiency for the same gain
        self.assertGreater(long_scores[0].stat_efficiency, sprint_scores[0].stat_efficiency)

    def test_diagnostics_round_trip(self):
        chara = make_chara(bonds={4: 90})
        cmd = make_training_cmd(command_id=101, stat_gains={"speed": 10}, partners=[4], tips_partners=[4])
        scores = score_trainings({"command_info_array": [cmd]}, chara)
        d = scores[0].to_dict()
        for key in (
            "command_id", "command_type", "stat_name", "score", "stat_efficiency",
            "relationship", "misc", "rainbow_multiplier", "level_multiplier",
            "raw_stat_gain", "skill_point_gain", "failure_rate",
            "training_partners", "rainbow_partners", "near_rainbow_partners",
            "facility_level", "skipped_reason",
        ):
            self.assertIn(key, d)


# --------------------------------------------------------------------------
# Pre-summer helper
# --------------------------------------------------------------------------


class PreSummerActionTests(unittest.TestCase):
    def test_returns_none_on_non_pre_summer_turn(self):
        self.assertIsNone(pre_summer_action(turn=10, energy=100, energy_max=100, mood=5))
        self.assertIsNone(pre_summer_action(turn=25, energy=100, energy_max=100, mood=5))

    def test_rests_when_energy_below_floor(self):
        self.assertEqual(
            pre_summer_action(turn=24, energy=60, energy_max=100, mood=5),
            "rest",
        )

    def test_recovers_when_mood_below_great(self):
        self.assertEqual(
            pre_summer_action(turn=24, energy=100, energy_max=100, mood=3),
            "recover",
        )

    def test_trains_wit_when_energy_and_mood_are_fine(self):
        self.assertEqual(
            pre_summer_action(turn=48, energy=100, energy_max=100, mood=5),
            "train_wit",
        )

    def test_energy_floor_is_configurable(self):
        # With floor=0.5, 60% energy is fine -> not "rest"
        self.assertNotEqual(
            pre_summer_action(turn=24, energy=60, energy_max=100, mood=5, energy_floor_pct=0.5),
            "rest",
        )


# --------------------------------------------------------------------------
# Realistic command_info_array shape from your actual run
# --------------------------------------------------------------------------


class RealShapeRegressionTests(unittest.TestCase):
    """Mirrors the shape we observed in latest_career_log.json so the scorer
    is exercised on the exact API contract."""

    def test_realistic_payload_scores_cleanly(self):
        chara = {
            "speed": 173,
            "stamina": 74,
            "power": 195,
            "guts": 94,
            "wiz": 1,
            "evaluation_info_array": [
                {"support_card_id": 4, "evaluation": 75},
                {"support_card_id": 2, "evaluation": 30},
            ],
            "proper_distance_mile": 7,  # numeric A
            "proper_distance_middle": 7,
            "proper_distance_short": 6,
            "proper_distance_long": 6,
        }
        home_info = {
            "command_info_array": [
                {
                    "command_type": 1, "command_id": 101, "is_enable": 1,
                    "training_partner_array": [4],
                    "tips_event_partner_array": [4],
                    "params_inc_dec_info_array": [
                        {"target_type": 1, "value": 10},
                        {"target_type": 3, "value": 3},
                        {"target_type": 30, "value": 2},
                    ],
                    "failure_rate": 0, "level": 1,
                },
                {
                    "command_type": 1, "command_id": 105, "is_enable": 1,
                    "training_partner_array": [2],
                    "tips_event_partner_array": [],
                    "params_inc_dec_info_array": [
                        {"target_type": 2, "value": 7},
                        {"target_type": 30, "value": 1},
                    ],
                    "failure_rate": 0, "level": 1,
                },
            ]
        }
        scores = score_trainings(home_info, chara)
        self.assertEqual(len(scores), 2)
        # Both should score; Speed with the near-rainbow partner (75/80) at
        # 0.94 fill is heavily anticipated.
        for s in scores:
            self.assertGreater(s.score, 0)
            self.assertIsNone(s.skipped_reason)


if __name__ == "__main__":
    unittest.main()
