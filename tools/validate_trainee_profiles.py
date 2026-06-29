#!/usr/bin/env python3
"""Validate trainee profile coverage and Trackblazer usability.

Run:
  python tools/validate_trainee_profiles.py --root .
"""
from __future__ import annotations

import argparse
import json
from pathlib import Path

RANK_VALUE = {"S": 8, "A": 7, "B": 6, "C": 5, "D": 4, "E": 3, "F": 2, "G": 1}

REQUIRED = ["track_aptitude", "distance_aptitude", "style_aptitude", "recommended_style", "primary_distances"]


def load_json(path: Path):
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        return {}


def trackblazer_usable(profile):
    dist = profile.get("distance_aptitude") or {}
    track = profile.get("track_aptitude") or {}
    has_distance = any(RANK_VALUE.get(str(dist.get(k, "G")).upper(), 0) >= 6 for k in ["sprint", "mile", "medium", "long"])
    has_surface = any(RANK_VALUE.get(str(track.get(k, "G")).upper(), 0) >= 6 for k in ["turf", "dirt"])
    return has_distance and has_surface


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--root", default=".")
    args = ap.parse_args()
    root = Path(args.root)
    generated = load_json(root / "data" / "trainee_skill_profiles.generated.json")
    manual = load_json(root / "data" / "trainee_skill_profiles.json")
    merged = dict(generated)
    merged.update(manual)

    rows = []
    for name, profile in sorted(merged.items()):
        if name == "__fallback__":
            continue
        missing = [key for key in REQUIRED if key not in profile]
        rows.append({
            "name": name,
            "source": profile.get("profile_source") or profile.get("source") or "unknown",
            "missing": missing,
            "trackblazer_usable": trackblazer_usable(profile),
            "primary_distances": profile.get("primary_distances") or [],
            "recommended_style": profile.get("recommended_style") or profile.get("running_style") or "",
        })

    report = {
        "profile_count": len(rows),
        "trackblazer_usable_count": sum(1 for row in rows if row["trackblazer_usable"]),
        "profiles": rows,
    }
    out = root / "data" / "trainee_skill_profiles.validation.json"
    out.write_text(json.dumps(report, indent=2, ensure_ascii=False), encoding="utf-8")
    print(f"Profiles: {report['profile_count']}")
    print(f"Trackblazer usable: {report['trackblazer_usable_count']}")
    print(f"Wrote {out}")


if __name__ == "__main__":
    main()
