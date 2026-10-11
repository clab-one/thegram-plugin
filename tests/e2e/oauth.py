"""OAuth for the E2E: discovers the authorization server the way an MCP client does and keeps one refresh token.

The first run opens a browser for one sign-in on a loopback redirect; later runs reuse the stored refresh
token (0600, outside the repository) to mint access tokens for any resource.
"""
import base64
import hashlib
import http.server
import json
import os
import re
import secrets
import threading
import urllib.error
import urllib.parse
import urllib.request
import webbrowser


def fetch(url, data=None, headers=None, method=None):
    req = urllib.request.Request(url, data=data, method=method, headers=headers or {})
    try:
        with urllib.request.urlopen(req, timeout=60) as r:
            return r.status, dict(r.headers), r.read()
    except urllib.error.HTTPError as e:
        return e.code, dict(e.headers), e.read()


def challenge_params(header):
    return dict(re.findall(r'(\w+)="([^"]*)"', header or ""))


def discover(server):
    """Follows 401 → protected resource metadata → authorization server metadata."""
    status, headers, _ = fetch(server + "/mcp", json.dumps({"jsonrpc": "2.0", "id": 1, "method": "tools/list"}).encode(),
                               {"Content-Type": "application/json", "Accept": "application/json, text/event-stream"}, "POST")
    www = headers.get("WWW-Authenticate") or headers.get("Www-Authenticate") or ""
    params = challenge_params(www)
    out = {"status": status, "www_authenticate": www, "challenge": params}
    if "resource_metadata" not in params:
        return out
    _, _, body = fetch(params["resource_metadata"])
    prm = json.loads(body)
    issuer = prm["authorization_servers"][0]
    _, _, body = fetch(issuer.rstrip("/") + "/.well-known/openid-configuration")
    out.update(prm=prm, issuer=issuer, metadata=json.loads(body))
    return out


def jwt_claims(token):
    payload = token.split(".")[1]
    return json.loads(base64.urlsafe_b64decode(payload + "=" * (-len(payload) % 4)))


class Session:
    def __init__(self, server, store, client_id):
        self.server, self.store, self.client_id = server, store, client_id
        self.found = discover(server)
        self.meta = self.found["metadata"]
        self.refresh = None
        if os.path.exists(store):
            with open(store) as f:
                self.refresh = json.load(f).get("refresh_token")

    def _save(self, tokens):
        if tokens.get("refresh_token"):
            self.refresh = tokens["refresh_token"]
            os.makedirs(os.path.dirname(self.store), exist_ok=True)
            fd = os.open(self.store, os.O_WRONLY | os.O_CREAT | os.O_TRUNC, 0o600)
            with os.fdopen(fd, "w") as f:
                json.dump({"refresh_token": self.refresh}, f)

    def _token(self, fields):
        status, _, body = fetch(self.meta["token_endpoint"], urllib.parse.urlencode(fields).encode(),
                                {"Content-Type": "application/x-www-form-urlencoded"}, "POST")
        if status != 200:
            raise RuntimeError(f"token endpoint {status}: {body[:300]!r}")
        tokens = json.loads(body)
        self._save(tokens)
        return tokens

    def login(self, resource):
        verifier = secrets.token_urlsafe(48)
        state = secrets.token_urlsafe(16)
        result = {}

        class Handler(http.server.BaseHTTPRequestHandler):
            def do_GET(self):
                query = urllib.parse.parse_qs(urllib.parse.urlparse(self.path).query)
                result.update({k: v[0] for k, v in query.items()})
                self.send_response(200)
                self.end_headers()
                self.wfile.write(b"Thegram E2E sign-in finished; you can close this tab.")

            def log_message(self, *_):
                pass

        httpd = http.server.HTTPServer(("127.0.0.1", 0), Handler)
        redirect = f"http://127.0.0.1:{httpd.server_port}/callback"
        query = {"client_id": self.client_id, "redirect_uri": redirect, "response_type": "code", "state": state,
                 "scope": " ".join(self.found["prm"].get("scopes_supported") or ["openid", "offline_access"]),
                 "resource": resource, "prompt": "consent",
                 "code_challenge": base64.urlsafe_b64encode(hashlib.sha256(verifier.encode()).digest()).rstrip(b"=").decode(),
                 "code_challenge_method": "S256"}
        url = self.meta["authorization_endpoint"] + "?" + urllib.parse.urlencode(query)
        thread = threading.Thread(target=httpd.handle_request)
        thread.start()
        print("Sign in to finish the E2E setup:", url, flush=True)
        webbrowser.open(url)
        thread.join(timeout=600)
        httpd.server_close()
        if result.get("state") != state or "code" not in result:
            raise RuntimeError(f"authorization failed: {result.get('error')} {result.get('error_description')}")
        return self._token({"grant_type": "authorization_code", "client_id": self.client_id, "code": result["code"],
                            "redirect_uri": redirect, "code_verifier": verifier, "resource": resource})

    def access_token(self, resource):
        if self.refresh:
            try:
                return self._token({"grant_type": "refresh_token", "client_id": self.client_id,
                                    "refresh_token": self.refresh, "resource": resource})["access_token"]
            except RuntimeError:
                self.refresh = None
        return self.login(resource)["access_token"]
