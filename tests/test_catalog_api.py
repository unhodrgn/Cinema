"""T3: the public catalog (movies, screenings) through real Flask requests against PostgreSQL.

No login is needed for any of it (D4). Needs a disposable PostgreSQL (explicit TEST_DB_PORT).
"""

import datetime as dt
import re
import uuid
from zoneinfo import ZoneInfo

import pytest

import disposable_db
from app import create_app
from helpers import ApiClient
from time_travel import create_spare_room_screening, start_screening_in_past

FRONTEND = "http://localhost:8080"
EVIL = "http://evil.example"
FAR_DAY = "2030-03-15"  # far from the seed's 7-day window, so test rows never mix with it


@pytest.fixture(scope="module")
def catalog_db(cinema_template_db):
    with disposable_db.clone_database(cinema_template_db) as clone:
        yield clone


@pytest.fixture(scope="module")
def owner(catalog_db):
    connection = catalog_db.connect()
    yield connection
    connection.close()


@pytest.fixture(scope="module")
def app(catalog_db):
    return create_app("testing", dict(catalog_db.app_config(), CORS_ALLOWED_ORIGINS=FRONTEND))


@pytest.fixture
def client(app):
    return ApiClient(app.test_client(), origin=FRONTEND)


def scalar(connection, sql, params=()):
    with connection.cursor() as cur:
        cur.execute(sql, params)
        value = cur.fetchone()[0]
    connection.rollback()
    return value


def new_room(owner):
    with owner.cursor() as cur:
        cur.execute("INSERT INTO theater_rooms(room_name) VALUES (%s) RETURNING room_id",
                    ("Catalog " + uuid.uuid4().hex[:10],))
        room_id = cur.fetchone()[0]
    owner.commit()
    return room_id


def add_screening(owner, room_id, movie_id, start_local, end_local, price="9500.50"):
    """Insert a screening with cinema-local (Asia/Seoul) times, e.g. '2030-03-15 23:59'."""
    with owner.cursor() as cur:
        cur.execute(
            "INSERT INTO showtimes(movie_id, room_id, starts_at, ends_at, ticket_price) VALUES "
            "(%s, %s, %s::timestamp AT TIME ZONE 'Asia/Seoul', %s::timestamp AT TIME ZONE 'Asia/Seoul', %s) "
            "RETURNING showtime_id",
            (movie_id, room_id, start_local, end_local, price),
        )
        showtime_id = cur.fetchone()[0]
    owner.commit()
    return showtime_id


def add_movie(owner, title="Catalog movie", **columns):
    values = {"genre": None, "duration_minutes": 100, "rating": None, "synopsis": None, "release_date": None}
    values.update(columns)
    with owner.cursor() as cur:
        cur.execute(
            "INSERT INTO movies(title, genre, duration_minutes, rating, synopsis, release_date) "
            "VALUES (%s, %s, %s, %s, %s, %s) RETURNING movie_id",
            (title, values["genre"], values["duration_minutes"], values["rating"], values["synopsis"],
             values["release_date"]),
        )
        movie_id = cur.fetchone()[0]
    owner.commit()
    return movie_id


def error_of(response):
    return response.get_json()["error"]


# --- movies -----------------------------------------------------------------------------


def test_the_movie_list_needs_no_login_and_has_the_six_attributes(client):
    response = client.get("/api/movies")

    assert response.status_code == 200
    movies = response.get_json()["movies"]
    assert [m["title"] for m in movies][:6] == ["Jujutsu Kaisen 0", "Jujutsu Kaisen: Hidden Inventory / Premature Death", "Jujutsu Kaisen: Execution", "20th Century Girl", "Exhuma", "Godzilla x Kong: The New Empire"]
    first = movies[0]
    assert set(first) == {"movie_id", "title", "genre", "duration_minutes", "rating", "synopsis", "release_date", "poster_url"}
    assert first["genre"] == "Animation" and first["duration_minutes"] == 105 and first["rating"] == "15"
    assert first["synopsis"].startswith("Yuta Okkotsu") and first["release_date"] == "2022-02-17"
    assert first["poster_url"] == "/images/posters/jjk-0.jpg"
    assert [m["poster_url"] for m in movies[:6]] == [
        "/images/posters/" + f for f in ("jjk-0.jpg", "jjk-hidden-inventory.jpg", "jjk-execution.jpg",
                                         "20th-century-girl.jpg", "exhuma.jpg", "godzilla-x-kong.jpg")]
    assert "Set-Cookie" not in response.headers and response.headers["Cache-Control"] == "no-store"


def test_a_single_movie_matches_its_list_entry(client):
    movies = client.get("/api/movies").get_json()["movies"]

    detail = client.get(f"/api/movies/{movies[2]['movie_id']}")

    assert detail.status_code == 200
    assert detail.get_json() == {"movie": movies[2]}


def test_optional_movie_attributes_are_null_not_missing(client, owner):
    movie_id = add_movie(owner, title="No extras")

    movie = client.get(f"/api/movies/{movie_id}").get_json()["movie"]

    assert movie["title"] == "No extras" and movie["duration_minutes"] == 100
    assert movie["genre"] is None and movie["rating"] is None
    assert movie["synopsis"] is None and movie["release_date"] is None


def test_free_text_and_markup_in_a_movie_are_returned_unchanged_as_data(client, owner):
    hostile = '<img src=x onerror=alert(1)><script>alert(2)</script> & "quotes" \'single\''
    movie_id = add_movie(owner, title=hostile, genre="한국어 장르", synopsis=hostile + "\nline two")

    movie = client.get(f"/api/movies/{movie_id}").get_json()["movie"]
    listed = next(m for m in client.get("/api/movies").get_json()["movies"] if m["movie_id"] == movie_id)

    assert movie["title"] == hostile and movie["genre"] == "한국어 장르"
    assert movie["synopsis"] == hostile + "\nline two"
    assert listed == movie


@pytest.mark.parametrize("path", ["/api/movies/999999", "/api/movies/0", "/api/movies/-1", "/api/movies/abc",
                                   "/api/movies/1.5", "/api/movies/99999999999999999999",
                                   "/api/movies/9223372036854775808", "/api/movies/%27%20OR%201=1",
                                   "/api/movies/1/extra"])
def test_unknown_or_unusable_movie_ids_are_a_json_404_never_a_500(client, path):
    response = client.get(path)

    assert response.status_code == 404
    assert response.mimetype == "application/json"
    assert error_of(response)["code"] == "not_found"
    assert "SELECT" not in response.get_data(as_text=True)


def test_the_largest_valid_id_is_looked_up_normally(client):
    assert client.get("/api/movies/9223372036854775807").status_code == 404  # valid id, no such movie


# --- screenings by day ------------------------------------------------------------------


def test_screenings_are_listed_for_one_day_with_the_documented_fields(client, owner):
    room = new_room(owner)
    movie_id = add_movie(owner, title="Day movie")
    show = add_screening(owner, room, movie_id, f"{FAR_DAY} 19:00", f"{FAR_DAY} 21:00")

    response = client.get(f"/api/screenings?date={FAR_DAY}&movie_id={movie_id}")

    assert response.status_code == 200
    body = response.get_json()
    assert body["date"] == FAR_DAY and len(body["screenings"]) == 1
    row = body["screenings"][0]
    assert set(row) == {"showtime_id", "movie_id", "title", "poster_url", "room_id", "room_name", "starts_at",
                        "ends_at", "ticket_price", "has_started"}
    assert row["poster_url"] is None  # a movie added without a poster
    assert row["showtime_id"] == show and row["title"] == "Day movie" and row["room_id"] == room
    assert row["starts_at"] == f"{FAR_DAY}T19:00:00+09:00" and row["ends_at"] == f"{FAR_DAY}T21:00:00+09:00"
    assert row["ticket_price"] == "9500.50" and isinstance(row["ticket_price"], str)
    assert row["has_started"] is False
    assert re.fullmatch(r".*[+-]\d\d:\d\d", row["starts_at"])


def test_the_day_is_the_cinemas_local_calendar_day_with_exact_boundaries(client, owner):
    room = new_room(owner)
    movie_id = add_movie(owner, title="Boundary movie")
    day_before = add_screening(owner, room, movie_id, "2030-04-14 23:59", "2030-04-15 00:00")
    first = add_screening(owner, room, movie_id, "2030-04-15 00:00", "2030-04-15 00:30")
    last = add_screening(owner, room, movie_id, "2030-04-15 23:59", "2030-04-16 00:00")
    day_after = add_screening(owner, room, movie_id, "2030-04-16 00:00", "2030-04-16 00:30")

    ids = lambda day: [r["showtime_id"] for r in client.get(
        f"/api/screenings?date={day}&movie_id={movie_id}").get_json()["screenings"]]

    assert ids("2030-04-15") == [first, last]  # 00:00 is in, 23:59 is in, neighbours are out
    assert ids("2030-04-14") == [day_before]
    assert ids("2030-04-16") == [day_after]


def test_screenings_are_ordered_by_start_time_then_room(client, owner):
    movie_id = add_movie(owner, title="Order movie")
    room_a, room_b = new_room(owner), new_room(owner)
    late = add_screening(owner, room_a, movie_id, "2030-05-01 20:00", "2030-05-01 21:00")
    early = add_screening(owner, room_b, movie_id, "2030-05-01 09:00", "2030-05-01 10:00")
    same_a = add_screening(owner, room_a, movie_id, "2030-05-01 12:00", "2030-05-01 13:00")
    same_b = add_screening(owner, room_b, movie_id, "2030-05-01 12:00", "2030-05-01 13:00")

    rows = client.get(f"/api/screenings?date=2030-05-01&movie_id={movie_id}").get_json()["screenings"]

    assert [r["showtime_id"] for r in rows] == [early, same_a, same_b, late]
    assert room_a < room_b


def test_without_a_movie_all_movies_of_the_day_are_listed(client, owner):
    room = new_room(owner)
    first, second = add_movie(owner, title="All A"), add_movie(owner, title="All B")
    add_screening(owner, room, first, "2030-06-01 10:00", "2030-06-01 11:00")
    add_screening(owner, room, second, "2030-06-01 12:00", "2030-06-01 13:00")

    rows = client.get("/api/screenings?date=2030-06-01").get_json()["screenings"]

    assert [r["title"] for r in rows] == ["All A", "All B"]
    assert len(client.get(f"/api/screenings?date=2030-06-01&movie_id={first}").get_json()["screenings"]) == 1


def test_a_day_without_screenings_is_an_empty_list(client):
    response = client.get("/api/screenings?date=2031-01-01")

    assert response.status_code == 200
    assert response.get_json() == {"date": "2031-01-01", "screenings": []}


def test_the_seeded_week_has_three_or_four_screenings_per_movie_per_day(client, owner):
    day = scalar(owner, "SELECT (min(starts_at) AT TIME ZONE 'Asia/Seoul')::date::text FROM showtimes "
                        "WHERE starts_at > now() - interval '1 day' AND room_id <= 5")
    movies = client.get("/api/movies").get_json()["movies"][:6]

    rows = client.get(f"/api/screenings?date={day}").get_json()["screenings"]
    assert len(rows) >= 20
    counts = []
    for movie in movies:  # 6 movies share the 20 daily slots: every movie plays every day
        per_movie = client.get(f"/api/screenings?date={day}&movie_id={movie['movie_id']}").get_json()["screenings"]
        assert all(r["movie_id"] == movie["movie_id"] for r in per_movie)
        counts.append(len(per_movie))
    assert counts == [3, 3, 3, 4, 4, 3]


def test_the_default_day_is_today_in_the_cinemas_time_zone_decided_by_the_database(client, owner):
    before = scalar(owner, "SELECT (now() AT TIME ZONE 'Asia/Seoul')::date::text")
    body = client.get("/api/screenings").get_json()
    after = scalar(owner, "SELECT (now() AT TIME ZONE 'Asia/Seoul')::date::text")

    assert body["date"] in {before, after}
    assert client.get("/api/screenings?date=").get_json()["date"] in {before, after}  # empty = not given


def test_has_started_comes_from_the_database_clock(client, owner):
    spare = create_spare_room_screening(owner)
    future = client.get(f"/api/screenings/{spare['showtime_id']}").get_json()["screening"]
    start_screening_in_past(owner, spare["showtime_id"])
    started = client.get(f"/api/screenings/{spare['showtime_id']}").get_json()["screening"]

    assert future["has_started"] is False and started["has_started"] is True
    assert started["starts_at"] < future["starts_at"]


def test_a_single_screening_has_the_same_shape_as_a_list_row(client, owner):
    room = new_room(owner)
    movie_id = add_movie(owner, title="Single")
    show = add_screening(owner, room, movie_id, "2030-07-01 18:30", "2030-07-01 20:00", price="0")

    single = client.get(f"/api/screenings/{show}").get_json()["screening"]
    listed = client.get(f"/api/screenings?date=2030-07-01&movie_id={movie_id}").get_json()["screenings"][0]

    assert single == listed and single["ticket_price"] == "0.00"


@pytest.mark.parametrize("date", ["2026-13-40", "2026-02-30", "20261125", "2026-W47-3", "2026-11-5", "26-11-25",
                                   "2026/11/25", "2026-11-25T10:00", "2026-11-25 ", "tomorrow", "0000-01-01",
                                   "'; DROP TABLE showtimes; --", "2026-11-25%00", "２０２６-１１-２５", "-1"])
def test_an_invalid_date_is_a_validation_error(client, date):
    response = client.get("/api/screenings", query_string={"date": date})

    if date == "2026-11-25 ":  # surrounding blanks are tolerated, like an empty value
        assert response.status_code == 200
        return
    assert response.status_code == 400
    assert error_of(response)["code"] == "validation_error"
    assert set(error_of(response)["fields"]) == {"date"}
    assert error_of(response)["fields"]["date"] == "Use the format YYYY-MM-DD, for example 2026-11-25."
    # the offending value is never echoed back (the fixed hint itself contains a sample date)
    echoed = response.get_data(as_text=True).replace(error_of(response)["fields"]["date"], "")
    assert date not in echoed


@pytest.mark.parametrize("movie_id", ["abc", "0", "-1", "1.5", "1e3", "99999999999999999999", "9223372036854775808",
                                       "1 OR 1=1", "'", "١٢"])
def test_an_invalid_movie_id_is_a_validation_error(client, movie_id):
    response = client.get("/api/screenings", query_string={"movie_id": movie_id})

    assert response.status_code == 400
    assert error_of(response)["code"] == "validation_error"
    assert error_of(response)["fields"] == {"movie_id": "Must be a positive whole number."}


def test_both_bad_parameters_are_reported_together(client):
    response = client.get("/api/screenings?movie_id=x&date=y")

    assert set(error_of(response)["fields"]) == {"movie_id", "date"}


def test_an_unknown_movie_in_the_schedule_is_a_404(client):
    response = client.get("/api/screenings?date=2030-03-15&movie_id=999999")

    assert response.status_code == 404 and error_of(response)["code"] == "not_found"


def test_extra_and_repeated_query_parameters_are_harmless(client):
    response = client.get("/api/screenings?date=2031-01-01&date=garbage&unknown=1&movie_id=")

    assert response.status_code == 200 and response.get_json()["date"] == "2031-01-01"


@pytest.mark.parametrize("path", ["/api/screenings/999999", "/api/screenings/0", "/api/screenings/-5",
                                   "/api/screenings/abc", "/api/screenings/99999999999999999999"])
def test_unknown_or_unusable_screening_ids_are_a_json_404(client, path):
    response = client.get(path)

    assert response.status_code == 404 and error_of(response)["code"] == "not_found"


# --- access, headers, method rules ------------------------------------------------------


@pytest.mark.parametrize("path", ["/api/movies", "/api/movies/1", "/api/screenings", "/api/screenings/1"])
def test_the_catalog_is_public_and_carries_no_cookie_or_token(client, path):
    response = client.get(path)

    assert response.status_code == 200  # no Authorization header was sent
    assert "Set-Cookie" not in response.headers
    assert response.headers["Cache-Control"] == "no-store"
    assert response.headers["X-Content-Type-Options"] == "nosniff"


def test_a_token_is_not_required_but_an_invalid_one_does_not_break_a_public_page(client):
    response = client.get("/api/movies", headers={"Authorization": "Bearer not.a.token"})

    assert response.status_code == 200  # public routes do not look at the token


@pytest.mark.parametrize("path", ["/api/movies", "/api/movies/1", "/api/screenings", "/api/screenings/1"])
def test_the_catalog_is_read_only(client, path):
    for method in ("post", "put", "delete"):
        response = getattr(client, method)(path, **({"json": {}} if method != "delete" else {}))
        assert response.status_code == 405, (method, path)
        assert error_of(response)["code"] == "method_not_allowed"
        assert "GET" in response.headers["Allow"]


def test_the_frontend_origin_may_read_the_catalog_and_other_origins_may_not(app, client):
    allowed = client.get("/api/movies")
    foreign = ApiClient(app.test_client(), origin=EVIL).get("/api/movies")
    preflight = client.options("/api/screenings", headers={"Origin": FRONTEND, "Access-Control-Request-Method": "GET"})
    wrong_method = client.options("/api/screenings", headers={"Origin": FRONTEND, "Access-Control-Request-Method": "POST"})

    assert allowed.headers["Access-Control-Allow-Origin"] == FRONTEND
    assert "Access-Control-Allow-Origin" not in foreign.headers
    assert preflight.status_code == 204 and preflight.headers["Access-Control-Allow-Origin"] == FRONTEND
    assert "Access-Control-Allow-Origin" not in wrong_method.headers
    # errors stay readable by the frontend
    assert client.get("/api/movies/999999").headers["Access-Control-Allow-Origin"] == FRONTEND


def test_catalog_errors_never_leak_database_details(client):
    texts = [client.get(p).get_data(as_text=True) for p in
             ("/api/movies/999999", "/api/screenings?date=x", "/api/screenings?movie_id=x", "/api/screenings/0")]

    for text in texts:
        for marker in ("SELECT", "psycopg2", "Traceback", "showtimes", "movies WHERE", "postgres"):
            assert marker not in text


def test_the_catalog_reports_a_database_outage_safely(catalog_db):
    unreachable = create_app("testing", dict(catalog_db.app_config(), DB_PORT=1, DB_CONNECT_TIMEOUT=1,
                                             CORS_ALLOWED_ORIGINS=FRONTEND))
    client = ApiClient(unreachable.test_client(), origin=FRONTEND)

    for path in ("/api/movies", "/api/movies/1", "/api/screenings", "/api/screenings/1"):
        response = client.get(path)
        assert response.status_code == 503 and error_of(response)["code"] == "database_unavailable"
        assert catalog_db.name not in response.get_data(as_text=True)
        assert response.headers["Access-Control-Allow-Origin"] == FRONTEND
