"""v2.1: Career History must record completed careers (session-only).

Bug: in LOOP mode the finished snapshot is transient (the next career starts
before the /api/career/runner poll can observe it), so the poll-based recorder
missed every looped career and Career History showed nothing — even before a
restart. The loop now records each career explicitly at completion via
record_completed_career_from_snapshot(); this test pins the recorder contract
(records finished, de-dups by run_id, skips running/errored/idless snapshots).
"""
import unittest


def _finished_snap(run_id="run-1", card_id="100101"):
    return {
        "finished": True,
        "running": False,
        "last_error": "",
        "run_id": run_id,
        "scenario_id": 4,
        "turn": 78,
        "steps": 78,
        "fans_gained": 12000,
        "fans_current": 30000,
        "final_chara": {
            "card_id": card_id,
            "stats": {"speed": 1000, "stamina": 800, "power": 900, "guts": 400, "wit": 600},
            "aptitudes": {},
            "fans": 30000,
            "race_count": 12,
            "win_count": 9,
        },
        "race_results": [{"rank": 1}] * 9,
        "action_history": [],
    }


class CareerHistoryRecordTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        import main
        cls.main = main

    def setUp(self):
        self.main.COMPLETED_CAREER_HISTORY.clear()
        self.main.COMPLETED_CAREER_RUN_IDS.clear()

    def test_records_a_finished_career(self):
        entry = self.main.record_completed_career_from_snapshot(_finished_snap())
        self.assertIsNotNone(entry)
        self.assertEqual(len(self.main.COMPLETED_CAREER_HISTORY), 1)
        self.assertEqual(entry["card_id"], "100101")
        self.assertEqual(entry["wins"], 9)

    def test_dedups_by_run_id(self):
        self.main.record_completed_career_from_snapshot(_finished_snap(run_id="dup"))
        self.main.record_completed_career_from_snapshot(_finished_snap(run_id="dup"))
        self.assertEqual(len(self.main.COMPLETED_CAREER_HISTORY), 1)

    def test_records_each_distinct_loop_career(self):
        for i in range(3):
            self.main.record_completed_career_from_snapshot(_finished_snap(run_id=f"loop-{i}"))
        self.assertEqual(len(self.main.COMPLETED_CAREER_HISTORY), 3)

    def test_skips_running_snapshot(self):
        snap = _finished_snap(run_id="r")
        snap["running"] = True
        snap["finished"] = False
        self.assertIsNone(self.main.record_completed_career_from_snapshot(snap))
        self.assertEqual(len(self.main.COMPLETED_CAREER_HISTORY), 0)

    def test_skips_errored_and_idless(self):
        err = _finished_snap(run_id="e")
        err["last_error"] = "boom"
        self.assertIsNone(self.main.record_completed_career_from_snapshot(err))
        idless = _finished_snap(run_id="")
        self.assertIsNone(self.main.record_completed_career_from_snapshot(idless))
        self.assertEqual(len(self.main.COMPLETED_CAREER_HISTORY), 0)


if __name__ == "__main__":
    unittest.main()
