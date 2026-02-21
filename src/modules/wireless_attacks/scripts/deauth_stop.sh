#!/usr/bin/env bash
# Stop the continuous deauth attack started by deauth.sh --continuous.
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "$SCRIPT_DIR/../../.." && pwd)"
REPORTS_DIR="$PROJECT_ROOT/reports/wireless_attacks"
PID_FILE="$REPORTS_DIR/.current_deauth_pid"

if [ ! -f "$PID_FILE" ]; then
  echo "[!] No deauth process found (no PID file). Start deauth first with 'Deauth attack'." >&2
  exit 1
fi

PID="$(cat "$PID_FILE")"
if ! kill -0 "$PID" 2>/dev/null; then
  echo "[+] Deauth process $PID was not running (already stopped)."
  rm -f "$PID_FILE"
  exit 0
fi

kill -TERM "$PID" 2>/dev/null || true
sleep 1
kill -9 "$PID" 2>/dev/null || true
rm -f "$PID_FILE"
echo "[+] Deauth attack stopped."
