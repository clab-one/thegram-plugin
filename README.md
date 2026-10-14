# thegram-cloud

The cloud plugin for [Thegram](https://thegram.one) gives people and supported AI clients a shared, purpose-based memory. **One purpose. One structured .gram file.** Keep useful information, sources, decisions, relationships and change history together, then explore the same records through document, dashboard and graph views in compatible Thegram apps, with revision history instead of a separate history or duplicated content for each view. Thegram Cloud currently supports Document and Dashboard; Graph is available in the desktop app. Each document has one dashboard for its type.

Use it for plans, research, shared projects or everyday work—not only software development. When you authorize saving, the assistant can preserve useful context from conversations and other apps available through its authorized connectors, with source attribution rather than a raw transcript archive. The plugin itself does not fetch Slack or Gmail, and reading another source does not itself authorize copying it into Thegram. People can read and manage the same memory in supported Thegram apps; AI clients retrieve context and record authorized outcomes. No running Mac or desktop app is required for this cloud plugin.

The plugin connects to https://vault.thegram.one/mcp using OAuth. It preserves the existing thegram-cloud identity and thegram MCP server binding. Local-only Mac files are not visible to the cloud server.

## Storage and local/cloud distinction

| Mount | Path | Storage |
| --- | --- | --- |
| Thegram Cloud vault granted to this agent | `@mounts/<vault-id>/<project>.gram` | Top-level cloud vault document. |
| Connected Drive account explicitly granted to this agent | `@mounts/google-drive-<account>/<folders>/<name>.gram` | Requested Google Drive destination. |

Use the exact keys from `gram_projects`. Reuse the established project document. Do not copy between mounts or redirect failed saves. Shared-vault viewers cannot write. Local-only Mac folders are not visible to the cloud server.

## Per-agent access scope

The server identifies an agent by the Logto access-token `client_id`, not its display name. Each agent has its own vault grants: **none < read < write < delete**, with higher levels including lower levels. First sight grants **write only to the owned default vault named Thegram** (created if needed); every other vault and personal Drive account starts with no agent access. Connecting Drive or owning a second vault does not automatically expose it to an agent.

Manage access and disconnect agents in **Settings → Connected agents** at https://vault.thegram.one/settings/agents. Grants cannot raise the user's vault role or an applicable organization ceiling. `gram_projects` hides none mounts and marks read mounts read-only; use its current exact keys instead of inferring visibility from the account's web UI. User permission to save is still required even for a writable mount.

**Reviewer handling:** `AGENT_SCOPE_DENIED` is a tool error, not a successful empty result or a save receipt. Stop the denied operation, explain which requested access is blocked, and give the settings URL. Do not retry unchanged, switch credentials, copy to another mount, or report success. The user must change the scope in their cookie-authenticated settings session; agent bearer tokens cannot manage grants. After an authorized scope change, rediscover mounts and obtain fresh revision/hash before retrying the original authorized operation. Disconnecting clears access immediately, including still-unexpired tokens and existing MCP sessions; reconnecting is a separate user action.

The current MCP tool set has **no document-delete tool**. A delete-level grant includes write but does not add a deletion tool. Deleting records with `gram_patch` is a document edit, not proof of document-delete permission. API-audience tokens represent an app user (`KindBearer`), not an MCP agent (`KindAgent`); API deletion with those tokens cannot verify agent delete enforcement.

[`clab-one/thegram-mcp`](https://github.com/clab-one/thegram-mcp) owns the separate **thegram-memory** desktop integration. Its Node hooks/adapters, repository-folder mapping, local MCP proxy and injected brief require the running Mac app. This repository owns the remote cloud plugin and its distribution; installing this package does not install that local integration.

## Install with the bundled skill

The [versioned release ZIP](https://github.com/clab-one/thegram-plugin/releases) is the portable plugin package for supported ChatGPT/Codex directory import: root `plugin.json`, `mcp.json`, `skills/`, assets and cloud-client compatibility files. Agent Plugins clients discover the skill at `skills/thegram-cloud/SKILL.md`; references and synthetic lifecycle examples ship in that same skill folder. A directory import and an end-user installation are separate steps. Availability or approval in a public directory is not established merely by publishing a GitHub release.

For the step-by-step connection flow, see [the install guide](https://thegram.one/install/#chatgpt) and its [agent-readable guide](https://thegram.one/install/chatgpt.md). Sign in at [Thegram Cloud](https://vault.thegram.one), finish sign-up, and keep OAuth when connecting. First sight grants write to the owned default Thegram vault only. Connect Drive in **Settings → Connections**, then explicitly allow this agent in **Settings → Connected agents** when needed.

## Public ChatGPT review materials

The English [reviewer guide](review/reviewer-guide.md) defines five positive and three negative tool scenarios; the [demo script](review/demo-script.md) distinguishes the actual recorded run from future bundled-package reproduction. Recordings used a dev-mode custom `gram` MCP connection without the bundled skill and are published at https://thegram.one/review/openai/. Keep credentials, account identifiers and private reviewer details out of public files.

### Existing private ChatGPT custom MCP plugin

Creating a custom MCP server at `https://vault.thegram.one/mcp` supplies tools but **does not automatically install this repository's skill**. To add/update it through that existing plugin's real packaging route:

1. On the plugin page, download its ZIP through **⋯ → Download plugin ZIP**.
2. Run `scripts/chatgpt-package.sh /path/to/downloaded-plugin.zip 2.0.1 /path/to/thegram-private-2.0.1.zip` in this repository. Use a version higher than that private plugin's current version.
3. Choose **⋯ → Upload new version** and upload the generated ZIP to the same plugin.
4. Verify the host lists `thegram-cloud` with the new description and can load its references. Then call `gram_projects` and a relevant `gram_brief` to verify connection separately.

The updater preserves the exported plugin's identity, app dependency, OAuth/connection configuration, unknown metadata, unrelated skills and assets. It replaces only the owned `thegram-cloud` folder, updates version and merges the skill-discovery route. It does not re-create the plugin or deploy a server. Disconnecting the plugin in the host revokes its use there.

For other MCP clients, use the same remote endpoint and OAuth discovery. If a client does not support plugin skill loading, explicitly load the [skill](skills/thegram-cloud/SKILL.md) and its referenced resources as agent instructions; connecting tools alone is not equivalent to installing the package.

## Connect Claude with the remote MCP server

In Claude **Settings → Connectors**, add a custom connector named **Thegram** with `https://vault.thegram.one/mcp`. Keep **Sign in now** and **Use Claude’s published identity** (CIMD), then complete Thegram OAuth and authorize only the intended vaults. Verify the connection by listing accessible projects and reading a relevant memory.

A remote connector supplies the MCP tools; it does not install the bundled skill or the Claude Code plugin. The Connectors Directory submission is separate from this package’s release and from a private custom connection.

## Validate and package

```sh
python3 -m unittest discover -s tests -p 'test_*.py' -v
python3 scripts/package_plugin.py build --output /tmp/thegram-cloud-2.0.1.zip
python3 scripts/package_plugin.py validate /tmp/thegram-cloud-2.0.1.zip --expected-version 2.0.1
```

The offline packaging tests use synthetic exported ZIPs to check preservation, discovery, owned-folder replacement, references and unsafe-archive rejection. No OAuth tokens or personal files are required. The CI workflow runs these checks for the exact source commit.

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

Build and validate `thegram-cloud-<version>.zip`, commit/push the source, and publish tag `v<version>` on the exact commit with that ZIP attached. Check the exact commit's validation run and download/revalidate the published asset. Keep host-install and directory-publication claims separate from package checks. This release process publishes source and a package; it does not deploy the cloud server or change OAuth scopes, credentials, access or production settings.

## Current limits

- Cloud recall ranks by meaning like the desktop app: `semantic` and `hybrid` work, and `auto` fuses keyword and semantic ranks. When `gram_capabilities.semantic` is unavailable, or a recall reports `mode`/`reason` (for example `SEMANTIC_INDEX_STALE` while a new document is still being indexed), that call used keyword matching. Historical (`as_of`) recall is keyword-only.
- The rich profile supports collection list and table; its collection `view=board` example is not a supported-view guarantee.
- Each document has one dashboard, chosen by Core from its template: `project@1` Project Tracker, `schedule@1` Journal, `knowledge@1` Knowledge. Only a declared document is editable on it; a document without a template shows the dashboard of the type Core recommends (`~project@1` in `gram_brief`/`gram_list`) read-only, and an unknown template declaration has no dashboard. Graph, sparklines, Mermaid and historical-slider behavior depends on the consuming renderer, and the plugin's package/API validation does not establish host UI rendering.
- Historical `effective_at` selects a revision prefix, not a general merge of unordered backfilled facts. Recording time is separate from event/observation time.
- The bundled skill and public installation guidance require user authorization before saving. This repository's package changes do not establish the current deployment state of server-side onboarding instructions. Connecting only a custom MCP server without loading/updating its skill does not deliver the bundled workflow.
