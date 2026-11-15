# Spec: Appium in the tool comparison (iOS)

Status: approved 2026-11-16.

## Why

`tests/compare.py` times simnav, AXe and Maestro on one scenario. Appium is missing, and it is the
established tool that reads WebView content the way simnav does: its XCUITest driver switches to a
web context through the simulator's `webinspectord`. So it is the fair comparison for the `web`
target, where AXe cannot read and Maestro reads through accessibility. It also shows how Appium
picks a page when an app has several WebViews: it lists one context per page, so NavDemo's Web and
Plain web tabs (the same HTML in two WebViews) test that case directly.

## Setup

- Node from mise (v26 is installed), then `npm install -g appium` and
  `appium driver install xcuitest`. Neither is installed yet. The results record the Appium,
  driver and WebDriverAgent versions.
- WebDriverAgent (WDA) is the XCTest runner app the driver installs on the simulator. Its first
  build takes minutes. It is built once, outside the timings, and stays installed on the pool
  simulator that runs it.
- The harness starts `appium` on a free local port for the run and stops it at the end.

## The client

The harness speaks W3C WebDriver over HTTP with `urllib`, not the Appium Python client. That keeps
`compare.py` on the standard library, as it is now, and times only the HTTP calls the tool makes.

## The scenario in Appium

One session per run, with `appium:udid`, `appium:bundleId dev.navdemo.ios`, `appium:noReset` and
`appium:autoLaunch false`, so it attaches to the app that simnav has opened on the target. Waits
use the session's implicit wait (10 s), so a wait is one find call and the server does the polling.

| Step | `native` | `web` (in the page's web context) |
|---|---|---|
| read | `GET /source` | `GET /source` (the page's HTML) |
| tap X | find by `-ios predicate string` `label == 'X'`, then click | find by XPath on text, then click |
| wait X | find, with the implicit wait | find, with the implicit wait |
| type Ada | find the `Your name` text field, send keys | find `#name`, send keys |
| submit | send `\n` to the field | send Enter (``) to the field |
| reveal X | find, `mobile: scrollToElement`, check it is above the tab bar, then click | find, then click |

- **Web clicks are not touches.** In a web context Appium dispatches clicks and keys by JavaScript
  in the page, so they work on elements off screen or under the tab bar. A reveal in `web` is
  therefore a click with no scrolling. The table says so beside the figure, as a different kind
  of action from simnav's press at a point.
- **Start-up is reported apart, as for Maestro.** That covers the Appium server start, session
  creation and WDA launch for each run.
- **The switch to the web context is reported apart too:** `GET /contexts` and then
  `POST /context`, with the context chosen as below. It is a cost an agent pays once per WebView.

## Picking the context

`GET /contexts` lists `NATIVE_APP` and one `WEBVIEW_*` entry per inspectable page, each with its
URL and title when the session asks for full context info (`mobile: getContexts`). On `web` there
should be one page: the Plain web tab's WebView is not inspectable. The harness takes the single
`WEBVIEW_*` context, and fails the run if there are none or several. It does not guess.

- **`plain`** has no web context: each run relaunches the app, so the Web tab's page does not
  exist yet. Appium is reported as "cannot" there, with the reason it gives.
- **The hidden-page case** is checked once, untimed: open the Web tab, then the Plain web tab, then
  list the contexts. The Web tab's page is now hidden but still listed. The results record what
  `mobile: getContexts` reports for it (URL, title, and any visibility field), and whether a
  `/source` in that context returns the hidden page. Reading a hidden page is the failure simnav's
  SN-87 fixed, and seeing whether Appium can tell is part of the point.

## Interference with the other tools

- **Accessibility.** WDA runs an XCTest session in the simulator. As after Maestro, the harness
  deletes the session and runs `simnav recover` at the end of each Appium run. A check after the
  first run confirms that simnav still reads the screen.
- **Web Inspector.** One client gets answers at a time (see simnav's notes on a second client), so
  simnavd may be the one holding webinspectord. The harness runs `simnav quit` before each
  Appium run. simnav's untimed `open` before the next run starts simnavd again.

## Tests first (`tests/test_compare.py`)

- the session capabilities name the UDID and bundle, and do not launch or reset the app;
- each scenario step becomes the WebDriver requests in the table, native and web;
- the context is the single `WEBVIEW_*` entry, and none or several is an error that names them;
- an element's rect counts as on screen only above the tab bar (`TAB_BAR_TOP`), so a native
  reveal is judged as for AXe;
- a failed WebDriver reply (`value.error`) raises `StepFailed` with its message.

## Results

- Rows join the iOS results file (`compare-<time>.json`), with an Appium column per target, and
  `appium_startup_ms` and `appium_context_ms` reported beside the table, as Maestro's start-up is.
- The iOS baseline (`tests/compare-baseline.ios.json`) is replaced only by a full run of every
  tool, so that all its columns come from one host load.

## Not in scope

- **Android** (the UiAutomator2 driver, with Chromedriver for the WebView): a follow-up spec, if
  the iOS figures are interesting.
- **Physical devices**, and Appium's other iOS options such as Safari sessions.
- **Tuning Appium**, for example its settle and snapshot settings. It runs with the driver's
  defaults, as Maestro does, and the defaults are recorded with the results.
