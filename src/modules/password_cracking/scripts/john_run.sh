#!/usr/bin/env bash
set -euo pipefail

# John the Ripper password cracking script
# Usage: john_run.sh <hash_file> <wordlist> [--format <format>]

HASH_FILE="${1:-}"
WORDLIST="${2:-}"
FORMAT_ARG=""

# Parse optional format argument
if [[ "${3:-}" == "--format" ]] && [[ -n "${4:-}" ]]; then
    FORMAT_ARG="--format=${4}"
fi

if [[ -z "$HASH_FILE" ]] || [[ -z "$WORDLIST" ]]; then
    echo "[!] Usage: john_run.sh <hash_file> <wordlist> [--format <format>]"
    exit 1
fi

if [[ ! -f "$HASH_FILE" ]]; then
    echo "[!] Hash file not found: $HASH_FILE"
    exit 1
fi

if [[ ! -f "$WORDLIST" ]]; then
    echo "[!] Wordlist not found: $WORDLIST"
    exit 1
fi

REPORTS_DIR="$(cd "$(dirname "$0")/../../.." && pwd)/reports/password_cracking"
mkdir -p "$REPORTS_DIR"

TIMESTAMP=$(date +"%Y%m%d_%H%M%S")
OUTPUT_FILE="$REPORTS_DIR/john_${TIMESTAMP}.txt"

echo "[+] Starting John the Ripper..."
echo "[+] Hash file: $HASH_FILE"
echo "[+] Wordlist: $WORDLIST"
if [[ -n "$FORMAT_ARG" ]]; then
    echo "[+] Format: ${FORMAT_ARG#--format=}"
fi
echo "[+] Output will be saved to: $OUTPUT_FILE"
echo ""

if [[ -n "$FORMAT_ARG" ]]; then
    john "$FORMAT_ARG" --wordlist="$WORDLIST" "$HASH_FILE" 2>&1 | tee "$OUTPUT_FILE"
else
    john --wordlist="$WORDLIST" "$HASH_FILE" 2>&1 | tee "$OUTPUT_FILE"
fi

echo ""
echo "[+] John cracking session completed."
echo "[+] Results saved to: $OUTPUT_FILE"
