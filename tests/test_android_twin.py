"""The Android app's native page is a twin of shared/web/index.html and page2.html: the same ids,
texts and order, so one scenario runs on both and a tool's cost on native content can be set
against its cost on the same page in a WebView."""
import os
import re
import unittest

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
MAIN = os.path.join(ROOT, "android", "app", "src", "main")


def read(*path):
    with open(os.path.join(*path)) as f:
        return f.read()


def html_ids(page):
    return re.findall(r'\bid="([^"]+)"', read(ROOT, "shared", "web", page))


def layout(name):
    return read(MAIN, "res", "layout", name)


def layout_ids(xml):
    return re.findall(r'android:id="@\+id/([^"]+)"', xml)


def layout_texts(xml):
    return re.findall(r'android:(?:text|hint)="([^"]+)"', xml)


class FirstPage(unittest.TestCase):
    xml = layout("fragment_native_page.xml")

    def test_every_element_id_of_the_web_page_is_there_in_order(self):
        want = [i for i in html_ids("index.html") if i != "form"]
        self.assertEqual([i for i in layout_ids(self.xml) if i in want], want)

    def test_the_texts_of_the_web_page_are_there_in_order(self):
        want = ["NavDemo Web", "This page is served from the app bundle, so the WebView works offline.",
                "Actions", "Say hello", "Form", "Your name", "Type a name", "Favourite colour", "Send",
                "Navigation", "Second page", "Slow content", "Loading…"]
        self.assertEqual([t for t in layout_texts(self.xml) if t in want], want)


class SecondPage(unittest.TestCase):
    xml = layout("fragment_native_page2.xml")

    def test_its_ids_and_texts_are_the_web_page_s(self):
        self.assertEqual([i for i in layout_ids(self.xml) if i in ("title", "back", "list", "bottom")],
                         ["title", "back", "list", "bottom"])
        self.assertEqual([t for t in layout_texts(self.xml)],
                         ["Second page", "Back to start", "You reached the bottom."])

    def test_its_forty_rows_are_named_and_labelled_as_the_web_page_s(self):
        kt = read(MAIN, "java", "dev", "navdemo", "android", "NativePage.kt")
        self.assertIn("for (i in 1..40)", kt)
        self.assertIn('"Web row $i"', kt)
        self.assertIn(':id/row-$i"', kt)


class Reaching(unittest.TestCase):
    def test_home_opens_the_native_page_above_the_bottom_navigation(self):
        self.assertIn('android:id="@+id/nativePage"', layout("fragment_home.xml"))
        home = read(MAIN, "java", "dev", "navdemo", "android", "HomeFragment.kt")
        self.assertIn("NativePageFragment()", home)
        self.assertIn("addToBackStack", home)

    def test_sending_closes_the_keyboard_so_the_result_is_not_under_it(self):
        kt = read(MAIN, "java", "dev", "navdemo", "android", "NativePage.kt")
        self.assertIn("hideSoftInputFromWindow", kt)

    def test_each_page_ends_with_half_a_screen(self):
        kt = read(MAIN, "java", "dev", "navdemo", "android", "NativePage.kt")
        self.assertEqual(kt.count("endWithHalfAScreen("), 3)  # the helper and its two calls


if __name__ == "__main__":
    unittest.main()
