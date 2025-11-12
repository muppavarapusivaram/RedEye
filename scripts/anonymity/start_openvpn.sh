#!/bin/bash
set -euo pipefail

if [ "$#" -ne 1 ]; then
  echo "Usage: $0 <ovpn_config_path>" >&2
  exit 1
fi

PROFILE="$1"

if [ ! -f "$PROFILE" ]; then
  echo "OpenVPN profile not found: $PROFILE" >&2
  exit 1
fi

exec openvpn --config "$PROFILE"

