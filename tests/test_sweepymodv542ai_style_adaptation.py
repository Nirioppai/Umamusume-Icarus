import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from career_bot import style_adaptation
from career_bot import ai_trainer
from career_bot import master_data


def _state(turn=12):
    return {
        "data_headers": {"viewer_id": 123},
        "data": {
            "chara_info": {
                "turn": turn,
                "card_id": 1001,
                "speed": 620,
                "stamina": 420,
                "power": 560,
                "guts": 330,
                "wiz": 510,
                "fans": 12000,
                "motivation": 5,
                "proper_running_style_nige": 4,
                "proper_running_style_senko": 7,
                "proper_running_style_sashi": 6,
                "proper_running_style_oikomi": 3,
                "proper_distance_mile": 7,
                "proper_distance_middle": 6,
                "proper_ground_turf": 7,
                "proper_ground_dirt": 3,
                "skill_array": [{"skill_id": 2001}],
            }
        },
    }


def _race_summary():
    return {
        "program_id": 555,
        "name": "Test Mile",
        "grade": "G1",
        "distance_m": 1600,
        "distance_type": "mile",
        "terrain": "turf",
        "fans": 10000,
        "master_metadata": {"venue": "Tokyo", "fans_first": 10000, "race_track_id": 101},
        "performance_hint": {"aggregate_rate": 9600},
    }


def test_style_adaptation_shadow_logs_decision_observation_and_outcome(tmp_path, monkeypatch):
    monkeypatch.setenv("UMA_RUNTIME_DIR", str(tmp_path / "uma_runtime"))
    ctx = style_adaptation.build_style_context(tmp_path, _state(), {"name": "Preset", "scenario_id": 4}, _race_summary(), 2, 12)
    decision = style_adaptation.decide_style(tmp_path, ctx, {"style_adaptation_mode": "shadow"})
    assert decision["applied_style"] == 2
    assert decision["action_type"] == "shadow_only"
    style_adaptation.record_decision(tmp_path, decision)
    obs = style_adaptation.record_observation(tmp_path, decision["decision_id"], {"race_horse_data": [
        {"viewer_id": 123, "running_style": 2},
        {"viewer_id": 999, "running_style": 1},
        {"viewer_id": 998, "running_style": 3},
    ]}, state=_state())
    assert obs["opponent_style_counts"]["1"] == 1
    assert obs["opponent_style_counts"]["3"] == 1
    out = style_adaptation.record_outcome(tmp_path, decision, {"program_id": 555, "rank": 1}, clock_retry={"used": 0, "initial_rank": 1, "won_before_retry": True})
    assert out["reward"] > 0
    rows = (tmp_path / "uma_runtime" / "ai" / "style_adaptation_experiences.jsonl").read_text().strip().splitlines()
    assert len(rows) == 3


def test_style_adaptation_training_outputs_report_and_keeps_auto_locked(tmp_path, monkeypatch):
    monkeypatch.setenv("UMA_RUNTIME_DIR", str(tmp_path / "uma_runtime"))
    for i in range(3):
        ctx = style_adaptation.build_style_context(tmp_path, _state(turn=10 + i), {"name": "Preset", "scenario_id": 4}, _race_summary(), 2, 10 + i)
        dec = style_adaptation.decide_style(tmp_path, ctx, {"style_adaptation_mode": "shadow"})
        style_adaptation.record_decision(tmp_path, dec)
        style_adaptation.record_outcome(tmp_path, dec, {"program_id": 555, "rank": 1}, clock_retry={"used": 0, "initial_rank": 1, "won_before_retry": True})
    payload = style_adaptation.train_from_experiences(tmp_path, {"style_adaptation_mode": "shadow"})
    report = payload["report"]
    assert report["completed_experiences"] == 3
    assert report["auto_apply_unlocked"] is False
    latest = style_adaptation.latest_payload(tmp_path)
    assert latest["success"] is True
    assert latest["report"]["completed_experiences"] == 3


def test_ai_trainer_dashboard_includes_style_adaptation(tmp_path, monkeypatch):
    monkeypatch.setenv("UMA_RUNTIME_DIR", str(tmp_path / "uma_runtime"))
    ctx = style_adaptation.build_style_context(tmp_path, _state(), {"name": "Preset", "scenario_id": 4}, _race_summary(), 2, 12)
    dec = style_adaptation.decide_style(tmp_path, ctx, {"style_adaptation_mode": "shadow"})
    style_adaptation.record_decision(tmp_path, dec)
    style_adaptation.record_outcome(tmp_path, dec, {"program_id": 555, "rank": 2}, clock_retry={"used": 0, "initial_rank": 2})
    result = ai_trainer.train_once(tmp_path, reason="test", rebuild_stats=False)
    assert result["success"] is True
    dash = ai_trainer.latest_dashboard(tmp_path)
    assert dash["style_adaptation"]["report"]["completed_experiences"] == 1
    assert dash["records"]["style_adaptation_experiences"] == 1


def test_ui_contains_style_adaptation_dashboard_controls():
    root = Path(__file__).resolve().parents[1]
    html = (root / "public" / "index.html").read_text(encoding="utf-8")
    app = (root / "public" / "app.js").read_text(encoding="utf-8")
    assert "v542-style-adaptation-mode" in html
    assert "Racing Style Adaptation" in html
    assert "saveStyleAdaptationMode" in app
    assert "renderStyleAdaptation" in app


def test_master_table_catalog_exporter_writes_limitations(tmp_path):
    import sqlite3
    db = tmp_path / "mini.mdb"
    conn = sqlite3.connect(db)
    try:
        conn.execute("CREATE TABLE race (id INTEGER PRIMARY KEY, name TEXT)")
        conn.execute("INSERT INTO race (id, name) VALUES (1, 'A')")
        conn.commit()
        cursor = conn.cursor()
        result = master_data.synthesize_master_table_catalog_core_from_cursor(tmp_path, cursor, {"race"})
    finally:
        conn.close()
    assert result["file"] == "master_table_catalog_core.json"
    payload = json.loads((tmp_path / "data" / "master_table_catalog_core.json").read_text())
    assert payload["table_count"] == 1
    assert payload["tables"][0]["table"] == "race"
    assert "hidden" in " ".join(payload["limitations"]).lower()
