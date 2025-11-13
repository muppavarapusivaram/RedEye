#!/usr/bin/env bash
set -euo pipefail

if [ "$#" -lt 2 ]; then
  echo "Usage: $0 <domain> <workspace>" >&2
  exit 1
fi

DOMAIN="$1"
WORKSPACE="$2"

if ! command -v recon-ng >/dev/null 2>&1; then
  echo "recon-ng is not installed. Install it before running this script." >&2
  exit 1
fi

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "$SCRIPT_DIR/../../../.." && pwd)"
REPORT_DIR="$PROJECT_ROOT/reports/network_recon"
mkdir -p "$REPORT_DIR"

TIMESTAMP="$(date +%Y%m%d_%H%M%S)"
OUTFILE="$REPORT_DIR/reconng_${WORKSPACE}_${TIMESTAMP}.txt"
RC_FILE="$(mktemp)"

cat > "$RC_FILE" <<EOF
workspaces select $WORKSPACE
workspaces create $WORKSPACE
workspaces select $WORKSPACE
set TIMEOUT 10
modules load recon/domains-hosts/brute_hosts
options set SOURCE $DOMAIN
run
back
modules load recon/domains-hosts/enum_simple
options set SOURCE $DOMAIN
run
back
modules load recon/domains-hosts/google_site_web
options set SOURCE $DOMAIN
run
back
workspaces summary
exit
EOF

echo "[+] Running recon-ng with workspace '$WORKSPACE' against $DOMAIN"

if command -v timeout >/dev/null 2>&1; then
  timeout 900 recon-ng -r "$RC_FILE" | tee "$OUTFILE"
else
  recon-ng -r "$RC_FILE" | tee "$OUTFILE"
fi

rm -f "$RC_FILE"

echo ""
echo "[+] Recon-ng results saved to: $OUTFILE"

