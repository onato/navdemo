"""Maestro, timed from the durations it records, with its start-up reported apart."""
import json
import os
import statistics
import tempfile
import time

from drivers.androidnav import Androidnav
from drivers.common import ANDROID_APP, BUNDLE, SCENARIO, StepFailed, sh
from drivers.simnav import Simnav

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

    def extras(self, targets):
        ms = statistics.median(self.startup) if self.startup else None
        notes = [f"Maestro start-up per run (not in the table): {ms:,.0f}ms"] if ms else []
        return {"maestro_startup_ms": ms}, notes

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

