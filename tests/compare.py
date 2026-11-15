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
import atexit
import datetime
import json
import os
import platform
import re
import socket
import statistics
import subprocess
import sys
import tempfile
import time
import urllib.error
import urllib.request
import xml.etree.ElementTree as ET

SIMNAV = os.path.expanduser("~/.claude/skills/simnav/bin/simnav")
ANDROIDNAV = os.path.expanduser("~/.claude/skills/androidnav/androidnav")
BUNDLE = "dev.navdemo.ios"
ANDROID_APP = "dev.navdemo.android"
PLAIN_ON_ANDROID = "the same WebView as web on Android, where WebView debugging is app-wide"
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
ANDROID_TARGETS = {
    "native": [["tap", "id=nav_home"], ["tap", "id=nativePage"], ["wait", "Say hello"]],
    "web": [["tap", "id=nav_web"], ["wait", "web", "Say hello"]],
}


class StepFailed(Exception):
    pass


class Cannot(StepFailed):
    """The tool cannot do the scenario on this target at all, found only once it is running."""


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


def rect_on_screen(rect, bottom=TAB_BAR_TOP):
    return on_screen({"frame": rect}, bottom)


def element_id(value):
    return value["element-6066-11e4-a52e-4f735466cecf"]


def webdriver_value(reply):
    value = reply.get("value")
    if isinstance(value, dict) and "error" in value:
        raise StepFailed(f"{value['error']}: {value.get('message', '')}".strip())
    return value


def parse_dump(xml):
    """The nodes of a `uiautomator dump`: text, description, id and centre in pixels."""
    root = ET.fromstring(xml[xml.index("<?xml"):xml.rindex("</hierarchy>") + len("</hierarchy>")])
    out = []
    for n in root.iter("node"):
        x1, y1, x2, y2 = map(int, re.findall(r"\d+", n.get("bounds", "[0,0][0,0]")))
        out.append({"text": n.get("text", ""), "desc": n.get("content-desc", ""),
                    "id": n.get("resource-id", "").rsplit(":id/", 1)[-1], "centre": ((x1 + x2) // 2, (y1 + y2) // 2),
                    "top": y1})
    return out


def dump_find(nodes, label):
    """The first node whose text or description is `label`, or whose id is `label` without `id=`."""
    if label.startswith("id="):
        return next((n for n in nodes if n["id"] == label[3:]), None)
    return next((n for n in nodes if label in (n["text"], n["desc"])), None)


def nav_top(nodes):
    nav = next((n for n in nodes if n["id"] == "bottomNav"), None)
    return nav["top"] if nav else 10 ** 9


def on_screen_android(node, nav):
    return 0 < node["centre"][1] < nav


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


class Androidnav:
    name = "androidnav"

    def __init__(self, serial):
        self.serial = serial
        self.target = None

    def __call__(self, *args, timeout=30, check=True):
        return sh([ANDROIDNAV, "--serial", self.serial, *args], timeout=timeout, check=check)

    def can(self, target):
        return PLAIN_ON_ANDROID if target == "plain" else None

    def open(self, target):
        self.target = target
        self("launch", ANDROID_APP, timeout=60)
        for step in ANDROID_TARGETS[target]:
            self(*step, "--timeout", "15")

    def release(self):
        """Gives up the device's one UiAutomation connection, for adb or Maestro."""
        self("quit", check=False)

    def sel(self, label):
        return ["web", label] if self.target == "web" else [label]

    def run(self, target):
        out = []
        for what, arg in SCENARIO:
            if what == "read":
                out.append(timed(lambda: self("tree", "--web") if target == "web" else self("tree")))
            elif what == "tap":
                out.append(timed(lambda a=arg: self("tap", *self.sel(a))))
            elif what == "wait":
                out.append(timed(lambda a=arg: self("wait", *self.sel(a), "--timeout", "10")))
            elif what == "type":
                field = "web id=name" if target == "web" else "id=name"
                out.append(timed(lambda a=arg, f=field: self("type", "--field", f, a)))
            elif what == "submit":
                out.append(timed(lambda: self("key", "enter")))
            elif what == "reveal":
                out.append(timed(lambda a=arg: self("tap", *self.sel(a), "--timeout", "10")))
        return out


class Adb:
    """What every Android developer has: `uiautomator dump` to read, `input` to act."""
    name = "adb"

    def __init__(self, serial):
        self.serial = serial
        self.driver = Androidnav(serial)

    def adb(self, *args, timeout=30):
        return sh(["adb", "-s", self.serial, *args], timeout=timeout)

    def can(self, target):
        return self.driver.can(target)

    def open(self, target):
        self.driver.open(target)
        self.driver.release()

    def size(self):
        if not hasattr(self, "_size"):
            self._size = tuple(map(int, re.findall(r"(\d+)x(\d+)", self.adb("shell", "wm", "size").stdout)[-1]))
        return self._size

    def dump(self):
        return parse_dump(self.adb("exec-out", "uiautomator", "dump", "/dev/tty").stdout)

    def find(self, label, timeout=10):
        deadline = time.time() + timeout
        while time.time() < deadline:
            nodes = self.dump()
            n = dump_find(nodes, label)
            if n:
                return n, nodes
        raise StepFailed(f"adb: {label} did not appear")

    def tap(self, label):
        n, _ = self.find(label)
        self.adb("shell", "input", "tap", *map(str, n["centre"]))

    def reveal(self, label):
        for _ in range(10):
            nodes = self.dump()
            n = dump_find(nodes, label)
            if n and on_screen_android(n, nav_top(nodes)):
                self.adb("shell", "input", "tap", *map(str, n["centre"]))
                return
            w, h = self.size()
            self.adb("shell", "input", "swipe", str(w // 2), str(h * 7 // 10), str(w // 2), str(h * 3 // 10), "300")
        raise StepFailed(f"adb: {label} not reached")

    def run(self, target):
        out = []
        for what, arg in SCENARIO:
            if what == "read":
                out.append(timed(self.dump))
            elif what == "tap":
                out.append(timed(lambda a=arg: self.tap(a)))
            elif what == "wait":
                out.append(timed(lambda a=arg: self.find(a)))
            elif what == "type":
                out.append(timed(lambda a=arg: (self.tap("id=name"), self.adb("shell", "input", "text", a))))
            elif what == "submit":
                out.append(timed(lambda: self.adb("shell", "input", "keyevent", "66")))
            elif what == "reveal":
                out.append(timed(lambda a=arg: self.reveal(a)))
        return out


class Maestro:
    name = "maestro"

    def __init__(self, device, android=False):
        self.device = device
        self.android = android
        self.driver = Androidnav(device) if android else Simnav(device)
        self.startup = []

    def can(self, target):
        return self.driver.can(target)

    def open(self, target):
        self.driver.open(target)
        if self.android:
            self.driver.release()

    @staticmethod
    def flow(app=BUNDLE):
        lines, sizes = [f"appId: {app}", "---"], []
        for what, arg in SCENARIO:
            if what == "read":
                lines.append('- assertVisible: "NavDemo Web"'); sizes.append(1)
            elif what == "tap":
                lines.append(f'- tapOn: "{arg}"'); sizes.append(1)
            elif what == "wait":
                lines.append(f'- extendedWaitUntil:\n    visible: "{arg}"\n    timeout: 10000'); sizes.append(1)
            elif what == "type":
                # iOS gives the field the label's text too (index 1 is the field); Android only the label.
                field = '- tapOn:\n    id: "name"' if app == ANDROID_APP else '- tapOn:\n    text: "Your name"\n    index: 1'
                lines += [field, f'- inputText: "{arg}"']; sizes.append(2)
            elif what == "submit":
                lines.append("- pressKey: Enter"); sizes.append(1)
            elif what == "reveal":
                # centerElement: an element under the tab bar counts as visible otherwise, and the tap hits the bar.
                lines += [f'- scrollUntilVisible:\n    element:\n      text: "{arg}"\n    direction: DOWN\n    centerElement: true\n    timeout: 60000',
                          f'- tapOn: "{arg}"']
                sizes.append(2)
        return "\n".join(lines) + "\n", sizes

    def run(self, target):
        text, sizes = self.flow(ANDROID_APP if self.android else BUNDLE)
        with tempfile.TemporaryDirectory(prefix="maestro-") as d:
            path = os.path.join(d, "scenario.yaml")
            with open(path, "w") as f:
                f.write(text)
            t = time.perf_counter()
            r = sh(["maestro", "--device" if self.android else "--udid", self.device, "test", "--debug-output", os.path.join(d, "out"), path], timeout=600, check=False)
            wall = (time.perf_counter() - t) * 1000
            reports = [os.path.join(root, "commands.json") for root, _, files in os.walk(os.path.join(d, "out")) if "commands.json" in files]
            if not reports:
                raise StepFailed("Maestro wrote no report: " + (r.stdout + r.stderr).strip()[-300:])
            with open(reports[0]) as f:
                steps = group(maestro_durations(json.load(f)), sizes)
        self.startup.append(wall - sum(steps))
        if not self.android:
            # Maestro turns accessibility off when it exits, which leaves the screen unreadable.
            self.driver("recover", timeout=60)
        return steps


class Appium:
    """Appium's XCUITest driver, spoken to as plain W3C WebDriver over HTTP."""
    name = "appium"

    def __init__(self, udid):
        self.udid = udid
        self.simnav = Simnav(udid)
        self.server = None
        self.base = None
        self.session = None
        self.startup = []
        self.context = []
        self.server_ms = None

    @staticmethod
    def capabilities(udid):
        return {"capabilities": {"alwaysMatch": {
            "platformName": "iOS", "appium:automationName": "XCUITest", "appium:udid": udid,
            "appium:bundleId": BUNDLE, "appium:noReset": True, "appium:autoLaunch": False,
            "appium:wdaLaunchTimeout": 600000, "appium:newCommandTimeout": 300,
            "appium:additionalWebviewBundleIds": ["process-NavDemo"],
        }}}

    @staticmethod
    def plan(what, arg, target):
        web = target != "native"

        def by_text(text):
            if web:
                return ("find", "xpath", f"//*[normalize-space(text())='{text}']")
            return ("find", "-ios predicate string", f"label == '{text}'")

        field = ("find", "css selector", "#name") if web else \
            ("find", "-ios predicate string", "type == 'XCUIElementTypeTextField' AND label == 'Your name'")
        if what == "read":
            return [("source",)]
        if what == "tap":
            return [by_text(arg), ("click",)]
        if what == "wait":
            return [by_text(arg)]
        if what == "type":
            return [field, ("keys", arg)]
        if what == "submit":
            return [field, ("keys", "" if web else "\n")]
        if what == "reveal":
            if web:
                return [by_text(arg), ("click",)]
            return [by_text(arg), ("scroll to",), ("on screen",), ("click",)]
        raise ValueError(what)

    @staticmethod
    def web_context(contexts):
        ids = [c["id"] if isinstance(c, dict) else c for c in contexts]
        webviews = [c for c in ids if c.startswith("WEBVIEW")]
        if len(webviews) != 1:
            raise Cannot(f"Appium lists {len(webviews)} web contexts: {', '.join(ids)}")
        return webviews[0]

    def call(self, method, path, body=None, timeout=120):
        url = self.base + (f"/session/{self.session}" if self.session else "") + path
        data = json.dumps(body if body is not None else {}).encode() if method == "POST" else None
        req = urllib.request.Request(url, data=data, method=method, headers={"Content-Type": "application/json"})
        try:
            with urllib.request.urlopen(req, timeout=timeout) as r:
                return webdriver_value(json.load(r))
        except urllib.error.HTTPError as e:
            return webdriver_value(json.load(e))

    def start_server(self):
        with socket.socket() as s:
            s.bind(("127.0.0.1", 0))
            port = s.getsockname()[1]
        self.base = f"http://127.0.0.1:{port}"
        t = time.perf_counter()
        self.server = subprocess.Popen(["appium", "--address", "127.0.0.1", "--port", str(port), "--log-level", "error"],
                                       stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        atexit.register(self.server.terminate)
        deadline = time.time() + 60
        while time.time() < deadline:
            try:
                self.call("GET", "/status", timeout=2)
                self.server_ms = (time.perf_counter() - t) * 1000
                return
            except (urllib.error.URLError, ConnectionError):
                time.sleep(0.2)
        raise StepFailed("the Appium server did not start within 60s")

    def can(self, target):
        return None

    def open(self, target):
        if not self.server:
            self.start_server()
        self.simnav.open(target)
        # One Web Inspector client gets answers at a time, and simnavd holds one.
        self.simnav("quit", check=False)
        t = time.perf_counter()
        self.session = None
        self.session = self.call("POST", "/session", self.capabilities(self.udid), timeout=900)["sessionId"]
        self.call("POST", "/timeouts", {"implicit": 10000})
        self.startup.append((time.perf_counter() - t) * 1000)
        if target != "native":
            t = time.perf_counter()
            try:
                self.call("POST", "/context", {"name": self.web_context(self.call("GET", "/contexts"))})
            except Cannot:
                self.close()
                raise
            self.context.append((time.perf_counter() - t) * 1000)

    def do(self, op):
        kind = op[0]
        if kind == "source":
            self.call("GET", "/source")
        elif kind == "find":
            self.element = element_id(self.call("POST", "/element", {"using": op[1], "value": op[2]}))
        elif kind == "click":
            self.call("POST", f"/element/{self.element}/click")
        elif kind == "keys":
            self.call("POST", f"/element/{self.element}/value", {"text": op[1], "value": list(op[1])})
        elif kind == "scroll to":
            self.call("POST", "/execute/sync", {"script": "mobile: scrollToElement",
                                                "args": [{"elementId": self.element}]})
        elif kind == "on screen":
            rect = self.call("GET", f"/element/{self.element}/rect")
            if not rect_on_screen(rect):
                raise StepFailed(f"appium: revealed at {rect}, not above the tab bar")

    def close(self):
        if self.session:
            self.call("DELETE", "")
            self.session = None
        # WebDriverAgent's XCTest session can leave accessibility as Maestro does.
        self.simnav("recover", timeout=60, check=False)

    def run(self, target):
        out = []
        try:
            for what, arg in SCENARIO:
                ops = self.plan(what, arg, target)
                t = time.perf_counter()
                for op in ops:
                    self.do(op)
                out.append((time.perf_counter() - t) * 1000)
            return out
        finally:
            self.close()

    def hidden_page(self):
        """Web tab, then Plain web: what Appium lists for the Web tab's now hidden page."""
        self.simnav.open("web")
        self.simnav("tap", "Plain web")
        self.simnav("wait", "web", "Say hello", "--timeout", "15")
        self.simnav("quit", check=False)
        self.session = self.call("POST", "/session", self.capabilities(self.udid), timeout=900)["sessionId"]
        try:
            listed = self.call("POST", "/execute/sync", {"script": "mobile: getContexts", "args": [{}]})
            pages = []
            for c in listed:
                cid = c["id"] if isinstance(c, dict) else c
                if not cid.startswith("WEBVIEW"):
                    continue
                self.call("POST", "/context", {"name": cid})
                state = self.call("POST", "/execute/sync", {"script": "return document.visibilityState", "args": []})
                pages.append({"context": c, "visibilityState": state,
                              "source_has_say_hello": "Say hello" in self.call("GET", "/source")})
                self.call("POST", "/context", {"name": "NATIVE_APP"})
            return {"contexts": listed, "pages": pages}
        finally:
            self.close()


def environment(udid):
    xcode = sh(["xcodebuild", "-version"], check=False).stdout.split("\n")
    runtime = sh(["xcrun", "simctl", "list", "devices", "-j"], check=False).stdout
    rt = next((k.rsplit(".", 1)[-1] for k, v in json.loads(runtime)["devices"].items() for d in v if d["udid"] == udid), "?")
    return {"xcode": " ".join(x for x in xcode[:2] if x), "runtime": rt, "host": platform.mac_ver()[0],
            "load": os.getloadavg()[0], "axe": sh(["axe", "--version"], check=False).stdout.strip(),
            "maestro": sh(["maestro", "--version"], check=False).stdout.strip().splitlines()[-1:],
            "appium": appium_versions(),
            "when": datetime.datetime.now().isoformat(timespec="seconds")}


def appium_versions():
    try:
        server = sh(["appium", "--version"], check=False).stdout.strip()
        drivers = sh(["appium", "driver", "list", "--installed", "--json"], check=False).stdout
        xcuitest = json.loads(drivers).get("xcuitest", {}).get("version")
    except (FileNotFoundError, ValueError):
        return None
    return {"server": server, "xcuitest": xcuitest}


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
    results, extra = {}, {}
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
        if name == "maestro":
            extra["maestro_startup_ms"] = statistics.median(tool.startup) if tool.startup else None
        if name == "appium":
            extra["appium_server_ms"] = tool.server_ms
            extra["appium_startup_ms"] = statistics.median(tool.startup) if tool.startup else None
            extra["appium_context_ms"] = statistics.median(tool.context) if tool.context else None
            if "plain" in a.targets.split(","):
                try:
                    extra["appium_hidden_page"] = tool.hidden_page()
                except (StepFailed, subprocess.TimeoutExpired) as e:
                    extra["appium_hidden_page"] = {"error": str(e)}
    os.makedirs(a.out, exist_ok=True)
    stamp = datetime.datetime.now().strftime("%Y%m%d-%H%M%S")
    env = android_environment(device) if android else environment(device)
    doc = {"platform": a.platform, "environment": env, "scenario": STEP_NAMES, "results": results, **extra}
    with open(os.path.join(a.out, f"compare-{'android-' if android else ''}{stamp}.json"), "w") as f:
        json.dump(doc, f, indent=1)
    print(table(results))
    if extra.get("maestro_startup_ms"):
        print(f"\nMaestro start-up per run (not in the table): {extra['maestro_startup_ms']:,.0f}ms")
    if extra.get("appium_startup_ms"):
        print(f"Appium session start per run (not in the table): {extra['appium_startup_ms']:,.0f}ms;"
              f" server start {extra['appium_server_ms']:,.0f}ms once")
    if extra.get("appium_context_ms"):
        print(f"Appium switch to the web context (not in the table): {extra['appium_context_ms']:,.0f}ms")
    if "appium_hidden_page" in extra:
        print("Appium on Plain web after Web: " + json.dumps(extra["appium_hidden_page"])[:600])


if __name__ == "__main__":
    main()
