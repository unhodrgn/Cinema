"""Tests for Phase 4 Tasks T4, T5, and T6 against a real PostgreSQL instance:
* T4: Seat availability API (GET /api/screenings/{id}/seats)
* T5: Booking creation and simulated payment (POST /api/bookings, POST /api/bookings/{id}/pay)
* T6: Booking history, details, and cancellation (GET /api/bookings, GET /api/bookings/{id}, POST /api/bookings/{id}/cancel)
* Concurrency: parallel booking of the same seat (race-safety)
* Direct database verification: checking tables bookings and booking_seats directly in PostgreSQL.

Needs a disposable PostgreSQL (explicit TEST_DB_PORT); skipped automatically otherwise.
"""

import threading
import uuid
from decimal import Decimal

import pytest

import disposable_db
from app import create_app, passwords, security
from helpers import ApiClient

FRONTEND = "http://localhost:8080"
HASH = passwords.hash_password("test-password-123")


@pytest.fixture(scope="module")
def booking_db(cinema_template_db):
    with disposable_db.clone_database(cinema_template_db) as clone:
        yield clone


@pytest.fixture(scope="module")
def app(booking_db):
    return create_app("testing", dict(booking_db.app_config(), CORS_ALLOWED_ORIGINS=FRONTEND))


@pytest.fixture(scope="module")
def customer(app, booking_db):
    conn = booking_db.connect()
    try:
        with conn.cursor() as cur:
            cur.execute(
                "INSERT INTO users(username, password_hash, role) VALUES (%s, %s, 'CUSTOMER') RETURNING user_id",
                (f"cust_{uuid.uuid4().hex[:8]}", HASH),
            )
            uid = cur.fetchone()[0]
        conn.commit()
    finally:
        conn.close()

    with app.app_context():
        token, _ = security.issue_token(uid)
    return {"user_id": uid, "client": ApiClient(app.test_client(), origin=FRONTEND).set_token(token)}


@pytest.fixture(scope="module")
def customer2(app, booking_db):
    conn = booking_db.connect()
    try:
        with conn.cursor() as cur:
            cur.execute(
                "INSERT INTO users(username, password_hash, role) VALUES (%s, %s, 'CUSTOMER') RETURNING user_id",
                (f"cust2_{uuid.uuid4().hex[:8]}", HASH),
            )
            uid = cur.fetchone()[0]
        conn.commit()
    finally:
        conn.close()

    with app.app_context():
        token, _ = security.issue_token(uid)
    return {"user_id": uid, "client": ApiClient(app.test_client(), origin=FRONTEND).set_token(token)}


@pytest.fixture(scope="module")
def admin(app, booking_db):
    conn = booking_db.connect()
    try:
        with conn.cursor() as cur:
            cur.execute(
                "INSERT INTO users(username, password_hash, role) VALUES (%s, %s, 'ADMIN') RETURNING user_id",
                (f"admin_{uuid.uuid4().hex[:8]}", HASH),
            )
            uid = cur.fetchone()[0]
        conn.commit()
    finally:
        conn.close()

    with app.app_context():
        token, _ = security.issue_token(uid)
    return {"user_id": uid, "client": ApiClient(app.test_client(), origin=FRONTEND).set_token(token)}


@pytest.fixture(scope="module")
def public_client(app):
    return ApiClient(app.test_client(), origin=FRONTEND)


@pytest.fixture(scope="module")
def future_screenings(public_client):
    """Retrieve screenings that are strictly in the future (has_started is False)."""
    resp = public_client.get("/api/screenings")
    screenings = resp.get_json()["screenings"]
    future = [s for s in screenings if not s["has_started"]]
    assert len(future) >= 2, "Need at least 2 future screenings for testing"
    return future


# --- T4: Seat Availability ---


def test_seat_availability_public_access(public_client, future_screenings):
    showtime_id = future_screenings[0]["showtime_id"]
    resp = public_client.get(f"/api/screenings/{showtime_id}/seats")
    assert resp.status_code == 200
    data = resp.get_json()
    assert "screening" in data
    assert "seats" in data
    assert len(data["seats"]) == 50
    first = data["seats"][0]
    assert "seat_id" in first
    assert "seat_row" in first
    assert "seat_number" in first
    assert first["is_available"] is True


def test_seat_availability_unknown_screening(public_client):
    resp = public_client.get("/api/screenings/999999/seats")
    assert resp.status_code == 404
    assert resp.get_json()["error"]["code"] == "not_found"


def test_seat_availability_invalid_id(public_client):
    assert public_client.get("/api/screenings/abc/seats").status_code == 404
    assert public_client.get("/api/screenings/0/seats").status_code == 404
    assert public_client.get("/api/screenings/-1/seats").status_code == 404


# --- T5: Booking and Payment ---


def test_booking_requires_customer_auth(public_client, admin, future_screenings):
    sid = future_screenings[0]["showtime_id"]
    # Anonymous -> 401
    resp = public_client.post("/api/bookings", {"screening_id": sid, "seat_ids": [1]})
    assert resp.status_code == 401

    # Admin -> 403
    resp = admin["client"].post("/api/bookings", {"screening_id": sid, "seat_ids": [1]})
    assert resp.status_code == 403


def test_booking_input_validation(customer, future_screenings):
    client = customer["client"]
    sid = future_screenings[0]["showtime_id"]

    # Missing screening_id
    resp = client.post("/api/bookings", {"seat_ids": [1]})
    assert resp.status_code == 400
    assert "screening_id" in resp.get_json()["error"]["fields"]

    # Empty seat_ids
    resp = client.post("/api/bookings", {"screening_id": sid, "seat_ids": []})
    assert resp.status_code == 400
    assert "seat_ids" in resp.get_json()["error"]["fields"]

    # Duplicates in seat_ids
    resp = client.post("/api/bookings", {"screening_id": sid, "seat_ids": [1, 1]})
    assert resp.status_code == 400
    assert "seat_ids" in resp.get_json()["error"]["fields"]

    # Invalid non-integer seat
    resp = client.post("/api/bookings", {"screening_id": sid, "seat_ids": ["A1"]})
    assert resp.status_code == 400


def test_cannot_book_started_screening(customer, public_client):
    # Find a screening that has already started
    resp = public_client.get("/api/screenings")
    screenings = resp.get_json()["screenings"]
    started = [s for s in screenings if s["has_started"]]
    if not started:
        pytest.skip("No started screenings available at current time")
    sid = started[0]["showtime_id"]
    seats_resp = public_client.get(f"/api/screenings/{sid}/seats").get_json()["seats"]
    seat_id = seats_resp[0]["seat_id"]

    book_resp = customer["client"].post("/api/bookings", {"screening_id": sid, "seat_ids": [seat_id]})
    assert book_resp.status_code == 409
    assert book_resp.get_json()["error"]["code"] == "screening_started"


def test_create_booking_success_and_duplicate_prevention(customer, customer2, public_client, future_screenings, booking_db):
    client1 = customer["client"]
    client2 = customer2["client"]
    sid = future_screenings[0]["showtime_id"]

    # Find available seats for this future screening
    seats_resp = public_client.get(f"/api/screenings/{sid}/seats").get_json()["seats"]
    seat1 = seats_resp[0]["seat_id"]
    seat2 = seats_resp[1]["seat_id"]

    # Customer 1 books seat1 and seat2
    resp = client1.post("/api/bookings", {"screening_id": sid, "seat_ids": [seat1, seat2]})
    assert resp.status_code == 201
    booking = resp.get_json()["booking"]
    assert booking["status"] == "BOOKED"
    assert booking["payment_status"] == "UNPAID"
    assert len(booking["seats"]) == 2
    booking_id = booking["booking_id"]

    # DIRECT DATABASE CHECK: verify row in PostgreSQL
    conn = booking_db.connect()
    try:
        with conn.cursor() as cur:
            cur.execute("SELECT user_id, showtime_id, status, payment_status, total_amount, expires_at, booked_at FROM bookings WHERE booking_id = %s", (booking_id,))
            db_row = cur.fetchone()
            assert db_row[0] == customer["user_id"]
            assert db_row[1] == sid
            assert db_row[2] == "BOOKED"
            assert db_row[3] == "UNPAID"
            assert db_row[4] == Decimal("24000.00")  # 2 * 12000.00
            # expires_at must be booked_at + 10 minutes
            assert int((db_row[5] - db_row[6]).total_seconds()) == 600

            # Check booking_seats table: 2 rows with price snapshot
            cur.execute("SELECT seat_id, price_at_booking FROM booking_seats WHERE booking_id = %s ORDER BY seat_id", (booking_id,))
            seat_rows = cur.fetchall()
            assert len(seat_rows) == 2
            assert seat_rows[0][0] == seat1 and seat_rows[0][1] == Decimal("12000.00")
            assert seat_rows[1][0] == seat2 and seat_rows[1][1] == Decimal("12000.00")
    finally:
        conn.close()

    # Verify seats are now unavailable in seat picker API
    updated_seats = public_client.get(f"/api/screenings/{sid}/seats").get_json()["seats"]
    seat1_obj = next(s for s in updated_seats if s["seat_id"] == seat1)
    seat2_obj = next(s for s in updated_seats if s["seat_id"] == seat2)
    assert seat1_obj["is_available"] is False
    assert seat2_obj["is_available"] is False

    # Customer 2 attempts to book the already taken seat1 -> 409 seat_unavailable
    conflict_resp = client2.post("/api/bookings", {"screening_id": sid, "seat_ids": [seat1]})
    assert conflict_resp.status_code == 409
    assert conflict_resp.get_json()["error"]["code"] == "seat_unavailable"

    # Payment: Customer 2 cannot pay Customer 1's booking -> 404
    pay_other = client2.post(f"/api/bookings/{booking_id}/pay", {})
    assert pay_other.status_code == 404

    # Customer 1 pays their booking -> 200 PAID
    pay_resp = client1.post(f"/api/bookings/{booking_id}/pay", {})
    assert pay_resp.status_code == 200
    pay_data = pay_resp.get_json()
    assert pay_data["outcome"] == "PAID"
    assert pay_data["booking"]["payment_status"] == "PAID"
    assert pay_data["booking"]["paid_at"] is not None

    # DIRECT DATABASE CHECK: payment_status is PAID in PostgreSQL
    conn = booking_db.connect()
    try:
        with conn.cursor() as cur:
            cur.execute("SELECT payment_status, paid_at FROM bookings WHERE booking_id = %s", (booking_id,))
            p_status, paid_at = cur.fetchone()
            assert p_status == "PAID"
            assert paid_at is not None
    finally:
        conn.close()

    # Paying again -> 409 invalid_booking_state
    pay_again = client1.post(f"/api/bookings/{booking_id}/pay", {})
    assert pay_again.status_code == 409
    assert pay_again.get_json()["error"]["code"] == "invalid_booking_state"


# --- T6: History, Details, and Cancellation ---


def test_booking_history_and_details(customer, customer2, future_screenings):
    client1 = customer["client"]
    client2 = customer2["client"]

    # Customer 1 history includes their booking
    hist_resp = client1.get("/api/bookings")
    assert hist_resp.status_code == 200
    bookings = hist_resp.get_json()["bookings"]
    assert len(bookings) >= 1
    my_booking = bookings[0]
    bid = my_booking["booking_id"]

    # Customer 1 can get single booking details
    det_resp = client1.get(f"/api/bookings/{bid}")
    assert det_resp.status_code == 200
    assert det_resp.get_json()["booking"]["booking_id"] == bid

    # Customer 2 cannot see Customer 1's booking details -> 404
    det_other = client2.get(f"/api/bookings/{bid}")
    assert det_other.status_code == 404


def test_cancellation_releases_seats_and_preserves_history(customer, customer2, public_client, future_screenings, booking_db):
    client1 = customer["client"]
    client2 = customer2["client"]
    sid = future_screenings[1]["showtime_id"]

    # Screening 2: Customer 1 books a seat
    seats_resp = public_client.get(f"/api/screenings/{sid}/seats").get_json()["seats"]
    seat_a = seats_resp[0]["seat_id"]

    resp = client1.post("/api/bookings", {"screening_id": sid, "seat_ids": [seat_a]})
    assert resp.status_code == 201
    booking_id = resp.get_json()["booking"]["booking_id"]

    # Customer 1 pays
    pay_res = client1.post(f"/api/bookings/{booking_id}/pay", {})
    assert pay_res.status_code == 200

    # Customer 2 cannot cancel Customer 1's booking -> 404
    cancel_other = client2.post(f"/api/bookings/{booking_id}/cancel", {})
    assert cancel_other.status_code == 404

    # Customer 1 cancels booking
    cancel_resp = client1.post(f"/api/bookings/{booking_id}/cancel", {})
    assert cancel_resp.status_code == 200
    cancel_data = cancel_resp.get_json()
    assert cancel_data["outcome"] == "CANCELLED"
    cancelled_booking = cancel_data["booking"]
    assert cancelled_booking["status"] == "CANCELLED"
    assert cancelled_booking["payment_status"] == "PAID"  # D1: payment_status stays PAID
    assert cancelled_booking["cancelled_at"] is not None
    assert cancelled_booking["seats"] == []  # detail seats deleted

    # DIRECT DATABASE CHECK:
    # 1. Parent booking record preserved in PostgreSQL with status CANCELLED, payment_status PAID
    # 2. booking_seats rows deleted (0 rows)
    conn = booking_db.connect()
    try:
        with conn.cursor() as cur:
            cur.execute("SELECT status, payment_status, total_amount, cancelled_at FROM bookings WHERE booking_id = %s", (booking_id,))
            c_status, c_pay_status, c_total, c_cancelled_at = cur.fetchone()
            assert c_status == "CANCELLED"
            assert c_pay_status == "PAID"
            assert c_total == Decimal("12000.00")
            assert c_cancelled_at is not None

            cur.execute("SELECT count(*) FROM booking_seats WHERE booking_id = %s", (booking_id,))
            assert cur.fetchone()[0] == 0, "booking_seats detail rows must be deleted on cancellation"
    finally:
        conn.close()

    # Cancelling again -> 409 invalid_booking_state
    cancel_again = client1.post(f"/api/bookings/{booking_id}/cancel", {})
    assert cancel_again.status_code == 409

    # Verify seat_a is released and available again in seat picker API!
    updated_seats = public_client.get(f"/api/screenings/{sid}/seats").get_json()["seats"]
    seat_a_obj = next(s for s in updated_seats if s["seat_id"] == seat_a)
    assert seat_a_obj["is_available"] is True

    # Customer 2 can now book seat_a successfully!
    c2_book = client2.post("/api/bookings", {"screening_id": sid, "seat_ids": [seat_a]})
    assert c2_book.status_code == 201


# --- Concurrency: Race-safe seat booking ---


def test_concurrent_seat_booking_exactly_one_wins(customer, customer2, public_client, future_screenings, booking_db):
    """Two concurrent threads attempt to book the exact same seat simultaneously.

    PostgreSQL row-level locking on the screening serializes the validation:
    exactly one client receives 201 (success), and the other receives 409 (seat_unavailable).
    Direct DB verification confirms exactly one active booking exists for that seat.
    """
    client1 = customer["client"]
    client2 = customer2["client"]
    sid = future_screenings[0]["showtime_id"]

    # Pick an available seat
    seats_resp = public_client.get(f"/api/screenings/{sid}/seats").get_json()["seats"]
    target_seat = next(s["seat_id"] for s in seats_resp if s["is_available"])

    results = []
    barrier = threading.Barrier(2)

    def attempt_booking(client, tag):
        barrier.wait()
        res = client.post("/api/bookings", {"screening_id": sid, "seat_ids": [target_seat]})
        results.append((tag, res.status_code, res.get_json()))

    t1 = threading.Thread(target=attempt_booking, args=(client1, "c1"))
    t2 = threading.Thread(target=attempt_booking, args=(client2, "c2"))

    t1.start()
    t2.start()
    t1.join(timeout=10)
    t2.join(timeout=10)

    status_codes = sorted([r[1] for r in results])
    assert status_codes == [201, 409], f"Expected [201, 409] but got: {results}"

    # Verify in PostgreSQL directly: exactly one booking_seat exists
    conn = booking_db.connect()
    try:
        with conn.cursor() as cur:
            cur.execute(
                """
                SELECT count(*)
                FROM booking_seats bs
                JOIN bookings b ON b.booking_id = bs.booking_id
                WHERE b.showtime_id = %s AND bs.seat_id = %s AND b.status = 'BOOKED'
                """,
                (sid, target_seat),
            )
            count = cur.fetchone()[0]
            assert count == 1, "Exactly one active booking must exist in PostgreSQL"
    finally:
        conn.close()
