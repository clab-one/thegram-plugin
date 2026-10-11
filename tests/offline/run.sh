#!/bin/sh
# Run the real cloud gateway/Core against synthetic, temporary storage only.
set -eu

: "${THEGRAM_VAULT_SOURCE:?Set THEGRAM_VAULT_SOURCE to a checkout of thegram-vault}"
: "${GRAM_CORE_BINARY:?Set GRAM_CORE_BINARY to the native gram executable}"

script_dir=$(CDPATH= cd -- "$(dirname -- "$0")" && pwd)
plugin_dir=$(CDPATH= cd -- "$script_dir/../.." && pwd)
vault_source=$(CDPATH= cd -- "$THEGRAM_VAULT_SOURCE" && pwd)
core_dir=$(CDPATH= cd -- "$(dirname -- "$GRAM_CORE_BINARY")" && pwd)
core_binary="$core_dir/$(basename -- "$GRAM_CORE_BINARY")"
fixture=${THEGRAM_LIFECYCLE_FIXTURE:-"$plugin_dir/skills/thegram-cloud/references/lifecycle.json"}
test -x "$core_binary" || { echo "GRAM_CORE_BINARY must be executable" >&2; exit 1; }
test -f "$fixture" || { echo "Lifecycle fixture not found: $fixture" >&2; exit 1; }
fixture_dir=$(CDPATH= cd -- "$(dirname -- "$fixture")" && pwd)
fixture="$fixture_dir/$(basename -- "$fixture")"

scratch=$(mktemp -d "${TMPDIR:-/tmp}/thegram-offline.XXXXXX")
trap 'rm -rf "$scratch"' EXIT HUP INT TERM
for package in mcp gramcore identity; do
  mkdir -p "$scratch/internal/$package"
  for source_file in "$vault_source/internal/$package/"*.go; do
    case "$source_file" in *_test.go) continue ;; esac
    cp "$source_file" "$scratch/internal/$package/"
  done
done
cp "$script_dir/gateway_test.go" "$scratch/internal/mcp/offline_test.go"
printf 'module thegram.one/vaultd\n\ngo 1.26\n' > "$scratch/go.mod"

echo "Offline synthetic cloud gateway checks (no HTTP server, OAuth, provider, or user mount)"
echo "Gateway source: $vault_source"
echo "Core binary: $core_binary"
echo "Fixture: $fixture"
cd "$scratch"
GRAM_CORE_BINARY="$core_binary" THEGRAM_LIFECYCLE_FIXTURE="$fixture" \
  GOCACHE="$scratch/go-cache" GOPATH="$scratch/go-path" \
  GOPROXY=off GOSUMDB=off GOTOOLCHAIN=local CGO_ENABLED=0 \
  go test -count=1 -v ./internal/mcp -run '^TestOffline'
