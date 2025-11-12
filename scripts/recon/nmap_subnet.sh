#!/bin/bash
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

# Get script directory and project root
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "$SCRIPT_DIR/../.." && pwd)"
REPORTS_DIR="$PROJECT_ROOT/reports"

# Create reports directory if it doesn't exist
mkdir -p "$REPORTS_DIR"

# Generate timestamp for filename
TIMESTAMP="$(date +%Y%m%d_%H%M%S)"
REPORT_FILE="$REPORTS_DIR/nmap_scan_${TIMESTAMP}.txt"

echo "[+] Running Nmap scan against subnet $cidr via interface $interface"
echo "[+] Using faster scan options: SYN scan with service detection (OS detection disabled for speed)"
echo "[+] Report will be saved to: $REPORT_FILE"

# Use faster timing (-T4), SYN scan (-sS), service detection (-sV), but skip OS detection (-O) for speed
# Add --max-retries 1 and --min-rate 1000 for faster scanning
# Save output to both file and stdout using tee
nmap -sS -sV -T4 --max-retries 1 --min-rate 1000 "$cidr" | tee "$REPORT_FILE"

echo ""
echo "[+] Scan completed. Report saved to: $REPORT_FILE"

