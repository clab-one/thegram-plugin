# thegram-cloud

The cloud plugin for [Thegram](https://thegram.one) gives people and supported AI clients a shared, purpose-based memory. **One purpose. One structured .gram file.** Keep useful information, sources, decisions, relationships and change history together, then explore the same records through document, dashboard and graph views in compatible Thegram apps, with revision history instead of a separate history or duplicated content for each view. Thegram Cloud currently supports Document and Dashboard; Graph is available in the desktop app. Each document has one dashboard for its type.

Use it for plans, research, shared projects or everyday work—not only software development. When you authorize saving, the assistant can preserve useful context from conversations and other apps available through its authorized connectors, with source attribution rather than a raw transcript archive. The plugin itself does not fetch Slack or Gmail, and reading another source does not itself authorize copying it into Thegram. People can read and manage the same memory in supported Thegram apps; AI clients retrieve context and record authorized outcomes. No running Mac or desktop app is required for this cloud plugin.

The plugin connects to https://vault.thegram.one/mcp using OAuth. It preserves the existing thegram-cloud identity and thegram MCP server binding. Local-only Mac files are not visible to the cloud server.

## Storage and local/cloud distinction

| Mount | Path | Storage |
| --- | --- | --- |
| Thegram Cloud vault granted to this agent | `@mounts/<vault-id>/[<folders>/]<project>.gram` | Cloud vault document, at the root or in a folder. |
| Connected Drive account explicitly granted to this agent | `@mounts/google-drive-<account>/<folders>/<name>.gram` | Requested Google Drive destination. |

Use the exact keys from `gram_projects`. Reuse the established project document. Do not copy between mounts or redirect failed saves. Shared-vault viewers cannot write. Local-only Mac folders are not visible to the cloud server.

## Per-agent access scope

The server identifies an agent by the Logto access-token `client_id`, not its display name. Each agent has its own vault grants: **none < read < write < delete**, with higher levels including lower levels. First sight grants **write only to the owned default vault named Thegram** (created if needed); every other vault and personal Drive account starts with no agent access. Connecting Drive or owning a second vault does not automatically expose it to an agent.

Manage access and disconnect agents in **Settings → Connected agents** at https://vault.thegram.one/settings/agents. Grants cannot raise the user's vault role or an applicable organization ceiling. `gram_projects` hides none mounts and marks read mounts read-only; use its current exact keys instead of inferring visibility from the account's web UI. User permission to save is still required even for a writable mount.

**Reviewer handling:** `AGENT_SCOPE_DENIED` is a tool error, not a successful empty result or a save receipt. Stop the denied operation, explain which requested access is blocked, and give the settings URL. Do not retry unchanged, switch credentials, copy to another mount, or report success. The user must change the scope in their cookie-authenticated settings session; agent bearer tokens cannot manage grants. After an authorized scope change, rediscover mounts and obtain fresh revision/hash before retrying the original authorized operation. Disconnecting clears access immediately, including still-unexpired tokens and existing MCP sessions; reconnecting is a separate user action.

Discover supported tools from the running MCP server; a grant never creates a capability the server does not offer. Coding-agent API keys are `KindAgent` credentials confined to MCP and their explicit scopes. Logto API-audience tokens represent an app user (`KindBearer`), not an MCP agent; native API responses do not establish MCP agent permissions.

[`clab-one/thegram-mcp`](https://github.com/clab-one/thegram-mcp) owns **thegram-memory**, the coding-agent integration for Claude Code, Codex, OpenCode and OMP. Version 3.1 uses a scoped API key with the same Cloud MCP and requires no desktop app or DMG. Its `skills/thegram-memory/` is the canonical workflow. This repository imports that committed directory, pins every normalized file hash in `skill-source.lock.json` and retains the cloud skill's existing name `thegram-cloud`. Only that frontmatter name differs; the workflow and references are shared. API keys do not replace the ChatGPT or Claude OAuth connections.

## Install with the bundled skill

Choose the native ZIP for your host from the [versioned releases](https://github.com/clab-one/thegram-plugin/releases):

| Client | ZIP | Connection |
| --- | --- | --- |
| ChatGPT | `thegram-chatgpt-2.0.5.zip` | Existing registered Thegram app and OAuth |
| Claude | `thegram-claude-2.0.5.zip` | Remote Thegram MCP and OAuth |
| Local coding agents | `clab-one/thegram-mcp` 3.1 | Scoped API key, no desktop app |

The ChatGPT ZIP contains `.codex-plugin/plugin.json`, the registered app mapping `.app.json`, `.mcp.json`, `skills/` and assets. The Claude ZIP contains `.claude-plugin/plugin.json`, `.mcp.json`, the same skill and assets; it does not include the OpenAI app mapping. Both retain the plugin name `thegram-cloud`, the MCP server name `thegram` and `https://vault.thegram.one/mcp`. A ZIP contains no account credentials: first use still requires the host's OAuth consent. Update an existing installation through that host's plugin update/upload-new-version route, not by creating a different connection.

Do not use the old generic `thegram-cloud-2.0.4.zip` as a native end-user installer. Its failed ChatGPT upload was reported by the user; no server-side rejection reason was available. Publishing a correctly structured ZIP, native CLI parser checks and successful account/UI installation are separate evidence. The source root's portable manifest remains for directory metadata; the release builder emits only the explicitly selected native host format.

For the step-by-step connection flow, see [the install guide](https://thegram.one/install/#chatgpt) and its [agent-readable guide](https://thegram.one/install/chatgpt.md). Sign in at [Thegram Cloud](https://vault.thegram.one), finish sign-up, and keep OAuth when connecting. First sight grants write to the owned default Thegram vault only. Connect Drive in **Settings → Connections**, then explicitly allow this agent in **Settings → Connected agents** when needed.

## Public ChatGPT review materials

The English [reviewer guide](review/reviewer-guide.md) defines five positive and three negative tool scenarios; the [demo script](review/demo-script.md) distinguishes the actual recorded run from future bundled-package reproduction. Recordings used a dev-mode custom `gram` MCP connection without the bundled skill and are published at https://thegram.one/review/openai/. Keep credentials, account identifiers and private reviewer details out of public files.

### Existing private ChatGPT custom MCP plugin

Creating a custom MCP server at `https://vault.thegram.one/mcp` supplies tools but **does not automatically install this repository's skill**. To add/update it through that existing plugin's real packaging route:

1. On the plugin page, download its ZIP through **⋯ → Download plugin ZIP**.
2. Run `scripts/chatgpt-package.sh /path/to/downloaded-plugin.zip 2.0.5 /path/to/thegram-private-2.0.5.zip` in this repository. Use a version higher than that private plugin's current version.
3. Choose **⋯ → Upload new version** and upload the generated ZIP to the same plugin.
4. Verify the host lists `thegram-cloud` with the new description and can load its references. Then call `gram_projects` and a relevant `gram_brief` to verify connection separately.

The updater preserves the exported plugin's identity, app dependency, OAuth/connection configuration, unknown metadata, unrelated skills and assets. It replaces only the owned `thegram-cloud` folder, updates version and merges the skill-discovery route. It does not re-create the plugin or deploy a server. A private custom plugin can have a different registered app ID: update its own export rather than replacing its identity with the public ChatGPT ZIP. Claude native exports can use `python3 scripts/package_plugin.py private --host claude --help` and the same preservation rules. Disconnecting the plugin in the host revokes its use there.

For other MCP clients, use the same remote endpoint and OAuth discovery. If a client does not support plugin skill loading, explicitly load the [skill](skills/thegram-cloud/SKILL.md) and its referenced resources as agent instructions; connecting tools alone is not equivalent to installing the package.

## Install the Claude OAuth plugin

Upload `thegram-claude-2.0.5.zip` through Claude's plugin upload flow. For later skill releases update the same `thegram-cloud` plugin, keeping the `thegram` MCP binding and OAuth connection. The ZIP carries both the bundled skill and remote MCP configuration. Complete OAuth only when Claude requires first connection or renewed consent; no API key belongs in this package.

If using **Settings → Connectors** independently, add **Thegram** at `https://vault.thegram.one/mcp`, keep **Sign in now** and **Use Claude’s published identity** (CIMD), then grant only the intended vaults. A connector alone supplies tools, not the bundled skill. The Connectors Directory submission is separate from ZIP release or private installation.

Shared instructions do not imply identical host hooks: Chat does not run Claude Code/Cowork hooks. The workflow is the common skill; local lifecycle reminders are host adapters.

## Validate and package

```sh
python3 -m unittest discover -s tests -p 'test_*.py' -v
python3 scripts/sync_skill.py --source /path/to/thegram-mcp
python3 scripts/sync_skill.py --check
python3 scripts/package_plugin.py build --host chatgpt --output /tmp/thegram-chatgpt-2.0.5.zip --expected-version 2.0.5
python3 scripts/package_plugin.py validate /tmp/thegram-chatgpt-2.0.5.zip --host chatgpt --expected-version 2.0.5
python3 scripts/package_plugin.py build --host claude --output /tmp/thegram-claude-2.0.5.zip --expected-version 2.0.5
python3 scripts/package_plugin.py validate /tmp/thegram-claude-2.0.5.zip --host claude --expected-version 2.0.5
```

Change and commit shared workflow files in the canonical coding-agent repository before syncing. `sync_skill.py` rejects uncommitted skill files; release builds reject hash drift from the pinned import. The offline packaging tests check both native formats, reproducible archives, private identity/connection preservation, discovery, owned-folder replacement, references and unsafe-archive rejection. No OAuth tokens or personal files are required. CI checks the exact source commit and builds both host ZIPs; it does not establish actual account/UI installation or OAuth consent.

With the `claude` and `codex` CLIs installed, run the native-parser E2E in a new, task-owned workspace:

```sh
python3 tests/e2e/host_packages.py --agents /path/to/thegram-mcp \
  --workspace /tmp/thegram-host-check-unique --output /path/to/evidence/native-host-e2e.json
```

It builds both real ZIPs, compares their complete shared workflow with the canonical source, runs Claude's strict validator and
discovers the OpenAI package through Codex's native parser. Isolated profiles contain no credentials; the driver does not install
into a real account, invoke a model, or start OAuth. It retains the command outputs and archive hashes in the JSON report.
Preserve that report and required ZIPs before removing the workspace; successful parser checks do not prove ChatGPT/Claude UI installation.

For cloud-wrapper lifecycle behavior, use [tests/offline](tests/offline/README.md) with the matching vault source and native Core binary. It exercises the shipped fictional payloads in temporary storage. This verifies the API layer independently of production mounts and does not establish end-user installation, provider/OAuth behavior or UI rendering.

`tests/e2e/mcp_e2e.py` and `tests/e2e/consent_e2e.mjs` are **live** OAuth/provider checks, not packaging CI. The agent-scope mode creates a fresh temporary Logto Native application for first-sight isolation, signs an existing consenting adult E2E mailbox in with a Management API one-time token, obtains MCP tokens through 401 discovery and PKCE, and manages scopes only with the user's cookie session + CSRF. It cleans its own vaults/documents and temporary application, never resets an account or another agent's grants.

Run next before production (the production run is skipped if next fails):

```sh
stamp=$(date -u +%Y%m%dT%H%M%SZ)
export THEGRAM_AGENT_SCOPE=1 GRAM_VAULT_E2E_SIGNIN=token
export THEGRAM_E2E_MAILBOX='<mailbox-listed-in-~/.config/thegram-vault/e2e-mailboxes.json>'
THEGRAM_SERVER=https://next.thegram.one python3 tests/e2e/mcp_e2e.py "evidence/agent-scope-$stamp/next" &&
THEGRAM_SERVER=https://vault.thegram.one python3 tests/e2e/mcp_e2e.py "evidence/agent-scope-$stamp/production"
```

Management credentials remain outside the repository in `~/.config/thegram-vault/logto-apps.json`. Each `agent-scope-report.json` includes checks, credential-redacted exact MCP and scope-API exchanges, cleanup results, the advertised MCP audience, and explicit coverage gaps. The suite verifies default-only visibility, hidden new vaults, read-only denials, write sync, delete-level write inclusion, and immediate disconnect using the same unexpired MCP token/session. **It cannot test document-delete enforcement through MCP**; that criterion is recorded as unreachable, not passed. Server unit tests cover enforcement. The next endpoint currently advertises the production MCP audience `https://vault.thegram.one/mcp`; the report records this separate isolation risk rather than pretending the audiences are independent.

## Release

Follow [CHANGELOG.md](CHANGELOG.md). Bump `version` together in root `plugin.json` and `.claude-plugin/plugin.json`; there is no npm version for this cloud package. Keep one `thegram-cloud` skill rather than adding a competing memory entry point.

Build and validate `thegram-chatgpt-<version>.zip` and `thegram-claude-<version>.zip`, commit/push the canonical source and cloud source, then publish tag `v<version>` on the exact cloud commit with both ZIPs attached. Check the exact commit's validation run and download/revalidate each published asset. Never publish an ambiguous generic ZIP as the native installer. Keep host-install and directory-publication claims separate from package checks. This process does not deploy the cloud server or change OAuth scopes, credentials, access or production settings.

## Current limits

- Cloud recall ranks by meaning like the desktop app: `semantic` and `hybrid` work, and `auto` fuses keyword and semantic ranks. When `gram_capabilities.semantic` is unavailable, or a recall reports `mode`/`reason` (for example `SEMANTIC_INDEX_STALE` while a new document is still being indexed), that call used keyword matching. Historical (`as_of`) recall is keyword-only.
- The rich profile supports collection list and table; its collection `view=board` example is not a supported-view guarantee.
- Each document has one dashboard, chosen by Core from its template: `project@1` Project Tracker, `schedule@1` Journal, `knowledge@1` Knowledge. Only a declared document is editable on it; a document without a template shows the dashboard of the type Core recommends (`~project@1` in `gram_brief`/`gram_list`) read-only, and an unknown template declaration has no dashboard. Graph, sparklines, Mermaid and historical-slider behavior depends on the consuming renderer, and the plugin's package/API validation does not establish host UI rendering.
- Historical `effective_at` selects a revision prefix, not a general merge of unordered backfilled facts. Recording time is separate from event/observation time.
- The bundled skill and public installation guidance require user authorization before saving. This repository's package changes do not establish the current deployment state of server-side onboarding instructions. Connecting only a custom MCP server without loading/updating its skill does not deliver the bundled workflow.
