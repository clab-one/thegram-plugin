# thegram-cloud

Thegram memory for cloud agents: ChatGPT dots, ChatGPT and Codex, Claude, and any MCP client that runs off your Mac. The agent connects to `https://vault.thegram.one/mcp`, you sign in with your Thegram account once, and the agent gets the same `gram_*` tools as the desktop app's local MCP. No Mac, desktop app or token copying is needed.

New to Thegram? The step-by-step guide at https://thegram.one/install/#chatgpt covers sign-up and every click, and a ChatGPT dot can walk you through it from https://thegram.one/install/chatgpt.md.

## What the agent sees

| Mount | Path | Stored in |
|---|---|---|
| Each Thegram Cloud vault you can access | `@mounts/<vault id>/<name>.gram` | Thegram Cloud |
| Each Google Drive account connected at vault.thegram.one | `@mounts/google-drive-<account>/<folders>/<name>.gram` | your Google Drive |

You choose where a document lives. Nothing is copied between Thegram Cloud and Drive; the desktop app shows the same files when you mount the same vaults or Drive accounts there. Documents that exist only in a local folder on your Mac are not visible to cloud agents.

## Connect a ChatGPT dot

1. Sign in at https://vault.thegram.one. The first sign-in creates your Thegram account; finish signing up (date of birth, terms). Then, under **Settings → Connections**, create a vault with **New Vault** or connect Google Drive with **Add account**, so the agent has somewhere to keep documents.
2. Open https://chatgpt.com/plugins (in the ChatGPT Mac app: **Settings → Plugins → Browse directory**), select **Add**, then **Create custom MCP server**.
3. Name it `Thegram`, enter `https://vault.thegram.one/mcp` as the server URL and keep **OAuth** authentication. Leave **Advanced OAuth settings** alone: ChatGPT detects the Thegram sign-in and picks the client ID metadata document (CIMD) registration itself.
4. Tick the risk notice and select **Create as plugin**.
5. In the **Connect Thegram** dialog select **Continue to Thegram**, sign in with your Thegram account if asked, and select **Authorize** on the consent screen. ChatGPT returns to its plugin list with Thegram installed.
6. Add the gram skill, which makes the dot use Thegram on its own and save what it reads from Slack, Gmail and other connectors. On the plugin's page select **⋯ → Download plugin ZIP**, run `scripts/chatgpt-package.sh ~/Downloads/plugin.zip 1.2.0` in this repository, then select **⋯ → Upload new version** and choose the `gram-chatgpt-1.2.0.zip` it printed. The plugin is now called `gram` and lists one app and the `thegram-cloud` skill. Use a higher version for each later upload.
7. In the dot's chat, select **+**, then gram under **Plugins** (it inserts `@gram`). After that, ask normally; for example "record this year's Slack history by topic" makes the dot read Slack and write it to Thegram.

The dot keeps working while your Mac is off: ChatGPT renews its access with a refresh token. Disconnect the plugin in ChatGPT to cut it off. ChatGPT shows your ChatGPT account name as the plugin's developer; `developerName` in the package is ignored for private plugins.

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
