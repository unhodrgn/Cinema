from app.models.showtime import SCREENING_COLUMNS, SCREENING_FROM


def fetch_screening(cur, showtime_id):
    """The screening as a dict, or None."""
    cur.execute(
        f"SELECT {SCREENING_COLUMNS} {SCREENING_FROM} WHERE s.showtime_id = %s", (showtime_id,)
    )
    row = cur.fetchone()
    return dict(row) if row is not None else None
