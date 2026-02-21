#!/usr/bin/env bash
set -euo pipefail

if [ "$#" -lt 1 ]; then
  echo "Usage: $0 <interface>   (e.g. wlan0)" >&2
  exit 1
fi

IFACE="$1"

if ! command -v airmon-ng >/dev/null 2>&1; then
  echo "airmon-ng is not installed. Install aircrack-ng suite and try again." >&2
  exit 1
fi

echo "[+] Enabling monitor mode on $IFACE..."
# airmon-ng start IFACE creates mon0 (or wlan0mon on some systems); output contains the new name
OUTPUT="$(airmon-ng start "$IFACE" 2>&1)" || true
echo "$OUTPUT"

# Try to detect created interface: usually "mon0" or "${IFACE}mon"
if echo "$OUTPUT" | grep -q "monitor mode enabled"; then
  # Common: " (monitor mode enabled on mon0)" or " (monitor mode enabled on wlan0mon)"
  MON_IFACE="$(echo "$OUTPUT" | grep -oP 'monitor mode enabled on \K\S+' | head -1)"
  if [ -n "$MON_IFACE" ]; then
    echo ""
    echo "MONITOR_INTERFACE=$MON_IFACE"
  fi
fi

# Fallback: check for mon0 or wlan0mon
if [ -z "${MON_IFACE:-}" ]; then
  if ip link show mon0 &>/dev/null; then
    echo "MONITOR_INTERFACE=mon0"
  elif ip link show "${IFACE}mon" &>/dev/null 2>&1; then
    echo "MONITOR_INTERFACE=${IFACE}mon"
  fi
fi
