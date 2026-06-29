"""v2.1: Trackblazer RIVAL OVERWRITE for manual race selection.

A turn-slot may hold a MAIN race plus one or more RIVAL OVERWRITE races
(extra_race_list = [main, overwrite, ...] for that turn). When the game presents
a rival on that turn whose race is one of the overwrites, the bot should run the
RIVAL race instead of the main pick.

Before the fix, manual mode returned valid_wanted[0] unconditionally, so rival
overwrites were silently ignored (the old UI exposed them but they never worked).
Single-race turns and turns with no rival match are unaffected.
"""
import tempfile
import unittest
from pathlib import Path

from career_bot.races import RacePlanner


def _planner():
    tmp = Path(tempfile.mkdtemp())
    (tmp / "data").mkdir()
    p = RacePlanner(tmp)
    p.program = {
        100: {"name": "Main Pick", "grade": "G1", "distance": 1600, "ground": 1, "fans": 20000},
        200: {"name": "Rival Race", "grade": "G1", "distance": 1600, "ground": 1, "fans": 20000},
    }
    p._replan_smart_schedule = lambda *a, **k: None
    return p


def _state(available, turn=40, rival_pids=()):
    return {"data": {
        "chara_info": {
            "turn": turn, "scenario_id": 4, "fans": 5000, "card_id": 100101, "chara_id": 1001,
            "proper_distance_short": 8, "proper_distance_mile": 8,
            "proper_distance_middle": 8, "proper_distance_long": 8,
            "proper_ground_turf": 8, "proper_ground_dirt": 8,
        },
        "home_info": {"command_info_array": [
            {"command_type": 4, "command_id": 401, "is_enable": 1}]},
        "race_condition_array": [{"program_id": pid} for pid in available],
        "free_data_set": {"rival_race_info_array": [
            {"program_id": pid, "chara_id": 1011} for pid in rival_pids]},
    }}


class RivalOverwriteTests(unittest.TestCase):
    def _preset(self):
        return {"extra_race_list": [100, 200], "extra_race_list_source": "manual",
                "mant_config": {}}

    def test_runs_rival_overwrite_when_rival_present(self):
        p = _planner()
        # main=100 (not the rival), overwrite=200 IS the rival this turn -> run 200.
        st = _state(available=[100, 200], rival_pids=[200])
        self.assertEqual(p.choose(st, self._preset()), 200)

    def test_runs_main_when_no_rival_this_turn(self):
        p = _planner()
        st = _state(available=[100, 200], rival_pids=[])
        self.assertEqual(p.choose(st, self._preset()), 100)

    def test_runs_main_when_main_is_the_rival(self):
        p = _planner()
        st = _state(available=[100, 200], rival_pids=[100])
        self.assertEqual(p.choose(st, self._preset()), 100)

    def test_single_race_turn_unaffected(self):
        p = _planner()
        st = _state(available=[100, 200], rival_pids=[200])
        preset = {"extra_race_list": [100], "extra_race_list_source": "manual", "mant_config": {}}
        # only the main is listed -> main runs even though 200 is a rival.
        self.assertEqual(p.choose(st, preset), 100)

    def test_overwrite_not_offered_falls_back_to_main(self):
        p = _planner()
        # rival race 200 is NOT offered this turn (only 100 available) -> main.
        st = _state(available=[100], rival_pids=[200])
        self.assertEqual(p.choose(st, self._preset()), 100)


if __name__ == "__main__":
    unittest.main()
