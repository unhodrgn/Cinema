MOVIE_COLUMNS = "movie_id, title, genre, duration_minutes, rating, synopsis, release_date, poster_url"


def fetch_movie(cur, movie_id):
    """The movie as a dict, or None."""
    cur.execute(f"SELECT {MOVIE_COLUMNS} FROM movies WHERE movie_id = %s", (movie_id,))
    row = cur.fetchone()
    return dict(row) if row is not None else None
