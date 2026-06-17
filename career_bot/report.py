import json
import re
import traceback
import tempfile
from datetime import datetime
from pathlib import Path

from career_bot.ai_dataset import export_report_ai_datasets
try:
    from career_bot.ai_trainer import after_career_export
except Exception:  # keep report writer import-safe for minimal test harnesses
    after_career_export = None


def now_iso():
    return datetime.now().isoformat(timespec="seconds")


def new_report(preset=None, scenario_id=0):
    preset = preset or {}
    return {
        "started_at": now_iso(),
        "ended_at": None,
        "preset_name": preset.get("name", ""),
        "scenario_id": scenario_id,
        "status": "running",
        "error": None,
        "final_turn": 0,
        "turns": [],
    }


def safe_int(value, default=0):
    try:
        return int(value or 0)
    except (TypeError, ValueError):
        return default


def turn_from_event(event):
    data = event.get("data") or {}
    for key in ("payload", "request_payload"):
        payload = data.get(key) or {}
        if payload.get("current_turn") is not None:
            return safe_int(payload.get("current_turn"))
    if event.get("turn") is not None:
        return safe_int(event.get("turn"))
    return 0


def get_turn(report, turn_number):
    turn_number = safe_int(turn_number)
    for turn in report.setdefault("turns", []):
        if safe_int(turn.get("turn")) == turn_number:
            return turn
    turn = {
        "turn": turn_number,
        "api_calls": [],
        "skill_buy_attempts": [],
        "item_buy_attempts": [],
        "item_usage_attempts": [],
    }
    report.setdefault("turns", []).append(turn)
    report["turns"].sort(key=lambda row: safe_int(row.get("turn")))
    return turn


def merge_turn(report, row):
    turn_number = safe_int(row.get("turn"))
    turn = get_turn(report, turn_number)
    preserved = {
        "api_calls": turn.get("api_calls") or [],
        "skill_buy_attempts": turn.get("skill_buy_attempts") or [],
        "item_buy_attempts": turn.get("item_buy_attempts") or [],
        "item_usage_attempts": turn.get("item_usage_attempts") or [],
    }
    turn.update(row)
    for key, value in preserved.items():
        turn[key] = value
    report["final_turn"] = max(safe_int(report.get("final_turn")), turn_number)
    return turn


def add_event(report, row):
    event = row.get("event")
    turn = get_turn(report, row.get("turn"))
    if event == "turn":
        return merge_turn(report, row)
    if event == "skills_attempt":
        turn.setdefault("skill_buy_attempts", []).append(row)
    elif event == "items_buy_attempt":
        turn.setdefault("item_buy_attempts", []).append(row)
    elif event == "items_use_attempt":
        turn.setdefault("item_usage_attempts", []).append(row)
    else:
        turn.setdefault("events", []).append(row)
    report["final_turn"] = max(safe_int(report.get("final_turn")), safe_int(row.get("turn")))
    return turn


def add_api_call(report, event):
    turn = get_turn(report, turn_from_event(event))
    turn.setdefault("api_calls", []).append(event)
    report["final_turn"] = max(safe_int(report.get("final_turn")), safe_int(turn.get("turn")))


def add_decision(report, state, decision):
    data = (state or {}).get("data") or {}
    chara = data.get("chara_info") or {}
    payload = dict(getattr(decision, "payload", {}) or {})
    runner_context = data.get("runner_context") or {}
    clock_policy = runner_context.get("clock_retry_policy") or {
        "user_enabled": bool(runner_context.get("burn_clocks")),
        "enabled": bool(runner_context.get("burn_clocks")),
        "source": "decision_context",
    }
    turn = get_turn(report, payload.get("current_turn") or chara.get("turn") or 0)
    turn["current_command"] = payload
    turn["selected_action"] = getattr(decision, "action", "")
    turn["decision_reason"] = getattr(decision, "reason", "")
    turn["current_action_taken"] = getattr(decision, "action", "")
    turn["decision_report"] = {
        "action": getattr(decision, "action", ""),
        "reason": getattr(decision, "reason", ""),
        "payload": payload,
        "state": {
            "turn": safe_int(chara.get("turn")),
            "hp": safe_int(chara.get("vital")),
            "max_hp": safe_int(chara.get("max_vital"), 100),
            "mood": safe_int(chara.get("motivation")),
            "fans": safe_int(chara.get("fans")),
            "speed": safe_int(chara.get("speed")),
            "stamina": safe_int(chara.get("stamina")),
            "power": safe_int(chara.get("power")),
            "guts": safe_int(chara.get("guts")),
            "wit": safe_int(chara.get("wiz")),
            "skill_point": safe_int(chara.get("skill_point")),
        },
        "race_context": {
            "program_id": payload.get("program_id"),
            "forced_race": bool(payload.get("_forced_race")),
            "clock_policy": clock_policy,
            "clocks_used_so_far": safe_int(runner_context.get("clocks_used")),
            "clocks_left": safe_int(runner_context.get("clocks_left")),
        },
    }


def set_error(report, exc):
    report["status"] = "error"
    report["error"] = {
        "type": type(exc).__name__,
        "message": str(exc),
        "stack_trace": "".join(traceback.format_exception(type(exc), exc, exc.__traceback__)),
    }


def finish_report(report, status=None):
    if status:
        report["status"] = status
    if report.get("status") == "running":
        report["status"] = "finished"
    report["ended_at"] = now_iso()
    turns = report.get("turns") or []
    if turns:
        report["final_turn"] = max(safe_int(turn.get("turn")) for turn in turns)


def write_report(report, output_dir):
    output_dir = Path(output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)
    stamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    path = output_dir / f"career_log_{stamp}.json"

    def _json_default(obj):
        if isinstance(obj, bytes):
            return obj.hex()
        return str(obj)

    # v5.31: write atomically and validate before replacing the final log.
    # This prevents truncated/malformed JSON exports if Python is killed while
    # the file is being written.
    fd, tmp_name = tempfile.mkstemp(prefix=path.name, suffix=".tmp", dir=str(output_dir))
    tmp = Path(tmp_name)
    try:
        with open(fd, "w", encoding="utf-8") as f:
            json.dump(report, f, ensure_ascii=False, indent=2, default=_json_default)
            f.write("\n")
        json.loads(tmp.read_text(encoding="utf-8"))
        tmp.replace(path)
    except Exception:
        try:
            broken = output_dir / f"career_log_{stamp}.broken.json"
            tmp.replace(broken)
        except Exception:
            try:
                tmp.unlink(missing_ok=True)
            except Exception:
                pass
        raise

    latest = output_dir / "latest_career_log.json"
    try:
        import shutil
        shutil.copyfile(path, latest)
        json.loads(latest.read_text(encoding="utf-8"))
    except Exception:
        pass

    # v5.32: AI-ready learning exports are best-effort observability.
    # They never alter the user-facing career log and must never stop report
    # creation if a derived dataset cannot be written.
    try:
        manifest = export_report_ai_datasets(report, output_dir, build_version="SweepyModv5.40AI")
        report["ai_export_manifest"] = manifest
        if after_career_export:
            report["ai_auto_training"] = after_career_export(output_dir, manifest=manifest, build_version="SweepyModv5.40AI")
    except Exception as exc:
        report["ai_export_error"] = {"type": type(exc).__name__, "message": str(exc)}
    return path
