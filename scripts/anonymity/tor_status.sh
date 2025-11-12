#!/bin/bash
set -euo pipefail

if command -v systemctl >/dev/null 2>&1; then
  if systemctl is-active --quiet tor; then
    echo "active"
    exit 0
  elif systemctl is-active --quiet tor@default; then
    echo "active"
    exit 0
  fi
elif command -v service >/dev/null 2>&1; then
  if service tor status >/dev/null 2>&1; then
    echo "active"
    exit 0
  fi
fi

if pgrep -x tor >/dev/null 2>&1; then
  echo "active"
  exit 0
fi

echo "inactive"
exit 1

