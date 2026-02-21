#!/usr/bin/env bash
# Start tcpdump on an interface. Saves to reports/network_attacks/.
# Usage: capture_start.sh <interface>
set -euo pipefail

if [ "$#" -lt 1 ]; then
  echo "Usage: $0 <interface>" >&2
  exit 1
fi

IFACE="$1"
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "$SCRIPT_DIR/../../.." && pwd)"
REPORTS_DIR="$PROJECT_ROOT/reports/network_attacks"
mkdir -p "$REPORTS_DIR"
PID_FILE="$REPORTS_DIR/.capture_pid"

TIMESTAMP="$(date +%Y%m%d_%H%M%S)"
PCAP="$REPORTS_DIR/capture_${TIMESTAMP}.pcap"

if ! command -v tcpdump >/dev/null 2>&1; then
  echo "tcpdump not found. Install it (apt install tcpdump)." >&2
  exit 1
fi

[ -f "$PID_FILE" ] && kill -0 "$(cat "$PID_FILE")" 2>/dev/null && kill "$(cat "$PID_FILE")" 2>/dev/null || true
rm -f "$PID_FILE"

tcpdump -i "$IFACE" -w "$PCAP" >> "$REPORTS_DIR/capture.log" 2>&1 &
echo $! > "$PID_FILE"
echo "[+] Capture started on $IFACE → $PCAP"
echo "CAPTURE_PID=$(cat "$PID_FILE")"
echo "CAPTURE_FILE=$PCAP"
