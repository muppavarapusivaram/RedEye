#!/usr/bin/env bash
set -euo pipefail

if [ "$#" -lt 2 ]; then
  echo "Usage: $0 <domain> <mode: passive|active|bruteforce>" >&2
  exit 1
fi

DOMAIN="$1"
MODE="$2"

if ! command -v amass >/dev/null 2>&1; then
  echo "amass is not installed. Install it before running this script." >&2
  exit 1
fi

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "$SCRIPT_DIR/../../../.." && pwd)"
REPORT_DIR="$PROJECT_ROOT/reports/network_recon"
mkdir -p "$REPORT_DIR"

TIMESTAMP="$(date +%Y%m%d_%H%M%S)"
OUTFILE="$REPORT_DIR/amass_${MODE}_${DOMAIN}_${TIMESTAMP}.txt"

echo "[+] Running Amass ($MODE mode) against $DOMAIN"

COMMAND=(amass enum -d "$DOMAIN")
case "$MODE" in
  passive)
    COMMAND+=( -passive )
    ;;
  bruteforce)
    COMMAND+=( -brute )
    ;;
  active)
    # default active scan – no special flag needed
    ;;
  *)
    echo "Unknown mode: $MODE" >&2
    exit 1
    ;;
esac

if command -v timeout >/dev/null 2>&1; then
  timeout 900 "${COMMAND[@]}" | tee "$OUTFILE"
else
  "${COMMAND[@]}" | tee "$OUTFILE"
fi

echo ""
echo "[+] Amass results saved to: $OUTFILE"

