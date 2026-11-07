#!/usr/bin/env bash
# Build the iOS simulator app. Prints the path of the built .app on the last line.
set -euo pipefail
HERE="$(cd "$(dirname "$0")/.." && pwd -P)"
cd "$HERE/ios"
command -v xcodegen >/dev/null || { echo "build-ios: needs xcodegen (brew install xcodegen)" >&2; exit 2; }
xcodegen generate --quiet
xcodebuild -project NavDemo.xcodeproj -scheme NavDemo -configuration Debug \
  -destination 'generic/platform=iOS Simulator' -derivedDataPath build \
  CODE_SIGNING_ALLOWED=NO build -quiet
echo "$HERE/ios/build/Build/Products/Debug-iphonesimulator/NavDemo.app"
