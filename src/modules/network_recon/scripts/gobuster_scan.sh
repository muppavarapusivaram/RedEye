#!/usr/bin/env bash
set -euo pipefail

if [ "$#" -lt 3 ]; then
  echo "Usage: $0 <mode: dir|dns> <target> <wordlist> [extensions]" >&2
  exit 1
fi

MODE="$1"
TARGET="$2"
WORDLIST="$3"
EXTENSIONS="${4:-}"

if ! command -v gobuster >/dev/null 2>&1; then
  echo "gobuster is not installed. Install it before running this script." >&2
  exit 1
fi

if [ ! -f "$WORDLIST" ]; then
  echo "Wordlist not found: $WORDLIST" >&2
  exit 1
fi

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "$SCRIPT_DIR/../../../.." && pwd)"
REPORT_DIR="$PROJECT_ROOT/reports/network_recon"
mkdir -p "$REPORT_DIR"

TIMESTAMP="$(date +%Y%m%d_%H%M%S)"
OUTFILE="$REPORT_DIR/gobuster_${MODE}_${TIMESTAMP}.txt"

echo "[+] Running Gobuster ($MODE mode) with target: $TARGET"

case "$MODE" in
  dir)
    COMMAND=(gobuster dir -u "$TARGET" -w "$WORDLIST")
    if [ -n "$EXTENSIONS" ]; then
      COMMAND+=( -x "$EXTENSIONS" )
    fi
    ;;
  dns)
    COMMAND=(gobuster dns -d "$TARGET" -w "$WORDLIST")
    ;;
  *)
    echo "Unknown mode: $MODE (expected dir or dns)" >&2
    exit 1
    ;;
esac

if command -v timeout >/dev/null 2>&1; then
  timeout 900 "${COMMAND[@]}" | tee "$OUTFILE"
else
  "${COMMAND[@]}" | tee "$OUTFILE"
fi

echo ""
echo "[+] Gobuster results saved to: $OUTFILE"

