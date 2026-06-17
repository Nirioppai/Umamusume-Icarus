import json
from copy import deepcopy
from pathlib import Path

from .presets import hydrate_preset, serialize_preset, slugify

SETTING_PRESET_KEYS = {
    "name",
    "scenario_id",
    "scenario",
    "training_stat_priority",
    "event_choice_stat_priority",
    "summer_stat_priority",
    "running_style",
    "race_strategy_by_distance",
    "preferred_distances",
    "preferred_surfaces",
    "event_overrides",
    "prioritize_event_energy",
    "event_energy_priority_multiplier",
    "event_stat_priority_bonus_by_rank",
    "mant_config",
    "selection",
}

SKILL_CONFIG_KEYS = {
    "enable_skill_point_check",
    "learn_skill_threshold",
    "enable_skill_point_check_plan",
    "pre_finals_enabled",
    "career_complete_enabled",
    "purchase_negative_skills",
    "skip_green_skills",
    "skip_red_skills",
    "skip_unique_skills",
    "show_only_selected_skills",
    "skill_spending_strategy",
    "skill_profile",
    "skill_strategy",
    "smart_skill_max_green_per_purchase",
    "smart_skill_yellow_bonus",
    "smart_skill_green_penalty",
    "smart_skill_min_score",
    "learn_skill_list",
    "learn_skill_blacklist",
}

SMART_SOLVER_KEYS = {
    "extra_race_list",
    "trackblazer_solver_settings",
    "trackblazer_manual_aptitudes",
    "trackblazer_manual_aptitudes_by_trainee",
    "trackblazer_solver_profiles",
    "trackblazer_weights",
    "trackblazer_target_epithets",
    "trackblazer_forced_epithets",
    "trackblazer_last_plan",
    "training_blocks",
    "manual_locks",
}

LEGACY_SETTINGS_PRESET_NAMES = {
    "fan farming",
    "maru fan farming",
    "oguri",
    "parent farming",
    "xguri",
    "xguri parent",
}


def _is_legacy_settings_preset(preset):
    """Return True for bundled legacy presets that v5.27 should not load.

    User-created presets are kept.  The comparison is intentionally strict on
    normalized names so we do not delete unrelated user presets that merely
    contain similar words.
    """
    return str((preset or {}).get("name") or "").strip().lower() in LEGACY_SETTINGS_PRESET_NAMES



def _read_json(path, default):
    try:
        if Path(path).exists():
            return json.loads(Path(path).read_text(encoding="utf-8"))
    except Exception:
        return deepcopy(default)
    return deepcopy(default)


def _write_json(path, payload):
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")


def _only_keys(data, keys):
    data = dict(data or {})
    return {k: deepcopy(v) for k, v in data.items() if k in keys}


def _default_settings_preset(name="Default"):
    return {
        "name": name,
        "scenario_id": 4,
        "training_stat_priority": ["speed", "power", "wit", "stamina", "guts"],
        "event_choice_stat_priority": ["speed", "power", "wit", "stamina", "guts"],
        "summer_stat_priority": ["speed", "power", "wit", "stamina", "guts"],
        "running_style": 1,
        "race_strategy_by_distance": {},
        "preferred_distances": [],
        "preferred_surfaces": [],
        "event_overrides": {},
        "mant_config": {},
        "selection": {},
    }


def _default_skill_config():
    return {
        "enable_skill_point_check": True,
        "learn_skill_threshold": 888,
        "enable_skill_point_check_plan": True,
        "pre_finals_enabled": False,
        "career_complete_enabled": False,
        "purchase_negative_skills": False,
        "skip_green_skills": False,
        "skip_red_skills": False,
        "skip_unique_skills": False,
        "show_only_selected_skills": False,
        "skill_spending_strategy": "best_skills_first",
        "skill_profile": "auto",
        "learn_skill_list": [],
        "learn_skill_blacklist": [],
        "smart_skill_max_green_per_purchase": 1,
        "smart_skill_yellow_bonus": 100,
        "smart_skill_green_penalty": 90,
        "smart_skill_min_score": 18,
        "skill_strategy": {
            "forced_skills": [],
            "blacklist": [],
            "manual_skill_weights": {},
            "running_style": "auto",
            "primary_distances": ["auto"],
            "secondary_distances": [],
            "track": "auto",
            "max_green_per_purchase": 1,
            "weights": {
                "recommended": 190,
                "community": 1,
                "yellow": 100,
                "green_penalty": 90,
                "style": 70,
                "distance": 75,
            },
        },
    }


def _default_solver_config():
    return {
        "extra_race_list": [],
        "trackblazer_solver_settings": {},
        "trackblazer_manual_aptitudes": {},
        "trackblazer_manual_aptitudes_by_trainee": {},
        "trackblazer_solver_profiles": [],
        "trackblazer_weights": {},
        "trackblazer_target_epithets": [],
        "trackblazer_forced_epithets": [],
        "trackblazer_last_plan": {},
        "training_blocks": [],
        "manual_locks": {},
    }


class ConfigStore:
    """Split config store used by the post-v5.8 UI.

    Runtime callers can still use read_one/read_all/write/delete as a PresetStore
    compatibility shim.  Settings presets live separately from skill and smart
    solver config on disk; read_one composes them back together for the runner.
    """

    def __init__(self, base_dir, userdata_dir=None):
        """v6.7.6: ``userdata_dir`` (optional) holds the active settings,
        skill, and solver JSON files.  When None, defaults to
        ``<base_dir>/data`` (the legacy in-build location).  When set, the
        settings/skill/solver/preset files persist outside the build folder
        so SweepyCL version upgrades don't blow away saved presets.
        ``base_dir`` is still used as the source for default templates and
        the legacy preset migration path.
        """
        self.base_dir = Path(base_dir)
        if userdata_dir and str(userdata_dir) != str(base_dir):
            self.data_dir = Path(userdata_dir) / "data"
        else:
            self.data_dir = self.base_dir / "data"
        self.data_dir.mkdir(parents=True, exist_ok=True)
        self.settings_path = self.data_dir / "settings_presets.json"
        self.skill_path = self.data_dir / "skill_config.json"
        self.solver_path = self.data_dir / "smart_solver_config.json"
        # Migration source is the legacy in-build location.  v6.7.6
        # additionally migrates from in-build data/ -> userdata data/ on
        # first run, so an upgrade can pick up the previous version's
        # settings_presets.json automatically.
        self.legacy_preset_dir = self.base_dir / "data" / "presets"
        self._maybe_migrate_from_build()
        self.migrate_legacy_presets()
        self._ensure_files()

    def _maybe_migrate_from_build(self):
        """One-way migration from in-build data/ to userdata/ data/ on
        first start of a new version.  No-op when data_dir is the
        in-build location (no migration needed) or when destination
        already exists (user customized it)."""
        src_data = self.base_dir / "data"
        if self.data_dir == src_data or not src_data.exists():
            return
        for name in ("settings_presets.json", "skill_config.json", "smart_solver_config.json"):
            src = src_data / name
            dst = self.data_dir / name
            if src.exists() and not dst.exists():
                try:
                    dst.write_bytes(src.read_bytes())
                except Exception:
                    pass

    def _ensure_files(self):
        if not self.settings_path.exists():
            _write_json(self.settings_path, {"active": "Default", "presets": [_default_settings_preset()]})
        if not self.skill_path.exists():
            _write_json(self.skill_path, _default_skill_config())
        if not self.solver_path.exists():
            _write_json(self.solver_path, _default_solver_config())

    def migrate_legacy_presets(self):
        if not self.legacy_preset_dir.exists():
            return {"migrated": False, "reason": "no legacy preset directory"}
        settings_payload = _read_json(self.settings_path, {"active": "", "presets": []})
        settings_by_name = {str(p.get("name", "")).lower(): p for p in settings_payload.get("presets", []) if p.get("name")}
        first_skill = None
        first_solver = None
        migrated = 0
        for path in sorted(self.legacy_preset_dir.glob("*.json")):
            try:
                raw = json.loads(path.read_text(encoding="utf-8"))
            except Exception:
                continue
            hydrated = hydrate_preset(raw)
            settings = _default_settings_preset(hydrated.get("name") or path.stem)
            settings.update(_only_keys(hydrated, SETTING_PRESET_KEYS))
            settings["name"] = settings.get("name") or path.stem
            settings_by_name[settings["name"].lower()] = settings
            if first_skill is None:
                first_skill = _default_skill_config()
                first_skill.update(_only_keys(hydrated, SKILL_CONFIG_KEYS))
                strat = dict(first_skill.get("skill_strategy") or {})
                strat.setdefault("forced_skills", ((hydrated.get("learn_skill_list") or [[]])[0] if hydrated.get("learn_skill_list") else []))
                strat.setdefault("blacklist", hydrated.get("learn_skill_blacklist") or [])
                first_skill["skill_strategy"] = strat
            if first_solver is None:
                first_solver = _default_solver_config()
                first_solver.update(_only_keys(hydrated, SMART_SOLVER_KEYS))
            try:
                path.unlink()
            except Exception:
                pass
            migrated += 1
        settings_payload["presets"] = sorted(settings_by_name.values(), key=lambda p: str(p.get("name", "")).lower())
        if not settings_payload.get("active") and settings_payload["presets"]:
            settings_payload["active"] = settings_payload["presets"][0].get("name", "")
        _write_json(self.settings_path, settings_payload)
        if first_skill:
            self.save_skill_config(first_skill)
        if first_solver:
            self.save_solver_config(first_solver)
        try:
            if not any(self.legacy_preset_dir.iterdir()):
                self.legacy_preset_dir.rmdir()
        except Exception:
            pass
        return {"migrated": True, "count": migrated}

    def read_settings_presets(self):
        payload = _read_json(self.settings_path, {"active": "", "presets": []})
        changed = False
        presets = []
        for p in payload.get("presets", []):
            if _is_legacy_settings_preset(p):
                changed = True
                continue
            clean = _default_settings_preset(p.get("name") or "Default")
            clean.update(_only_keys(p, SETTING_PRESET_KEYS))
            presets.append(clean)

        active = str(payload.get("active") or "").strip()
        if active.lower() in LEGACY_SETTINGS_PRESET_NAMES:
            active = ""
            changed = True

        payload = {"active": active or (presets[0]["name"] if presets else ""), "presets": presets}
        if not payload["presets"]:
            payload["presets"] = [_default_settings_preset()]
            payload["active"] = "Default"
            changed = True
        elif not any(str(p.get("name", "")).lower() == str(payload["active"]).lower() for p in payload["presets"]):
            payload["active"] = payload["presets"][0]["name"]
            changed = True

        if changed:
            _write_json(self.settings_path, payload)
        return payload

    def save_settings_preset(self, preset):
        payload = self.read_settings_presets()
        clean = _default_settings_preset(str((preset or {}).get("name") or payload.get("active") or "Settings Preset").strip())
        clean.update(_only_keys(preset, SETTING_PRESET_KEYS))
        clean["name"] = slugify(clean.get("name") or "Settings Preset")
        presets = [p for p in payload.get("presets", []) if str(p.get("name", "")).lower() != clean["name"].lower()]
        presets.append(clean)
        payload["presets"] = sorted(presets, key=lambda p: p.get("name", "").lower())
        payload["active"] = clean["name"]
        _write_json(self.settings_path, payload)
        return clean

    def delete_settings_preset(self, name):
        payload = self.read_settings_presets()
        payload["presets"] = [p for p in payload.get("presets", []) if str(p.get("name", "")).lower() != str(name or "").lower()]
        payload["active"] = payload["presets"][0]["name"] if payload["presets"] else ""
        if not payload["presets"]:
            payload["presets"] = [_default_settings_preset()]
            payload["active"] = "Default"
        _write_json(self.settings_path, payload)
        return True

    def read_skill_config(self):
        cfg = _default_skill_config()
        loaded = _read_json(self.skill_path, {})
        cfg.update(_only_keys(loaded, SKILL_CONFIG_KEYS))
        strat = _default_skill_config()["skill_strategy"]
        strat.update(dict(cfg.get("skill_strategy") or {}))
        strat["weights"] = {**_default_skill_config()["skill_strategy"]["weights"], **dict(strat.get("weights") or {})}
        cfg["skill_strategy"] = strat
        return cfg

    def save_skill_config(self, config):
        cfg = self.read_skill_config()
        cfg.update(_only_keys(config, SKILL_CONFIG_KEYS))
        if "skill_strategy" in (config or {}):
            strat = dict(cfg.get("skill_strategy") or {})
            incoming = dict(config.get("skill_strategy") or {})
            strat.update(incoming)
            strat["weights"] = {**_default_skill_config()["skill_strategy"]["weights"], **dict(strat.get("weights") or {})}
            cfg["skill_strategy"] = strat
        _write_json(self.skill_path, cfg)
        return cfg

    def read_solver_config(self):
        cfg = _default_solver_config()
        cfg.update(_only_keys(_read_json(self.solver_path, {}), SMART_SOLVER_KEYS))
        return cfg

    def save_solver_config(self, config):
        cfg = self.read_solver_config()
        cfg.update(_only_keys(config, SMART_SOLVER_KEYS))
        _write_json(self.solver_path, cfg)
        return cfg

    def compose_runtime_preset(self, name=None):
        settings_payload = self.read_settings_presets()
        wanted = str(name or settings_payload.get("active") or "").lower()
        settings = next((p for p in settings_payload["presets"] if p.get("name", "").lower() == wanted), None)
        settings = settings or settings_payload["presets"][0]
        runtime = hydrate_preset(settings)
        runtime.update(self.read_skill_config())
        runtime.update(self.read_solver_config())
        runtime["name"] = settings.get("name") or runtime.get("name") or "runtime"
        return runtime

    # PresetStore-compatible methods.
    def read_all(self):
        return [self.compose_runtime_preset(p.get("name")) for p in self.read_settings_presets().get("presets", [])]

    def read_one(self, name):
        wanted = str(name or "").strip().lower()
        if not wanted:
            return self.compose_runtime_preset(None)
        for p in self.read_settings_presets().get("presets", []):
            if str(p.get("name", "")).lower() == wanted:
                return self.compose_runtime_preset(p.get("name"))
        return None

    def write(self, preset):
        settings = self.save_settings_preset(preset)
        self.save_skill_config(preset)
        self.save_solver_config(preset)
        return self.compose_runtime_preset(settings.get("name"))

    def delete(self, name):
        return self.delete_settings_preset(name)
