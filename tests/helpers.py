"""Shared helpers for API tests."""

import json as jsonlib


def future_showtime_id(connection, min_hours=2):
    """A seeded screening that starts more than ``min_hours`` ahead and has no booking.

    The seed covers 14 days from the day it ran, so there is always one tomorrow; the
    margin keeps the test valid at any time of day. Ends the read-only transaction.
    """
    with connection.cursor() as cur:
        cur.execute(
            "SELECT showtime_id FROM showtimes s "
            "WHERE s.starts_at > now() + make_interval(hours => %s) "
            "AND NOT EXISTS (SELECT 1 FROM bookings b WHERE b.showtime_id = s.showtime_id) "
            "ORDER BY s.starts_at, s.showtime_id LIMIT 1",
            (min_hours,),
        )
        row = cur.fetchone()
    connection.rollback()
    if row is None:
        raise LookupError("no future screening without bookings in the seed data")
    return row[0]


class ApiClient:
    """A JSON-speaking wrapper around Flask's test client.

    * ``json=`` bodies are sent with ``Content-Type: application/json``.
    * ``token`` (set by ``set_token`` or by a later login helper) is sent as
      ``Authorization: Bearer ...``.
    * ``origin`` is sent as the ``Origin`` header, as a browser would for a request that
      comes from the independent frontend.

    A ``login()`` helper is deliberately absent: the authentication endpoints belong to T2.
    """

    def __init__(self, flask_client, origin=None):
        self.flask = flask_client
        self.origin = origin
        self.token = None

    def set_token(self, token):
        self.token = token
        return self

    def request(self, method, path, json=None, headers=None, **kwargs):
        merged = {}
        if self.origin:
            merged["Origin"] = self.origin
        if self.token:
            merged["Authorization"] = f"Bearer {self.token}"
        merged.update(headers or {})
        if json is not None:
            kwargs["data"] = jsonlib.dumps(json)
            merged.setdefault("Content-Type", "application/json")
        return self.flask.open(path, method=method, headers=merged, **kwargs)

    def get(self, path, **kwargs):
        return self.request("GET", path, **kwargs)

    def post(self, path, json=None, **kwargs):
        return self.request("POST", path, json=json, **kwargs)

    def put(self, path, json=None, **kwargs):
        return self.request("PUT", path, json=json, **kwargs)

    def delete(self, path, **kwargs):
        return self.request("DELETE", path, **kwargs)

    def options(self, path, **kwargs):
        return self.request("OPTIONS", path, **kwargs)


# --- live servers and real processes -----------------------------------------------------

import http.client
import socket
import time
import urllib.error
import urllib.request


def free_port():
    """A TCP port on 127.0.0.1 that is free right now (a tiny race is acceptable in tests)."""
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
        sock.bind(("127.0.0.1", 0))
        return sock.getsockname()[1]


def raw_request(port, method, target, headers=None, body=None, host="127.0.0.1"):
    """One HTTP request with the request target sent EXACTLY as given (no normalization).

    ``urllib`` and ``requests`` tidy ``..`` and encodings away; path-traversal tests need
    the raw form. Returns ``(status, headers dict with lower-case names, body bytes)``.
    """
    connection = http.client.HTTPConnection(host, port, timeout=5)
    try:
        connection.putrequest(method, target, skip_host=False, skip_accept_encoding=True)
        for name, value in (headers or {}).items():
            connection.putheader(name, value)
        connection.endheaders(body)
        response = connection.getresponse()
        return response.status, {k.lower(): v for k, v in response.getheaders()}, response.read()
    finally:
        connection.close()


def fetch(url, method="GET", headers=None, data=None, timeout=5):
    """``(status, headers dict with lower-case names, body bytes)``; HTTP errors are returned."""
    request = urllib.request.Request(url, method=method, headers=headers or {}, data=data)
    try:
        with urllib.request.urlopen(request, timeout=timeout) as response:
            return response.status, {k.lower(): v for k, v in response.getheaders()}, response.read()
    except urllib.error.HTTPError as error:
        return error.code, {k.lower(): v for k, v in error.headers.items()}, error.read()


def wait_until_serving(url, timeout=20.0):
    """Poll ``url`` until it answers with any HTTP status; raise ``TimeoutError`` otherwise."""
    deadline = time.monotonic() + timeout
    last = None
    while time.monotonic() < deadline:
        try:
            fetch(url, timeout=1)
            return
        except (urllib.error.URLError, ConnectionError, OSError) as error:
            last = error
            time.sleep(0.1)
    raise TimeoutError(f"{url} did not start serving: {last}")


def is_refused(port, host="127.0.0.1"):
    """True when nothing accepts connections on ``host:port``."""
    try:
        socket.create_connection((host, port), timeout=1).close()
    except OSError:
        return True
    return False


def load_frontend_server():
    """Load frontend/server.py by path (it is a standalone program, not part of ``app``)."""
    import importlib.util
    from pathlib import Path

    path = Path(__file__).resolve().parents[1] / "frontend" / "server.py"
    spec = importlib.util.spec_from_file_location("frontend_server", path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def wait_until_refused(port, timeout=10.0, host="127.0.0.1"):
    """Poll until nothing accepts connections on ``host:port``; raise ``TimeoutError`` otherwise."""
    deadline = time.monotonic() + timeout
    while time.monotonic() < deadline:
        if is_refused(port, host):
            return
        time.sleep(0.05)
    raise TimeoutError(f"{host}:{port} still accepts connections")
