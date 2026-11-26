"""SEC-01 & API-01: Active SQL Injection, XSS surface, and booking-capacity security tests."""

import ast
import re
import uuid
from pathlib import Path

import psycopg2
from psycopg2.extensions import TRANSACTION_STATUS_IDLE, TRANSACTION_STATUS_INTRANS
import pytest

import disposable_db
from app import create_app
from app.core import database, passwords, security
from app.core.errors import ValidationError
from app.schemas.booking import MAX_SEATS_PER_BOOKING, booking_request
from helpers import ApiClient
from time_travel import create_spare_room_screening

ROOT = Path(__file__).resolve().parents[2]
BACKEND_APP = ROOT / "backend" / "app"
FRONTEND_URL = "http://localhost:8080"
HASH = passwords.hash_password("sec-test-password-123")

SQLI_PAYLOADS = [
    "' OR '1'='1",
    "\" OR \"1\"=\"1",
    "admin'--",
    "'; DROP TABLE users; --",
    "1; SELECT pg_sleep(5)--",
    "1 UNION SELECT username, password_hash, role, null FROM users--",
    "') OR 1=1--",
    "BOOKED' OR '1'='1",
]

XSS_PAYLOADS = [
    "<script>window.__xss=1</script>",
    "<img src=x onerror=\"window.__xss=2\">",
    "<svg onload=\"window.__xss=3\">",
    "\"><script>alert(1)</script>",
]


# --------------------------------------------------------------------------------------
# Offline unit & static security checks (run without PostgreSQL)
# --------------------------------------------------------------------------------------


def test_all_backend_sql_execute_calls_avoid_user_input_interpolation():
    """Every cur.execute() in backend/app/ must avoid interpolating request/input variables."""
    for path in sorted(BACKEND_APP.rglob("*.py")):
        tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
        for node in ast.walk(tree):
            if (
                isinstance(node, ast.Call)
                and isinstance(node.func, ast.Attribute)
                and node.func.attr == "execute"
                and node.args
            ):
                sql_arg = node.args[0]
                if isinstance(sql_arg, ast.JoinedStr):
                    for value in sql_arg.values:
                        if isinstance(value, ast.FormattedValue):
                            assert isinstance(value.value, ast.Name), f"{path.name}: complex f-string SQL"
                            assert value.value.id.isupper(), (
                                f"{path.name}: non-constant SQL interpolation {value.value.id!r}"
                            )
                elif isinstance(sql_arg, ast.BinOp):
                    raise AssertionError(f"{path.name}: binary string operation in cur.execute()")


def test_booking_request_enforces_max_seat_count():
    assert MAX_SEATS_PER_BOOKING == 50
    screening_id, seat_ids = booking_request(
        {"screening_id": 1, "seat_ids": list(range(1, MAX_SEATS_PER_BOOKING + 1))}
    )
    assert screening_id == 1
    assert len(seat_ids) == MAX_SEATS_PER_BOOKING

    for bad_count in (MAX_SEATS_PER_BOOKING + 1, 200, 5000):
        with pytest.raises(ValidationError) as exc:
            booking_request({"screening_id": 1, "seat_ids": list(range(1, bad_count + 1))})
        assert "seat_ids" in exc.value.fields


def test_reserve_rejects_seats_above_room_capacity_and_handles_numeric_overflow(fake_app, fake_driver, monkeypatch):
    security.set_user_loader(
        fake_app, lambda uid: {"user_id": uid, "username": "cust", "role": "CUSTOMER"}
    )
    with fake_app.app_context():
        token, _ = security.issue_token(1)
    client = ApiClient(fake_app.test_client()).set_token(token)

    class CapacityCursor:
        def __init__(self, conn, capacity, overflow=False):
            self.conn = conn
            self.capacity = capacity
            self.overflow = overflow
            self._row = None

        def __enter__(self):
            return self

        def __exit__(self, *exc_info):
            self.close()
            return False

        def execute(self, sql, params=None):
            self.conn.status = TRANSACTION_STATUS_INTRANS
            if "FROM showtimes s" in sql:
                self._row = {"capacity": self.capacity}
            elif "create_booking(" in sql:
                if self.overflow:
                    err_cls = type("FakeDataError", (psycopg2.DataError,), {"pgcode": "22003"})
                    raise err_cls("numeric field overflow")
                self._row = {"booking_id": 1}

        def fetchone(self):
            return self._row

        def close(self):
            pass

    class CapacityConn:
        def __init__(self, capacity, overflow=False):
            self.capacity = capacity
            self.overflow = overflow
            self.closed = 0
            self.status = TRANSACTION_STATUS_IDLE
            self.events = []
            self.info = type("Info", (), {"transaction_status": property(lambda s: self.status)})()

        def cursor(self):
            return CapacityCursor(self, self.capacity, self.overflow)

        def commit(self):
            self.events.append("commit")
            self.status = TRANSACTION_STATUS_IDLE

        def rollback(self):
            self.events.append("rollback")
            self.status = TRANSACTION_STATUS_IDLE

        def close(self):
            self.events.append("close")
            self.closed = 1

    # Case 1: room capacity smaller than requested seat count (e.g. 5 seats requested, capacity 3)
    conn1 = CapacityConn(capacity=3)
    monkeypatch.setattr(psycopg2, "connect", lambda **kw: conn1)
    resp1 = client.post("/api/bookings", {"screening_id": 10, "seat_ids": [1, 2, 3, 4, 5]})
    assert resp1.status_code == 400
    assert resp1.get_json()["error"]["code"] == "validation_error"
    assert "3 seats" in resp1.get_json()["error"]["fields"]["seat_ids"]
    assert "commit" not in conn1.events and "rollback" in conn1.events

    # Case 2: defensive 22003 numeric overflow caught as 400 validation_error, never 500
    conn2 = CapacityConn(capacity=50, overflow=True)
    monkeypatch.setattr(psycopg2, "connect", lambda **kw: conn2)
    resp2 = client.post("/api/bookings", {"screening_id": 10, "seat_ids": [1, 2]})
    assert resp2.status_code == 400
    assert resp2.get_json()["error"]["code"] == "validation_error"
    assert "seat_ids" in resp2.get_json()["error"]["fields"]
    assert "commit" not in conn2.events and "rollback" in conn2.events


def test_api_rejects_sqli_and_xss_in_identifiers_and_headers_without_db(fake_app):
    security.set_user_loader(
        fake_app, lambda uid: {"user_id": uid, "username": "cust", "role": "CUSTOMER"}
    )
    with fake_app.app_context():
        token, _ = security.issue_token(1)
    client = ApiClient(fake_app.test_client()).set_token(token)

    for payload in SQLI_PAYLOADS + XSS_PAYLOADS:
        # Malformed Authorization headers -> 401 without echoing payload
        resp = ApiClient(fake_app.test_client()).get(
            "/api/bookings", headers={"Authorization": f"Bearer {payload}"}
        )
        assert resp.status_code == 401
        assert payload not in resp.get_data(as_text=True)

        # Invalid screening / booking booking payload -> 400 without 500
        resp_book = client.post("/api/bookings", {"screening_id": payload, "seat_ids": [payload]})
        assert resp_book.status_code == 400
        assert resp_book.get_json()["error"]["code"] == "validation_error"
        assert payload not in resp_book.get_data(as_text=True)

        # Path ids -> 404 JSON envelope, never 500
        for path in (f"/api/movies/{payload}", f"/api/screenings/{payload}", f"/api/bookings/{payload}"):
            r = client.get(path)
            assert r.status_code == 404
            assert r.mimetype == "application/json"
            assert payload not in r.get_data(as_text=True)


def test_booking_confirmation_pages_enforce_sync_locks_and_loading_states():
    react_booking = (ROOT / "frontend/src/pages/BookingPage.tsx").read_text(encoding="utf-8")
    assert "useRef(false)" in react_booking
    assert "inFlight.current" in react_booking
    assert 'aria-busy={busy || undefined}' in react_booking
    assert '"Booking…"' in react_booking

    legacy_seats = (ROOT / "frontend/js/pages/seats.js").read_text(encoding="utf-8")
    assert "isSubmitting" in legacy_seats
    assert legacy_seats.index("bookButton.disabled = true") < legacy_seats.index("await pageUser(")
    assert '"Booking…"' in legacy_seats


# --------------------------------------------------------------------------------------
# Live PostgreSQL Active SQL Injection & Stored XSS tests
# --------------------------------------------------------------------------------------


@pytest.fixture(scope="module")
def sec_db(cinema_template_db):
    with disposable_db.clone_database(cinema_template_db) as clone:
        yield clone


@pytest.fixture(scope="module")
def sec_app(sec_db):
    return create_app("testing", dict(sec_db.app_config(), CORS_ALLOWED_ORIGINS=FRONTEND_URL))


def _make_account(app, db, role, username=None):
    uname = username or f"{role.lower()}_{uuid.uuid4().hex[:8]}"
    conn = db.connect()
    try:
        with conn.cursor() as cur:
            cur.execute(
                "INSERT INTO users(username, password_hash, role) VALUES (%s, %s, %s) RETURNING user_id",
                (uname, HASH, role),
            )
            uid = cur.fetchone()[0]
        conn.commit()
    finally:
        conn.close()
    with app.app_context():
        token, _ = security.issue_token(uid)
    return uid, uname, ApiClient(app.test_client(), origin=FRONTEND_URL).set_token(token)


def test_active_sql_injection_across_auth_catalog_booking_and_admin_endpoints(sec_app, sec_db):
    _, _, admin_client = _make_account(sec_app, sec_db, "ADMIN")
    _, _, cust_client = _make_account(sec_app, sec_db, "CUSTOMER")
    anon_client = ApiClient(sec_app.test_client(), origin=FRONTEND_URL)

    conn = sec_db.connect()
    try:
        spare = create_spare_room_screening(conn, starts_in_hours=48)
    finally:
        conn.close()
    sid = spare["showtime_id"]

    for idx, payload in enumerate(SQLI_PAYLOADS):
        # 1. Auth login never bypasses password check
        login_resp = anon_client.post("/api/auth/login", {"username": payload, "password": "x"})
        assert login_resp.status_code == 401
        assert login_resp.get_json()["error"]["code"] == "invalid_credentials"

        # 2. Registration rejects unsupported account-ID syntax
        reg_name = f"sqli_{idx}_{payload}"[:60]
        reg_resp = anon_client.post("/api/auth/register", {"username": reg_name, "password": "pw"})
        assert reg_resp.status_code == 400
        assert "username" in reg_resp.get_json()["error"]["fields"]

        # 3. Catalog & seat endpoints reject SQLi query/path params with 400/404, never 500
        assert anon_client.get("/api/screenings", query_string={"date": payload}).status_code == 400
        assert anon_client.get("/api/screenings", query_string={"movie_id": payload}).status_code == 400
        assert anon_client.get(f"/api/screenings/{payload}/seats").status_code == 404

        # 4. Booking endpoints reject SQLi identifiers cleanly
        b_resp = cust_client.post("/api/bookings", {"screening_id": payload, "seat_ids": [spare["seat_ids"][0]]})
        assert b_resp.status_code == 400
        assert cust_client.post(f"/api/bookings/{payload}/pay", {}).status_code == 404
        assert cust_client.post(f"/api/bookings/{payload}/cancel", {}).status_code == 404

        # 5. Admin booking filters reject SQLi in status, screening_id, user_id
        for q in ({"status": payload}, {"screening_id": payload}, {"user_id": payload}):
            f_resp = admin_client.get("/api/admin/bookings", query_string=q)
            assert f_resp.status_code == 400
            assert f_resp.get_json()["error"]["code"] == "validation_error"

        # 6. Admin movie creation stores SQLi strings safely as data without executing SQL
        m_resp = admin_client.post(
            "/api/admin/movies",
            {"title": payload, "genre": payload, "rating": payload[:50], "synopsis": payload, "duration_minutes": 95},
        )
        assert m_resp.status_code == 201
        assert m_resp.get_json()["movie"]["title"] == payload

        # 7. Admin screening creation rejects SQLi in numeric/date/price fields with 400
        s_resp = admin_client.post(
            "/api/admin/screenings",
            {"movie_id": payload, "room_id": payload, "starts_at": payload, "ticket_price": payload},
        )
        assert s_resp.status_code == 400

    # Verify core tables and seed data remain intact after all SQLi probes
    conn = sec_db.connect()
    try:
        with conn.cursor() as cur:
            cur.execute("SELECT count(*) FROM users")
            assert cur.fetchone()[0] >= 5
            cur.execute("SELECT count(*) FROM movies")
            assert cur.fetchone()[0] >= 6
            cur.execute("SELECT count(*) FROM showtimes WHERE showtime_id = %s", (sid,))
            assert cur.fetchone()[0] == 1
    finally:
        conn.close()


def test_stored_xss_payloads_returned_as_safe_json_with_security_headers(sec_app, sec_db):
    _, _, admin_client = _make_account(sec_app, sec_db, "ADMIN")
    anon_client = ApiClient(sec_app.test_client(), origin=FRONTEND_URL)

    xss_title = "<script>window.__xss=1</script><img src=x onerror=alert(1)>"
    xss_user = f"xss_{uuid.uuid4().hex[:6]}_<svg onload=alert(1)>"

    reg_resp = anon_client.post("/api/auth/register", {"username": xss_user, "password": "pw"})
    assert reg_resp.status_code == 400
    assert reg_resp.headers["Content-Type"] == "application/json"
    assert reg_resp.headers["X-Content-Type-Options"] == "nosniff"
    assert "default-src 'none'" in reg_resp.headers["Content-Security-Policy"]

    movie_resp = admin_client.post(
        "/api/admin/movies",
        {
            "title": xss_title,
            "genre": "<b onmouseover=alert(1)>Action</b>",
            "rating": "<script>1</script>",
            "synopsis": "<iframe src='javascript:alert(1)'></iframe>",
            "duration_minutes": 100,
        },
    )
    assert movie_resp.status_code == 201
    movie_id = movie_resp.get_json()["movie"]["movie_id"]

    public_resp = anon_client.get(f"/api/movies/{movie_id}")
    assert public_resp.status_code == 200
    assert public_resp.headers["Content-Type"] == "application/json"
    assert public_resp.headers["X-Content-Type-Options"] == "nosniff"
    assert "default-src 'none'" in public_resp.headers["Content-Security-Policy"]
    assert public_resp.get_json()["movie"]["title"] == xss_title

    for bad_poster in ("javascript:alert(1)", "data:text/html,<script>alert(1)</script>", "/images/posters/x.svg"):
        bad = admin_client.post(
            "/api/admin/movies",
            {"title": "Bad Poster", "duration_minutes": 90, "poster_url": bad_poster},
        )
        assert bad.status_code == 400
        assert "poster_url" in bad.get_json()["error"]["fields"]
