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


DUMP = """<?xml version='1.0' encoding='UTF-8' standalone='yes' ?><hierarchy rotation="0">
<node index="0" text="" resource-id="" class="android.widget.FrameLayout" content-desc="" bounds="[0,0][1080,2400]">
<node index="0" text="Say hello" resource-id="dev.navdemo.android:id/hello" class="android.widget.Button" content-desc="" bounds="[44,665][338,797]" />
<node index="1" text="• Web row 40" resource-id="" class="android.widget.TextView" content-desc="Web row 40" bounds="[44,2300][1036,2407]" />
<node index="2" text="" resource-id="name" class="android.widget.EditText" content-desc="" bounds="[44,1100][635,1224]" />
<node index="3" text="" resource-id="dev.navdemo.android:id/bottomNav" class="android.widget.FrameLayout" content-desc="" bounds="[0,2190][1080,2400]" />
</node></hierarchy>
UI hierchary dumped to: /dev/tty"""


class UiautomatorDump(unittest.TestCase):
    nodes = compare.parse_dump(DUMP)

    def test_an_element_is_found_by_its_text_or_its_description(self):
        self.assertEqual(compare.dump_find(self.nodes, "Say hello")["centre"], (191, 731))
        self.assertEqual(compare.dump_find(self.nodes, "Web row 40")["centre"], (540, 2353))
        self.assertIsNone(compare.dump_find(self.nodes, "Nope"))

    def test_an_element_is_found_by_its_id_with_or_without_the_package(self):
        self.assertEqual(compare.dump_find(self.nodes, "id=hello")["centre"], (191, 731))
        self.assertEqual(compare.dump_find(self.nodes, "id=name")["centre"], (339, 1162))

    def test_on_screen_means_its_centre_is_above_the_bottom_navigation(self):
        top = compare.nav_top(self.nodes)
        self.assertEqual(top, 2190)
        self.assertTrue(compare.on_screen_android(compare.dump_find(self.nodes, "Say hello"), top))
        self.assertFalse(compare.on_screen_android(compare.dump_find(self.nodes, "Web row 40"), top))


class Android(unittest.TestCase):
    def test_the_maestro_flow_names_the_platform_s_app(self):
        self.assertTrue(compare.Maestro.flow("dev.navdemo.android")[0].startswith("appId: dev.navdemo.android\n"))
        self.assertTrue(compare.Maestro.flow("dev.navdemo.ios")[0].startswith("appId: dev.navdemo.ios\n"))

    def test_plain_web_is_not_timed_on_android_and_says_why(self):
        for tool in (compare.Androidnav("emulator-5554"), compare.Adb("emulator-5554")):
            self.assertIn("same WebView", tool.can("plain"))
            self.assertIsNone(tool.can("web"))
            self.assertIsNone(tool.can("native"))


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
