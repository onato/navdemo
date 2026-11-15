#!/usr/bin/env python3
"""Time one scenario on NavDemo with each tool, on each kind of screen, the same way each time.

    tests/compare.py --udid UDID [--runs 3] [--tools simnav,axe,maestro] [--targets native,web,plain]
                     [--out tests/results]

Targets are the same page three ways: `native` (Home → Native page, a SwiftUI twin of the web
page), `web` (the Web tab: an inspectable WKWebView) and `plain` (the Plain web tab: the same page
in a WebView that is not inspectable). The scenario reads the screen, taps a button and waits for
its result, types into a field and submits, follows a link that sits under the tab bar, and taps
a row far below the fold on the next page.

Each run relaunches the app and opens the target with simnav (untimed), then times every step:
for simnav and AXe the wall time of each command, process start included, as an agent pays it;
for Maestro the duration it records for each command, with its start-up (JVM, XCTest driver)
reported apart. A tool that cannot do a step on a target is reported as such, not timed.

Writes <out>/compare-<time>.json and prints a Markdown table.
"""
import argparse
import datetime
import json
import os
import platform
import statistics
import subprocess
import sys
import tempfile
import time

SIMNAV = os.path.expanduser("~/.claude/skills/simnav/bin/simnav")
BUNDLE = "dev.navdemo.ios"
TAB_BAR_TOP = 791   # iPhone 17 Pro, points

# (what, argument). `reveal` means: bring it on screen as the tool does, then tap it.
SCENARIO = [
    ("read", None),
    ("tap", "Say hello"),
    ("wait", "Hello from the web"),
    ("type", "Ada"),
    ("submit", None),
    ("wait", "Sent: Ada, Red"),
    ("reveal", "Second page"),
    ("wait", "Web row 1"),
    ("reveal", "Web row 40"),
]
STEP_NAMES = [f"{w} {a}" if a else w for w, a in SCENARIO]

TARGETS = {
    "native": [["tap", "Home"], ["tap", "id=nativePage"], ["wait", "Say hello"]],
    "web": [["tap", "Web"], ["wait", "web", "Say hello"]],
    "plain": [["tap", "Plain web"], ["wait", "web", "Say hello"]],
}


class StepFailed(Exception):
    pass


# MARK: - Pure helpers (tests/test_compare.py)

MAESTRO_SETUP = {"defineVariablesCommand", "applyConfigurationCommand"}


def maestro_durations(report):
    """(command, ms) for each command Maestro ran for the scenario, from its commands.json."""
    out = []
    for c in report:
        name = next(iter(c["command"]))
        if name in MAESTRO_SETUP:
            continue
        meta = c.get("metadata", {})
        if meta.get("status") != "COMPLETED":
            raise StepFailed(f"Maestro {name}: {meta.get('status')} {meta.get('error', '')}".strip())
        out.append((name, meta.get("duration", 0)))
    return out


def group(durations, sizes):
    """Sums consecutive command durations into scenario steps of the given sizes."""
    if sum(sizes) != len(durations):
        raise StepFailed(f"Maestro ran {len(durations)} commands, the flow has {sum(sizes)}")
    out, i = [], 0
    for n in sizes:
        out.append(sum(ms for _, ms in durations[i:i + n]))
        i += n
    return out


def axe_find(tree, label):
    for e in tree:
        if e.get("AXLabel") == label or e.get("AXValue") == label:
            return e
        found = axe_find(e.get("children") or [], label)
        if found:
            return found
    return None


def on_screen(e, bottom=TAB_BAR_TOP):
    f = e["frame"]
    cy = f["y"] + f["height"] / 2
    return 0 < cy < bottom


def summarise(runs, cannot=None):
    if cannot:
        return {"cannot": cannot}
    steps = [statistics.median(r[i] for r in runs) for i in range(len(runs[0]))]
    return {"steps": steps, "total": statistics.median(sum(r) for r in runs), "runs": runs}


# MARK: - Device

def sh(args, timeout=60, check=True):
    r = subprocess.run(args, capture_output=True, text=True, timeout=timeout, check=False)
    if check and r.returncode != 0:
        raise StepFailed(f"{' '.join(args[:4])}…: {(r.stderr or r.stdout).strip()[-300:]}")
    return r


def timed(fn):
    t = time.perf_counter()
    fn()
    return (time.perf_counter() - t) * 1000


class Simnav:
    name = "simnav"

    def __init__(self, udid):
        self.udid = udid

    def __call__(self, *args, timeout=30, check=True):
        return sh([SIMNAV, "--udid", self.udid, *args], timeout=timeout, check=check)

    def open(self, target):
        # After a Maestro run the relaunched app can come up unreadable even once recovered.
        if self("launch", BUNDLE, check=False).returncode != 0:
            self("recover", timeout=60)
            self("launch", BUNDLE)
        for step in TARGETS[target]:
            self(*step, "--timeout", "15")

    def can(self, target):
        return None

    def run(self, target):
        out = []
        for what, arg in SCENARIO:
            if what == "read":
                out.append(timed(lambda: self("tree", "--web")))
            elif what == "tap":
                out.append(timed(lambda a=arg: self("tap", a)))
            elif what == "wait":
                out.append(timed(lambda a=arg: self("wait", a, "--timeout", "10")))
            elif what == "type":
                out.append(timed(lambda a=arg: self("type", "--field", 'type=TextField "Your name"', a)))
            elif what == "submit":
                out.append(timed(lambda: self("key", "return")))
            elif what == "reveal":
                out.append(timed(lambda a=arg: self.reveal(a)))
        return out

    def reveal(self, label):
        # An inspectable page and a native screen find it wherever it is; probing sees only the
        # screen, so scroll a page at a time as an agent would.
        for _ in range(10):
            if self("tap", label, "--timeout", "0", check=False).returncode == 0:
                return
            self("scroll", "down")
        raise StepFailed(f"simnav: {label} not reached")


class Axe:
    name = "axe"

    def __init__(self, udid):
        self.udid = udid
        self.simnav = Simnav(udid)

    def axe(self, *args):
        return sh(["axe", *args, "--udid", self.udid])

    def tree(self):
        return json.loads(self.axe("describe-ui").stdout)

    def can(self, target):
        return None if target == "native" else "reads no webview content (describe-ui shows only the native views)"

    def open(self, target):
        self.simnav.open(target)

    def wait(self, label, timeout=10):
        deadline = time.time() + timeout
        while time.time() < deadline:
            if axe_find(self.tree(), label):
                return
        raise StepFailed(f"axe: {label} did not appear")

    def reveal(self, label):
        for _ in range(10):
            e = axe_find(self.tree(), label)
            if e and on_screen(e):
                self.axe("tap", "--label", label)
                return
            self.axe("swipe", "--start-x", "200", "--start-y", "650", "--end-x", "200", "--end-y", "250")
        raise StepFailed(f"axe: {label} not reached")

    def run(self, target):
        out = []
        for what, arg in SCENARIO:
            if what == "read":
                out.append(timed(self.tree))
            elif what == "tap":
                out.append(timed(lambda a=arg: self.axe("tap", "--label", a)))
            elif what == "wait":
                out.append(timed(lambda a=arg: self.wait(a)))
            elif what == "type":
                out.append(timed(lambda a=arg: (self.axe("tap", "--label", "Your name", "--element-type", "TextField"),
                                                self.axe("type", a))))
            elif what == "submit":
                out.append(timed(lambda: self.axe("key", "40")))
            elif what == "reveal":
                out.append(timed(lambda a=arg: self.reveal(a)))
        return out


class Maestro:
    name = "maestro"

    def __init__(self, udid):
        self.udid = udid
        self.simnav = Simnav(udid)
        self.startup = []

    def can(self, target):
        return None

    def open(self, target):
        self.simnav.open(target)

    @staticmethod
    def flow():
        lines, sizes = [f"appId: {BUNDLE}", "---"], []
        for what, arg in SCENARIO:
            if what == "read":
                lines.append('- assertVisible: "NavDemo Web"'); sizes.append(1)
            elif what == "tap":
                lines.append(f'- tapOn: "{arg}"'); sizes.append(1)
            elif what == "wait":
                lines.append(f'- extendedWaitUntil:\n    visible: "{arg}"\n    timeout: 10000'); sizes.append(1)
            elif what == "type":
                lines += ['- tapOn:\n    text: "Your name"\n    index: 1', f'- inputText: "{arg}"']; sizes.append(2)
            elif what == "submit":
                lines.append("- pressKey: Enter"); sizes.append(1)
            elif what == "reveal":
                # centerElement: an element under the tab bar counts as visible otherwise, and the tap hits the bar.
                lines += [f'- scrollUntilVisible:\n    element:\n      text: "{arg}"\n    direction: DOWN\n    centerElement: true',
                          f'- tapOn: "{arg}"']
                sizes.append(2)
        return "\n".join(lines) + "\n", sizes

    def run(self, target):
        text, sizes = self.flow()
        with tempfile.TemporaryDirectory(prefix="maestro-") as d:
            path = os.path.join(d, "scenario.yaml")
            with open(path, "w") as f:
                f.write(text)
            t = time.perf_counter()
            r = sh(["maestro", "--udid", self.udid, "test", "--debug-output", os.path.join(d, "out"), path], timeout=600, check=False)
            wall = (time.perf_counter() - t) * 1000
            reports = [os.path.join(root, "commands.json") for root, _, files in os.walk(os.path.join(d, "out")) if "commands.json" in files]
            if not reports:
                raise StepFailed("Maestro wrote no report: " + (r.stdout + r.stderr).strip()[-300:])
            with open(reports[0]) as f:
                steps = group(maestro_durations(json.load(f)), sizes)
        self.startup.append(wall - sum(steps))
        # Maestro turns accessibility off when it exits, which leaves the screen unreadable.
        self.simnav("recover", timeout=60)
        return steps


def environment(udid):
    xcode = sh(["xcodebuild", "-version"], check=False).stdout.split("\n")
    runtime = sh(["xcrun", "simctl", "list", "devices", "-j"], check=False).stdout
    rt = next((k.rsplit(".", 1)[-1] for k, v in json.loads(runtime)["devices"].items() for d in v if d["udid"] == udid), "?")
    return {"xcode": " ".join(x for x in xcode[:2] if x), "runtime": rt, "host": platform.mac_ver()[0],
            "load": os.getloadavg()[0], "axe": sh(["axe", "--version"], check=False).stdout.strip(),
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
    ap.add_argument("--udid", required=True)
    ap.add_argument("--runs", type=int, default=3)
    ap.add_argument("--tools", default="simnav,axe,maestro")
    ap.add_argument("--targets", default="native,web,plain")
    ap.add_argument("--out", default=os.path.join(os.path.dirname(os.path.abspath(__file__)), "results"))
    a = ap.parse_args()
    kinds = {"simnav": Simnav, "axe": Axe, "maestro": Maestro}
    results, extra = {}, {}
    for name in a.tools.split(","):
        tool = kinds[name](a.udid)
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
            except (StepFailed, subprocess.TimeoutExpired) as e:
                results[name][target] = {"error": str(e), "runs": runs}
                print(f"{name} {target}: {e}", file=sys.stderr)
        if name == "maestro":
            extra["maestro_startup_ms"] = statistics.median(tool.startup) if tool.startup else None
    os.makedirs(a.out, exist_ok=True)
    stamp = datetime.datetime.now().strftime("%Y%m%d-%H%M%S")
    doc = {"environment": environment(a.udid), "scenario": STEP_NAMES, "results": results, **extra}
    with open(os.path.join(a.out, f"compare-{stamp}.json"), "w") as f:
        json.dump(doc, f, indent=1)
    print(table(results))
    if extra.get("maestro_startup_ms"):
        print(f"\nMaestro start-up per run (not in the table): {extra['maestro_startup_ms']:,.0f}ms")


if __name__ == "__main__":
    main()
