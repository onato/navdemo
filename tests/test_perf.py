"""perf.py's parsing and arithmetic: no device. Run with `python3 -m unittest discover -s tests`."""
import unittest

import perf

PASSING = """\
  454ms  tap General → pressed Button "General" #com.apple.settings.general (16,293 370x52)
  208ms  wait About → Button "About" #About (20,391 362x53)
   88ms  scroll down → scrolled
   90ms  scroll down → scrolled
total 840ms
"""

FAILING = """\
   32ms  tap General --hid → touched  "General" (16,293 370x52)
 5111ms  back ✗ not found after 5.0s: id=BackButton native
FAILED after 5143ms
"""


class ParseRun(unittest.TestCase):
    def test_each_step_is_keyed_by_its_position_so_repeated_commands_stay_apart(self):
        steps = perf.parse_run(PASSING)
        self.assertEqual([s.key for s in steps],
                         ["01 tap General", "02 wait About", "03 scroll down", "04 scroll down"])
        self.assertEqual([s.ms for s in steps], [454, 208, 88, 90])

    def test_a_failed_step_raises_with_the_step_and_its_reason(self):
        with self.assertRaises(perf.TourFailed) as e:
            perf.parse_run(FAILING)
        self.assertIn("back", str(e.exception))
        self.assertIn("not found after 5.0s", str(e.exception))

    def test_output_with_no_steps_is_a_failure(self):
        with self.assertRaises(perf.TourFailed):
            perf.parse_run("simnav: no device given\n")


class Kinds(unittest.TestCase):
    def test_waits_and_load_checks_measure_the_app_and_the_rest_the_driver(self):
        self.assertEqual(perf.kind("wait id=increment"), "app")
        self.assertEqual(perf.kind("loaded"), "app")
        self.assertEqual(perf.kind("tap web Send"), "driver")
        self.assertEqual(perf.kind("type Ada"), "driver")


class Summarise(unittest.TestCase):
    def test_medians_per_step_and_per_kind_with_a_tour_total(self):
        runs = [perf.parse_run(PASSING),
                perf.parse_run(PASSING.replace("454ms", "500ms").replace("208ms", "300ms"))]
        rows = perf.summarise(runs)
        self.assertEqual(rows["01 tap General"]["median"], 477)
        self.assertEqual(rows["driver"]["median"], (454 + 88 + 90 + 500 + 88 + 90) / 2)
        self.assertEqual(rows["app"]["median"], 254)
        self.assertEqual(rows["total"]["median"], (840 + 978) / 2)


class Compare(unittest.TestCase):
    def test_slower_by_more_than_a_fifth_and_the_floor_is_a_regression(self):
        self.assertTrue(perf.regressed(now=130, before=100))

    def test_noise_below_the_floor_or_the_fraction_is_not(self):
        self.assertFalse(perf.regressed(now=119, before=100))
        self.assertFalse(perf.regressed(now=12, before=8))

    def test_only_the_totals_decide_the_verdict(self):
        base = {"01 tap General": {"median": 10}, "driver": {"median": 100}, "app": {"median": 100},
                "total": {"median": 200}}
        now = {"01 tap General": {"median": 50}, "driver": {"median": 105}, "app": {"median": 100},
               "total": {"median": 205}}
        self.assertEqual(perf.regressions(now, base), [])
        now["driver"]["median"] = 200
        self.assertEqual(perf.regressions(now, base), ["driver"])


class Profile(unittest.TestCase):
    def test_the_bundle_and_signed_in_marker_come_from_the_app_profile(self):
        p = perf.profile("ios")
        self.assertEqual(p["bundle"], "dev.navdemo.ios")
        self.assertEqual(p["signed_in"], "type=TabButton label=Home")


if __name__ == "__main__":
    unittest.main()
