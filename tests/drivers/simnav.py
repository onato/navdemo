"""simnav, through its C client: the wall time of each command, process start included."""
import os

from drivers.common import BUNDLE, SCENARIO, TARGETS, StepFailed, sh, timed

SIMNAV = os.path.expanduser("~/.claude/skills/simnav/bin/simnav")


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

