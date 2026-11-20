"""T1: frontend server and API running side by side on real sockets (in one test process).

The frontend server and the Flask API are separate HTTP servers on separate ports, i.e.
separate origins, exactly as in the intended deployment. The browser's part is played by
plain HTTP requests carrying an ``Origin`` header, and by the frontend's real ``api.js``
running under Node (Node does not enforce CORS, so CORS itself is asserted on the headers).
"""

import json
import os
import shutil
import subprocess
import threading
from pathlib import Path

import pytest
from werkzeug.serving import make_server

from app import create_app
from helpers import fetch, free_port, load_frontend_server

FRONTEND_DIR = Path(__file__).resolve().parents[1] / "frontend"
NODE = shutil.which("node")
server_module = load_frontend_server()


class Stack:
    """A frontend server and an API server, each in its own thread and on its own port."""

    def __init__(self, api_config):
        self.frontend_port = free_port()
        self.api_port = free_port()
        self.frontend_origin = f"http://127.0.0.1:{self.frontend_port}"
        self.api_origin = f"http://127.0.0.1:{self.api_port}"
        overrides = dict(api_config, CORS_ALLOWED_ORIGINS=self.frontend_origin)
        self.app = create_app("testing", overrides)
        self.api = make_server("127.0.0.1", self.api_port, self.app, threaded=True)
        self.frontend = server_module.create_server(
            server_module.Settings("127.0.0.1", self.frontend_port, self.api_origin)
        )
        self.threads = [
            threading.Thread(target=self.api.serve_forever, daemon=True),
            threading.Thread(target=self.frontend.serve_forever, daemon=True),
        ]

    def __enter__(self):
        for thread in self.threads:
            thread.start()
        return self

    def __exit__(self, *exc):
        self.api.shutdown()
        self.frontend.shutdown()
        self.frontend.server_close()
        self.api.server_close()
        for thread in self.threads:
            thread.join(timeout=5)


@pytest.fixture(scope="module")
def stack():
    with Stack({}) as running:  # no database configured: /health/db must report 503
        yield running


def browser_get(stack, path, origin=None):
    headers = {"Origin": origin or stack.frontend_origin}
    return fetch(stack.api_origin + path, headers=headers)


def test_the_two_servers_are_separate_origins_on_separate_ports(stack):
    assert stack.frontend_port != stack.api_port
    assert stack.frontend_origin != stack.api_origin


def test_the_frontend_serves_its_page_and_tells_the_browser_where_the_api_is(stack):
    status, headers, body = fetch(stack.frontend_origin + "/")
    assert status == 200 and b"Cinema Reservation" in body
    assert "connect-src 'self' " + stack.api_origin in headers["content-security-policy"]

    status, _, config = fetch(stack.frontend_origin + "/config.js")
    assert status == 200
    assert stack.api_origin in config.decode()


def test_the_frontend_can_call_health_on_the_api_across_origins(stack):
    status, headers, body = browser_get(stack, "/health")

    assert status == 200
    assert json.loads(body) == {"status": "ok"}
    assert headers["access-control-allow-origin"] == stack.frontend_origin
    assert "origin" in headers["vary"].lower()


def test_another_origin_gets_the_data_but_no_permission_to_read_it(stack):
    status, headers, _ = browser_get(stack, "/health", origin="http://evil.example")

    assert status == 200
    assert "access-control-allow-origin" not in headers


def test_a_real_preflight_is_granted_to_the_frontend_only(stack):
    request = {"Access-Control-Request-Method": "GET", "Access-Control-Request-Headers": "authorization"}

    status, headers, _ = fetch(stack.api_origin + "/health", method="OPTIONS",
                               headers={"Origin": stack.frontend_origin, **request})
    denied_status, denied_headers, _ = fetch(stack.api_origin + "/health", method="OPTIONS",
                                             headers={"Origin": "http://evil.example", **request})

    assert status == 204
    assert headers["access-control-allow-origin"] == stack.frontend_origin
    assert "authorization" in headers["access-control-allow-headers"].lower()
    assert "access-control-allow-origin" not in denied_headers
    assert denied_status != 204


def test_json_errors_cross_the_origin_boundary_readable(stack):
    for method, path, status, code in (
        ("GET", "/api/nope", 404, "not_found"),
        ("POST", "/health", 405, "method_not_allowed"),
    ):
        got, headers, body = fetch(stack.api_origin + path, method=method,
                                   headers={"Origin": stack.frontend_origin}, data=b"" if method == "POST" else None)
        assert got == status
        assert headers["content-type"] == "application/json"
        assert json.loads(body)["error"]["code"] == code
        assert headers["access-control-allow-origin"] == stack.frontend_origin


def test_the_database_state_is_reported_by_the_api_not_known_to_the_frontend(stack):
    status, headers, body = browser_get(stack, "/health/db")

    assert status == 503
    assert json.loads(body) == {"status": "unavailable", "database": "unavailable"}
    assert headers["access-control-allow-origin"] == stack.frontend_origin
    assert b"psycopg" not in body and b"password" not in body.lower()


def test_the_api_serves_no_pages_or_files(stack):
    for path in ("/", "/index.html", "/css/style.css", "/js/api.js", "/config.js", "/static/style.css"):
        status, headers, body = fetch(stack.api_origin + path)
        assert status == 404, path
        assert headers["content-type"] == "application/json"
        assert json.loads(body)["error"]["code"] == "not_found"


def test_the_frontend_server_has_no_api(stack):
    for path in ("/api", "/api/movies", "/health", "/health/db"):
        status, headers, body = fetch(stack.frontend_origin + path)
        assert status == 404, path
        assert headers["content-type"].startswith("text/plain")


# --- the real api.js against the live API (Node) ------------------------------------------

NODE_SCRIPT = """
import {{ createApiClient, ApiError }} from {api_module};

const api = createApiClient({{ baseUrl: process.env.API_BASE_URL }});
const outcome = async (promise) => {{
  try {{ return {{ ok: true, body: await promise }}; }}
  catch (error) {{
    return {{ ok: false, isApiError: error instanceof ApiError, status: error.status, code: error.code, body: error.body }};
  }}
}};
const result = {{
  health: await outcome(api.get("/health")),
  healthDb: await outcome(api.get("/health/db")),
  service: await outcome(api.get("/api")),
  missing: await outcome(api.get("/api/does-not-exist")),
  wrongMethod: await outcome(api.post("/health", {{}})),
}};
console.log(JSON.stringify(result));
"""


def run_api_js(api_origin, tmp_path):
    script = tmp_path / "probe.mjs"
    script.write_text(NODE_SCRIPT.format(api_module=json.dumps((FRONTEND_DIR / "js" / "api.js").as_uri())),
                      encoding="utf-8")
    result = subprocess.run([NODE, str(script)], capture_output=True, text=True, encoding="utf-8",
                            errors="replace", timeout=60, env={**os.environ, "API_BASE_URL": api_origin})
    assert result.returncode == 0, result.stderr[-2000:]
    return json.loads(result.stdout.strip().splitlines()[-1])


@pytest.mark.skipif(NODE is None, reason="Node.js is not installed (optional)")
def test_the_real_api_client_talks_to_the_live_api_without_a_database(stack, tmp_path):
    result = run_api_js(stack.api_origin, tmp_path)

    assert result["health"] == {"ok": True, "body": {"status": "ok"}}
    assert result["service"] == {"ok": True, "body": {"service": "cinema-reservation-api", "status": "ok"}}
    assert result["healthDb"]["isApiError"] and result["healthDb"]["status"] == 503
    assert result["healthDb"]["body"] == {"status": "unavailable", "database": "unavailable"}
    assert result["missing"]["isApiError"] and result["missing"]["code"] == "not_found"
    assert result["wrongMethod"]["isApiError"] and result["wrongMethod"]["code"] == "method_not_allowed"


@pytest.mark.skipif(NODE is None, reason="Node.js is not installed (optional)")
def test_the_real_api_client_sees_a_healthy_database(cinema_test_db, tmp_path):
    with Stack(cinema_test_db.app_config()) as running:
        result = run_api_js(running.api_origin, tmp_path)
        _, headers, body = browser_get(running, "/health/db")

    assert result["healthDb"] == {"ok": True, "body": {"status": "ok", "database": "ok"}}
    assert json.loads(body) == {"status": "ok", "database": "ok"}
    assert headers["access-control-allow-origin"] == running.frontend_origin
