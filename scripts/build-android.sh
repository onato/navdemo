#!/usr/bin/env bash
# Build the Android debug APK. Prints the path of the APK on the last line.
set -euo pipefail
HERE="$(cd "$(dirname "$0")/.." && pwd -P)"
cd "$HERE/android"
if [ -z "${JAVA_HOME:-}" ] && [ -d "/Applications/Android Studio.app/Contents/jbr/Contents/Home" ]; then
  export JAVA_HOME="/Applications/Android Studio.app/Contents/jbr/Contents/Home"
fi
[ -x ./gradlew ] || { echo "build-android: no gradlew; run 'gradle wrapper --gradle-version 8.9' once" >&2; exit 2; }
./gradlew --quiet --console=plain :app:assembleDebug
echo "$HERE/android/app/build/outputs/apk/debug/app-debug.apk"
