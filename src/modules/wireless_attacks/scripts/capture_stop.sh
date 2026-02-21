#!/usr/bin/env bash
# Stop the running airodump-ng capture (kill PID saved by capture_start.sh).
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "$SCRIPT_DIR/../../.." && pwd)"
REPORTS_DIR="$PROJECT_ROOT/reports/wireless_attacks"
PID_FILE="$REPORTS_DIR/.current_capture_pid"
LOG_PATH_FILE="$REPORTS_DIR/.current_capture_log"
CAP_BASE_FILE="$REPORTS_DIR/.current_capture_base"

if [ ! -f "$PID_FILE" ]; then
  echo "[!] No active capture found (no PID file). Start a capture first." >&2
  exit 1
fi

PID="$(cat "$PID_FILE")"
if ! kill -0 "$PID" 2>/dev/null; then
  echo "[+] Capture process $PID was not running (already stopped)."
  rm -f "$PID_FILE" "$LOG_PATH_FILE" "$CAP_BASE_FILE"
  exit 0
fi

# Kill airodump (graceful TERM first)
kill -TERM "$PID" 2>/dev/null || true
for _ in 1 2 3 4 5; do
  kill -0 "$PID" 2>/dev/null || break
  sleep 1
done
kill -9 "$PID" 2>/dev/null || true

rm -f "$PID_FILE" "$LOG_PATH_FILE" "$CAP_BASE_FILE"

# Also kill any child processes (tee, airodump) that might have been started in the same process group
pkill -P "$PID" 2>/dev/null || true

echo "[+] Capture stopped. Cap file is in $REPORTS_DIR (e.g. cap_*-01.cap)."
