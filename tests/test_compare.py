"""tests/compare.py's logic, with no device: reading Maestro's report, finding text in AXe's tree,
and summarising runs."""
import os
import sys
import unittest

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import compare


class MaestroReport(unittest.TestCase):
    def test_each_scenario_command_keeps_its_duration_and_setup_commands_are_dropped(self):
        report = [
            {"command": {"defineVariablesCommand": {}}, "metadata": {"status": "COMPLETED", "duration": 3}},
            {"command": {"applyConfigurationCommand": {}}, "metadata": {"status": "COMPLETED", "duration": 1}},
            {"command": {"tapOnElement": {}}, "metadata": {"status": "COMPLETED", "duration": 1987}},
            {"command": {"assertConditionCommand": {}}, "metadata": {"status": "COMPLETED", "duration": 356}},
        ]
        self.assertEqual(compare.maestro_durations(report), [("tapOnElement", 1987), ("assertConditionCommand", 356)])

    def test_a_failed_command_is_reported(self):
        report = [{"command": {"tapOnElement": {}}, "metadata": {"status": "FAILED", "duration": 5000}}]
        with self.assertRaises(compare.StepFailed):
            compare.maestro_durations(report)

    def test_commands_are_grouped_back_into_scenario_steps(self):
        # A step can take several Maestro commands (scroll until visible, then tap).
        durations = [("a", 10), ("b", 20), ("c", 5), ("d", 7)]
        self.assertEqual(compare.group(durations, [1, 2, 1]), [10, 25, 7])
        with self.assertRaises(compare.StepFailed):
            compare.group(durations, [1, 1])


TREE = [{"AXLabel": "NavDemo", "frame": {"x": 0, "y": 0, "width": 402, "height": 874}, "children": [
        {"AXLabel": "Say hello", "AXValue": None, "frame": {"x": 16, "y": 322, "width": 93, "height": 34}, "children": []},
        {"AXLabel": "Web row 40", "frame": {"x": 40, "y": 2100, "width": 90, "height": 20}, "children": []},
    ]}]


class AxeTree(unittest.TestCase):
    def test_an_element_is_found_by_label_anywhere_in_the_tree(self):
        self.assertEqual(compare.axe_find(TREE, "Say hello")["frame"]["y"], 322)
        self.assertIsNone(compare.axe_find(TREE, "Nope"))

    def test_on_screen_means_its_centre_is_above_the_tab_bar(self):
        self.assertTrue(compare.on_screen(compare.axe_find(TREE, "Say hello"), bottom=791))
        self.assertFalse(compare.on_screen(compare.axe_find(TREE, "Web row 40"), bottom=791))


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
