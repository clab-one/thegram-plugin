# thegram-cloud

The cloud plugin for [Thegram](https://thegram.one): **where your thoughts connect.** Plans, notes, ideas and knowledge live in structured .gram files that people and supported AI clients share. Each file holds a readable document, structured records, relationships and revision history. On the web at https://vault.thegram.one, people write and edit documents, explore the same records through document, dashboard and graph views, arrange dashboard widgets, and revisit earlier revisions. Each document has one dashboard for its template.

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

[`thegram-one/thegram-mcp`](https://github.com/thegram-one/thegram-mcp) owns **thegram-memory**, the coding-agent integration for Claude Code, Codex, OpenCode and OMP. Version 3.1 uses a scoped API key with the same Cloud MCP and requires no desktop app or DMG. This repository owns the OAuth cloud plugin for the OpenAI and Claude directories; API keys do not replace those OAuth connections.

Its `skills/thegram-memory/` is the canonical workflow. This repository imports that committed directory into `skills/thegram-cloud/`, pins every normalized file hash in `skill-source.lock.json` and keeps only the skill name `thegram-cloud`. Builds fail on drift; change the workflow in `thegram-mcp` first, then run `scripts/sync_skill.py --source /path/to/thegram-mcp`.

| Channel | Package | Connection |
| --- | --- | --- |
| OpenAI plugin directory (ChatGPT, Codex) | `thegram-cloud-<version>.zip` from releases | Remote MCP, OAuth |
| Claude plugin directory | This repository root (`.claude-plugin/plugin.json`) | Remote MCP, OAuth |
| Local coding agents | `thegram-one/thegram-mcp` | Scoped API key |

## Install with the bundled skill

The [versioned release ZIP](https://github.com/thegram-one/thegram-plugin/releases) is the portable package for OpenAI directory submission: root `plugin.json` carries the listing (`extensions.com.openai.interface`), icons, review cases and publication notes, with `mcp.json`, `skills/`, assets and the `.claude-plugin`/`.mcp.json` compatibility files. It must not contain `.app.json` or an `apps` binding. Submit the Claude directory listing from this repository at the `.claude-plugin/plugin.json` root through Claude's developer portal. Package checks, directory approval and end-user installation are separate steps.

In Claude Code, add this repository as a marketplace and install the plugin with `/plugin marketplace add thegram-one/thegram-plugin` and `/plugin install thegram-cloud@thegram-cloud`.

For the step-by-step connection flow, see [the install guide](https://thegram.one/install/#chatgpt) and its [agent-readable guide](https://thegram.one/install/chatgpt.md). Sign in at [Thegram Cloud](https://vault.thegram.one), finish sign-up, and keep OAuth when connecting. First sight grants write to the owned default Thegram vault only. Connect Drive in **Settings → Connections**, then explicitly allow this agent in **Settings → Connected agents** when needed.

## Public ChatGPT review materials

The English [reviewer guide](review/reviewer-guide.md) defines five positive and three negative tool scenarios; the [demo script](review/demo-script.md) distinguishes the actual recorded run from future bundled-package reproduction. Recordings used a dev-mode custom `gram` MCP connection without the bundled skill and are published at https://thegram.one/review/openai/. Keep credentials, account identifiers and private reviewer details out of public files.

### Existing private ChatGPT custom MCP plugin

Creating a custom MCP server at `https://vault.thegram.one/mcp` supplies tools but **does not automatically install this repository's skill**. To add/update it through that existing plugin's real packaging route:

1. On the plugin page, download its ZIP through **⋯ → Download plugin ZIP**.
2. Run `scripts/chatgpt-package.sh /path/to/downloaded-plugin.zip 2.4.1 /path/to/thegram-private-2.4.1.zip` in this repository. Use a version higher than that private plugin's current version.
3. Choose **⋯ → Upload new version** and upload the generated ZIP to the same plugin.
4. Verify the host lists `thegram-cloud` with the new description and can load its references. Then call `gram_projects` and a relevant `gram_brief` to verify connection separately.

The updater preserves the exported plugin's identity, app dependency, OAuth/connection configuration, unknown metadata, unrelated skills and assets. It replaces only the owned `thegram-cloud` folder, updates version and merges the skill-discovery route. It does not re-create the plugin or deploy a server. Disconnecting the plugin in the host revokes its use there.

For other MCP clients, use the same remote endpoint and OAuth discovery. If a client does not support plugin skill loading, explicitly load the [skill](skills/thegram-cloud/SKILL.md) and its referenced resources as agent instructions; connecting tools alone is not equivalent to installing the package.

## Connect Claude with the remote MCP server

In Claude **Settings → Connectors**, add a custom connector named **Thegram** with `https://vault.thegram.one/mcp`. Keep **Sign in now** and **Use Claude’s published identity** (CIMD), then complete Thegram OAuth and authorize only the intended vaults. Verify the connection by listing accessible projects and reading a relevant memory.

A remote connector supplies the MCP tools; it does not install the bundled skill or the Claude Code plugin. The Connectors Directory submission is separate from this package’s release and from a private custom connection.

## Document chat requests

People can send instructions from the chat of a Thegram document. ChatGPT receives them through MCP Events: after the plugin is connected and the agent has write access to the vault, ask ChatGPT (a Work chat or a dot) to subscribe to `chat.task.created`. Each delivered request is handled with `chat_task_get`, `chat_doc_read` and one `chat_task_submit`; these tools take a task ID instead of a path, so the agent reads and changes only the document the request came from. The tools and event are served by `https://vault.thegram.one/mcp` (protocol `2026-07-28`); after a server release that changes them, rescan the MCP server on the plugin page so the event appears beside the tools. Clients without MCP Events can still pick up requests with `chat_task_list` when the person asks.


## Search-first project binding (2.4.1)

The bundled `thegram-cloud` skill first searches accessible Cloud documents and binds the repository to a matching document; it no longer assumes a path from the selected vault or asks users to maintain a `projects.json` mapping.
## Document chat read mode (2.4.0)

The bundled skill follows the request's `mode` from `chat_task_get`. For `read`, answer in `reply` only and never submit `operations`; if `chat_task_submit` returns `E_READ_ONLY`, resubmit with the reply alone. This behavior remains unchanged from 2.4.0.

## Agent work (2.3.0)

When an agent works for you, it keeps each piece of work as one task naming the agent (`owner`) and the repository (`s`), with `start` and `done`, moves its status with the work and records each PR, merge, release, deployment or verification as one step event linked `part-of` that task. The AI work board shows who is doing what, the board of their work, how it went by day and what waits on you from exactly these records.

## Scheduled automations (2.2.0)

A document a scheduled run writes (a research digest, a monitor, a collected log) records one `run` event per execution, keeps each found item under one stable ID with `ref`, `at` and `source:`/`topic:` tags linked `derives` only to the run that first found it, and tags watched things `target`. What needs a person follows the automation's own rule in the project's description. The research, monitoring and collected-log dashboards in thegram-ui 3.31.0 read this shape. Imported from `thegram-mcp` 3.3.0 (`2f57a40`); its authoring E2E scores 54/54 and 38/38 with this skill against 18/54 and 10/38 with 3.2.2.

## One record vocabulary (2.1.2)

Every document follows Core's one record vocabulary, so the skill no longer chooses a template. Each status has an open, done or closed class shared by the dashboard, `gram_brief`, `gram_recall` and the graph. Closing a record rewrites its description, resolving evidence links `related`, and `ref` holds only links others can open.

## Semantic records and widget data (2.1.1)

The shared skill classifies atomic facts by meaning, with commits/PRs/reports as provenance. Reuse task/component/metric identities, keep proposed ADRs distinct from merged implementation, and record meaningful dated occurrences as events only when supported. Routine image pins can remain source coverage. Do not invent completed historical tasks, deployment evidence or revision activity.

The bundled widget-data reference covers the 60-kind catalog: current progress uses status classes, goal progress uses task-to-goal `part-of`, metric trends use actual same-ID observations and loaded native history, and team/presence/sync widgets require runtime capabilities. Structural readiness does not prove useful rendering or live health. The canonical source supplies offline semantic, native scratch and actual UI-selector tests; this repository checks packaging and the committed source lock.

## Validate and package

```sh
python3 -m unittest discover -s tests -p 'test_*.py' -v
python3 scripts/sync_skill.py --check
python3 scripts/package_plugin.py build --output /tmp/thegram-cloud-2.4.1.zip
python3 scripts/package_plugin.py validate /tmp/thegram-cloud-2.4.1.zip --expected-version 2.4.1
claude plugin validate --strict .
```

The CI workflow checks shell syntax and the pinned shared workflow, then builds and validates the portable package for the exact source commit. Complete lifecycle verification runs as the final integrated E2E after all builds; CI does not run separate unit or slice tests.

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

Follow [CHANGELOG.md](CHANGELOG.md). Bump `version` together in root `plugin.json`, `.claude-plugin/plugin.json` and `.claude-plugin/marketplace.json`; there is no npm version for this cloud package. Keep one `thegram-cloud` skill rather than adding a competing memory entry point.

Build and validate `thegram-cloud-<version>.zip`, commit/push the source, and publish tag `v<version>` on the exact commit with that ZIP attached. Check the exact commit's validation run and download/revalidate the published asset. Keep host-install and directory-publication claims separate from package checks. This release process publishes source and a package; it does not deploy the cloud server or change OAuth scopes, credentials, access or production settings.

## Current limits

- Cloud recall ranks by meaning like the desktop app: `semantic` and `hybrid` work, and `auto` fuses keyword and semantic ranks. When `gram_capabilities.semantic` is unavailable, or a recall reports `mode`/`reason` (for example `SEMANTIC_INDEX_STALE` while a new document is still being indexed), that call used keyword matching. Historical (`as_of`) recall is keyword-only.
- The rich profile supports collection list and table; its collection `view=board` example is not a supported-view guarantee.
- Each document has one dashboard, chosen by Core from its template: `project@1` Project Tracker, `schedule@1` Journal, `knowledge@1` Knowledge. Only a declared document is editable on it; a document without a template shows the dashboard of the type Core recommends (`~project@1` in `gram_brief`/`gram_list`) read-only, and an unknown template declaration has no dashboard. Graph, sparklines, Mermaid and historical-slider behavior depends on the consuming renderer, and the plugin's package/API validation does not establish host UI rendering.
- Historical `effective_at` selects a revision prefix, not a general merge of unordered backfilled facts. Recording time is separate from event/observation time.
- The bundled skill and public installation guidance require user authorization before saving. This repository's package changes do not establish the current deployment state of server-side onboarding instructions. Connecting only a custom MCP server without loading/updating its skill does not deliver the bundled workflow.
