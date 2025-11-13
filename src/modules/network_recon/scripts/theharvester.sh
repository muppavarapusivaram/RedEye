#!/usr/bin/env bash
set -euo pipefail

if [ "$#" -lt 3 ]; then
  echo "Usage: $0 <domain> <sources> <limit>" >&2
  exit 1
fi

DOMAIN="$1"
SOURCES="$2"
LIMIT="$3"

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "$SCRIPT_DIR/../../../.." && pwd)"
REPORT_DIR="$PROJECT_ROOT/reports/network_recon"
mkdir -p "$REPORT_DIR"

TIMESTAMP="$(date +%Y%m%d_%H%M%S)"
OUTFILE="$REPORT_DIR/theharvester_${DOMAIN}_${TIMESTAMP}.txt"

if command -v theHarvester >/dev/null 2>&1; then
  TOOL="theHarvester"
elif command -v theharvester >/dev/null 2>&1; then
  TOOL="theharvester"
else
  echo "theHarvester is not installed. Please install it (pip install theHarvester) and try again." >&2
  exit 1
fi

echo "[+] Running $TOOL against $DOMAIN (sources: $SOURCES, limit: $LIMIT)"

if command -v timeout >/dev/null 2>&1; then
  timeout 900 "$TOOL" -d "$DOMAIN" -b "$SOURCES" -l "$LIMIT" | tee "$OUTFILE"
else
  "$TOOL" -d "$DOMAIN" -b "$SOURCES" -l "$LIMIT" | tee "$OUTFILE"
fi

echo ""
echo "[+] theHarvester results saved to: $OUTFILE"

