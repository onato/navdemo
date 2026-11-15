# NavDemo

A small iOS + Android app whose only purpose is to exercise automated UI navigation:
a login screen, a tab bar, native lists, a search field, dialogs, a detail screen, and a
WebView with buttons, a form, links and slow-loading content. Both apps share the web pages in
`shared/web/` and use the same labels and identifiers, so one navigation script can drive both.

| | iOS | Android |
|---|---|---|
| id | `dev.navdemo.ios` | `dev.navdemo.android` |
| build | `scripts/build-ios.sh` (XcodeGen + xcodebuild) | `scripts/build-android.sh` (Gradle) |
| login | any username, password `demo` | same |

`.mobile-device/` holds the app profile and the login flows the `mobile-device` skill runs.

## Driving it

```bash
M=~/.claude/skills/mobile-device/mobile-device
tests/smoke.sh ios            # lease a simulator, build, install, launch, sign in, tour
tests/smoke.sh android        # the same on an emulator
$M --platform ios nav tests/tour.ios.nav      # just the tour, on this session's device
$M --platform ios do tap id=searchField       # any one simnav / androidnav command
tests/perf.py --platform ios --runs 5         # time the tour: median and p90 per step
tests/compare.py --udid <udid> --runs 3       # simnav, AXe, Maestro and Appium on native, web and plain web
```

- `.mobile-device/app.toml` names the bundle ids, build commands, app paths, the signed-in /
  signed-out markers and where the password comes from.
- `.mobile-device/login.*.nav` and `logout.*.nav` are the sign-in and sign-out flows, one per
  platform, as driver scripts: `$USERNAME` and `$SECRET_FILE` are filled in at run time, and the
  password only ever goes through `type --secret-file` into the password field.
- The Web and Plain web tabs show the same pages. On iOS, Web's WebView is inspectable in Debug
  builds and Plain web's never is, so a tool can be compared on one page read both ways, and in an
  app with both kinds of WebView. On Android, WebView debugging is one switch for the whole app,
  so the two tabs are the same.
- Home → **Native page** (iOS) is a SwiftUI twin of the web page: the same elements, texts, order
  and identifiers (the HTML ids), and a native second page of 40 rows. One script runs on all three,
  so a tool's cost on native content can be set against the same page in either WebView. The
  differences native controls bring: "Second page" is a Button, not a Link, and the colour picker's
  label includes its value.
- `tests/tour.*.nav` walk every screen: counter, list → detail, favourite, back, the WebView's
  button, form, link and second page, scrolling, search, profile, dialog. About 10 s per platform.
- `tests/perf.py` runs the tour several times on a signed-in app, relaunching it before each run,
  and prints each step's median and p90. Its `driver` row sums the taps, typing and scrolling (the
  driver's own cost), its `app` row the waits (mostly the app's animations and page loads). With
  `--save-baseline` it writes `tests/perf-baseline.<platform>.json`; later runs mark rows more than
  a fifth and 10 ms slower, and exit 1 when the driver, app or total row is.
- `tests/compare.py` runs one scenario (read, tap, wait, type and submit, follow a link under the
  tab bar, tap a row far down the next page) with simnav, AXe, Maestro and Appium on the native
  page, the inspectable Web tab and the Plain web tab. It times each step as an agent pays it: for
  simnav and AXe the wall time of each command, for Maestro the duration it records per command,
  for Appium the wall time of its WebDriver calls; start-ups are reported apart. A tool that cannot
  do a target says so instead of a time (AXe reads no WebView content, Appium no page that is not
  inspectable). Each tool's driver is a module in `tests/drivers/`. Results go to `tests/results/compare-<time>.json`, and a Markdown table is
  printed. `tests/compare-baseline.ios.json` is the run to compare against (2026-11-16, iOS 26.5,
  load 6 at the end of the run); compare.py does not read it, so set the two side by side.
  Appium needs `npm install -g appium` and `appium driver install xcuitest`; its first session
  builds WebDriverAgent onto the simulator. `--platform android --serial <serial>` runs androidnav, adb and Maestro on the Android app's
  native twin and web page; `tests/compare-baseline.android.json` is its baseline (2026-11-16,
  Android 14 emulator, load 4).
