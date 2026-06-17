#!/usr/bin/env python3
"""v6.5 -- Training-scorer backtest against historical career logs.

Reality-check tool for evaluating whether to promote the v6.1 scorer to
``authoritative`` mode for a given character profile.  Reads existing
career_log_*.json files, extracts the training command executed at each
turn, tallies them by stat, and compares the distribution against the
v6.1 scorer's stat priority for the active profile.

This is a *data-only* backtest -- the career log doesn't store the full
``home_info.command_info_array`` per turn, so we can't actually replay
``score_trainings()`` and check which command_id the scorer would have
picked.  What we CAN do is observe the strategy engine's training
distribution and ask: "given the active profile's stat priority, is the
strategy training the right stats in the right proportion?"

A run that's well-aligned with the profile shows a training distribution
that mostly matches the priority order -- top-priority stat trained most,
bottom-priority stat trained least.  A misaligned run shows under-priority
stats being over-trained, which is the signal that promoting the v6.1
scorer to authoritative would change behavior in a meaningful way.

Usage
-----

    # Single log:
    python scripts/backtest_training_scorer.py /path/to/career_log.json

    # Directory of logs:
    python scripts/backtest_training_scorer.py /path/to/bot_logs/

    # Filter by trainee:
    python scripts/backtest_training_scorer.py /path/to/bot_logs/ --trainee "Oguri Cap"

    # CSV output for spreadsheet analysis:
    python scripts/backtest_training_scorer.py /path/to/bot_logs/ --csv out.csv
"""

from __future__ import annotations

import argparse
import csv
import json
import sys
from collections import Counter
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple


# Standard Umamusume command_id -> stat mapping.  Matches the convention
# in career_bot/runner.py::TRAINING_LABELS exactly.  v6.7.2 fix: earlier
# versions of this script had wrong mappings (assumed 102=Stamina,
# 105=Wit) and would mis-categorize every training in the histogram.
COMMAND_TO_STAT: Dict[int, str] = {
    101: "speed",
    102: "power",
    103: "guts",
    105: "stamina",
    106: "wit",
    # Summer-camp variants
    601: "speed",
    602: "stamina",
    603: "power",
    604: "guts",
    605: "wit",
}

# Pretty labels for output
STAT_ORDER = ["speed", "stamina", "power", "guts", "wit"]


# --------------------------------------------------------------------------
# Data extraction from a single career log
# --------------------------------------------------------------------------


@dataclass
class RunSummary:
    """One backtest result row -- per career_log file."""
    path: str
    trainee_name: str = ""
    card_id: int = 0
    chara_id: int = 0
    scenario_id: int = 0
    preset_name: str = ""
    final_turn: int = 0
    status: str = ""
    final_stats: Dict[str, int] = field(default_factory=dict)
    final_rating: int = 0
    final_fans: int = 0
    training_counts: Counter = field(default_factory=Counter)
    total_trainings: int = 0
    profile_id: str = ""
    profile_derivation: str = ""
    profile_stat_priority: List[str] = field(default_factory=list)
    alignment_score: float = 0.0
    over_trained: List[str] = field(default_factory=list)
    under_trained: List[str] = field(default_factory=list)


def _extract_trainee_from_api_calls(turns: List[Dict[str, Any]]) -> Tuple[int, int, str]:
    """Walk api_calls looking for chara_info or card data; returns
    (card_id, chara_id, display_name).  chara_info comes back in RES
    payloads of check_event / exec_command / finish, nested under
    ``response`` or directly in ``data``."""
    for turn in turns:
        for call in turn.get("api_calls") or []:
            if call.get("direction") != "RES":
                continue
            d = call.get("data") or {}
            if not isinstance(d, dict):
                continue
            payload = d.get("response") or d
            ch = payload.get("chara_info") if isinstance(payload, dict) else None
            if isinstance(ch, dict):
                card_id = int(ch.get("card_id") or 0)
                chara_id = int(ch.get("chara_id") or 0)
                for name_key in ("trained_chara_name", "chara_name", "name"):
                    name = ch.get(name_key)
                    if isinstance(name, str) and name.strip():
                        return card_id, chara_id, name.strip()
                if card_id or chara_id:
                    return card_id, chara_id, ""
    return 0, 0, ""


def _extract_command_ids_executed(turns: List[Dict[str, Any]]) -> List[Tuple[int, int]]:
    """Return [(turn_number, command_id)] for every training command
    executed (command_type == 1)."""
    out: List[Tuple[int, int]] = []
    for turn in turns:
        turn_no = int(turn.get("turn") or 0)
        for call in turn.get("api_calls") or []:
            if call.get("direction") != "REQ":
                continue
            if "exec_command" not in str(call.get("endpoint") or ""):
                continue
            d = call.get("data") or {}
            if not isinstance(d, dict):
                continue
            # The exec_command payload is nested under "payload"
            payload = d.get("payload") if isinstance(d.get("payload"), dict) else d
            if int(payload.get("command_type") or 0) != 1:
                continue
            cmd_id = int(payload.get("command_id") or 0)
            if cmd_id in COMMAND_TO_STAT:
                out.append((turn_no, cmd_id))
                break  # one training command per turn max
    return out


def _final_stats(turns: List[Dict[str, Any]]) -> Tuple[Dict[str, int], int, int]:
    """Return (stat_dict, rating, fans) pulled from the last turn that has them."""
    for turn in reversed(turns):
        stats = turn.get("stats") or {}
        if isinstance(stats, dict) and stats:
            normalized = {
                "speed":   int(stats.get("speed") or 0),
                "stamina": int(stats.get("stamina") or 0),
                "power":   int(stats.get("power") or 0),
                "guts":    int(stats.get("guts") or 0),
                "wit":     int(stats.get("wit") or stats.get("wiz") or 0),
            }
            rating = int(stats.get("rating") or stats.get("evaluation_value") or 0)
            fans = int(stats.get("fans") or stats.get("fan_num") or 0)
            return normalized, rating, fans
    return {s: 0 for s in STAT_ORDER}, 0, 0


# --------------------------------------------------------------------------
# Alignment scoring
# --------------------------------------------------------------------------


def _expected_distribution(stat_priority: List[str], total: int) -> Dict[str, float]:
    """Expected training count per stat given a priority order.

    Uses a simple decaying weight: priority[0] gets 5/15ths of trainings,
    priority[1] gets 4/15ths, ..., priority[4] gets 1/15th.  This is a
    rough prior -- a real scorer-driven distribution wouldn't follow this
    exactly (failure rates, support card placement, and stat caps all
    shift it) -- but it's a useful baseline to detect gross misalignment.
    """
    if not stat_priority or total <= 0:
        return {s: 0.0 for s in STAT_ORDER}
    weights = [5, 4, 3, 2, 1][:len(stat_priority)]
    total_weight = sum(weights)
    out = {s: 0.0 for s in STAT_ORDER}
    for stat, w in zip(stat_priority, weights):
        out[stat] = total * (w / total_weight)
    return out


def _alignment(actual: Counter, expected: Dict[str, float]) -> Tuple[float, List[str], List[str]]:
    """Compute a 0..1 alignment score using L1 distance against expected
    distribution.  Returns (score, over_trained_stats, under_trained_stats).

    Over-trained: actual count > expected by > 25% AND > 2 trainings.
    Under-trained: actual count < expected by > 25% AND expected > 4.
    """
    total = sum(actual.values()) or 1
    expected_total = sum(expected.values()) or 1
    l1_distance = 0.0
    over: List[str] = []
    under: List[str] = []
    for stat in STAT_ORDER:
        a_norm = actual.get(stat, 0) / total
        e_norm = expected.get(stat, 0.0) / expected_total
        l1_distance += abs(a_norm - e_norm)
        actual_count = actual.get(stat, 0)
        expected_count = expected.get(stat, 0.0)
        if expected_count > 0:
            ratio = actual_count / expected_count
            if ratio > 1.25 and actual_count > 2:
                over.append(stat)
            elif ratio < 0.75 and expected_count > 4:
                under.append(stat)
    # L1 distance ranges 0..2; normalize to 0..1 score (1 = perfect)
    score = max(0.0, 1.0 - (l1_distance / 2.0))
    return score, over, under


# --------------------------------------------------------------------------
# Per-log backtest
# --------------------------------------------------------------------------


def backtest_one_log(path: Path, base_dir: Path) -> Optional[RunSummary]:
    try:
        with path.open("r", encoding="utf-8") as f:
            data = json.load(f)
    except (OSError, json.JSONDecodeError) as exc:
        print(f"  skipped {path.name}: {exc}", file=sys.stderr)
        return None

    turns = data.get("turns") or []
    if not turns:
        return None

    card_id, chara_id, name = _extract_trainee_from_api_calls(turns)
    cmd_ids = _extract_command_ids_executed(turns)
    counts: Counter = Counter()
    for _, cid in cmd_ids:
        stat = COMMAND_TO_STAT.get(cid)
        if stat:
            counts[stat] += 1

    stats, rating, fans = _final_stats(turns)
    scenario_id = int(data.get("scenario_id") or 0)
    preset_name = str(data.get("preset_name") or "")

    # Resolve the active profile for this trainee
    from career_bot import character_profiles
    profile = character_profiles.resolve_profile(
        card_id=card_id, chara_id=chara_id, scenario_id=scenario_id,
        base_dir=base_dir, preset_name=preset_name,
        chara_info={"trained_chara_name": name} if name else None,
    )
    priority = profile.training_scorer_overrides.get("stat_priority") or list(STAT_ORDER)
    expected = _expected_distribution(priority, sum(counts.values()))
    alignment, over, under = _alignment(counts, expected)

    return RunSummary(
        path=str(path),
        trainee_name=name,
        card_id=card_id,
        chara_id=chara_id,
        scenario_id=scenario_id,
        preset_name=preset_name,
        final_turn=int(data.get("final_turn") or 0),
        status=str(data.get("status") or ""),
        final_stats=stats,
        final_rating=rating,
        final_fans=fans,
        training_counts=counts,
        total_trainings=sum(counts.values()),
        profile_id=profile.profile_id,
        profile_derivation=profile.derivation,
        profile_stat_priority=list(priority),
        alignment_score=alignment,
        over_trained=over,
        under_trained=under,
    )


# --------------------------------------------------------------------------
# Reporting
# --------------------------------------------------------------------------


def _print_run(summary: RunSummary) -> None:
    print(f"\n=== {Path(summary.path).name} ===")
    print(f"  trainee: {summary.trainee_name or '?'} (card_id={summary.card_id}, chara_id={summary.chara_id})")
    print(f"  scenario: {summary.scenario_id}  preset: {summary.preset_name}  turns: {summary.final_turn}  status: {summary.status}")
    print(f"  profile: {summary.profile_id} ({summary.profile_derivation})  priority: {summary.profile_stat_priority}")
    print(f"  final stats: " + " ".join(f"{k.title()}={summary.final_stats.get(k, 0)}" for k in STAT_ORDER))
    print(f"  rating: {summary.final_rating}  fans: {summary.final_fans}")
    print(f"  training counts ({summary.total_trainings} total):")
    for stat in STAT_ORDER:
        count = summary.training_counts.get(stat, 0)
        pct = (count / summary.total_trainings * 100) if summary.total_trainings else 0
        bar = "#" * int(pct / 3)
        flag = ""
        if stat in summary.over_trained: flag = "  [OVER]"
        elif stat in summary.under_trained: flag = "  [UNDER]"
        print(f"    {stat.title():8s} {count:3d}  {pct:5.1f}%  {bar}{flag}")
    print(f"  alignment score: {summary.alignment_score:.3f}  (1.0 = perfect match to priority)")
    if summary.over_trained:
        print(f"    over-trained vs priority:  {', '.join(summary.over_trained)}")
    if summary.under_trained:
        print(f"    under-trained vs priority: {', '.join(summary.under_trained)}")


def _print_aggregate(summaries: List[RunSummary]) -> None:
    if not summaries:
        return
    print("\n" + "=" * 70)
    print("AGGREGATE ACROSS ALL RUNS")
    print("=" * 70)
    by_profile: Dict[str, List[RunSummary]] = {}
    for s in summaries:
        by_profile.setdefault(s.profile_id, []).append(s)

    for profile_id, group in sorted(by_profile.items()):
        print(f"\n  Profile: {profile_id}  ({len(group)} run(s))")
        print(f"    priority: {group[0].profile_stat_priority}")
        avg_alignment = sum(s.alignment_score for s in group) / len(group)
        avg_rating = sum(s.final_rating for s in group) / len(group)
        avg_fans = sum(s.final_fans for s in group) / len(group)
        avg_turns = sum(s.final_turn for s in group) / len(group)
        print(f"    avg alignment: {avg_alignment:.3f}  avg rating: {avg_rating:.0f}  avg fans: {avg_fans:.0f}  avg turns: {avg_turns:.1f}")

        # Aggregate training distribution
        total_counts: Counter = Counter()
        for s in group:
            total_counts.update(s.training_counts)
        total = sum(total_counts.values()) or 1
        print(f"    aggregate training distribution:")
        for stat in STAT_ORDER:
            pct = total_counts.get(stat, 0) / total * 100
            print(f"      {stat.title():8s} {pct:5.1f}%")

        over_freq = Counter()
        under_freq = Counter()
        for s in group:
            over_freq.update(s.over_trained)
            under_freq.update(s.under_trained)
        if over_freq:
            print(f"    consistently over-trained across runs: {dict(over_freq)}")
        if under_freq:
            print(f"    consistently under-trained across runs: {dict(under_freq)}")


def _emit_csv(summaries: List[RunSummary], csv_path: Path) -> None:
    fieldnames = [
        "path", "trainee_name", "card_id", "chara_id", "scenario_id", "preset_name",
        "final_turn", "status", "profile_id", "profile_derivation",
        "profile_stat_priority", "total_trainings", "alignment_score",
        "over_trained", "under_trained",
        "speed_train", "stamina_train", "power_train", "guts_train", "wit_train",
        "speed_final", "stamina_final", "power_final", "guts_final", "wit_final",
        "final_rating", "final_fans",
    ]
    with csv_path.open("w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        for s in summaries:
            row = {
                "path": s.path,
                "trainee_name": s.trainee_name,
                "card_id": s.card_id,
                "chara_id": s.chara_id,
                "scenario_id": s.scenario_id,
                "preset_name": s.preset_name,
                "final_turn": s.final_turn,
                "status": s.status,
                "profile_id": s.profile_id,
                "profile_derivation": s.profile_derivation,
                "profile_stat_priority": " ".join(s.profile_stat_priority),
                "total_trainings": s.total_trainings,
                "alignment_score": round(s.alignment_score, 4),
                "over_trained": " ".join(s.over_trained),
                "under_trained": " ".join(s.under_trained),
                "final_rating": s.final_rating,
                "final_fans": s.final_fans,
            }
            for stat in STAT_ORDER:
                row[f"{stat}_train"] = s.training_counts.get(stat, 0)
                row[f"{stat}_final"] = s.final_stats.get(stat, 0)
            writer.writerow(row)
    print(f"\nCSV written to {csv_path}")


# --------------------------------------------------------------------------
# CLI
# --------------------------------------------------------------------------


def _collect_log_paths(target: Path) -> List[Path]:
    if target.is_file():
        return [target] if target.suffix == ".json" else []
    if target.is_dir():
        return sorted(target.glob("career_log_*.json"))
    return []


def main() -> int:
    parser = argparse.ArgumentParser(description="Backtest the v6.1 training scorer against historical career logs.")
    parser.add_argument("target", help="Path to a career_log_*.json file OR directory containing such files")
    parser.add_argument("--trainee", help="Filter to runs of this trainee (substring match on name)", default=None)
    parser.add_argument("--scenario", type=int, help="Filter by scenario_id", default=None)
    parser.add_argument("--csv", help="Write per-run results to this CSV path", default=None)
    parser.add_argument("--quiet", action="store_true", help="Skip per-run printout, only show aggregate")
    args = parser.parse_args()

    target = Path(args.target).expanduser().resolve()
    log_paths = _collect_log_paths(target)
    if not log_paths:
        print(f"No career_log_*.json files found under {target}", file=sys.stderr)
        return 1
    print(f"Found {len(log_paths)} log(s) under {target}")

    # The base_dir for profile resolution is the project root, which is the
    # parent of scripts/.
    base_dir = Path(__file__).resolve().parent.parent
    sys.path.insert(0, str(base_dir))

    summaries: List[RunSummary] = []
    for path in log_paths:
        summary = backtest_one_log(path, base_dir)
        if summary is None:
            continue
        if args.trainee and args.trainee.lower() not in summary.trainee_name.lower():
            continue
        if args.scenario is not None and summary.scenario_id != args.scenario:
            continue
        summaries.append(summary)
        if not args.quiet:
            _print_run(summary)

    _print_aggregate(summaries)
    if args.csv:
        _emit_csv(summaries, Path(args.csv).expanduser().resolve())

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
