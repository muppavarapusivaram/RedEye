#!/usr/bin/env bash
# Phase 2: run airodump-ng targeting one BSSID/channel, write capture to file. Runs in background.
# Usage: capture_start.sh <monitor_interface> <bssid> <channel>
# Generates cap_base under REPORTS_DIR. Writes PID to .current_capture_pid for capture_stop.sh
set -euo pipefail

if [ "$#" -lt 3 ]; then
  echo "Usage: $0 <monitor_interface> <bssid> <channel>" >&2
  exit 1
fi

IFACE="$1"
BSSID="$2"
CHANNEL="$3"

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "$SCRIPT_DIR/../../.." && pwd)"
REPORTS_DIR="$PROJECT_ROOT/reports/wireless_attacks"
mkdir -p "$REPORTS_DIR"

if ! command -v airodump-ng >/dev/null 2>&1; then
  echo "airodump-ng is not installed. Install aircrack-ng suite and try again." >&2
  exit 1
fi

TIMESTAMP="$(date +%Y%m%d_%H%M%S)"
CAP_BASE="$REPORTS_DIR/cap_${TIMESTAMP}"
LOG_FILE="${CAP_BASE}.log"
PID_FILE="$REPORTS_DIR/.current_capture_pid"
LOG_PATH_FILE="$REPORTS_DIR/.current_capture_log"
CAP_BASE_FILE="$REPORTS_DIR/.current_capture_base"

# Start airodump in background: target one AP, write to CAP_BASE; stdout to log for handshake detection
# airodump-ng --bssid BSSID --channel CH -w BASE IFACE
airodump-ng --bssid "$BSSID" --channel "$CHANNEL" -w "$CAP_BASE" "$IFACE" >> "$LOG_FILE" 2>&1 &
AIRDump_PID=$!

echo $AIRDump_PID > "$PID_FILE"
echo "$LOG_FILE" > "$LOG_PATH_FILE"
echo "$CAP_BASE" > "$CAP_BASE_FILE"

echo "[+] Capture started (PID $AIRDump_PID). Monitoring BSSID $BSSID on channel $CHANNEL."
echo "[+] Capture file: ${CAP_BASE}-01.cap (and -01.csv). Log: $LOG_FILE"
echo "[+] Run deauth attack to force handshake, then stop capture when handshake is seen."
echo "CAPTURE_PID=$AIRDump_PID"
echo "CAPTURE_LOG=$LOG_FILE"
echo "CAPTURE_BASE=$CAP_BASE"
