import json
from pathlib import Path

from career_bot.config_store import ConfigStore

ROOT = Path(__file__).resolve().parents[1]
APP = (ROOT / "public" / "app.js").read_text(encoding="utf-8")
INDEX = (ROOT / "public" / "index.html").read_text(encoding="utf-8")
STYLES = (ROOT / "public" / "styles.css").read_text(encoding="utf-8")
MAIN = (ROOT / "main.py").read_text(encoding="utf-8")
BUNDLED = json.loads((ROOT / "data" / "settings_presets.json").read_text(encoding="utf-8"))


def test_settings_presets_can_store_team_selection_without_skill_config(tmp_path):
    store = ConfigStore(tmp_path)
    saved = store.save_settings_preset({
        "name": "Team Memory",
        "running_style": 2,
        "selection": {
            "deck": {"id": 3},
            "friend": {"viewer_id": "22", "support_card_id": "30001"},
            "trainee": {"id": "100101"},
            "veterans": [{"instance_id": 111}, {"instance_id": 222}],
            "guestParents": [{"viewer_id": 44, "instance_id": 555, "card_id": 100201}],
        },
        "skill_config_by_trainee": {"100101": {"should_not": "be_saved"}},
    })

    assert saved["selection"]["deck"]["id"] == 3
    assert saved["selection"]["friend"]["support_card_id"] == "30001"
    assert saved["selection"]["trainee"]["id"] == "100101"
    assert "skill_config_by_trainee" not in saved

    payload = store.read_settings_presets()
    preset = next(p for p in payload["presets"] if p["name"] == "Team Memory")
    assert preset["selection"]["veterans"][1]["instance_id"] == 222


def test_bundled_default_has_empty_selection():
    preset = BUNDLED["presets"][0]
    assert preset["name"] == "Default"
    assert preset.get("selection") == {}


def test_frontend_restores_preset_selection_and_no_longer_exposes_sync_button():
    assert "buildSelectionPresetSnapshot" in APP
    assert "applyPresetSelection" in APP
    assert "current.selection = buildSelectionPresetSnapshot();" in APP
    assert 'id="v520-sync-btn"' not in INDEX
    assert "v520SyncBtn" not in APP
    assert "Syncing dashboard state" not in APP
    assert 'id="v526-pause-runner-btn"' in INDEX


def test_top_bar_labels_are_user_facing_tp_potions_and_carrots():
    assert "TP POTIONS" in APP
    assert "CARROTS" in APP
    assert "JEWELS" not in APP


def test_career_history_major_wins_are_snapshotted():
    assert "from copy import deepcopy" in MAIN
    assert "major_win_summary" in MAIN
    assert "deepcopy(list(snap.get(\"race_results\")" in MAIN
    assert "\"major_wins\": major_wins" in MAIN


def test_compact_controls_override_old_large_sync_layout():
    assert "SweepyModv5.28: compact operator controls" in STYLES
    assert ".v520-sync-btn { display: none !important; }" in STYLES
    assert ".v526-pause-btn { grid-column: 3" in STYLES
