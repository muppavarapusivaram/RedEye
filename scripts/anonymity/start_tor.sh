#!/bin/bash
set -euo pipefail

if command -v systemctl >/dev/null 2>&1; then
  if systemctl list-unit-files | grep -q '^tor@'; then
    systemctl start tor@default
  else
    systemctl start tor
  fi
elif command -v service >/dev/null 2>&1; then
  service tor start
else
  echo "Neither systemctl nor service command available to start TOR." >&2
  exit 1
fi

