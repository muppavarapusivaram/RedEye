#!/usr/bin/env bash
# Stop ARP spoofing and restore IP forwarding.
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "$SCRIPT_DIR/../../.." && pwd)"
REPORTS_DIR="$PROJECT_ROOT/reports/network_attacks"
PID_FILE="$REPORTS_DIR/.arp_spoof_pids"

# Restore IP forwarding
echo 0 > /proc/sys/net/ipv4/ip_forward 2>/dev/null || true

if [ ! -f "$PID_FILE" ]; then
  echo "[+] No ARP spoof PIDs found. Already stopped."
  exit 0
fi

while read -r pid; do
  [ -n "$pid" ] && kill -0 "$pid" 2>/dev/null && kill -TERM "$pid" 2>/dev/null || true
done < "$PID_FILE"
sleep 1
while read -r pid; do
  [ -n "$pid" ] && kill -0 "$pid" 2>/dev/null && kill -9 "$pid" 2>/dev/null || true
done < "$PID_FILE"
rm -f "$PID_FILE"
echo "[+] ARP spoofing stopped."
