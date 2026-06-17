import unittest
from pathlib import Path

from career_bot.runner import CareerRunner

ROOT = Path(__file__).resolve().parents[1]
MAIN = (ROOT / "main.py").read_text(encoding="utf-8", errors="replace")
RUNNER = (ROOT / "career_bot" / "runner.py").read_text(encoding="utf-8", errors="replace")
CLIENT = (ROOT / "uma_api" / "client.py").read_text(encoding="utf-8", errors="replace")
PARENT_FILTER = (ROOT / "public" / "js" / "parent-filter.js").read_text(encoding="utf-8", errors="replace")
MONITOR = (ROOT / "public" / "js" / "monitor.js").read_text(encoding="utf-8", errors="replace")
SHELL = (ROOT / "public" / "css" / "shell.css").read_text(encoding="utf-8", errors="replace")


def state(turn=1, playing_state=1, extra=None):
    data = {
        "chara_info": {"turn": turn, "playing_state": playing_state, "vital": 50, "max_vital": 100},
        "home_info": {"command_info_array": []},
    }
    if extra:
        data.update(extra)
    return {"data": data}


class DummyRacePlanner:
    def __init__(self):
        self.rejected = []
    def reject(self, turn, program_id):
        self.rejected.append((turn, program_id))


class SweepyModV525UmabotStabilityTests(unittest.TestCase):
    def test_state_missing_chara_info_guard_refreshes_before_turn_read(self):
        runner = CareerRunner(str(ROOT))
        class Client:
            def __init__(self):
                self.loads = 0
            def load_career(self):
                self.loads += 1
                return state(12)
        client = Client()
        refreshed = runner._ensure_chara_info(client, None, {"data": {}})
        self.assertEqual((refreshed["data"]["chara_info"])["turn"], 12)
        self.assertEqual(client.loads, 1)

    def test_race_entry_205_or_208_reconciles_mid_race_state(self):
        runner = CareerRunner(str(ROOT))
        runner.race_planner = DummyRacePlanner()
        class Client:
            def race_entry(self, **kwargs):
                raise Exception("API error 208 on single_mode_free/race_entry")
            def load_career(self):
                return state(60, 2, {"race_start_info": {"program_id": 7}})
        result = runner._race(Client(), state(60), {"scenario_id": 1}, {"program_id": 7, "current_turn": 60})
        self.assertEqual(result["data"]["chara_info"]["playing_state"], 2)
        self.assertEqual(runner.race_planner.rejected, [])
        self.assertTrue(any(row.get("action") == "race_entry_reconciled" for row in runner.status.get("log", [])))

    def test_race_entry_205_or_208_rejects_only_when_reload_not_in_race(self):
        runner = CareerRunner(str(ROOT))
        runner.race_planner = DummyRacePlanner()
        class Client:
            def race_entry(self, **kwargs):
                raise Exception("API error 205 on single_mode_free/race_entry")
            def load_career(self):
                return state(60, 1)
        runner._race(Client(), state(60), {"scenario_id": 1}, {"program_id": 7, "current_turn": 60})
        self.assertEqual(runner.race_planner.rejected, [(60, 7)])

    def test_static_routes_use_traversal_safe_resolver(self):
        self.assertIn("def safe_public_path(subdir: str, file_name: str):", MAIN)
        self.assertIn('path = safe_public_path("assets/data", file_name)', MAIN)
        self.assertIn('path = safe_public_path("races", file_name)', MAIN)
        self.assertIn("base not in path.parents", MAIN)
        self.assertNotIn('base_dir / "public" / "assets" / "data" / file_name', MAIN)

    def test_rescue_endpoint_and_diagnostics_button_exist(self):
        app = (ROOT / "public" / "app.js").read_text(encoding="utf-8", errors="replace")
        index = (ROOT / "public" / "index.html").read_text(encoding="utf-8", errors="replace")
        self.assertIn('@app.post("/api/career/rescue")', MAIN)
        self.assertIn('career_runner.snapshot().get("running")', MAIN)
        self.assertIn("Runner must be stopped", index)
        self.assertIn("/api/career/rescue", app)
        self.assertIn("runStuckCareerRescue", app)

    def test_monitor_remains_optional_modular_component(self):
        self.assertIn("SWEEPY_DISABLE_MONITOR", MONITOR)
        self.assertIn("window.SweepyCareerMonitor", MONITOR)
        self.assertIn("monitor-host", MONITOR)
        self.assertNotIn("monitor-drawer", (ROOT / "public" / "app.js").read_text(encoding="utf-8", errors="replace"))

    def test_theme_and_ui_polish_are_in_shell_css_layer(self):
        styles = (ROOT / "public" / "styles.css").read_text(encoding="utf-8", errors="replace")
        self.assertIn("css/shell.css", (ROOT / "public" / "index.html").read_text(encoding="utf-8", errors="replace"))
        self.assertIn('html[data-sweepy-theme="clean-dark"]', SHELL)
        self.assertIn(".theme-select-wrap", SHELL)
        self.assertNotIn("v5.24 selective keep: persisted appearance selector", styles)

    def test_parent_and_guest_parent_filters_never_remove_for_filter_sort(self):
        self.assertIn("guest-parent-grid", PARENT_FILTER)
        self.assertIn("card.el.style.display = ok ? '' : 'none'", PARENT_FILTER)
        self.assertIn("card.el.style.order = String(order)", PARENT_FILTER)
        filtering_source = PARENT_FILTER.split("async function previewAndDeleteRecentParents", 1)[0]
        self.assertNotIn(".remove(", filtering_source)

    def test_client_retry_loop_keeps_205_and_208_counters_independent(self):
        self.assertIn("retries_205_left = retry_205", CLIENT)
        self.assertIn("retries_208_left = retry_208", CLIENT)
        self.assertIn("wait_min = min(0.8 * (2 ** attempt_208), 12.0)", CLIENT)
        self.assertIn("retryable_http_statuses = {500, 502, 503, 504}", CLIENT)
        self.assertNotIn("return self.call(ep, args", CLIENT)


if __name__ == "__main__":
    unittest.main()
