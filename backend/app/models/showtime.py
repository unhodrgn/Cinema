# One row shape for every API that shows a screening (catalog, seats, bookings, admin).
SCREENING_COLUMNS = """
    s.showtime_id, s.movie_id, m.title, m.poster_url, s.room_id, r.room_name,
    s.starts_at, s.ends_at, s.ticket_price,
    (s.starts_at <= clock_timestamp()) AS has_started
"""
SCREENING_FROM = """
    FROM showtimes s
    JOIN movies m ON m.movie_id = s.movie_id
    JOIN theater_rooms r ON r.room_id = s.room_id
"""
