"""Movie catalog (public): B03 C-02. Login is not required (D4).

The six approved movie attributes (D5) plus the technical key. B03 calls the running time
``duration``; the column and the API field are ``duration_minutes``.
"""

from flask import Blueprint, jsonify

from .database import transaction
from .errors import HTTP_ERRORS, AppError
from .params import check_path_id
from .security import Policy, policy

bp = Blueprint("movies", __name__, url_prefix="/movies")

MOVIE_COLUMNS = "movie_id, title, genre, duration_minutes, rating, synopsis, release_date, poster_url"


def fetch_movie(cur, movie_id):
    """The movie as a dict, or None."""
    cur.execute(f"SELECT {MOVIE_COLUMNS} FROM movies WHERE movie_id = %s", (movie_id,))
    row = cur.fetchone()
    return dict(row) if row is not None else None


@bp.get("")
@policy(Policy.PUBLIC)
def list_movies():
    with transaction() as cur:
        cur.execute(f"SELECT {MOVIE_COLUMNS} FROM movies ORDER BY movie_id")
        movies = [dict(row) for row in cur.fetchall()]
    return jsonify(movies=movies)


@bp.get("/<int:movie_id>")
@policy(Policy.PUBLIC)
def get_movie(movie_id):
    check_path_id(movie_id)
    with transaction() as cur:
        movie = fetch_movie(cur, movie_id)
    if movie is None:
        raise AppError(HTTP_ERRORS[404])
    return jsonify(movie=movie)
