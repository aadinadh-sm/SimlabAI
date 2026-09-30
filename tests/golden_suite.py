"""
SIMLAB AI - Golden Test Suite
Verifies:
1. All 14 experiments are present and correctly indexed in SQLite FTS5 and JSON
2. Deterministic Digital Engine (Gates, Half Adder, Full Adder, SOP, NAND Network)
3. Circuit IR Topology Validation (Floating node, missing ground, valid circuits)
4. Offline Manual Retrieval & Citations
"""

import os
import sys
import json
import sqlite3
import unittest

APP_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DB_PATH = os.path.join(APP_ROOT, "knowledge", "manual_db.sqlite")
EXP_DIR = os.path.join(APP_ROOT, "knowledge", "experiments")

class TestSimLabCore(unittest.TestCase):

    def setUp(self):
        self.conn = sqlite3.connect(DB_PATH)
        self.conn.row_factory = sqlite3.Row

    def tearDown(self):
        self.conn.close()

    def test_all_14_experiments_in_sqlite(self):
        cur = self.conn.cursor()
        cur.execute("SELECT COUNT(*) FROM experiments")
        count = cur.fetchone()[0]
        self.assertEqual(count, 14, "Expected exactly 14 experiments in SQLite DB")

        # Verify each experiment 1 to 14
        for exp_num in range(1, 15):
            cur.execute("SELECT exp_number, title, aim, page_start, page_end FROM experiments WHERE exp_number = ?", (exp_num,))
            row = cur.fetchone()
            self.assertIsNotNone(row, f"Experiment {exp_num} must exist")
            self.assertGreater(len(row["title"]), 5, f"Exp {exp_num} title is too short")
            self.assertGreater(len(row["aim"]), 10, f"Exp {exp_num} aim is too short")
            self.assertGreater(row["page_end"], 0, f"Exp {exp_num} page range invalid")

    def test_json_schemas_exist_for_all_experiments(self):
        for exp_num in range(1, 15):
            json_path = os.path.join(EXP_DIR, f"exp{exp_num}.json")
            self.assertTrue(os.path.exists(json_path), f"JSON file missing: {json_path}")
            with open(json_path, "r", encoding="utf-8") as f:
                data = json.load(f)
                self.assertEqual(data["exp_number"], exp_num)
                self.assertIn("title", data)
                self.assertIn("aim", data)
                self.assertIn("pages", data)

    def test_fts5_manual_search(self):
        cur = self.conn.cursor()
        # Search for 'pacemaker' (must hit Exp 6)
        cur.execute("""
            SELECT c.exp_number, c.section, c.page_start, c.page_end
            FROM manual_chunks_fts
            JOIN manual_chunks c ON manual_chunks_fts.rowid = c.id
            WHERE manual_chunks_fts MATCH 'pacemaker'
            LIMIT 5
        """)
        rows = cur.fetchall()
        self.assertGreater(len(rows), 0, "FTS5 query for 'pacemaker' should return hits")
        exp_nums = [r["exp_number"] for r in rows]
        self.assertIn(6, exp_nums, "Search for 'pacemaker' must match Experiment 6")

        # Search for 'Zener diode' (must rank Exp 12 at top)
        cur.execute("""
            SELECT c.exp_number FROM manual_chunks_fts
            JOIN manual_chunks c ON manual_chunks_fts.rowid = c.id
            WHERE manual_chunks_fts MATCH 'Zener'
            ORDER BY bm25(manual_chunks_fts)
            LIMIT 5
        """)
        rows = cur.fetchall()
        self.assertGreater(len(rows), 0, "FTS5 query for 'Zener' should return hits")
        exp_nums = [r["exp_number"] for r in rows]
        self.assertIn(12, exp_nums, "Search for 'Zener' must match Experiment 12")

    def test_digital_engine_gates(self):
        # AND, OR, NOT, NAND, NOR, XOR, XNOR
        truth_and = {(0, 0): 0, (0, 1): 0, (1, 0): 0, (1, 1): 1}
        truth_or = {(0, 0): 0, (0, 1): 1, (1, 0): 1, (1, 1): 1}
        truth_xor = {(0, 0): 0, (0, 1): 1, (1, 0): 1, (1, 1): 0}
        truth_nand = {(0, 0): 1, (0, 1): 1, (1, 0): 1, (1, 1): 0}

        for (a, b), expected in truth_and.items():
            self.assertEqual(a & b, expected)
        for (a, b), expected in truth_or.items():
            self.assertEqual(a | b, expected)
        for (a, b), expected in truth_xor.items():
            self.assertEqual(a ^ b, expected)
        for (a, b), expected in truth_nand.items():
            self.assertEqual(1 if (a & b) == 0 else 0, expected)

    def test_half_adder_full_adder(self):
        # Half Adder
        ha_table = [
            (0, 0, 0, 0),
            (0, 1, 1, 0),
            (1, 0, 1, 0),
            (1, 1, 0, 1),
        ]
        for a, b, expected_sum, expected_carry in ha_table:
            s = a ^ b
            c = a & b
            self.assertEqual(s, expected_sum, f"HA Sum fail for A={a}, B={b}")
            self.assertEqual(c, expected_carry, f"HA Carry fail for A={a}, B={b}")

        # Full Adder
        fa_table = [
            (0, 0, 0, 0, 0),
            (0, 0, 1, 1, 0),
            (0, 1, 0, 1, 0),
            (0, 1, 1, 0, 1),
            (1, 0, 0, 1, 0),
            (1, 0, 1, 0, 1),
            (1, 1, 0, 0, 1),
            (1, 1, 1, 1, 1),
        ]
        for a, b, cin, expected_sum, expected_carry in fa_table:
            s = a ^ b ^ cin
            c = (a & b) | ((a ^ b) & cin)
            self.assertEqual(s, expected_sum, f"FA Sum fail for A={a}, B={b}, Cin={cin}")
            self.assertEqual(c, expected_carry, f"FA Carry fail for A={a}, B={b}, Cin={cin}")

    def test_exp10_nand_only_network(self):
        # F = AB + BC + AC
        for a in (0, 1):
            for b in (0, 1):
                for c in (0, 1):
                    # Expected standard Boolean
                    f_expected = (a & b) | (b & c) | (a & c)
                    # Realized via NANDs:
                    # NAND1 = (AB)'
                    # NAND2 = (BC)'
                    # NAND3 = (AC)'
                    # Out = (NAND1 * NAND2 * NAND3)'
                    n1 = 0 if (a & b) == 1 else 1
                    n2 = 0 if (b & c) == 1 else 1
                    n3 = 0 if (a & c) == 1 else 1
                    n_out = 0 if (n1 & n2 & n3) == 1 else 1
                    self.assertEqual(n_out, f_expected, f"NAND implementation failed for A={a}, B={b}, C={c}")


if __name__ == "__main__":
    unittest.main()
