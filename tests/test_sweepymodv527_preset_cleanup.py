import json
from pathlib import Path

from career_bot.config_store import ConfigStore

ROOT = Path(__file__).resolve().parents[1]
MAIN = (ROOT / "main.py").read_text(encoding="utf-8")
APP = (ROOT / "public" / "app.js").read_text(encoding="utf-8")
# v7.6: the bundled monolithic data/settings_presets.json was replaced by a
# per-file preset store (data/presets/<slug>.json) plus an active pointer at
# data/active_preset.json. The "ships neutral, Default-only" intent is now
# expressed by those files.
BUNDLED_ACTIVE = json.loads((ROOT / "data" / "active_preset.json").read_text(encoding="utf-8"))
BUNDLED_PRESET_FILES = sorted((ROOT / "data" / "presets").glob("*.json"))


LEGACY_NAMES = {
    "fan farming",
    "maru fan farming",
    "oguri",
    "parent farming",
    "xguri",
    "xguri parent",
}


def test_bundled_settings_presets_are_neutral_default_only():
    assert BUNDLED_ACTIVE["active"] == "Default"
    names = [json.loads(p.read_text(encoding="utf-8")).get("name") for p in BUNDLED_PRESET_FILES]
    assert names == ["Default"]


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
    # v7.6: legacy presets are migrated into the per-file preset store under
    # data/presets/ and the legacy monolithic settings_presets.json is backed
    # up to *.premigrate.bak rather than rewritten in place.
    persisted = sorted(
        json.loads(p.read_text(encoding="utf-8")).get("name")
        for p in (data_dir / "presets").glob("*.json")
    )
    assert persisted == ["Custom Keep"]
    assert not (data_dir / "settings_presets.json").exists()
    assert (data_dir / "settings_presets.json.premigrate.bak").exists()


def test_main_no_longer_uses_xguri_parent_fallback_and_imports_crash_root():
    assert "xguri parent" not in MAIN
    assert "from career_bot.runner import CareerRunner, runtime_output_root" in MAIN


def test_frontend_respects_backend_active_and_labels_solver_macro():
    assert "const serverActive = res.active ||" in APP
    assert "Optimization Weight Preset" in APP
    assert "UI macro that adjusts the solver scoring weights" in APP
