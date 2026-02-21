#!/usr/bin/env bash
# Phase 1: run airodump-ng for a short time to list APs, then output numbered list for GUI.
# Usage: capture_scan.sh <monitor_interface>
# Output: lines "N BSSID CHANNEL ESSID", then "CAP_BASE=<path>" for use in capture_start.sh
set -euo pipefail

if [ "$#" -lt 1 ]; then
  echo "Usage: $0 <monitor_interface>   (e.g. mon0)" >&2
  exit 1
fi

IFACE="$1"
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "$SCRIPT_DIR/../../.." && pwd)"
REPORTS_DIR="$PROJECT_ROOT/reports/wireless_attacks"
mkdir -p "$REPORTS_DIR"

if ! command -v airodump-ng >/dev/null 2>&1; then
  echo "airodump-ng is not installed. Install aircrack-ng suite and try again." >&2
  exit 1
fi

TIMESTAMP="$(date +%Y%m%d_%H%M%S)"
BASE="$REPORTS_DIR/scan_${TIMESTAMP}"

echo "[+] Scanning for networks on $IFACE (15 seconds)..."
# Run airodump-ng for 15 seconds; it writes BASE-01.csv (and .cap). We only need the CSV for the list.
timeout 15 airodump-ng -w "$BASE" "$IFACE" >/dev/null 2>&1 || true

CSV="${BASE}-01.csv"
if [ ! -f "$CSV" ]; then
  echo "[!] No CSV output from airodump. Try checking interface and permissions (run as root)." >&2
  exit 1
fi

# Parse CSV: skip header and empty BSSID; BSSID is col 1, channel 4, ESSID 14 (ESSID can contain spaces)
# Format varies; airodump CSV has: BSSID, First time seen, Last time seen, channel, Speed, Privacy, Cipher, Auth, Power, # beacons, # IV, LAN IP, ID-length, ESSID, Key
N=0
while IFS= read -r line; do
  # Skip header and station list (we only want AP lines; AP lines have BSSID in form XX:XX:XX:XX:XX:XX)
  if [[ "$line" =~ ^([0-9A-Fa-f]{2}:[0-9A-Fa-f]{2}:[0-9A-Fa-f]{2}:[0-9A-Fa-f]{2}:[0-9A-Fa-f]{2}:[0-9A-Fa-f]{2}) ]]; then
    BSSID="${BASH_REMATCH[1]}"
    # Simple field split: first 4 comma-separated fields then rest; channel is 4th
    CHANNEL="$(echo "$line" | cut -d',' -f4 | tr -d ' ')"
    # ESSID is typically after 13th comma (field 14); be careful with commas inside ESSID
    ESSID="$(echo "$line" | cut -d',' -f14- | sed 's/^ *//;s/ *$//' | head -c 32)"
    [ -z "$ESSID" ] && ESSID="(hidden)"
    N=$((N + 1))
    echo "$N $BSSID $CHANNEL $ESSID"
  fi
done < "$CSV"

if [ "$N" -eq 0 ]; then
  echo "[!] No access points found. Ensure monitor mode is enabled and in range." >&2
  exit 1
fi

# Cap base for the actual targeted capture (phase 2) - use a new timestamp so we write to a new file
CAP_TS="$(date +%Y%m%d_%H%M%S)"
CAP_BASE="$REPORTS_DIR/cap_${CAP_TS}"
echo "CAP_BASE=$CAP_BASE"
echo "[+] Scan complete. Select target number and start monitoring with capture_start.sh <interface> <bssid> <channel>"
