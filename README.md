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
