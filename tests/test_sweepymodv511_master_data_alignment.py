import json
import sqlite3
import tempfile
import unittest
from pathlib import Path

from career_bot import master_data
from career_bot.races import RacePlanner


class SweepyModV511MasterDataAlignmentTests(unittest.TestCase):
    def _build_master_fixture(self, root: Path) -> Path:
        db = root / "master.mdb"
        conn = sqlite3.connect(str(db))
        cur = conn.cursor()
        cur.execute('CREATE TABLE item_data (id INTEGER PRIMARY KEY, item_category INTEGER, effect_type_1 INTEGER, effect_value_1 INTEGER)')
        cur.execute('CREATE TABLE text_data (id INTEGER, category INTEGER, "index" INTEGER, text TEXT, PRIMARY KEY(category, "index"))')
        cur.execute('CREATE TABLE single_mode_fan_count (id INTEGER PRIMARY KEY, fan_set_id INTEGER, "order" INTEGER, fan_count INTEGER)')
        cur.execute('CREATE TABLE single_mode_program (id INTEGER PRIMARY KEY, base_program_id INTEGER, race_instance_id INTEGER, race_permission INTEGER, month INTEGER, half INTEGER, need_fan_count INTEGER, fan_set_id INTEGER, reward_set_id INTEGER)')
        cur.execute('CREATE TABLE race_instance (id INTEGER PRIMARY KEY, race_id INTEGER)')
        cur.execute('CREATE TABLE race (id INTEGER PRIMARY KEY, grade INTEGER, course_set INTEGER)')
        cur.execute('CREATE TABLE race_course_set (id INTEGER PRIMARY KEY, race_track_id INTEGER, distance INTEGER, ground INTEGER)')
        cur.execute('CREATE TABLE single_mode_wins_saddle (id INTEGER PRIMARY KEY, priority INTEGER, group_id INTEGER, condition INTEGER, win_saddle_type INTEGER, race_instance_id_1 INTEGER, race_instance_id_2 INTEGER, race_instance_id_3 INTEGER, race_instance_id_4 INTEGER, race_instance_id_5 INTEGER, race_instance_id_6 INTEGER, race_instance_id_7 INTEGER, race_instance_id_8 INTEGER)')
        cur.execute('CREATE TABLE single_mode_rank (id INTEGER PRIMARY KEY, min_value INTEGER, max_value INTEGER)')

        cur.execute('INSERT INTO item_data VALUES (32, 20, 2, 30)')
        cur.execute('INSERT INTO item_data VALUES (174, 20, 2, 30)')
        cur.executemany('INSERT INTO text_data VALUES (?, ?, ?, ?)', [
            (23, 23, 32, 'Toughness 30'),
            (10, 10, 32, 'Drink this for revitalization! Restores 30 TP.'),
            (23, 23, 174, 'Star Fruit'),
            (10, 10, 174, 'A peculiar star-shaped fruit. Restores 30 TP.'),
            (28, 28, 100101, 'February Stakes'),
            (111, 111, 7, 'Dual Miles'),
        ])
        cur.execute('INSERT INTO single_mode_fan_count VALUES (1, 30, 1, 10000)')
        cur.execute('INSERT INTO single_mode_program VALUES (1, 0, 100101, 4, 2, 2, 12000, 30, 100101)')
        cur.execute('INSERT INTO race_instance VALUES (100101, 1001)')
        cur.execute('INSERT INTO race VALUES (1001, 100, 501)')
        cur.execute('INSERT INTO race_course_set VALUES (501, 10006, 1600, 2)')
        cur.execute('INSERT INTO single_mode_wins_saddle VALUES (7, 10, 10, 0, 0, 100101, 100102, 0, 0, 0, 0, 0, 0)')
        cur.executemany('INSERT INTO single_mode_rank VALUES (?, ?, ?)', [
            (13, 10000, 12099),
            (14, 12100, 14499),
            (15, 14500, 15899),
        ])
        conn.commit()
        conn.close()
        return db

    def test_master_data_outputs_tp_race_wins_and_rank_core_files(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            (root / "data").mkdir()
            (root / "public" / "assets" / "data").mkdir(parents=True)
            db = self._build_master_fixture(root)
            result = master_data.generate(root, db)
            self.assertTrue(result["success"])

            tp_items = json.loads((root / "data" / "tp_restore_items_core.json").read_text(encoding="utf-8"))
            toughness = [row for row in tp_items if row.get("kind") == "toughness_30"]
            self.assertEqual([row["item_id"] for row in toughness], [32])

            races = json.loads((root / "data" / "race_planner_core.json").read_text(encoding="utf-8"))
            program_one = next(row for row in races if row["program_id"] == 1)
            self.assertEqual(program_one["fans"], 10000)
            self.assertEqual(program_one["fan_set_id"], 30)
            self.assertEqual(program_one["terrain"], "Dirt")
            self.assertEqual(program_one["distance"], "Mile")

            planner = RacePlanner(root)
            info = planner._program_info(1)
            self.assertEqual(info["fans"], 10000)
            self.assertEqual(info["fan_set_id"], 30)

            win_saddles = json.loads((root / "data" / "win_saddle_core.json").read_text(encoding="utf-8"))
            dual_miles = next(row for row in win_saddles if row["id"] == 7)
            self.assertEqual(dual_miles["name"], "Dual Miles")
            self.assertIn("G1", dual_miles["grades"])

            ranks = json.loads((root / "data" / "career_rank_thresholds_core.json").read_text(encoding="utf-8"))
            self.assertIn({"id": 14, "min_value": 12100, "max_value": 14499}, ranks)


if __name__ == "__main__":
    unittest.main()
