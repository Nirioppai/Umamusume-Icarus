import os
import tempfile
import unittest
from pathlib import Path

from career_bot.runner import CareerRunner
from career_bot import trackblazer

ROOT = Path(__file__).resolve().parents[1]


class RepeatingEventStrategy:
    def _choice(self, event):
        return 1


class RepeatingEventClient:
    def __init__(self):
        self.check_event_calls = 0
        self.load_career_calls = 0

    def check_event(self, **kwargs):
        self.check_event_calls += 1
        return {
            "data": {
                "chara_info": {"turn": kwargs.get("current_turn", 40)},
                "unchecked_event_array": [{"event_id": kwargs.get("event_id", 777), "chara_id": kwargs.get("chara_id", 888)}],
            }
        }

    def load_career(self):
        self.load_career_calls += 1
        return {"data": {"chara_info": {"turn": 41}, "unchecked_event_array": []}}


class SweepyModV54AuditFollowupTests(unittest.TestCase):
    def test_event_drain_repeated_event_refreshes_state_instead_of_returning_pending_event(self):
        runner = CareerRunner(str(ROOT))
        runner.status["turn"] = 40
        client = RepeatingEventClient()
        state = {
            "data": {
                "chara_info": {"turn": 40},
                "unchecked_event_array": [{"event_id": 777, "chara_id": 888}],
            }
        }

        recovered = runner._drain_events(client, RepeatingEventStrategy(), state, limit=20)

        self.assertEqual((recovered.get("data") or {}).get("unchecked_event_array"), [])
        self.assertGreaterEqual(client.check_event_calls, 3)
        self.assertEqual(client.load_career_calls, 1)
        self.assertTrue(any((row or {}).get("action") == "event_drain_repeat" for row in (runner.status.get("log") or [])))

    def test_milp_fallback_records_diagnostics_and_returns_trace_fields(self):
        original_milp = trackblazer._smart_milp_schedule
        original_beam = trackblazer._smart_beam_schedule
        old_runtime = os.environ.get("UMA_RUNTIME_DIR")
        with tempfile.TemporaryDirectory() as tmp:
            os.environ["UMA_RUNTIME_DIR"] = str(Path(tmp) / "runtime")

            def failing_milp(*args, **kwargs):
                raise ValueError("synthetic milp failure")

            def fake_beam(*args, **kwargs):
                return {"success": True, "solver": "smart-race-solver-beam", "schedule": []}

            trackblazer._smart_milp_schedule = failing_milp
            trackblazer._smart_beam_schedule = fake_beam
            try:
                result = trackblazer.make_schedule(ROOT, solver="smart")
            finally:
                trackblazer._smart_milp_schedule = original_milp
                trackblazer._smart_beam_schedule = original_beam
                if old_runtime is None:
                    os.environ.pop("UMA_RUNTIME_DIR", None)
                else:
                    os.environ["UMA_RUNTIME_DIR"] = old_runtime

            self.assertTrue(result["fallback_used"])
            self.assertEqual(result["fallback_exception_type"], "ValueError")
            self.assertIn("synthetic milp failure", result["fallback_reason"])
            self.assertIn("fallback_traceback_tail", result)
            log_path = Path(result["fallback_log"])
            self.assertTrue(log_path.exists())
            self.assertIn("synthetic milp failure", log_path.read_text(encoding="utf-8"))

    def test_solver_status_no_longer_reports_legacy_node_bridge_fields_as_smart_backend(self):
        status = trackblazer.solver_status(ROOT)
        self.assertIn(status["active_backend"], {"milp", "beam"})
        self.assertNotIn("node_found", status)
        self.assertNotIn("node_path", status)
        self.assertNotIn("bridge_script", status)
        self.assertNotIn("bridge_exists", status)


if __name__ == "__main__":
    unittest.main()
