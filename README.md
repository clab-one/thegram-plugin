# thegram-cloud

Thegram memory for cloud agents: ChatGPT dots, ChatGPT and Codex, Claude, and any MCP client that runs off your Mac. The agent connects to `https://vault.thegram.one/mcp`, you sign in with your Thegram account once, and the agent gets the same `gram_*` tools as the desktop app's local MCP. No Mac, desktop app or token copying is needed.

New to Thegram? The step-by-step guide at https://thegram.one/install/#chatgpt covers sign-up and every click, and a ChatGPT dot can walk you through it from https://thegram.one/install/chatgpt.md.

## What the agent sees

| Mount | Path | Stored in |
|---|---|---|
| Each Thegram Cloud vault you can access | `@mounts/<vault id>/<name>.gram` | Thegram Cloud |
| Each Google Drive account connected at vault.thegram.one | `@mounts/google-drive-<account>/<folders>/<name>.gram` | your Google Drive |

Agents write to your Thegram Cloud vault by default and to Google Drive only when you ask. Nothing is copied between Thegram Cloud and Drive; the desktop app shows the same files when you mount the same vaults or Drive accounts there. Documents that exist only in a local folder on your Mac are not visible to cloud agents.

## Before you install

Sign in once at https://vault.thegram.one. The first sign-in creates your Thegram account; finish signing up (date of birth, terms). Agents keep memory in your Thegram Cloud vault; if you have none, Thegram creates one named `Thegram` the first time an agent connects. To let agents write to Google Drive when you ask for it, connect it under **Settings → Connections → Add account**.

## ChatGPT

1. Open https://chatgpt.com/plugins (in the ChatGPT Mac app: **Settings → Plugins → Browse directory**), select **Add**, then **Create custom MCP server**.
2. Name it `Thegram`, enter `https://vault.thegram.one/mcp` as the server URL and keep **OAuth** authentication. Leave **Advanced OAuth settings** alone: ChatGPT detects the Thegram sign-in and picks the client ID metadata document (CIMD) registration itself.
3. Tick the risk notice and select **Create as plugin**.
4. In the **Connect Thegram** dialog select **Continue to Thegram**, sign in with your Thegram account if asked, and select **Authorize** on the consent screen. The server itself tells ChatGPT to use Thegram on its own, keep memory in your vault and save what it reads from other connectors.
5. In a chat, select **+**, then Thegram under **Plugins** (it inserts `@Thegram`), and ask normally; for example "record this year's Slack history by topic" makes ChatGPT read Slack and write it to Thegram.
6. Optional: add the `thegram-cloud` skill for the full write rules. On the plugin's page select **⋯ → Download plugin ZIP**, run `scripts/chatgpt-package.sh ~/Downloads/plugin.zip 1.4.0` in this repository, then select **⋯ → Upload new version** and choose the ZIP it printed. Use a higher version for each later upload.

ChatGPT keeps access while your Mac is off by renewing it with a refresh token; disconnect the plugin in ChatGPT to cut it off. ChatGPT shows your own account name as the developer of a plugin you create this way.

## ChatGPT desktop (Work, Codex) and Codex CLI

```sh
codex plugin marketplace add clab-one/thegram-plugin
codex plugin add thegram-cloud@thegram
```

Or, after the first command, restart the ChatGPT desktop app and install Thegram from the **Thegram** marketplace under **Plugins**. It brings the MCP server and the `thegram-cloud` skill; sign in when it first connects. ChatGPT marks such plugins **Desktop only**: use the steps above for ChatGPT on the web and mobile.

## Claude Code

```sh
claude plugin marketplace add clab-one/thegram-plugin
claude plugin install thegram-cloud@thegram-cloud
```

Then run `/mcp`, select `thegram` and authenticate.

## ChatGPT Business and Enterprise workspaces

An owner or admin can upload the `thegram-cloud-<version>.zip` from the latest [release](https://github.com/clab-one/thegram-plugin/releases) at https://admin.openai.com → **Plugins → Add → Upload plugin**, and update it later with **Upload new version**. ChatGPT marks uploaded plugins that declare an MCP server **Desktop only**.

## Any other MCP client

Streamable HTTP at `https://vault.thegram.one/mcp`; the 401 response names the OAuth metadata (RFC 9728).

Give the agent `skills/thegram-cloud/SKILL.md` as its instructions if the host does not load plugin skills.

## Check

Ask the agent to call `gram_projects`. It lists your vaults and Drive accounts as mounts; `gram_brief {"folder": "<mount key>"}` then shows that mount's documents.

## Verify

`tests/e2e/mcp_e2e.py` runs the agent path end to end against a server (OAuth discovery, initialize, tools/list, create, patch, replay, stale write, brief, read, recall, state, account isolation) and writes `mcp-e2e-report.json`; see the script header for its environment variables.

## Release

The ZIP attached to each GitHub release is the package for the ChatGPT and Codex plugin directory: `zip -r thegram-cloud-<version>.zip plugin.json mcp.json skills assets`. `plugin.json` carries the listing, icons, review test cases and release notes the directory imports; the demo video URL and reviewer credentials are entered in the developer dashboard. `scripts/chatgpt-package.sh` is only for updating a private plugin made with **Create custom MCP server**.

## Limits

- Semantic search is not available on the server yet; `gram_recall` in `auto` mode uses keyword matching and says so.
- A write fails with `STORAGE_CONFLICT` instead of overwriting when the file changed elsewhere since the agent read it.
