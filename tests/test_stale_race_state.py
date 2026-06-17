"""Stale race-state regression copied from the Umabot crash suite and adapted.
If a race is already recorded in race_history and home commands are available,
the strategy should continue normal turn work rather than endlessly resuming.
"""
from pathlib import Path

from career_bot.scenarios.mant import MantStrategy
from career_bot.races import RacePlanner

ROOT = Path(__file__).resolve().parents[1]


def stuck_state():
    return {"data": {
        "chara_info": {
            "turn": 60, "playing_state": 3, "race_program_id": 74,
            "race_running_style": 1, "vital": 47, "max_vital": 108,
            "motivation": 5, "skill_point": 156, "state": 0,
            "speed": 789, "stamina": 504, "power": 840, "guts": 395, "wiz": 451,
        },
        "race_start_info": {"program_id": 74, "continue_num": 0},
        "race_history": [
            {"program_id": 73, "result_rank": 1, "turn": 59},
            {"program_id": 74, "result_rank": 1, "turn": 60},
        ],
        "home_info": {"command_info_array": [
            {"command_type": 1, "command_id": 101, "is_enable": 1, "failure_rate": 8,
             "params_inc_dec_info_array": [{"target_type": 1, "value": 10}]},
            {"command_type": 7, "command_id": 701, "is_enable": 1, "failure_rate": 0},
        ]},
        "unchecked_event_array": [],
    }}


def make_strategy():
    return MantStrategy(RacePlanner(str(ROOT)))


def test_stale_race_state_does_not_race():
    decision = make_strategy().next_decision(stuck_state(), {"scenario_id": 4})
    assert decision.action not in ("race_progress", "race"), f"still stuck: {decision.action} ({decision.reason})"


def test_genuine_inrace_state_still_resumes():
    state = stuck_state()
    state["data"]["race_history"] = [{"program_id": 73, "result_rank": 1, "turn": 59}]
    decision = make_strategy().next_decision(state, {"scenario_id": 4})
    assert decision.action == "race_progress", f"expected race_progress, got {decision.action}"
