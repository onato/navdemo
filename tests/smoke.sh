#!/bin/bash
# NavDemo smoke test: lease a device, build, install, launch, sign in, tour the app.
#   tests/smoke.sh ios|android [--no-build]
# Uses the device this session already leased (simpool mine) when there is one; otherwise leases
# one and releases it at the end. Needs the mobile-device, simnav/androidnav and sim-pool skills.
set -euo pipefail
cd "$(dirname "$0")/.."
P=${1:?usage: tests/smoke.sh ios|android [--no-build]}
M=${MOBILE_DEVICE:-$HOME/.claude/skills/mobile-device/mobile-device}
leased=
if ! "$M" --platform "$P" device >/dev/null 2>&1; then
  if [ "$P" = android ]; then "$M" --platform "$P" acquire --boot "${NAVDEMO_AVD:-Pixel_3a_API_34_extension_level_7_arm64-v8a}"
  else "$M" --platform "$P" acquire; fi
  leased=1
fi
trap '[ -n "$leased" ] && "$M" --platform "$P" release || true' EXIT
[ "${2:-}" = --no-build ] || "$M" --platform "$P" build
"$M" --platform "$P" install
"$M" --platform "$P" relaunch
"$M" --platform "$P" sign-in
"$M" --platform "$P" nav "tests/tour.$P.nav"
echo "smoke $P: PASS"
