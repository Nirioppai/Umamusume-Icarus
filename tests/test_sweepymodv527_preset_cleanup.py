import json
from pathlib import Path

from career_bot.config_store import ConfigStore

ROOT = Path(__file__).resolve().parents[1]
MAIN = (ROOT / "main.py").read_text(encoding="utf-8")
APP = (ROOT / "public" / "app.js").read_text(encoding="utf-8")
BUNDLED_SETTINGS = json.loads((ROOT / "data" / "settings_presets.json").read_text(encoding="utf-8"))


LEGACY_NAMES = {
    "fan farming",
    "maru fan farming",
    "oguri",
    "parent farming",
    "xguri",
    "xguri parent",
}


def test_bundled_settings_presets_are_neutral_default_only():
    assert BUNDLED_SETTINGS["active"] == "Default"
    assert [p["name"] for p in BUNDLED_SETTINGS["presets"]] == ["Default"]


def test_config_store_filters_legacy_presets_and_rewrites_active(tmp_path):
    data_dir = tmp_path / "data"
    data_dir.mkdir()
    (data_dir / "settings_presets.json").write_text(json.dumps({
        "active": "xguri parent",
        "presets": [
            {"name": "Fan Farming"},
            {"name": "Custom Keep", "running_style": 3},
            {"name": "Oguri"},
            {"name": "xguri parent"},
        ],
    }), encoding="utf-8")

    store = ConfigStore(tmp_path)
    payload = store.read_settings_presets()

    names = [p["name"] for p in payload["presets"]]
    assert names == ["Custom Keep"]
    assert payload["active"] == "Custom Keep"
    persisted = json.loads((data_dir / "settings_presets.json").read_text(encoding="utf-8"))
    assert [p["name"] for p in persisted["presets"]] == ["Custom Keep"]


def test_main_no_longer_uses_xguri_parent_fallback_and_imports_crash_root():
    assert "xguri parent" not in MAIN
    assert "from career_bot.runner import CareerRunner, runtime_output_root" in MAIN


def test_frontend_respects_backend_active_and_labels_solver_macro():
    assert "const serverActive = res.active ||" in APP
    assert "Optimization Weight Preset" in APP
    assert "UI macro that adjusts the solver scoring weights" in APP
