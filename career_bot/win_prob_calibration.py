"""Automatic win-probability self-calibration (no manual report runs).

Turns the manual loop -- run a career, run tools/race_winnability_report.py, read
the best-fit logistic scale k, hand-edit DEFAULT_K -- into an automatic
on-career-finish process:

  * After each career the runner appends that career's MODELLED races (the ones
    with a known named-rival field) to a rolling observation store.
  * It re-fits k (Brier-minimising over a grid) on ALL stored observations and
    computes whole-field strength->finish concordance from race_scenario data.
  * It writes a calibration file; the win-probability model auto-loads the fitted
    k for the live ~P(win) estimate once enough races have accrued AND the fit
    actually beats the predict-the-base-rate baseline.

So the model self-tunes from real play with zero manual steps. READ-ONLY w.r.t.
gameplay: it only reads finished-race records and writes analytics files under
uma_runtime/ (build-excluded). It never changes how the bot trains or races.
"""
from __future__ import annotations

import json
import os
import time

from career_bot import win_probability as wp

_MIN_RACES = 25            # below this keep DEFAULT_K (too little signal to trust a fit)
_MAX_OBS = 2000            # rolling cap on stored observations
_K_GRID = [50, 75, 100, 125, 150, 175, 200, 250, 300, 400, 500]


def _dir(base_dir):
    return os.path.join(str(base_dir), "uma_runtime", "win_prob")


def _obs_path(base_dir):
    return os.path.join(_dir(base_dir), "observations.jsonl")


def calibration_path(base_dir):
    return os.path.join(_dir(base_dir), "calibration.json")


def _ground_from_row(r):
    perf = r.get("performance_hint") or {}
    label = str(perf.get("surface_label") or r.get("terrain") or "").lower()
    return 2 if label.startswith("dirt") else 1


def observations_from_career(race_results, model, card_id=0, chara_id=None):
    """Compact calibration observations from one career's race_results.

    Each MODELLED (named-rival) race -> {s_t, opp:[...], won}; that needs the rival
    field, which old logs may lack. Whole-field concordance ({field:[[str,finish]..]})
    is captured INDEPENDENTLY whenever race_scenario field_results were logged, so a
    career still contributes data even when the named-rival model can't run.

    `chara_id` (the base chara) may be passed directly (e.g. backfill reads it from a
    log); otherwise it's derived from card_id.
    """
    cid = int(chara_id) if chara_id else wp.chara_id_from_card(card_id)
    out = []
    for r in race_results or []:
        if not isinstance(r, dict):
            continue
        perf = r.get("performance_hint") or {}
        obs = None
        try:
            res = model.compute(
                stats=r.get("stat_snapshot") or {}, distance_m=r.get("distance_m"),
                ground=_ground_from_row(r),
                distance_grade=perf.get("distance_aptitude"),
                surface_grade=perf.get("surface_aptitude"),
                style_grade=perf.get("running_style_aptitude"),
                motivation=int(perf.get("motivation") or 3),
                trainee_chara_id=cid, turn=int(r.get("turn") or 0),
                program_id=int(r.get("program_id") or 0),
            )
        except Exception:
            res = {}
        if res.get("available"):
            obs = {
                "s_t": res.get("trainee_strength"),
                "opp": [f.get("strength") for f in res.get("field") or []],
                "won": 1 if int(r.get("rank") or 99) == 1 else 0,
            }
        # whole-field concordance inputs (only when race_horse_data carried stats);
        # independent of the named-rival model, so logged careers count even when it
        # can't run.
        field = r.get("field_results")
        if field:
            dist = r.get("distance_m")
            pairs = [[wp.simple_field_strength(h.get("stats") or {}, dist), int(h.get("finish_order") or 0)]
                     for h in field if h.get("stats") and h.get("finish_order")]
            if len(pairs) >= 2:
                if obs is None:
                    obs = {}
                obs["field"] = pairs
        if obs:
            out.append(obs)
    return out


def _append_observations(base_dir, obs):
    if not obs:
        return
    os.makedirs(_dir(base_dir), exist_ok=True)
    path = _obs_path(base_dir)
    with open(path, "a", encoding="utf-8") as fh:
        for o in obs:
            fh.write(json.dumps(o, separators=(",", ":")) + "\n")
    try:                                   # roll to the last _MAX_OBS lines
        with open(path, "r", encoding="utf-8") as fh:
            lines = fh.readlines()
        if len(lines) > _MAX_OBS:
            with open(path, "w", encoding="utf-8") as fh:
                fh.writelines(lines[-_MAX_OBS:])
    except OSError:
        pass


def _read_observations(base_dir):
    out = []
    try:
        with open(_obs_path(base_dir), "r", encoding="utf-8") as fh:
            for line in fh:
                line = line.strip()
                if line:
                    try:
                        out.append(json.loads(line))
                    except ValueError:
                        pass
    except OSError:
        pass
    return out


def _brier(pairs):
    ps = [(max(0.0, min(1.0, float(p))), float(y)) for p, y in pairs]
    return sum((p - y) ** 2 for p, y in ps) / len(ps) if ps else None


def _field_concordance(field_obs):
    cw = ct = 0
    for pairs in field_obs:
        for i in range(len(pairs)):
            for j in range(i + 1, len(pairs)):
                (sa, fa), (sb, fb) = pairs[i], pairs[j]
                if sa == sb or fa == fb:
                    continue
                ct += 1
                if (sa > sb) == (fa < fb):
                    cw += 1
    return (round(cw / ct, 4) if ct else None), ct


def refit(base_dir, now=None):
    """Re-fit k + field concordance from ALL stored observations; write
    calibration.json and return the summary."""
    obs = _read_observations(base_dir)
    win_obs = [o for o in obs if o.get("opp") is not None and o.get("s_t") is not None]
    n = len(win_obs)
    summary = {"n_races": n, "min_races": _MIN_RACES, "default_k": wp.DEFAULT_K,
               "updated_at": now if now is not None else time.time()}
    if n:
        base_rate = sum(o["won"] for o in win_obs) / n
        ref_brier = _brier([(base_rate, o["won"]) for o in win_obs])
        best_k, best_b = wp.DEFAULT_K, None
        for k in _K_GRID:
            b = _brier([(wp.win_probability(o["s_t"], o["opp"], k=k)["p_win"], o["won"]) for o in win_obs])
            if b is not None and (best_b is None or b < best_b):
                best_k, best_b = k, b
        beats = bool(best_b is not None and ref_brier is not None and best_b < ref_brier)
        summary.update({
            "fitted_k": best_k,
            "brier": round(best_b, 4) if best_b is not None else None,
            "baseline_brier": round(ref_brier, 4) if ref_brier is not None else None,
            "beats_baseline": beats,
            "base_win_rate": round(base_rate, 3),
            "healthy": bool(n >= _MIN_RACES and beats),
        })
    else:
        summary.update({"fitted_k": wp.DEFAULT_K, "beats_baseline": False, "healthy": False})
    conc, pairs = _field_concordance([o["field"] for o in obs if o.get("field")])
    summary["field_concordance"] = conc
    summary["field_pairs"] = pairs
    summary["has_field_stats"] = pairs > 0
    try:
        os.makedirs(_dir(base_dir), exist_ok=True)
        with open(calibration_path(base_dir), "w", encoding="utf-8") as fh:
            json.dump(summary, fh, indent=2)
    except OSError:
        pass
    return summary


def update_from_career(base_dir, race_results, card_id=0, model=None):
    """Append a finished career's modelled races and re-fit. Best-effort; never
    raises. Returns the calibration summary (or {} on failure)."""
    try:
        m = model or wp.load_model(base_dir)
        _append_observations(base_dir, observations_from_career(race_results, m, card_id))
        return refit(base_dir)
    except Exception:
        return {}


# --- historical backfill ------------------------------------------------------
# Pull observations out of EVERY persisted career log (uma_runtime/*/bot_logs),
# including careers that finished BEFORE auto-calibration existed, so the model
# has far more data to fit on. This REBUILDS observations.jsonl from the logs
# (authoritative: every finished career writes a log) instead of appending, which
# makes it dedup-safe and idempotent.

import glob


def _log_files(base_dir):
    root = os.path.join(str(base_dir), "uma_runtime")
    files = glob.glob(os.path.join(root, "*", "bot_logs", "career_log_*.json"))
    try:                                   # newest-first so an obs cap keeps recent careers
        files.sort(key=os.path.getmtime, reverse=True)
    except OSError:
        pass
    return files


def _race_results_from_log(log):
    rs = log.get("runner_status") if isinstance(log, dict) else None
    if isinstance(rs, dict) and rs.get("race_results"):
        return rs["race_results"]
    return (log or {}).get("race_results") or []


def _run_id_from_log(log):
    rs = log.get("runner_status") if isinstance(log, dict) else None
    return str((rs or {}).get("run_id") or log.get("run_id") or "")


def _chara_id_from_log(log):
    """Trainee base-chara id from a career log, cheapest source first."""
    rs = log.get("runner_status") or {}
    for getter in (
        lambda: (log.get("final_chara") or {}).get("card_id"),
        lambda: rs.get("card_id"),
        lambda: (rs.get("final_chara") or {}).get("card_id"),
        lambda: log.get("card_id"),
    ):
        try:
            cid = wp.chara_id_from_card(getter())
            if cid:
                return cid
        except Exception:
            pass
    # the is_player horse in any captured race field carries the live chara id
    for r in _race_results_from_log(log):
        for h in (r.get("field_results") or []):
            if h.get("is_player") and h.get("chara_id"):
                try:
                    return int(h["chara_id"])
                except (TypeError, ValueError):
                    pass
    # last resort: chara_info.card_id buried in the per-turn api_calls
    for t in (log.get("turns") or []):
        for c in (t.get("api_calls") or []):
            chara = (((c.get("data") or {}).get("data") or {}).get("chara_info") or {})
            try:
                cid = wp.chara_id_from_card(chara.get("card_id"))
                if cid:
                    return cid
            except Exception:
                pass
    return 0


def backfill_from_logs(base_dir, model=None, max_obs=_MAX_OBS, status=None):
    """Rebuild the observation store from every persisted career log, then re-fit.

    Lets the model learn from careers that finished before auto-calibration existed.
    Best-effort; never raises. Returns the calibration summary with a `backfill`
    block. `status` (a mutable dict) is updated live for progress polling.
    """
    try:
        m = model or wp.load_model(base_dir)
        files = _log_files(base_dir)
        if status is not None:
            status.update({"files_total": len(files), "scanned": 0, "careers_used": 0})
        seen, all_obs, used, scanned = set(), [], 0, 0
        for path in files:
            if len(all_obs) >= max_obs:
                break
            scanned += 1
            try:
                with open(path, "r", encoding="utf-8") as fh:
                    log = json.load(fh)
            except (OSError, ValueError):
                continue
            run_id = _run_id_from_log(log) or os.path.basename(path)
            if run_id in seen:
                continue
            seen.add(run_id)
            races = _race_results_from_log(log)
            if not races:
                continue
            try:
                obs = observations_from_career(races, m, chara_id=_chara_id_from_log(log))
            except Exception:
                obs = []
            if obs:
                used += 1
                all_obs.extend(obs)
            if status is not None:
                status.update({"scanned": scanned, "careers_used": used, "observations": len(all_obs)})
        all_obs = all_obs[:max_obs]
        try:                                # rebuild (oldest-first, matching live append order)
            os.makedirs(_dir(base_dir), exist_ok=True)
            with open(_obs_path(base_dir), "w", encoding="utf-8") as fh:
                for o in reversed(all_obs):
                    fh.write(json.dumps(o, separators=(",", ":")) + "\n")
        except OSError:
            pass
        summary = refit(base_dir)
        summary["backfill"] = {
            "files_total": len(files), "careers_scanned": scanned,
            "careers_used": used, "observations": len(all_obs),
        }
        try:
            with open(os.path.join(_dir(base_dir), "backfill.json"), "w", encoding="utf-8") as fh:
                json.dump({"at": time.time(), **summary["backfill"]}, fh, indent=2)
        except OSError:
            pass
        if status is not None:
            status.update({"done": True, **summary["backfill"]})
        return summary
    except Exception as exc:
        if status is not None:
            status.update({"done": True, "error": str(exc)})
        return {}


def last_backfill(base_dir):
    """The persisted result of the most recent backfill (or {} if never run)."""
    try:
        with open(os.path.join(_dir(base_dir), "backfill.json"), "r", encoding="utf-8") as fh:
            return json.load(fh)
    except (OSError, ValueError):
        return {}


# --- read side (mtime-cached so the live ~P(win) path picks up new fits) ------
_cache = {"path": None, "mtime": 0.0, "data": {}}


def load_calibration(base_dir):
    path = calibration_path(base_dir)
    try:
        mtime = os.path.getmtime(path)
    except OSError:
        return {}
    if _cache["path"] == path and _cache["mtime"] == mtime:
        return _cache["data"]
    try:
        with open(path, "r", encoding="utf-8") as fh:
            data = json.load(fh)
    except (OSError, ValueError):
        data = {}
    _cache.update({"path": path, "mtime": mtime, "data": data})
    return data


def calibrated_k(base_dir, default=None):
    """Fitted k IF the calibration is healthy (>= MIN_RACES and beats the
    base-rate baseline), else the default (DEFAULT_K)."""
    default = wp.DEFAULT_K if default is None else default
    data = load_calibration(base_dir)
    if data.get("healthy") and data.get("fitted_k"):
        try:
            return float(data["fitted_k"])
        except (TypeError, ValueError):
            return default
    return default
