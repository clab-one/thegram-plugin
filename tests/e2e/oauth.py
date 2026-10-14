"""OAuth for the E2E: discovers the authorization server the way an MCP client does and keeps one refresh token.

The first run opens a browser for one sign-in on a loopback redirect; later runs reuse the stored refresh
token (0600, outside the repository) to mint access tokens for any resource.
"""
import base64
import hashlib
import http.server
import http.cookiejar
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
        # Logto binds a refresh token to the resource of its authorization request, so each resource keeps its own.
        self.refresh = {}
        if os.path.exists(store):
            with open(store) as f:
                self.refresh = json.load(f).get("refresh_tokens", {})

    def _save(self, resource, tokens):
        if tokens.get("refresh_token"):
            self.refresh[resource] = tokens["refresh_token"]
            os.makedirs(os.path.dirname(self.store), exist_ok=True)
            fd = os.open(self.store, os.O_WRONLY | os.O_CREAT | os.O_TRUNC, 0o600)
            with os.fdopen(fd, "w") as f:
                json.dump({"refresh_tokens": self.refresh}, f)

    def _token(self, fields):
        status, _, body = fetch(self.meta["token_endpoint"], urllib.parse.urlencode(fields).encode(),
                                {"Content-Type": "application/x-www-form-urlencoded"}, "POST")
        if status != 200:
            raise RuntimeError(f"token endpoint {status}: {body[:300]!r}")
        tokens = json.loads(body)
        self._save(fields["resource"], tokens)
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
        if resource in self.refresh:
            try:
                return self._token({"grant_type": "refresh_token", "client_id": self.client_id,
                                    "refresh_token": self.refresh[resource], "resource": resource})["access_token"]
            except RuntimeError:
                del self.refresh[resource]
        return self.login(resource)["access_token"]


class NoRedirect(urllib.request.HTTPRedirectHandler):
    def redirect_request(self, *args, **kwargs):
        return None


class CookieSession:
    """User cookies + CSRF manage grants; agent tokens never do."""
    def __init__(self, server):
        self.server, self.csrf = server, None
        self.opener = urllib.request.build_opener(
            urllib.request.HTTPCookieProcessor(http.cookiejar.CookieJar()), NoRedirect())

    def request(self, method, path, body=None, headers=None):
        url = path if path.startswith(("https://", "http://")) else self.server + path
        h = dict(headers or {})
        if url.startswith(self.server + "/"):
            h["Origin"] = self.server
            if self.csrf and method not in ("GET", "HEAD"):
                h["X-CSRF-Token"] = self.csrf
        if isinstance(body, (dict, list)):
            body = json.dumps(body).encode()
            h["Content-Type"] = "application/json"
        req = urllib.request.Request(url, data=body, headers=h, method=method)
        try:
            with self.opener.open(req, timeout=60) as response:
                status, hdrs, raw = response.status, response.headers, response.read()
        except urllib.error.HTTPError as error:
            status, hdrs, raw = error.code, error.headers, error.read()
        try:
            result = json.loads(raw) if raw else None
        except ValueError:
            result = raw.decode(errors="replace")
        return status, dict(hdrs), result

    def follow(self, url, until):
        for _ in range(20):
            if until(url):
                return url
            status, headers, _ = self.request("GET", url)
            location = headers.get("Location")
            if status not in (301, 302, 303, 307, 308) or not location:
                return url
            url = urllib.parse.urljoin(url, location)
        raise RuntimeError("OAuth redirect loop")

    def sign_in(self, config, email, management):
        if os.environ.get("GRAM_VAULT_E2E_SIGNIN") != "token":
            raise RuntimeError("Agent-scope suite requires GRAM_VAULT_E2E_SIGNIN=token")
        logto = config["oidc"]["issuer"].rsplit("/oidc", 1)[0]
        page = self.follow(self.server + "/auth/login?provider=email&next=/settings/agents",
                           lambda url: url.startswith(logto + "/") and "/oidc/" not in url)
        if urllib.parse.urlparse(page).path != "/identifier-sign-in":
            raise RuntimeError("Vault login did not open Logto email sign-in")
        status, _, result = self.request("PUT", logto + "/api/experience", {"interactionEvent": "SignIn"})
        if status not in (200, 204):
            raise RuntimeError(f"Logto interaction {status}: {result}")
        one_time = management.request("POST", "/api/one-time-tokens", {"email": email, "expiresIn": 600})
        status, _, result = self.request("POST", logto + "/api/experience/verification/one-time-token/verify",
                                        {"identifier": {"type": "email", "value": email}, "token": one_time["token"]})
        if status != 200:
            raise RuntimeError(f"Logto verification {status}: {result}")
        status, _, result = self.request("POST", logto + "/api/experience/identification", {"verificationId": result["verificationId"]})
        if status != 204:
            raise RuntimeError(f"Existing E2E account identification {status}: {result}")
        status, _, result = self.request("POST", logto + "/api/experience/submit")
        if status != 200:
            raise RuntimeError(f"Logto submit {status}: {result}")
        self.follow(result["redirectTo"], lambda url: url.startswith(self.server + "/")
                    and urllib.parse.urlparse(url).path != "/auth/callback")
        status, _, profile = self.request("GET", "/v1/me")
        if status != 200 or not profile.get("csrf_token") or profile.get("consent_required"):
            raise RuntimeError("Use an existing adult E2E account with current consent and a cookie session")
        self.csrf = profile["csrf_token"]
        return profile

    def access_token(self, found, client_id, resource):
        """PKCE through the Logto cookie session, without storing tokens."""
        verifier, state = secrets.token_urlsafe(48), secrets.token_urlsafe(24)
        redirect = "http://127.0.0.1:53682/callback"
        query = {"client_id": client_id, "redirect_uri": redirect, "response_type": "code",
                 "scope": " ".join(found["prm"]["scopes_supported"]), "resource": resource,
                 "state": state, "code_challenge_method": "S256",
                 "code_challenge": base64.urlsafe_b64encode(hashlib.sha256(verifier.encode()).digest()).rstrip(b"=").decode()}
        callback = self.follow(found["metadata"]["authorization_endpoint"] + "?" + urllib.parse.urlencode(query),
                               lambda url: url.startswith(redirect))
        params = urllib.parse.parse_qs(urllib.parse.urlparse(callback).query)
        if params.get("state") != [state] or not params.get("code"):
            raise RuntimeError(f"PKCE did not return a code (path={urllib.parse.urlparse(callback).path}, error={params.get('error')})")
        status, _, raw = fetch(found["metadata"]["token_endpoint"], urllib.parse.urlencode({
            "grant_type": "authorization_code", "client_id": client_id, "code": params["code"][0],
            "redirect_uri": redirect, "code_verifier": verifier, "resource": resource}).encode(),
            {"Content-Type": "application/x-www-form-urlencoded"}, "POST")
        if status != 200:
            raise RuntimeError(f"PKCE token exchange {status}: {raw!r}")
        return json.loads(raw)["access_token"]


class Management:
    """Short-lived Logto Management token; secrets never enter reports."""
    def __init__(self, issuer):
        self.base = issuer.rsplit("/oidc", 1)[0]
        with open(os.path.expanduser("~/.config/thegram-vault/logto-apps.json")) as file:
            app = json.load(file)["applications"]["management"]
        basic = base64.b64encode(f"{app['clientId']}:{app['clientSecret']}".encode()).decode()
        status, _, raw = fetch(self.base + "/oidc/token", urllib.parse.urlencode({
            "grant_type": "client_credentials", "resource": "https://default.logto.app/api", "scope": "all"}).encode(),
            {"Authorization": "Basic " + basic, "Content-Type": "application/x-www-form-urlencoded"}, "POST")
        if status != 200:
            raise RuntimeError(f"Management token {status}")
        self.token = json.loads(raw)["access_token"]

    def request(self, method, path, body=None):
        status, _, raw = fetch(self.base + path, None if body is None else json.dumps(body).encode(),
                               {"Authorization": "Bearer " + self.token, "Content-Type": "application/json"}, method)
        if status not in (200, 201, 204):
            raise RuntimeError(f"Management {method} {path} {status}: {raw!r}")
        return json.loads(raw) if raw else None

