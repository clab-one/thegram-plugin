#!/usr/bin/env python3
"""End-to-end check of the remote Thegram MCP endpoint as a cloud agent uses it.

Usage:
  THEGRAM_SERVER=https://vault.thegram.one [THEGRAM_MOUNT=google-drive-<account>] \
  [THEGRAM_OAUTH_CLIENT_ID=<Logto app with a loopback redirect; default: the server's desktop client>] \
  [THEGRAM_OAUTH_STORE=<refresh token file; default ~/.config/thegram-e2e/<host>.json>] \
  [THEGRAM_OTHER_TOKEN=<MCP access token of a second account without access to the mount>] \
  python3 tests/e2e/mcp_e2e.py <evidence-dir>

Discovers OAuth from the endpoint's 401 like an MCP client, signs in once in a browser (later runs refresh),
creates one scratch document in the mount, exercises the tools on it, checks the stored file through the
vault or Drive API, deletes it there, and writes <evidence-dir>/mcp-e2e-report.json. Exits non-zero when any step fails.
Without THEGRAM_MOUNT it creates a vault named mcp-e2e-<UTC time>, runs there and always deletes that vault;
leftover vaults named mcp-e2e-* from interrupted runs are deleted first. Nothing else is touched.
"""
import json
import os
import sys
import time
import urllib.error
import urllib.parse
import urllib.request

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import oauth  # noqa: E402

SERVER = os.environ["THEGRAM_SERVER"].rstrip("/")
MOUNT = os.environ.get("THEGRAM_MOUNT", "")
OTHER = os.environ.get("THEGRAM_OTHER_TOKEN")
DOC = "mcp-e2e-" + time.strftime("%Y%m%d%H%M%S")
SCRATCH_PREFIX = "mcp-e2e-"
steps = []


def http(method, path, body=None, token=None, headers=None):
    data = None if body is None else json.dumps(body).encode()
    h = {"Content-Type": "application/json", "Accept": "application/json, text/event-stream", **(headers or {})}
    if token:
        h["Authorization"] = "Bearer " + token
    req = urllib.request.Request(SERVER + path, data=data, method=method, headers=h)
    try:
        with urllib.request.urlopen(req, timeout=120) as r:
            status, headers, raw = r.status, dict(r.headers), r.read()
    except urllib.error.HTTPError as e:
        status, headers, raw = e.code, dict(e.headers), e.read()
    try:
        return status, headers, json.loads(raw) if raw else None
    except ValueError:
        return status, headers, raw


class Client:
    def __init__(self, token):
        self.token, self.session, self.next = token, None, 0

    def rpc(self, method, params=None, notify=False):
        body = {"jsonrpc": "2.0", "method": method, "params": params or {}}
        if not notify:
            self.next += 1
            body["id"] = self.next
        headers = {"MCP-Protocol-Version": "2025-06-18"}
        if self.session:
            headers["Mcp-Session-Id"] = self.session
        status, h, answer = http("POST", "/mcp", body, self.token, headers)
        self.session = h.get("Mcp-Session-Id") or h.get("mcp-session-id") or self.session
        return status, answer

    def start(self):
        status, answer = self.rpc("initialize", {"protocolVersion": "2025-06-18", "capabilities": {}, "clientInfo": {"name": "mcp-e2e", "version": "1"}})
        self.rpc("notifications/initialized", notify=True)
        return status, answer

    def tool(self, name, args):
        status, answer = self.rpc("tools/call", {"name": name, "arguments": args})
        result = (answer or {}).get("result") or {}
        return bool(result.get("isError")), result.get("structuredContent")


def record(name, ok, **detail):
    steps.append({"step": name, "ok": bool(ok), **detail})
    print(("PASS " if ok else "FAIL ") + name, flush=True)


def error_code(content):
    return ((content or {}).get("error") or {}).get("code")


def main():
    evidence = sys.argv[1]
    os.makedirs(evidence, exist_ok=True)
    _, _, config = http("GET", "/v1/config")
    oidc = (config or {}).get("oidc") or {}
    store = os.environ.get("THEGRAM_OAUTH_STORE") or os.path.expanduser(f"~/.config/thegram-e2e/{urllib.parse.urlparse(SERVER).hostname}.json")
    session = oauth.Session(SERVER, store, os.environ.get("THEGRAM_OAUTH_CLIENT_ID") or oidc.get("desktop_client_id"))
    found = session.found
    record("no token is refused with a resource_metadata challenge", found["status"] == 401 and "resource_metadata" in found["challenge"],
           www_authenticate=found["www_authenticate"])
    prm = found.get("prm") or {}
    record("protected resource metadata names /mcp and the authorization server", prm.get("resource") == SERVER + "/mcp" and bool(prm.get("authorization_servers")), prm=prm)
    meta = found.get("metadata") or {}
    record("authorization server supports PKCE S256, CIMD and issuer identification",
           "S256" in meta.get("code_challenge_methods_supported", []) and meta.get("client_id_metadata_document_supported") is True
           and meta.get("authorization_response_iss_parameter_supported") is True, issuer=meta.get("issuer"))

    token = session.access_token(prm["resource"])
    api_token = session.access_token(oidc["resource"])
    record("MCP access token is bound to the /mcp audience", oauth.jwt_claims(token).get("aud") == prm["resource"], aud=oauth.jwt_claims(token).get("aud"))
    status, _, _ = http("GET", "/v1/vaults", token=token)
    record("MCP token is refused by the vault API", status == 401, status=status)
    status, _, _ = http("POST", "/mcp", {"jsonrpc": "2.0", "id": 1, "method": "tools/list"}, token=api_token)
    record("vault API token is refused by /mcp", status == 401, status=status)
    status, _, _ = http("POST", "/mcp", {"jsonrpc": "2.0", "id": 1, "method": "tools/list"}, token="not-a-jwt")
    record("invalid token gets 401", status == 401, status=status)

    mount, scratch = MOUNT, None
    if not mount:
        _, _, listed = http("GET", "/v1/vaults", token=api_token)
        for v in (listed or {}).get("vaults", []):
            if v.get("name", "").startswith(SCRATCH_PREFIX) and v.get("role") == "owner":
                delete_vault(api_token, v["id"])
        name = SCRATCH_PREFIX + time.strftime("%Y%m%dT%H%MZ", time.gmtime())
        status, _, created = http("POST", "/v1/vaults", {"name": name}, token=api_token)
        record("scratch vault created", status == 201, status=status, vault_name=name)
        if status != 201:
            return finish(evidence, mount)
        mount = scratch = created["id"]
    try:
        exercise(token, api_token, mount)
    finally:
        if scratch:
            status = delete_vault(api_token, scratch)
            record("scratch vault deleted", status == 204, status=status)
    finish(evidence, mount)


def delete_vault(api_token, vault):
    status, _, meta = http("GET", f"/v1/vaults/{vault}", token=api_token)
    if status != 200:
        return status
    status, _, _ = http("DELETE", f"/v1/vaults/{vault}", token=api_token, headers={"If-Match": meta["policy_etag"]})
    return status


def finish(evidence, mount):
    report = {"server": SERVER, "mount": mount, "document": DOC, "at": time.strftime("%Y-%m-%dT%H:%M:%S%z"),
              "passed": sum(s["ok"] for s in steps), "total": len(steps), "steps": steps}
    with open(os.path.join(evidence, "mcp-e2e-report.json"), "w") as f:
        json.dump(report, f, indent=2, ensure_ascii=False)
    print(f"{report['passed']}/{report['total']} passed")
    sys.exit(0 if report["passed"] == report["total"] else 1)


def exercise(token, api_token, mount):
    drive = mount.removeprefix("google-drive-") if mount.startswith("google-drive-") else None
    path = f"@mounts/{mount}/{DOC}.gram"
    agent = Client(token)
    status, init = agent.start()
    record("initialize", status == 200 and "result" in (init or {}), server=((init or {}).get("result") or {}).get("serverInfo"))
    _, listed = agent.rpc("tools/list")
    names = sorted(t["name"] for t in ((listed or {}).get("result") or {}).get("tools", []))
    record("tools/list has the 15 gram tools", len(names) == 15 and all(n.startswith("gram_") for n in names), tools=names)

    failed, projects = agent.tool("gram_projects", {})
    mounts = {m["id"]: m for m in (projects or {}).get("mounts", [])}
    record("gram_projects lists the mount as writable", not failed and mounts.get(mount, {}).get("access") == "write", mounts=list(mounts))

    failed, created = agent.tool("gram_create", {"path": path, "base_revision": None, "title": "MCP E2E", "content": {
        "text": "# Overview\n\n[[prj-e2e]]\n\n# Decisions\n\n# Log\n",
        "records": [{"type": "project", "id": "prj-e2e", "fields": {"t": ["MCP E2E project"], "x": ["active"]}}]}})
    doc = (created or {}).get("doc") or {}
    record("gram_create commits to storage", not failed and doc.get("rev") == 0 and (created or {}).get("sync", {}).get("state") == "synced", result=created)

    patch = {"path": path, "base_revision": doc.get("rev"), "expected_hash": doc.get("hash"), "request_id": DOC + "-dec",
             "operations": [{"op": "add", "record": {"type": "decision", "id": "dec-e2e", "fields": {"t": ["Cloud agents use the remote MCP"], "x": ["accepted"]},
                                                     "links": [["part-of", "prj-e2e"]]}, "place": {"section": "Decisions"}}]}
    failed, patched = agent.tool("gram_patch", patch)
    record("gram_patch adds one revision", not failed and ((patched or {}).get("doc") or {}).get("rev") == 1, result=patched)
    failed, replay = agent.tool("gram_patch", patch)
    record("same request_id replays without a new revision", not failed and ((replay or {}).get("receipt") or {}).get("replayed") is True
           and ((replay or {}).get("doc") or {}).get("rev") == 1, result=replay)
    stale = dict(patch, request_id=DOC + "-stale", operations=[{"op": "set", "entity": "dec-e2e", "key": "x", "value": "superseded"}])
    failed, refused = agent.tool("gram_patch", stale)
    record("stale base is refused", failed and error_code(refused) == "STALE_REVISION", result=refused)

    failed, brief = agent.tool("gram_brief", {"path": path})
    record("gram_brief sees revision 1", not failed and (brief or {}).get("docs", [[None, None, None]])[0][2] == 1)
    failed, read = agent.tool("gram_read", {"path": path, "section": "Decisions"})
    record("gram_read renders the decision", not failed and "dec-e2e" in (read or {}).get("md", ""))
    failed, recall = agent.tool("gram_recall", {"query": "remote MCP", "folder": f"@mounts/{mount}"})
    record("gram_recall finds the decision", not failed and any("#dec-e2e" in str(hit[0]) for hit in (recall or {}).get("hits", [])), result=recall)
    failed, state = agent.tool("gram_state", {"path": path, "selector": {"revision": 0}})
    record("gram_state reads revision 0", not failed)

    item = None
    if drive:
        status, _, tree = http("GET", f"/v1/drive/accounts/{drive}/items", token=api_token)
        item = next((i for i in (tree or {}).get("items", []) if i.get("name") == DOC + ".gram"), None)
        record("Drive holds the document", status == 200 and item is not None, status=status, item=item)
    else:
        status, _, body = http("GET", f"/v1/vaults/{mount}/files/{DOC}/history", token=api_token)
        record("vault history holds both revisions", status == 200 and len((body or {}).get("history", [])) == 2, status=status)

    if OTHER:
        other = Client(OTHER)
        other.start()
        failed, denied = other.tool("gram_read", {"path": path})
        record("another account cannot read the document", failed and error_code(denied) in ("E_PATH", "E_FORBIDDEN"), result=denied)

    status = None
    if drive:
        if item:
            status, _, _ = http("DELETE", f"/v1/drive/accounts/{drive}/items/{item['id']}", token=api_token,
                                headers={"If-Match": '"' + str(item.get("head_revision_id")) + '"'})
    else:
        status, headers, _ = http("GET", f"/v1/vaults/{mount}/files/{DOC}", token=api_token)
        etag = headers.get("ETag") or headers.get("Etag")
        if etag:
            status, _, _ = http("DELETE", f"/v1/vaults/{mount}/files/{DOC}", token=api_token, headers={"If-Match": etag})
    record("scratch document deleted", status in (200, 204), status=status)


main()
