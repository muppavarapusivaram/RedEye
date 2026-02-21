#!/usr/bin/env bash
# Stop Bettercap.
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "$SCRIPT_DIR/../../.." && pwd)"
REPORTS_DIR="$PROJECT_ROOT/reports/network_attacks"
PID_FILE="$REPORTS_DIR/.bettercap_pid"

if [ ! -f "$PID_FILE" ]; then
  echo "[+] No Bettercap process found."
  exit 0
fi

PID="$(cat "$PID_FILE")"
if kill -0 "$PID" 2>/dev/null; then
  kill -TERM "$PID" 2>/dev/null || true
  sleep 2
  kill -9 "$PID" 2>/dev/null || true
fi
rm -f "$PID_FILE"
echo "[+] Bettercap stopped."
