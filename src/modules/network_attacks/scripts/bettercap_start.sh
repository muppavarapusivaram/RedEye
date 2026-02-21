#!/usr/bin/env bash
# Start Bettercap on an interface (background). Run bettercap_stop.sh to stop.
# Usage: bettercap_start.sh <interface>
set -euo pipefail

if [ "$#" -lt 1 ]; then
  echo "Usage: $0 <interface>" >&2
  exit 1
fi

IFACE="$1"
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "$SCRIPT_DIR/../../.." && pwd)"
REPORTS_DIR="$PROJECT_ROOT/reports/network_attacks"
PID_FILE="$REPORTS_DIR/.bettercap_pid"
LOG_FILE="$REPORTS_DIR/bettercap_$(date +%Y%m%d_%H%M%S).log"
mkdir -p "$REPORTS_DIR"

if ! command -v bettercap >/dev/null 2>&1; then
  echo "bettercap not found. Install it: apt install bettercap" >&2
  exit 1
fi

[ -f "$PID_FILE" ] && kill -0 "$(cat "$PID_FILE")" 2>/dev/null && kill "$(cat "$PID_FILE")" 2>/dev/null || true
rm -f "$PID_FILE"

nohup bettercap -iface "$IFACE" >> "$LOG_FILE" 2>&1 &
echo $! > "$PID_FILE"
echo "[+] Bettercap started on $IFACE (PID $(cat "$PID_FILE")). Log: $LOG_FILE"
echo "[+] Use 'bettercap -iface $IFACE' in another terminal to attach, or run bettercap_stop.sh to stop."
echo "BETTERCAP_PID=$(cat "$PID_FILE")"
