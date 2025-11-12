#!/bin/bash
set -euo pipefail

if [ "$#" -lt 1 ]; then
  echo "Usage: $0 <chain_mode> [scheme,host,port ...]" >&2
  exit 1
fi

CHAIN_MODE="$1"
shift

if [[ "$CHAIN_MODE" != "dynamic_chain" && "$CHAIN_MODE" != "strict_chain" && "$CHAIN_MODE" != "random_chain" ]]; then
  echo "Invalid chain mode: $CHAIN_MODE" >&2
  exit 1
fi

CONFIG=""
for candidate in /etc/proxychains.conf /etc/proxychains4.conf; do
  if [ -f "$candidate" ]; then
    CONFIG="$candidate"
    break
  fi
done

if [ -z "$CONFIG" ]; then
  echo "proxychains configuration file not found." >&2
  exit 1
fi

TMP="$(mktemp)"
trap 'rm -f "$TMP"' EXIT

mode_written=0
in_proxy_section=0
proxies_inserted=0

write_proxies() {
  if [ $proxies_inserted -eq 0 ]; then
    if [ "$#" -gt 0 ]; then
      for proxy in "$@"; do
        IFS=',' read -r scheme host port <<< "$proxy"
        echo "$scheme $host $port" >> "$TMP"
      done
    else
      echo "# (No proxies configured)" >> "$TMP"
    fi
    proxies_inserted=1
  fi
}

while IFS= read -r line || [ -n "$line" ]; do
  trimmed="$(echo "$line" | sed 's/^[[:space:]]*//;s/[[:space:]]*$//')"
  lowered="$(echo "$trimmed" | tr '[:upper:]' '[:lower:]')"

  case "$lowered" in
    dynamic_chain|strict_chain|random_chain)
      if [ "$lowered" == "$CHAIN_MODE" ]; then
        echo "$CHAIN_MODE" >> "$TMP"
        mode_written=1
      else
        echo "# $trimmed" >> "$TMP"
      fi
      continue
      ;;
    "# dynamic_chain"|"# strict_chain"|"# random_chain")
      original="${trimmed#\# }"
      if [ "$original" == "$CHAIN_MODE" ]; then
        echo "$CHAIN_MODE" >> "$TMP"
        mode_written=1
      else
        echo "# $original" >> "$TMP"
      fi
      continue
      ;;
  esac

  if [ "$lowered" == "[proxylist]" ]; then
    echo "[ProxyList]" >> "$TMP"
    in_proxy_section=1
    proxies_inserted=0
    continue
  fi

  if [ $in_proxy_section -eq 1 ]; then
    if [ -z "$trimmed" ] || [[ "$trimmed" == \#* ]]; then
      echo "$line" >> "$TMP"
      continue
    fi
    if [[ "$trimmed" == \[* ]]; then
      write_proxies "$@"
      echo "$line" >> "$TMP"
      in_proxy_section=0
      continue
    fi
    # Skip existing proxy entries
    continue
  fi

  echo "$line" >> "$TMP"
done < "$CONFIG"

if [ $mode_written -eq 0 ]; then
  echo "$CHAIN_MODE" | cat - "$TMP" > "${TMP}.mode"
  mv "${TMP}.mode" "$TMP"
fi

if [ $in_proxy_section -eq 1 ]; then
  write_proxies "$@"
fi

cat "$TMP" > "$CONFIG"
echo "Updated $CONFIG with chain mode $CHAIN_MODE."

