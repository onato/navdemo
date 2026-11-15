"""AXe, one process per command. It reads no webview content."""
import json
import time

from drivers.common import SCENARIO, StepFailed, on_screen, sh, timed
from drivers.simnav import Simnav


def axe_find(tree, label):
    for e in tree:
        if e.get("AXLabel") == label or e.get("AXValue") == label:
            return e
        found = axe_find(e.get("children") or [], label)
        if found:
            return found
    return None


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

