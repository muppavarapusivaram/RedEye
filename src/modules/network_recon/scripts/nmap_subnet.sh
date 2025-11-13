#!/usr/bin/env bash
set -euo pipefail

interface="$(ip route | awk '/default/ {print $5; exit}')"
if [ -z "$interface" ]; then
  echo "Unable to determine default network interface." >&2
  exit 1
fi

cidr="$(ip -o -f inet addr show "$interface" | awk '{print $4}' | head -n 1)"
if [ -z "$cidr" ]; then
  echo "Unable to determine subnet for interface $interface." >&2
  exit 1
fi

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "$SCRIPT_DIR/../../../.." && pwd)"
REPORTS_DIR="$PROJECT_ROOT/reports/network_recon"
mkdir -p "$REPORTS_DIR"

TIMESTAMP="$(date +%Y%m%d_%H%M%S)"
REPORT_FILE="$REPORTS_DIR/nmap_subnet_${TIMESTAMP}.txt"

echo "[+] Running Nmap subnet scan against $cidr via interface $interface"
echo "[+] Report will be saved to: $REPORT_FILE"

COMMAND=(nmap -sS -sV -T4 --max-retries 1 --min-rate 1000 "$cidr")
if command -v timeout >/dev/null 2>&1; then
  timeout 900 "${COMMAND[@]}" | tee "$REPORT_FILE"
else
  "${COMMAND[@]}" | tee "$REPORT_FILE"
fi

echo ""
echo "[+] Scan completed. Report saved to: $REPORT_FILE"
