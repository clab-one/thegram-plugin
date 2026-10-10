#!/bin/sh
# Issues a Thegram bearer token for a cloud agent through the vault's device authorization flow.
# Usage: scripts/thegram-token.sh ["DOT"]   (needs curl and python3; prints the token on stdout)
set -eu
server="${THEGRAM_SERVER:-https://vault.thegram.one}"
name="${1:-Cloud agent}"

field() { python3 -c 'import json,sys; v=json.load(sys.stdin).get(sys.argv[1]); print("" if v is None else v)' "$1"; }
body=$(python3 -c 'import json,sys; print(json.dumps({"client_name": sys.argv[1]}))' "$name")

code=$(curl -fsS -X POST -H 'Content-Type: application/json' -d "$body" "$server/v1/device/code")
device=$(printf '%s' "$code" | field device_code)
interval=$(printf '%s' "$code" | field interval)
printf 'Open %s and approve "%s" (code %s).\n' "$(printf '%s' "$code" | field verification_uri_complete)" "$name" "$(printf '%s' "$code" | field user_code)" >&2

while :; do
	sleep "${interval:-5}"
	answer=$(curl -sS -X POST -H 'Content-Type: application/json' -d "{\"device_code\":\"$device\"}" "$server/v1/device/token")
	token=$(printf '%s' "$answer" | field access_token)
	if [ -n "$token" ]; then
		printf '%s\n' "$token"
		exit 0
	fi
	case $(printf '%s' "$answer" | field error) in
	authorization_pending) ;;
	slow_down) interval=$((${interval:-5} + 5)) ;;
	*) printf 'Token request failed: %s\n' "$answer" >&2; exit 1 ;;
	esac
done
