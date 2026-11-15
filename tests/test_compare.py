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

    def test_maestro_reaches_the_field_by_its_id_on_android_where_only_the_label_has_the_text(self):
        self.assertIn('- tapOn:\n    id: "name"', compare.Maestro.flow("dev.navdemo.android")[0])
        self.assertIn('- tapOn:\n    text: "Your name"\n    index: 1', compare.Maestro.flow("dev.navdemo.ios")[0])

    def test_a_reveal_may_take_maestro_a_minute_of_swipes(self):
        # Its default 20s ran out before row 40 on Android's web page.
        self.assertEqual(compare.Maestro.flow("dev.navdemo.android")[0].count("    timeout: 60000"), 2)

    def test_plain_web_is_not_timed_on_android_and_says_why(self):
        for tool in (compare.Androidnav("emulator-5554"), compare.Adb("emulator-5554")):
            self.assertIn("same WebView", tool.can("plain"))
            self.assertIsNone(tool.can("web"))
            self.assertIsNone(tool.can("native"))


class Appium(unittest.TestCase):
    def test_the_session_attaches_to_the_app_already_open_and_neither_launches_nor_resets_it(self):
        caps = compare.Appium.capabilities("UDID-1")["capabilities"]["alwaysMatch"]
        self.assertEqual(caps["platformName"], "iOS")
        self.assertEqual(caps["appium:automationName"], "XCUITest")
        self.assertEqual(caps["appium:udid"], "UDID-1")
        self.assertEqual(caps["appium:bundleId"], "dev.navdemo.ios")
        self.assertIs(caps["appium:noReset"], True)
        self.assertIs(caps["appium:autoLaunch"], False)

    def test_the_session_matches_navdemo_by_the_name_web_inspector_lists_it_under(self):
        # Web Inspector lists the app as process-NavDemo, not by its bundle id, and Appium matches
        # web apps by bundle id: without this it retries for 10s and finds no web context.
        caps = compare.Appium.capabilities("UDID-1")["capabilities"]["alwaysMatch"]
        self.assertEqual(caps["appium:additionalWebviewBundleIds"], ["process-NavDemo"])

    def test_native_steps_find_by_predicate_and_web_steps_by_text_or_id(self):
        plan = compare.Appium.plan
        self.assertEqual(plan("read", None, "native"), [("source",)])
        self.assertEqual(plan("read", None, "web"), [("source",)])
        self.assertEqual(plan("tap", "Say hello", "native"),
                         [("find", "-ios predicate string", "label == 'Say hello'"), ("click",)])
        self.assertEqual(plan("tap", "Say hello", "web"),
                         [("find", "xpath", "//*[normalize-space(text())='Say hello']"), ("click",)])
        self.assertEqual(plan("wait", "Sent: Ada, Red", "web"),
                         [("find", "xpath", "//*[normalize-space(text())='Sent: Ada, Red']")])

    def test_typing_and_submitting_go_to_the_name_field(self):
        plan = compare.Appium.plan
        field = ("find", "-ios predicate string", "type == 'XCUIElementTypeTextField' AND label == 'Your name'")
        self.assertEqual(plan("type", "Ada", "native"), [field, ("keys", "Ada")])
        self.assertEqual(plan("submit", None, "native"), [field, ("keys", "\n")])
        self.assertEqual(plan("type", "Ada", "web"), [("find", "css selector", "#name"), ("keys", "Ada")])
        self.assertEqual(plan("submit", None, "web"), [("find", "css selector", "#name"), ("keys", "")])

    def test_a_native_reveal_scrolls_to_the_found_element_then_checks_and_clicks_and_a_web_one_only_clicks(self):
        # Web clicks are dispatched in the page by JavaScript, so nothing needs to be on screen.
        # mobile: scroll is for tables and collection views; the twin is a SwiftUI scroll view.
        self.assertEqual(compare.Appium.plan("reveal", "Web row 40", "native"), [
            ("find", "-ios predicate string", "label == 'Web row 40'"),
            ("scroll to",),
            ("on screen",),
            ("click",),
        ])
        self.assertEqual(compare.Appium.plan("reveal", "Web row 40", "web"),
                         [("find", "xpath", "//*[normalize-space(text())='Web row 40']"), ("click",)])

    def test_the_web_context_is_the_one_webview_listed_and_none_or_several_is_an_error_naming_them(self):
        pick = compare.Appium.web_context
        self.assertEqual(pick(["NATIVE_APP", "WEBVIEW_123.1"]), "WEBVIEW_123.1")
        self.assertEqual(pick([{"id": "NATIVE_APP"}, {"id": "WEBVIEW_9.2", "url": "file:///index.html"}]), "WEBVIEW_9.2")
        with self.assertRaisesRegex(compare.StepFailed, "NATIVE_APP"):
            pick(["NATIVE_APP"])
        with self.assertRaisesRegex(compare.StepFailed, "WEBVIEW_1.1.*WEBVIEW_2.1"):
            pick(["NATIVE_APP", "WEBVIEW_1.1", "WEBVIEW_2.1"])

    def test_an_element_is_on_screen_only_if_its_centre_is_above_the_tab_bar(self):
        self.assertTrue(compare.rect_on_screen({"x": 16, "y": 322, "width": 93, "height": 34}))
        self.assertFalse(compare.rect_on_screen({"x": 40, "y": 780, "width": 90, "height": 30}))
        self.assertFalse(compare.rect_on_screen({"x": 40, "y": -40, "width": 90, "height": 20}))

    def test_a_found_element_s_id_is_read_from_the_w3c_key(self):
        # As Appium's XCUITest driver answers a native find.
        reply = {"ELEMENT": "A1", "element-6066-11e4-a52e-4f735466cecf": "A1"}
        self.assertEqual(compare.element_id(reply), "A1")
        self.assertEqual(compare.element_id({"element-6066-11e4-a52e-4f735466cecf": "W2"}), "W2")

    def test_a_webdriver_error_reply_raises_with_its_message(self):
        self.assertEqual(compare.webdriver_value({"value": {"ELEMENT": "e1"}}), {"ELEMENT": "e1"})
        with self.assertRaisesRegex(compare.StepFailed, "no such element: An element could not be located"):
            compare.webdriver_value({"value": {"error": "no such element", "message": "An element could not be located"}})


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
