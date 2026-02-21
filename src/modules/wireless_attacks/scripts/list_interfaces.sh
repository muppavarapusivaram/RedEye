#!/usr/bin/env bash
set -euo pipefail

if ! command -v airmon-ng >/dev/null 2>&1; then
  echo "airmon-ng is not installed. Install aircrack-ng suite and try again." >&2
  exit 1
fi

echo "[+] Wireless interfaces (airmon-ng):"
echo ""
airmon-ng
