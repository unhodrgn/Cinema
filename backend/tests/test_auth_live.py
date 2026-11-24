"""T2: authentication over real sockets: wire-level HTTP, and the frontend's own modules.

The API and the frontend server run as separate HTTP servers on separate ports (separate
origins). The browser is played by plain HTTP requests with an ``Origin`` header and by the
real ``frontend/js/api.js`` and ``auth.js`` running under Node (Node does not enforce CORS,
so CORS is asserted on the response headers). Needs a disposable PostgreSQL.
"""

import json
import os
import shutil
import subprocess
import uuid
from pathlib import Path

import pytest

from app.core import passwords
from helpers import fetch
from test_architecture_live import Stack

FRONTEND_DIR = Path(__file__).resolve().parents[2] / "frontend"
NODE = shutil.which("node")
PASSWORD = "Live-Test pw 1!"


def post(origin_api, path, body, frontend_origin, token=None):
    headers = {"Content-Type": "application/json", "Origin": frontend_origin}
    if token:
        headers["Authorization"] = f"Bearer {token}"
    status, response_headers, data = fetch(origin_api + path, method="POST", headers=headers,
                                           data=json.dumps(body).encode())
    return status, response_headers, (json.loads(data) if data else None)


def get(origin_api, path, frontend_origin, token=None):
    headers = {"Origin": frontend_origin}
    if token:
        headers["Authorization"] = f"Bearer {token}"
    status, response_headers, data = fetch(origin_api + path, headers=headers)
    return status, response_headers, (json.loads(data) if data else None)


def owner_execute(db, sql, params=()):
    connection = db.connect()
    try:
        with connection.cursor() as cur:
            cur.execute(sql, params)
        connection.commit()
    finally:
        connection.close()


def test_registration_login_and_role_authorization_over_real_http(fresh_db):
    admin_name, customer_name = f"admin_{uuid.uuid4().hex[:8]}", f"cust_{uuid.uuid4().hex[:8]}"
    with Stack(fresh_db.app_config()) as live:
        api, front = live.api_origin, live.frontend_origin
        # an administrator exists only because someone with database rights created one
        owner_execute(fresh_db, "INSERT INTO users(username, password_hash, role) VALUES (%s, %s, 'ADMIN')",
                      (admin_name, passwords.hash_password(PASSWORD)))

        # register: a role in the request is ignored
        status, headers, body = post(api, "/api/auth/register",
                                     {"username": customer_name, "password": PASSWORD, "role": "ADMIN"}, front)
        assert status == 201 and body["user"]["role"] == "CUSTOMER"
        assert headers["access-control-allow-origin"] == front and "set-cookie" not in headers

        # duplicate
        status, _, body = post(api, "/api/auth/register", {"username": customer_name, "password": "x"}, front)
        assert status == 409 and body["error"]["code"] == "duplicate_value"

        # login: wrong password and unknown account are indistinguishable
        wrong = post(api, "/api/auth/login", {"username": customer_name, "password": "nope"}, front)
        ghost = post(api, "/api/auth/login", {"username": "no_such_account", "password": "nope"}, front)
        assert wrong[0] == ghost[0] == 401 and wrong[2] == ghost[2]
        assert wrong[1]["access-control-allow-origin"] == front  # the 401 body is readable by the page

        # login ok, then /me with the Bearer token
        status, _, login = post(api, "/api/auth/login", {"username": customer_name, "password": PASSWORD}, front)
        assert status == 200 and login["user"]["role"] == "CUSTOMER"
        token = login["token"]
        assert get(api, "/api/auth/me", front)[0] == 401
        status, headers, me = get(api, "/api/auth/me", front, token)
        assert status == 200 and me["user"]["username"] == customer_name
        assert headers["access-control-allow-origin"] == front

        # a foreign origin gets the data but no permission to read it
        status, headers, _ = get(api, "/api/auth/me", "http://evil.example", token)
        assert status == 200 and "access-control-allow-origin" not in headers

        # a role change in the database applies to the very next request
        owner_execute(fresh_db, "UPDATE users SET role = 'ADMIN' WHERE username = %s", (customer_name,))
        assert get(api, "/api/auth/me", front, token)[2]["user"]["role"] == "ADMIN"
        owner_execute(fresh_db, "UPDATE users SET role = 'CUSTOMER' WHERE username = %s", (customer_name,))
        assert get(api, "/api/auth/me", front, token)[2]["user"]["role"] == "CUSTOMER"

        # the administrator logs in through the same endpoint
        status, _, admin_login = post(api, "/api/auth/login", {"username": admin_name, "password": PASSWORD}, front)
        assert status == 200 and admin_login["user"]["role"] == "ADMIN"

        # deleting the account ends the session on the next request
        owner_execute(fresh_db, "DELETE FROM users WHERE username = %s", (customer_name,))
        assert get(api, "/api/auth/me", front, token)[0] == 401

        # logout is public and stateless
        assert post(api, "/api/auth/logout", {}, front)[0] == 204

        # the frontend server serves the pages that use all this
        for page in ("/login.html", "/register.html"):
            status, headers, html = fetch(live.frontend_origin + page)
            assert status == 200 and b"/config.js" in html
            assert "connect-src 'self' " + live.api_origin in headers["content-security-policy"]


NODE_SCRIPT = """
import {{ ApiError, createApiClient, TOKEN_KEY }} from {api_module};
import {{ createAuth }} from {auth_module};

const data = new Map(Object.entries(JSON.parse(process.env.STORAGE ?? "{{}}")));
const storage = {{ getItem: (k) => (data.has(k) ? data.get(k) : null), setItem: (k, v) => void data.set(k, String(v)), removeItem: (k) => void data.delete(k) }};
const navigations = [];
let auth;
const api = createApiClient({{ baseUrl: process.env.API_BASE_URL, storage, onUnauthorized: (e) => auth.handleUnauthorized(e) }});
auth = createAuth({{ api, navigate: (u) => navigations.push(u), here: () => "/index.html" }});
const attempt = async (fn) => {{ try {{ return {{ ok: true, value: await fn() }}; }} catch (e) {{ return {{ ok: false, status: e.status, code: e.code, message: e.message, fields: e.fields, isApiError: e instanceof ApiError }}; }} }};
const out = {{}};
const phase = process.env.PHASE;
if (phase === "flow") {{
  const name = process.env.ACCOUNT, password = process.env.PASSWORD;
  out.registerInvalid = await attempt(() => auth.register("", ""));
  out.register = await attempt(() => auth.register(name, password));
  out.afterRegister = {{ token: storage.getItem(TOKEN_KEY) }};
  out.wrong = await attempt(() => auth.login(name, "wrong password"));
  out.ghost = await attempt(() => auth.login("no_such_account_x", "wrong password"));
  out.tokenAfterFailures = storage.getItem(TOKEN_KEY);
  out.login = await attempt(() => auth.login(name, password));
  out.hasToken = Boolean(storage.getItem(TOKEN_KEY));
  out.user = await attempt(() => auth.currentUser({{ refresh: true }}));
  out.token = storage.getItem(TOKEN_KEY);
  await auth.logout();
  out.tokenAfterLogout = storage.getItem(TOKEN_KEY);
  out.userAfterLogout = await attempt(() => auth.currentUser());
}} else if (phase === "stale") {{
  out.user = await attempt(() => auth.currentUser());
  out.tokenAfter = storage.getItem(TOKEN_KEY);
}}
out.navigations = navigations;
console.log(JSON.stringify(out));
"""


def run_node(api_origin, tmp_path, phase, **env):
    script = tmp_path / f"probe_{phase}.mjs"
    script.write_text(NODE_SCRIPT.format(api_module=json.dumps((FRONTEND_DIR / "js" / "api.js").as_uri()),
                                         auth_module=json.dumps((FRONTEND_DIR / "js" / "auth.js").as_uri())),
                      encoding="utf-8")
    result = subprocess.run([NODE, str(script)], capture_output=True, text=True, encoding="utf-8", errors="replace",
                            timeout=120, env={**os.environ, "API_BASE_URL": api_origin, "PHASE": phase, **env})
    assert result.returncode == 0, result.stderr[-2000:]
    return json.loads(result.stdout.strip().splitlines()[-1])


@pytest.mark.skipif(NODE is None, reason="Node.js is not installed (optional)")
def test_the_frontend_auth_modules_work_against_the_live_api(fresh_db, tmp_path):
    name = f"web_{uuid.uuid4().hex[:8]}"
    with Stack(fresh_db.app_config()) as live:
        flow = run_node(live.api_origin, tmp_path, "flow", ACCOUNT=name, PASSWORD=PASSWORD)

        assert flow["registerInvalid"]["code"] == "validation_error"
        assert set(flow["registerInvalid"]["fields"]) == {"username", "password"}
        assert flow["register"]["ok"] and flow["register"]["value"]["role"] == "CUSTOMER"
        assert flow["afterRegister"]["token"] is None, "registering does not log in"
        for failure in (flow["wrong"], flow["ghost"]):
            assert failure["isApiError"] and failure["status"] == 401 and failure["code"] == "invalid_credentials"
        assert flow["wrong"]["message"] == flow["ghost"]["message"] == "The account ID or password is incorrect."
        assert flow["tokenAfterFailures"] is None
        assert flow["login"]["ok"] and flow["hasToken"]
        assert flow["user"]["ok"] and flow["user"]["value"]["username"] == name
        assert flow["tokenAfterLogout"] is None and flow["userAfterLogout"]["value"] is None
        assert flow["navigations"] == [], "no redirect without a stale token"

        # Stale token: the account disappears; the next protected call returns to the login page
        status, _, login = post(live.api_origin, "/api/auth/login", {"username": name, "password": PASSWORD},
                                live.frontend_origin)
        assert status == 200
        owner_execute(fresh_db, "DELETE FROM users WHERE username = %s", (name,))
        stale = run_node(live.api_origin, tmp_path, "stale", STORAGE=json.dumps({"cinema.token": login["token"]}))

        assert stale["user"]["value"] is None
        assert stale["tokenAfter"] is None
        assert stale["navigations"] == ["/login.html?next=%2Findex.html"]
        # and the token never appeared in a URL the frontend navigated to
        assert login["token"] not in json.dumps(stale["navigations"])
