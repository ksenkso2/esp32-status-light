#!/bin/sh
set -eu

cd "$(dirname "$0")"
if [ "$#" -gt 1 ]; then
    echo "Usage: $0 [wifi-ssid]" >&2
    exit 2
fi
if [ "$#" -eq 1 ]; then
    exec python3 configure_wifi.py --ssid "$1"
fi
exec python3 configure_wifi.py
