"""The Android comparison, with no device: Maestro's flow per platform, and plain web not timed."""
import os
import sys
import unittest

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from drivers import (
    adb,
    androidnav,
    maestro,
)


class Android(unittest.TestCase):
    def test_the_maestro_flow_names_the_platform_s_app(self):
        self.assertTrue(maestro.Maestro.flow("dev.navdemo.android")[0].startswith("appId: dev.navdemo.android\n"))
        self.assertTrue(maestro.Maestro.flow("dev.navdemo.ios")[0].startswith("appId: dev.navdemo.ios\n"))

    def test_maestro_reaches_the_field_by_its_id_on_android_where_only_the_label_has_the_text(self):
        self.assertIn('- tapOn:\n    id: "name"', maestro.Maestro.flow("dev.navdemo.android")[0])
        self.assertIn('- tapOn:\n    text: "Your name"\n    index: 1', maestro.Maestro.flow("dev.navdemo.ios")[0])

    def test_a_reveal_may_take_maestro_a_minute_of_swipes(self):
        # Its default 20s ran out before row 40 on Android's web page.
        self.assertEqual(maestro.Maestro.flow("dev.navdemo.android")[0].count("    timeout: 60000"), 2)

    def test_plain_web_is_not_timed_on_android_and_says_why(self):
        for tool in (androidnav.Androidnav("emulator-5554"), adb.Adb("emulator-5554")):
            self.assertIn("same WebView", tool.can("plain"))
            self.assertIsNone(tool.can("web"))
            self.assertIsNone(tool.can("native"))


if __name__ == "__main__":
    unittest.main()
