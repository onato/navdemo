"""tests/compare.py, with no device: summarising runs."""
import os
import sys
import unittest

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import compare


class Summary(unittest.TestCase):
    def test_median_per_step_and_of_the_totals(self):
        runs = [[100, 10], [300, 30], [200, 20]]
        s = compare.summarise(runs)
        self.assertEqual(s["steps"], [200, 20])
        self.assertEqual(s["total"], 220)

    def test_a_cell_that_cannot_run_says_why(self):
        self.assertEqual(compare.summarise([], cannot="no webview content")["cannot"], "no webview content")


if __name__ == "__main__":
    unittest.main()
