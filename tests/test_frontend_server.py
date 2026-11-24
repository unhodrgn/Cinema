"""T1: the standard-library frontend server (frontend/server.py): files, headers, safety."""

import importlib.util
import os
import threading
from pathlib import Path

import pytest

from helpers import raw_request

FRONTEND_DIR = Path(__file__).resolve().parents[1] / "frontend"

# frontend/server.py is a standalone program, not part of the ``app`` package: load it by path.
_spec = importlib.util.spec_from_file_location("frontend_server", FRONTEND_DIR / "server.py")
server_module = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(server_module)

API = "http://127.0.0.1:5000"


def settings(**overrides):
    values = {"host": "127.0.0.1", "port": 0, "api_base_url": API}
    values.update(overrides)
    return server_module.Settings(**values)


def run(root=FRONTEND_DIR, **overrides):
    server = server_module.create_server(settings(**overrides), root=root)
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    return server, thread


@pytest.fixture(scope="module")
def live():
    server, thread = run()
    try:
        yield server
    finally:
        server.shutdown()
        server.server_close()
        thread.join(timeout=5)


def get(live, target, method="GET", headers=None):
    return raw_request(live.server_port, method, target, headers=headers)


# --- serving files ----------------------------------------------------------------------


def test_the_index_page_is_served_at_the_root_and_by_name(live):
    for target in ("/", "/index.html", "/?x=1", "/#frag"):
        status, headers, body = get(live, target)
        assert status == 200, target
        assert headers["content-type"] == "text/html; charset=utf-8"
        assert b"Cinema Reservation" in body
        assert int(headers["content-length"]) == len(body)


@pytest.mark.parametrize(
    "target, content_type",
    [
        ("/css/style.css", "text/css; charset=utf-8"),
        ("/js/api.js", "text/javascript; charset=utf-8"),
        ("/js/ui.js", "text/javascript; charset=utf-8"),
        ("/js/pages/index.js", "text/javascript; charset=utf-8"),
        ("/images/posters/exhuma.jpg", "image/jpeg"),
        ("/fonts/bebas-neue-latin-400-normal.woff2", "font/woff2"),
        ("/fonts/inter-latin-400-normal.woff2", "font/woff2"),
        ("/fonts/LICENSE-inter.txt", "text/plain; charset=utf-8"),
    ],
)
def test_static_assets_have_the_right_content_type(live, target, content_type):
    status, headers, body = get(live, target)

    assert status == 200
    assert headers["content-type"] == content_type
    assert len(body) > 0


def test_poster_jpg_files_are_real_jpegs_with_nosniff(live):
    for name in ("jjk-0", "jjk-hidden-inventory", "jjk-execution", "20th-century-girl", "exhuma", "godzilla-x-kong"):
        status, headers, body = get(live, f"/images/posters/{name}.jpg")
        assert status == 200 and body[:3] == b"\xff\xd8\xff", name
        assert headers["content-type"] == "image/jpeg" and headers["x-content-type-options"] == "nosniff"
        assert 0 < len(body) <= 200 * 1024, name  # "reasonably small"
    status, headers, body = get(live, "/images/posters/exhuma.jpg", method="HEAD")
    assert status == 200 and headers["content-type"] == "image/jpeg" and body == b""


def test_woff2_fonts_are_real_woff2_files(live):
    status, _, body = get(live, "/fonts/bebas-neue-latin-400-normal.woff2")
    assert status == 200 and body[:4] == b"wOF2"


def test_images_of_other_types_are_still_not_served(live):
    for target in ("/images/posters/exhuma.gif", "/images/posters/exhuma.jpg.bak", "/images/posters/exhuma.svg"):
        assert get(live, target)[0] == 404, target


def test_head_returns_the_headers_without_a_body(live):
    status, headers, body = get(live, "/index.html", method="HEAD")

    assert status == 200
    assert body == b""
    assert int(headers["content-length"]) > 0


def test_config_js_is_generated_from_the_api_base_url(live):
    status, headers, body = get(live, "/config.js")

    assert status == 200
    assert headers["content-type"] == "text/javascript; charset=utf-8"
    assert headers["cache-control"] == "no-store"
    assert body.decode() == 'window.APP_CONFIG = Object.freeze({"apiBaseUrl": "http://127.0.0.1:5000"});\n'
    assert not (FRONTEND_DIR / "config.js").exists(), "config.js must be generated, not a file"


def test_config_js_follows_the_environment_setting():
    server, thread = run(api_base_url="http://192.168.0.10:5000")
    try:
        _, _, body = raw_request(server.server_port, "GET", "/config.js")
    finally:
        server.shutdown()
        server.server_close()
        thread.join(timeout=5)

    assert b"http://192.168.0.10:5000" in body


# --- headers ----------------------------------------------------------------------------


def test_every_response_carries_the_security_headers(live):
    for target, method in (("/index.html", "GET"), ("/config.js", "GET"), ("/missing", "GET"),
                           ("/index.html", "POST"), ("/index.html", "HEAD")):
        _, headers, _ = get(live, target, method=method)
        assert headers["x-content-type-options"] == "nosniff", (target, method)
        assert headers["referrer-policy"] == "no-referrer"
        assert headers["x-frame-options"] == "DENY"
        assert "content-security-policy" in headers
        assert "geolocation=()" in headers["permissions-policy"]


def test_the_csp_allows_only_this_server_and_the_api(live):
    _, headers, _ = get(live, "/index.html")
    policy = {d.split(" ", 1)[0]: d.split(" ", 1)[1] if " " in d else "" for d in headers["content-security-policy"].split("; ")}

    assert policy["default-src"] == "'self'"
    assert policy["script-src"] == "'self'"
    assert policy["style-src"] == "'self'"
    assert policy["connect-src"] == f"'self' {API}"
    assert policy["object-src"] == "'none'"
    assert policy["base-uri"] == "'none'"
    assert policy["form-action"] == "'none'"
    assert policy["frame-ancestors"] == "'none'"
    text = headers["content-security-policy"]
    assert "unsafe-inline" not in text and "unsafe-eval" not in text and "*" not in text


def test_the_server_does_not_announce_its_python_version(live):
    _, headers, _ = get(live, "/index.html")

    assert headers["server"] == "CinemaFrontend"


# --- methods ----------------------------------------------------------------------------


@pytest.mark.parametrize("method", ["POST", "PUT", "PATCH", "DELETE", "OPTIONS", "TRACE"])
def test_only_get_and_head_are_allowed(live, method):
    status, headers, body = get(live, "/index.html", method=method)

    assert status == 405
    assert headers["allow"] == "GET, HEAD"
    assert body == b"405 Method Not Allowed\n"


def test_an_unknown_method_is_refused_without_an_html_page(live):
    status, headers, body = get(live, "/index.html", method="BREW")

    assert status in (405, 501)
    assert headers["content-type"].startswith("text/plain")
    assert b"<" not in body


# --- path safety ------------------------------------------------------------------------

TRAVERSAL_AND_HIDDEN_TARGETS = [
    "/../server.py",
    "/..%2fserver.py",
    "/%2e%2e/server.py",
    "/%2E%2E/%2E%2E/app/config.py",
    "/..%5cserver.py",
    "/%5c..%5cserver.py",
    "/css/../../app/config.py",
    "/js/%2e%2e/%2e%2e/app/__init__.py",
    "/css/%2e%2e%2f%2e%2e%2fapp/config.py",
    "/%252e%252e/server.py",  # double encoding stays literal after one decode
    "/%00",
    "/index.html%00.css",
    "/css/style.css%00.py",
    "/C:/Windows/win.ini",
    "/css/C:style.css",
    "/index.html::$DATA",
    "/server.py",
    "/SERVER.PY",
    "/server.py.",
    "/server.py%20",
    "/package.json",
    "/tests/api.test.js",
    "/tests/",
    "/Tests/ui.test.js",
    "/node_modules/x.js",
    "/.env",
    "/.git/config",
    "/js/.hidden.js",
    "//etc/passwd",
    "///server.py",
    "/js/../server.py",
    "http://evil.example/index.html",
    "/index.html/../../server.py",
]


@pytest.mark.parametrize("target", TRAVERSAL_AND_HIDDEN_TARGETS)
def test_traversal_and_hidden_files_are_never_served(live, target):
    status, _, body = get(live, target)

    assert status == 404
    assert body == b"404 Not Found\n"
    assert b"import " not in body and b"def " not in body


def test_directories_are_not_listed(live):
    for target in ("/css", "/css/", "/js", "/js/", "/js/pages/"):
        status, _, body = get(live, target)
        assert status == 404, target
        assert b"style.css" not in body and b"api.js" not in body


def test_error_pages_never_echo_the_request(live):
    status, headers, body = get(live, "/%3Cscript%3Ealert(1)%3C/script%3E")

    assert status == 404
    assert headers["content-type"] == "text/plain; charset=utf-8"
    assert b"script" not in body and b"alert" not in body


def test_a_malformed_request_line_gets_a_plain_text_error(live):
    import socket

    with socket.create_connection(("127.0.0.1", live.server_port), timeout=5) as sock:
        sock.sendall(b"NONSENSE\r\n\r\n")
        data = sock.recv(4096)

    # A one-word request line is HTTP/0.9-style: the server answers with the bare body.
    assert data.startswith((b"HTTP/1.", b"400 Bad Request"))
    assert b"<html" not in data.lower() and b"<body" not in data.lower()


def test_an_overlong_request_target_is_refused(live):
    status, _, body = get(live, "/" + "a" * 70000)

    assert status in (404, 414)
    assert b"<html" not in body.lower()


# --- a private root: allow-list and links -----------------------------------------------


@pytest.fixture
def private_root(tmp_path):
    root = tmp_path / "site"
    root.mkdir()
    (root / "index.html").write_text("<!doctype html><title>t</title>", encoding="utf-8")
    for name, text in {
        "page.html": "<p>x</p>", "a.css": "a{}", "a.js": "1", "notes.txt": "n", "x.ico": "i",
        "run.py": "print(1)", "data.json": "{}", "key.pem": "secret", "page.php": "<?php", "noext": "n",
        "evil.svg": "<svg/>", "x.mjs": "1",
    }.items():
        (root / name).write_text(text, encoding="utf-8")
    secret = tmp_path / "outside-secret.html"
    secret.write_text("TOP SECRET", encoding="utf-8")
    return root, secret


def test_only_allow_listed_extensions_are_served(private_root):
    root, _ = private_root
    server, thread = run(root=root)
    try:
        served = {name: raw_request(server.server_port, "GET", f"/{name}")[0]
                  for name in ("page.html", "a.css", "a.js", "notes.txt", "x.ico",
                               "run.py", "data.json", "key.pem", "page.php", "noext", "evil.svg", "x.mjs")}
    finally:
        server.shutdown()
        server.server_close()
        thread.join(timeout=5)

    assert {name for name, status in served.items() if status == 200} == {
        "page.html", "a.css", "a.js", "notes.txt", "x.ico"}


def test_a_symbolic_link_out_of_the_directory_is_not_followed(private_root):
    root, secret = private_root
    try:
        os.symlink(secret, root / "leak.html")
        os.symlink(secret.parent, root / "leakdir", target_is_directory=True)
    except (OSError, NotImplementedError):
        pytest.skip("this system does not allow creating symbolic links")
    server, thread = run(root=root)
    try:
        results = [raw_request(server.server_port, "GET", target)
                   for target in ("/leak.html", "/leakdir/outside-secret.html")]
    finally:
        server.shutdown()
        server.server_close()
        thread.join(timeout=5)

    for status, _, body in results:
        assert status == 404
        assert b"TOP SECRET" not in body


def test_a_link_to_a_disallowed_extension_inside_the_root_is_not_served(private_root):
    root, _ = private_root
    try:
        os.symlink(root / "run.py", root / "innocent.html")
    except (OSError, NotImplementedError):
        pytest.skip("this system does not allow creating symbolic links")
    server, thread = run(root=root)
    try:
        status, _, body = raw_request(server.server_port, "GET", "/innocent.html")
    finally:
        server.shutdown()
        server.server_close()
        thread.join(timeout=5)

    assert status == 404 and b"print(1)" not in body


# --- settings ---------------------------------------------------------------------------


def test_defaults():
    s = server_module.read_settings({})

    assert (s.host, s.port, s.api_base_url) == ("127.0.0.1", 8080, "http://localhost:5000")


def test_settings_from_the_environment_and_blank_values():
    s = server_module.read_settings(
        {"FRONTEND_HOST": "0.0.0.0", "FRONTEND_PORT": "9090", "API_BASE_URL": "HTTP://192.168.0.10:5000/"}
    )
    assert (s.host, s.port, s.api_base_url) == ("0.0.0.0", 9090, "http://192.168.0.10:5000")

    blank = server_module.read_settings({"FRONTEND_HOST": " ", "FRONTEND_PORT": "", "API_BASE_URL": ""})
    assert (blank.host, blank.port, blank.api_base_url) == ("127.0.0.1", 8080, "http://localhost:5000")


@pytest.mark.parametrize(
    "environ",
    [
        {"FRONTEND_PORT": "0"},
        {"FRONTEND_PORT": "70000"},
        {"FRONTEND_PORT": "abc"},
        {"FRONTEND_PORT": "-1"},
        {"FRONTEND_HOST": "bad host"},
        {"FRONTEND_HOST": "a/b"},
        {"API_BASE_URL": "*"},
        {"API_BASE_URL": "localhost:5000"},
        {"API_BASE_URL": "ftp://example.org"},
        {"API_BASE_URL": "http://example.org/api"},
        {"API_BASE_URL": "http://example.org?x=1"},
        {"API_BASE_URL": "http://user@example.org"},
        {"API_BASE_URL": "javascript:alert(1)"},
    ],
)
def test_invalid_settings_are_rejected(environ):
    with pytest.raises(server_module.SettingsError):
        server_module.read_settings(environ)


def test_the_csp_helper_embeds_only_the_normalized_api_origin():
    assert "connect-src 'self' https://api.example.org" in server_module.content_security_policy("https://api.example.org")


def test_the_server_never_imports_backend_code():
    import ast

    tree = ast.parse((FRONTEND_DIR / "server.py").read_text(encoding="utf-8"))
    imported = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            imported.update(alias.name.split(".")[0] for alias in node.names)
        elif isinstance(node, ast.ImportFrom):
            imported.add((node.module or "").split(".")[0])

    assert imported.isdisjoint({"app", "flask", "werkzeug", "psycopg2", "sqlalchemy", "dotenv", "tests"})
    # standard library only
    import sys

    assert imported <= set(sys.stdlib_module_names)


@pytest.mark.skipif(os.name != "nt", reason="directory junctions are a Windows feature")
def test_a_directory_junction_out_of_the_root_is_not_followed(private_root):
    import subprocess

    root, secret = private_root
    result = subprocess.run(
        ["cmd", "/c", "mklink", "/J", str(root / "junction"), str(secret.parent)],
        capture_output=True, text=True,
    )
    if result.returncode != 0:
        pytest.skip(f"could not create a junction: {result.stdout.strip() or result.stderr.strip()}")
    server, thread = run(root=root)
    try:
        status, _, body = raw_request(server.server_port, "GET", "/junction/outside-secret.html")
    finally:
        server.shutdown()
        server.server_close()
        thread.join(timeout=5)
        os.rmdir(root / "junction")  # removes the junction only, never its target

    assert status == 404
    assert b"TOP SECRET" not in body
