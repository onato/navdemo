"""The demo pages end with half a screen of space, so any element on them can be scrolled to the
middle of the screen. A tool that centres what it reveals (Maestro, so that its tap clears the tab
bar) otherwise swipes at the end of a page until its timeout."""
import os
import re
import unittest

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


def read(*path):
    with open(os.path.join(ROOT, *path)) as f:
        return f.read()


class PageEnds(unittest.TestCase):
    def test_each_web_page_ends_with_half_a_screen(self):
        for page in ("index.html", "page2.html"):
            body = re.search(r"\bbody\s*\{([^}]*)\}", read("shared", "web", page)).group(1)
            self.assertIn("padding-bottom: 50vh", body, page)

    def test_each_native_page_ends_with_half_a_screen(self):
        swift = read("ios", "NavDemo", "NativePageView.swift")
        self.assertEqual(swift.count(".padding(.bottom, pageEnd)"), 2)
        self.assertRegex(swift, r"let pageEnd: CGFloat = \d+")


if __name__ == "__main__":
    unittest.main()
