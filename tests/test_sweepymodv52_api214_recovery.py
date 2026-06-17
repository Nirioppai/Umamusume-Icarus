import unittest

import career_bot.runner as runner_mod
from career_bot.runner import CareerRunner


class FakeStrategy:
    def _choice(self, event):
        return 1


class FakeClient214DuringRaceOut:
    api_jitter = 0.0

    def __init__(self):
        self.check_event_calls = 0
        self.load_career_calls = 0

    def race_entry(self, **kwargs):
        return {"data": {"race_start_info": {}}}

    def race_start(self, **kwargs):
        return {"data": {"race_start_info": {}}, "data_headers": {}}

    def race_end(self, **kwargs):
        return {"data": {}}

    def race_out(self, **kwargs):
        return {
            "data": {
                "chara_info": {"turn": kwargs.get("current_turn", 1)},
                "unchecked_event_array": [{"event_id": 123, "chara_id": 456}],
            }
        }

    def check_event(self, **kwargs):
        self.check_event_calls += 1
        raise Exception('API error 214 on single_mode_free/check_event: {"result_code": 214}')

    def load_career(self):
        self.load_career_calls += 1
        return {"data": {"chara_info": {"turn": 55}, "unchecked_event_array": []}}


class Api214RecoveryTests(unittest.TestCase):
    def test_214_is_recoverable_and_parsed_for_debug(self):
        runner = CareerRunner(".")
        self.assertTrue(runner._is_recoverable_error(Exception("API error 214 on single_mode_free/check_event")))
        parsed = runner._api_result({"error": "API error 214 on single_mode_free/check_event"})
        self.assertEqual(parsed["result_code"], 214)

    def test_race_out_event_214_refreshes_career_state_instead_of_crashing(self):
        original_sleep = runner_mod.dna_sleep
        runner_mod.dna_sleep = lambda *args, **kwargs: None
        try:
            runner = CareerRunner(".")
            client = FakeClient214DuringRaceOut()
            payload = {"program_id": 999, "current_turn": 54, "_strategy": FakeStrategy()}
            state = {"data": {"home_info": {}, "chara_info": {"turn": 54}}}

            recovered = runner._race(client, state, {"scenario_id": 1}, payload)

            self.assertEqual((recovered.get("data") or {}).get("chara_info", {}).get("turn"), 55)
            self.assertEqual(client.check_event_calls, 1)
            self.assertGreaterEqual(client.load_career_calls, 1)
        finally:
            runner_mod.dna_sleep = original_sleep


if __name__ == "__main__":
    unittest.main()
