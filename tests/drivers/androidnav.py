"""androidnav, through its Python client."""
import os

from drivers.common import (
    ANDROID_APP,
    ANDROID_TARGETS,
    PLAIN_ON_ANDROID,
    SCENARIO,
    sh,
    timed,
)

ANDROIDNAV = os.path.expanduser("~/.claude/skills/androidnav/androidnav")


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

