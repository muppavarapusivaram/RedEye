#!/bin/bash
set -euo pipefail

if pkill -f "openvpn --config" >/dev/null 2>&1; then
  echo "OpenVPN processes terminated."
  exit 0
fi

if pkill openvpn >/dev/null 2>&1; then
  echo "OpenVPN processes terminated."
  exit 0
fi

echo "No running OpenVPN process found."
exit 1

