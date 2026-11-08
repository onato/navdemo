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
```

- `.mobile-device/app.toml` names the bundle ids, build commands, app paths, the signed-in /
  signed-out markers and where the password comes from.
- `.mobile-device/login.*.nav` and `logout.*.nav` are the sign-in and sign-out flows, one per
  platform, as driver scripts: `$USERNAME` and `$SECRET_FILE` are filled in at run time, and the
  password only ever goes through `type --secret-file` into the password field.
- `tests/tour.*.nav` walk every screen: counter, list → detail, favourite, back, the WebView's
  button, form, link and second page, scrolling, search, profile, dialog. About 10 s per platform.
