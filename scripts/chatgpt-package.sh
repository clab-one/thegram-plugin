#!/bin/sh
# Turns the plugin ZIP ChatGPT made for the custom MCP server into a new version that also carries the gram skill.
# Usage: scripts/chatgpt-package.sh <downloaded plugin.zip> <version> [out.zip]
set -eu
src=$1
version=$2
out=${3:-gram-chatgpt-$version.zip}
root=$(cd "$(dirname "$0")/.." && pwd)
work=$(mktemp -d)
trap 'rm -rf "$work"' EXIT
unzip -q "$src" -d "$work"
app=$(python3 -c 'import json,sys; print(json.load(open(sys.argv[1]))["name"])' "$work/.codex-plugin/plugin.json")
mkdir -p "$work/skills"
cp -R "$root/skills/thegram-cloud" "$work/skills/"
python3 - "$work/.codex-plugin/plugin.json" "$app" "$version" "$root/plugin.json" <<'EOF'
import json, sys
path, name, version, portable = sys.argv[1:]
ui = json.load(open(portable))["extensions"]["com.openai"]["interface"]
json.dump({
    "name": name,
    "version": version,
    "description": ui["longDescription"],
    "author": {"name": ui["developerName"]},
    "apps": "./.app.json",
    "skills": "./skills/",
    "interface": {k: ui[k] for k in ("displayName", "shortDescription", "longDescription", "developerName", "category", "capabilities")},
}, open(path, "w"), indent=2)
EOF
case $out in /*) ;; *) out=$PWD/$out ;; esac
rm -f "$out"
(cd "$work" && zip -qr "$out" .)
echo "$out"
