#!/usr/bin/env python3
"""End-to-end check of the remote Thegram MCP endpoint as a cloud agent uses it.

Usage:
  THEGRAM_SERVER=https://vault.thegram.one THEGRAM_TOKEN=gvt_... THEGRAM_VAULT=<vault id> \
  [THEGRAM_OTHER_TOKEN=gvt_... (a second account without access to the vault)] \
  python3 tests/e2e/mcp_e2e.py <evidence-dir>

Creates one scratch document in the vault, exercises the tools on it, deletes it through the vault API,
and writes <evidence-dir>/mcp-e2e-report.json. Exits non-zero when any step fails.
"""
import json
import os
import sys
import time
import urllib.error
import urllib.request

SERVER = os.environ["THEGRAM_SERVER"].rstrip("/")
TOKEN = os.environ["THEGRAM_TOKEN"]
VAULT = os.environ["THEGRAM_VAULT"]
OTHER = os.environ.get("THEGRAM_OTHER_TOKEN")
DOC = "mcp-e2e-" + time.strftime("%Y%m%d%H%M%S")
PATH = f"@mounts/{VAULT}/{DOC}.gram"
steps = []


def http(method, path, body=None, token=TOKEN, headers=None):
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
    status, _, _ = http("POST", "/mcp", {"jsonrpc": "2.0", "id": 1, "method": "tools/list"}, token=None)
    record("no token is refused", status == 401, status=status)

    agent = Client(TOKEN)
    status, init = agent.start()
    record("initialize", status == 200 and "result" in (init or {}), server=((init or {}).get("result") or {}).get("serverInfo"))
    _, listed = agent.rpc("tools/list")
    names = sorted(t["name"] for t in ((listed or {}).get("result") or {}).get("tools", []))
    record("tools/list has the 15 gram tools", len(names) == 15 and all(n.startswith("gram_") for n in names), tools=names)

    failed, projects = agent.tool("gram_projects", {})
    mounts = {m["id"]: m for m in (projects or {}).get("mounts", [])}
    record("gram_projects lists the vault as a writable mount", not failed and mounts.get(VAULT, {}).get("access") == "write", mounts=list(mounts))

    failed, created = agent.tool("gram_create", {"path": PATH, "base_revision": None, "title": "MCP E2E", "content": {
        "text": "# Overview\n\n[[prj-e2e]]\n\n# Decisions\n\n# Log\n",
        "records": [{"type": "project", "id": "prj-e2e", "fields": {"t": ["MCP E2E project"], "x": ["active"]}}]}})
    doc = (created or {}).get("doc") or {}
    record("gram_create commits to storage", not failed and doc.get("rev") == 0 and (created or {}).get("sync", {}).get("state") == "synced", result=created)

    patch = {"path": PATH, "base_revision": doc.get("rev"), "expected_hash": doc.get("hash"), "request_id": DOC + "-dec",
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

    failed, brief = agent.tool("gram_brief", {"path": PATH})
    record("gram_brief sees revision 1", not failed and (brief or {}).get("docs", [[None, None, None]])[0][2] == 1)
    failed, read = agent.tool("gram_read", {"path": PATH, "section": "Decisions"})
    record("gram_read renders the decision", not failed and "dec-e2e" in (read or {}).get("md", ""))
    failed, recall = agent.tool("gram_recall", {"query": "remote MCP", "folder": f"@mounts/{VAULT}"})
    record("gram_recall finds the decision", not failed and any("#dec-e2e" in str(hit[0]) for hit in (recall or {}).get("hits", [])), result=recall)
    failed, state = agent.tool("gram_state", {"path": PATH, "selector": {"revision": 0}})
    record("gram_state reads revision 0", not failed)

    status, _, body = http("GET", f"/v1/vaults/{VAULT}/files/{DOC}/history")
    record("vault history holds both revisions", status == 200 and len((body or {}).get("history", [])) == 2, status=status)

    if OTHER:
        other = Client(OTHER)
        other.start()
        failed, denied = other.tool("gram_read", {"path": PATH})
        record("another account cannot read the document", failed and error_code(denied) in ("E_PATH", "E_FORBIDDEN"), result=denied)

    status, headers, _ = http("GET", f"/v1/vaults/{VAULT}/files/{DOC}")
    etag = headers.get("ETag") or headers.get("Etag")
    status, _, _ = http("DELETE", f"/v1/vaults/{VAULT}/files/{DOC}", headers={"If-Match": etag})
    record("scratch document deleted", status in (200, 204), status=status)

    report = {"server": SERVER, "vault": VAULT, "document": DOC, "at": time.strftime("%Y-%m-%dT%H:%M:%S%z"),
              "passed": sum(s["ok"] for s in steps), "total": len(steps), "steps": steps}
    with open(os.path.join(evidence, "mcp-e2e-report.json"), "w") as f:
        json.dump(report, f, indent=2, ensure_ascii=False)
    print(f"{report['passed']}/{report['total']} passed")
    sys.exit(0 if report["passed"] == report["total"] else 1)


main()
