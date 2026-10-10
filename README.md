# thegram-cloud

Thegram memory for cloud agents (DOT, ChatGPT, Claude, Codex and any MCP client that runs off your Mac). The agent talks to `https://vault.thegram.one/mcp` with your Thegram token and gets the same `gram_*` tools as the desktop app's local MCP. No Mac, desktop app or Node is needed.

## What the agent sees

| Mount | Path | Stored in |
|---|---|---|
| Each Thegram Cloud vault you can access | `@mounts/<vault id>/<name>.gram` | Thegram Cloud |
| Each Google Drive account connected at vault.thegram.one | `@mounts/google-drive-<account>/<folders>/<name>.gram` | your Google Drive |

You choose where a document lives. Nothing is copied between Thegram Cloud and Drive; the desktop app shows the same files when you mount the same vaults or Drive accounts there.

## Connect

1. Sign in at https://vault.thegram.one, and connect Google Drive there if you want Drive mounts.
2. Get a token for the agent:

   ```sh
   scripts/thegram-token.sh "DOT"
   ```

   Open the printed link, approve, and keep the printed `gvt_…` token secret. It lasts 90 days. To revoke it, call `DELETE https://vault.thegram.one/v1/me/tokens/<token_id>` with the same token.
3. Add a remote MCP server to the agent:

   | Setting | Value |
   |---|---|
   | Transport | Streamable HTTP |
   | URL | `https://vault.thegram.one/mcp` |
   | Header | `Authorization: Bearer <token>` |

   Hosts that install plugins read `.mcp.json` (Claude-style) or `.codex-plugin/mcp.json` (Codex) from this repository and take the token from the `THEGRAM_TOKEN` environment variable.
4. Give the agent `skills/thegram-cloud/SKILL.md` as its instructions if the host does not load plugin skills.

## Check

Ask the agent to call `gram_projects`. It lists your vaults and Drive accounts as mounts; `gram_brief {"folder": "<mount key>"}` then shows that mount's documents.

## Verify

`tests/e2e/mcp_e2e.py` runs the agent path end to end against a server (initialize, tools/list, create, patch, replay, stale write, brief, read, recall, state, account isolation) and writes `mcp-e2e-report.json`; see the script header for its environment variables.

## Limits

- Semantic search is not available on the server yet; `gram_recall` in `auto` mode uses keyword matching and says so.
- A write fails with `STORAGE_CONFLICT` instead of overwriting when the file changed elsewhere since the agent read it.
