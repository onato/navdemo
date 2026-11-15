"""adb alone: `uiautomator dump` to read, `input` to act."""
import re
import time
import xml.etree.ElementTree as ET

from drivers.androidnav import Androidnav
from drivers.common import SCENARIO, StepFailed, sh, timed


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

