#!/usr/bin/env python3
"""Time the NavDemo tour: run it several times and report each step's median and p90.

    tests/perf.py --platform ios|android [--device ID] [--runs 5] [--warmup 1]
                  [--tour PATH] [--baseline PATH] [--save-baseline]

The app must be installed and signed in (tests/smoke.sh, or mobile-device sign-in). Each run
relaunches the app first, so every run starts from the same screen with the same state.

A tour step either drives the app (tap, type, find, back, scroll) or waits on it (wait, loaded).
The `driver` row adds up the first kind, the driver's own cost; the `app` row adds up the second,
which is mostly the app's animations and page loads. Compare drivers, or a driver before and after
a change, on the `driver` row.

Against a baseline (tests/perf-baseline.<platform>.json by default), a row that is slower by more
than a fifth and more than 10ms is marked; the run exits 1 when the driver, app or total row is.
Single steps are too noisy to fail on.
"""
import argparse
import json
import os
import re
import statistics
import subprocess
import sys
import tomllib
from dataclasses import dataclass

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DRIVERS = {
    "ios": (os.path.expanduser("~/.claude/skills/simnav/bin/simnav"), "--udid"),
    "android": (os.path.expanduser("~/.claude/skills/androidnav/androidnav"), "--serial"),
}
SIMPOOL = os.path.join(os.environ.get("SIM_POOL_SKILL", os.path.expanduser("~/.claude/skills/sim-pool")),
                       "scripts", "simpool")
TOTALS = ("driver", "app", "total")
FLOOR_MS = 10

STEP = re.compile(r"^\s*(\d+)ms\s+(.*?)\s+(→|✗)\s?(.*)$")


class TourFailed(Exception):
    pass


@dataclass
class Step:
    key: str
    command: str
    ms: int


def parse_run(output):
    """The steps of one `run`, in order. A step is keyed by its position, since a tour repeats
    commands (`scroll down` twice) whose times must not be pooled."""
    steps = []
    for line in output.splitlines():
        m = STEP.match(line)
        if not m:
            continue
        ms, command, mark, rest = int(m.group(1)), m.group(2), m.group(3), m.group(4)
        if mark == "✗":
            raise TourFailed(f"step {len(steps) + 1} `{command}` failed: {rest}")
        steps.append(Step(f"{len(steps) + 1:02d} {command}", command, ms))
    if not steps:
        raise TourFailed("the driver ran no steps: " + output.strip()[-300:])
    return steps


def kind(command):
    return "app" if command.split()[0] in ("wait", "loaded") else "driver"


def stats(values):
    ordered = sorted(values)
    return {"median": statistics.median(ordered), "p90": ordered[max(0, int(len(ordered) * 0.9 + 0.5) - 1)]}


def summarise(runs):
    """Median and p90 per step, then per kind and for the whole tour."""
    rows = {}
    for key in [s.key for s in runs[0]]:
        rows[key] = stats([next(s.ms for s in run if s.key == key) for run in runs])
    for k in ("driver", "app"):
        rows[k] = stats([sum(s.ms for s in run if kind(s.command) == k) for run in runs])
    rows["total"] = stats([sum(s.ms for s in run) for run in runs])
    return rows


def regressed(now, before):
    return now - before > max(FLOOR_MS, before * 0.2)


def regressions(now, base):
    return [k for k in TOTALS if k in base and regressed(now[k]["median"], base[k]["median"])]


def profile(platform):
    with open(os.path.join(ROOT, ".mobile-device", "app.toml"), "rb") as f:
        return tomllib.load(f)[platform]


def device(platform, given):
    """The device to drive: the one named, else this session's own lease. Never a guess."""
    if given:
        return given
    r = subprocess.run([SIMPOOL, "mine", "--" + platform], capture_output=True, text=True, check=False)
    if r.returncode != 0 or not r.stdout.strip():
        sys.exit(f"perf: no {platform} device: pass --device, or lease one (simpool acquire)")
    return r.stdout.split()[0]


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--platform", choices=sorted(DRIVERS), required=True)
    ap.add_argument("--device")
    ap.add_argument("--runs", type=int, default=5)
    ap.add_argument("--warmup", type=int, default=1, help="untimed runs first (daemon start, caches)")
    ap.add_argument("--tour")
    ap.add_argument("--baseline")
    ap.add_argument("--save-baseline", action="store_true")
    a = ap.parse_args()

    tour = a.tour or os.path.join(ROOT, "tests", f"tour.{a.platform}.nav")
    baseline = a.baseline or os.path.join(ROOT, "tests", f"perf-baseline.{a.platform}.json")
    app = profile(a.platform)
    exe, flag = DRIVERS[a.platform]
    target = device(a.platform, a.device)

    def drive(*args, **kw):
        return subprocess.run([exe, flag, target, *args], capture_output=True, text=True, check=False, **kw)

    def one_run():
        drive("launch", app["bundle"])
        if drive("wait", *app["signed_in"].split(), "--timeout", "15").returncode != 0:
            sys.exit("perf: the app is not signed in; run tests/smoke.sh or mobile-device sign-in first")
        with open(tour) as f:
            r = drive("run", "-", input=f.read())
        return parse_run(r.stdout + r.stderr)

    runs = []
    try:
        for i in range(a.warmup + a.runs):
            steps = one_run()
            if i >= a.warmup:
                runs.append(steps)
            print(f"run {i + 1}/{a.warmup + a.runs}{' (warm-up)' if i < a.warmup else ''}: "
                  f"{sum(s.ms for s in steps)}ms", file=sys.stderr)
    except TourFailed as e:
        sys.exit(f"perf: {e}")

    rows = summarise(runs)
    base = {}
    if os.path.exists(baseline) and not a.save_baseline:
        with open(baseline) as f:
            base = json.load(f)
    load = os.getloadavg()[0]
    print(f"{a.platform} {target}, {a.runs} runs, host load {load:.1f}"
          + (f" (baseline at {base['_load']:.1f})" if "_load" in base else ""))
    print(f"{'step':<46} {'median':>8} {'p90':>8} {'baseline':>9}")
    for key, row in rows.items():
        if key == "driver":
            print()
        old = (base.get(key) or {}).get("median")
        mark = "  SLOWER" if old is not None and regressed(row["median"], old) else ""
        print(f"{key[:46]:<46} {row['median']:>6.0f}ms {row['p90']:>6.0f}ms "
              f"{f'{old:.0f}ms' if old is not None else '':>9}{mark}")

    if a.save_baseline:
        with open(baseline, "w") as f:
            json.dump({**rows, "_load": load, "_runs": a.runs}, f, indent=2)
        print(f"\nsaved baseline to {os.path.relpath(baseline, ROOT)}")
        return 0
    worse = regressions(rows, base)
    print("\nRESULT:", f"REGRESSED ({', '.join(worse)})" if worse else ("PASS" if base else "no baseline"))
    return 1 if worse else 0


if __name__ == "__main__":
    sys.exit(main())
