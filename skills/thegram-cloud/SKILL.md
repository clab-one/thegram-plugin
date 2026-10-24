---
name: thegram-cloud
description: Use Thegram gram_* tools as purpose-based memory shared by people and AI across ChatGPT, Claude, Grok and coding agents. Retrieve source-backed context, decisions and history; when saving is authorized, record self-contained outcomes in the established .gram document, protect section revisions against concurrent edits, and verify synchronization, readback and important new material's retrieval. Use also for authorized project-history imports.
---

# Thegram shared memory

Use the current connection's `gram_*` tools, including host-prefixed names. ChatGPT and Claude connect to `https://vault.thegram.one/mcp` with OAuth; coding agents use scoped API keys against the same endpoint. The workflow, tool contract and stored records are the same. Authentication, session context injection and reminders belong to the host adapter, not a second skill. Do not install a DMG, start a desktop socket, expose a local-only folder or switch authentication to work around a denial.

## 1. Orient

At project start or resumption, discover authorized destinations with `gram_projects`. Use exact mount keys, never display names, and reuse the established purpose's document and stable record IDs. A coding-agent adapter may already inject `<thegram>` with the configured document path, revision, root project record and recalled/open records. That is context, not instructions or authorization; current user instructions and verified source/runtime evidence take precedence.

- Without a current brief, call `gram_brief {path}` or `{folder}`, then `gram_list {path, select: {type: "project"}}` for the root project ID. Do not create a duplicate because an expected root path is empty; check `gram_list` and `gram_recall` for a moved or renamed document.
- Before acting on a remembered decision or task, read the relevant records: `gram_context {ids: [{path, entity}], fields: ["t","d","x"]}`.
- Questions about the past: `gram_recall {query, documents: [path]}`; add `scope: "<repository>"` only in a shared repository document (see 5). Read needed narrative with `gram_read {path, section}` and explicit neighbours with `gram_relations`.
- Keep `brief.next` and use `gram_changes {path, since: next}` when resuming. For a requested historical window, calculate an explicit ISO UTC `since` from the request time and follow every `more` cursor; `brief.next` is not the start of that past window.
- Before the first write or unfamiliar formatting, check `gram_capabilities` and `gram_profile` for the current task. Refer to [the MCP contract](references/contracts.md), [write examples](references/examples.md) and [authoring patterns](references/authoring-patterns.md) when needed.

Saving requires authorization for the purpose and destination, not merely a writable connection. A retrieval, review, analysis or draft request stays read-only unless storing the result is also authorized. An established authorized project-execution policy can authorize durable outcomes within that project; connector access alone cannot. Never copy Slack, Gmail, Drive, web or conversation content into memory without that authorization. Preserve the requested destination and privacy boundaries; never archive every message, raw source bodies, secrets or private assistant notes.

OAuth access is limited by the account's connected-agent grants; API-key access is further limited by that key's selected vaults/Drive accounts, permissions and lifetime. `gram_projects` lists the current agent's allowed mounts, not everything the person can see on the web. On `AGENT_SCOPE_DENIED`, stop and direct the person to Thegram Settings → Connected agents. Do not retry unchanged, change credentials or choose another destination. After the person changes scope, rediscover mounts and use fresh records before retrying.

## 2. What to record

Within an authorized purpose, keep one atomic fact per record and reuse existing identities. A commit, PR, report or chat is a source container, not a record type. One source may support several kinds of fact, or only source coverage.

### Classify before writing

1. Read the source body/diff and relevant follow-ups; separate choices, implementation, tracked work, observations and claims. Retain source identity, timestamp, scope and uncertainty for each fact.
2. Look up the existing fact/work/component/metric before adding anything. Update its fields and relations when the meaning is unchanged; repeated fixes do not create a new task lifecycle per commit.
3. Choose the type by meaning using the table below. Use only the current profile's fields, statuses and predicates. A merged implementation does not accept a proposed ADR, complete an entire task, or prove deployment or successful verification.
4. Add only relations the source establishes, in the stated direction. `A depends B` does not imply `B supports A`. For partial replacement, retain the still-applicable old decision and describe the changed scope with `related`; reserve `replaces` plus old `superseded` for full replacement.
5. Preserve source time separately from this write's runtime recording time. Reconcile current state and supported widget requirements, then submit the smallest sourced delta. No fact worth a record means no domain record; source coverage can still account for inspected material.

| Atomic meaning | Record/update | Section and relation | State boundary |
|---|---|---|---|
| a choice, proposed alternative or adopted policy | `decision` | Decisions; `part-of` project | `proposed` until a person accepts it, then `accepted`; `rejected`, or `superseded` when fully replaced |
| a desired outcome, required behavior or untested premise | `goal`, `requirement` or `assumption` respectively | Plan; `part-of` project/goal as sourced | do not infer these merely to fill a widget |
| tracked work or a sourced change to its progress | existing `task`, or add a genuinely sourced work item | Plan; `part-of` goal/project | partial → retain active work; review/unmerged PR → `review` when supported; `completed` only for the work's verified completion |
| architecture responsibility, interface or dependency | existing/new `component`, `system` or `service` | Architecture; `depends` in the sourced direction | code existence does not establish runtime health |
| possible harm versus an actual impediment | `risk` versus `blocker`; update affected task if sourced | Plan; `related` concern or blocker `blocks` task | `mitigated` while the harm is reduced but still possible, `resolved` once it is gone; do not invent priority, owner or due date |
| observation, test or report supporting/contradicting a claim | `evidence` | Log; `supports` or `contradicts` the claim | failed verification is evidence of failure; a source report is not this agent's runtime verification |
| reusable explanation or constraint | `knowledge` (or `context` for situational background) | relevant existing section; `part-of` project | preserve scope and uncertainty |
| a comparable measured quantity | same `metric` ID; `set value` + `set observed` | relevant section; retain report via `source`/`ref` | same definition, denominator and unit; one observation is valid |
| an identifiable build, report or deliverable | `artifact` with `ref` | Log; `derives` only from an actual producing record | publishing an artifact alone does not require an event |
| a meaningful dated occurrence, incident, verified rollout or milestone | `event` with sourced `at` and `ref`/`source` | Log; `implements` only a demonstrated choice, else `part-of` project | no event per commit or push; a tracked task's PR, merge, release, deployment or verification is one step event `part-of` that task (Agent work in 5); no guessed deployment or milestone |
| provenance or inspected low-signal material | reusable `source` or coverage note | cite near supported facts | routine image pins/formatting may need coverage only, with no event/task/evidence |

A factual outcome can update a task and component, explain a decision, and retain verification evidence from one commit. Do not fabricate completed historical tasks, intermediate statuses, events or revisions from its subject. Do not record chatter, raw logs, secrets, private assistant notes or every transient experiment. See [worked classification cases](references/examples.md) for ambiguous inputs.

An event's `at` is the actual occurrence time: a commit author date proves the commit time only, not a deployment time. Record source timestamps at their known precision in source descriptions or profile-supported source fields; do not force a decision or component onto a calendar with an invented `at`. Keep date-only facts date-only. `ref` is one URI others can open: a source permalink, release/PR URL or commit URL built from its actual remote. Never put a `file://` URL or a local path in `ref`; a local report stays in `d` with its path and hash, and without a remote retain the commit hash in provenance. Put a real source record ID, not a URL, in `source`.

## 3. One turn, one patch

After classification, write the whole outcome of a turn as one `gram_patch` against the head. Operations run in order, so later ones can link to records added earlier.

This example assumes a sourced full replacement and a retained passing check; it does not claim a release or deployment. Both closed records get a `d` that says how they ended.

```json
{"path": "@mounts/<vault-id>/<project>.gram", "request_id": "slugify-unicode",
 "operations": [
  {"op": "add", "record": {"type": "decision", "id": "dec-unicode-slugs",
    "fields": {"t": ["Keep Unicode letters in slugs"], "d": ["slugify keeps letters and digits of every script and joins the rest with one hyphen."], "x": ["accepted"]},
    "links": [["part-of", "prj-strings"], ["replaces", "dec-ascii-slugs"]]}, "place": {"section": "Decisions"}},
  {"op": "set", "entity": "dec-ascii-slugs", "key": "x", "value": "superseded", "old": "accepted"},
  {"op": "set", "entity": "dec-ascii-slugs", "key": "d", "value": "Replaced by keeping Unicode letters; slugs used to drop every non-ASCII character.", "old": "Slugs keep only ASCII letters and digits."},
  {"op": "add", "record": {"type": "evidence", "id": "evd-unicode-slugs",
    "fields": {"t": ["Unicode regression check"], "d": ["The retained local test report confirms '카페 Latte' maps to '카페-latte'."], "ref": ["https://example.com/reports/unicode-regression"]},
    "links": [["supports", "dec-unicode-slugs"]]}, "place": {"section": "Log"}},
  {"op": "set", "entity": "risk-ascii-only", "key": "x", "value": "resolved", "old": "open"},
  {"op": "set", "entity": "risk-ascii-only", "key": "d", "value": "Resolved: Korean titles now keep their letters in slugs, as the regression check shows.", "old": "Korean titles turn into empty slugs."},
  {"op": "link", "entity": "risk-ascii-only", "predicate": "related", "target": "evd-unicode-slugs"},
  {"op": "add", "record": {"type": "task", "id": "task-slug-length",
    "fields": {"t": ["Cap slug length"], "d": ["Very long titles still produce unbounded slugs."], "x": ["open"]},
    "links": [["part-of", "prj-strings"], ["related", "dec-unicode-slugs"]]}, "place": {"section": "Plan"}}
 ]}
```

- Every field value in `add` is an array; `set` takes `value` (or `values`) and `old`, exactly what you read (`null` when empty).
- Array syntax does not make a singular field repeatable: `t`, `d`, `x`, `at` and `ref` keep one value unless the current profile says otherwise. `tag`, `s` and `source` may repeat. Keep source attribution near the supported claim.
- `t` is a concise title naming the subject and claim, never a time or id. `d` is a short, self-contained explanation: keep the subject, applicable scope, essential conditions and exceptions needed to understand this record outside its document. Prefer completeness over a one-sentence limit; retain uncertainty and provenance without copying the whole source. Use the person's/source's natural terms, not keyword lists, invented synonyms or unsupported detail.
- Ids are short slugs with a type prefix (`dec-`, `ev-`, `task-`, `risk-`, `art-`, `evd-`, `m-`), no dates.
- `place` is `{"section": "<heading>"}`, `{"after": "<id>"}` or `"end"`. A record without `place` is not in the body.
- A write landed only when the answer shows `sync.state: synced`. The final answer names the records (`path#id`, revision).

## 4. Status values

Every document follows one record vocabulary (`gram@1`); there is no template to choose. Each status belongs to one class, and the dashboard, `gram_brief`, `gram_recall {status}` and the graph all count by it: `open` still needs attention, `done` ended as intended, `closed` is no longer pursued. Check `gram_profile {topic: "templates"}` when unsure.

| type | open | done | closed |
|---|---|---|---|
| task | `backlog` `open` `active` `review` `blocked` `waiting` | `completed` | `cancelled` `archived` |
| goal | `open` `active` | `completed` | `cancelled` `archived` |
| project | `planning` `active` `at-risk` `on-hold` | `completed` | `cancelled` `archived` |
| decision | `proposed` | `accepted` | `rejected` `superseded` |
| risk | `open` `mitigated` | `resolved` | `accepted` `closed` |
| event | `confirmed` `tentative` | — | `cancelled` |
| blocker | `open` (no fixed list) | `completed` `resolved` | `closed` `cancelled` |

Task, goal, project, decision and risk need `x`; an event needs `at`, a metric `value` and `unit`, an artifact `ref`. Other optional fields: `p` (`urgent` `high` `medium` `low`), `owner`, `tag`, `due` (task, ISO date), `start` and `done` (task: when work began and finished). Unknown keys warn `W_EXTENSION_FIELD`.

Closing a record:

- When a status moves to `done` or `closed`, rewrite `d` in the same patch to say how it ended (what replaced it, how the harm went away). Keep the old situation as a clause when it helps; the revision history keeps the earlier text. Thegram marks a description that was written before the status change.
- Link the evidence or event that resolved a risk or blocker with `related`. `supports`/`contradicts` argue for or against a claim (a decision, requirement or knowledge), not that a risk is gone.
- `mitigated` stays open. Do not mark a risk `resolved` or a decision `accepted` without a source that says so; a merged change does not accept a proposal.
- Before changing a state, look for the same fact in the purpose's other documents (`gram_recall {query, folder}`, or each document's brief) and reconcile them in the same turn, one patch per document.

## 5. Documents

- A purpose can be a plan, research topic, shared project or everyday work, not only a Git repository. Reuse its established document and readable structure. An existing project document has Overview, Architecture, Plan, Decisions and Log; keep the overview, sources, decisions, evolution and unresolved work understandable without rebuilding context.
- Create a document only when authorized: one `gram_create` with `base_revision: null`, a short descriptive title, a body with the purpose's sections, a root purpose/project record and the first sourced records. Preserve the exact authorized mount, folder and path. Use an existing writable Cloud destination; use Drive only when requested. Create folders or move documents only when asked.
- For coding repositories, the adapter resolves the document afresh by the exact `repo:<host>/<repository-path>` tag on an existing project record, searching currently authorized Vault documents and all result pages. Exactly one project record must match, including within a shared document; missing or duplicate matches stop rather than guessing, creating a substitute or issuing a write reminder. Git worktrees sharing an origin resolve to the same repository identity.
- To associate an existing project, use the host adapter's explicit bind command to add that exact repo tag server-side. Local `projects.json` mappings and fallback document paths are not project bindings. A repository without an origin needs an explicitly supplied exact repository identity; a non-Git directory has no inferred repository binding.
- Every document uses the same record types and statuses; shape it by its sections and records. Schedules use an event per occurrence and a completion time in `done`.
- Each document has one dashboard, editable by anyone who can write. Its view follows the records (Project Tracker, Journal, Knowledge, Operations; a document with `run` events opens on the automation widgets), and a person can apply a dashboard starter in the app. An older document's `template` line only hints the view; leave it.
- Link only within the document. For a record in another document, cite its URL in `ref` (cross-document targets stay unresolved).

### Scheduled automations

A document a scheduled run writes (a research digest, a monitor, a collected log) has one shape, and the 리서치, 감시·알림 and 수집 일지 dashboards read exactly it. Write each run as one patch:

1. Read what earlier runs left (`gram_list {path, select: {type}}`, `gram_recall` by URL or title). An item already recorded (same URL, release, notice or message) is not added again: `set` only the fields that changed on the existing record and leave its links alone, so it keeps pointing at the run that first found it.
2. Add one run record: `event`, `t` such as "리서치 실행", `at` the actual run time with its zone, `x` `confirmed`, `tag` `run` plus `failed:<source>` for every source that could not be read, `d` saying what was checked and how many new items, `part-of` the project. A run that finds nothing still records itself.
3. Each new item: `knowledge` for a news item, post or finding; `event` for something that happened or is scheduled (`at`, and `end` when the source gives one). Give it `ref` (the original URL), `at` (when it was published or happens; leave it out when the source gives no time), `tag` `source:<name>` (`news`, `hn`, `github`, `reddit`, `gmail`, `slack`, `calendar`, …) and `topic:<slug>` (one slug per story, the same on every source that covers it), link `derives` to this run only, and place it. Its ID comes from the item (`k-hn-41234567`, `ev-sui-testnet-v1-82-1`), never from the run time.
4. Each watched thing (a chain, server, repository or mailbox) is one record tagged `target`, created once and reused; every detection links `related` to its target.
5. What needs a person follows the automation's own rule in the root project's `d`. A change still ahead that someone must act on (an upgrade to apply, a price change to review) becomes a `task` due by its start; a possible harm nobody here can act on (a reboot during a provider's maintenance) is a `risk`, with `p` only when stated. A task is never created already overdue. Link either `related` to its item. Status belongs in `x` and dates, never in a title (`[완료]`, `[과거]`).
6. The schedule itself (cadence, sources, scope) is the root project's `d`; the dashboard reads the cadence from the runs, so never invent a run that did not happen.

### Agent work

When an agent works for the person (code, a release, an investigation), the AI 작업 보드 dashboard shows who is doing what and how it went from exactly these records:

1. One `task` per piece of work, added when the work starts or reused when it continues (find it by title, `ref` or repository with `gram_recall`). `t` names the work, not a step; `owner` is your agent name as the person knows it (`Codex`, `Claude Code`, `OMP`, `ChatGPT`); `s` the repository; `start` when you began; `part-of` the project or goal. Never a task per commit or per session.
2. Move `x` with the work, in the same patch as the step that moved it: `active` while you work; `review` when the result waits for the person's review or approval (`d` says what to look at); `waiting` when you need the person's answer (`d` asks the question; a choice between options is also a `proposed` decision linked `related`); `blocked` when something else stops it (`d` says what); `completed` with `done` the finish time and `d` rewritten to the outcome; `cancelled` with the reason. Before you stop, never leave your task `active`: set what it actually waits for.
3. Each meaningful step is one `event` linked `part-of` the task: a PR opened for review, merged, a release, a deployment, a verification, or a plan the person agreed to. `at` is when it happened and `ref` the PR, commit, release or run URL. No event per commit, push or test run, and none for a step that did not happen.
4. A choice settled along the way is a decision (rules above); the step that carries it out may also link `implements` it.

### Long documents

An architecture document, spec, design review, report or manual is written in steps, never in one call:

1. Plan the outline: `#` title, `##` sections, `###` subsections. Headings are unique, so each section can be found again.
2. `gram_create` with the title heading and a short overview only.
3. One `gram_patch` per `##` section: `{"op":"section","heading":"## 3. Storage","text":"<Markdown under the heading, its ### subsections included>"}`. A missing section is added at the end; an existing one is replaced up to the next `##`. Keep each call under about 8,000 characters; split a bigger section into `###` sections written one per call.
4. Records the section explains (components, decisions, risks) go in the same patch: `add` with `"place":"none"`, and their `[[id]]` lines inside `text`.
5. Before replacing an existing section, read it with `gram_read {path, section:"3. Storage", source:true}` and retain that response's `doc.rev` and `doc.hash` with the text. Follow every `more` cursor to finish the same snapshot; on a stale cursor, restart the read. The stored Markdown preserves headings, tables, list markers, `[label](@id)` mentions and `[[id]]` lines. Edit it and send `gram_patch {path, request_id, base_revision:<that doc.rev>, expected_hash:<that doc.hash>, operations:[{op:"section",heading:"## 3. Storage",text:<edited text>}]}`. Never pair old text with tokens from a later brief or write receipt, omit the preconditions to force a write, or resend the plain read's rendered HTML. A one-sentence fix is an `edit-text`.
6. On a revision/hash conflict, reread the section and reconcile the intended change with the intervening edits; if they conflict in meaning, ask the person rather than choosing an overwrite. Submit the reconciled payload with the new read's tokens and a new `request_id`. For other errors, fix the named cause; sections already written stay. `E_NO_CHANGE` means the section already reads that way, not that another write succeeded.

Use headings, short paragraphs (three to six sentences), lists, tables, code blocks and `flowchart` diagrams; a paragraph is never a container for a list of facts.

## 6. Body and dashboard

Prose is for people reading the document now. History lives in records.

- A status or overview paragraph states only the current state in a few sentences. When the state changes, rewrite that paragraph; never append the latest change to it. Growing an existing paragraph past 1,000 characters is refused (`E_LONG_PARAGRAPH`).
- Each meaningful change (a release, deployment, decision, incident) is one dated `event` (or the right record type) placed in Log, with `ref` to the PR, release or run. Prose may mention it with `[label](@id)`.
- No lists of PR numbers, commit hashes, image digests or clock times in prose. One event per meaningful step, not one per PR or commit; group a batch of merged PRs into the one release or deployment they shipped in.
- A recurring writer (a scheduled run, a session hook) updates the same records and the same status paragraph each time; it never grows a running log in the body.

- `[[id]]` alone on a line places a record; never place a record twice. `[label](@id)` mentions a record inside a sentence: the label is the words a reader needs there (`[the two remotes](@ctx-histories) share no ancestor`). Never append a bare mention after a finished sentence or table cell; it reads as a cut-off phrase. Mention instead of copying numbers.
- `[[*]]{type=risk status=open view=list}` shows matching records live as cards in the document view (not on the dashboard) without placing them; `view` is `list` or `table`.
- Callouts: `> [!note]` (or `tip`, `important`, `warning`, `caution`) followed by `> ` lines. Tables need a `|---|` row and equal cells.
- Prose changes use `{"op":"edit-text","entity":"doc","kind":"rich","old":"<exact text, once>","new":"…"}`; it cannot share a patch with `place`, so add records first, then edit text in the next patch. Copy `old` from `gram_read` with `source:true`, which keeps the stored `[label](@id)` syntax; the plain read flattens mentions to their labels. To rewrite a whole section use `section` (Long documents above).
- Mermaid: only `flowchart`/`graph`; label only `-->` edges.
- For saved widgets, read [widget data contracts](references/widget-data.md) and, when exposed, `gram_profile {path, topic:"presentation"}`. Preserve the saved layout and report missing data or unavailable capabilities; never invent records, owners or dates to make a widget ready.
- Metrics: one `metric` record per quantity (`value` a plain number, constant `unit`, `observed` a past ISO time with zone). Each new measurement is `set value` + `set observed` on that record, never a new record.
- `d` on `doc` is the document summary; `set doc view dashboard` opens it on the dashboard.

## 7. What the dashboard counts

Widgets select stored records, their template states, relationships and real history; they do not turn commit prose into progress. Never add, split, relabel or complete records to move a number. With the person's consent, correct a misclassified record to the type its facts support (which may be a task update, decision, component, evidence, artifact, event or coverage only). Preserve useful content and provenance; removals require fresh CAS. Do not force every wrongly recorded commit into an event.

| Surface | Data needed | Authoring consequence |
|---|---|---|
| Task board/checklist and progress rings | selected tasks and their status class | track real work; update existing tasks from completion evidence; do not manufacture historical tasks |
| Goal progress | tasks with `part-of` that goal | `related` does not count; a goal with no linked tasks can remain without a ratio |
| Decisions/pending choices | decision `x`; full replacement `replaces` links | proposed stays proposed despite merged code; acceptance is distinct from implementation |
| Risk/attention | actual risks/blockers, explicit states and sourced priority | an empty attention list does not prove health |
| Calendar/timeline | event `at`, metric `observed`, other records' supported `due` | omit unknown dates; a source commit date is not every fact's occurrence date |
| Metric trend | same ID, numeric `value`, same `unit`, sourced `observed` and available history | retain real observations; never create revisions just to draw a line |
| Activity/revision history | actual runtime recording time and loaded revision history | imports remain recorded today; no fake commit-era activity |
| Automation (new items, runs, sources, watched targets) | `run` events; items with `derives` to their run, `ref`, `at`, `source:`/`topic:` tags; `target` records and `related` detections | one run record per real run; reuse items and targets; see Scheduled automations in 5 |
| Sync/team/presence/workspace | runtime/capability data | document records cannot fabricate live sync, membership, presence or access |

The inspected newer widget model counts completion as done ÷ (open + done), excluding closed and unknown states; older Core tracker summaries can use all-task totals. Check the target's current contract and selected records before explaining a percentage. Details, version limits and offline selector checks are in [widget-data.md](references/widget-data.md).

## 8. Read

- `gram_read {path}` outline; `{path, section}` one section as lines (title, type, id, x, dates, `d`).
- `gram_list {path, select: {type, status}}` filters; `gram_context {ids: [{path, entity}]}` reads one or many records.
- `gram_relations {from: {path, entity}}` lists edges both ways.
- `gram_changes {path, since}` (or `since_revision`) lists later revisions and what they changed; past state via `revision`, `effective_at` or `recorded_at` on `gram_read`, `gram_list {path}` and each `gram_context` item.
- Some read views display a decision using its earliest implementing event date. That is an implementation date, not its acceptance date; leave it absent when no such event exists and retain documentary dates in provenance.
- Recall: ask in a plain sentence with the default `mode` (`auto` ranks by meaning and by any matching words together). `keyword` needs every word in the record and `exact` takes one record id, so use them only for a known phrase or id. Date filters `from`/`to` (inclusive; `YYYY-MM` covers the month). `duplicates` counts repeated hits left out. Retry once with other wording before concluding nothing is recorded.

## 9. Reminders and the stop check

Coding-agent adapters can remind after file edits, commits or releases and can request one continuation when finishing. Cloud chat hosts need not expose those hooks. The reminder does not authorize a write or alter this workflow. Finish authorized work, report the result and reconcile relevant tasks as completed, blocked or superseded according to evidence; record only a qualifying outcome or explain why nothing was saved. Do not invent a background continuation, write filler to silence a hook, or make the user wait for unrelated memory work.

### Verify important material can be found

After creating a document, adding a substantial knowledge set or materially changing an important decision/policy, verify retrieval as well as storage; skip this for routine small field edits.

1. Choose one or two representative questions a person would naturally ask later, based on the source's subject and conditions, not a copied title or record ID. Use `gram_recall` with default `auto` in the authorized collection/folder where the material should be found, not `exact` or an ID lookup.
2. Open the returned record with `gram_context` or the suggested section with `gram_read`. Check that it actually answers the question with the right subject, scope and conditions. A matching title, high score or section hint alone is not proof; if the section is wrong, use the outline to inspect the actual answer and report the hint failure.
3. If it is not found, inspect the written record and source. Within the authorized write, clarify only missing source-backed subject/conditions in `t`/`d` or the relevant section, without keyword stuffing, invented facts or duplicate records. Retry once with another natural wording. If it still fails, or indexing/model availability limits the check, report "saved and read back; retrieval not verified" with the question and observed limitation. Do not keep rewriting to chase rank or claim future retrieval is guaranteed.

Report storage/readback and retrieval separately, naming the question and `path#id` or section actually checked; do not claim semantic search was verified when the response used keyword fallback.

## 10. Errors

| code | cause → fix |
|---|---|
| `E_PRECONDITION` | a field you read changed, the id exists with other content, or a `place` target is gone (`details.conditions`) → reread, decide, resend with a new `request_id` |
| `E_TEMPLATE` | the write breaks the record vocabulary (a required field is missing, or the type has no such status); `details.diagnostics` names record, field, expected → fix them |
| `STALE_REVISION`, `HASH_MISMATCH`, `E_CAS_REQUIRED` | document changed or a replacement lacks preconditions → reread the section/source, reconcile concurrent edits, and resend with that read's `doc.rev`/`doc.hash` and a new request ID; never attach a later brief's tokens to an old draft |
| `E_ARGUMENT` | value not an array, `set` without `old`, `place` with a body edit, unknown section or argument shape |
| `E_FIELD`, `E_LINK`, `E_TIME`, `E_MISSING_TITLE` | bad field key, unknown predicate, `effective_at` without time or zone, no `t` |
| `E_MISSING_TARGET`, `E_MISSING_SOURCE` | link target not added yet; `source` names a non-`source` record → add it first, or cite with `ref` |
| `E_AMBIGUOUS_TEXT` | `edit-text` `old` not found exactly once → copy from `gram_read`, widen it |
| `E_LONG_PARAGRAPH` | your change grew an existing paragraph past 1,000 characters (`details.starts` shows which) → rewrite it as the current state in a few sentences, put new detail in its own paragraph or section, and move history into dated event records |
| `E_DUPLICATE_ID` | id exists → `set` that record or pick another id |
| `E_REQUEST_REUSE` | `request_id` already used for a different request → new id |
| `AGENT_SCOPE_DENIED`, `E_READ_ONLY`, `E_PATH` | the key, membership or policy denies it, or the path is invalid → report it; never switch to another mount or the desktop app |

One `request_id` per exact intended change. After a lost answer, reconcile the outcome and retry the identical request with its original ID; a landed write replays its receipt (`replayed:true`). On `E_PRECONDITION`, reread the affected fields, preserve concurrent edits and use a new request ID for a revised intent. Confirm `sync.state:synced` and fresh readback of changed prose, fields, statuses, links and revision before reporting saved; report storage and actual UI rendering separately. Only the main agent writes; subagents can supply candidates only when the user permits delegation. Never remove records that were true; change their status. Correct a wrongly classified record only with the person's consent.

## 11. Backfill

To build memory from project history, follow [backfill.md](backfill.md).
