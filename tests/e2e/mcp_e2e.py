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
Without THEGRAM_MOUNT it uses the default writable Thegram vault and deletes only the scratch document.
THEGRAM_AGENT_SCOPE=1 GRAM_VAULT_E2E_SIGNIN=token THEGRAM_E2E_MAILBOX=<configured mailbox>
runs the fresh-client scope suite instead, with cookie+CSRF management and temporary Logto application cleanup.
Its agent-scope-report.json records raw requests/responses with credentials redacted and the unavailable MCP deletion coverage.
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

steps = []
exchanges = []


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
        exchanges.append({"request": {"method": "POST", "url": SERVER + "/mcp", "body": body,
                          "headers": {"MCP-Protocol-Version": "2025-06-18", "Authorization": "Bearer [REDACTED]",
                                      **({"Mcp-Session-Id": "[REDACTED]"} if "Mcp-Session-Id" in headers else {})}},
                          "response": {"status": status, "body": answer}})
        return status, answer

    def start(self):
        status, answer = self.rpc("initialize", {"protocolVersion": "2025-06-18", "capabilities": {}, "clientInfo": {"name": "mcp-e2e", "version": "1"}})
        self.rpc("notifications/initialized", notify=True)
        return status, answer

    def tool(self, name, args):
        status, answer = self.rpc("tools/call", {"name": name, "arguments": args})
        result = (answer or {}).get("result") or {}
        return status != 200 or not result or "error" in (answer or {}) or bool(result.get("isError")), result.get("structuredContent")


def record(name, ok, **detail):
    steps.append({"step": name, "ok": bool(ok), **detail})
    print(("PASS " if ok else "FAIL ") + name, flush=True)


def error_code(content):
    return ((content or {}).get("error") or {}).get("code")


def main():
    evidence = sys.argv[1] if len(sys.argv) > 1 else "evidence/agent-scope-" + time.strftime("%Y%m%dT%H%M%SZ", time.gmtime())
    os.makedirs(evidence, exist_ok=True)
    if os.environ.get("THEGRAM_AGENT_SCOPE") == "1":
        return scope_main(evidence)
    _, _, config = http("GET", "/v1/config")
    oidc = (config or {}).get("oidc") or {}
    store = os.environ.get("THEGRAM_OAUTH_STORE") or os.path.expanduser(f"~/.config/thegram-e2e/{urllib.parse.urlparse(SERVER).hostname}.json")
    session = oauth.Session(SERVER, store, os.environ.get("THEGRAM_OAUTH_CLIENT_ID") or oidc.get("desktop_client_id"))
    found = session.found
    record("no token is refused with a resource_metadata challenge", found["status"] == 401 and "resource_metadata" in found["challenge"],
           www_authenticate=found["www_authenticate"])
    prm = found.get("prm") or {}
    record("protected resource metadata names /mcp and the authorization server", prm.get("resource", "").endswith("/mcp") and bool(prm.get("authorization_servers")), prm=prm)
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

    mount = MOUNT
    if not mount:
        agent = Client(token)
        agent.start()
        failed, projects = agent.tool("gram_projects", {})
        mount = next((m["id"] for m in (projects or {}).get("mounts", [])
                      if m.get("name") == "Thegram" and m.get("access") == "write"), None)
        record("default Thegram mount is writable", not failed and bool(mount), result=projects)
        if not mount:
            return finish(evidence, mount)
    exercise(token, api_token, mount)
    finish(evidence, mount)


def finish(evidence, mount, detail=None):
    report = {"server": SERVER, "mount": mount, "document": DOC, "at": time.strftime("%Y-%m-%dT%H:%M:%S%z"),
              "passed": sum(s["ok"] for s in steps), "total": len(steps), "steps": steps, **(detail or {})}
    filename = "agent-scope-report.json" if detail is not None else "mcp-e2e-report.json"
    with open(os.path.join(evidence, filename), "w") as f:
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
        record("another account cannot read the document", failed and error_code(denied) in ("AGENT_SCOPE_DENIED", "E_PATH", "E_FORBIDDEN"), result=denied)

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


def require(name, ok, **detail):
    record(name, ok, **detail)
    if not ok:
        raise RuntimeError("step failed: " + name)


def scope_main(evidence):
    user, management = oauth.CookieSession(SERVER), None
    client_id, second, before, default = None, None, None, None
    disconnected = False
    report_detail = {"coverage_gaps": [{"criterion": "write denies document delete; delete permits document delete",
        "status": "unreachable_through_mcp", "reason": "The 15 MCP tools expose no document deletion. API-audience tokens are KindBearer, not KindAgent, and cannot prove agent delete enforcement. Server unit tests must cover delete enforcement."}],
        "requests": exchanges}

    def api(method, path, body=None, headers=None):
        status, h, answer = user.request(method, path, body, headers)
        exchanges.append({"request": {"method": method, "url": SERVER + path, "body": body,
                          "headers": {"Origin": SERVER, **(headers or {}),
                                      **({"X-CSRF-Token": "[REDACTED]"} if method != "GET" else {})},
                          "authentication": "cookie session [REDACTED]"},
                          "response": {"status": status, "body": answer}})
        return status, h, answer

    def projects(agent):
        failed, result = agent.tool("gram_projects", {})
        require("gram_projects succeeds", not failed, result=result)
        return {m["id"]: m for m in (result or {}).get("mounts", [])}

    def denial(agent, name, args, label):
        failed, result = agent.tool(name, args)
        require(label, failed and error_code(result) == "AGENT_SCOPE_DENIED"
                and "https://vault.thegram.one/settings/agents" in json.dumps(result), result=result)

    def create(agent, path, label):
        failed, result = agent.tool("gram_create", {"path": path, "base_revision": None,
            "title": "Agent scope E2E", "content": {"text": "# Overview\n\nSynthetic agent-scope check.\n", "records": []}})
        require(label, not failed and (result or {}).get("sync", {}).get("state") == "synced", result=result)

    def grant(level):
        body = {"vaults": {default: "write", second: level}, "drive": {}}
        status, _, answer = api("PUT", "/v1/me/agents/" + client_id, body)
        require(level + " grant saved using cookie + CSRF", status == 200 and answer.get("vaults") == body["vaults"], status=status, result=answer)

    def remove_vault(vault):
        status, _, meta = api("GET", "/v1/vaults/" + vault)
        require("cleanup vault metadata", status == 200, status=status)
        status, _, answer = api("DELETE", "/v1/vaults/" + vault, headers={"If-Match": meta["policy_etag"]})
        require("created vault deleted", status == 204, status=status, vault=vault, result=answer)

    try:
        status, _, config = http("GET", "/v1/config")
        require("vault config", status == 200, status=status)
        found = oauth.discover(SERVER)
        require("401 OAuth discovery", found["status"] == 401 and bool(found.get("prm")), discovery=found)
        audience = found["prm"]["resource"]
        report_detail.update(mcp_audience=audience, audience_matches_endpoint=audience == SERVER + "/mcp")
        if audience != SERVER + "/mcp":
            report_detail["isolation_risk"] = "This endpoint advertises the production MCP audience; a production-audience token is accepted here."
        management = oauth.Management(config["oidc"]["issuer"])
        email = os.environ["THEGRAM_E2E_MAILBOX"]
        profile = user.sign_in(config, email, management)
        require("cookie sign-in with CSRF", bool(user.csrf), principal=profile["principal"])
        status, _, vaults = api("GET", "/v1/vaults")
        require("user vault list before first sight", status == 200, status=status)
        before = {v["id"] for v in vaults["vaults"]}
        app = management.request("POST", "/api/applications", {"name": "Agent scope E2E " + DOC, "type": "Native"})
        client_id = app["id"]
        report_detail["client_id"] = client_id
        management.request("PATCH", "/api/applications/" + client_id, {"oidcClientMetadata": {"redirectUris": ["http://127.0.0.1:53682/callback"], "postLogoutRedirectUris": []}})
        status, _, listed = api("GET", "/v1/me/agents")
        require("fresh client has no prior grant", status == 200 and all(a["client"] != client_id for a in listed["agents"]), status=status)
        token = user.access_token(found, client_id, audience)
        claims = oauth.jwt_claims(token)
        require("MCP token identifies the fresh Logto client", claims.get("client_id") == client_id and claims.get("aud") == audience,
                client_id=claims.get("client_id"), aud=claims.get("aud"), exp=claims.get("exp"))
        agent = Client(token)
        status, init = agent.start()
        require("initialize", status == 200 and "result" in (init or {}), status=status, response=init)
        _, listed = agent.rpc("tools/list")
        names = [t["name"] for t in ((listed or {}).get("result") or {}).get("tools", [])]
        require("15 MCP tools (no document delete)", len(names) == 15 and "gram_delete" not in names, tools=names)
        mounts = projects(agent)
        require("first sight exposes only writable Thegram", len(mounts) == 1 and next(iter(mounts.values())).get("name") == "Thegram"
                and next(iter(mounts.values())).get("access") == "write", mounts=mounts)
        default = next(iter(mounts))
        status, _, listed = api("GET", "/v1/me/agents")
        initial = next(a for a in listed["agents"] if a["client"] == client_id)
        require("first sight grants default write only and no Drive", initial["vaults"] == {default: "write"} and initial["drive"] == {}, grant=initial)
        default_path = f"@mounts/{default}/{DOC}-default.gram"
        create(agent, default_path, "default vault write syncs")
        status, _, created = api("POST", "/v1/vaults", {"name": DOC})
        require("second user-owned vault created via vault API", status == 201, status=status, result=created)
        second = created["id"]
        path = f"@mounts/{second}/{DOC}.gram"
        require("new vault is invisible without a grant", second not in projects(agent), vault=second)
        denial(agent, "gram_read", {"path": path}, "none grant rejects direct path reads")
        grant("read")
        require("read grant exposes a read-only mount", projects(agent).get(second, {}).get("access") == "read", vault=second)
        failed, brief = agent.tool("gram_brief", {"folder": f"@mounts/{second}"})
        require("read grant permits reads", not failed, result=brief)
        denial(agent, "gram_create", {"path": path, "base_revision": None, "title": "Denied", "content": "No write"}, "read grant rejects writes with settings URL")
        grant("write")
        require("write grant exposes writable mount", projects(agent).get(second, {}).get("access") == "write")
        api_token = user.access_token(found, client_id, config["oidc"]["resource"])
        status, _, _ = http("GET", "/v1/vaults", token=token)
        require("MCP audience cannot access vault API", status == 401, status=status)
        exercise(token, api_token, second)
        grant("delete")
        create(agent, f"@mounts/{second}/{DOC}-delete-grant.gram", "delete level includes MCP write")
        status, _, answer = api("DELETE", "/v1/me/agents/" + client_id)
        disconnected = status == 204
        require("agent disconnected and Logto grant revoked", disconnected, status=status, result=answer)
        require("same access token is still unexpired", claims["exp"] > time.time(), exp=claims["exp"])
        denial(agent, "gram_read", {"path": default_path}, "disconnect immediately denies existing default read with same token and session")
        denial(agent, "gram_create", {"path": f"@mounts/{second}/revoked.gram", "base_revision": None, "title": "Denied", "content": "No write"},
               "disconnect immediately denies writes with same token and session")
        require("disconnect hides all mounts", not projects(agent))
        status, _, listed = api("GET", "/v1/me/agents")
        final = next(a for a in listed["agents"] if a["client"] == client_id)
        require("disconnect persists empty grants", final["disconnected"] and final["vaults"] == {} and final["drive"] == {}, grant=final)
    except Exception as error:
        record("agent-scope suite exception", False, error=str(error))
    finally:
        # Each cleanup is independent so a failure cannot strand the other resources.
        if client_id and not disconnected:
            try:
                status, _, answer = api("DELETE", "/v1/me/agents/" + client_id)
                record("cleanup agent disconnected", status in (204, 404), status=status, result=answer)
            except Exception as error:
                record("cleanup agent disconnected", False, error=str(error))
        if before is not None:
            try:
                status, _, current = api("GET", "/v1/vaults")
                require("cleanup vault list", status == 200, status=status)
                for vault in current["vaults"]:
                    if vault["id"] == second or (vault["id"] not in before and vault.get("name") == "Thegram" and vault.get("role") == "owner"):
                        try:
                            remove_vault(vault["id"])
                        except Exception as error:
                            record("cleanup created vault", False, vault=vault["id"], error=str(error))
                if default in before:
                    file_path = f"/v1/vaults/{default}/files/{DOC}-default"
                    status, h, _ = user.request("GET", file_path)
                    if status == 200:
                        status, _, _ = api("DELETE", file_path, headers={"If-Match": h.get("ETag") or h.get("Etag")})
                        require("default scratch document deleted", status == 204, status=status)
                    else:
                        require("default scratch document absent", status == 404, status=status)
            except Exception as error:
                record("cleanup vaults", False, error=str(error))
        if client_id:
            try:
                management.request("DELETE", "/api/applications/" + client_id)
                record("temporary Logto application deleted", True)
            except Exception as error:
                record("temporary Logto application deleted", False, error=str(error))
        finish(evidence, second, report_detail)


if __name__ == "__main__":
    main()
