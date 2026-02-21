#!/usr/bin/env bash
set -euo pipefail

# Stop John the Ripper processes

echo "[+] Stopping John the Ripper processes..."

# Kill all john processes
pkill -f "john.*--wordlist" || true

# Wait a moment for processes to terminate
sleep 1

# Force kill if still running
pkill -9 -f "john.*--wordlist" || true

echo "[+] John processes stopped."
