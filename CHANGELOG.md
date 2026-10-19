# Changelog

## 2.1.2 — 2026-10-19

- Import the canonical 3.2.2 skill: every document follows Core's one record vocabulary (`gram@1`), so `gram_create` takes no template. One status table gives each status its open, done or closed class, which the dashboard, `gram_brief`, `gram_recall {status}` and the graph all count by; `mitigated` risks and `proposed` decisions stay open.
- Closing a record: rewrite `d` in the same patch, link resolving evidence `related` rather than `supports`, reconcile the same fact in other documents first, and keep `ref` to links others can open (no `file://` or local paths). A new classification case covers a fix that resolves one risk and only mitigates another.
- Needs the vaultd release that serves the one vocabulary; the OAuth configuration and MCP endpoint are unchanged.

## 2.1.1 — 2026-10-19

- Import the canonical 3.2.1 skill: classify atomic facts by meaning; reuse tracked tasks, components and metric identities; preserve proposed decisions, incomplete work, relation scope and source dates. No automatic commit events or invented historical task lifecycles.
- Add worked classification regressions and widget data contracts for status classes, goal links, calendars, metrics, saved-layout readiness and runtime-only capabilities.
- The eight shared skill files match the tested private ChatGPT plugin 2.1.1 after the canonical frontmatter identity replacement. Package and adapter configuration are unchanged.

## 2.1.0 — 2026-10-18

- Document chat: the skill (pinned from `thegram-mcp` 3.2.0, commit `bc0e2dd`) tells ChatGPT how to subscribe to the `chat.task.created` MCP event and answer each request with `chat_task_get`, `chat_doc_read` and one `chat_task_submit`, which read and change only the document the request came from. The contract reference lists the chat tools, event and errors.
- The listing adds the document chat capability, one positive and one negative review case, and 2.1.0 release notes. The MCP E2E accepts the four chat tools beside the `gram_*` tools.
- The OAuth configuration and MCP endpoint are unchanged. The tools and event need the vaultd release from clab-one/thegram-vault#26; rescan the MCP server on the plugin page after it is deployed.

## 2.0.9 — 2026-10-16

- The Claude manifest declares the directory listing fields: display name Thegram, the Thegram logo as its icon, and the support, privacy policy and terms URLs. This clears the directory validator's missing privacy policy warning. No MCP, OAuth, skill, server, credential or production setting is changed.

## 2.0.8 — 2026-10-16

- The OpenAI listing's AI access section, in English and Korean, now says "compatible AI assistants and coding agents" instead of naming ChatGPT and Claude. No MCP, OAuth, skill, server, credential or production setting is changed.

## 2.0.7 — 2026-10-16

- Rewrite the OpenAI and Claude listing around "Where your thoughts connect": everyday life, learning, hobbies and teamwork, not only projects. Refresh the English and Korean descriptions, capabilities, example prompts, keywords and Claude manifest descriptions.
- Describe web document editing, document/dashboard/graph views on the web, widget dashboards, semantic search with word fallback, revision history and per-agent access. Drop the outdated claim that Graph is desktop-only.
- Add the Claude Code marketplace install line to the README. No MCP, OAuth, skill, server, credential or production setting is changed.

## 2.0.6 — 2026-10-16

- Return to the single portable package used through 2.0.4: root `plugin.json` with the OpenAI listing, icons, review cases and publication notes, plus `mcp.json`, `.claude-plugin/` and `.mcp.json`. The OpenAI directory reads its listing from it again; the Claude directory is submitted from the repository's `.claude-plugin/plugin.json` root.
- Remove the `.app.json` binding; directory ZIP uploads must not include apps.
- Keep the 2.0.5 shared workflow: `skills/thegram-cloud/` is the pinned import of `thegram-mcp`'s `skills/thegram-memory/`, and builds reject drift.
- Coding agents continue to use `thegram-mcp` with scoped API keys. No server, OAuth scope, credential or production setting is changed.

## 2.0.5 — 2026-10-16 (withdrawn)

- Split the release into `thegram-chatgpt-2.0.5.zip` and `thegram-claude-2.0.5.zip`. Neither is a valid OpenAI directory upload: without the root `plugin.json` the listing metadata and icons are missing, and the ChatGPT ZIP includes `.app.json`, which directory ZIP uploads do not accept. Do not submit either.
- Imported the `thegram-mcp` 3.1 skill and references as the one workflow source with pinned file hashes.

## 2.0.4 — 2026-10-16

- A record of the wrong kind, such as a commit written as a task, is treated as a mistake rather than history: the skill reports it and, with the user's consent, keeps the fact as an `event` and removes the wrong record. Changing records to move a number stays forbidden.
- Tools, MCP/OAuth configuration, package identity and review cases are unchanged from 2.0.3.

## 2.0.3 — 2026-10-16

- Dashboard: the skill now says what the Project Tracker counts. Progress, open tasks and the task board count `task` records (cancelled/superseded stay in the total); goal rings count tasks linked `part-of` the goal; risks count by status; a metric chart needs repeated `value`/`observed` updates on one metric; revision history is recording time. Planned work is a `task` closed with `completed` + `done`; a commit, release or deploy is an `event`. Adding, splitting, relabelling or completing records to move a number is forbidden; a misleading number is reported instead.
- Body: a mention `[label](@id)` sits inside a sentence; body collections render in the document view, not on the dashboard.
- Tools, MCP/OAuth configuration, package identity and review cases are unchanged from 2.0.2.

## 2.0.2 — 2026-10-16

- Recording: when saving is authorized, the skill maps each kind of outcome to one linked record (accepted or replaced decision, shipped or verified event, caveat as risk or task, status change with `old`, metric observation) and reads the root project record before the first write. Nothing qualifying means nothing is written.
- Folders: Thegram Cloud vaults support folders (`gram_folder`, `gram_move`, `gram_list {}`), so the skill reuses a document wherever it sits, moves or creates folders only when asked, and never creates a second document because an expected path is empty. Contracts no longer claim only root vault documents are writable.
- Writes: `gram_create` accepts `request_id` and replays an identical create; Cloud `gram_patch` rejects `action`/`action_target` (`E_ARGUMENT`), so template requirements are met with ordinary operations and `E_ACTION` guidance is removed. `gram_relations` takes `from: {path, entity}`.
- Tools, MCP/OAuth configuration, package identity and review cases are unchanged from 2.0.1.

## 2.0.1 — 2026-10-14

- Thegram 2.0.1 shows one dashboard per document type: `project@1` Project Tracker, `schedule@1` Journal, `knowledge@1` Knowledge. The bundled skill, contracts and README now say so: pick one template for a new document with `gram_create {template}`; only a declared document is editable on its dashboard; a document without a template shows Core's recommended dashboard (`~project@1`) read-only, and the agent declares a template only when the user asks; an unknown template declaration has no dashboard. Wording that suggested several screens or boards per template is removed.
- Tools, MCP/OAuth configuration, package identity and review cases are unchanged from 2.0.0.

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
