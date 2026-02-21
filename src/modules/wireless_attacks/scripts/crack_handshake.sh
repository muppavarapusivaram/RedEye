#!/usr/bin/env bash
# Crack WPA/WPA2 handshake using aircrack-ng.
# Usage: crack_handshake.sh <handshake.cap> <wordlist.txt>
set -euo pipefail

if [ "$#" -lt 2 ]; then
  echo "Usage: $0 <handshake_cap_file> <wordlist_file>" >&2
  exit 1
fi

CAP_FILE="$1"
WORDLIST="$2"

if [ ! -f "$CAP_FILE" ]; then
  echo "Handshake file not found: $CAP_FILE" >&2
  exit 1
fi

if [ ! -f "$WORDLIST" ]; then
  echo "Wordlist file not found: $WORDLIST" >&2
  exit 1
fi

if ! command -v aircrack-ng >/dev/null 2>&1; then
  echo "aircrack-ng is not installed. Install aircrack-ng suite and try again." >&2
  exit 1
fi

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "$SCRIPT_DIR/../../.." && pwd)"
REPORTS_DIR="$PROJECT_ROOT/reports/wireless_attacks"
mkdir -p "$REPORTS_DIR"

echo "[+] Cracking handshake: $CAP_FILE"
echo "[+] Wordlist: $WORDLIST"
echo ""
# -w = wordlist, capture file can contain one or more handshakes; aircrack will try all
aircrack-ng -w "$WORDLIST" "$CAP_FILE"
