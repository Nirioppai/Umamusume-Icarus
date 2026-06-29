import json

from career_bot.events import EventManager
from career_bot.runner import CareerRunner


def test_runner_pause_resume_snapshot(tmp_path):
    runner = CareerRunner(tmp_path)
    runner.status.update({"running": True, "turn": 12})

    runner.pause()
    snap = runner.snapshot()
    assert snap["paused"] is True
    assert snap["last_action"] in {"", "paused"}

    runner.resume()
    snap = runner.snapshot()
    assert snap["paused"] is False


def test_runner_loop_info_is_exposed(tmp_path):
    runner = CareerRunner(tmp_path)
    runner.set_loop_info(3, 5)
    snap = runner.snapshot()
    assert snap["loop_index"] == 3
    assert snap["loop_target"] == 5


def test_runtime_event_override_wins_and_seen_log_is_written(tmp_path):
    # The override is read from uma_runtime/event_overrides.json and wins over
    # automatic scoring regardless of any effect data.
    runtime = tmp_path / "uma_runtime"
    runtime.mkdir()
    (runtime / "event_overrides.json").write_text(json.dumps({"12345": 0}), encoding="utf-8")

    mgr = EventManager(tmp_path)
    event = {
        "story_id": "12345",
        "event_id": "event-a",
        "title": "Test Event",
        "event_contents_info": {"choice_array": [{"select_index": 1}, {"select_index": 2}]},
    }

    assert mgr.choose(event, preset={}, current_turn=1, chara={}) == 0
    seen = json.loads((runtime / "events_seen.json").read_text(encoding="utf-8"))
    assert seen["12345"]["source"] == "override"
    assert seen["12345"]["picked"] == 0


def test_event_choice_weighted_from_inline_rewards_and_records_seen(tmp_path):
    # No KB; scoring uses the inline rewards carried in the event payload (the
    # game8 scrape only fills gaps). Choice 2 grants Speed +10, choice 1 nothing,
    # so weighted scoring picks option 2 (index 1).
    mgr = EventManager(tmp_path)
    event = {
        "story_id": "555",
        "event_id": "event-b",
        "event_contents_info": {"choice_array": [
            {"select_index": 1},
            {"select_index": 2, "params_inc_dec_info_array": [{"target_type": 1, "value": 10}]},
        ]},
    }

    assert mgr.choose(event, preset={}, current_turn=1, chara={}) == 1
    seen = json.loads((tmp_path / "uma_runtime" / "events_seen.json").read_text(encoding="utf-8"))
    assert seen["555"]["source"] == "weighted"
