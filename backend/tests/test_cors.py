"""T1 / Spike B: exact-origin CORS for the independent frontend."""

import pytest
from flask import request

from app import create_app
from app.core.config import ConfigError, DevelopmentConfig
from app.core.cors import OriginError, normalize_origin, parse_origin_list
from app.core.errors import UNAUTHORIZED, AppError

FRONTEND = "http://localhost:8080"
LAN_FRONTEND = "http://192.168.0.10:8080"
EVIL = "http://evil.example"


def make_app(origins=f"{FRONTEND},{LAN_FRONTEND}"):
    overrides = {"CORS_ALLOWED_ORIGINS": origins} if origins is not None else {}
    app = create_app("testing", overrides)

    @app.post("/t/write")
    def write():
        request.get_data()  # Werkzeug enforces MAX_CONTENT_LENGTH only when the body is read
        return {"ok": True}

    @app.get("/t/denied")
    def denied():
        raise AppError(UNAUTHORIZED)

    return app


@pytest.fixture
def client():
    return make_app().test_client()


def preflight(client, origin, method="GET", path="/health", headers=None):
    request_headers = {"Origin": origin, "Access-Control-Request-Method": method}
    request_headers.update(headers or {})
    return client.options(path, headers=request_headers)


def allow_origin(response):
    return response.headers.get("Access-Control-Allow-Origin")


# --- normalization ----------------------------------------------------------------------


@pytest.mark.parametrize(
    "value, expected",
    [
        ("http://localhost:8080", "http://localhost:8080"),
        ("HTTP://LocalHost:8080/", "http://localhost:8080"),
        ("http://localhost:80", "http://localhost"),
        ("https://example.org:443", "https://example.org"),
        ("https://example.org:8443", "https://example.org:8443"),
        ("http://192.168.0.10:8080", "http://192.168.0.10:8080"),
        ("http://[::1]:8080", "http://[::1]:8080"),
    ],
)
def test_origins_are_normalized_like_the_browser_serializes_them(value, expected):
    assert normalize_origin(value) == expected


@pytest.mark.parametrize(
    "value",
    [
        "*",
        "http://*.example.org",
        "https://*",
        "",
        "   ",
        "localhost:8080",
        "ftp://example.org",
        "file:///tmp",
        "http://",
        "http://example.org/path",
        "http://example.org?x=1",
        "http://example.org#frag",
        "http://user@example.org",
        "http://example.org:notaport",
        "http://example.org:99999",
        "null",
    ],
)
def test_invalid_origins_are_rejected(value):
    with pytest.raises(OriginError):
        normalize_origin(value)


def test_origin_lists_ignore_blanks_and_duplicates_and_keep_order():
    assert parse_origin_list(f" {LAN_FRONTEND} , ,{FRONTEND},{LAN_FRONTEND}/") == (
        LAN_FRONTEND,
        FRONTEND,
    )
    assert parse_origin_list(None) == () and parse_origin_list("") == ()
    assert parse_origin_list([FRONTEND]) == (FRONTEND,)


def test_one_bad_entry_rejects_the_whole_list():
    with pytest.raises(OriginError):
        parse_origin_list(f"{FRONTEND},*")


def test_the_app_refuses_to_start_with_a_wildcard_origin():
    with pytest.raises(OriginError):
        create_app("testing", {"CORS_ALLOWED_ORIGINS": "*"})


def test_environment_configuration_reports_bad_origins_without_starting(monkeypatch):
    env = {"SECRET_KEY": "a-secret-key-with-enough-length", "DB_NAME": "x", "DB_USER": "y"}
    with pytest.raises(ConfigError, match="CORS_ALLOWED_ORIGINS"):
        DevelopmentConfig(dict(env, CORS_ALLOWED_ORIGINS=f"{FRONTEND},*"))
    cfg = DevelopmentConfig(dict(env, CORS_ALLOWED_ORIGINS=f"{FRONTEND}, {LAN_FRONTEND}/"))
    assert cfg.CORS_ALLOWED_ORIGINS == (FRONTEND, LAN_FRONTEND)
    assert DevelopmentConfig(env).CORS_ALLOWED_ORIGINS == ()


# --- simple requests --------------------------------------------------------------------


def test_an_allowed_origin_gets_its_own_origin_back(client):
    response = client.get("/health", headers={"Origin": FRONTEND})

    assert response.status_code == 200
    assert allow_origin(response) == FRONTEND
    assert "Origin" in response.headers["Vary"]
    assert "Access-Control-Allow-Credentials" not in response.headers


def test_each_configured_origin_is_echoed_individually_never_a_list_or_wildcard(client):
    assert allow_origin(client.get("/health", headers={"Origin": LAN_FRONTEND})) == LAN_FRONTEND
    assert allow_origin(client.get("/health", headers={"Origin": FRONTEND})) == FRONTEND


@pytest.mark.parametrize(
    "origin",
    [
        EVIL,
        "http://localhost:8081",  # other port
        "https://localhost:8080",  # other scheme
        "http://localhost",  # default port is a different origin
        "http://localhost.evil.example:8080",
        "http://evil.example/http://localhost:8080",
        "null",
        "",
        "*",
    ],
)
def test_other_origins_get_no_cors_permission(client, origin):
    response = client.get("/health", headers={"Origin": origin})

    assert response.status_code == 200  # the server still answers; the browser enforces CORS
    assert allow_origin(response) is None
    assert not any(name.lower().startswith("access-control-") for name, _ in response.headers)
    assert "Origin" in response.headers["Vary"]


def test_requests_without_an_origin_get_no_cors_headers_but_still_vary(client):
    response = client.get("/health")

    assert allow_origin(response) is None
    assert "Origin" in response.headers["Vary"]


def test_error_responses_carry_the_allowed_origin(client):
    for response in (
        client.get("/no/such/path", headers={"Origin": FRONTEND}),  # 404 from the JSON handler
        client.post("/health", headers={"Origin": FRONTEND}),  # 405 from Werkzeug
        client.get("/t/denied", headers={"Origin": FRONTEND}),  # AppError (401)
        client.get("/api/missing", headers={"Origin": FRONTEND}),
    ):
        assert response.status_code in (401, 404, 405)
        assert response.mimetype == "application/json"
        assert allow_origin(response) == FRONTEND


def test_error_responses_of_other_origins_carry_nothing(client):
    for response in (
        client.get("/no/such/path", headers={"Origin": EVIL}),
        client.post("/health", headers={"Origin": EVIL}),
        client.get("/t/denied", headers={"Origin": EVIL}),
    ):
        assert allow_origin(response) is None


def test_oversized_request_errors_are_readable_by_the_frontend(client):
    response = client.post(
        "/t/write",
        data=b"x" * (70 * 1024),
        headers={"Origin": FRONTEND, "Content-Type": "application/json"},
    )

    assert response.status_code == 413
    assert allow_origin(response) == FRONTEND


def test_without_an_allow_list_cors_is_completely_off():
    client = make_app(origins=None).test_client()

    for origin in (FRONTEND, EVIL):
        response = client.get("/health", headers={"Origin": origin})
        assert allow_origin(response) is None
        assert "Vary" not in response.headers
    assert allow_origin(preflight(client, FRONTEND)) is None


# --- preflight --------------------------------------------------------------------------


def test_an_allowed_origin_preflight_is_answered_with_the_permissions(client):
    response = preflight(
        client, FRONTEND, method="POST", path="/t/write",
        headers={"Access-Control-Request-Headers": "authorization, content-type"},
    )

    assert response.status_code == 204
    assert response.get_data() == b""
    assert allow_origin(response) == FRONTEND
    assert response.headers["Access-Control-Allow-Methods"] == "GET, POST, PUT, DELETE"
    assert response.headers["Access-Control-Allow-Headers"] == "Authorization, Content-Type"
    assert response.headers["Access-Control-Max-Age"] == "600"
    assert "Origin" in response.headers["Vary"]
    assert "Access-Control-Allow-Credentials" not in response.headers


def test_preflight_for_a_get_route_without_request_headers(client):
    response = preflight(client, FRONTEND, method="GET", path="/health")

    assert response.status_code == 204
    assert allow_origin(response) == FRONTEND


def test_a_denied_origin_preflight_gets_no_permission(client):
    response = preflight(client, EVIL, method="POST", path="/t/write")

    assert allow_origin(response) is None
    assert "Access-Control-Allow-Methods" not in response.headers
    assert response.status_code != 204


def test_preflight_for_an_unknown_path_gets_no_permission(client):
    response = preflight(client, FRONTEND, path="/api/does-not-exist")

    assert allow_origin(response) is None
    assert response.status_code == 404
    assert response.mimetype == "application/json"


@pytest.mark.parametrize("method", ["PATCH", "TRACE", "", "GE T"])
def test_preflight_for_a_method_the_api_does_not_use_gets_no_permission(client, method):
    response = preflight(client, FRONTEND, method=method, path="/t/write")

    assert allow_origin(response) is None
    assert "Access-Control-Allow-Methods" not in response.headers


def test_preflight_for_a_method_the_route_does_not_accept_gets_no_permission(client):
    # /health is GET-only; a browser asking to PUT there is refused before any request
    response = preflight(client, FRONTEND, method="PUT", path="/health")

    assert allow_origin(response) is None
    assert "Access-Control-Allow-Methods" not in response.headers


@pytest.mark.parametrize("requested", ["x-custom", "authorization, x-custom", "cookie"])
def test_preflight_requesting_other_headers_gets_no_permission(client, requested):
    response = preflight(
        client, FRONTEND, method="POST", path="/t/write",
        headers={"Access-Control-Request-Headers": requested},
    )

    assert allow_origin(response) is None
    assert "Access-Control-Allow-Headers" not in response.headers


def test_a_plain_options_request_is_not_treated_as_a_preflight(client):
    response = client.options("/health", headers={"Origin": FRONTEND})

    assert response.status_code == 200  # Flask's automatic OPTIONS answer
    assert "Access-Control-Allow-Methods" not in response.headers
    assert "GET" in response.headers["Allow"]


def test_credentials_are_never_allowed(client):
    for response in (
        client.get("/health", headers={"Origin": FRONTEND}),
        preflight(client, FRONTEND, method="POST", path="/t/write"),
    ):
        assert "Access-Control-Allow-Credentials" not in response.headers
        assert allow_origin(response) != "*"


# --- regression: a real preflight for EVERY route and EVERY method it supports ---------------
# Found in the browser check (Phase 5): a URL served by separate GET and POST rules was granted
# only for the first rule's method, so every admin write and GET /api/bookings failed in a browser.

import re  # noqa: E402

from app.core.cors import ALLOWED_METHODS  # noqa: E402


def _concrete(rule_text):
    return re.sub(r"<[^>]+>", "1", rule_text)


def _methods_by_path(app):
    """{concrete path: set of methods any rule for it accepts} for the API and health routes."""
    by_path = {}
    for rule in app.url_map.iter_rules():
        if rule.rule.startswith(("/api", "/health")):
            by_path.setdefault(_concrete(rule.rule), set()).update(rule.methods & set(ALLOWED_METHODS))
    return by_path


ROUTE_METHODS = sorted((path, method) for path, methods in _methods_by_path(make_app()).items() for method in methods)
WRITE_HEADERS = {"Access-Control-Request-Headers": "authorization,content-type"}


def test_the_route_list_covers_the_whole_api():
    paths = {path for path, _ in ROUTE_METHODS}
    assert "/api/admin/movies" in paths and "/api/bookings" in paths and "/api/admin/screenings/1" in paths
    assert {m for p, m in ROUTE_METHODS if p == "/api/admin/movies"} == {"GET", "POST"}
    assert {m for p, m in ROUTE_METHODS if p == "/api/bookings"} == {"GET", "POST"}
    assert {m for p, m in ROUTE_METHODS if p == "/api/admin/movies/1"} == {"GET", "PUT", "DELETE"}
    assert {m for p, m in ROUTE_METHODS if p == "/api/admin/screenings/1"} == {"GET", "PUT", "DELETE"}


@pytest.mark.parametrize("path, method", ROUTE_METHODS)
def test_a_preflight_is_granted_for_every_route_and_every_method_it_supports(client, path, method):
    response = preflight(client, FRONTEND, method, path, WRITE_HEADERS)

    assert response.status_code == 204
    assert allow_origin(response) == FRONTEND
    assert method in response.headers["Access-Control-Allow-Methods"].split(", ")


@pytest.mark.parametrize("path, method", ROUTE_METHODS)
def test_a_preflight_from_a_disallowed_origin_gets_no_permission_on_every_route(client, path, method):
    response = preflight(client, EVIL, method, path, WRITE_HEADERS)

    assert allow_origin(response) is None
    assert "Access-Control-Allow-Methods" not in response.headers


def test_a_preflight_for_a_method_the_url_does_not_accept_is_refused(client):
    by_path = _methods_by_path(client.application)
    checked = 0
    for path, accepted in by_path.items():
        for method in set(ALLOWED_METHODS) - accepted:
            response = preflight(client, FRONTEND, method, path, WRITE_HEADERS)
            assert allow_origin(response) is None, (path, method)
            assert "Access-Control-Allow-Methods" not in response.headers, (path, method)
            checked += 1
    assert checked > 20


@pytest.mark.parametrize("method", ["PATCH", "TRACE", ""])
def test_a_preflight_for_a_method_outside_the_allow_list_is_refused_on_every_route(client, method):
    for path in _methods_by_path(client.application):
        response = preflight(client, FRONTEND, method, path, WRITE_HEADERS)
        assert allow_origin(response) is None, (path, method)


def test_a_preflight_for_an_unknown_path_or_header_is_refused(client):
    assert allow_origin(preflight(client, FRONTEND, "POST", "/api/admin/nothing", WRITE_HEADERS)) is None
    odd_header = {"Access-Control-Request-Headers": "authorization,x-custom"}
    assert allow_origin(preflight(client, FRONTEND, "POST", "/api/admin/movies", odd_header)) is None
