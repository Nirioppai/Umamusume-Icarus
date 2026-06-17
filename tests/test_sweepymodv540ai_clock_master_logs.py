from pathlib import Path

from career_bot.ai_dataset import turn_decision_records, career_summary_record
from career_bot.ai_trainer import build_race_outcome_table, build_race_risk_model, build_policy_adjustments
from career_bot.race_intelligence import record_race_outcome, load_outcomes, race_outcome_risk
from career_bot.trackblazer import _smart_race_score


def _clocked_report():
    return {
        "started_at": "2026-06-14T00:00:00",
        "preset_name": "Clock Test",
        "scenario_id": 4,
        "status": "finished",
        "runtime_settings": {
            "burn_clocks": True,
            "clock_retry_policy": {"user_enabled": True, "enabled": True, "source": "test"},
        },
        "runner_status": {
            "race_results": [
                {
                    "turn": 56,
                    "program_id": 123,
                    "name": "Long Risk G1",
                    "grade": "G1",
                    "rank": 1,
                    "initial_rank": 4,
                    "final_rank": 1,
                    "clocks_used": 1,
                    "won_after_clock": True,
                    "won_without_clock": False,
                    "clock_retry": {
                        "user_enabled": True,
                        "enabled": True,
                        "used": 1,
                        "initial_rank": 4,
                        "final_rank": 1,
                        "won_before_retry": False,
                        "won_after_retry": True,
                    },
                    "master_metadata": {"fans_first": 20000, "trackblazer_coin_first": 100},
                    "performance_hint": {"distance_label": "Long", "distance_aptitude": 6, "aggregate_rate": 9000},
                }
            ]
        },
        "turns": [
            {
                "turn": 56,
                "selected_action": "race",
                "decision_report": {
                    "action": "race",
                    "reason": "planned race",
                    "payload": {"program_id": 123, "current_turn": 56},
                    "state": {"speed": 900, "stamina": 430, "power": 850, "guts": 400, "wit": 700, "hp": 80, "mood": 5, "fans": 300000},
                    "race_context": {"program_id": 123, "clock_policy": {"user_enabled": True, "enabled": True}},
                },
            }
        ],
    }


def test_turn_records_include_clock_retry_and_master_metadata():
    rows = turn_decision_records(_clocked_report(), build_version="SweepyModv5.40AI")
    assert len(rows) == 1
    row = rows[0]
    assert row["outcome"]["race_result"]["initial_rank"] == 4
    assert row["outcome"]["race_result"]["master_metadata"]["fans_first"] == 20000
    assert row["outcome"]["race_result"]["performance_hint"]["distance_label"] == "Long"
    assert row["outcome"]["clocks_used"] == 1
    assert row["outcome"]["won_after_clock"] is True
    assert row["turn_metadata"]["clock_policy"]["user_enabled"] is True


def test_career_summary_counts_clock_saved_wins():
    summary = career_summary_record(_clocked_report(), build_version="SweepyModv5.40AI")
    assert summary["race_count"] == 1
    assert summary["race_wins"] == 1
    assert summary["clock_retry_races"] == 1
    assert summary["clock_saved_wins"] == 1


def test_race_table_and_policy_track_clock_dependency():
    rows = turn_decision_records(_clocked_report(), build_version="SweepyModv5.40AI")
    table = build_race_outcome_table(rows)
    bucket = table["programs"]["123"]
    assert bucket["starts"] == 1
    assert bucket["wins"] == 1
    assert bucket["clean_wins"] == 0
    assert bucket["wins_after_clock"] == 1
    assert bucket["clock_dependency_rate"] == 1.0
    model = build_race_risk_model(table, min_samples=1)
    assert model["model"]["123"]["clock_dependency_penalty"] > 0
    policy = build_policy_adjustments(model, {"items": {}}, {"events": {}}, {"confidence_threshold": 0.1, "max_abs_live_adjustment": 25, "enable_live_policy_assistance": True})
    assert policy["races"]["123"]["clock_dependency_penalty"] > 0


def test_runtime_race_outcomes_store_clock_fields(tmp_path, monkeypatch):
    monkeypatch.setenv("UMA_RUNTIME_DIR", str(tmp_path / "runtime"))
    record_race_outcome(
        tmp_path,
        {
            "program_id": 456,
            "turn": 42,
            "rank": 1,
            "initial_rank": 3,
            "clocks_used": 1,
            "won_after_clock": True,
            "clock_retry": {"user_enabled": True, "used": 1, "initial_rank": 3, "final_rank": 1, "won_after_retry": True},
        },
        stats={"stamina": 500},
        preset_name="Preset",
        trainee_id="1001",
    )
    data = load_outcomes(tmp_path)
    bucket = data["programs"]["456"]
    assert bucket["wins_after_clock"] == 1
    assert bucket["clock_retry_races"] == 1
    risk = race_outcome_risk(tmp_path, 456, min_samples=1)
    assert risk["clock_dependency_penalty"] > 0


def test_smart_score_penalizes_clock_dependency_when_burn_clocks_disabled():
    row = {
        "program_id": 789,
        "turn": 66,
        "grade": "G1",
        "fans": 30000,
        "est_fans": 30000,
        "outcome_risk": {"penalty": 0, "clock_dependency_penalty": 20},
        "outcome_risk_penalty": 0,
    }
    disabled = _smart_race_score(dict(row), {"runtimeSupport": {"clocks": 10, "burn_clocks_enabled": False}, "fanWeight": 0.001})
    enabled = _smart_race_score(dict(row), {"runtimeSupport": {"clocks": 10, "burn_clocks_enabled": True}, "fanWeight": 0.001})
    assert enabled > disabled
