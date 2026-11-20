"""app/params.py: id guard and query-parameter readers."""

import psycopg2
import pytest
from flask import Flask

from app import params
from app.errors import AppError, ValidationError  # noqa: F401  (ValidationError documents intent)
from app.params import MAX_ID, check_path_id, query_date, query_id


@pytest.mark.parametrize("value", [1, 2, 12345, MAX_ID])
def test_usable_ids_pass(value):
    assert check_path_id(value) == value


@pytest.mark.parametrize("value", [0, -1, -MAX_ID, MAX_ID + 1, 10**30, True, False, "1", None, 1.0])
def test_unusable_ids_are_the_standard_404(value):
    with pytest.raises(AppError) as caught:
        check_path_id(value)

    assert caught.value.info.status == 404 and caught.value.info.code == "not_found"


def readers(query):
    """Run both readers inside a request with the given query string."""
    app = Flask(__name__)
    with app.test_request_context(query):
        problems = {}
        movie, day = query_id("movie_id", problems), query_date("date", problems)
        return movie, day, problems


def test_readers_accept_good_values_and_blanks():
    assert readers("/?movie_id=7&date=2026-11-25") == (7, "2026-11-25", {})
    assert readers("/?movie_id=&date=") == (None, None, {})
    assert readers("/") == (None, None, {})
    assert readers("/?movie_id=%207%20&date=%202026-11-25%20") == (7, "2026-11-25", {})
    assert readers(f"/?movie_id={MAX_ID}")[0] == MAX_ID


@pytest.mark.parametrize("query, field", [
    ("/?movie_id=0", "movie_id"), ("/?movie_id=-3", "movie_id"), ("/?movie_id=1.5", "movie_id"),
    (f"/?movie_id={MAX_ID + 1}", "movie_id"), ("/?movie_id=" + "9" * 40, "movie_id"), ("/?movie_id=x", "movie_id"),
    ("/?date=2026-02-30", "date"), ("/?date=20261125", "date"), ("/?date=2026-W47-3", "date"),
    ("/?date=2026-1-1", "date"), ("/?date=2026-11-25T00:00", "date"),
])
def test_readers_report_bad_values_by_field(query, field):
    movie, day, problems = readers(query)

    assert set(problems) == {field}
    assert (movie if field == "movie_id" else day) is None


def test_a_huge_id_really_breaks_a_database_function_call_which_is_why_the_guard_exists(cinema_template_db):
    """Plain comparisons just match nothing, but a bigint FUNCTION parameter raises an error.

    The booking functions (pay_booking, cancel_booking) take the id from the URL, so without
    ``check_path_id`` a long number in the address would turn into a server error.
    """
    import disposable_db

    with disposable_db.clone_database(cinema_template_db) as clone:
        connection = clone.connect()
        try:
            with connection.cursor() as cur:
                cur.execute("SELECT count(*) FROM movies WHERE movie_id = %s", (MAX_ID + 1,))
                assert cur.fetchone()[0] == 0  # harmless in a comparison
            connection.rollback()
            with pytest.raises(psycopg2.Error):
                with connection.cursor() as cur:
                    cur.execute("SELECT pay_booking(%s, %s)", (MAX_ID + 1, 1))
            connection.rollback()
        finally:
            connection.close()
