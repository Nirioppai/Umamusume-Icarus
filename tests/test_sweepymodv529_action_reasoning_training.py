from pathlib import Path

from career_bot.scenarios.mant import MantStrategy

ROOT = Path(__file__).resolve().parents[1]
APP = (ROOT / "public" / "app.js").read_text(encoding="utf-8")
STYLES = (ROOT / "public" / "styles.css").read_text(encoding="utf-8")


def test_reasoning_selection_is_locked_across_refreshes():
    assert "selectedReasonKey" in APP
    assert "reasonSelectionLocked" in APP
    assert "function actionReasonKey" in APP
    assert "renderDecisionReasoning(allRows, activeIndex, { scrollActive: false })" in APP
    assert "state.reasonSelectionLocked = true" in APP


def test_live_footer_ticker_is_suppressed_while_running():
    assert "Live turn/action details already live in the Action Log" in APP
    assert "setFooterStatus('');" in APP
    assert ".v520-start-status.is-empty" in STYLES
    assert "z-index: 2 !important" in STYLES


def test_wit_balance_and_target_pressure_helpers_are_enabled():
    strategy = MantStrategy()
    chara = {
        "turn": 43,
        "speed": 250,
        "stamina": 210,
        "power": 260,
        "guts": 240,
        "wiz": 700,
        "vital": 60,
        "max_vital": 100,
    }
    targets = [1000, 700, 900, 700, 800]
    preset = {"mant_config": {}}
    assert strategy._target_pressure_multiplier(0, chara, targets, preset) > 1.0
    assert strategy._wit_balance_multiplier(chara, targets, preset) < 1.0


def test_training_candidate_trace_explains_wit_damping():
    strategy = MantStrategy()
    chara = {
        "turn": 43,
        "speed": 250,
        "stamina": 210,
        "power": 260,
        "guts": 240,
        "wiz": 700,
        "vital": 60,
        "max_vital": 100,
        "skill_point": 300,
    }
    preset = {"mant_config": {"stat_targets_by_distance": {"mile": [1000, 700, 900, 700, 800]}, "preferred_distance": "mile"}}
    wit_cmd = {
        "command_type": 1,
        "command_id": 106,
        "is_enable": 1,
        "failure_rate": 0,
        "training_partner_array": [],
        "params_inc_dec_info_array": [
            {"target_type": 5, "value": 18},
            {"target_type": 10, "value": 10},
            {"target_type": 30, "value": 20},
        ],
    }
    score = strategy._score_command(wit_cmd, {"home_info": {"command_info_array": [wit_cmd]}}, chara, preset)
    trace = strategy._training_candidate_trace(wit_cmd, score, chara, preset)
    assert trace["name"] == "Wit"
    assert "energy recovery" in trace["reason_flags"]
    assert "wit damped because other stats are behind" in trace["reason_flags"]
