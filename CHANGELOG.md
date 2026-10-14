# Changelog

## 2.0.0 — 2026-10-14

- Start new memories from a template: schedule@1 for schedules and journals, project@1 for tasks and projects, knowledge@1 for research, knowledge and operations notes. Create with `gram_create {template}` and follow `gram_profile {topic: "templates"}` for required fields, status values and action ids.
- Write to the head by default: omit base_revision and expected_hash, give each set/unset `old` (the value read, null if empty) and use `values` for repeated fields. Reread and decide on `E_PRECONDITION`; fix `E_TEMPLATE` and `E_ACTION` by `details.diagnostics` (field, expected, example) before dropping an action.
- Add live agent-scope MCP E2E with a fresh Logto client, one-time-token cookie sign-in, CSRF-protected grant management, default-only visibility, hidden ungranted vaults, read/write enforcement, and immediate revocation with the same unexpired MCP token/session. Clean temporary vaults/documents and the Logto application; write credential-redacted JSON request/response evidence.
- Keep the ordinary MCP E2E on the default granted Thegram vault unless a pre-granted mount is specified; creating an arbitrary vault no longer implies agent write access.
- Explain per-agent scopes and Connected agents settings in README, package descriptions, reviewer expectations and bundled skill error guidance. Preserve five positive and three negative review cases and existing package identity/version/OAuth bindings.
- Record the unavailable MCP document-delete coverage explicitly: no deletion tool exists, and app API tokens do not exercise agent grants. Report the next endpoint’s production MCP audience as an isolation risk.
- Document Claude custom-connector setup using the existing MCP endpoint and CIMD OAuth, separately from bundled-skill installation and directory publication.
- Preserve safety-hint checks in the live consent E2E without pinning the entire annotations object or initialization wording.

## 1.5.4 — 2026-10-13

- Thegram Cloud recall now ranks by meaning like the desktop app: `semantic` and `hybrid` work and `auto` fuses keyword and semantic ranks. Update the skill, contracts and README, which previously said cloud recall was keyword-only.
- Explain how to recognize a keyword fallback: `gram_capabilities.semantic` unavailable, or a recall reporting `mode`/`reason` such as `SEMANTIC_INDEX_STALE` while a new document is indexed. Historical (`as_of`) recall stays keyword-only.

The server-side change was deployed separately to vault.thegram.one; this package changes no MCP/OAuth configuration, credentials, access or scopes.

## 1.5.3 — 2026-10-12

- Clarify purpose-based .gram memory for people and AI: save only what the user asks to save, with source attribution and revision history; Cloud supports Document and Dashboard, with Graph in the desktop app. MCP/OAuth configuration is unchanged.
- Update the package's save-consent guidance and public installation documentation to require explicit user authorization. This package change does not establish the deployment state of server-side onboarding instructions.
- Prepare the synthetic Atlas review fixture; keep reviewer account details and portal configuration private.
- Record five positive and three negative live cases in ChatGPT web on 2026-10-12. The runs used a dev-mode custom `gram` MCP connection without the bundled skill and do not establish bundled-skill behavior. The recordings are published at https://thegram.one/review/openai/.
- The three recordings are publicly available: [review cases](https://thegram.one/assets/review/thegram-review-cases-en.mp4), [ChatGPT walkthrough](https://thegram.one/assets/review/chatgpt-gram-demo-en.mp4), and [web/Mac montage](https://thegram.one/assets/review/thegram-chatgpt-web-mac-montage-en.mp4).

Owner maintenance: if the service requests updated terms acceptance, complete it before continuing. Before each repeat run, restore Atlas to the clean fixture and remove `northstar-website-refresh` if present; the existing authorized user account can be reused.

No server deployment or credential/access/scope change is performed by this package update. The review recordings are publicly available at the URL above.

## 1.5.2 — 2026-10-12

- Reposition the public plugin for people and AI working from shared, purpose-based .gram memory, with source-grounded history and relationships kept in one reusable file.
- Clarify the same records' document/dashboard/graph presentation and revision history in compatible apps: Cloud supports Document and Dashboard; Graph is available in the desktop app. Preserve connector-provided context only when saving is authorized, without implying direct Slack/Gmail fetching or indiscriminate capture.
- Synchronize package manifests at 1.5.2 and align the English/Korean listing, marketplace and skill description. Preserve thegram-cloud identity, C.Lab developer, Roy Kim author and existing MCP/OAuth configuration.
- Keep five positive and three negative scenarios; attribute the staging outcome to the user's report rather than independently verified evidence.

These package changes do not deploy the cloud server, change accounts/access/scopes/OAuth/credentials, or establish review submission or publication.

## 1.5.1 — 2026-10-12

- Align the OpenAI interface developer name with C.Lab and synchronize public package manifests at version 1.5.1; keep Roy Kim as package author.
- Finalize the five-positive/three-negative English review cases and proposed recording sequence; add explicit ISO 8601 UTC historical `gram_changes` guidance to the reviewer materials and bundled skill/contracts.
- Record that 1.5.3 updates package consent guidance and reviewer setup, cases, and published recording status.

No cloud server deployment, account/access/scope change, OAuth change, or credential change accompanies these metadata and documentation updates.

## 1.5.0 — 2026-10-11

- Replace broad connector capture instructions with the English durable project-memory lifecycle for dot and other cloud agents: current context, selective retrieval, authorized outcomes, readable purpose/state/reasons/evolution and unresolved work.
- Add source-grounded typed-record/relationship guidance, stable metric IDs, honest event/recording time, conflict/replay recovery, supported-view limits and fictional lifecycle payloads.
- Bundle the single thegram-cloud skill and its references through the portable release package and the existing private ChatGPT ZIP update route.
- Preserve private plugin identity, app bindings, connection settings, unknown metadata and unrelated skills during ZIP updates; validate discovery and reject unsafe archives.
- Add offline package/behavior validation and exact-commit CI. Keep cloud/local integration, storage verification, host installation and renderer verification distinct.

No cloud server deployment, access/scope change or credential change accompanied 1.5.0.
