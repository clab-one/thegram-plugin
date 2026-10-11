# Offline cloud gateway checks

Run with Go 1.26+ and a native Gram Core binary compatible with the inspected
cloud server source:

```sh
THEGRAM_VAULT_SOURCE=/path/to/thegram-vault \
GRAM_CORE_BINARY=/path/to/gram \
sh tests/offline/run.sh
```

`THEGRAM_LIFECYCLE_FIXTURE` optionally selects another lifecycle JSON fixture.
The default is the synthetic example bundled with this skill.

The runner copies only the cloud gateway and its standard-library support
packages into a temporary Go module. An in-package test supplies a fake
`Workspaces` implementation with synthetic mounts and temporary `.gram` files,
then executes the real gateway and native Core. Go module downloads are disabled.
No HTTP server or MCP session starts; no OAuth, provider connection, cloud account,
local Thegram app, or real mount is used. The scratch module/storage/cache are
removed on exit. The source checkout and binary are read, not modified.

Checks cover the fixture lifecycle and its selective retrieval calls; source and
relation readback; task completion and decision replacement; stable metric
history; exact-payload replay and changed-payload request-ID rejection; stale CAS
preservation and reconciliation; injected storage-conflict restoration; and the
required separation between `place` and body edits. Scope checks reject nested
vault writes, unknown mounts, and read-only writes. Successful cloud gateway
writes must return `sync.state = synced`.

The fake workspace tests the gateway's behavior when storage returns a conflict.
It does **not** validate the real provider's conditional-upload or rollback code.
These checks also do not prove live OAuth/sync, a released server's binary parity,
host installation/discovery, dashboard/sparkline visuals, or diagram rendering.
The fixture is fictional; a passing run does not establish real project facts.
