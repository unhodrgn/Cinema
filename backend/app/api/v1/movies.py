"""Movie catalog (public): B03 C-02. Login is not required (D4).

The six approved movie attributes (D5) plus the technical key. B03 calls the running time
``duration``; the column and the API field are ``duration_minutes``.
"""

from flask import Blueprint, jsonify

from app.core.database import transaction
from app.core.errors import HTTP_ERRORS, AppError
from app.core.params import check_path_id
from app.core.security import Policy, policy

from app.models.movie import MOVIE_COLUMNS, fetch_movie

bp = Blueprint("movies", __name__, url_prefix="/movies")

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
