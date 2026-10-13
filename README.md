# thegram-cloud

The cloud plugin for [Thegram](https://thegram.one) gives people and supported AI clients a shared, purpose-based memory. **One purpose. One structured .gram file.** Keep useful information, sources, decisions, relationships and change history together, then explore the same records through document, dashboard and graph views in compatible Thegram apps, with revision history instead of a separate history or duplicated content for each view. Cloud surfaces currently support Document and Dashboard; Graph is available in the desktop app. Views depend on the recorded structure and the app.

Use it for plans, research, shared projects or everyday work—not only software development. When you authorize saving, the assistant can preserve useful context from conversations and other apps available through its authorized connectors, with source attribution rather than a raw transcript archive. The plugin itself does not fetch Slack or Gmail, and reading another source does not itself authorize copying it into Thegram. People can read and manage the same memory in supported Thegram apps; AI clients retrieve context and record authorized outcomes. No running Mac or desktop app is required for this cloud plugin.

The plugin connects to https://vault.thegram.one/mcp using OAuth. It preserves the existing thegram-cloud identity and thegram MCP server binding. Local-only Mac files are not visible to the cloud server.

## Storage and local/cloud distinction

| Mount | Path | Storage |
| --- | --- | --- |
| Thegram Cloud vault accessible to the account | `@mounts/<vault-id>/<project>.gram` | Top-level cloud vault document. |
| Drive account connected at vault.thegram.one | `@mounts/google-drive-<account>/<folders>/<name>.gram` | Requested Google Drive destination. |

Use the exact keys from `gram_projects`. Reuse the established project document. Do not copy between mounts or redirect failed saves. Shared-vault viewers cannot write. Local-only Mac folders are not visible to the cloud server.

[`clab-one/thegram-mcp`](https://github.com/clab-one/thegram-mcp) owns the separate **thegram-memory** desktop integration. Its Node hooks/adapters, repository-folder mapping, local MCP proxy and injected brief require the running Mac app. This repository owns the remote cloud plugin and its distribution; installing this package does not install that local integration.

## Install with the bundled skill

The [versioned release ZIP](https://github.com/clab-one/thegram-plugin/releases) is the portable plugin package for supported ChatGPT/Codex directory import: root `plugin.json`, `mcp.json`, `skills/`, assets and cloud-client compatibility files. Agent Plugins clients discover the skill at `skills/thegram-cloud/SKILL.md`; references and synthetic lifecycle examples ship in that same skill folder. A directory import and an end-user installation are separate steps. Availability or approval in a public directory is not established merely by publishing a GitHub release.

For the step-by-step connection flow, see [the install guide](https://thegram.one/install/#chatgpt) and its [agent-readable guide](https://thegram.one/install/chatgpt.md). Sign in at [Thegram Cloud](https://vault.thegram.one), finish sign-up, and keep OAuth when connecting. The server may create a default writable vault on first discovery. Connect Drive in **Settings → Connections** when needed.

## Public ChatGPT review materials

The English [reviewer guide](review/reviewer-guide.md) defines five positive and three negative tool scenarios; the [demo script](review/demo-script.md) distinguishes the actual recorded run from future bundled-package reproduction. Recordings used a dev-mode custom `gram` MCP connection without the bundled skill and are published at https://thegram.one/review/openai/. Keep credentials, account identifiers and private reviewer details out of public files.

### Existing private ChatGPT custom MCP plugin

Creating a custom MCP server at `https://vault.thegram.one/mcp` supplies tools but **does not automatically install this repository's skill**. To add/update it through that existing plugin's real packaging route:

1. On the plugin page, download its ZIP through **⋯ → Download plugin ZIP**.
2. Run `scripts/chatgpt-package.sh /path/to/downloaded-plugin.zip 1.5.4 /path/to/thegram-private-1.5.4.zip` in this repository. Use a version higher than that private plugin's current version.
3. Choose **⋯ → Upload new version** and upload the generated ZIP to the same plugin.
4. Verify the host lists `thegram-cloud` with the new description and can load its references. Then call `gram_projects` and a relevant `gram_brief` to verify connection separately.

The updater preserves the exported plugin's identity, app dependency, OAuth/connection configuration, unknown metadata, unrelated skills and assets. It replaces only the owned `thegram-cloud` folder, updates version and merges the skill-discovery route. It does not re-create the plugin or deploy a server. Disconnecting the plugin in the host revokes its use there.

For other MCP clients, use the same remote endpoint and OAuth discovery. If a client does not support plugin skill loading, explicitly load the [skill](skills/thegram-cloud/SKILL.md) and its referenced resources as agent instructions; connecting tools alone is not equivalent to installing the package.

## Validate and package

```sh
python3 -m unittest discover -s tests -p 'test_*.py' -v
python3 scripts/package_plugin.py build --output /tmp/thegram-cloud-1.5.4.zip
python3 scripts/package_plugin.py validate /tmp/thegram-cloud-1.5.4.zip --expected-version 1.5.4
```

The offline packaging tests use synthetic exported ZIPs to check preservation, discovery, owned-folder replacement, references and unsafe-archive rejection. No OAuth tokens or personal files are required. The CI workflow runs these checks for the exact source commit.

For cloud-wrapper lifecycle behavior, use [tests/offline](tests/offline/README.md) with the matching vault source and native Core binary. It exercises the shipped fictional payloads in temporary storage. This verifies the API layer independently of production mounts and does not establish end-user installation, provider/OAuth behavior or UI rendering.

`tests/e2e/mcp_e2e.py` and `tests/e2e/consent_e2e.mjs` are existing **live** OAuth/provider checks. They create/delete scratch cloud resources and need explicit appropriate authorization and configured credentials; they are not run by packaging CI.

## Release

Follow [CHANGELOG.md](CHANGELOG.md). Bump `version` together in root `plugin.json` and `.claude-plugin/plugin.json`; there is no npm version for this cloud package. Keep one `thegram-cloud` skill rather than adding a competing memory entry point.

Build and validate `thegram-cloud-<version>.zip`, commit/push the source, and publish tag `v<version>` on the exact commit with that ZIP attached. Check the exact commit's validation run and download/revalidate the published asset. Keep host-install and directory-publication claims separate from package checks. This release process publishes source and a package; it does not deploy the cloud server or change OAuth scopes, credentials, access or production settings.

## Current limits

- Cloud recall ranks by meaning like the desktop app: `semantic` and `hybrid` work, and `auto` fuses keyword and semantic ranks. When `gram_capabilities.semantic` is unavailable, or a recall reports `mode`/`reason` (for example `SEMANTIC_INDEX_STALE` while a new document is still being indexed), that call used keyword matching. Historical (`as_of`) recall is keyword-only.
- The rich profile supports collection list and table; its generic board example is not a supported-view guarantee. A .gram file can contain typed, linked records and can be rendered in different ways, but each surface supports its own view types and may require explicit view configuration in the file.
- Dashboard, graph, sparklines, Mermaid and historical-slider behavior depends on the consuming renderer and the file's supported structure/configuration. The plugin does not automatically generate a dashboard or graph, and its package/API validation does not establish host UI rendering.
- Historical `effective_at` selects a revision prefix, not a general merge of unordered backfilled facts. Recording time is separate from event/observation time.
- The bundled skill and public installation guidance require user authorization before saving. This repository's package changes do not establish the current deployment state of server-side onboarding instructions. Connecting only a custom MCP server without loading/updating its skill does not deliver the bundled workflow.
