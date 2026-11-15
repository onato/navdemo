# Spec: the tool comparison on Android

Status: approved 2026-11-15.

## Why

`tests/compare.py` times one scenario with simnav, AXe and Maestro on iOS, and its iOS baseline is
`tests/compare-baseline.ios.json`. androidnav claims ~80 ms a call against adb's ~2 s and Maestro's
~18 s (its SKILL.md), but nothing in NavDemo measures that the way the iOS comparison does. The
same scenario on Android would give androidnav a baseline and show where its time goes.

## What differs from iOS

- **There is no native twin.** The iOS app's Native page is a SwiftUI copy of `index.html` and
  `page2.html`. The Android app has none, so there is no native target to time.
- **The Plain web tab is the Web tab again.** WebView debugging is one switch for the whole app
  (`MainActivity.kt`), so Plain web is just as inspectable. A `plain` target would repeat `web`.
- **One UiAutomation connection per device.** androidnav's server holds it. Maestro and
  `uiautomator dump` fail while it runs, so the harness stops it (`androidnav quit`) before a
  Maestro or adb run, and androidnav starts it again on its next call.
- **The tab bar is Android's bottom navigation**, and its top edge is read from the device, not
  fixed as `TAB_BAR_TOP` is for the iPhone 17 Pro.

## The app: a native twin

`NativePageFragment` and `NativePage2Fragment`, opened from a "Native page" button on Home
(`id=nativePage`, as on iOS): the same elements, texts, order and ids as the two web pages, laid
out the same way, with the same half screen of space at the end (`b87b9dd`). Ids are view ids, so
`id=hello` finds the same element on the twin and on the web page. Tests first, as for the iOS
twin: a unit test that the twin's texts and ids match `index.html` and `page2.html`.

## The harness: `compare.py --platform android`

- `--platform ios|android`, default `ios`; `--serial` for Android in place of `--udid`.
- Targets on Android: `native` and `web`. `plain` is reported as "the same WebView as web on
  Android" rather than timed.
- Tools on Android:
  - **androidnav**: the same commands as simnav (the client speaks them), `--serial` in place of
    `--udid`, and `type --field` as its tour does.
  - **adb**: `uiautomator dump` for reading and waiting, `input tap` at the element's centre,
    `input text` for typing, `input keyevent 66` to submit, `input swipe` to reveal. It reads
    WebView content through accessibility, so unlike AXe it runs the web target too.
  - **Maestro**: the same flow as iOS with `appId: dev.navdemo.android`, timed from its
    `commands.json` with start-up apart.
- Each run relaunches the app and opens the target with androidnav (untimed), then quits
  androidnav's server before adb or Maestro runs.
- Results go to `tests/results/compare-android-<time>.json`, with the emulator's Android version,
  the AVD and the load. The saved baseline is `tests/compare-baseline.android.json`.
- Tests first (`tests/test_compare.py`): parsing a `uiautomator dump` and finding an element by
  text or content description in it; an element counted on screen only above the bottom
  navigation; the `plain` cell on Android saying why it is not timed; the Maestro flow naming the
  Android app id.

## Not in scope

- A non-inspectable WebView on Android: debugging is app-wide, so it would take a second app or
  a process of its own.
- Appium, Espresso and other in-app frameworks: they need the app built with them.
