"""AXe's driver, with no device: finding text in its tree."""
import os
import sys
import unittest

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from drivers import (
    axe,
    common,
)

TREE = [{"AXLabel": "NavDemo", "frame": {"x": 0, "y": 0, "width": 402, "height": 874}, "children": [
        {"AXLabel": "Say hello", "AXValue": None, "frame": {"x": 16, "y": 322, "width": 93, "height": 34}, "children": []},
        {"AXLabel": "Web row 40", "frame": {"x": 40, "y": 2100, "width": 90, "height": 20}, "children": []},
    ]}]


class AxeTree(unittest.TestCase):
    def test_an_element_is_found_by_label_anywhere_in_the_tree(self):
        self.assertEqual(axe.axe_find(TREE, "Say hello")["frame"]["y"], 322)
        self.assertIsNone(axe.axe_find(TREE, "Nope"))

    def test_on_screen_means_its_centre_is_above_the_tab_bar(self):
        self.assertTrue(common.on_screen(axe.axe_find(TREE, "Say hello"), bottom=791))
        self.assertFalse(common.on_screen(axe.axe_find(TREE, "Web row 40"), bottom=791))


if __name__ == "__main__":
    unittest.main()
