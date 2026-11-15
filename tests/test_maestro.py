"""Maestro's driver, with no device: reading its report and grouping its commands into steps."""
import os
import sys
import unittest

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from drivers import (
    common,
    maestro,
)


class MaestroReport(unittest.TestCase):
    def test_each_scenario_command_keeps_its_duration_and_setup_commands_are_dropped(self):
        report = [
            {"command": {"defineVariablesCommand": {}}, "metadata": {"status": "COMPLETED", "duration": 3}},
            {"command": {"applyConfigurationCommand": {}}, "metadata": {"status": "COMPLETED", "duration": 1}},
            {"command": {"tapOnElement": {}}, "metadata": {"status": "COMPLETED", "duration": 1987}},
            {"command": {"assertConditionCommand": {}}, "metadata": {"status": "COMPLETED", "duration": 356}},
        ]
        self.assertEqual(maestro.maestro_durations(report), [("tapOnElement", 1987), ("assertConditionCommand", 356)])

    def test_a_failed_command_is_reported(self):
        report = [{"command": {"tapOnElement": {}}, "metadata": {"status": "FAILED", "duration": 5000}}]
        with self.assertRaises(common.StepFailed):
            maestro.maestro_durations(report)

    def test_commands_are_grouped_back_into_scenario_steps(self):
        # A step can take several Maestro commands (scroll until visible, then tap).
        durations = [("a", 10), ("b", 20), ("c", 5), ("d", 7)]
        self.assertEqual(maestro.group(durations, [1, 2, 1]), [10, 25, 7])
        with self.assertRaises(common.StepFailed):
            maestro.group(durations, [1, 1])


class Extras(unittest.TestCase):
    def test_start_up_is_reported_beside_the_table_as_the_median_of_the_runs(self):
        tool = maestro.Maestro("UDID-1")
        tool.startup = [12000, 14000, 13000]
        values, notes = tool.extras(["native"])
        self.assertEqual(values, {"maestro_startup_ms": 13000})
        self.assertEqual(notes, ["Maestro start-up per run (not in the table): 13,000ms"])

    def test_nothing_is_reported_when_it_never_ran(self):
        self.assertEqual(maestro.Maestro("UDID-1").extras(["native"]), ({"maestro_startup_ms": None}, []))


if __name__ == "__main__":
    unittest.main()
