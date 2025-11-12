#!/bin/bash
set -euo pipefail

if command -v systemctl >/dev/null 2>&1; then
  if systemctl list-unit-files | grep -q '^tor@'; then
    systemctl stop tor@default
  else
    systemctl stop tor
  fi
elif command -v service >/dev/null 2>&1; then
  service tor stop
else
  echo "Neither systemctl nor service command available to stop TOR." >&2
  exit 1
fi

echo "TOR service stopped."

