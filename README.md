# thegram-cloud

Thegram memory for cloud agents: ChatGPT dots, ChatGPT and Codex, Claude, and any MCP client that runs off your Mac. The agent connects to `https://vault.thegram.one/mcp`, you sign in with your Thegram account once, and the agent gets the same `gram_*` tools as the desktop app's local MCP. No Mac, desktop app or token copying is needed.

## What the agent sees

| Mount | Path | Stored in |
|---|---|---|
| Each Thegram Cloud vault you can access | `@mounts/<vault id>/<name>.gram` | Thegram Cloud |
| Each Google Drive account connected at vault.thegram.one | `@mounts/google-drive-<account>/<folders>/<name>.gram` | your Google Drive |

You choose where a document lives. Nothing is copied between Thegram Cloud and Drive; the desktop app shows the same files when you mount the same vaults or Drive accounts there. Documents that exist only in a local folder on your Mac are not visible to cloud agents.

## Connect a ChatGPT dot

1. Sign in at https://vault.thegram.one, and connect Google Drive there if you want Drive mounts.
2. Open https://chatgpt.com/plugins, select **+**, then **Add custom MCP server**.
3. Name it `Thegram`, enter `https://vault.thegram.one/mcp` as the URL, and choose **OAuth** authentication. ChatGPT finds the Thegram sign-in on its own; leave the client fields empty.
4. Accept the risk notice, select **Create as a plugin**, then **Install**.
5. Sign in with your Thegram account and approve the consent screen.
6. In the dot, open **Customize → Plugins** and enable Thegram, or mention `@Thegram` in a chat.

The dot keeps working while your Mac is off: ChatGPT renews its access with a refresh token. Disconnect the plugin in ChatGPT to cut it off.

To install the packaged plugin instead (skills included), add this repository as a marketplace and install `thegram-cloud`; `plugin.json` and `mcp.json` declare the same server with OAuth.

## Other MCP clients

| Client | Setup |
|---|---|
| Claude Code | install this repository as a plugin, or `claude mcp add --transport http thegram https://vault.thegram.one/mcp`, then authenticate from `/mcp` |
| Codex | install the plugin from a marketplace that lists this repository |
| Anything else | Streamable HTTP at `https://vault.thegram.one/mcp`; the 401 response names the OAuth metadata (RFC 9728) |

Give the agent `skills/thegram-cloud/SKILL.md` as its instructions if the host does not load plugin skills.

## Check

Ask the agent to call `gram_projects`. It lists your vaults and Drive accounts as mounts; `gram_brief {"folder": "<mount key>"}` then shows that mount's documents.

## Verify

`tests/e2e/mcp_e2e.py` runs the agent path end to end against a server (OAuth discovery, initialize, tools/list, create, patch, replay, stale write, brief, read, recall, state, account isolation) and writes `mcp-e2e-report.json`; see the script header for its environment variables.

## Limits

- Semantic search is not available on the server yet; `gram_recall` in `auto` mode uses keyword matching and says so.
- A write fails with `STORAGE_CONFLICT` instead of overwriting when the file changed elsewhere since the agent read it.
