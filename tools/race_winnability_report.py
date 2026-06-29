#!/usr/bin/env python3
"""Offline race-winnability analysis (Phase 1, analysis-only).

Reads a finished career log and checks whether simple "field strength vs your
stats" signals separate the races you WON from the races you LOST. It changes
nothing about how the bot plays -- it only prints a report. The point is to find
out, on real data, whether a win-probability model is worth wiring into the
solver before we build anything bigger.

Two analyses:

  A) Player strength vs outcome -- needs only the career log. For each race it
     takes your stats at race time (the log already records these) and checks
     whether a strength score separates wins from losses, overall and per grade.

  B) Player-vs-rival gap -- needs data/single_mode_npc_core.json, produced by a
     master-data sync after this build (the new single_mode_npc exporter). For
     races where a named rival appeared, it compares your stats to that rival's
     actual stat block and checks whether the gap predicts the result.

"AUC" here is the probability that a randomly chosen WON race scored higher than
a randomly chosen LOST race. 0.50 = the signal tells you nothing; 0.70+ = a
useful separation; 1.00 = perfect. If Analysis A/B come back near 0.50, a
win-probability model probably is not worth building. If they are high, it is.

Usage:
    python tools/race_winnability_report.py <career_log.json> \
        [--npc data/single_mode_npc_core.json] \
        [--rivals data/rival_races_core.json] [--verbose]
"""
import argparse
import json
import os
import sys


def _load(path):
    with open(path, "r", encoding="utf-8") as fh:
        return json.load(fh)


def _race_results(log):
    rs = log.get("runner_status") if isinstance(log, dict) else None
    if isinstance(rs, dict) and rs.get("race_results"):
        return rs["race_results"]
    return (log or {}).get("race_results") or []


def _dist_bucket(distance_m):
    m = int(distance_m or 0)
    if m and m <= 1400:
        return "sprint", 0.30
    if m and m <= 1800:
        return "mile", 0.50
    if m and m <= 2400:
        return "medium", 0.70
    return "long", 1.00


def _scores(stats, distance_m):
    """Three candidate strength scores from a stat block."""
    spd = float(stats.get("speed") or 0)
    sta = float(stats.get("stamina") or 0)
    pwr = float(stats.get("power") or stats.get("pow") or 0)
    gut = float(stats.get("guts") or 0)
    wit = float(stats.get("wit") or stats.get("wiz") or 0)
    _, w_sta = _dist_bucket(distance_m)
    return {
        "total": spd + sta + pwr + gut + wit,
        "speed_power": spd + pwr,
        "dist_weighted": spd + 0.6 * pwr + w_sta * sta + 0.2 * gut + 0.2 * wit,
    }


def _auc(pairs):
    """pairs: list of (score, label) with label 1=win, 0=loss."""
    wins = [s for s, l in pairs if l == 1 and s is not None]
    losses = [s for s, l in pairs if l == 0 and s is not None]
    if not wins or not losses:
        return None, len(wins), len(losses)
    c = 0.0
    for w in wins:
        for l in losses:
            if w > l:
                c += 1.0
            elif w == l:
                c += 0.5
    return c / (len(wins) * len(losses)), len(wins), len(losses)


def _mean(xs):
    xs = [x for x in xs if x is not None]
    return sum(xs) / len(xs) if xs else None


def _fmt(x, nd=1):
    return "n/a" if x is None else f"{x:.{nd}f}"


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("log", help="career log JSON")
    here = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    ap.add_argument("--npc", default=os.path.join(here, "data", "single_mode_npc_core.json"))
    ap.add_argument("--rivals", default=os.path.join(here, "data", "rival_races_core.json"))
    ap.add_argument("--verbose", action="store_true", help="print a per-race table")
    args = ap.parse_args()

    log = _load(args.log)
    races = _race_results(log)
    if not races:
        print("No race_results found in this log. Use a finished-career log.")
        return 1

    # Optional competitor data.
    npc_by_id = {}
    rivals_by_program = {}
    npc_loaded = False
    if os.path.exists(args.npc):
        try:
            for n in _load(args.npc):
                npc_by_id[int(n.get("id") or 0)] = n
            npc_loaded = True
        except Exception as exc:
            print(f"(could not read {args.npc}: {exc})")
    if os.path.exists(args.rivals):
        try:
            for r in _load(args.rivals):
                pid = int(r.get("race_program_id") or 0)
                if pid:
                    rivals_by_program.setdefault(pid, []).append(r)
        except Exception:
            pass

    recs = []
    for r in races:
        rank = int(r.get("rank") or 99)
        won = 1 if rank == 1 else 0
        snap = r.get("stat_snapshot") or {}
        dist = r.get("distance_m")
        rec = {
            "turn": r.get("turn"),
            "name": r.get("name") or "",
            "grade": str(r.get("grade") or ""),
            "dist": dist,
            "bucket": _dist_bucket(dist)[0],
            "rank": rank,
            "won": won,
            "player": _scores(snap, dist),
            "rival_gap": None,
            "rival_name": "",
        }
        # Rival match: a named rival in this race whose NPC stats we have.
        prog = int(r.get("program_id") or 0)
        for rv in rivals_by_program.get(prog, []):
            npc = npc_by_id.get(int(rv.get("single_mode_npc_id") or 0))
            if npc:
                rsc = _scores(npc, dist)
                rec["rival_gap"] = {k: rec["player"][k] - rsc[k] for k in rsc}
                rec["rival_name"] = rv.get("rival_name") or npc.get("name") or ""
                break
        recs.append(rec)

    wins = [r for r in recs if r["won"]]
    losses = [r for r in recs if not r["won"]]
    print("=" * 70)
    print("RACE WINNABILITY REPORT")
    print("=" * 70)
    print(f"Races: {len(recs)}   Wins: {len(wins)}   Losses: {len(losses)}   "
          f"Win rate: {(100*len(wins)/len(recs)):.0f}%")
    print()

    # ---- Analysis A: player strength vs outcome ----
    print("ANALYSIS A - does YOUR strength separate wins from losses?")
    print("-" * 70)
    score_keys = ["total", "speed_power", "dist_weighted"]
    for key in score_keys:
        pairs = [(r["player"][key], r["won"]) for r in recs]
        a, nw, nl = _auc(pairs)
        mw = _mean([r["player"][key] for r in wins])
        ml = _mean([r["player"][key] for r in losses])
        print(f"  {key:13}  win avg {_fmt(mw):>8}   loss avg {_fmt(ml):>8}   AUC {_fmt(a,2)}")
    # per grade, using the best generic score
    print("\n  Win rate by grade (sample size in parens):")
    grades = {}
    for r in recs:
        grades.setdefault(r["grade"], []).append(r)
    for g, rr in sorted(grades.items()):
        w = sum(x["won"] for x in rr)
        print(f"    {g or '?':<8} {100*w/len(rr):3.0f}%  ({len(rr)})")

    # ---- Analysis B: player-vs-rival gap vs outcome ----
    print()
    print("ANALYSIS B - for RIVAL races, does (your stats - rival stats) predict the result?")
    print("-" * 70)
    if not npc_loaded:
        print("  Skipped: data/single_mode_npc_core.json not found.")
        print("  Run a master-data sync on this build first (it now exports")
        print("  single_mode_npc), then re-run this report.")
    else:
        rival_recs = [r for r in recs if r["rival_gap"] is not None]
        if not rival_recs:
            print("  No races in this log matched a known rival with NPC stats.")
        else:
            print(f"  Rival races matched: {len(rival_recs)} of {len(recs)}")
            for key in score_keys:
                pairs = [(r["rival_gap"][key], r["won"]) for r in rival_recs]
                a, nw, nl = _auc(pairs)
                # sign accuracy: positive gap -> predict win
                correct = sum(1 for r in rival_recs
                              if (r["rival_gap"][key] > 0) == bool(r["won"]))
                acc = 100 * correct / len(rival_recs)
                print(f"  gap[{key:13}]  AUC {_fmt(a,2)}   sign predicts result {acc:3.0f}% "
                      f"(wins={nw}, losses={nl})")

    if args.verbose:
        print("\nPER-RACE DETAIL")
        print("-" * 70)
        for r in sorted(recs, key=lambda x: (x["turn"] or 0)):
            gap = ""
            if r["rival_gap"] is not None:
                gap = f"  vs {r['rival_name']} gap(distw)={r['rival_gap']['dist_weighted']:+.0f}"
            outcome = "WON " if r["won"] else f"{r['rank']:>2}th"
            distw = r["player"]["dist_weighted"]
            print(f"  T{str(r['turn']):>3} {outcome} {r['grade']:<5} {r['bucket']:<6} "
                  f"distw={distw:.0f}  {r['name'][:26]}{gap}")

    print()
    print("How to read this: AUC ~0.50 means the signal does not separate wins")
    print("from losses (a model would not help). 0.70+ means it does (worth")
    print("wiring into the solver as an optional, gated race-preference nudge).")
    return 0


if __name__ == "__main__":
    sys.exit(main())
