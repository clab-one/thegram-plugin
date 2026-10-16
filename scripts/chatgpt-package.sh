#!/bin/sh
# Overlay the bundled skill onto a private ChatGPT custom-MCP plugin download.
# Keeps the downloaded plugin's identity, bindings, credentials and settings.
# Usage: scripts/chatgpt-package.sh <downloaded plugin.zip> <version> [out.zip]
set -eu
if [ "$#" -lt 2 ] || [ "$#" -gt 3 ]; then
    echo "Usage: $0 <downloaded plugin.zip> <version> [out.zip]" >&2
    exit 2
fi
root=$(CDPATH= cd -- "$(dirname -- "$0")/.." && pwd)
exec python3 "$root/scripts/package_plugin.py" update-private "$1" "$2" \
    --host chatgpt --root "$root" --output "${3:-thegram-chatgpt-$2.zip}"
