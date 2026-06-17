"""Recommended stat build helpers.

Generated from Game8 guide data when available. Missing character-specific data
falls back to the default balanced target.
"""
from __future__ import annotations

import json
import re
from pathlib import Path

DEFAULT_RECOMMENDED_STATS = {
    "Speed": 1200,
    "Stamina": 600,
    "Power": 1200,
    "Guts": 600,
    "Wit": 1200,
}


def _norm(value):
    return re.sub(r"[^a-z0-9]+", "", str(value or "").lower())


def load_recommended_stats(base_dir):
    path = Path(base_dir) / "data" / "recommended_stat_builds.json"
    if not path.exists():
        return {}
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
        return data if isinstance(data, dict) else {}
    except Exception:
        return {}


def get_recommended_stats(base_dir, trainee_name):
    builds = load_recommended_stats(base_dir)
    if trainee_name in builds:
        return dict(builds[trainee_name])

    wanted = _norm(trainee_name)
    for name, stats in builds.items():
        key = _norm(name)
        if wanted and (wanted == key or wanted in key or key in wanted):
            return dict(stats)

    return dict(DEFAULT_RECOMMENDED_STATS)
