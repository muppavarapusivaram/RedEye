#!/usr/bin/env bash
set -euo pipefail

if [ "$#" -lt 1 ]; then
  echo "Usage: $0 <monitor_interface>   (e.g. mon0 or wlan0mon)" >&2
  exit 1
fi

IFACE="$1"

if ! command -v airmon-ng >/dev/null 2>&1; then
  echo "airmon-ng is not installed. Install aircrack-ng suite and try again." >&2
  exit 1
fi

echo "[+] Disabling monitor mode on $IFACE..."
airmon-ng stop "$IFACE" 2>&1 || true
echo "[+] Monitor mode disabled."
