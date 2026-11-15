"""What every driver shares: the app, the scenario, the targets and how a step fails."""
import subprocess
import time

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


def sh(args, timeout=60, check=True):
    r = subprocess.run(args, capture_output=True, text=True, timeout=timeout, check=False)
    if check and r.returncode != 0:
        raise StepFailed(f"{' '.join(args[:4])}…: {(r.stderr or r.stdout).strip()[-300:]}")
    return r


def timed(fn):
    t = time.perf_counter()
    fn()
    return (time.perf_counter() - t) * 1000


def on_screen(e, bottom=TAB_BAR_TOP):
    f = e["frame"]
    cy = f["y"] + f["height"] / 2
    return 0 < cy < bottom

