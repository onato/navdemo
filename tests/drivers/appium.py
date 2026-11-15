"""Appium's XCUITest driver, spoken to as plain W3C WebDriver over HTTP."""
import atexit
import json
import socket
import statistics
import subprocess
import time
import urllib.error
import urllib.request

from drivers.common import (
    BUNDLE,
    SCENARIO,
    TAB_BAR_TOP,
    Cannot,
    StepFailed,
    on_screen,
    sh,
)
from drivers.simnav import Simnav


def rect_on_screen(rect, bottom=TAB_BAR_TOP):
    return on_screen({"frame": rect}, bottom)


def element_id(value):
    return value["element-6066-11e4-a52e-4f735466cecf"]


def webdriver_value(reply):
    value = reply.get("value")
    if isinstance(value, dict) and "error" in value:
        raise StepFailed(f"{value['error']}: {value.get('message', '')}".strip())
    return value


def appium_versions():
    try:
        server = sh(["appium", "--version"], check=False).stdout.strip()
        drivers = sh(["appium", "driver", "list", "--installed", "--json"], check=False).stdout
        xcuitest = json.loads(drivers).get("xcuitest", {}).get("version")
    except (FileNotFoundError, ValueError):
        return None
    return {"server": server, "xcuitest": xcuitest}


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
            return [field, ("keys", "\ue007" if web else "\n")]
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

    def extras(self, targets):
        values = {"appium_server_ms": self.server_ms,
                  "appium_startup_ms": statistics.median(self.startup) if self.startup else None,
                  "appium_context_ms": statistics.median(self.context) if self.context else None}
        notes = []
        if values["appium_startup_ms"]:
            notes.append(f"Appium session start per run (not in the table): {values['appium_startup_ms']:,.0f}ms;"
                         f" server start {self.server_ms:,.0f}ms once")
        if values["appium_context_ms"]:
            notes.append(f"Appium switch to the web context (not in the table): {values['appium_context_ms']:,.0f}ms")
        if "plain" in targets:
            try:
                values["appium_hidden_page"] = self.hidden_page()
            except (StepFailed, subprocess.TimeoutExpired) as e:
                values["appium_hidden_page"] = {"error": str(e)}
            notes.append("Appium on Plain web after Web: " + json.dumps(values["appium_hidden_page"])[:600])
        return values, notes

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

