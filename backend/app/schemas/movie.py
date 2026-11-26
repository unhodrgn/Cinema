import re

from app.core.errors import ValidationError
from app.core.params import strict_iso_date


# Same rule as the CHECK on movies.poster_url: a file directly under /images/posters/.
POSTER_PATH = re.compile(r"/images/posters/[A-Za-z0-9][A-Za-z0-9._-]*\.(jpg|png)")
POSTER_PROBLEM = "Poster path must look like /images/posters/name.jpg (at most 255 characters)."


def validate_movie_input(body):
    problems = {}

    title = body.get("title")
    if not isinstance(title, str) or not title.strip():
        problems["title"] = "Title is required."
    elif len(title.strip()) > 200:
        problems["title"] = "Title must be at most 200 characters."
    else:
        title = title.strip()

    duration = body.get("duration_minutes")
    if duration is None:
        problems["duration_minutes"] = "Running time is required."
    elif isinstance(duration, bool) or not isinstance(duration, int):
        problems["duration_minutes"] = "Running time must be a whole number of minutes."
    elif not (1 <= duration <= 300):
        problems["duration_minutes"] = "Running time must be between 1 and 300 minutes."

    genre = body.get("genre")
    if genre is not None:
        if not isinstance(genre, str):
            problems["genre"] = "Genre must be text."
        else:
            genre = genre.strip() or None
            if genre and len(genre) > 100:
                problems["genre"] = "Genre must be at most 100 characters."

    rating = body.get("rating")
    if rating is not None:
        if not isinstance(rating, str):
            problems["rating"] = "Rating must be text."
        else:
            rating = rating.strip() or None
            if rating and len(rating) > 50:
                problems["rating"] = "Rating must be at most 50 characters."

    synopsis = body.get("synopsis")
    if synopsis is not None:
        if not isinstance(synopsis, str):
            problems["synopsis"] = "Synopsis must be text."
        else:
            synopsis = synopsis.strip() or None

    release_date = body.get("release_date")
    if release_date is not None:
        if not isinstance(release_date, str):
            problems["release_date"] = "Release date must be in YYYY-MM-DD format."
        else:
            release_date = release_date.strip() or None
            if release_date and strict_iso_date(release_date) is None:
                problems["release_date"] = "Release date must be in YYYY-MM-DD format."

    poster_url = body.get("poster_url")
    if poster_url is not None:
        if not isinstance(poster_url, str):
            problems["poster_url"] = POSTER_PROBLEM
        else:
            poster_url = poster_url.strip() or None
            if poster_url and (len(poster_url) > 255 or not POSTER_PATH.fullmatch(poster_url)):
                problems["poster_url"] = POSTER_PROBLEM

    # PostgreSQL cannot store NUL (0x00); psycopg2 would raise ValueError -> HTTP 500.
    for name, value in (("title", title), ("genre", genre), ("rating", rating), ("synopsis", synopsis)):
        if name not in problems and isinstance(value, str) and "\x00" in value:
            problems[name] = "Text must not contain NUL (0x00) characters."

    if problems:
        raise ValidationError(problems)

    return {
        "title": title,
        "genre": genre,
        "duration_minutes": duration,
        "rating": rating,
        "synopsis": synopsis,
        "release_date": release_date,
        "poster_url": poster_url,
    }
