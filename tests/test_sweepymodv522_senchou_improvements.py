import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
MAIN = (ROOT / "main.py").read_text(encoding="utf-8")
CLIENT = (ROOT / "uma_api" / "client.py").read_text(encoding="utf-8")
APP = (ROOT / "public" / "app.js").read_text(encoding="utf-8")
INDEX = (ROOT / "public" / "index.html").read_text(encoding="utf-8")
CSS = (ROOT / "public" / "styles.css").read_text(encoding="utf-8")
PARENT_FILTER = (ROOT / "public" / "js" / "parent-filter.js").read_text(encoding="utf-8")
MONITOR = (ROOT / "public" / "js" / "monitor.js").read_text(encoding="utf-8")


class SweepyModV522SenchouImprovementTests(unittest.TestCase):
    def test_tp_item_recovery_uses_umabot_endpoint(self):
        self.assertIn("def use_recovery_item", CLIENT)
        self.assertIn('self.call("item/use_recovery_item"', CLIENT)
        self.assertIn("active_client.use_recovery_item", MAIN)
        self.assertIn("TP recovery mode", MAIN)
        self.assertNotIn("active_client.recovery_tp(needed, currency=mode", MAIN)

    def test_parent_filter_module_loaded_and_has_safe_cleanup(self):
        self.assertIn('js/parent-filter.js?v=522', INDEX)
        self.assertIn('id="parent-filter-bar"', PARENT_FILTER)
        self.assertIn('/api/parents/remove-recent', PARENT_FILTER)
        self.assertIn('dry_run: true', PARENT_FILTER)
        self.assertIn('Selected/active parents are excluded', PARENT_FILTER)
        self.assertIn('data-instance-id', APP)
        self.assertIn('data-create-date', APP)
        self.assertIn('parent-filter-bar', CSS)

    def test_parent_cleanup_backend_excludes_selected_parents(self):
        self.assertIn('class RemoveRecentParentsRequest', MAIN)
        self.assertIn('@app.post("/api/parents/remove-recent")', MAIN)
        self.assertIn('def _selected_parent_instance_ids', MAIN)
        self.assertIn('iid in selected', MAIN)
        self.assertIn('remove_trained_chara', CLIENT)

    def test_monitor_drawer_loaded_with_live_history_and_crash_trace(self):
        self.assertIn('js/monitor.js?v=522', INDEX)
        self.assertIn('@app.get("/api/career/live_history")', MAIN)
        self.assertIn('@app.get("/api/career/crash_trace")', MAIN)
        self.assertIn('/api/career/live_history', MONITOR)
        self.assertIn('/api/career/crash_trace', MONITOR)
        self.assertIn('monitor-drawer', CSS)

    def test_completed_career_history_endpoint_was_not_repurposed(self):
        self.assertIn('@app.get("/api/career/history")', MAIN)
        self.assertIn('COMPLETED_CAREER_HISTORY', MAIN)
        self.assertIn('career_live_history', MAIN)


if __name__ == "__main__":
    unittest.main()
