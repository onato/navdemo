"""Appium's driver, with no device: the session, the requests each step becomes, and its replies."""
import os
import sys
import unittest

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from drivers import (
    appium,
    common,
)


class Appium(unittest.TestCase):
    def test_the_session_attaches_to_the_app_already_open_and_neither_launches_nor_resets_it(self):
        caps = appium.Appium.capabilities("UDID-1")["capabilities"]["alwaysMatch"]
        self.assertEqual(caps["platformName"], "iOS")
        self.assertEqual(caps["appium:automationName"], "XCUITest")
        self.assertEqual(caps["appium:udid"], "UDID-1")
        self.assertEqual(caps["appium:bundleId"], "dev.navdemo.ios")
        self.assertIs(caps["appium:noReset"], True)
        self.assertIs(caps["appium:autoLaunch"], False)

    def test_the_session_matches_navdemo_by_the_name_web_inspector_lists_it_under(self):
        # Web Inspector lists the app as process-NavDemo, not by its bundle id, and Appium matches
        # web apps by bundle id: without this it retries for 10s and finds no web context.
        caps = appium.Appium.capabilities("UDID-1")["capabilities"]["alwaysMatch"]
        self.assertEqual(caps["appium:additionalWebviewBundleIds"], ["process-NavDemo"])

    def test_native_steps_find_by_predicate_and_web_steps_by_text_or_id(self):
        plan = appium.Appium.plan
        self.assertEqual(plan("read", None, "native"), [("source",)])
        self.assertEqual(plan("read", None, "web"), [("source",)])
        self.assertEqual(plan("tap", "Say hello", "native"),
                         [("find", "-ios predicate string", "label == 'Say hello'"), ("click",)])
        self.assertEqual(plan("tap", "Say hello", "web"),
                         [("find", "xpath", "//*[normalize-space(text())='Say hello']"), ("click",)])
        self.assertEqual(plan("wait", "Sent: Ada, Red", "web"),
                         [("find", "xpath", "//*[normalize-space(text())='Sent: Ada, Red']")])

    def test_typing_and_submitting_go_to_the_name_field(self):
        plan = appium.Appium.plan
        field = ("find", "-ios predicate string", "type == 'XCUIElementTypeTextField' AND label == 'Your name'")
        self.assertEqual(plan("type", "Ada", "native"), [field, ("keys", "Ada")])
        self.assertEqual(plan("submit", None, "native"), [field, ("keys", "\n")])
        self.assertEqual(plan("type", "Ada", "web"), [("find", "css selector", "#name"), ("keys", "Ada")])
        self.assertEqual(plan("submit", None, "web"), [("find", "css selector", "#name"), ("keys", "")])

    def test_a_native_reveal_scrolls_to_the_found_element_then_checks_and_clicks_and_a_web_one_only_clicks(self):
        # Web clicks are dispatched in the page by JavaScript, so nothing needs to be on screen.
        # mobile: scroll is for tables and collection views; the twin is a SwiftUI scroll view.
        self.assertEqual(appium.Appium.plan("reveal", "Web row 40", "native"), [
            ("find", "-ios predicate string", "label == 'Web row 40'"),
            ("scroll to",),
            ("on screen",),
            ("click",),
        ])
        self.assertEqual(appium.Appium.plan("reveal", "Web row 40", "web"),
                         [("find", "xpath", "//*[normalize-space(text())='Web row 40']"), ("click",)])

    def test_the_web_context_is_the_one_webview_listed_and_none_or_several_is_an_error_naming_them(self):
        pick = appium.Appium.web_context
        self.assertEqual(pick(["NATIVE_APP", "WEBVIEW_123.1"]), "WEBVIEW_123.1")
        self.assertEqual(pick([{"id": "NATIVE_APP"}, {"id": "WEBVIEW_9.2", "url": "file:///index.html"}]), "WEBVIEW_9.2")
        with self.assertRaisesRegex(common.StepFailed, "NATIVE_APP"):
            pick(["NATIVE_APP"])
        with self.assertRaisesRegex(common.StepFailed, "WEBVIEW_1.1.*WEBVIEW_2.1"):
            pick(["NATIVE_APP", "WEBVIEW_1.1", "WEBVIEW_2.1"])

    def test_an_element_is_on_screen_only_if_its_centre_is_above_the_tab_bar(self):
        self.assertTrue(appium.rect_on_screen({"x": 16, "y": 322, "width": 93, "height": 34}))
        self.assertFalse(appium.rect_on_screen({"x": 40, "y": 780, "width": 90, "height": 30}))
        self.assertFalse(appium.rect_on_screen({"x": 40, "y": -40, "width": 90, "height": 20}))

    def test_a_found_element_s_id_is_read_from_the_w3c_key(self):
        # As Appium's XCUITest driver answers a native find.
        reply = {"ELEMENT": "A1", "element-6066-11e4-a52e-4f735466cecf": "A1"}
        self.assertEqual(appium.element_id(reply), "A1")
        self.assertEqual(appium.element_id({"element-6066-11e4-a52e-4f735466cecf": "W2"}), "W2")

    def test_a_webdriver_error_reply_raises_with_its_message(self):
        self.assertEqual(appium.webdriver_value({"value": {"ELEMENT": "e1"}}), {"ELEMENT": "e1"})
        with self.assertRaisesRegex(common.StepFailed, "no such element: An element could not be located"):
            appium.webdriver_value({"value": {"error": "no such element", "message": "An element could not be located"}})


class Extras(unittest.TestCase):
    def test_session_start_server_start_and_the_switch_to_the_web_context_are_reported_apart(self):
        tool = appium.Appium("UDID-1")
        tool.server_ms, tool.startup, tool.context = 1040, [2400, 2600, 2500], [120, 130, 110]
        values, notes = tool.extras(["native", "web"])
        self.assertEqual(values, {"appium_server_ms": 1040, "appium_startup_ms": 2500, "appium_context_ms": 120})
        self.assertEqual(notes, [
            "Appium session start per run (not in the table): 2,500ms; server start 1,040ms once",
            "Appium switch to the web context (not in the table): 120ms",
        ])

    def test_with_plain_web_among_the_targets_it_also_records_the_hidden_page_check(self):
        tool = appium.Appium("UDID-1")
        tool.server_ms, tool.startup = 1040, [2500]
        tool.hidden_page = lambda: {"contexts": [{"id": "NATIVE_APP"}], "pages": []}
        values, notes = tool.extras(["native", "plain"])
        self.assertEqual(values["appium_hidden_page"], {"contexts": [{"id": "NATIVE_APP"}], "pages": []})
        self.assertTrue(notes[-1].startswith('Appium on Plain web after Web: {"contexts"'))

    def test_a_failed_hidden_page_check_is_recorded_not_raised(self):
        tool = appium.Appium("UDID-1")

        def fails():
            raise common.StepFailed("no session")
        tool.hidden_page = fails
        values, _ = tool.extras(["plain"])
        self.assertEqual(values["appium_hidden_page"], {"error": "no session"})


if __name__ == "__main__":
    unittest.main()
