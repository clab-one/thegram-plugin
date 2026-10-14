# Current cloud MCP contract

This reference describes the inspected cloud contract, not an installation or permission grant. The current connection's schemas, `gram_capabilities` and `gram_profile` win when versions differ.

## Connection and storage

The cloud package uses Streamable HTTP at `https://vault.thegram.one/mcp` with OAuth. `gram_projects` returns `mounts` with `{key,id,kind,name,count,access}`. Use `key` as the path prefix. Vault and Drive mounts both support folder paths; a write to a nested path creates the missing folders in the vault or in Google Drive. Never substitute a display name for a key or fall back to another mount after denial/conflict.

The server may create a default vault when an account has no writable vault during discovery; discovery does not authorize the agent to create memory records or capture other sources. `CONSENT_REQUIRED` and `PROVIDER_AUTH_REQUIRED` require the user's sign-up/reconnection flow. Preserve the requested storage destination.

The separate `clab-one/thegram-mcp` package (`thegram-memory`) is a Node integration for the running Mac app (hooks, a local Unix-socket MCP proxy, repository-name folders and an injected brief); those are not cloud features. Local folder writes may have no `sync`; cloud successful writes report `sync.state: synced`. Cloud semantic search uses the desktop model and ranking; rendering features do not transfer to cloud.

## Selective reads

| Tool | Arguments and result to use |
| --- | --- |
| `gram_brief` | `{path}` or `{folder}`; `docs` rows are path/title/rev/hash/recorded/effective, then the template (`project@1` declared, `~project@1` Core's recommendation for an undeclared document, whose dashboard is read-only), plus open work and `next`. |
| `gram_changes` | `{path or folder, since}`; exclusive recording-time cursor. A requested historical window starts at an explicit ISO 8601 UTC `since` computed from the request time, not `gram_brief.next`; follow each `more`. One document also takes `since_revision`. |
| `gram_recall` | `{query, folder, mode?, type?, from?, to?, date?, top_k?, cursor?}`; `path#id` hits and document section hits. `scope` is exact `s` tag membership, not section/type. |
| `gram_context` | `{ids:[{path,entity}], fields:[...]}`; selected fields, links and bounded rich text. Request `observed` explicitly for metric dates; the default field set omits it. |
| `gram_read` | `{path}` gives outline; `{path,section}` gives one section's Markdown. Use outline heading/node IDs for ambiguous section names. |
| `gram_list` | `{path,select:{type?,status?,tag?,from?,to?,date?}}` selects current records (ignoring historical selectors); without `select` document rows end with the template mark and `folders` lists every folder in scope, empty ones too. `{path,trash:true}` lists the trash as `[original path, kind, id, trashed_at, explicit]`. |
| `gram_relations` | `{from:{path,entity}, direction?, predicates?, depth?, paths?, limit?, cursor?}`; explicit edges, not relations inferred from prose. |
| `gram_range` | `{path,query?,start?,limit?}`; relevant revisions, or sequential history with `start:0`; pass `more` as the next start. |
| `gram_state` | `{path,selector:{revision}}`, `{path,selector:{recorded_at}}` or `{path,selector:{effective_at}}`; choose one selector. |

Date filters are inclusive; date-only `to` covers the whole day, and `YYYY-MM`/`YYYY` represent a span. Default record date: event `at`, metric `observed`, task `due`, otherwise `at`. `date` chooses another field. `auto` fuses keyword and semantic ranks; `gram_capabilities.semantic` reports whether the model is available and `index` how many documents are indexed. A recall that returns `mode`/`reason` used keyword matching for that call. Follow pagination and report incomplete coverage.

Historical selectors also work on `gram_read`, `gram_get`, `gram_list` without `select`, and in each `gram_context.ids[]` item. Such answers keep the current revision/hash and put the selected history under `at`; do not mistake a past projection for the current state.

`effective_at` selection walks revision order, uses `recorded_at` where effective time is absent, and stops when the next applicable timestamp exceeds the selected time. It is not a general merge of arbitrarily reordered historical facts. Prefer explicit revisions/recording-time queries for audit, and verify any authorized historical-state change at the affected dates.

## Structured writes

`gram_create` requires `{path,title,base_revision:null}` and `content` (text or `{text|rich,records,fields,blocks}`) unless `template` (`schedule@1`, `project@1`, `knowledge@1`) starts the body from its own headings. A template declares the document: Core then checks its records against `gram_profile {topic:"templates"}` and refuses violations with `E_TEMPLATE` and `details.diagnostics`. It has **no `request_id`**. If its answer is lost, inspect the destination before retrying; do not create a similarly named duplicate. An already existing path is not an overwrite route.

`gram_patch` requires `{path,request_id,operations}`; request ID is 1–128 characters and operations are nonempty. Without `base_revision`/`expected_hash` it writes to the head: each set/unset carries `old`, the value read (string, array in order, or `null`), and Core refuses with `E_PRECONDITION` and `details.conditions` only when such a field changed, an added ID exists with other content or a place target is gone. With a nonnegative `base_revision` and the opaque 16-hex `expected_hash` the whole document must be unchanged; `remove` and whole-body `text`/`drop-text`/`rich` need them. `action`/`action_target` name a template action, whose listed operations and fields must match exactly (`E_ACTION`; without `action` the same change is still checked against the template). One successful call is one real revision.

| Operation | Shape |
| --- | --- |
| add | `{op:"add",record:{type,id,fields:{t:["Title"],d:["Outcome."]},links:[["part-of","prj-atlas"]]},place:{section:"Plan"}}` |
| set | `{op:"set",entity:"task-verify",key:"x",value:"completed",old:"active"}`; several values `values:["a","b"]` |
| link / unlink | `{op:"link",entity:"dec-new",predicate:"replaces",target:"dec-old"}` |
| edit-text | `{op:"edit-text",entity:"doc",kind:"rich",old:"exact unique text",new:"replacement"}` |

Add field values are arrays of strings; a set takes `value` (one string) or `values`. `t` is required and single-line. Current types: `project goal requirement assumption decision task blocker risk event artifact evidence metric component system service source history knowledge context person agent run asset`. Known predicates: `part-of implements depends derives related supports contradicts replaces blocks enables`. Unsupported add predicates can be stored without appearing in relation reads; do not use them as graph links. Valid extension fields may be stored with `W_EXTENSION_FIELD`, but prefer profile fields. Unknown record types fail. A template document accepts only its listed `x` values and required fields.

`source` refers to a real `source` record ID, not a URL. Put URLs in `ref`. Preserve sourced owners/deadlines and omit unknown ones. Raw `x` accepts strings; misspellings can appear as open work. Missing `x` can omit a task/risk from the open brief, so compare both brief and selected records.

`place` belongs on an add and supports `"end"`, `{after:"id"}` or `{section:"exact heading or node ID"}`. It requires a rich document body and cannot share a patch with `edit-text`, `rich`, `text` or `drop-text`. A record without placement can exist without being visible in the body. Operations run in order; add a target before linking to it in a patch. In create content, records may link to each other regardless of order; place them with standalone `[[id]]` lines or appropriate collections.

## Files and folders

Use these only when the user asks to organize, delete or restore.

| Tool | Arguments and result |
| --- | --- |
| `gram_folder` | `{path}` creates the folder and missing parents; returns `{folder, created}`. An existing folder returns `created:false`. |
| `gram_move` | `{path, to}` renames and/or moves one document or folder inside the same mount; missing destination folders are created; returns the new `path`. Doc history, record IDs and links stay. |
| `gram_delete` | `{path}` moves one document or folder (with contents) to the mount's trash; returns `{trashed, kind, id}`. A changed document fails with `STORAGE_CONFLICT`: read it again first. |
| `gram_restore` | `{path}` with the original path, or `{path: <mount key>, id}` from the trash listing. A folder restores everything trashed with it; a missing parent restores into the root and a name clash gets a `(1)` suffix, so report the returned `restored` path. |

`E_NAME_CONFLICT` means the destination already holds that name; `E_INVALID_MOVE` a folder moved into itself or the root; `E_AMBIGUOUS` several trashed items share the path (pass one of `details.candidates` as `id`); `E_PRUNED` the trashed version is no longer retained. Moving between mounts is not supported.

## Recovery and completion

1. Retain the exact patch payload and response. If the response is lost, inspect the document and retry the **identical** request with the same ID. The receipt may report `replayed:true`; there is no public `gram_receipt` tool.
2. `E_PRECONDITION`, `STALE_REVISION`, stale hash or `STORAGE_CONFLICT`: refresh the affected prose/records; preserve concurrent edits, check whether the intent remains needed and rebuild with a new request ID. Do not retry an old write blindly. Fix `E_TEMPLATE`/`E_ACTION` by `details.diagnostics`; `E_CAS_REQUIRED` means the operation needs `base_revision`/`expected_hash`.
3. `E_REQUEST_REUSE` means the same ID was used for a different request. Use a new ID only after reconciling the actual outcome. A rare replay can return `intent_checked:false`; readback is required even when a receipt is successful.
4. Resolve `E_AMBIGUOUS_TEXT` by reading the exact text and selecting a unique span. Resolve missing/duplicate IDs by reusing the existing record or correcting the target, never by repeated imports.
5. Confirm `sync.state = synced`, then read the changed sections, selected fields and relations freshly. Check selected historical states if changed. A replay can report the document's newer current revision; verify the intended fields, not merely a revision number.

`AGENT_SCOPE_DENIED` identifies per-agent access denial and points to https://vault.thegram.one/settings/agents. Stop the operation, report the denial and let the user change access in Settings → Connected agents; do not retry unchanged, change credentials or redirect to another mount. After an approved scope change, rediscover mounts and fetch fresh revision/hash before an authorized retry. None mounts are hidden; read mounts are read-only. `E_FORBIDDEN` identifies other cloud access denials; local integrations may instead expose `E_READ_ONLY`. `E_PATH`, missing targets/sources, bad field types or bad timestamps require correcting the request within its original scope. Provider authentication, consent, quota or uncertain storage outcome remains a blocker; do not bypass it with another destination.

`at` accepts an event's known ISO date/time; task `due` can be date-only. Metric `observed` should retain the source's known precision. A timezone-bearing observation gives a supporting chart an actual time axis. `effective_at`, when deliberately used, requires a full ISO timestamp with a zone. Recording time is supplied by the runtime; never manufacture it.

## Supported representations

Standalone `[[id]]` places a record. `[label](@id)` mentions a record. A field mention can be built with a rich text mark `{type:"mention",ref:"met-availability",field:"value"}` according to `gram_profile {task:"rich"}`; the mark's text should fit the sentence.

Collection examples supported by the current rich profile:

```text
[[*]]{type=risk status=open view=table}
[[*]]{type=task status=active view=list}
```

Only collection `list` and `table` are listed as supported; item `view` is ignored. Each document has one dashboard, chosen by Core from its template: declared `project@1` Project Tracker, `schedule@1` Journal and `knowledge@1` Knowledge are editable there; an undeclared document shows its recommended type's dashboard read-only; an unknown template declaration has no dashboard. `set doc view dashboard` opens the document on that dashboard in supporting apps. Desktop metric series use the stable metric entity's numeric `value`, `unit` and `observed` history; use plain `-?digits[.digits]`, no comma, unit or percent sign in `value`. Changed units separate the series. Desktop goal progress counts same-document tasks linked to a goal, excluding superseded tasks; use meaningful `part-of` goal links, not decorative links.

Mermaid `flowchart`/`graph` blocks are supported by the inspected desktop renderer; other diagram kinds remain source. Labeled `-->` edges are supported there, while labeled `==>`/`-.->` can be dropped. Cloud storage accepting a code block does not prove a particular host renders it. Validate the target renderer and retain readable prose when rendering is unavailable.
