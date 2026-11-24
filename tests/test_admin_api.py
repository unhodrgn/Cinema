"""T7: admin movie and screening API (B03 A-01, A-02) against a real PostgreSQL.

Covers CRUD, input validation and the technical limits, the D2 protection (a screening with
any booking record cannot be changed), overlap prevention, and access control. The admin
booking list (T8) has its own tests.

All tests share one disposable database. Every test that creates screenings uses its own
calendar day in 2030 (``next_day``), so tests cannot overlap each other whatever the order.

Needs a disposable PostgreSQL (explicit TEST_DB_PORT); skipped automatically otherwise.
"""

import datetime as dt
import itertools
import uuid

import pytest

import disposable_db
import time_travel
from app import create_app, passwords, security
from helpers import ApiClient

FRONTEND = "http://localhost:8080"
HASH = passwords.hash_password("test-password-123")
SEOUL = dt.timezone(dt.timedelta(hours=9))

_days = itertools.count()


def next_day():
    """A calendar day (2030) that no other test uses."""
    return (dt.date(2030, 1, 1) + dt.timedelta(days=next(_days))).isoformat()


# --- fixtures -------------------------------------------------------------------------------


@pytest.fixture(scope="module")
def admin_db(cinema_template_db):
    with disposable_db.clone_database(cinema_template_db) as clone:
        yield clone


@pytest.fixture(scope="module")
def app(admin_db):
    return create_app("testing", dict(admin_db.app_config(), CORS_ALLOWED_ORIGINS=FRONTEND))


def _account(app, database, role):
    conn = database.connect()
    try:
        with conn.cursor() as cur:
            cur.execute(
                "INSERT INTO users(username, password_hash, role) VALUES (%s, %s, %s) RETURNING user_id",
                (f"{role.lower()}_{uuid.uuid4().hex[:8]}", HASH, role),
            )
            user_id = cur.fetchone()[0]
        conn.commit()
    finally:
        conn.close()
    with app.app_context():
        token, _ = security.issue_token(user_id)
    return ApiClient(app.test_client(), origin=FRONTEND).set_token(token)


@pytest.fixture(scope="module")
def admin(app, admin_db):
    return _account(app, admin_db, "ADMIN")


@pytest.fixture(scope="module")
def customer(app, admin_db):
    return _account(app, admin_db, "CUSTOMER")


@pytest.fixture(scope="module")
def anonymous(app):
    return ApiClient(app.test_client(), origin=FRONTEND)


@pytest.fixture(scope="module")
def movies(admin):
    return admin.get("/api/admin/movies").get_json()["movies"]


@pytest.fixture(scope="module")
def rooms(admin):
    return admin.get("/api/admin/screenings").get_json()["rooms"]


def db_row(database, sql, params=()):
    conn = database.connect()
    try:
        with conn.cursor() as cur:
            cur.execute(sql, params)
            return cur.fetchone()
    finally:
        conn.close()


def movie_body(**overrides):
    body = {"title": "Test Movie " + uuid.uuid4().hex[:6], "duration_minutes": 100}
    body.update(overrides)
    return body


def screening_body(movie_id, room_id, day=None, time="10:00", price="14000", **overrides):
    day = day or next_day()
    body = {"movie_id": movie_id, "room_id": room_id, "starts_at": f"{day}T{time}", "ticket_price": price}
    body.update(overrides)
    return body


def create_screening(admin, movie_id, room_id, **kwargs):
    response = admin.post("/api/admin/screenings", screening_body(movie_id, room_id, **kwargs))
    assert response.status_code == 201, response.get_json()
    return response.get_json()["screening"]


def book_first_free_seat(customer, showtime_id):
    seats = customer.get(f"/api/screenings/{showtime_id}/seats").get_json()["seats"]
    seat_id = next(s["seat_id"] for s in seats if s["is_available"])
    response = customer.post("/api/bookings", {"screening_id": showtime_id, "seat_ids": [seat_id]})
    assert response.status_code == 201, response.get_json()
    return response.get_json()["booking"]["booking_id"]


def error_of(response):
    return response.get_json()["error"]


def assert_field_error(response, field):
    assert response.status_code == 400, response.get_json()
    error = error_of(response)
    assert error["code"] == "validation_error"
    assert field in error["fields"], error


# --- access control ---------------------------------------------------------------------------

ADMIN_ROUTES = [
    ("GET", "/api/admin/movies", None),
    ("GET", "/api/admin/movies/1", None),
    ("POST", "/api/admin/movies", {"title": "x", "duration_minutes": 90}),
    ("PUT", "/api/admin/movies/1", {"title": "x", "duration_minutes": 90}),
    ("GET", "/api/admin/screenings", None),
    ("GET", "/api/admin/screenings/1", None),
    ("POST", "/api/admin/screenings", {"movie_id": 1, "room_id": 1, "starts_at": "2030-01-01T10:00", "ticket_price": "1"}),
    ("PUT", "/api/admin/screenings/1", {"movie_id": 1, "room_id": 1, "starts_at": "2030-01-01T10:00", "ticket_price": "1"}),
    ("GET", "/api/admin/bookings", None),
]


@pytest.mark.parametrize("method,path,body", ADMIN_ROUTES, ids=lambda v: v if isinstance(v, str) else "")
def test_anonymous_gets_401_and_customer_gets_403(anonymous, customer, method, path, body):
    assert anonymous.request(method, path, json=body).status_code == 401
    assert customer.request(method, path, json=body).status_code == 403


def test_denied_writes_change_nothing(anonymous, customer, admin_db):
    before = db_row(admin_db, "SELECT count(*) FROM movies")[0]
    anonymous.post("/api/admin/movies", movie_body())
    customer.post("/api/admin/movies", movie_body())
    assert db_row(admin_db, "SELECT count(*) FROM movies")[0] == before


# --- movies -----------------------------------------------------------------------------------


def test_list_movies_returns_the_seeded_movies_in_id_order(admin):
    data = admin.get("/api/admin/movies").get_json()["movies"]
    assert len(data) >= 6
    assert [m["movie_id"] for m in data] == sorted(m["movie_id"] for m in data)
    assert set(data[0]) == {"movie_id", "title", "genre", "duration_minutes", "rating", "synopsis", "release_date",
                            "poster_url"}


def test_create_movie_with_only_the_required_fields(admin, admin_db):
    response = admin.post("/api/admin/movies", {"title": "Minimal", "duration_minutes": 90})
    assert response.status_code == 201
    movie = response.get_json()["movie"]
    assert movie["title"] == "Minimal" and movie["duration_minutes"] == 90
    assert movie["genre"] is None and movie["rating"] is None
    assert movie["synopsis"] is None and movie["release_date"] is None
    row = db_row(admin_db, "SELECT title, duration_minutes, genre FROM movies WHERE movie_id = %s", (movie["movie_id"],))
    assert row == ("Minimal", 90, None)


def test_create_movie_with_all_fields_and_read_it_back(admin):
    body = movie_body(genre="Sci-Fi", rating="15+", synopsis="Line one\nLine two", release_date="2026-12-24")
    created = admin.post("/api/admin/movies", body).get_json()["movie"]
    fetched = admin.get(f"/api/admin/movies/{created['movie_id']}").get_json()["movie"]
    assert fetched == created
    assert fetched["release_date"] == "2026-12-24"
    assert fetched["synopsis"] == "Line one\nLine two"


def test_new_movie_is_visible_in_the_public_catalog(admin, anonymous):
    created = admin.post("/api/admin/movies", movie_body(title="Public Visible")).get_json()["movie"]
    public = anonymous.get(f"/api/movies/{created['movie_id']}")
    assert public.status_code == 200
    assert public.get_json()["movie"]["title"] == "Public Visible"


def test_text_is_trimmed_and_blank_optional_fields_become_null(admin):
    body = movie_body(title="  Padded  ", genre="   ", rating="", synopsis=" ", release_date="")
    movie = admin.post("/api/admin/movies", body).get_json()["movie"]
    assert movie["title"] == "Padded"
    assert movie["genre"] is None and movie["rating"] is None
    assert movie["synopsis"] is None and movie["release_date"] is None


def test_markup_in_text_is_stored_and_returned_as_plain_data(admin):
    title = "<script>alert(1)</script> & \"quotes\""
    movie = admin.post("/api/admin/movies", movie_body(title=title)).get_json()["movie"]
    assert movie["title"] == title


@pytest.mark.parametrize("title", [None, "", "   ", 5, True, ["x"]])
def test_movie_title_is_required_text(admin, title):
    assert_field_error(admin.post("/api/admin/movies", movie_body(title=title)), "title")


def test_movie_title_length_limit(admin):
    assert admin.post("/api/admin/movies", movie_body(title="a" * 200)).status_code == 201
    assert_field_error(admin.post("/api/admin/movies", movie_body(title="a" * 201)), "title")


@pytest.mark.parametrize("duration", [None, 0, -1, 301, 1.5, "120", True, [90]])
def test_movie_duration_must_be_an_integer_from_1_to_300(admin, duration):
    assert_field_error(admin.post("/api/admin/movies", movie_body(duration_minutes=duration)), "duration_minutes")


@pytest.mark.parametrize("duration", [1, 300])
def test_movie_duration_boundaries_are_accepted(admin, duration):
    assert admin.post("/api/admin/movies", movie_body(duration_minutes=duration)).status_code == 201


def test_movie_missing_duration_is_rejected(admin):
    assert_field_error(admin.post("/api/admin/movies", {"title": "No duration"}), "duration_minutes")


def test_genre_and_rating_length_limits_and_types(admin):
    assert admin.post("/api/admin/movies", movie_body(genre="g" * 100, rating="r" * 50)).status_code == 201
    assert_field_error(admin.post("/api/admin/movies", movie_body(genre="g" * 101)), "genre")
    assert_field_error(admin.post("/api/admin/movies", movie_body(rating="r" * 51)), "rating")
    assert_field_error(admin.post("/api/admin/movies", movie_body(genre=5)), "genre")
    assert_field_error(admin.post("/api/admin/movies", movie_body(rating=["PG"])), "rating")
    assert_field_error(admin.post("/api/admin/movies", movie_body(synopsis=5)), "synopsis")


@pytest.mark.parametrize("value", ["2026-13-01", "2026-02-30", "11/20/2026", "20261120", "not a date", 20261120])
def test_release_date_must_be_a_real_yyyy_mm_dd_date(admin, value):
    assert_field_error(admin.post("/api/admin/movies", movie_body(release_date=value)), "release_date")


GOOD_POSTERS = ["/images/posters/exhuma.jpg", "/images/posters/a-b_c.2.png", "/images/posters/20th-century-girl.jpg"]
BAD_POSTERS = [
    "images/posters/a.jpg", "/images/a.jpg", "/images/posters/", "/images/posters/a.gif", "/images/posters/a",
    "/images/posters/../a.jpg", "/images/posters/sub/a.jpg", "/images/posters/.hidden.jpg", "/images/posters/a b.jpg",
    "http://evil.example/images/posters/a.jpg", "//evil.example/images/posters/a.jpg", "javascript:alert(1)",
    "/images/posters/" + "a" * 250 + ".jpg", 5, True, ["/images/posters/a.jpg"],
]


@pytest.mark.parametrize("value", GOOD_POSTERS)
def test_a_poster_path_under_images_posters_is_accepted_and_returned(admin, value):
    movie = admin.post("/api/admin/movies", movie_body(poster_url=f"  {value}  ")).get_json()["movie"]
    assert movie["poster_url"] == value
    assert admin.get(f"/api/admin/movies/{movie['movie_id']}").get_json()["movie"]["poster_url"] == value


@pytest.mark.parametrize("value", BAD_POSTERS, ids=lambda v: repr(v)[:40])
def test_a_poster_path_must_be_a_file_directly_under_images_posters(admin, value):
    response = admin.post("/api/admin/movies", movie_body(poster_url=value))
    assert_field_error(response, "poster_url")
    created = admin.post("/api/admin/movies", movie_body()).get_json()["movie"]
    assert_field_error(admin.put(f"/api/admin/movies/{created['movie_id']}", movie_body(poster_url=value)), "poster_url")


def test_the_poster_is_optional_empty_means_none_and_put_replaces_it(admin):
    movie = admin.post("/api/admin/movies", movie_body(poster_url="")).get_json()["movie"]
    assert movie["poster_url"] is None
    with_poster = admin.post("/api/admin/movies", movie_body(poster_url="/images/posters/exhuma.jpg")).get_json()["movie"]
    cleared = admin.put(f"/api/admin/movies/{with_poster['movie_id']}", movie_body(poster_url=None)).get_json()["movie"]
    assert cleared["poster_url"] is None


def test_the_screening_and_booking_apis_carry_the_poster(admin, customer):
    movie = admin.post("/api/admin/movies", movie_body(poster_url="/images/posters/exhuma.jpg")).get_json()["movie"]
    rooms = admin.get("/api/admin/screenings").get_json()["rooms"]
    screening = create_screening(admin, movie["movie_id"], rooms[0]["room_id"])
    assert admin.get(f"/api/admin/screenings/{screening['showtime_id']}").get_json()["screening"]["poster_url"] == "/images/posters/exhuma.jpg"
    book_first_free_seat(customer, screening["showtime_id"])
    assert customer.get("/api/bookings").get_json()["bookings"][0]["poster_url"] == "/images/posters/exhuma.jpg"


def test_several_invalid_fields_are_reported_together(admin):
    response = admin.post("/api/admin/movies", {"title": "", "duration_minutes": 0, "release_date": "x"})
    assert response.status_code == 400
    assert set(error_of(response)["fields"]) == {"title", "duration_minutes", "release_date"}


def test_invalid_movie_creates_nothing(admin, admin_db):
    before = db_row(admin_db, "SELECT count(*) FROM movies")[0]
    admin.post("/api/admin/movies", {"title": "Bad", "duration_minutes": 0})
    assert db_row(admin_db, "SELECT count(*) FROM movies")[0] == before


def test_request_body_must_be_a_json_object(admin):
    assert admin.post("/api/admin/movies", ["not", "an", "object"]).status_code == 400
    response = admin.post("/api/admin/movies", headers={"Content-Type": "text/plain"}, data="title=x")
    assert response.status_code == 415
    response = admin.post("/api/admin/movies", headers={"Content-Type": "application/json"}, data="{broken")
    assert response.status_code == 400 and error_of(response)["code"] == "invalid_json"


def test_update_movie_replaces_all_editable_fields(admin):
    created = admin.post("/api/admin/movies", movie_body(genre="Drama", rating="12+", synopsis="Old")).get_json()["movie"]
    body = {"title": "Renamed", "duration_minutes": 111, "genre": "Comedy", "rating": "all", "synopsis": "New",
            "release_date": "2027-01-02", "poster_url": "/images/posters/new.png"}
    response = admin.put(f"/api/admin/movies/{created['movie_id']}", body)
    assert response.status_code == 200
    assert response.get_json()["movie"] == {"movie_id": created["movie_id"], **body}
    assert admin.get(f"/api/admin/movies/{created['movie_id']}").get_json()["movie"]["title"] == "Renamed"


def test_update_movie_is_a_full_replace_so_omitted_optional_fields_become_null(admin):
    created = admin.post("/api/admin/movies", movie_body(genre="Drama", rating="12+")).get_json()["movie"]
    updated = admin.put(f"/api/admin/movies/{created['movie_id']}", {"title": "Only required", "duration_minutes": 80}).get_json()["movie"]
    assert updated["genre"] is None and updated["rating"] is None


def test_update_movie_validates_like_create_and_keeps_the_old_data(admin):
    created = admin.post("/api/admin/movies", movie_body(title="Keep me")).get_json()["movie"]
    response = admin.put(f"/api/admin/movies/{created['movie_id']}", {"title": "", "duration_minutes": 400})
    assert response.status_code == 400
    assert set(error_of(response)["fields"]) == {"title", "duration_minutes"}
    assert admin.get(f"/api/admin/movies/{created['movie_id']}").get_json()["movie"]["title"] == "Keep me"


def test_editing_a_movie_with_booked_screenings_is_allowed(admin, customer):
    # Only the screening is protected by D2 (no movie-duration lock exists: decision log).
    movie = admin.post("/api/admin/movies", movie_body(title="Booked movie", duration_minutes=100)).get_json()["movie"]
    rooms = admin.get("/api/admin/screenings").get_json()["rooms"]
    screening = create_screening(admin, movie["movie_id"], rooms[0]["room_id"])
    book_first_free_seat(customer, screening["showtime_id"])
    response = admin.put(f"/api/admin/movies/{movie['movie_id']}", {"title": "Renamed booked", "duration_minutes": 130})
    assert response.status_code == 200
    unchanged = admin.get(f"/api/admin/screenings/{screening['showtime_id']}").get_json()["screening"]
    assert unchanged["ends_at"] == screening["ends_at"]  # existing screenings keep their end time


@pytest.mark.parametrize("path", ["/api/admin/movies/999999", "/api/admin/movies/0", f"/api/admin/movies/{2**63}", f"/api/admin/movies/{10**30}"])
def test_unknown_movie_ids_are_404(admin, path):
    assert admin.get(path).status_code == 404
    assert admin.put(path, {"title": "x", "duration_minutes": 90}).status_code == 404


def test_non_numeric_movie_id_is_404(admin):
    assert admin.get("/api/admin/movies/abc").status_code == 404


def test_movies_cannot_be_deleted_through_the_api(admin):
    assert admin.delete("/api/admin/movies/1").status_code == 405


# --- screenings: read ---------------------------------------------------------------------------


def test_list_screenings_returns_screenings_and_the_rooms(admin):
    data = admin.get("/api/admin/screenings").get_json()
    assert len(data["rooms"]) >= 5
    assert set(data["rooms"][0]) == {"room_id", "room_name"}
    assert len(data["screenings"]) >= 280
    first = data["screenings"][0]
    assert {"showtime_id", "movie_id", "title", "room_id", "room_name", "starts_at", "ends_at",
            "ticket_price", "has_started", "has_bookings"} <= set(first)
    assert isinstance(first["ticket_price"], str)  # money is an exact decimal string


def test_list_screenings_is_newest_first_then_by_room(admin):
    screenings = admin.get("/api/admin/screenings").get_json()["screenings"]
    keys = [(dt.datetime.fromisoformat(s["starts_at"]), -s["room_id"]) for s in screenings]
    assert keys == sorted(keys, reverse=True)


def test_list_screenings_can_be_filtered_by_movie(admin, movies):
    movie_id = movies[0]["movie_id"]
    screenings = admin.get(f"/api/admin/screenings?movie_id={movie_id}").get_json()["screenings"]
    assert screenings and all(s["movie_id"] == movie_id for s in screenings)
    assert admin.get("/api/admin/screenings?movie_id=999999").get_json()["screenings"] == []


@pytest.mark.parametrize("value", ["abc", "0", "-1", "1.5", str(2**63)])
def test_list_screenings_rejects_a_bad_movie_filter(admin, value):
    assert_field_error(admin.get(f"/api/admin/screenings?movie_id={value}"), "movie_id")


def test_get_one_screening_and_404s(admin):
    first = admin.get("/api/admin/screenings").get_json()["screenings"][0]
    fetched = admin.get(f"/api/admin/screenings/{first['showtime_id']}").get_json()["screening"]
    assert fetched["showtime_id"] == first["showtime_id"]
    for path in ("/api/admin/screenings/999999", "/api/admin/screenings/0", f"/api/admin/screenings/{10**30}"):
        assert admin.get(path).status_code == 404


def test_has_started_and_has_bookings_flags(admin, customer, movies, rooms):
    fresh = create_screening(admin, movies[0]["movie_id"], rooms[0]["room_id"])
    assert fresh["has_started"] is False and fresh["has_bookings"] is False
    book_first_free_seat(customer, fresh["showtime_id"])
    after = admin.get(f"/api/admin/screenings/{fresh['showtime_id']}").get_json()["screening"]
    assert after["has_bookings"] is True and after["has_started"] is False
    # every screening reported as started really began in the past (the clock is the database's)
    now = dt.datetime.now(dt.timezone.utc)
    listed = admin.get("/api/admin/screenings").get_json()["screenings"]
    assert all(dt.datetime.fromisoformat(s["starts_at"]) <= now for s in listed if s["has_started"])


# --- screenings: create -----------------------------------------------------------------------


def test_create_screening_calculates_the_end_time_from_the_movie_duration(admin, admin_db, movies, rooms):
    movie = movies[0]
    created = create_screening(admin, movie["movie_id"], rooms[0]["room_id"], day=next_day(), time="09:30", price="12000")
    start = dt.datetime.fromisoformat(created["starts_at"])
    end = dt.datetime.fromisoformat(created["ends_at"])
    assert end - start == dt.timedelta(minutes=movie["duration_minutes"])
    assert created["ticket_price"] == "12000.00"
    assert created["title"] == movie["title"] and created["room_id"] == rooms[0]["room_id"]
    row = db_row(admin_db, "SELECT ticket_price FROM showtimes WHERE showtime_id = %s", (created["showtime_id"],))
    assert str(row[0]) == "12000.00"


def test_create_screening_with_an_explicit_end_time(admin, movies, rooms):
    day = next_day()
    created = create_screening(admin, movies[0]["movie_id"], rooms[1]["room_id"], day=day, time="10:00", ends_at=f"{day}T12:45")
    assert created["ends_at"] == f"{day}T12:45:00+09:00"


def test_a_time_without_an_offset_is_the_cinema_local_time(admin, movies, rooms):
    day = next_day()
    created = create_screening(admin, movies[0]["movie_id"], rooms[0]["room_id"], day=day, time="19:05")
    assert created["starts_at"] == f"{day}T19:05:00+09:00"


def test_a_time_with_an_offset_is_the_same_instant(admin, movies, rooms):
    day = next_day()
    created = admin.post("/api/admin/screenings", {
        "movie_id": movies[0]["movie_id"], "room_id": rooms[0]["room_id"],
        "starts_at": f"{day}T01:00:00Z", "ticket_price": "10000"}).get_json()["screening"]
    assert dt.datetime.fromisoformat(created["starts_at"]) == dt.datetime.fromisoformat(f"{day}T01:00:00+00:00")


def test_price_may_be_a_number_or_a_string_and_keeps_two_decimals(admin, movies, rooms):
    for price, expected in [("12500.50", "12500.50"), (9000, "9000.00"), (9000.5, "9000.50"), ("0", "0.00")]:
        created = create_screening(admin, movies[0]["movie_id"], rooms[2]["room_id"], price=price)
        assert created["ticket_price"] == expected


def test_price_boundaries(admin, movies, rooms):
    assert create_screening(admin, movies[0]["movie_id"], rooms[3]["room_id"], price="99999999.99")["ticket_price"] == "99999999.99"
    for bad in ("100000000", "99999999.995"):
        response = admin.post("/api/admin/screenings", screening_body(movies[0]["movie_id"], rooms[3]["room_id"], price=bad))
        assert_field_error(response, "ticket_price")


@pytest.mark.parametrize("price", ["-1", -0.01, "abc", "", "  ", "Infinity", "-Infinity", "NaN", "inf", "1e30", 1e30, "100.005", True, None, [1], {"a": 1}])
def test_invalid_prices_are_400_never_500(admin, movies, rooms, price):
    response = admin.post("/api/admin/screenings", screening_body(movies[0]["movie_id"], rooms[0]["room_id"], price=price))
    assert_field_error(response, "ticket_price")


def test_a_huge_json_number_as_price_is_400(admin, movies, rooms):
    # json.dumps cannot write this, so send the raw text: 1e999 parses to infinity in Python
    body = ('{"movie_id": %d, "room_id": %d, "starts_at": "%sT10:00", "ticket_price": 1e999}'
            % (movies[0]["movie_id"], rooms[0]["room_id"], next_day()))
    response = admin.post("/api/admin/screenings", headers={"Content-Type": "application/json"}, data=body)
    assert_field_error(response, "ticket_price")


def test_missing_required_fields_are_each_reported(admin):
    response = admin.post("/api/admin/screenings", {})
    assert response.status_code == 400
    assert set(error_of(response)["fields"]) == {"movie_id", "room_id", "starts_at", "ticket_price"}


@pytest.mark.parametrize("field", ["movie_id", "room_id"])
@pytest.mark.parametrize("value", [None, 0, -1, "1", 1.0, True, [1]])
def test_ids_must_be_positive_integers(admin, movies, rooms, field, value):
    body = screening_body(movies[0]["movie_id"], rooms[0]["room_id"])
    body[field] = value
    assert_field_error(admin.post("/api/admin/screenings", body), field)


def test_an_unknown_movie_or_room_is_a_field_error(admin, movies, rooms):
    assert_field_error(admin.post("/api/admin/screenings", screening_body(999999, rooms[0]["room_id"])), "movie_id")
    assert_field_error(admin.post("/api/admin/screenings", screening_body(movies[0]["movie_id"], 999999)), "room_id")
    assert_field_error(admin.post("/api/admin/screenings", screening_body(10**30, rooms[0]["room_id"])), "movie_id")
    assert_field_error(admin.post("/api/admin/screenings", screening_body(movies[0]["movie_id"], 10**30)), "room_id")


@pytest.mark.parametrize("value", ["", "  ", "tomorrow", "2030-13-01T10:00", "2030-01-01T25:00", 5, True, None, "10:00"])
def test_start_time_must_be_a_valid_timestamp(admin, movies, rooms, value):
    body = screening_body(movies[0]["movie_id"], rooms[0]["room_id"])
    body["starts_at"] = value
    assert_field_error(admin.post("/api/admin/screenings", body), "starts_at")


@pytest.mark.parametrize("year", [1800, 1899, 2201, 9999])
def test_timestamps_outside_the_technical_year_range_are_400(admin, movies, rooms, year):
    body = screening_body(movies[0]["movie_id"], rooms[0]["room_id"])
    body["starts_at"] = f"{year}-06-01T10:00"
    assert_field_error(admin.post("/api/admin/screenings", body), "starts_at")
    body = screening_body(movies[0]["movie_id"], rooms[0]["room_id"], ends_at=f"{year}-06-01T10:00")
    assert_field_error(admin.post("/api/admin/screenings", body), "ends_at")


def test_end_time_must_be_after_the_start_time(admin, movies, rooms):
    day = next_day()
    for ends in (f"{day}T10:00", f"{day}T09:59"):
        response = admin.post("/api/admin/screenings", screening_body(movies[0]["movie_id"], rooms[0]["room_id"], day=day, ends_at=ends))
        assert_field_error(response, "ends_at")


def test_an_invalid_end_time_is_a_field_error_and_blank_means_calculate(admin, movies, rooms):
    assert_field_error(admin.post("/api/admin/screenings", screening_body(movies[0]["movie_id"], rooms[0]["room_id"], ends_at="soon")), "ends_at")
    created = create_screening(admin, movies[0]["movie_id"], rooms[0]["room_id"], ends_at="")
    span = dt.datetime.fromisoformat(created["ends_at"]) - dt.datetime.fromisoformat(created["starts_at"])
    assert span == dt.timedelta(minutes=movies[0]["duration_minutes"])  # calculated, not rejected


def test_invalid_screenings_create_nothing(admin, admin_db, movies, rooms):
    before = db_row(admin_db, "SELECT count(*) FROM showtimes")[0]
    admin.post("/api/admin/screenings", screening_body(movies[0]["movie_id"], rooms[0]["room_id"], price="-5"))
    admin.post("/api/admin/screenings", screening_body(999999, rooms[0]["room_id"]))
    assert db_row(admin_db, "SELECT count(*) FROM showtimes")[0] == before


# --- screenings: overlap (BR-04) -----------------------------------------------------------------


def test_an_overlapping_screening_in_the_same_room_is_409(admin, admin_db, movies, rooms):
    day = next_day()
    room = rooms[0]["room_id"]
    first = create_screening(admin, movies[0]["movie_id"], room, day=day, time="10:00")  # runs to 10:00 + duration
    before = db_row(admin_db, "SELECT count(*) FROM showtimes")[0]
    response = admin.post("/api/admin/screenings", screening_body(movies[0]["movie_id"], room, day=day, time="10:30"))
    assert response.status_code == 409
    assert error_of(response)["code"] == "screening_overlap"
    assert db_row(admin_db, "SELECT count(*) FROM showtimes")[0] == before
    assert first["has_bookings"] is False


def test_the_same_time_in_another_room_is_fine(admin, movies, rooms):
    day = next_day()
    create_screening(admin, movies[0]["movie_id"], rooms[0]["room_id"], day=day, time="10:00")
    create_screening(admin, movies[0]["movie_id"], rooms[1]["room_id"], day=day, time="10:00")


def test_back_to_back_screenings_do_not_overlap(admin, movies, rooms):
    day = next_day()
    room = rooms[0]["room_id"]
    first = create_screening(admin, movies[0]["movie_id"], room, day=day, time="10:00", ends_at=f"{day}T12:00")
    follow_up = admin.post("/api/admin/screenings", screening_body(movies[0]["movie_id"], room, day=day, time="12:00"))
    assert follow_up.status_code == 201  # the end instant belongs to no screening ([start, end))
    assert first["ends_at"].startswith(f"{day}T12:00:00")


def test_a_screening_fully_inside_another_is_409(admin, movies, rooms):
    day = next_day()
    room = rooms[0]["room_id"]
    create_screening(admin, movies[0]["movie_id"], room, day=day, time="10:00", ends_at=f"{day}T14:00")
    response = admin.post("/api/admin/screenings", screening_body(movies[0]["movie_id"], room, day=day, time="11:00", ends_at=f"{day}T12:00"))
    assert response.status_code == 409 and error_of(response)["code"] == "screening_overlap"


# --- screenings: update ---------------------------------------------------------------------------


def update_body(screening, **overrides):
    body = {
        "movie_id": screening["movie_id"], "room_id": screening["room_id"],
        "starts_at": screening["starts_at"], "ends_at": screening["ends_at"],
        "ticket_price": screening["ticket_price"],
    }
    body.update(overrides)
    return body


def test_update_an_unbooked_screening(admin, admin_db, movies, rooms):
    created = create_screening(admin, movies[0]["movie_id"], rooms[0]["room_id"])
    day = next_day()
    body = {"movie_id": movies[1]["movie_id"], "room_id": rooms[1]["room_id"],
            "starts_at": f"{day}T15:00", "ticket_price": "16500"}
    response = admin.put(f"/api/admin/screenings/{created['showtime_id']}", body)
    assert response.status_code == 200, response.get_json()
    updated = response.get_json()["screening"]
    assert updated["showtime_id"] == created["showtime_id"]
    assert updated["movie_id"] == movies[1]["movie_id"] and updated["room_id"] == rooms[1]["room_id"]
    assert updated["starts_at"] == f"{day}T15:00:00+09:00"
    assert updated["ticket_price"] == "16500.00"
    # the end time was left empty, so it follows the NEW movie's duration
    assert dt.datetime.fromisoformat(updated["ends_at"]) - dt.datetime.fromisoformat(updated["starts_at"]) == dt.timedelta(minutes=movies[1]["duration_minutes"])
    row = db_row(admin_db, "SELECT movie_id, room_id, ticket_price FROM showtimes WHERE showtime_id = %s", (created["showtime_id"],))
    assert (row[0], row[1], str(row[2])) == (movies[1]["movie_id"], rooms[1]["room_id"], "16500.00")


def test_update_validates_like_create_and_changes_nothing(admin, movies, rooms):
    created = create_screening(admin, movies[0]["movie_id"], rooms[0]["room_id"], price="11000")
    path = f"/api/admin/screenings/{created['showtime_id']}"
    for field, bad in [("ticket_price", "-1"), ("ticket_price", "Infinity"), ("movie_id", 0), ("starts_at", "nope")]:
        assert_field_error(admin.put(path, update_body(created, **{field: bad})), field)
    assert_field_error(admin.put(path, update_body(created, movie_id=999999)), "movie_id")
    assert_field_error(admin.put(path, update_body(created, room_id=999999)), "room_id")
    assert admin.get(path).get_json()["screening"] == created


def test_update_unknown_screening_is_404(admin, movies, rooms):
    body = screening_body(movies[0]["movie_id"], rooms[0]["room_id"])
    for path in ("/api/admin/screenings/999999", "/api/admin/screenings/0", f"/api/admin/screenings/{10**30}"):
        assert admin.put(path, body).status_code == 404


def test_a_screening_does_not_overlap_itself_when_resaved(admin, movies, rooms):
    created = create_screening(admin, movies[0]["movie_id"], rooms[0]["room_id"])
    response = admin.put(f"/api/admin/screenings/{created['showtime_id']}", update_body(created, ticket_price="15000"))
    assert response.status_code == 200
    assert response.get_json()["screening"]["ticket_price"] == "15000.00"


def test_update_into_an_overlap_is_409_and_keeps_the_old_values(admin, movies, rooms):
    day = next_day()
    room = rooms[0]["room_id"]
    create_screening(admin, movies[0]["movie_id"], room, day=day, time="10:00", ends_at=f"{day}T12:00")
    other = create_screening(admin, movies[0]["movie_id"], room, day=day, time="14:00", ends_at=f"{day}T16:00")
    response = admin.put(f"/api/admin/screenings/{other['showtime_id']}", update_body(other, starts_at=f"{day}T11:00", ends_at=f"{day}T13:00"))
    assert response.status_code == 409 and error_of(response)["code"] == "screening_overlap"
    assert admin.get(f"/api/admin/screenings/{other['showtime_id']}").get_json()["screening"] == other


# --- D2: a screening with any booking record cannot be modified ------------------------------------


@pytest.mark.parametrize("change", [
    {"ticket_price": "1.00"},
    {"starts_at": "SHIFT"},
    {"room_id": "OTHER_ROOM"},
    {"movie_id": "OTHER_MOVIE"},
])
def test_d2_a_booked_screening_cannot_be_changed(admin, customer, admin_db, movies, rooms, change):
    created = create_screening(admin, movies[0]["movie_id"], rooms[0]["room_id"])
    book_first_free_seat(customer, created["showtime_id"])
    resolved = {}
    for field, value in change.items():
        if value == "SHIFT":
            day = next_day()
            value = f"{day}T20:00"
        elif value == "OTHER_ROOM":
            value = rooms[1]["room_id"]
        elif value == "OTHER_MOVIE":
            value = movies[1]["movie_id"]
        resolved[field] = value
    body = update_body(created, **resolved)
    if "starts_at" in resolved:
        body.pop("ends_at")
    response = admin.put(f"/api/admin/screenings/{created['showtime_id']}", body)
    assert response.status_code == 409, response.get_json()
    assert error_of(response)["code"] == "screening_has_bookings"
    row = db_row(admin_db, "SELECT ticket_price FROM showtimes WHERE showtime_id = %s", (created["showtime_id"],))
    assert str(row[0]) == created["ticket_price"]
    assert admin.get(f"/api/admin/screenings/{created['showtime_id']}").get_json()["screening"] == {**created, "has_bookings": True}


def test_d2_a_cancelled_booking_still_protects_the_screening(admin, customer, movies, rooms):
    created = create_screening(admin, movies[0]["movie_id"], rooms[0]["room_id"])
    booking_id = book_first_free_seat(customer, created["showtime_id"])
    assert customer.post(f"/api/bookings/{booking_id}/cancel", {}).status_code == 200
    response = admin.put(f"/api/admin/screenings/{created['showtime_id']}", update_body(created, ticket_price="5"))
    assert response.status_code == 409 and error_of(response)["code"] == "screening_has_bookings"
    assert admin.get(f"/api/admin/screenings/{created['showtime_id']}").get_json()["screening"]["has_bookings"] is True


def test_d2_an_expired_booking_still_protects_the_screening(admin, customer, admin_db, movies, rooms):
    created = create_screening(admin, movies[0]["movie_id"], rooms[0]["room_id"])
    booking_id = book_first_free_seat(customer, created["showtime_id"])
    conn = admin_db.connect()
    try:
        time_travel.age_booking(conn, booking_id)
    finally:
        conn.close()
    assert customer.get(f"/api/bookings/{booking_id}").get_json()["booking"]["status"] == "EXPIRED"
    response = admin.put(f"/api/admin/screenings/{created['showtime_id']}", update_body(created, ticket_price="5"))
    assert response.status_code == 409 and error_of(response)["code"] == "screening_has_bookings"


def test_d2_saving_a_booked_screening_without_any_change_is_not_a_modification(admin, customer, movies, rooms):
    # The database rejects a changed value only; an identical save is accepted and changes nothing.
    created = create_screening(admin, movies[0]["movie_id"], rooms[0]["room_id"])
    book_first_free_seat(customer, created["showtime_id"])
    response = admin.put(f"/api/admin/screenings/{created['showtime_id']}", update_body(created))
    assert response.status_code == 200
    assert response.get_json()["screening"]["starts_at"] == created["starts_at"]


def test_a_booking_keeps_its_price_snapshot_when_the_screening_price_changes_before_booking(admin, customer, movies, rooms):
    created = create_screening(admin, movies[0]["movie_id"], rooms[0]["room_id"], price="10000")
    assert admin.put(f"/api/admin/screenings/{created['showtime_id']}", update_body(created, ticket_price="13000")).status_code == 200
    booking_id = book_first_free_seat(customer, created["showtime_id"])
    booking = customer.get(f"/api/bookings/{booking_id}").get_json()["booking"]
    assert booking["total_amount"] == "13000.00"
    assert booking["seats"][0]["price_at_booking"] == "13000.00"


# --- regression (Phase 5 browser check): messages are written for people, not for programmers ---

RAW_NAMES = ("starts_at", "ends_at", "movie_id", "room_id", "duration_minutes", "ticket_price", "release_date", " ID ")


def _all_messages(response):
    return list(error_of(response)["fields"].values())


def test_screening_validation_messages_name_no_internal_field(admin):
    empty = _all_messages(admin.post("/api/admin/screenings", {}))
    bad_time = _all_messages(admin.post("/api/admin/screenings", {
        "movie_id": 1, "room_id": 1, "starts_at": "not a time", "ends_at": "x", "ticket_price": 1}))
    odd_year = _all_messages(admin.post("/api/admin/screenings", {
        "movie_id": 1, "room_id": 1, "starts_at": "1800-01-01T10:00", "ticket_price": 1}))

    for message in empty + bad_time + odd_year:
        assert not any(raw in message for raw in RAW_NAMES), message
    assert "Please choose a movie." in empty and "Please choose a theater room." in empty
    assert "Start time is required." in empty
    assert "Start time must be a valid date and time." in bad_time
    assert "End time must be a valid date and time." in bad_time


def test_movie_validation_messages_name_no_internal_field(admin):
    missing = _all_messages(admin.post("/api/admin/movies", {}))
    wrong_type = _all_messages(admin.post("/api/admin/movies", {"title": "T", "duration_minutes": "90"}))

    for message in missing + wrong_type:
        assert not any(raw in message for raw in RAW_NAMES), message
    assert "Running time is required." in missing
    assert "Running time must be a whole number of minutes." in wrong_type


# --- a screening that has started can no longer be edited (like a real cinema) -----------------


def _spare_screening(admin_db, started=False, starts_in_hours=3):
    """A screening alone in its own new room (so it can be moved into the past without an overlap)."""
    conn = admin_db.connect()
    try:
        spare = time_travel.create_spare_room_screening(conn, starts_in_hours=starts_in_hours)
        if started:
            time_travel.start_screening_in_past(conn, spare["showtime_id"])
    finally:
        conn.close()
    return spare


def _screening_of(admin, spare):
    return admin.get(f"/api/admin/screenings/{spare['showtime_id']}").get_json()["screening"]


def test_a_started_screening_cannot_be_edited(admin, admin_db):
    spare = _spare_screening(admin_db, started=True)
    screening = _screening_of(admin, spare)
    assert screening["has_started"] is True and screening["has_bookings"] is False

    response = admin.put(f"/api/admin/screenings/{spare['showtime_id']}", update_body(screening, ticket_price="5000"))

    assert response.status_code == 409, response.get_json()
    assert error_of(response) == {"code": "screening_has_started",
                                  "message": "This screening has already started and can't be edited."}
    assert _screening_of(admin, spare) == screening  # nothing changed


def test_a_started_screening_rejects_even_an_identical_save(admin, admin_db):
    spare = _spare_screening(admin_db, started=True)
    screening = _screening_of(admin, spare)

    response = admin.put(f"/api/admin/screenings/{spare['showtime_id']}", update_body(screening))

    assert response.status_code == 409 and error_of(response)["code"] == "screening_has_started"


def test_a_future_screening_without_bookings_can_be_edited(admin, admin_db):
    spare = _spare_screening(admin_db)
    screening = _screening_of(admin, spare)
    assert screening["has_started"] is False and screening["has_bookings"] is False

    response = admin.put(f"/api/admin/screenings/{spare['showtime_id']}", update_body(screening, ticket_price="7500"))

    assert response.status_code == 200, response.get_json()
    assert _screening_of(admin, spare)["ticket_price"] == "7500.00"


def test_both_locks_apply_a_booked_future_screening_and_a_started_one_are_each_refused(admin, customer, admin_db):
    booked = _spare_screening(admin_db)
    book_first_free_seat(customer, booked["showtime_id"])
    response = admin.put(f"/api/admin/screenings/{booked['showtime_id']}",
                         update_body(_screening_of(admin, booked), ticket_price="1"))
    assert response.status_code == 409 and error_of(response)["code"] == "screening_has_bookings"

    # started AND booked: the booking was made while it was still in the future
    both = _spare_screening(admin_db)
    book_first_free_seat(customer, both["showtime_id"])
    conn = admin_db.connect()
    try:
        time_travel.start_screening_in_past(conn, both["showtime_id"])
    finally:
        conn.close()
    screening = _screening_of(admin, both)
    assert screening["has_started"] is True and screening["has_bookings"] is True
    response = admin.put(f"/api/admin/screenings/{both['showtime_id']}", update_body(screening, ticket_price="1"))
    assert response.status_code == 409 and error_of(response)["code"] == "screening_has_started"


def test_editing_an_unknown_screening_is_still_404_and_invalid_data_still_400(admin, admin_db):
    spare = _spare_screening(admin_db, started=True)
    screening = _screening_of(admin, spare)
    assert admin.put("/api/admin/screenings/99999999", update_body(screening)).status_code == 404
    bad = admin.put(f"/api/admin/screenings/{spare['showtime_id']}", {})  # validation comes before the lock
    assert bad.status_code == 400 and error_of(bad)["code"] == "validation_error"
