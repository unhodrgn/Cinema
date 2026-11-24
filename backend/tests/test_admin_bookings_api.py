"""T8: admin booking list (B03 A-03, view only) against a real PostgreSQL.

``GET /api/admin/bookings`` shows the bookings of every customer in every status, can be
filtered by status, screening and customer, expires overdue bookings before reading, and
never changes anything. Every test works on screenings it creates itself and filters by
them, so the shared database of this module cannot make tests depend on each other.

Needs a disposable PostgreSQL (explicit TEST_DB_PORT); skipped automatically otherwise.
"""

import datetime as dt
import itertools
import uuid

import pytest

import disposable_db
import time_travel
from app import create_app
from app.core import passwords, security
from helpers import ApiClient

FRONTEND = "http://localhost:8080"
HASH = passwords.hash_password("test-password-123")
PRICE = "14000"

_days = itertools.count()


def next_day():
    return (dt.date(2031, 1, 1) + dt.timedelta(days=next(_days))).isoformat()


@pytest.fixture(scope="module")
def booking_list_db(cinema_template_db):
    with disposable_db.clone_database(cinema_template_db) as clone:
        yield clone


@pytest.fixture(scope="module")
def app(booking_list_db):
    return create_app("testing", dict(booking_list_db.app_config(), CORS_ALLOWED_ORIGINS=FRONTEND))


def _account(app, database, role):
    conn = database.connect()
    try:
        with conn.cursor() as cur:
            cur.execute(
                "INSERT INTO users(username, password_hash, role) VALUES (%s, %s, %s) RETURNING user_id, username",
                (f"{role.lower()}_{uuid.uuid4().hex[:8]}", HASH, role),
            )
            user_id, username = cur.fetchone()
        conn.commit()
    finally:
        conn.close()
    with app.app_context():
        token, _ = security.issue_token(user_id)
    client = ApiClient(app.test_client(), origin=FRONTEND).set_token(token)
    return {"client": client, "user_id": user_id, "username": username}


@pytest.fixture(scope="module")
def admin(app, booking_list_db):
    return _account(app, booking_list_db, "ADMIN")["client"]


@pytest.fixture(scope="module")
def alice(app, booking_list_db):
    return _account(app, booking_list_db, "CUSTOMER")


@pytest.fixture(scope="module")
def bob(app, booking_list_db):
    return _account(app, booking_list_db, "CUSTOMER")


@pytest.fixture(scope="module")
def catalog(admin):
    movie = admin.get("/api/admin/movies").get_json()["movies"][0]
    room = admin.get("/api/admin/screenings").get_json()["rooms"][0]
    return {"movie": movie, "room": room}


def new_screening(admin, catalog, price=PRICE):
    response = admin.post("/api/admin/screenings", {
        "movie_id": catalog["movie"]["movie_id"], "room_id": catalog["room"]["room_id"],
        "starts_at": f"{next_day()}T10:00", "ticket_price": price})
    assert response.status_code == 201, response.get_json()
    return response.get_json()["screening"]


def book(customer, showtime_id, seats=1):
    client = customer["client"]
    free = [s["seat_id"] for s in client.get(f"/api/screenings/{showtime_id}/seats").get_json()["seats"] if s["is_available"]]
    response = client.post("/api/bookings", {"screening_id": showtime_id, "seat_ids": free[:seats]})
    assert response.status_code == 201, response.get_json()
    return response.get_json()["booking"]["booking_id"]


def listing(admin, **params):
    query = "&".join(f"{k}={v}" for k, v in params.items())
    response = admin.get("/api/admin/bookings" + (f"?{query}" if query else ""))
    assert response.status_code == 200, response.get_json()
    return response.get_json()["bookings"]


def by_id(bookings):
    return {b["booking_id"]: b for b in bookings}


def age(database, booking_id):
    conn = database.connect()
    try:
        time_travel.age_booking(conn, booking_id)
    finally:
        conn.close()


def assert_filter_error(response, field):
    assert response.status_code == 400, response.get_json()
    error = response.get_json()["error"]
    assert error["code"] == "validation_error" and field in error["fields"]


# --- content ------------------------------------------------------------------------------------


def test_the_list_shows_the_bookings_of_every_customer(admin, alice, bob, catalog):
    screening = new_screening(admin, catalog)
    a = book(alice, screening["showtime_id"])
    b = book(bob, screening["showtime_id"])
    found = by_id(listing(admin, screening_id=screening["showtime_id"]))
    assert set(found) == {a, b}
    assert found[a]["username"] == alice["username"] and found[a]["user_id"] == alice["user_id"]
    assert found[b]["username"] == bob["username"]


def test_a_booking_carries_everything_the_page_needs(admin, alice, catalog):
    screening = new_screening(admin, catalog)
    booking_id = book(alice, screening["showtime_id"], seats=2)
    booking = by_id(listing(admin, screening_id=screening["showtime_id"]))[booking_id]
    assert set(booking) == {
        "booking_id", "user_id", "username", "showtime_id", "title", "starts_at", "ends_at",
        "room_name", "ticket_price", "booked_at", "expires_at", "total_amount", "status",
        "payment_status", "paid_at", "cancelled_at", "seats",
    }
    assert booking["title"] == catalog["movie"]["title"]
    assert booking["room_name"] == catalog["room"]["room_name"]
    assert booking["status"] == "BOOKED" and booking["payment_status"] == "UNPAID"
    assert booking["paid_at"] is None and booking["cancelled_at"] is None
    assert booking["ticket_price"] == "14000.00"
    assert booking["total_amount"] == "28000.00"
    assert len(booking["seats"]) == 2
    assert {s["price_at_booking"] for s in booking["seats"]} == {"14000.00"}
    assert [(s["seat_row"], s["seat_number"]) for s in booking["seats"]] == sorted(
        (s["seat_row"], s["seat_number"]) for s in booking["seats"])


def test_no_password_data_is_ever_listed(admin, alice, catalog):
    screening = new_screening(admin, catalog)
    book(alice, screening["showtime_id"])
    text = admin.get(f"/api/admin/bookings?screening_id={screening['showtime_id']}").get_data(as_text=True)
    assert "password" not in text.lower() and "pbkdf2" not in text


def test_paid_cancelled_and_expired_bookings_are_shown_with_their_state(admin, alice, booking_list_db, catalog):
    screening = new_screening(admin, catalog)
    sid = screening["showtime_id"]
    paid = book(alice, sid)
    cancelled = book(alice, sid)
    expired = book(alice, sid)
    unpaid = book(alice, sid)
    assert alice["client"].post(f"/api/bookings/{paid}/pay", {}).status_code == 200
    assert alice["client"].post(f"/api/bookings/{cancelled}/cancel", {}).status_code == 200
    age(booking_list_db, expired)

    found = by_id(listing(admin, screening_id=sid))
    assert (found[paid]["status"], found[paid]["payment_status"]) == ("BOOKED", "PAID")
    assert found[paid]["paid_at"] is not None and len(found[paid]["seats"]) == 1
    assert (found[unpaid]["status"], found[unpaid]["payment_status"]) == ("BOOKED", "UNPAID")
    assert (found[cancelled]["status"], found[cancelled]["payment_status"]) == ("CANCELLED", "UNPAID")
    assert found[cancelled]["cancelled_at"] is not None
    assert (found[expired]["status"], found[expired]["payment_status"]) == ("EXPIRED", "UNPAID")


def test_cancelled_and_expired_bookings_keep_their_total_but_list_no_seats(admin, alice, booking_list_db, catalog):
    # D1/D3: the history stays, the seat rows are gone (the seats were given back).
    screening = new_screening(admin, catalog)
    sid = screening["showtime_id"]
    cancelled = book(alice, sid, seats=2)
    expired = book(alice, sid, seats=1)
    assert alice["client"].post(f"/api/bookings/{cancelled}/cancel", {}).status_code == 200
    age(booking_list_db, expired)
    found = by_id(listing(admin, screening_id=sid))
    assert found[cancelled]["seats"] == [] and found[cancelled]["total_amount"] == "28000.00"
    assert found[expired]["seats"] == [] and found[expired]["total_amount"] == "14000.00"


def test_a_paid_booking_never_expires_however_old(admin, alice, booking_list_db, catalog):
    screening = new_screening(admin, catalog)
    booking_id = book(alice, screening["showtime_id"])
    assert alice["client"].post(f"/api/bookings/{booking_id}/pay", {}).status_code == 200
    age(booking_list_db, booking_id)
    assert by_id(listing(admin, screening_id=screening["showtime_id"]))[booking_id]["status"] == "BOOKED"


# --- ordering -----------------------------------------------------------------------------------


def test_the_list_is_newest_booking_first(admin, alice, bob, catalog):
    screening = new_screening(admin, catalog)
    ids = [book(alice, screening["showtime_id"]), book(bob, screening["showtime_id"]), book(alice, screening["showtime_id"])]
    listed = [b["booking_id"] for b in listing(admin, screening_id=screening["showtime_id"])]
    assert listed == list(reversed(ids))


# --- filters ------------------------------------------------------------------------------------


def test_filter_by_status(admin, alice, booking_list_db, catalog):
    screening = new_screening(admin, catalog)
    sid = screening["showtime_id"]
    booked = book(alice, sid)
    cancelled = book(alice, sid)
    expired = book(alice, sid)
    assert alice["client"].post(f"/api/bookings/{cancelled}/cancel", {}).status_code == 200
    age(booking_list_db, expired)
    assert {b["booking_id"] for b in listing(admin, screening_id=sid, status="BOOKED")} == {booked}
    assert {b["booking_id"] for b in listing(admin, screening_id=sid, status="CANCELLED")} == {cancelled}
    assert {b["booking_id"] for b in listing(admin, screening_id=sid, status="EXPIRED")} == {expired}
    assert {b["booking_id"] for b in listing(admin, screening_id=sid)} == {booked, cancelled, expired}


def test_status_filter_ignores_case_and_blank_means_all(admin, alice, catalog):
    screening = new_screening(admin, catalog)
    booking_id = book(alice, screening["showtime_id"])
    sid = screening["showtime_id"]
    assert {b["booking_id"] for b in listing(admin, screening_id=sid, status="booked")} == {booking_id}
    assert {b["booking_id"] for b in listing(admin, screening_id=sid, status="")} == {booking_id}


@pytest.mark.parametrize("status", ["PAID", "UNPAID", "bogus", "BOOKED,EXPIRED", "1"])
def test_an_unknown_status_is_400(admin, status):
    assert_filter_error(admin.get(f"/api/admin/bookings?status={status}"), "status")


def test_filter_by_screening_and_by_customer(admin, alice, bob, catalog):
    first = new_screening(admin, catalog)
    second = new_screening(admin, catalog)
    a1 = book(alice, first["showtime_id"])
    b1 = book(bob, first["showtime_id"])
    a2 = book(alice, second["showtime_id"])
    assert {b["booking_id"] for b in listing(admin, screening_id=first["showtime_id"])} == {a1, b1}
    assert {b["booking_id"] for b in listing(admin, screening_id=second["showtime_id"])} == {a2}
    assert {b["booking_id"] for b in listing(admin, user_id=alice["user_id"], screening_id=first["showtime_id"])} == {a1}
    assert {b["booking_id"] for b in listing(admin, user_id=bob["user_id"], screening_id=first["showtime_id"])} == {b1}
    assert {a1, a2} <= {b["booking_id"] for b in listing(admin, user_id=alice["user_id"])}
    assert all(b["user_id"] == alice["user_id"] for b in listing(admin, user_id=alice["user_id"]))


def test_filters_combine_with_and(admin, alice, bob, catalog):
    screening = new_screening(admin, catalog)
    sid = screening["showtime_id"]
    a = book(alice, sid)
    book(bob, sid)
    assert alice["client"].post(f"/api/bookings/{a}/cancel", {}).status_code == 200
    assert listing(admin, screening_id=sid, user_id=alice["user_id"], status="BOOKED") == []
    assert [b["booking_id"] for b in listing(admin, screening_id=sid, user_id=alice["user_id"], status="CANCELLED")] == [a]


def test_unknown_screening_or_customer_gives_an_empty_list(admin):
    assert listing(admin, screening_id=999999) == []
    assert listing(admin, user_id=999999) == []


@pytest.mark.parametrize("name", ["screening_id", "user_id"])
@pytest.mark.parametrize("value", ["abc", "0", "-1", "1.5", "99999999999999999999"])
def test_a_bad_id_filter_is_400_never_500(admin, name, value):
    assert_filter_error(admin.get(f"/api/admin/bookings?{name}={value}"), name)


def test_several_bad_filters_are_reported_together(admin):
    response = admin.get("/api/admin/bookings?status=x&screening_id=y&user_id=z")
    assert response.status_code == 400
    assert set(response.get_json()["error"]["fields"]) == {"status", "screening_id", "user_id"}


# --- expiry on read -----------------------------------------------------------------------------


def test_reading_the_list_expires_overdue_bookings_and_gives_the_seats_back(admin, alice, booking_list_db, catalog):
    screening = new_screening(admin, catalog)
    sid = screening["showtime_id"]
    booking_id = book(alice, sid)
    age(booking_list_db, booking_id)  # nobody has touched it since: still BOOKED in the table

    conn = booking_list_db.connect()
    try:
        with conn.cursor() as cur:
            cur.execute("SELECT status FROM bookings WHERE booking_id = %s", (booking_id,))
            assert cur.fetchone()[0] == "BOOKED"
    finally:
        conn.close()

    found = by_id(listing(admin, screening_id=sid))
    assert found[booking_id]["status"] == "EXPIRED" and found[booking_id]["seats"] == []

    conn = booking_list_db.connect()  # the change was committed, not just displayed
    try:
        with conn.cursor() as cur:
            cur.execute("SELECT status FROM bookings WHERE booking_id = %s", (booking_id,))
            assert cur.fetchone()[0] == "EXPIRED"
            cur.execute("SELECT count(*) FROM booking_seats WHERE booking_id = %s", (booking_id,))
            assert cur.fetchone()[0] == 0
    finally:
        conn.close()
    seats = alice["client"].get(f"/api/screenings/{sid}/seats").get_json()["seats"]
    assert all(s["is_available"] for s in seats)


# --- view only ----------------------------------------------------------------------------------


@pytest.mark.parametrize("method", ["POST", "PUT", "PATCH", "DELETE"])
def test_the_list_cannot_be_written_to(admin, method):
    assert admin.request(method, "/api/admin/bookings", json={}).status_code == 405
    assert admin.request(method, "/api/admin/bookings/1", json={}).status_code in (404, 405)


def test_listing_changes_no_booking(admin, alice, booking_list_db, catalog):
    screening = new_screening(admin, catalog)
    sid = screening["showtime_id"]
    paid = book(alice, sid)
    assert alice["client"].post(f"/api/bookings/{paid}/pay", {}).status_code == 200

    def snapshot():
        conn = booking_list_db.connect()
        try:
            with conn.cursor() as cur:
                cur.execute("SELECT booking_id, status, payment_status, total_amount, paid_at FROM bookings WHERE showtime_id = %s ORDER BY booking_id", (sid,))
                return cur.fetchall()
        finally:
            conn.close()

    before = snapshot()
    listing(admin, screening_id=sid)
    listing(admin, screening_id=sid, status="BOOKED")
    assert snapshot() == before
