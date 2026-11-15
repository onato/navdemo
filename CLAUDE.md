# NavDemo

See README.md for what the app is and how to drive it.

## Project commands

- Tests (no device): `python3 -m unittest discover -s tests`
- Lint: `uvx ruff check tests`
- Build: `scripts/build-ios.sh`, `scripts/build-android.sh`
- On a device: `tests/smoke.sh ios|android` (works end to end), `tests/perf.py --platform ios|android` (timings), `tests/compare.py --udid <udid>` (tools against each other, iOS)
