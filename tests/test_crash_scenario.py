"""Focused crash regression tests adapted from Umabot.

The important path is: race_entry returns 205/208, the server actually entered
race state, race_out later returns a payload without chara_info, and the runner
must reload instead of crashing on chara['turn'].
"""
from pathlib import Path

import career_bot.delay as delay

delay.dna_sleep = lambda *a, **k: None

from career_bot.runner import CareerRunner

ROOT = Path(__file__).resolve().parents[1]


class Decision:
    def __init__(self, action, payload=None, reason=""):
        self.action = action
        self.payload = payload or {}
        self.reason = reason


def st(turn, playing_state=1, extra=None):
    data = {
        "chara_info": {
            "turn": turn,
            "playing_state": playing_state,
            "vital": 50,
            "max_vital": 100,
            "motivation": 3,
            "skill_point": 0,
            "speed": 100,
            "stamina": 100,
            "power": 100,
            "guts": 100,
            "wiz": 100,
        },
        "home_info": {"command_info_array": []},
        "unchecked_event_array": [],
    }
    if extra:
        data.update(extra)
    return {"data": data}


class FakeClient:
    api_jitter = 0.0
    def __init__(self):
        self.loads = 0
        self.entry_calls = 0
    def wait_turn_delay(self):
        pass
    def race_entry(self, **kwargs):
        self.entry_calls += 1
        raise Exception("API error 208 on single_mode_free/race_entry")
    def load_career(self):
        self.loads += 1
        if self.loads == 1:
            return st(60, 2, {"race_start_info": {"program_id": 7}})
        return st(61, 1)
    def race_start(self, is_short, current_turn):
        return {"data": {}}
    def race_end(self, current_turn):
        return {"data": {}}
    def race_out(self, current_turn):
        return {"data": {"race_reward": []}}


class FakeStrategy:
    def __init__(self):
        self.steps = 0
    def next_decision(self, state, preset):
        self.steps += 1
        data = state.get("data") or {}
        chara = data.get("chara_info") or {}
        ps = chara.get("playing_state") or 0
        if ps in (2, 3, 4, 5):
            return Decision("race_progress", {"current_turn": chara["turn"], "phase": "start", "chara_info": chara}, "resume race")
        if self.steps == 1:
            return Decision("race", {"program_id": 7, "current_turn": chara["turn"], "_strategy": self}, "scheduled race")
        return Decision("idle", {}, "test done")
    def _choice(self, event):
        return 1


def test_full_crash_sequence_survives_chara_less_race_out():
    runner = CareerRunner(str(ROOT))
    runner.status["running"] = True
    client = FakeClient()
    runner._buy_skills = lambda c, s, p, f: s
    runner._handle_items = lambda c, s, p, b, d=None: s
    runner.item_manager.handle_pre_race = lambda c, s, p, pl, st_, rp: (s, 0)
    runner.item_manager.use_attempt_events = []
    runner._run(client, {"name": "t", "scenario_id": 4}, st(60), FakeStrategy(), max_steps=10)
    assert runner.status["last_error"] == "", runner.status["last_error"]
    assert client.entry_calls == 1
    assert client.loads >= 2


def test_resume_loop_guard_stops_repeated_102_cycle():
    runner = CareerRunner(str(ROOT))
    runner.status["running"] = True
    runner._buy_skills = lambda c, s, p, f: s
    runner._handle_items = lambda c, s, p, b, d=None: s

    class StuckClient:
        api_jitter = 0.0
        def __init__(self):
            self.resets = 0
        def wait_turn_delay(self):
            pass
        def load_career(self):
            return st(60, 3, {"race_start_info": {"program_id": 7}})
        def hard_reset(self):
            self.resets += 1
            return st(60, 3, {"race_start_info": {"program_id": 7}})
        def race_start(self, is_short, current_turn):
            raise Exception("API error 102 on race_start")
        def race_end(self, current_turn):
            raise Exception("API error 102 on race_end")
        def race_out(self, current_turn):
            raise Exception("API error 102 on race_out")

    class StuckStrategy:
        def next_decision(self, state, preset):
            chara = (state.get("data") or {}).get("chara_info") or {}
            return Decision("race_progress", {"current_turn": chara["turn"], "phase": "start", "chara_info": chara}, "resume race")
        def _choice(self, event):
            return 1

    client = StuckClient()
    runner._run(client, {"name": "t", "scenario_id": 4}, st(60, 3, {"race_start_info": {"program_id": 7}}), StuckStrategy(), max_steps=100)
    assert "race resume loop" in runner.status["last_error"]
    assert client.resets >= 1
