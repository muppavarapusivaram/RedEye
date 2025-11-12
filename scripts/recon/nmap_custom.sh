#!/bin/bash
set -euo pipefail

if [ "$#" -lt 1 ]; then
  echo "Usage: $0 <target> [additional_nmap_arguments...]" >&2
  exit 1
fi

target="$1"
shift

if [ -z "$target" ]; then
  echo "Target cannot be empty." >&2
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

echo "[+] Running custom Nmap scan against $target"
echo "[+] Report will be saved to: $REPORT_FILE"

# Run nmap and save output to both file and stdout using tee
nmap -sS -sV -O "$target" "$@" | tee "$REPORT_FILE"

echo ""
echo "[+] Scan completed. Report saved to: $REPORT_FILE"

