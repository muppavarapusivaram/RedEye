#!/usr/bin/env bash
set -euo pipefail

# Hashcat password cracking script
# Usage: hashcat_run.sh <hash_file> <hash_type> <wordlist> [extra_args...]

HASH_FILE="${1:-}"
HASH_TYPE="${2:-}"
WORDLIST="${3:-}"
EXTRA_ARGS=("${@:4}")

if [[ -z "$HASH_FILE" ]] || [[ -z "$HASH_TYPE" ]] || [[ -z "$WORDLIST" ]]; then
    echo "[!] Usage: hashcat_run.sh <hash_file> <hash_type> <wordlist> [extra_args...]"
    echo "[!] Example: hashcat_run.sh hashes.txt 0 /usr/share/wordlists/rockyou.txt"
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
OUTPUT_FILE="$REPORTS_DIR/hashcat_${TIMESTAMP}.txt"

echo "[+] Starting Hashcat..."
echo "[+] Hash file: $HASH_FILE"
echo "[+] Hash type (-m): $HASH_TYPE"
echo "[+] Wordlist: $WORDLIST"
if [[ ${#EXTRA_ARGS[@]} -gt 0 ]]; then
    echo "[+] Extra arguments: ${EXTRA_ARGS[*]}"
fi
echo "[+] Output will be saved to: $OUTPUT_FILE"
echo ""

hashcat -m "$HASH_TYPE" -a 0 "$HASH_FILE" "$WORDLIST" "${EXTRA_ARGS[@]}" 2>&1 | tee "$OUTPUT_FILE"

echo ""
echo "[+] Hashcat cracking completed."
echo "[+] Results saved to: $OUTPUT_FILE"
