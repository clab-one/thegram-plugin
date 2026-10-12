# Changelog

## Unreleased

- Add live agent-scope MCP E2E with a fresh Logto client, one-time-token cookie sign-in, CSRF-protected grant management, default-only visibility, hidden ungranted vaults, read/write enforcement, and immediate revocation with the same unexpired MCP token/session. Clean temporary vaults/documents and the Logto application; write credential-redacted JSON request/response evidence.
- Keep the ordinary MCP E2E on the default granted Thegram vault unless a pre-granted mount is specified; creating an arbitrary vault no longer implies agent write access.
- Explain per-agent scopes and Connected agents settings in README, package descriptions, reviewer expectations and bundled skill error guidance. Preserve five positive and three negative review cases and existing package identity/version/OAuth bindings.
- Record the unavailable MCP document-delete coverage explicitly: no deletion tool exists, and app API tokens do not exercise agent grants. Report the next endpoint’s production MCP audience as an isolation risk.

## 1.5.3 — 2026-10-12

- Clarify purpose-based .gram memory for people and AI: save only what the user asks to save, with source attribution and revision history; Cloud supports Document and Dashboard, with Graph in the desktop app. MCP/OAuth configuration is unchanged.
- Align deployed vault save-consent instructions and thegram-web install documentation with explicit user authorization.
- Provision and verify the synthetic `openai_review` account and Atlas fixture; configure and authorize the plugin in the OpenAI portal, verify the domain, and save reviewer credentials only in private Review details.
- Record five positive and three negative live cases in ChatGPT web. The sessions used a dev-mode custom `gram` MCP connection without the bundled skill; they do not establish bundled-skill behavior. The public-but-unlisted review page is https://thegram.one/review/openai/.
- Videos are being finalized in `evidence/review-video-20261012/`.

Owner maintenance: when Thegram requests updated terms acceptance, re-accept for `openai_review` (next expected: 2026-10-19). Before each review run, reset Atlas from `evidence/review-video-20261012/atlas-fixture.gram` and delete `northstar-website-refresh`.

No deployment, credential/access/scope change, or publication is performed by this package update.

## 1.5.2 — 2026-10-12

- Reposition the public plugin for people and AI working from shared, purpose-based .gram memory, with source-grounded history and relationships kept in one reusable file.
- Clarify the same records' document/dashboard/graph presentation and revision history in compatible apps: Cloud supports Document and Dashboard; Graph is available in the desktop app. Preserve connector-provided context only when saving is authorized, without implying direct Slack/Gmail fetching or indiscriminate capture.
- Synchronize package manifests at 1.5.2 and align the English/Korean listing, marketplace and skill description. Preserve thegram-cloud identity, C.Lab developer, Roy Kim author and existing MCP/OAuth configuration.
- Keep five positive and three negative scenarios; attribute the staging outcome to the user's report rather than independently verified evidence.

These package changes do not deploy the cloud server, change accounts/access/scopes/OAuth/credentials, or establish review submission or publication.

## 1.5.1 — 2026-10-12

- Align the OpenAI interface developer name with C.Lab and synchronize public package manifests at version 1.5.1; keep Roy Kim as package author.
- Finalize the five-positive/three-negative English review cases and proposed recording sequence; add explicit ISO 8601 UTC historical `gram_changes` guidance to the reviewer materials and bundled skill/contracts.
- Record that deployed consent/documentation alignment and subsequent reviewer setup, cases, and recording status are updated in 1.5.3.

No cloud server deployment, account/access/scope change, OAuth change, or credential change accompanies these metadata and documentation updates.

## 1.5.0 — 2026-10-11

- Replace broad connector capture instructions with the English durable project-memory lifecycle for dot and other cloud agents: current context, selective retrieval, authorized outcomes, readable purpose/state/reasons/evolution and unresolved work.
- Add source-grounded typed-record/relationship guidance, stable metric IDs, honest event/recording time, conflict/replay recovery, supported-view limits and fictional lifecycle payloads.
- Bundle the single thegram-cloud skill and its references through the portable release package and the existing private ChatGPT ZIP update route.
- Preserve private plugin identity, app bindings, connection settings, unknown metadata and unrelated skills during ZIP updates; validate discovery and reject unsafe archives.
- Add offline package/behavior validation and exact-commit CI. Keep cloud/local integration, storage verification, host installation and renderer verification distinct.

No cloud server deployment, access/scope change or credential change accompanied 1.5.0.
