#!/usr/bin/env python3
"""Time one scenario on NavDemo with each tool, on each kind of screen, the same way each time.

    tests/compare.py --udid UDID [--runs 3] [--tools simnav,axe,maestro,appium] [--targets native,web,plain]
                     [--out tests/results]
    tests/compare.py --platform android --serial SERIAL [--runs 3] [--tools androidnav,adb,maestro]
                     [--targets native,web,plain]

Targets are the same page three ways: `native` (Home → Native page, a SwiftUI twin of the web
page), `web` (the Web tab: an inspectable WKWebView) and `plain` (the Plain web tab: the same page
in a WebView that is not inspectable). The scenario reads the screen, taps a button and waits for
its result, types into a field and submits, follows a link that sits under the tab bar, and taps
a row far below the fold on the next page.

Each run relaunches the app and opens the target with simnav (untimed), then times every step:
for simnav and AXe the wall time of each command, process start included, as an agent pays it;
for Maestro the duration it records for each command, with its start-up (JVM, XCTest driver)
reported apart; for Appium the wall time of its WebDriver calls, with session start and the switch
to the page's web context reported apart. Appium's web clicks and keys are dispatched in the page
by JavaScript, not touched, so its web reveal is a click with no scrolling. A tool that cannot do
a step on a target is reported as such, not timed.

On Android the tools are androidnav, adb (`uiautomator dump` and `input`) and Maestro, and
`native` is Home → Native page, a twin made of Android views. WebView debugging is one switch for
the whole app there, so `plain` is the same WebView as `web` and is reported, not timed. One
UiAutomation connection is allowed per device: androidnav's server holds it, so it is stopped
before adb or Maestro runs.

Writes <out>/compare-<time>.json (compare-android-<time>.json) and prints a Markdown table.
"""
import argparse
import datetime
import json
import os
import platform
import statistics
import subprocess
import sys

from drivers.adb import Adb
from drivers.androidnav import Androidnav
from drivers.appium import Appium, appium_versions
from drivers.axe import Axe
from drivers.common import STEP_NAMES, Cannot, StepFailed, sh
from drivers.maestro import Maestro
from drivers.simnav import Simnav


def summarise(runs, cannot=None):
    if cannot:
        return {"cannot": cannot}
    steps = [statistics.median(r[i] for r in runs) for i in range(len(runs[0]))]
    return {"steps": steps, "total": statistics.median(sum(r) for r in runs), "runs": runs}


def environment(udid):
    xcode = sh(["xcodebuild", "-version"], check=False).stdout.split("\n")
    runtime = sh(["xcrun", "simctl", "list", "devices", "-j"], check=False).stdout
    rt = next((k.rsplit(".", 1)[-1] for k, v in json.loads(runtime)["devices"].items() for d in v if d["udid"] == udid), "?")
    return {"xcode": " ".join(x for x in xcode[:2] if x), "runtime": rt, "host": platform.mac_ver()[0],
            "load": os.getloadavg()[0], "axe": sh(["axe", "--version"], check=False).stdout.strip(),
            "maestro": sh(["maestro", "--version"], check=False).stdout.strip().splitlines()[-1:],
            "appium": appium_versions(),
            "when": datetime.datetime.now().isoformat(timespec="seconds")}


def android_environment(serial):
    def prop(name):
        return sh(["adb", "-s", serial, "shell", "getprop", name], check=False).stdout.strip()
    return {"android": prop("ro.build.version.release"), "sdk": prop("ro.build.version.sdk"),
            "avd": sh(["adb", "-s", serial, "emu", "avd", "name"], check=False).stdout.split("\n")[0].strip(),
            "host": platform.mac_ver()[0], "load": os.getloadavg()[0],
            "maestro": sh(["maestro", "--version"], check=False).stdout.strip().splitlines()[-1:],
            "when": datetime.datetime.now().isoformat(timespec="seconds")}


def table(results):
    tools = list(results)
    cells = [(t, g) for t in tools for g in results[t]]
    head = "| step | " + " | ".join(f"{t} {g}" for t, g in cells) + " |"
    rows = [head, "|---" * (len(cells) + 1) + "|"]
    for i, name in enumerate(STEP_NAMES + ["**total**"]):
        row = []
        for t, g in cells:
            s = results[t][g]
            if "cannot" in s:
                row.append("cannot" if i == 0 else "")
            elif "error" in s:
                row.append("failed" if i == 0 else "")
            else:
                ms = s["total"] if i == len(STEP_NAMES) else s["steps"][i]
                row.append(f"{ms:,.0f}")
        rows.append(f"| {name} | " + " | ".join(row) + " |")
    return "\n".join(rows)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--platform", choices=["ios", "android"], default="ios")
    ap.add_argument("--udid")
    ap.add_argument("--serial")
    ap.add_argument("--runs", type=int, default=3)
    ap.add_argument("--tools")
    ap.add_argument("--targets", default="native,web,plain")
    ap.add_argument("--out", default=os.path.join(os.path.dirname(os.path.abspath(__file__)), "results"))
    a = ap.parse_args()
    android = a.platform == "android"
    device = a.serial if android else a.udid
    if not device:
        ap.error("--serial is required on Android" if android else "--udid is required")
    if android:
        kinds = {"androidnav": Androidnav, "adb": Adb, "maestro": lambda d: Maestro(d, android=True)}
    else:
        kinds = {"simnav": Simnav, "axe": Axe, "maestro": Maestro, "appium": Appium}
    results, extra, notes = {}, {}, []
    for name in (a.tools or ",".join(kinds)).split(","):
        tool = kinds[name](device)
        results[name] = {}
        for target in a.targets.split(","):
            why = tool.can(target)
            if why:
                results[name][target] = summarise([], cannot=why)
                continue
            runs = []
            try:
                for i in range(a.runs):
                    tool.open(target)
                    runs.append(tool.run(target))
                    print(f"{name} {target} run {i + 1}: {sum(runs[-1]):,.0f}ms", file=sys.stderr)
                results[name][target] = summarise(runs)
            except Cannot as e:
                results[name][target] = summarise([], cannot=str(e))
                print(f"{name} {target}: cannot: {e}", file=sys.stderr)
            except (StepFailed, subprocess.TimeoutExpired) as e:
                results[name][target] = {"error": str(e), "runs": runs}
                print(f"{name} {target}: {e}", file=sys.stderr)
        if hasattr(tool, "extras"):
            values, lines = tool.extras(a.targets.split(","))
            extra.update(values)
            notes += lines
    os.makedirs(a.out, exist_ok=True)
    stamp = datetime.datetime.now().strftime("%Y%m%d-%H%M%S")
    env = android_environment(device) if android else environment(device)
    doc = {"platform": a.platform, "environment": env, "scenario": STEP_NAMES, "results": results, **extra}
    with open(os.path.join(a.out, f"compare-{'android-' if android else ''}{stamp}.json"), "w") as f:
        json.dump(doc, f, indent=1)
    print(table(results))
    if notes:
        print("\n" + "\n".join(notes))



if __name__ == "__main__":
    main()
