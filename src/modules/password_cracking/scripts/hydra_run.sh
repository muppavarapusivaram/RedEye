#!/usr/bin/env bash
set -euo pipefail

# Hydra online password attack script
# Usage: hydra_run.sh <target> <service> <username> <wordlist> [-s <port>] [extra_args...]

TARGET="${1:-}"
SERVICE="${2:-}"
USERNAME="${3:-}"
WORDLIST="${4:-}"

if [[ -z "$TARGET" ]] || [[ -z "$SERVICE" ]] || [[ -z "$USERNAME" ]] || [[ -z "$WORDLIST" ]]; then
    echo "[!] Usage: hydra_run.sh <target> <service> <username> <wordlist> [-s <port>] [extra_args...]"
    echo "[!] Example: hydra_run.sh 192.168.1.100 ssh admin /usr/share/wordlists/rockyou.txt"
    exit 1
fi

if [[ ! -f "$WORDLIST" ]]; then
    echo "[!] Wordlist not found: $WORDLIST"
    exit 1
fi

REPORTS_DIR="$(cd "$(dirname "$0")/../../.." && pwd)/reports/password_cracking"
mkdir -p "$REPORTS_DIR"

TIMESTAMP=$(date +"%Y%m%d_%H%M%S")
OUTPUT_FILE="$REPORTS_DIR/hydra_${SERVICE}_${TARGET}_${TIMESTAMP}.txt"

echo "[+] Starting Hydra..."
echo "[+] Target: $TARGET"
echo "[+] Service: $SERVICE"
echo "[+] Username: $USERNAME"
echo "[+] Wordlist: $WORDLIST"
echo "[+] Output will be saved to: $OUTPUT_FILE"
echo ""

# Build hydra command
HYDRA_CMD=("hydra" "-l" "$USERNAME" "-P" "$WORDLIST")

# Parse remaining arguments for port and extra args
shift 4
while [[ $# -gt 0 ]]; do
    if [[ "$1" == "-s" ]] && [[ -n "${2:-}" ]]; then
        HYDRA_CMD+=("-s" "$2")
        shift 2
    else
        HYDRA_CMD+=("$1")
        shift
    fi
done

HYDRA_CMD+=("$TARGET" "$SERVICE")

"${HYDRA_CMD[@]}" 2>&1 | tee "$OUTPUT_FILE"

echo ""
echo "[+] Hydra attack completed."
echo "[+] Results saved to: $OUTPUT_FILE"
