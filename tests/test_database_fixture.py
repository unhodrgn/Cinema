"""Integration tests for the disposable-database fixture, against a real PostgreSQL.

These tests need a reachable server and are skipped when there is none (see
``cinema_test_db`` in conftest.py). They only ever touch databases named
``cinema_test_*`` that this test session created.
"""

from pathlib import Path

import pytest

import disposable_db
from app import create_app
from disposable_db import DatabaseSetupError, DisposableDatabase, UnsafeDatabaseError

TABLES = {
    "users",
    "movies",
    "theater_rooms",
    "seats",
    "showtimes",
    "bookings",
    "booking_seats",
}
FUNCTIONS = {"create_booking", "pay_booking", "cancel_booking", "expire_overdue_bookings"}


def scalar(connection, sql, params=None):
    with connection.cursor() as cur:
        cur.execute(sql, params)
        return cur.fetchone()[0]


def database_exists(settings, name):
    admin = disposable_db._open(settings, disposable_db.MAINTENANCE_DATABASE, autocommit=True)
    try:
        return scalar(admin, "SELECT count(*) FROM pg_database WHERE datname = %s", (name,)) == 1
    finally:
        admin.close()


# --- creation, name rules and marker --------------------------------------------------


def test_the_database_is_a_disposable_prefixed_database(cinema_test_db, db_connection):
    name = scalar(db_connection, "SELECT current_database()")

    assert name == cinema_test_db.name
    assert name.startswith(disposable_db.TEST_DB_PREFIX)
    assert name != disposable_db.MAINTENANCE_DATABASE


def test_the_database_carries_this_sessions_marker(cinema_test_db, postgres_settings):
    admin = disposable_db._open(postgres_settings, disposable_db.MAINTENANCE_DATABASE, True)
    try:
        comment = scalar(
            admin,
            "SELECT shobj_description(oid, 'pg_database') FROM pg_database WHERE datname = %s",
            (cinema_test_db.name,),
        )
    finally:
        admin.close()

    assert comment == disposable_db.MARKER
    assert cinema_test_db.name in disposable_db._created_this_session


def test_the_fixture_never_uses_the_development_database_name(cinema_test_db, monkeypatch):
    monkeypatch.setenv("DB_NAME", "cinema_dev")

    assert cinema_test_db.name != "cinema_dev"
    assert cinema_test_db.app_config()["DB_NAME"] == cinema_test_db.name


# --- schema and seed ------------------------------------------------------------------


def test_schema_was_applied(db_connection):
    tables = {
        row[0]
        for row in _fetch_all(
            db_connection,
            "SELECT table_name FROM information_schema.tables WHERE table_schema = 'public'",
        )
    }
    functions = {
        row[0]
        for row in _fetch_all(
            db_connection, "SELECT proname FROM pg_proc WHERE proname = ANY(%s)", (list(FUNCTIONS),)
        )
    }

    assert TABLES <= tables
    assert functions == FUNCTIONS
    assert scalar(db_connection, "SELECT count(*) FROM pg_extension WHERE extname = 'btree_gist'") == 1


@pytest.mark.parametrize(
    "table, expected",
    [("users", 3), ("movies", 6), ("theater_rooms", 5), ("seats", 250), ("showtimes", 280)],
)
def test_seed_record_counts(db_connection, table, expected):
    assert scalar(db_connection, f"SELECT count(*) FROM {table}") == expected


def test_seed_movies_are_the_six_real_films_with_posters(db_connection):
    rows = _fetch_all(db_connection, "SELECT title, genre, duration_minutes, rating, poster_url FROM movies ORDER BY movie_id")

    assert rows == [
        ("Jujutsu Kaisen 0", "Animation", 105, "15", "/images/posters/jjk-0.jpg"),
        ("Jujutsu Kaisen: Hidden Inventory / Premature Death", "Animation", 110, "15", "/images/posters/jjk-hidden-inventory.jpg"),
        ("Jujutsu Kaisen: Execution", "Animation", 87, "15", "/images/posters/jjk-execution.jpg"),
        ("20th Century Girl", "Romance", 119, "12", "/images/posters/20th-century-girl.jpg"),
        ("Exhuma", "Horror", 134, "15", "/images/posters/exhuma.jpg"),
        ("Godzilla x Kong: The New Empire", "Action", 115, "12", "/images/posters/godzilla-x-kong.jpg"),
    ]


def test_every_seeded_poster_file_exists_in_the_frontend(db_connection):
    frontend = Path(__file__).resolve().parents[1] / "frontend"
    for (url,) in _fetch_all(db_connection, "SELECT poster_url FROM movies"):
        assert (frontend / url.lstrip("/")).is_file(), url


@pytest.mark.parametrize("bad", ["a.jpg", "/images/posters/../a.jpg", "http://x/images/posters/a.jpg", "/images/posters/a.gif",
                                 "/images/posters/sub/a.jpg", "/images/posters/" + "a" * 250 + ".jpg"])
def test_the_database_itself_refuses_a_bad_poster_path(db_connection, bad):
    import psycopg2

    with db_connection.cursor() as cur, pytest.raises(psycopg2.Error):
        cur.execute("INSERT INTO movies(title, duration_minutes, poster_url) VALUES ('x', 90, %s)", (bad,))
    db_connection.rollback()


def test_every_seeded_movie_plays_every_day_without_overlap(db_connection):
    rows = _fetch_all(
        db_connection,
        "SELECT (starts_at AT TIME ZONE 'Asia/Seoul')::date AS d, movie_id, count(*) FROM showtimes GROUP BY 1, 2",
    )
    assert len({d for d, _, _ in rows}) == 14
    assert {n for _, _, n in rows} == {3, 4} and len(rows) == 14 * 6


def test_seed_leaves_no_bookings(db_connection):
    assert scalar(db_connection, "SELECT count(*) FROM bookings") == 0
    assert scalar(db_connection, "SELECT count(*) FROM booking_seats") == 0


def test_seed_roles(db_connection):
    roles = dict(_fetch_all(db_connection, "SELECT role, count(*) FROM users GROUP BY role"))

    assert roles == {"ADMIN": 1, "CUSTOMER": 2}


def _fetch_all(connection, sql, params=None):
    with connection.cursor() as cur:
        cur.execute(sql, params)
        return cur.fetchall()


# --- connection isolation -------------------------------------------------------------


def test_uncommitted_work_is_invisible_to_other_connections(cinema_test_db, db_connection):
    with db_connection.cursor() as cur:
        cur.execute("INSERT INTO movies(title, duration_minutes) VALUES ('Isolation probe', 90)")
    assert scalar(db_connection, "SELECT count(*) FROM movies") == 7

    other = cinema_test_db.connect()
    try:
        assert scalar(other, "SELECT count(*) FROM movies") == 6
    finally:
        other.close()


def test_the_fixture_rolls_back_uncommitted_work(db_connection):
    # The previous test inserted a row and never committed: it must not be here.
    assert scalar(db_connection, "SELECT count(*) FROM movies") == 6
    assert scalar(db_connection, "SELECT count(*) FROM movies WHERE title = 'Isolation probe'") == 0


def test_each_fixture_connection_is_a_separate_session(cinema_test_db):
    first, second = cinema_test_db.connect(), cinema_test_db.connect()
    try:
        assert scalar(first, "SELECT pg_backend_pid()") != scalar(second, "SELECT pg_backend_pid()")
    finally:
        first.close()
        second.close()


def test_app_config_builds_a_testing_app_for_the_test_database(db_app_config):
    app = create_app("testing", db_app_config)

    assert app.config["DB_NAME"].startswith(disposable_db.TEST_DB_PREFIX)
    assert app.config["TESTING"] is True


# --- cleanup and protection against dropping other databases --------------------------


@pytest.fixture
def fixed_name(monkeypatch):
    name = "cinema_test_unittest_" + disposable_db.uuid.uuid4().hex[:8]
    monkeypatch.setattr(disposable_db, "generate_database_name", lambda: name)
    return name


def test_a_provisioned_database_is_dropped_on_exit_and_others_survive(
    cinema_test_db, postgres_settings, fixed_name
):
    with disposable_db.provision_database(
        postgres_settings, _schema(), _seed()
    ) as extra:
        assert extra.name == fixed_name
        assert database_exists(postgres_settings, fixed_name)
        assert extra.name != cinema_test_db.name

    assert not database_exists(postgres_settings, fixed_name)
    assert database_exists(postgres_settings, cinema_test_db.name)


def test_cleanup_happens_even_if_the_test_body_fails(postgres_settings, cinema_test_db, fixed_name):
    with pytest.raises(RuntimeError, match="boom"):
        with disposable_db.provision_database(postgres_settings, _schema(), _seed()):
            raise RuntimeError("boom")

    assert not database_exists(postgres_settings, fixed_name)


def test_failed_schema_leaves_no_partial_database(
    cinema_test_db, postgres_settings, fixed_name, tmp_path
):
    broken = tmp_path / "broken_schema.sql"
    broken.write_text("CREATE TABLE ok_table(id int);\nTHIS IS NOT SQL;\n", encoding="utf-8")

    with pytest.raises(DatabaseSetupError, match="broken_schema.sql"):
        with disposable_db.provision_database(postgres_settings, broken, _seed()):
            pytest.fail("the body must not run when setup fails")

    assert not database_exists(postgres_settings, fixed_name)


def test_failed_seed_leaves_no_partial_database(
    cinema_test_db, postgres_settings, fixed_name, tmp_path
):
    broken = tmp_path / "broken_seed.sql"
    broken.write_text("INSERT INTO no_such_table VALUES (1);\n", encoding="utf-8")

    with pytest.raises(DatabaseSetupError, match="broken_seed.sql"):
        with disposable_db.provision_database(postgres_settings, _schema(), broken):
            pytest.fail("the body must not run when setup fails")

    assert not database_exists(postgres_settings, fixed_name)


def test_an_unrelated_prefixed_database_cannot_be_dropped(cinema_test_db, postgres_settings):
    """A ``cinema_test_*`` database that this session did not create is never dropped."""
    bystander = "cinema_test_bystander_" + disposable_db.uuid.uuid4().hex[:8]
    admin = disposable_db._open(postgres_settings, disposable_db.MAINTENANCE_DATABASE, True)
    try:
        with admin.cursor() as cur:
            cur.execute(f'CREATE DATABASE "{bystander}"')  # created by the test, not the fixture
        try:
            honest = DisposableDatabase(postgres_settings, name=bystander)
            with pytest.raises(UnsafeDatabaseError, match="not created by this fixture"):
                honest.drop()

            forged = DisposableDatabase(postgres_settings, name=bystander)
            forged.created = True
            with pytest.raises(UnsafeDatabaseError, match="not created by this fixture"):
                forged.drop()

            registered = DisposableDatabase(postgres_settings, name=bystander)
            registered.created = True
            disposable_db._created_this_session.add(bystander)
            try:
                with pytest.raises(UnsafeDatabaseError, match="marker"):
                    registered.drop()
            finally:
                disposable_db._created_this_session.discard(bystander)

            assert database_exists(postgres_settings, bystander)
        finally:
            with admin.cursor() as cur:
                cur.execute(f'DROP DATABASE IF EXISTS "{bystander}" WITH (FORCE)')
    finally:
        admin.close()


@pytest.mark.parametrize("name", ["postgres", "template1", "template0"])
def test_system_databases_cannot_be_targeted(cinema_test_db, postgres_settings, name):
    with pytest.raises(UnsafeDatabaseError):
        DisposableDatabase(postgres_settings, name=name)

    assert database_exists(postgres_settings, name)


def test_existing_database_is_never_overwritten(cinema_test_db, postgres_settings):
    clash = DisposableDatabase(postgres_settings, name=cinema_test_db.name)

    with pytest.raises(UnsafeDatabaseError, match="already exists"):
        clash.create()

    assert database_exists(postgres_settings, cinema_test_db.name)
    assert scalar(cinema_test_db.connect(), "SELECT count(*) FROM movies") == 6


def _schema():
    return disposable_db.SCHEMA_PATH


def _seed():
    return disposable_db.SEED_PATH
