import unittest
from pathlib import Path

import career_bot.runner as runner_mod
from career_bot.runner import CareerRunner
from career_bot import trackblazer

ROOT = Path(__file__).resolve().parents[1]
INDEX = (ROOT / "public" / "index.html").read_text(encoding="utf-8")
APP = (ROOT / "public" / "app.js").read_text(encoding="utf-8")
CSS = (ROOT / "public" / "styles.css").read_text(encoding="utf-8")


class FakeStrategy:
    def _choice(self, event):
        return 1


class FakeClient214AtRaceEntry:
    api_jitter = 0.0

    def __init__(self):
        self.load_career_calls = 0

    def race_entry(self, **kwargs):
        raise Exception('API error 214 on single_mode_free/race_entry: {"result_code": 214}')

    def load_career(self):
        self.load_career_calls += 1
        return {"data": {"chara_info": {"turn": 12}, "unchecked_event_array": []}}


class FakeClient214AtRaceStart:
    api_jitter = 0.0

    def __init__(self):
        self.load_career_calls = 0

    def race_entry(self, **kwargs):
        return {"data": {"race_start_info": {}}}

    def race_start(self, **kwargs):
        raise Exception('API error 214 on single_mode_free/race_start: {"result_code": 214}')

    def load_career(self):
        self.load_career_calls += 1
        return {"data": {"chara_info": {"turn": 13}, "unchecked_event_array": []}}




class FakeClient214RaceProgressOut:
    api_jitter = 0.0

    def __init__(self):
        self.load_career_calls = 0

    def race_out(self, **kwargs):
        raise Exception('API error 214 on single_mode_free/race_out: {"result_code": 214}')

    def load_career(self):
        self.load_career_calls += 1
        return {"data": {"chara_info": {"turn": 21}, "unchecked_event_array": []}}


class SweepyModV53UiAndRecoveryTests(unittest.TestCase):
    def test_settings_buttons_follow_team_slots_and_precede_config_sections(self):
        panel_body = INDEX.index('<div class="panel-body">')
        team = INDEX.index('class="team-slots"')
        bot = INDEX.index('id="bot-settings-section"')
        skill = INDEX.index('id="skill-config-launch-section"')
        presets = INDEX.index('id="settings-preset-section"')
        self.assertLess(panel_body, team)
        self.assertLess(team, bot)
        self.assertLess(bot, skill)
        self.assertLess(skill, presets)
        self.assertIn('body.dashboard-mode #setup-panel .panel-body > #bot-settings-section', CSS)

    def test_diagnostics_contains_solver_backend_indicator(self):
        self.assertIn('id="v53-solver-backend-status"', INDEX)
        self.assertIn('v53SolverBackendStatus', APP)
        self.assertIn('function renderSolverBackendStatus', APP)
        self.assertIn('active_backend_label', APP)
        self.assertIn('solver-backend-status.milp', CSS)
        self.assertIn('solver-backend-status.beam', CSS)

    def test_solver_status_reports_milp_or_beam_backend(self):
        status = trackblazer.solver_status(ROOT)
        self.assertTrue(status['success'])
        self.assertIn(status['active_backend'], {'milp', 'beam'})
        self.assertIn(status['active_backend_label'], {'MILP', 'Beam'})
        self.assertTrue(status['beam_available'])
        self.assertIn('milp_available', status)

    def test_race_entry_214_recovers_instead_of_crashing(self):
        original_sleep = runner_mod.dna_sleep
        runner_mod.dna_sleep = lambda *args, **kwargs: None
        try:
            runner = CareerRunner(str(ROOT))
            client = FakeClient214AtRaceEntry()
            state = {"data": {"home_info": {}, "chara_info": {"turn": 11}}}
            payload = {"program_id": 100, "current_turn": 11, "_strategy": FakeStrategy()}
            recovered = runner._race(client, state, {"scenario_id": 1}, payload)
            self.assertEqual((recovered.get("data") or {}).get("chara_info", {}).get("turn"), 12)
            self.assertGreaterEqual(client.load_career_calls, 1)
        finally:
            runner_mod.dna_sleep = original_sleep

    def test_race_start_214_recovers_instead_of_crashing(self):
        original_sleep = runner_mod.dna_sleep
        runner_mod.dna_sleep = lambda *args, **kwargs: None
        try:
            runner = CareerRunner(str(ROOT))
            client = FakeClient214AtRaceStart()
            state = {"data": {"home_info": {}, "chara_info": {"turn": 12}}}
            payload = {"program_id": 100, "current_turn": 12, "_strategy": FakeStrategy()}
            recovered = runner._race(client, state, {"scenario_id": 1}, payload)
            self.assertEqual((recovered.get("data") or {}).get("chara_info", {}).get("turn"), 13)
            self.assertGreaterEqual(client.load_career_calls, 1)
        finally:
            runner_mod.dna_sleep = original_sleep

    def test_race_progress_out_214_recovers_instead_of_crashing(self):
        original_sleep = runner_mod.dna_sleep
        runner_mod.dna_sleep = lambda *args, **kwargs: None
        try:
            runner = CareerRunner(str(ROOT))
            client = FakeClient214RaceProgressOut()
            payload = {"current_turn": 20, "phase": "out", "chara_info": {"playing_state": 2}}
            recovered = runner._race_progress(client, payload)
            self.assertEqual((recovered.get("data") or {}).get("chara_info", {}).get("turn"), 21)
            self.assertGreaterEqual(client.load_career_calls, 1)
        finally:
            runner_mod.dna_sleep = original_sleep


if __name__ == "__main__":
    unittest.main()
