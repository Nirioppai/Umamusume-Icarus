import json
from pathlib import Path

from career_bot.races import RacePlanner
from career_bot import trackblazer


def _write_race_map(base: Path):
    data = {
        "meta": {
            "1": {"program_id": 111, "turn": 20},
            "2": {"program_id": 222, "turn": 20},
        },
        "program": {
            "111": {"name": "Old Planned Race", "ground": 1, "distance": 1600, "grade": "G1", "fans": 10000},
            "222": {"name": "Legacy Fallback Race", "ground": 1, "distance": 1600, "grade": "G1", "fans": 20000},
        },
        "instance": {},
    }
    (base / "data").mkdir(parents=True, exist_ok=True)
    (base / "data" / "race_map.json").write_text(json.dumps(data), encoding="utf-8")


def _state(turn=20):
    return {
        "data": {
            "chara_info": {
                "turn": turn,
                "scenario_id": 4,
                "speed": 500,
                "stamina": 420,
                "power": 500,
                "guts": 300,
                "wiz": 450,
                "fans": 1000,
                "card_id": 1001,
                "proper_distance_short": 7,
                "proper_distance_mile": 7,
                "proper_distance_middle": 7,
                "proper_distance_long": 7,
                "proper_ground_turf": 7,
                "proper_ground_dirt": 7,
            },
            "home_info": {"command_info_array": [{"command_type": 4, "command_id": 401, "is_enable": 1}]},
            "race_condition_array": [{"program_id": 111}, {"program_id": 222}],
            "runner_context": {
                "clock_retry_policy": {"enabled": False, "user_enabled": False},
                "clocks_used": 0,
                "clocks_left": 3,
                "race_results": [{"turn": 18, "program_id": 999, "rank": 4, "final_rank": 4, "clocks_used": 0}],
                "runtime_support": {"energy_items": 2, "race_items": 1, "clocks": 3, "burn_clocks_enabled": False},
            },
        }
    }


def test_live_replan_passes_current_state_history_and_runtime_support(tmp_path, monkeypatch):
    _write_race_map(tmp_path)
    planner = RacePlanner(tmp_path)
    calls = []

    def fake_make_schedule(base_dir, **kwargs):
        calls.append(kwargs)
        return {
            "success": True,
            "solver": "fake-live",
            "extra_race_list": [222],
            "schedule": [{"turn": 20, "program_id": 222}],
            "decisions": {20: {"type": "race", "program_id": 222}},
            "dead_epithets": ["Dead Branch"],
            "projected_epithets": ["Projected"],
            "notes": ["live replan test"],
        }

    monkeypatch.setattr(trackblazer, "make_schedule", fake_make_schedule)
    preset = {"name": "LivePreset", "extra_race_list_source": "smart", "extra_race_list": [111], "mant_config": {}}

    choice = planner.choose(_state(), preset)

    assert choice == 222
    assert calls, "expected turn-level replan before choosing the race"
    call = calls[0]
    assert call["current_turn"] == 20
    assert call["trainee_id"] == 1001
    assert call["preset_name"] == "LivePreset"
    assert call["race_history"][0]["program_id"] == 999
    assert call["weights"]["currentStats"]["stamina"] == 420
    assert call["weights"]["runtimeSupport"]["burn_clocks_enabled"] is False
    assert preset["trackblazer_last_plan"]["dead_epithets"] == ["Dead Branch"]
    assert planner.last_live_replan["history_rows"] == 1


def test_smart_solver_train_decision_suppresses_legacy_fan_farming(tmp_path, monkeypatch):
    _write_race_map(tmp_path)
    planner = RacePlanner(tmp_path)

    def fake_make_schedule(base_dir, **kwargs):
        return {
            "success": True,
            "solver": "fake-live",
            "extra_race_list": [],
            "schedule": [],
            "decisions": {20: {"type": "train"}},
            "notes": ["train this turn"],
        }

    monkeypatch.setattr(trackblazer, "make_schedule", fake_make_schedule)
    preset = {
        "name": "LivePreset",
        "extra_race_list_source": "smart",
        "extra_race_list": [111],
        "mant_config": {"enable_farming_fans": True, "days_to_run_extra_races": 1},
    }
    state = _state()
    state["data"]["chara_info"]["fans"] = 100  # would trigger legacy maiden/fan fallback without smart suppression.

    assert planner.choose(state, preset) == 0
    assert preset["trackblazer_last_plan"]["decisions"][20]["type"] == "train"


def test_trackblazer_candidate_rows_use_profile_specific_risk(monkeypatch, tmp_path):
    seen = []

    monkeypatch.setattr(trackblazer, "load_or_download", lambda base_dir: {"races": [{"name": "Race", "grade": "G1", "distance": "Mile", "surface": "Turf", "fans": 10000}]})
    monkeypatch.setattr(trackblazer, "_build_program_name_index", lambda base_dir: {"race": [{"program_id": 77, "turn": 30, "name": "Race"}]})
    monkeypatch.setattr(trackblazer, "_official_program_core", lambda base_dir: {})
    monkeypatch.setattr(trackblazer, "_trackblazer_reward_core", lambda base_dir: {})
    monkeypatch.setattr(trackblazer, "_performance_rates", lambda base_dir: {})

    def fake_risk(base_dir, program_id, trainee_id="", preset_name="", min_samples=2):
        seen.append((program_id, trainee_id, preset_name))
        return {"penalty": 12, "samples": 8, "scope": "profile"}

    monkeypatch.setattr(trackblazer, "race_outcome_risk", fake_risk)
    rows = trackblazer._candidate_rows(tmp_path, aptitudes={"Mile": "A", "Turf": "A"}, trainee_id="1001", preset_name="PresetA")

    assert seen == [(77, "1001", "PresetA")]
    assert rows[0]["outcome_risk"]["scope"] == "profile"
    assert rows[0]["outcome_risk_penalty"] == 12
