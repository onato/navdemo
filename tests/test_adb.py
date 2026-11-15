"""adb's driver, with no device: reading a `uiautomator dump`."""
import os
import sys
import unittest

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from drivers import adb

DUMP = """<?xml version='1.0' encoding='UTF-8' standalone='yes' ?><hierarchy rotation="0">
<node index="0" text="" resource-id="" class="android.widget.FrameLayout" content-desc="" bounds="[0,0][1080,2400]">
<node index="0" text="Say hello" resource-id="dev.navdemo.android:id/hello" class="android.widget.Button" content-desc="" bounds="[44,665][338,797]" />
<node index="1" text="• Web row 40" resource-id="" class="android.widget.TextView" content-desc="Web row 40" bounds="[44,2300][1036,2407]" />
<node index="2" text="" resource-id="name" class="android.widget.EditText" content-desc="" bounds="[44,1100][635,1224]" />
<node index="3" text="" resource-id="dev.navdemo.android:id/bottomNav" class="android.widget.FrameLayout" content-desc="" bounds="[0,2190][1080,2400]" />
</node></hierarchy>
UI hierchary dumped to: /dev/tty"""


class UiautomatorDump(unittest.TestCase):
    nodes = adb.parse_dump(DUMP)

    def test_an_element_is_found_by_its_text_or_its_description(self):
        self.assertEqual(adb.dump_find(self.nodes, "Say hello")["centre"], (191, 731))
        self.assertEqual(adb.dump_find(self.nodes, "Web row 40")["centre"], (540, 2353))
        self.assertIsNone(adb.dump_find(self.nodes, "Nope"))

    def test_an_element_is_found_by_its_id_with_or_without_the_package(self):
        self.assertEqual(adb.dump_find(self.nodes, "id=hello")["centre"], (191, 731))
        self.assertEqual(adb.dump_find(self.nodes, "id=name")["centre"], (339, 1162))

    def test_on_screen_means_its_centre_is_above_the_bottom_navigation(self):
        top = adb.nav_top(self.nodes)
        self.assertEqual(top, 2190)
        self.assertTrue(adb.on_screen_android(adb.dump_find(self.nodes, "Say hello"), top))
        self.assertFalse(adb.on_screen_android(adb.dump_find(self.nodes, "Web row 40"), top))


if __name__ == "__main__":
    unittest.main()
