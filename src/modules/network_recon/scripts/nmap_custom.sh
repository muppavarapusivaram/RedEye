#!/usr/bin/env bash
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

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "$SCRIPT_DIR/../../../.." && pwd)"
REPORTS_DIR="$PROJECT_ROOT/reports/network_recon"
mkdir -p "$REPORTS_DIR"

TIMESTAMP="$(date +%Y%m%d_%H%M%S)"
REPORT_FILE="$REPORTS_DIR/nmap_custom_${TIMESTAMP}.txt"

echo "[+] Running custom Nmap scan against $target"
echo "[+] Report will be saved to: $REPORT_FILE"

COMMAND=(nmap -sS -sV -O "$target" "$@")
if command -v timeout >/dev/null 2>&1; then
  timeout 900 "${COMMAND[@]}" | tee "$REPORT_FILE"
else
  "${COMMAND[@]}" | tee "$REPORT_FILE"
fi

echo ""
echo "[+] Scan completed. Report saved to: $REPORT_FILE"
